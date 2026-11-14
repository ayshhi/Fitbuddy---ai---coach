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
    for d, entries in storage.load_exercises().items():  # exercise you logged on the Exercise page
        if entries:
            r = rows.setdefault(d, {})
            r["workout_min"] = max(float(r.get("workout_min", 0) or 0), float(sum(e["minutes"] for e in entries)))
            r["exercise_kcal"] = sum(e["kcal"] for e in entries)
    return rows


def weights(rows: dict) -> list[tuple[str, float]]:
    return [(d, float(r["weight_kg"])) for d, r in sorted(rows.items()) if r.get("weight_kg")]


# ---------------- Goal progress ----------------

def goal_progress(profile: dict, rows: dict) -> dict:
    """Progress towards the current goal. After you reach a goal and set a new one, the new journey starts
    from the weight you were at when you reached the last one."""
    w = weights(rows)
    start = float(profile.get("start_weight_kg") or (w[0][1] if w else 0) or 0)
    current = float(w[-1][1] if w else profile.get("current_weight_kg") or 0)
    goal = float(profile.get("goal_weight_kg") or 0)
    flowers = storage.load_flowers()
    journey_no = 1
    if flowers and goal and abs(float(flowers[-1]["goal"]) - goal) > 0.05:
        start = float(flowers[-1].get("weight") or flowers[-1]["goal"])  # a new goal: a new journey
        journey_no = len(flowers) + 1
    elif flowers:
        journey_no = len(flowers)
    pct = None
    if start and current and goal and start != goal:
        pct = max(0.0, min(100.0, (start - current) / (start - goal) * 100))
    first_start = float(profile.get("start_weight_kg") or start or 0)
    return {"start": start, "current": current, "goal": goal, "pct": pct, "journey": journey_no,
            "lost": round(start - current, 1) if start and current else 0,
            "lost_total": round(first_start - current, 1) if first_start and current else 0}


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
    reached = (goal["pct"] or 0) >= 100
    new_flower = False
    flowers = storage.load_flowers()
    if reached and not any(abs(float(f["goal"]) - goal["goal"]) < 0.05 for f in flowers):
        storage.add_flower({"goal": goal["goal"], "start": goal["start"], "weight": goal["current"],
                            "date": date.today().isoformat()})
        flowers = storage.load_flowers()
        new_flower = True

    effort_bonus = min(25.0, consistency_points(rows) / 8)  # up to 25% growth from effort alone
    value = (goal["pct"] or 0) + effort_bonus
    value = 100.0 if reached else min(value, 95.0)  # only the goal makes her bloom

    # Tulsi never shrinks within a journey. A new goal starts a new journey, but her flowers stay,
    # and she never drops below a leafy plant once she has bloomed.
    if storage.load_best_for() != goal["goal"]:
        storage.save_best_for(goal["goal"])
        storage.save_best_growth(value)
    best = max(value, storage.load_best_growth())
    if best > storage.load_best_growth():
        storage.save_best_growth(best)

    index = max(i for i, s in enumerate(STAGES) if best >= s[0])
    if flowers:
        index = max(index, 3)
    nxt = STAGES[index + 1] if index + 1 < len(STAGES) else None
    old_flowers = len(flowers) - (1 if reached else 0)  # flowers from earlier goals, drawn on her leaves
    message = STAGES[index][3]
    if reached and len(flowers) > 1:
        message = f"Full bloom again! That's {len(flowers)} goals reached, and a flower for each one. 💜"
    elif reached:
        message += " Set a new goal in Health profile, and Tulsi will grow another flower when you reach it."
    elif flowers:
        message = (f"Tulsi keeps her {len(flowers)} flower{'s' if len(flowers) > 1 else ''} from the goals you've reached, "
                   "and she's growing a new one for your next goal.")
    return {"value": round(best, 1), "stage": index, "name": STAGES[index][1], "emoji": STAGES[index][2],
            "message": message, "next": nxt[1] if nxt else None,
            "to_next": round(nxt[0] - best, 1) if nxt else 0, "goal": goal,
            "flowers": len(flowers), "old_flowers": old_flowers, "new_flower": new_flower}


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
    """{date: {symptom: 0-3}} from the symptoms log (and older check-ins that included symptoms)."""
    days = {d: c["symptoms"] for d, c in storage.load_checkins().items() if c.get("symptoms")}
    for d, entry in storage.load_symptoms().items():
        levels = {k: int(v) for k, v in entry.items() if k in SYMPTOMS}
        if any(levels.values()) or d not in days:
            days[d] = levels
    return days


