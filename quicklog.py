"""
quicklog.py - saves what Tulsi understood from "Just tell Tulsi" into the right places:
check-in, meals, water, symptoms and period dates. Anything you didn't mention is left as it was.
"""

import journey
import storage

LABELS = {
    "sleep_hours": ("😴", "Sleep", "{:g} h"), "steps": ("👟", "Steps", "{:,}"), "distance_km": ("📍", "Distance", "{:g} km"),
    "exercise": ("🏃‍♀️", "Exercise", "{}"), "exercise_minutes": ("⏱️", "Exercise time", "{} min"),
    "water_glasses": ("💧", "Water", "{} glasses"), "stress": ("😣", "Stress", "{}/5"), "energy": ("⚡", "Energy", "{}/5"),
    "mood": ("💭", "Mood", "{}"), "weight_kg": ("⚖️", "Weight", "{:g} kg"), "notes": ("📝", "Note", "{}"),
}


def understood(parsed: dict) -> list[str]:
    """Short, human chips of what was understood, for the confirmation card."""
    chips = [f"{e} {label}: {fmt.format(parsed[k])}" for k, (e, label, fmt) in LABELS.items() if parsed.get(k) not in (None, "")]
    for f in parsed.get("foods", []):
        chips.append(f"🍽️ {f['meal']}: {f['name']} (~{f['calories']} kcal)")
    for k, v in parsed.get("symptoms", {}).items():
        if v:
            chips.append(f"🌡️ {journey.SYMPTOMS.get(k, k)}: {journey.LEVELS[v].lower()}")
    if parsed.get("period_started"):
        chips.append("🩸 Period started")
    return chips


def save(day: str, parsed: dict) -> dict:
    """Merge into the day's check-in and the other logs. Returns the saved check-in."""
    entry = dict(storage.load_checkins().get(day, {}))
    sh = storage.load_samsung().get(day, {})
    # start from Samsung data for anything not already in the check-in
    for key, sh_key in [("sleep_hours", "sleep_hours"), ("steps", "steps"), ("distance_km", "distance_km"),
                        ("exercise_minutes", "workout_min")]:
        if entry.get(key) is None and sh.get(sh_key) is not None:
            entry[key] = sh[sh_key]
    for key in ("sleep_hours", "steps", "distance_km", "exercise", "exercise_minutes", "stress", "energy", "mood", "weight_kg"):
        if parsed.get(key) is not None:
            entry[key] = parsed[key]
    if parsed.get("notes"):
        entry["notes"] = (entry.get("notes", "") + " " + parsed["notes"]).strip()

    by_meal = {}
    for f in parsed.get("foods", []):
        by_meal.setdefault(f["meal"], []).append({"name": f["name"], "portion": "from your message", "calories": f["calories"],
                                                  "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fibre_g": 0, "servings": 1})
    for meal, items in by_meal.items():
        storage.add_meal(day, {"meal": meal, "items": items, "calories": sum(i["calories"] for i in items), "source": "quick log"})
    if by_meal or storage.day_calories(day):
        entry["calories"] = storage.day_calories(day)
        entry["foods"] = storage.day_foods(day)

    if parsed.get("exercise_minutes"):
        import exercise
        name = exercise.guess_exercise(parsed.get("exercise") or "")
        exercise.add(day, name, int(parsed["exercise_minutes"]), storage.load_profile(), source="quick log")

    if parsed.get("water_glasses") is not None:
        storage.set_water(day, max(storage.water_today(day), parsed["water_glasses"]))
    if parsed.get("symptoms"):
        old = storage.load_symptoms().get(day, {})
        storage.save_symptoms(day, {**old, **parsed["symptoms"]})
    if parsed.get("period_started") and day not in storage.load_flow():
        import cycle
        cycle.log_flow(day, "medium")

    entry.setdefault("stress", 2)
    entry.setdefault("energy", 3)
    entry.setdefault("mood", "🙂 Okay")
    storage.save_checkin(day, entry)
    return entry


def summary(day: str, entry: dict) -> str:
    """The check-in shown as your chat bubble."""
    parts = [f"📋 My check-in for {day}"]
    line1 = [f"😴 {entry['sleep_hours']:g}h sleep" if entry.get("sleep_hours") else "",
             f"👟 {int(entry['steps']):,} steps" if entry.get("steps") else "",
             f"📍 {float(entry['distance_km']):g} km" if entry.get("distance_km") else ""]
    line2 = [f"🍽️ {entry['calories']} kcal" if entry.get("calories") else "",
             f"🏃‍♀️ {entry.get('exercise') or 'exercise'} ({entry['exercise_minutes']} min)" if entry.get("exercise_minutes") else ""]
    for line in (line1, line2):
        if any(line):
            parts.append(" · ".join(x for x in line if x))
    parts.append(f"Stress {entry.get('stress', '-')}/5 · Energy {entry.get('energy', '-')}/5 · {entry.get('mood', '')}")
    if entry.get("notes"):
        parts.append("📝 " + entry["notes"])
    return "\n".join(parts)
