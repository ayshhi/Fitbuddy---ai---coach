"""
exercise.py - specific moves, ready-made workouts, logging, and estimating calories burned.

Calories are estimated with METs ("metabolic equivalents"), the standard way fitness research rates how hard
an activity is. 1 MET is roughly sitting still; a brisk walk is about 4.3 METs.
    calories burned  ≈  MET  x  body weight (kg)  x  hours
These are estimates (real burn depends on fitness, age and effort), so the app always says "about".
If Samsung Health recorded a workout, its own calorie number is used for that workout.
"""

from datetime import date, timedelta

import journey
import storage

# (name, emoji, MET) - values based on the Compendium of Physical Activities
EXERCISES = [
    ("Easy walk", "🚶‍♀️", 3.0), ("Brisk walk", "🚶‍♀️", 4.3), ("Jogging", "🏃‍♀️", 7.0), ("Hiking", "🥾", 6.0),
    ("Gentle yoga", "🧘‍♀️", 2.5), ("Power yoga", "🧘‍♀️", 4.0), ("Pilates", "🤸‍♀️", 3.0), ("Stretching", "🤸‍♀️", 2.3),
    ("Dance / Zumba", "💃", 6.0), ("Bodyweight strength (squats, lunges)", "🏋️‍♀️", 3.8), ("HIIT workout", "🔥", 8.0),
    ("Skipping rope", "🪢", 8.8), ("Stair climbing", "🪜", 4.0), ("Cycling (easy)", "🚴‍♀️", 4.0),
    ("Cycling (moderate)", "🚴‍♀️", 6.8), ("Swimming (leisurely)", "🏊‍♀️", 6.0), ("Badminton", "🏸", 5.5),
    ("Housework / cleaning", "🧹", 3.3), ("Gardening", "🌱", 3.8),
]
# Specific moves: (name, emoji, MET, measured in "reps" / "sec" / "min", seconds per rep, how to do it)
MOVES = [
    ("Plank", "🧱", 3.8, "sec", 0, "Forearms on the floor, body straight from head to heels, tummy tight."),
    ("Squats", "🏋️‍♀️", 5.0, "reps", 3, "Feet hip-width apart, sit back as if onto a chair, chest up, knees over toes."),
    ("Lunges", "🦵", 4.0, "reps", 3, "Step forward, bend both knees to 90°, push back up. Count both legs."),
    ("Side lunges", "🦵", 4.0, "reps", 3, "Step wide to one side, bend that knee, keep the other leg straight."),
    ("Squat jumps", "⚡", 8.0, "reps", 2.5, "Squat down, jump up explosively, land softly with bent knees."),
    ("Mountain climbers", "⛰️", 8.0, "sec", 0, "From a high plank, drive your knees to your chest one after the other, fast."),
    ("Jumping jacks", "⭐", 8.0, "sec", 0, "Jump feet out while raising arms overhead, then back together."),
    ("Skipping rope", "🪢", 8.8, "min", 0, "Small jumps on the balls of your feet, wrists turning the rope."),
    ("High knees", "🏃‍♀️", 8.0, "sec", 0, "Run on the spot, bringing your knees up to hip height."),
    ("Butt kicks", "🦶", 7.0, "sec", 0, "Jog on the spot, kicking your heels up towards your bottom."),
    ("Burpees", "🔥", 8.0, "reps", 4, "Squat, hands down, jump back to plank, jump feet in, jump up."),
    ("Push-ups (on knees)", "💪", 3.8, "reps", 2.5, "Hands under shoulders, knees down, lower your chest and push back up."),
    ("Glute bridges", "🍑", 3.5, "reps", 3, "Lie on your back, knees bent, lift your hips and squeeze your glutes."),
    ("Wall sit", "🧱", 4.0, "sec", 0, "Back against a wall, slide down until your knees are at 90° and hold."),
    ("Crunches", "🌀", 3.8, "reps", 2, "Lie on your back, knees bent, lift your shoulders using your tummy."),
    ("Bicycle crunches", "🚲", 4.0, "reps", 1.5, "Elbow to opposite knee, alternating like pedalling. Count both sides."),
    ("Leg raises", "🦵", 3.5, "reps", 3, "Lie flat, lift both straight legs up, lower slowly without touching the floor."),
    ("Superman", "🦸‍♀️", 3.0, "reps", 3, "Lie face down, lift arms and legs together, hold a second, lower."),
    ("March in place", "🚶‍♀️", 3.5, "min", 0, "March on the spot, swinging your arms. A great warm-up."),
    ("Arm circles", "🙆‍♀️", 2.5, "sec", 0, "Arms out to the sides, make small then big circles."),
    ("Cat-cow stretch", "🐈", 2.3, "reps", 5, "On hands and knees, round your back up, then let it dip down, slowly."),
    ("Child's pose", "🧘‍♀️", 2.0, "sec", 0, "Kneel, sit back on your heels, stretch your arms forward and breathe."),
    ("Spot jogging", "🏃‍♀️", 7.0, "min", 0, "Light jog on the spot."),
]
MOVE = {m[0]: m for m in MOVES}