def _permutation_p(a: list[float], b: list[float], rounds: int = 2000) -> float:
    """How likely is a gap this big between group a and group b just by chance?
    Shuffles the days between the two groups many times and counts how often chance does as well."""
    import random
    rng = random.Random(42)  # fixed seed, so the same data always gives the same answer
    observed = mean(a) - mean(b)
    pooled, n = a + b, len(a)
    hits = 0
    for _ in range(rounds):
        rng.shuffle(pooled)
        if mean(pooled[:n]) - mean(pooled[n:]) >= observed:
            hits += 1
    return (hits + 1) / (rounds + 1)


def phase_on(day: str) -> str | None:
    info = cycle_info(date.fromisoformat(day))
    return info["phase"] if info else None


def symptom_patterns(min_days: int = 3) -> list[dict]:
    """Compares each symptom between two groups of days (e.g. low-sleep vs normal-sleep days).
    A pattern is only reported when both groups have enough days, the gap is meaningful (at least
    half a level), and a permutation test says it's unlikely to be chance."""
    days = symptom_days()
    if len(days) < min_days * 2:
        return []
    checkins = storage.load_checkins()
    rows = all_days()
    water = storage.load_water()

    def sleep(d):
        return float(rows.get(d, {}).get("sleep_hours", 0) or 0)

    factors = [
        ("after low sleep (under 6.5 h)", "on nights with 6.5 h or more", lambda d: 0 < sleep(d) < 6.5, lambda d: sleep(d) >= 6.5),
        ("on high-stress days (4-5)", "on calmer days (1-3)", lambda d: int(checkins.get(d, {}).get("stress", 0) or 0) >= 4,
         lambda d: 0 < int(checkins.get(d, {}).get("stress", 0) or 0) <= 3),
        ("in the week before your period", "at other times", lambda d: phase_on(d) == "Luteal",
         lambda d: phase_on(d) not in (None, "Luteal")),
        ("during your period", "at other times", lambda d: phase_on(d) == "Period", lambda d: phase_on(d) not in (None, "Period")),
        ("on days with under 6 glasses of water", "on days with 6+ glasses", lambda d: 0 < int(water.get(d, 0) or 0) < 6,
         lambda d: int(water.get(d, 0) or 0) >= 6),
    ]
    candidates, tests = [], 0
    for label, other, test_in, test_out in factors:
        inside = [d for d in days if test_in(d)]
        outside = [d for d in days if test_out(d)]
        if len(inside) < min_days or len(outside) < min_days:
            continue
        for key, name in SYMPTOMS.items():
            tests += 1
            a = [float(days[d].get(key, 0)) for d in inside]
            b = [float(days[d].get(key, 0)) for d in outside]
            if mean(a) - mean(b) < 0.5:  # too small to matter, even if real
                continue
            candidates.append((name, label, other, a, b, _permutation_p(a, b)))

    # We test many symptom x factor combinations, so some will look "significant" by luck.
    # Benjamini-Hochberg adjusts for that: q is the p-value corrected for the number of tests.
    candidates.sort(key=lambda c: c[5])
    qs, running = [0.0] * len(candidates), 1.0
    for i in range(len(candidates) - 1, -1, -1):
        running = min(running, candidates[i][5] * tests / (i + 1))
        qs[i] = running

    found = []
    for (name, label, other, a, b, p), q in zip(candidates, qs):
        if q > 0.1:
            continue
        strength = "Strong pattern" if q < 0.05 and min(len(a), len(b)) >= 5 else "Possible pattern"
        found.append({
            "symptom": name, "factor": label, "strength": strength, "q": round(q, 3),
            "text": f"{name} is worse {label}: on average {LEVELS[round(mean(a))].lower()} "
                    f"vs {LEVELS[round(mean(b))].lower()} {other}.",
            "evidence": f"Based on {len(a)} vs {len(b)} logged days. After checking {tests} combinations, "
                        f"the chance this is just luck is about {q:.0%}.",
        })
    return found


def symptom_insights(min_days: int = 3) -> list[str]:
    """Short sentences for Tulsi's context and the doctor report."""
    return [f"{p['strength']}: {p['text']}" for p in symptom_patterns(min_days)]


