"""
storage.py - saves and loads the user's data.

Everything is stored as simple JSON files inside the local `data/` folder
on the user's own computer. Nothing is uploaded anywhere except the parts
we deliberately send to the AI coach.
"""

import json
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
PROFILE_FILE = DATA_DIR / "profile.json"
CHECKINS_FILE = DATA_DIR / "checkins.json"
MEALS_FILE = DATA_DIR / "meals.json"


def _read(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write(path: Path, data) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- Health profile ----------

def load_profile() -> dict:
    return _read(PROFILE_FILE, {})


def save_profile(profile: dict) -> None:
    _write(PROFILE_FILE, profile)


def delete_profile() -> None:
    if PROFILE_FILE.exists():
        PROFILE_FILE.unlink()


# ---------- Daily check-ins ----------
# Stored as {"2026-11-13": {...}, "2026-11-14": {...}}

def load_checkins() -> dict:
    return _read(CHECKINS_FILE, {})


def save_checkin(day: str, entry: dict) -> None:
    checkins = load_checkins()
    checkins[day] = entry
    _write(CHECKINS_FILE, checkins)


def recent_checkins(days: int = 7, today: date | None = None) -> dict:
    """Return check-ins from the last `days` days (including today), oldest first."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    checkins = load_checkins()
    return {
        d: checkins[d]
        for d in sorted(checkins)
        if start.isoformat() <= d <= today.isoformat()
    }


# ---------- Meals (from food photo scans) ----------
# Stored as {"2026-11-13": [{"meal": "Lunch", "items": [...], "calories": 650}, ...]}

def load_meals(day: str) -> list[dict]:
    return _read(MEALS_FILE, {}).get(day, [])


def add_meal(day: str, meal: dict) -> None:
    meals = _read(MEALS_FILE, {})
    meals.setdefault(day, []).append(meal)
    _write(MEALS_FILE, meals)


def delete_meal(day: str, index: int) -> None:
    meals = _read(MEALS_FILE, {})
    if 0 <= index < len(meals.get(day, [])):
        meals[day].pop(index)
        _write(MEALS_FILE, meals)


def day_calories(day: str) -> int:
    return sum(int(m.get("calories", 0)) for m in load_meals(day))


def day_foods(day: str) -> str:
    """Short text list of what was eaten, e.g. 'Lunch: rice, sambar; Dinner: chapati'."""
    return "; ".join(
        f"{m.get('meal')}: {', '.join(i['name'] for i in m.get('items', []))}"
        for m in load_meals(day)
    )


# ---------- Samsung Health import ----------
# Stored as {"2026-11-13": {"steps": 7798, "distance_km": 5.6, "sleep_hours": 7.5, ...}}

SAMSUNG_FILE = DATA_DIR / "samsung.json"


def load_samsung() -> dict:
    return _read(SAMSUNG_FILE, {})


def save_samsung(daily: dict) -> None:
    """Merge newly imported days into what we already have."""
    existing = load_samsung()
    for day, values in daily.items():
        existing.setdefault(day, {}).update(values)
    _write(SAMSUNG_FILE, existing)


def recent_samsung(days: int = 14, today: date | None = None) -> dict:
    today = today or date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    data = load_samsung()
    return {d: data[d] for d in sorted(data) if start <= d <= today.isoformat()}


def clear_samsung() -> None:
    if SAMSUNG_FILE.exists():
        SAMSUNG_FILE.unlink()


# ---------- Weight history entered by hand ----------
# Stored as {"2025-11-01": 80.0, "2026-11-13": 63.0}

WEIGHTS_FILE = DATA_DIR / "weights.json"


def load_weights() -> dict:
    return _read(WEIGHTS_FILE, {})


def add_weight(day: str, kg: float) -> None:
    weights = load_weights()
    weights[day] = kg
    _write(WEIGHTS_FILE, dict(sorted(weights.items())))


def delete_weight(day: str) -> None:
    weights = load_weights()
    weights.pop(day, None)
    _write(WEIGHTS_FILE, weights)


# ---------- Chat history with Tulsi ----------

CHAT_FILE = DATA_DIR / "chat.json"


def load_chat() -> list[dict]:
    return _read(CHAT_FILE, [])


def save_chat(messages: list[dict]) -> None:
    _write(CHAT_FILE, messages[-200:])  # keep the most recent 200 messages


# ---------- Water (glasses per day) ----------

WATER_FILE = DATA_DIR / "water.json"


def water_today(day: str) -> int:
    return int(_read(WATER_FILE, {}).get(day, 0))


def set_water(day: str, glasses: int) -> None:
    water = _read(WATER_FILE, {})
    water[day] = max(0, glasses)
    _write(WATER_FILE, water)


def load_water() -> dict:
    return _read(WATER_FILE, {})


# ---------- Period start dates (for cycle-aware coaching) ----------

PERIODS_FILE = DATA_DIR / "periods.json"


def load_periods() -> list[str]:
    return sorted(set(_read(PERIODS_FILE, [])))


def add_period(day: str) -> None:
    _write(PERIODS_FILE, sorted(set(load_periods() + [day])))


def delete_period(day: str) -> None:
    _write(PERIODS_FILE, [d for d in load_periods() if d != day])


# ---------- Non-scale victories ("wins") journal ----------

WINS_FILE = DATA_DIR / "wins.json"


def load_wins() -> list[dict]:
    return _read(WINS_FILE, [])


def add_win(day: str, text: str, emoji: str) -> None:
    wins = load_wins()
    wins.append({"date": day, "text": text, "emoji": emoji})
    _write(WINS_FILE, wins)


def delete_win(index: int) -> None:
    wins = load_wins()
    if 0 <= index < len(wins):
        wins.pop(index)
        _write(WINS_FILE, wins)


def count_meals() -> int:
    return sum(len(v) for v in _read(MEALS_FILE, {}).values())


# ---------- Tulsi's growth (she never shrinks) ----------

GARDEN_FILE = DATA_DIR / "garden.json"


def _garden() -> dict:
    return _read(GARDEN_FILE, {})


def load_best_growth() -> float:
    return float(_garden().get("best", 0))


def save_best_growth(value: float) -> None:
    g = _garden()
    g["best"] = value
    _write(GARDEN_FILE, g)


def load_seen_badges() -> list[str] | None:
    """None means badges have never been recorded yet."""
    return _garden().get("seen_badges")


def save_seen_badges(names: list[str]) -> None:
    g = _garden()
    g["seen_badges"] = sorted(set(names))
    _write(GARDEN_FILE, g)



# ---------- Walk challenge and friends ----------

CHALLENGE_FILE = DATA_DIR / "challenge.json"


def load_challenge() -> dict:
    return _read(CHALLENGE_FILE, {})


def save_challenge(data: dict) -> None:
    _write(CHALLENGE_FILE, data)
