"""
workouts.py - builds a fresh home workout for today from the moves library.

How it works:
- Tulsi picks the FOCUS (full body, legs, core, cardio, arms, gentle) and LEVEL from your cycle phase, sleep,
  stress, energy and what you trained yesterday, and says why.
- How LONG it is comes from a quiet daily burn goal: a gentle baseline, plus a little more if you've eaten above
  your target today (capped, and lower on gentle days). It never asks you to "burn off" food.
- The code then builds the workout (warm-up, main moves, cool-down) and works out the calories with
  MET x weight x time, so the numbers are calculated, never guessed.
"""

import random
from datetime import date, timedelta

import diet
import exercise
import journey
import storage

FOCUSES = {  # key: (label, the tags a main move must have)
    "full": ("🏃‍♀️ Full body", {"legs", "core", "upper", "cardio", "full"}),
    "legs": ("🍑 Legs & glutes", {"legs"}),
    "core": ("🧱 Core", {"core"}),
    "cardio": ("❤️ Cardio", {"cardio"}),
    "upper": ("💪 Arms & upper body", {"upper"}),
    "gentle": ("🌸 Gentle & stretch", {"gentle"}),
}
LEVELS = {1: "Gentle", 2: "Beginner", 3: "Intermediate"}
TIME_CHOICES = [10, 15, 20, 30, 45]
BASE_BURN = 150      # a normal day's movement goal, in kcal (about 30 min of home workout)
EXTRA_CAP = 150      # the most we ever add for eating above target
GENTLE_CAP = 120     # gentle days never ask for more than this
REST_BETWEEN_SETS = 25  # seconds


# ---------------- What fits today ----------------

def _today_state() -> dict:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    checkins = storage.load_checkins()
    c = checkins.get(today) or checkins.get(yesterday) or {}
    rows = journey.all_days()
    sleep = float((rows.get(today) or rows.get(yesterday) or {}).get("sleep_hours") or 7)
    info = journey.cycle_info() or {}
    try:
        import cycle
        phase = (cycle.day_info(date.today()) or {}).get("phase") or info.get("phase")
    except Exception:
        phase = info.get("phase")
    trained = [e.get("focus") for e in storage.load_exercises().get(yesterday, []) if e.get("focus")]
    return {"sleep": sleep, "stress": int(c.get("stress") or 2), "energy": int(c.get("energy") or 3),
            "phase": phase, "yesterday": trained[-1] if trained else None}


def tulsi_pick() -> dict:
    """Focus, level and the reason, from your cycle phase, sleep, stress, energy and yesterday's workout."""
    s = _today_state()
    if s["phase"] == "Period" or s["sleep"] < 6 or s["stress"] >= 4 or s["energy"] <= 2:
        why = ("you're on your period" if s["phase"] == "Period" else "you slept less than 6 hours" if s["sleep"] < 6
               else "you're stressed" if s["stress"] >= 4 else "your energy is low")
        return {"focus": "gentle", "level": 1, "gentle_day": True,
                "why": f"Because {why}, gentle movement is best today. It keeps cortisol down and still counts."}
    if s["phase"] == "Luteal":
        focus = "core" if s["yesterday"] == "legs" else "legs"
        return {"focus": focus, "level": 2, "gentle_day": False,
                "why": "In the week or so before your period, steady strength work feels better than lots of jumping."}
    if s["phase"] in ("Follicular", "Ovulation") and s["energy"] >= 4:
        focus = "full" if s["yesterday"] == "cardio" else "cardio"
        return {"focus": focus, "level": 3, "gentle_day": False,
                "why": "Your energy is high and this is your strongest time of the cycle, so today can be a little harder."}
    rotation = ["full", "legs", "cardio", "core", "upper"]
    options = [f for f in rotation if f != s["yesterday"]]
    focus = options[date.today().toordinal() % len(options)]
    return {"focus": focus, "level": 2, "gentle_day": False,
            "why": "A steady day. Tulsi picked a different focus from yesterday so every part of you gets a turn."}


def burn_plan(profile: dict, day: str | None = None, gentle_day: bool = False) -> dict:
    """Today's quiet movement goal. Baseline, plus a little extra if you've eaten above your target (capped)."""
    day = day or date.today().isoformat()
    target = diet.target(profile)["kcal"]
    eaten = storage.day_calories(day)
    burned = exercise.day_total(day)["kcal"]
    extra = min(EXTRA_CAP, max(0, eaten - target))
    base = int(profile.get("burn_goal") or BASE_BURN)
    goal = base + extra
    if gentle_day:
        goal = min(goal, GENTLE_CAP)
    return {"target": target, "eaten": eaten, "burned": burned, "base": base, "extra": extra, "goal": goal,
            "left": max(0, goal - burned), "progress": min(1.0, burned / goal) if goal else 1.0}


# ---------------- Building a workout ----------------

def _pool(focus: str, level: int, used: set) -> list[str]:
    want = FOCUSES[focus][1]
    out = []
    for name, (tags, lvl) in exercise.TAGS.items():
        if name in used or lvl > level or not (tags & want):
            continue
        if focus != "gentle" and (tags <= {"gentle", "cooldown", "warmup"} or ("warmup" in tags and level >= 2)):
            continue
        out.append(name)
    return out