def symptoms_by_phase() -> dict:
    """{phase: {symptom: average level}} for days where the cycle phase is known."""
    days = symptom_days()
    out = {}
    for phase in ["Period", "Follicular", "Ovulation", "Luteal"]:
        ds = [d for d in days if phase_on(d) == phase]
        if ds:
            out[phase] = {k: mean(float(days[d].get(k, 0)) for d in ds) for k in SYMPTOMS} | {"_days": len(ds)}
    return out


# ---------------- Cravings ----------------

SWAPS = {
    "🍫 Something sweet": ["2 dates with a little peanut butter", "Banana with cinnamon", "2-3 squares of dark chocolate (70%+)",
                          "Curd with fruit and a drizzle of honey", "One small ragi laddu"],
    "🍟 Fried or salty": ["Roasted makhana with a pinch of salt", "Roasted chana", "Cucumber with chaat masala and lemon",
                         "A small handful of masala peanuts", "Sprouts chaat"],
    "🍚 Rice or carbs": ["A smaller portion of rice with extra dal and veg", "Millet upma or ragi dosa",
                         "Whole wheat roti with a protein curry", "Puttu with kadala curry (more kadala, less puttu)"],
    "🥤 A cold drink": ["Sambharam (spiced buttermilk)", "Lemon water with mint", "Tender coconut water",
                       "Sparkling water with lime and salt"],
    "😩 I'm just stressed or bored": ["A 5-minute walk outside", "Call or text a friend", "A cup of herbal or ginger tea",
                                      "Write down what's bothering you", "Stretch for 3 minutes"],
}
TRIGGERS = ["😣 Stressed", "🥱 Tired", "😐 Bored", "🩸 Period / PMS", "🍽️ Actually hungry", "📱 Saw it somewhere", "🤷 Not sure"]
OUTCOMES = {"mindful": "💜 Ate it mindfully", "swap": "🥗 Had a swap", "passed": "🌊 It passed"}


def craving_patterns() -> dict:
    """Counts cravings by time of day, trigger, and cycle phase."""
    from collections import Counter
    cr = storage.load_cravings()
    if not cr:
        return {}

    def slot(h):
        return "Morning" if 5 <= h < 12 else "Afternoon" if h < 17 else "Evening" if h < 21 else "Night"

    times = Counter(slot(int(c["when"][11:13])) for c in cr)
    triggers = Counter(c.get("trigger") or "🤷 Not sure" for c in cr)
    phases = Counter(phase_on(c["when"][:10]) or "Unknown" for c in cr)
    outcomes = Counter(c.get("outcome") for c in cr if c.get("outcome"))
    return {"total": len(cr), "times": times, "triggers": triggers, "phases": phases, "outcomes": outcomes}




def daily_km(rows: dict) -> dict:
    """km walked per day: the larger of the day's total distance and its recorded walks."""
    return {d: max(float(r.get("distance_km", 0) or 0), float(r.get("workout_km", 0) or 0)) for d, r in rows.items()}


# ---------------- Tulsi's plans: how much of them actually happens ----------------

def follow_through(days: int = 7, today: date | None = None) -> dict:
    """Share of plan items ticked off over the last `days` days (today included)."""
    today = today or date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    items = [i for d, p in storage.load_plans().items() if start <= d <= today.isoformat() for i in p["items"]]
    done = sum(1 for i in items if i.get("done"))
    return {"done": done, "total": len(items), "rate": done / len(items) if items else None}


# ---------------- A calmer view of weight ----------------

def weight_trend(rows: dict) -> list[tuple[str, float]]:
    """For each weigh-in, the average of all weigh-ins in the 7 days up to it.
    This smooths out daily ups and downs from water, salt and hormones."""
    w = weights(rows)
    out = []
    for d, _ in w:
        end = date.fromisoformat(d)
        window = [v for dd, v in w if end - timedelta(days=6) <= date.fromisoformat(dd) <= end]
        out.append((d, round(sum(window) / len(window), 2)))
    return out