# Ready-made workouts: (name, minutes including short rests, best for, [(move, sets, amount per set)])
ROUTINES = {
    "🔥 15-min fat-burn warm-up": (15, "Getting your heart rate up", [
        ("Jumping jacks", 2, 45), ("High knees", 2, 30), ("Squat jumps", 3, 10),
        ("Mountain climbers", 3, 30), ("Skipping rope", 1, 3), ("Butt kicks", 1, 45)]),
    "🦵 Lower-body strength": (20, "Legs and glutes", [
        ("Squats", 3, 15), ("Lunges", 3, 20), ("Side lunges", 2, 16), ("Glute bridges", 3, 15), ("Wall sit", 3, 30)]),
    "🧱 Core & plank": (12, "A strong tummy and back", [
        ("Plank", 3, 60), ("Bicycle crunches", 3, 20), ("Leg raises", 3, 12), ("Superman", 3, 10), ("Crunches", 2, 15)]),
    "⚡ HIIT blast": (16, "Burning the most in the least time", [
        ("Burpees", 4, 8), ("Squat jumps", 4, 12), ("Mountain climbers", 4, 40), ("High knees", 4, 40)]),
    "💪 Full-body beginner": (18, "Starting out, or getting back into it", [
        ("March in place", 1, 2), ("Squats", 3, 12), ("Push-ups (on knees)", 3, 8), ("Glute bridges", 3, 12),
        ("Plank", 3, 30), ("Jumping jacks", 2, 30)]),
    "🌸 Period-friendly gentle": (15, "Period days, low energy or high stress", [
        ("March in place", 1, 3), ("Cat-cow stretch", 2, 10), ("Child's pose", 3, 45), ("Glute bridges", 2, 10),
        ("Arm circles", 2, 30), ("March in place", 1, 5)]),
}


def move_minutes(name: str, sets: int, amount: float) -> float:
    """Active minutes for a move: reps x seconds per rep, or seconds, or minutes, times sets."""
    _, _, _, unit, per_rep, _ = MOVE[name]
    seconds = amount * per_rep if unit == "reps" else amount if unit == "sec" else amount * 60
    return sets * seconds / 60


def amount_text(name: str, sets: int, amount: float) -> str:
    unit = MOVE[name][3]
    if unit == "reps":
        each = " (both legs)" if name in ("Lunges", "Side lunges") else ""
        return f"{sets} × {amount:g} reps{each}" if sets > 1 else f"{amount:g} reps{each}"
    if unit == "sec":
        shown = f"{amount / 60:g} min" if amount >= 60 and amount % 60 == 0 else f"{amount:g} sec"
        return f"{sets} × {shown}" if sets > 1 else shown
    return f"{sets} × {amount:g} min" if sets > 1 else f"{amount:g} min"


def move_kcal(name: str, sets: int, amount: float, weight_kg: float) -> int:
    return kcal(MOVE[name][2], weight_kg, move_minutes(name, sets, amount))


