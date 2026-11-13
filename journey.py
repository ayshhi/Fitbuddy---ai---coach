"""
journey.py - looks at all of the user's data together and works out:
  - one combined row per day (Samsung + check-ins + weights + water)
  - progress towards the goal weight
  - how much Tulsi has grown (she never shrinks)
  - where the user is in her menstrual cycle
  - which badges have been earned
"""

from datetime import date, timedelta
from statistics import mean, pstdev

import storage

# ---------------- All data, one row per day ----------------

def all_days() -> dict:
    """Priority when two sources disagree: check-ins > typed-in weights > Samsung Health."""
    rows = {d: dict(v) for d, v in storage.load_samsung().items()}
    for d, kg in storage.load_weights().items():
        rows.setdefault(d, {})["weight_kg"] = kg
    for d, c in storage.load_checkins().items():
        r = rows.setdefault(d, {})
        r["checked_in"] = 1
        for key in ("steps", "distance_km", "sleep_hours", "weight_kg", "calories"):
            if c.get(key):
                r[key] = c[key]
        if c.get("exercise_minutes"):
            r["workout_min"] = max(float(r.get("workout_min", 0)), float(c["exercise_minutes"]))
    for d, glasses in storage.load_water().items():
        if glasses:
            rows.setdefault(d, {})["water"] = glasses
    return rows


def weights(rows: dict) -> list[tuple[str, float]]:
    return [(d, float(r["weight_kg"])) for d, r in sorted(rows.items()) if r.get("weight_kg")]


# ---------------- Goal progress ----------------

def goal_progress(profile: dict, rows: dict) -> dict:
    w = weights(rows)
    start = float(profile.get("start_weight_kg") or (w[0][1] if w else 0) or 0)
    current = float(w[-1][1] if w else profile.get("current_weight_kg") or 0)
    goal = float(profile.get("goal_weight_kg") or 0)
    pct = None
    if start and current and goal and start != goal:
        pct = max(0.0, min(100.0, (start - current) / (start - goal) * 100))
    return {"start": start, "current": current, "goal": goal, "pct": pct,
            "lost": round(start - current, 1) if start and current else 0}


# ---------------- Tulsi's growth ----------------

STAGES = [
    (0,   "Seed",         "🌰", "Tulsi is a tiny seed, tucked into the soil, ready to grow with you."),
    (10,  "Sprout",       "🌱", "Tulsi has sprouted! Every check-in helps her grow."),
    (30,  "Young plant",  "🌿", "Tulsi is growing taller, just like your confidence."),
    (55,  "Leafy plant",  "🪴", "Look at all those leaves! You've come so far."),
    (80,  "Bud",          "🌷", "A bud has appeared! Your goal is so close."),
    (100, "Full bloom",   "🌸", "Tulsi is in full bloom. You reached your goal! 💜"),
]


def consistency_points(rows: dict) -> int:
    """Effort counts too, not just the scale."""
    pts = 0
    for r in rows.values():
        pts += 2 if r.get("checked_in") else 0
        pts += 1 if float(r.get("workout_min", 0) or 0) >= 15 else 0
        pts += 1 if float(r.get("sleep_hours", 0) or 0) >= 7 else 0
        pts += min(int(r.get("water", 0) or 0), 8) * 0.25  # every glass you water Tulsi with counts
    pts += storage.count_meals() + 2 * len(storage.load_wins())
    return pts


def growth(profile: dict, rows: dict | None = None) -> dict:
    rows = rows if rows is not None else all_days()
    goal = goal_progress(profile, rows)
    effort_bonus = min(25.0, consistency_points(rows) / 8)  # up to 25% growth from effort alone
    value = (goal["pct"] or 0) + effort_bonus
    value = 100.0 if (goal["pct"] or 0) >= 100 else min(value, 95.0)  # only the goal makes her bloom

    best = max(value, storage.load_best_growth())  # Tulsi never shrinks
    if best > storage.load_best_growth():
        storage.save_best_growth(best)

    index = max(i for i, s in enumerate(STAGES) if best >= s[0])
    nxt = STAGES[index + 1] if index + 1 < len(STAGES) else None
    return {"value": round(best, 1), "stage": index, "name": STAGES[index][1], "emoji": STAGES[index][2],
            "message": STAGES[index][3], "next": nxt[1] if nxt else None,
            "to_next": round(nxt[0] - best, 1) if nxt else 0, "goal": goal}


# ---------------- Menstrual cycle ----------------

PHASES = {
    "Period": ("🩸", "Rest is productive. Gentle walks, stretching, warm meals and iron-rich foods "
                     "(greens, dates, ragi, eggs). Low energy is normal."),
    "Follicular": ("🌱", "Energy usually rises. A great time to try strength workouts and new healthy recipes."),
    "Ovulation": ("✨", "Often your strongest days. Go for a longer walk or a more energetic workout if you feel good."),
    "Luteal": ("🌙", "Cravings and tiredness can increase before your period. Be kind to yourself, keep "
                     "protein and fibre high, add magnesium-rich foods (nuts, seeds, dark chocolate), "
                     "and choose calmer workouts."),
    "Late": ("💜", "Your period may be late, which is common with PCOS. Log it when it arrives, and "
                   "talk to your doctor if your cycle changes a lot."),
}