def scale_reasons(rows: dict) -> dict | None:
    """If the latest weigh-in is higher than the one before, list likely, temporary reasons from the data."""
    w = weights(rows)
    if len(w) < 2 or w[-1][1] - w[-2][1] < 0.3:
        return None
    last_day = date.fromisoformat(w[-1][0])
    up = round(w[-1][1] - w[-2][1], 1)
    reasons = []

    phase = (cycle_info(last_day) or {}).get("phase")
    if phase in ("Luteal", "Period"):
        reasons.append(f"🌙 You're in your {phase.lower()} phase. Hormones often make the body hold extra water "
                       "around this time, sometimes a kilo or more, and it goes once your period settles.")

    def recent(key, n=3):
        vals = [float(rows.get((last_day - timedelta(days=i)).isoformat(), {}).get(key) or 0) for i in range(1, n + 1)]
        vals = [v for v in vals if v]
        return sum(vals) / len(vals) if vals else None

    sleep = recent("sleep_hours")
    if sleep and sleep < 6.5:
        reasons.append(f"😴 You averaged {sleep:.1f} h of sleep over the last few nights. Short sleep raises cortisol "
                       "and can make the body hold on to water.")
    stress = [int(storage.load_checkins().get((last_day - timedelta(days=i)).isoformat(), {}).get("stress") or 0) for i in range(0, 3)]
    stress = [s for s in stress if s]
    if stress and sum(stress) / len(stress) >= 4:
        reasons.append("😣 Your stress has been high lately. Stress hormones can cause temporary water retention.")
    cal_yday = float(rows.get((last_day - timedelta(days=1)).isoformat(), {}).get("calories") or 0)
    cal_week = [float(rows.get((last_day - timedelta(days=i)).isoformat(), {}).get("calories") or 0) for i in range(2, 9)]
    cal_week = [c for c in cal_week if c]
    if cal_yday and cal_week and cal_yday > 1.3 * (sum(cal_week) / len(cal_week)):
        reasons.append("🍛 Yesterday was a bigger food day. Extra food, salt and carbs hold water for a day or two. "
                       "That's not fat, and it passes.")
    workout = float(rows.get((last_day - timedelta(days=1)).isoformat(), {}).get("workout_min") or 0)
    if workout >= 45:
        reasons.append("💪 You had a longer workout yesterday. Muscles hold extra water while they recover.")
    reasons.append("⚖️ Day-to-day weight naturally moves around by up to a kilo from water, salt and digestion. "
                   "The 7-day trend is the number that matters.")
    trend = weight_trend(rows)
    week_ago = [v for d, v in trend if date.fromisoformat(d) <= last_day - timedelta(days=7)]
    return {"up_by": up, "reasons": reasons, "trend_now": round(trend[-1][1], 1),
            "trend_change": round(trend[-1][1] - week_ago[-1], 1) if week_ago else None}