def add_move(day: str, name: str, sets: int, amount: float, profile: dict) -> int:
    emoji = MOVE[name][1]
    minutes = move_minutes(name, sets, amount)
    burned = move_kcal(name, sets, amount, body_weight(profile))
    storage.add_exercise(day, {"name": name, "emoji": emoji, "minutes": round(minutes, 1), "kcal": burned,
                               "detail": amount_text(name, sets, amount), "source": "you"})
    return burned


REST_MET = 3.0  # between sets you're breathing hard and moving around, roughly like walking slowly


def routine_breakdown(routine: str, weight_kg: float) -> list[dict]:
    """Each move in a workout with its time and calories, including its share of the rest between sets."""
    total_minutes, _, moves = ROUTINES[routine]
    active = [move_minutes(m, s, a) for m, s, a in moves]
    rest_total = max(0.0, total_minutes - sum(active))
    out = []
    for (m, s, a), act in zip(moves, active):
        rest = rest_total * act / sum(active)
        out.append({"move": m, "sets": s, "amount": a, "emoji": MOVE[m][1], "tip": MOVE[m][5],
                    "text": amount_text(m, s, a), "minutes": act + rest,
                    "kcal": round(move_kcal(m, s, a, weight_kg) + kcal(REST_MET, weight_kg, rest))})
    return out


def log_routine_moves(day: str, routine: str, indexes: list[int], profile: dict) -> int:
    """Logs the moves you ticked from a workout. Returns calories burned."""
    total = 0
    for i, row in enumerate(routine_breakdown(routine, body_weight(profile))):
        if i in indexes:
            storage.add_exercise(day, {"name": row["move"], "emoji": row["emoji"], "minutes": round(row["minutes"], 1),
                                       "kcal": row["kcal"], "detail": row["text"], "source": routine})
            total += row["kcal"]
    return total