def _dose(name: str, level: int, gentle: bool) -> tuple[int, float]:
    """Sets and amount per set for a move at this level."""
    unit = exercise.MOVE[name][3]
    if gentle:
        return {"reps": (2, 10), "sec": (2, 40), "min": (1, 3)}[unit]
    sets = 3
    if unit == "reps":
        return sets, {1: 10, 2: 12, 3: 15}[level] * (2 if "Count both" in exercise.MOVE[name][5] else 1)
    if unit == "sec":
        return sets, {1: 30, 2: 40, 3: 45}[level]
    return 1, {1: 2, 2: 3, 3: 4}[level]


def _row(name: str, sets: int, amount: float, part: str, weight: float, rest_s: float) -> dict:
    active = exercise.move_minutes(name, sets, amount)
    rest = rest_s * max(0, sets - 1) / 60
    m = exercise.MOVE[name]
    return {"move": name, "sets": sets, "amount": amount, "emoji": m[1], "tip": m[5], "part": part,
            "text": exercise.amount_text(name, sets, amount), "minutes": active + rest,
            "kcal": round(exercise.kcal(m[2], weight, active) + exercise.kcal(exercise.REST_MET, weight, rest))}


def build(focus: str, level: int, minutes: int, weight: float, seed: int = 0) -> list[dict]:
    """A fresh workout: a short warm-up, main moves until the time is filled, and a cool-down."""
    rng = random.Random(f"{date.today().isoformat()}-{focus}-{level}-{minutes}-{seed}")
    gentle = focus == "gentle"
    rows, used = [], set()

    warm = [n for n, (t, l) in exercise.TAGS.items() if "warmup" in t and l <= max(level, 1)]
    for name in rng.sample(warm, 2):
        unit = exercise.MOVE[name][3]
        rows.append(_row(name, 1, 1 if unit == "min" else 45, "Warm-up", weight, 0))
        used.add(name)
    cool = [n for n, (t, _) in exercise.TAGS.items() if "cooldown" in t]
    cool_rows = []
    for name in rng.sample(cool, 2):
        unit = exercise.MOVE[name][3]
        cool_rows.append(_row(name, 1, 1 if unit == "min" else 40, "Cool-down", weight, 0))
        used.add(name)

    budget = minutes - sum(r["minutes"] for r in rows + cool_rows)
    pool = _pool(focus, level, used)
    rng.shuffle(pool)
    if focus == "full":  # mix areas: take one from each in turn
        by_area = {a: [n for n in pool if a in exercise.TAGS[n][0]] for a in ("legs", "core", "upper", "cardio")}
        order, pool = [], []
        while any(by_area.values()):
            for a in ("legs", "cardio", "core", "upper"):
                while by_area[a] and (by_area[a][0] in order):
                    by_area[a].pop(0)
                if by_area[a]:
                    order.append(by_area[a].pop(0))
        pool = order
    for name in pool:
        if budget < 1.5:
            break
        sets, amount = _dose(name, level, gentle)
        row = _row(name, sets, amount, "Main", weight, 15 if gentle else REST_BETWEEN_SETS)
        if row["minutes"] > budget + 1:
            sets = max(1, sets - 1)
            row = _row(name, sets, amount, "Main", weight, 15 if gentle else REST_BETWEEN_SETS)
            if row["minutes"] > budget + 1:
                continue
        rows.append(row)
        used.add(name)
        budget -= row["minutes"] + 0.25  # a short breather between moves
    return rows + cool_rows


def swap(rows: list[dict], index: int, focus: str, level: int, weight: float, seed: int = 0) -> list[dict]:
    """Replaces one move with a similar one (same part of the workout, same focus) that isn't already in it."""
    old = rows[index]
    used = {r["move"] for r in rows}
    if old["part"] == "Main":
        tags = exercise.TAGS[old["move"]][0] & FOCUSES[focus][1] or FOCUSES[focus][1]
        options = [n for n in _pool(focus, level, used) if exercise.TAGS[n][0] & tags]
    else:
        tag = "warmup" if old["part"] == "Warm-up" else "cooldown"
        options = [n for n, (t, _) in exercise.TAGS.items() if tag in t and n not in used]
    if not options:
        return rows
    name = random.Random(f"{old['move']}-{seed}").choice(sorted(options))
    if old["part"] == "Main":
        sets, amount = _dose(name, level, focus == "gentle")
        new = _row(name, sets, amount, "Main", weight, 15 if focus == "gentle" else REST_BETWEEN_SETS)
    else:
        unit = exercise.MOVE[name][3]
        new = _row(name, 1, 1 if unit == "min" else 45, old["part"], weight, 0)
    return rows[:index] + [new] + rows[index + 1:]


def minutes_for(left_kcal: int, focus: str, level: int, weight: float, gentle_day: bool) -> int:
    """How long today's workout should be to meet the quiet goal, rounded to a friendly length."""
    sample = build(focus, level, 20, weight)
    per_min = sum(r["kcal"] for r in sample) / max(1, sum(r["minutes"] for r in sample))
    need = left_kcal / per_min if per_min else 15
    choices = [10, 15, 20] if gentle_day or focus == "gentle" else TIME_CHOICES
    return min(choices, key=lambda m: abs(m - need)) if left_kcal > 0 else 10


def log(day: str, rows: list[dict], indexes: list[int], focus: str) -> int:
    """Saves the moves you did. Returns calories (shown only in 'See the numbers' and My log)."""
    total = 0
    for i in indexes:
        r = rows[i]
        storage.add_exercise(day, {"name": r["move"], "emoji": r["emoji"], "minutes": round(r["minutes"], 1),
                                   "kcal": r["kcal"], "detail": r["text"], "focus": focus,
                                   "source": f"Tulsi's workout · {FOCUSES[focus][0]}"})
        total += r["kcal"]
    return total