# ---------- Specific craving swaps: you type what you want, you get swaps for exactly that ----------
# (keywords, pattern group, [(emoji, swap, why it works)], "if you still want it" tip)
CRAVING_LIBRARY = [
    (["chocolate", "dairy milk", "kitkat", "brownie", "nutella", "cocoa"], "🍫 Something sweet",
     [("🍫", "2 squares of 70% dark chocolate + 5 almonds", "Same chocolate hit, far less sugar, and the nuts keep you full"),
      ("🍌", "Banana slices dipped in 1 tsp cocoa + peanut butter", "Creamy and chocolatey with fibre and protein"),
      ("🥛", "Hot cocoa: milk + 1 tsp cocoa + a date blended", "Warm and comforting, sweetened by the date")],
     "Buy a small bar, not a big one. Put 2–3 pieces on a plate, put the rest away, and eat slowly."),
    (["ice cream", "icecream", "kulfi", "sundae", "gelato", "frozen"], "🍫 Something sweet",
     [("🍌", "'Nice cream': 1 frozen banana blended with cocoa or vanilla", "Tastes like soft-serve, no added sugar"),
      ("🥣", "Frozen thick curd with mango or berries", "Cold, creamy and full of protein"),
      ("🥥", "Tender coconut malai, chilled", "Naturally sweet and refreshing")],
     "Pick a single small cup instead of a tub, and sit down to enjoy it."),
    (["cake", "pastry", "muffin", "cupcake", "donut", "doughnut", "puffs", "bakery"], "🍫 Something sweet",
     [("🍎", "Baked apple with cinnamon and a spoon of curd", "Warm, sweet, dessert-like"),
      ("🥞", "Ragi or oats banana pancake (1 small)", "Cake-like with fibre that slows sugar spikes"),
      ("🍯", "2 dates stuffed with peanut butter", "Rich and sweet in two bites")],
     "Share a slice or have half, with tea, after a meal (not on an empty stomach)."),
    (["biscuit", "cookie", "marie", "good day", "oreo", "rusk"], "🍫 Something sweet",
     [("🥜", "A handful of roasted peanuts + 1 date", "Crunch and sweetness with protein"),
      ("🍪", "2 oats-date cookies (homemade)", "Same cookie feeling, slower sugar"),
      ("🌰", "Roasted makhana tossed with jaggery and ghee", "Crunchy and light")],
     "Take 2 biscuits out, close the packet, and have them with tea instead of eating from the packet."),
    (["sweet", "mithai", "laddu", "ladoo", "jalebi", "gulab", "halwa", "payasam", "kheer", "barfi", "unniyappam", "sugar", "dessert"],
     "🍫 Something sweet",
     [("🍯", "2 dates or 1 small ragi-nut laddu", "Traditional sweet taste, more fibre"),
      ("🥣", "Curd with fruit and a drizzle of honey", "Sweet plus protein"),
      ("🍠", "Steamed sweet potato with cardamom", "Naturally sweet and filling")],
     "Have one small piece after lunch, when your body handles sugar best, not late at night."),
    (["chips", "lays", "kurkure", "crisps", "nachos", "mixture", "namkeen", "banana chips"], "🍟 Fried or salty",
     [("🌰", "Roasted makhana with salt, pepper and a little ghee", "Same crunch and salt, a fraction of the oil"),
      ("🫘", "Roasted chana or masala peanuts (a small bowl)", "Crunchy and salty with protein"),
      ("🥒", "Cucumber and carrot sticks with chaat masala + lemon", "Tangy, salty, very crunchy")],
     "Pour a small bowl instead of eating from the packet."),
    (["fries", "french fries", "wedges"], "🍟 Fried or salty",
     [("🍠", "Air-fried or oven sweet potato wedges", "Crispy outside, soft inside, less oil"),
      ("🥔", "Pan-roasted baby potatoes with herbs (small bowl)", "Same potato comfort"),
      ("🌰", "Roasted makhana with peri-peri", "Crunchy and spicy")],
     "Get the small size and share it, with a protein like grilled chicken or paneer."),
    (["samosa", "pakoda", "pakora", "vada", "bajji", "bonda", "cutlet", "kachori", "pazham pori", "fried snack"],
     "🍟 Fried or salty",
     [("🫓", "Sprouts chaat with onion, tomato and lemon", "Spicy and tangy, full of protein"),
      ("🥟", "2 steamed idlis or a steamed momo with chutney", "Savoury snack without deep frying"),
      ("🍳", "Masala omelette or paneer bhurji (small)", "Hot, spicy and filling")],
     "Have one with your tea, not three, and skip the second round."),
    (["biryani", "fried rice", "pulao", "mandhi", "mandi"], "🍚 Rice or carbs",
     [("🍗", "Half a plate of biryani + a big bowl of raita and salad", "You still get biryani; protein and veg fill you up"),
      ("🥘", "Millet or brown-rice chicken / veg pulao at home", "Biryani spices with slower carbs"),
      ("🍳", "Egg or paneer 'biryani bowl' with more protein, less rice", "Same flavours, more filling")],
     "Start with salad and raita, then the biryani, and stop at one serving."),
    (["pizza"], "🍚 Rice or carbs",
     [("🫓", "Chapati or wheat-base pizza with paneer and lots of veg", "Same toppings, smaller base"),
      ("🍳", "Egg 'pizza' omelette with veg and a little cheese", "Cheesy, high protein"),
      ("🍅", "2 slices of thin-crust + a big salad", "You still have pizza, just fewer slices")],
     "Order thin crust, have 2 slices with salad, and save the rest."),
    (["burger", "sandwich", "shawarma", "wrap", "roll", "fried chicken", "kfc"], "🍟 Fried or salty",
     [("🌯", "Chapati wrap with grilled chicken or paneer and salad", "Same handheld comfort"),
      ("🍗", "Grilled chicken or tandoori instead of fried", "Smoky and filling, much less oil"),
      ("🥪", "Brown-bread sandwich with egg or paneer", "Quick and satisfying")],
     "Pick grilled over fried, skip the mayo or ask for less, and skip the side of fries."),
    (["maggi", "noodles", "pasta", "ramen", "chowmein"], "🍚 Rice or carbs",
     [("🍜", "Half a packet of noodles + lots of veg + an egg", "Same comfort bowl, more nutrition"),
      ("🥣", "Vegetable oats or millet upma", "Warm, savoury, quick"),
      ("🍝", "Whole-wheat pasta with tomato sauce and paneer", "Pasta night, more protein")],
     "Add an egg and a handful of veg, and have it in a bowl, not from the pan."),
    (["parotta", "porotta", "paratha", "naan", "bread", "puri", "poori"], "🍚 Rice or carbs",
     [("🫓", "2 chapatis or 1 wheat parotta with a protein curry", "Same meal, lighter bread"),
      ("🥚", "Appam or idiyappam with egg curry", "Kerala comfort, less oil"),
      ("🍲", "Kerala chicken / kadala curry with a small portion of puttu", "More curry, less carb")],
     "Have one parotta, not two, with plenty of curry and salad."),
    (["rice", "carb", "chor", "choru", "meals", "sadya"], "🍚 Rice or carbs",
     [("🍚", "Half cup matta rice + extra dal, thoran and curd", "A full Kerala plate, smaller rice"),
      ("🌾", "Millet (ragi/foxtail) with your curry", "Slower energy, steadier sugar"),
      ("🥗", "Rice with a big side of salad, eaten veg first", "Eating veg first softens the sugar spike")],
     "Fill half your plate with veg and dal first, then the rice."),
    (["coke", "cola", "pepsi", "soda", "soft drink", "sprite", "fanta", "juice", "milkshake", "bubble tea", "cold drink"],
     "🥤 A cold drink",
     [("🥛", "Sambharam (spiced buttermilk)", "Cold, tangy, good for digestion"),
      ("🍋", "Sparkling water with lime, mint and a pinch of salt", "Fizzy like soda, zero sugar"),
      ("🥥", "Tender coconut water", "Naturally sweet and hydrating")],
     "Pick the smallest can and drink it with a meal, not on its own."),
    (["tea", "chai", "coffee", "latte", "cappuccino"], "😩 I'm just stressed or bored",
     [("🍵", "Tea or coffee with half the sugar (or none)", "Same ritual, much less sugar"),
      ("🌿", "Ginger, tulsi or cinnamon tea", "Warm and calming, good for blood sugar"),
      ("🥛", "Turmeric milk without sugar", "Comforting before bed")],
     "Enjoy it, just skip the biscuits on the side, or have one."),
    (["chaat", "pani puri", "golgappa", "bhel", "sev puri", "pav bhaji", "vada pav"], "🍟 Fried or salty",
     [("🫘", "Sprouts or chana chaat with lots of onion, tomato and lemon", "Same chatpata taste, protein-packed"),
      ("🥗", "Bhel with puffed rice, roasted peanuts and veg (no sev)", "Light and tangy"),
      ("🌽", "Masala sweet corn cup", "Warm, spicy street-food feel")],
     "Have a small plate and skip the extra sev and sweet chutney."),
    (["popcorn"], "🍟 Fried or salty",
     [("🍿", "Home-popped popcorn with a little ghee and salt", "Whole grain, light"),
      ("🌰", "Roasted makhana", "Crunchy and airy"),
      ("🫘", "Roasted chana", "Crunch with protein")],
     "Home-made is fine; skip the caramel and butter versions."),
]


def specific_swaps(food: str):
    """Finds swaps for exactly what you typed. Returns (pattern group, swaps, tip), or None if not in the library."""
    text = food.lower()
    best = None
    for words, group, swaps, tip in CRAVING_LIBRARY:
        hits = [w for w in words if w in text]
        if hits:
            length = max(len(w) for w in hits)
            if not best or length > best[0]:
                best = (length, group, swaps, tip)
    return best[1:] if best else None


def resync_garden() -> None:
    """After data is deleted, Tulsi follows what's left: her growth is worked out again from the remaining data,
    and a flower is kept only if a logged weight still reaches that goal. (On normal bad days she never shrinks;
    this is only for deleted data.)"""
    logged = [kg for _, kg in weights(all_days())]
    lowest = min(logged) if logged else None
    keep = [f for f in storage.load_flowers() if lowest is not None and lowest <= float(f["goal"]) + 0.05]
    storage.reset_garden(keep_flowers=keep)