def suggested_routine() -> tuple[str, str]:
    """Which ready-made workout fits today, and why."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    checkins = storage.load_checkins()
    c = checkins.get(today) or checkins.get(yesterday) or {}
    rows = journey.all_days()
    sleep = float((rows.get(today) or rows.get(yesterday) or {}).get("sleep_hours") or 7)
    stress, energy = int(c.get("stress") or 2), int(c.get("energy") or 3)
    phase = (journey.cycle_info() or {}).get("phase")
    if phase == "Period" or sleep < 6 or stress >= 4 or energy <= 2:
        return "🌸 Period-friendly gentle", "Your body needs gentle movement today (period, low sleep, high stress or low energy)."
    if phase == "Luteal":
        return "🧱 Core & plank", "In the week before your period, steady strength work feels better than jumping."
    if phase in ("Follicular", "Ovulation") and energy >= 4:
        return "⚡ HIIT blast", "Your energy is high and this is your strongest time of the cycle. Go for it!"
    if energy >= 3:
        return "🔥 15-min fat-burn warm-up", "A good energy day: get your heart rate up, then add a strength workout if you like."
    return "💪 Full-body beginner", "A balanced, steady workout for today."


BY_NAME = {name: (emoji, met) for name, emoji, met in EXERCISES}
DEFAULT_GOAL = 250  # kcal a day from exercise; you can change it on the page


def body_weight(profile: dict) -> float:
    """Latest known weight, used in the calorie formula."""
    w = journey.weights(journey.all_days())
    return float(w[-1][1] if w else profile.get("current_weight_kg") or 60)


def kcal(met: float, weight_kg: float, minutes: float) -> int:
    return round(met * weight_kg * minutes / 60)


def guess_exercise(text: str) -> str:
    """Matches free text like 'walked', 'zumba class' or 'yoga' to an exercise in the list."""
    t = (text or "").lower()
    rules = [("skip", "Skipping rope"), ("jump rope", "Skipping rope"), ("zumba", "Dance / Zumba"), ("danc", "Dance / Zumba"),
             ("jog", "Jogging"), ("run", "Jogging"), ("hike", "Hiking"), ("power yoga", "Power yoga"), ("yoga", "Gentle yoga"),
             ("pilates", "Pilates"), ("stretch", "Stretching"), ("hiit", "HIIT workout"), ("squat", "Bodyweight strength (squats, lunges)"),
             ("strength", "Bodyweight strength (squats, lunges)"), ("stair", "Stair climbing"), ("cycl", "Cycling (easy)"),
             ("bike", "Cycling (easy)"), ("swim", "Swimming (leisurely)"), ("badminton", "Badminton"), ("clean", "Housework / cleaning"),
             ("garden", "Gardening"), ("brisk", "Brisk walk"), ("walk", "Easy walk")]
    for key, name in rules:
        if key in t:
            return name
    return "Easy walk"


def add(day: str, name: str, minutes: int, profile: dict, source: str = "you") -> int:
    emoji, met = BY_NAME[name]
    burned = kcal(met, body_weight(profile), minutes)
    storage.add_exercise(day, {"name": name, "emoji": emoji, "minutes": int(minutes), "kcal": burned, "source": source})
    return burned


def day_entries(day: str) -> list[dict]:
    """Everything you did that day: what you logged, plus walks Samsung Health recorded."""
    entries = list(storage.load_exercises().get(day, []))
    sh = storage.load_samsung().get(day, {})
    if sh.get("workout_min"):
        entries.append({"name": "Walks (Samsung Health)", "emoji": "📱", "minutes": int(float(sh["workout_min"])),
                        "kcal": int(float(sh.get("workout_kcal") or 0)), "source": "samsung"})
    return entries


def day_total(day: str) -> dict:
    entries = day_entries(day)
    return {"minutes": sum(e["minutes"] for e in entries), "kcal": sum(e["kcal"] for e in entries)}


def week_totals(today: date | None = None) -> list[tuple[str, int, int]]:
    today = today or date.today()
    out = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        t = day_total(d)
        out.append((d, t["minutes"], t["kcal"]))
    return out


def suggestions(profile: dict) -> tuple[str, list[tuple[str, int]]]:
    """Today's suggested exercises, adjusted to cycle phase, sleep, stress and energy. (reason, [(exercise, minutes)])"""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    checkins = storage.load_checkins()
    c = checkins.get(today) or checkins.get(yesterday) or {}
    rows = journey.all_days()
    sleep = float((rows.get(today) or rows.get(yesterday) or {}).get("sleep_hours") or 7)
    stress, energy = int(c.get("stress") or 2), int(c.get("energy") or 3)
    phase = (journey.cycle_info() or {}).get("phase")
    if phase == "Period" or sleep < 6 or stress >= 4 or energy <= 2:
        why = ("You're on your period, so" if phase == "Period" else
               "You slept less than 6 hours, so" if sleep < 6 else
               "Stress is high today, so" if stress >= 4 else "Your energy is low, so")
        return f"{why} today is for gentle movement that lowers cortisol, not pushing hard.", \
               [("Gentle yoga", 20), ("Easy walk", 20), ("Stretching", 10)]
    if phase == "Luteal":
        return "You're in the week before your period: steady, moderate movement feels best now.", \
               [("Brisk walk", 25), ("Pilates", 20), ("Stretching", 10)]
    if phase in ("Follicular", "Ovulation") and energy >= 3:
        return "Your energy is usually at its best in this part of your cycle, so it's a great day to build strength.", \
               [("Brisk walk", 30), ("Bodyweight strength (squats, lunges)", 20), ("Dance / Zumba", 15)]
    return "A balanced day: a walk, a little strength and a stretch.", \
           [("Brisk walk", 25), ("Bodyweight strength (squats, lunges)", 15), ("Stretching", 10)]


# ---------------------------------------------------------------- the sun