def cycle_info(today: date | None = None) -> dict | None:
    periods = [date.fromisoformat(d) for d in storage.load_periods()]
    today = today or date.today()
    periods = [p for p in periods if p <= today]
    if not periods:
        return None
    gaps = [(b - a).days for a, b in zip(periods, periods[1:]) if 15 <= (b - a).days <= 90]
    length = round(mean(gaps)) if gaps else 28
    irregular = bool(gaps) and (pstdev(gaps) > 7 or max(gaps) > 35) if len(gaps) >= 2 else False
    day = (today - periods[-1]).days + 1
    ovulation = max(length - 14, 10)
    if day <= 5:
        phase = "Period"
    elif day < ovulation - 1:
        phase = "Follicular"
    elif day <= ovulation + 1:
        phase = "Ovulation"
    elif day <= length + 5:
        phase = "Luteal"
    else:
        phase = "Late"
    emoji, tip = PHASES[phase]
    next_period = periods[-1] + timedelta(days=length)
    return {"day": day, "length": length, "phase": phase, "emoji": emoji, "tip": tip,
            "irregular": irregular, "next_period": next_period.isoformat(), "logged": len(periods)}


# ---------------- Badges ----------------

def _streak(days: set[str], today: date) -> int:
    """Longest run of consecutive days."""
    best = run = 0
    for i in range(400, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        run = run + 1 if d in days else 0
        best = max(best, run)
    return best


def badges(profile: dict, rows: dict | None = None) -> list[dict]:
    rows = rows if rows is not None else all_days()
    today = date.today()
    checkins = {d for d, r in rows.items() if r.get("checked_in")}
    walks = sum(float(r.get("workouts", 0) or 0) for r in rows.values())
    walk_km = sum(float(r.get("workout_km", 0) or 0) for r in rows.values())
    long_walk = any(float(r.get("workout_km", 0) or 0) >= 5 for r in rows.values())
    good_sleep = {d for d, r in rows.items() if float(r.get("sleep_hours", 0) or 0) >= 7}
    water_days = sum(1 for r in rows.values() if int(r.get("water", 0) or 0) >= 8)
    meals = storage.count_meals()
    wins = len(storage.load_wins())
    lost = goal_progress(profile, rows)["lost"]
    goal_pct = goal_progress(profile, rows)["pct"] or 0

    def b(emoji, name, desc, earned):
        return {"emoji": emoji, "name": name, "desc": desc, "earned": bool(earned)}

    return [
        b("👋", "Hello Tulsi", "Your first check-in", checkins),
        b("🔥", "3-day streak", "Check in 3 days in a row", _streak(checkins, today) >= 3),
        b("🗓️", "Week warrior", "Check in 7 days in a row", _streak(checkins, today) >= 7),
        b("📸", "Food explorer", "Scan your first meal", meals >= 1),
        b("🍽️", "Mindful eater", "Scan 10 meals", meals >= 10),
        b("🚶‍♀️", "First 5K", "Walk 5 km in one day", long_walk),
        b("👟", "10 walks", "Complete 10 walks", walks >= 10),
        b("🏃‍♀️", "100 walks", "Complete 100 walks", walks >= 100),
        b("🗺️", "100 km club", "Walk 100 km in total", walk_km >= 100),
        b("😴", "Sleep queen", "7 nights with 7+ hours of sleep", len(good_sleep) >= 7),
        b("💧", "Hydration hero", "Drink 8 glasses in a day", water_days >= 1),
        b("🌊", "Water week", "8 glasses on 7 different days", water_days >= 7),
        b("💜", "Not just a number", "Log your first non-scale win", wins >= 1),
        b("🎉", "First kilo", "Lose your first 1 kg", lost >= 1),
        b("⭐", "5 kg down", "Lose 5 kg", lost >= 5),
        b("🌟", "10 kg down", "Lose 10 kg", lost >= 10),
        b("🏆", "15 kg down", "Lose 15 kg", lost >= 15),
        b("🌸", "Full bloom", "Reach your goal weight", goal_pct >= 100),
    ]


# ---------------- PCOS symptoms ----------------

SYMPTOMS = {"acne": "Acne", "hair_fall": "Hair fall", "bloating": "Bloating", "cramps": "Cramps",
            "cravings": "Cravings", "fatigue": "Fatigue", "low_mood": "Low mood"}
LEVELS = ["None", "Mild", "Moderate", "Strong"]


def symptom_days() -> dict:
    """{date: {symptom: 0-3}} from check-ins."""
    return {d: c["symptoms"] for d, c in storage.load_checkins().items() if c.get("symptoms")}


def symptom_insights(min_days: int = 3) -> list[str]:
    """Simple, honest patterns: compares average symptom levels between two groups of days,
    and only reports a difference when both groups have enough days."""
    days = symptom_days()
    if len(days) < min_days * 2:
        return []
    checkins = storage.load_checkins()
    rows = all_days()
    groups = {
        "after low sleep (under 6.5 h)": lambda d: float(rows.get(d, {}).get("sleep_hours", 0) or 0) and float(rows[d]["sleep_hours"]) < 6.5,
        "on high-stress days (4-5)": lambda d: int(checkins.get(d, {}).get("stress", 0) or 0) >= 4,
        "in the week before your period": lambda d: (cycle_info(date.fromisoformat(d)) or {}).get("phase") == "Luteal",
        "during your period": lambda d: (cycle_info(date.fromisoformat(d)) or {}).get("phase") == "Period",
    }
    found = []
    for label, test in groups.items():
        inside = [d for d in days if test(d)]
        outside = [d for d in days if not test(d)]
        if len(inside) < min_days or len(outside) < min_days:
            continue
        for key, name in SYMPTOMS.items():
            a = mean(days[d].get(key, 0) for d in inside)
            b = mean(days[d].get(key, 0) for d in outside)
            if a - b >= 0.7:
                found.append(f"{name} tends to be worse {label} ({LEVELS[round(a)].lower()} vs {LEVELS[round(b)].lower()}).")
    return found


def daily_km(rows: dict) -> dict:
    """km walked per day: the larger of the day's total distance and its recorded walks."""
    return {d: max(float(r.get("distance_km", 0) or 0), float(r.get("workout_km", 0) or 0)) for d, r in rows.items()}