def sun_svg(progress: float) -> str:
    """A sun that grows brighter as you burn more. progress: 0 = nothing yet, 1 = daily goal reached."""
    p = max(0.0, min(1.0, progress))

    def mix(a, b):  # blend two colours by p
        return "#" + "".join(f"{int(int(a[i:i + 2], 16) + (int(b[i:i + 2], 16) - int(a[i:i + 2], 16)) * p):02X}" for i in (1, 3, 5))

    core, edge = mix("#F3E7B5", "#FFD23F"), mix("#E9D9A6", "#FF9F1C")
    radius = 46 + 22 * p
    ray_len = 8 + 46 * p
    rays = "".join(
        f'<rect x="146" y="{150 - radius - 10 - ray_len}" width="8" height="{ray_len}" rx="4" fill="{edge}" '
        f'opacity="{0.25 + 0.75 * p:.2f}" transform="rotate({a} 150 150)"/>' for a in range(0, 360, 30))
    clouds = ""
    if p < 0.6:  # clouds drift away as you get going
        o = 1 - p / 0.6
        clouds = (f'<g opacity="{o:.2f}" fill="#FFFFFF"><ellipse cx="{95 - 40 * p}" cy="190" rx="52" ry="26"/>'
                  f'<ellipse cx="{130 - 40 * p}" cy="176" rx="38" ry="28"/><ellipse cx="{215 + 40 * p}" cy="120" rx="46" ry="22"/>'
                  f'<ellipse cx="{188 + 40 * p}" cy="108" rx="30" ry="22"/></g>')
    if p >= 1:
        face = ('<path d="M128 142 Q136 132 144 142" stroke="#7A4A00" stroke-width="5" fill="none" stroke-linecap="round"/>'
                '<path d="M156 142 Q164 132 172 142" stroke="#7A4A00" stroke-width="5" fill="none" stroke-linecap="round"/>'
                '<path d="M130 160 Q150 182 170 160 Z" fill="#7A4A00"/>')
    elif p > 0.3:
        face = ('<circle cx="136" cy="142" r="5" fill="#7A4A00"/><circle cx="164" cy="142" r="5" fill="#7A4A00"/>'
                '<path d="M136 160 Q150 172 164 160" stroke="#7A4A00" stroke-width="5" fill="none" stroke-linecap="round"/>')
    else:  # sleepy until you start moving
        face = ('<path d="M130 144 Q136 149 142 144" stroke="#9A8550" stroke-width="4" fill="none" stroke-linecap="round"/>'
                '<path d="M158 144 Q164 149 170 144" stroke="#9A8550" stroke-width="4" fill="none" stroke-linecap="round"/>'
                '<path d="M142 162 Q150 166 158 162" stroke="#9A8550" stroke-width="4" fill="none" stroke-linecap="round"/>')
    sparkles = "".join(f'<text x="{x}" y="{y}" font-size="20">✨</text>' for x, y in [(40, 60), (240, 70), (250, 240), (30, 230)]) if p >= 1 else ""
    uid = f"{int(p * 1000)}"  # unique gradient names, so two suns on one page never share colours
    return (f'<svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">'
            f'<defs><radialGradient id="glow{uid}"><stop offset="0" stop-color="#FFE27A" stop-opacity="{0.15 + 0.6 * p:.2f}"/>'
            f'<stop offset="1" stop-color="#FFE27A" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="core{uid}" cx=".4" cy=".35"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".6"/>'
            f'<stop offset=".3" stop-color="{core}"/><stop offset="1" stop-color="{edge}"/></radialGradient></defs>'
            f'<circle cx="150" cy="150" r="{radius + 70 * p + 20}" fill="url(#glow{uid})"/>{rays}'
            f'<circle cx="150" cy="150" r="{radius}" fill="url(#core{uid})"/>'
            f'<ellipse cx="128" cy="156" rx="9" ry="5" fill="#FF8FA3" opacity="{0.2 + 0.6 * p:.2f}"/>'
            f'<ellipse cx="172" cy="156" rx="9" ry="5" fill="#FF8FA3" opacity="{0.2 + 0.6 * p:.2f}"/>'
            f'{face}{clouds}{sparkles}</svg>')
