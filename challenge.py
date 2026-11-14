"""
challenge.py - "Tulsi's Garden Path", a snakes-and-ladders style game with no snakes.

  - You choose a challenge type. In "Every step counts" (the default), ANY healthy action moves you
    forward: a check-in, movement of any kind, plan steps, water, sleep, food scans, cravings you rode out.
  - Ladders jump you ahead for special moments (a 3-day streak, finishing Tulsi's whole plan...).
  - Nothing ever sends you backwards: Tulsi never punishes.
  - Friends: each app makes a short "friend code" (name + position). Send it on WhatsApp,
    paste your friend's code, and their piece appears on your board. No server, no health data shared.
"""

import base64
import html
import json
from datetime import date

import journey
import storage

# Each ladder: (bottom square as a fraction of the board, squares it jumps, moment that unlocks it)
LADDERS = [
    (0.15, 4, "streak", "🔥", "Check in 3 days in a row"),
    (0.35, 4, "plan", "📋", "Finish all 3 steps of Tulsi's plan in a day"),
    (0.55, 5, "food", "📸", "Scan a meal"),
    (0.75, 5, "win", "💜", "Log a non-scale win"),
]

# Challenge types: name, short description, how you move, board lengths to choose from
TYPES = {
    "everything": ("🌈 Every step counts", "Any healthy action moves you forward. Great for tired or period days too.",
                   ["✅ Check-in +1", "🏃‍♀️ Every 15 min of any movement +1", "📋 Each plan step done +1",
                    "💧 8 glasses of water +1", "😴 7+ hours of sleep +1", "📸 Food scan +1", "🌊 Craving rode out or swapped +1"],
                   [50, 75, 100]),
    "movement": ("🧘 Movement minutes", "Walking, yoga, dancing, home workouts: it all counts.",
                 ["🏃‍♀️ Every 15 minutes of any movement +1"], [30, 50, 75]),
    "water": ("💧 Hydration", "Build the water habit, one glass at a time.", ["💧 Every glass of water +1"], [50, 75, 100]),
    "sleep": ("😴 Sleep", "Rest is part of the work, especially with PCOS.",
              ["😴 A night of 7+ hours +2", "🌙 A night of 6-7 hours +1"], [20, 30]),
    "walking": ("🚶 Walking km", "The classic: every km you walk.", ["🚶 Every 1 km walked +1"], [20, 30, 40, 50]),
}


COLS = 10


def _rc(n: int) -> tuple[int, int]:
    """Square number -> (row, column on screen), winding like snakes and ladders."""
    r, c = divmod(n - 1, COLS)
    return r, (COLS - 1 - c if r % 2 else c)


def _square(r: int, c: int) -> int:
    return r * COLS + (COLS - 1 - c if r % 2 else c) + 1


# Rough squares per day for someone doing well, used to show "about N days" when choosing a board
TYPICAL_PER_DAY = {"everything": 5, "movement": 2, "water": 7, "sleep": 1.5, "walking": 3}


def estimate_days(kind: str, length: int) -> int:
    return max(1, round(length / TYPICAL_PER_DAY.get(kind, 3)))


def ladders_for(length: int) -> list[dict]:
    """Ladders go straight up to the square in the row above, so they look like real ladders.
    Each starts near its spot on the board and jumps about 5-9 squares."""
    out, used = [], set()
    for frac, _jump, habit, emoji, desc in LADDERS:
        target = max(2, round(length * frac))
        best = None
        for n in sorted(range(2, length), key=lambda n: abs(n - target)):
            r, c = _rc(n)
            up = _square(r + 1, c)
            if up < length and 4 <= up - n <= 11 and n not in used and up not in used:
                best = (n, up)
                break
        if best:
            used.update(best)
            out.append({"bottom": best[0], "top": best[1], "habit": habit, "emoji": emoji, "desc": desc})
    return out


def habits_done(start: str) -> set[str]:
    """Which ladder moments have happened since the challenge started."""
    rows = {d: r for d, r in journey.all_days().items() if d >= start}
    done = set()
    checked = {d for d, r in rows.items() if r.get("checked_in")}
    if journey._streak(checked, date.today()) >= 3:
        done.add("streak")
    if any(d >= start and p["items"] and all(i.get("done") for i in p["items"]) for d, p in storage.load_plans().items()):
        done.add("plan")
    meals = storage._read(storage.MEALS_FILE, {})
    if any(d >= start and v for d, v in meals.items()):
        done.add("food")
    if any(w["date"] >= start for w in storage.load_wins()):
        done.add("win")
    return done


def events(start: str, kind: str) -> list[tuple[str, int, str]]:
    """Every move you've earned since the start: (date, squares, why). Used for your position and the activity feed."""
    rows = {d: r for d, r in journey.all_days().items() if d >= start and d <= date.today().isoformat()}
    checkins = storage.load_checkins()
    meals = storage._read(storage.MEALS_FILE, {})
    plans = storage.load_plans()
    cravings = storage.load_cravings()
    out = []
    for d in sorted(set(rows) | {m for m in meals if m >= start}):
        r = rows.get(d, {})
        minutes = max(float(checkins.get(d, {}).get("exercise_minutes") or 0), float(r.get("workout_min") or 0))
        water = int(r.get("water") or 0)
        sleep = float(r.get("sleep_hours") or 0)
        if kind == "everything":
            if r.get("checked_in"):
                out.append((d, 1, "✅ Checked in"))
            if minutes >= 15:
                out.append((d, int(minutes // 15), f"🏃‍♀️ {minutes:.0f} min of movement"))
            done = sum(1 for i in plans.get(d, {}).get("items", []) if i.get("done"))
            if done:
                out.append((d, done, f"📋 {done} plan step{'s' if done > 1 else ''} done"))
            if water >= 8:
                out.append((d, 1, "💧 8 glasses of water"))
            if sleep >= 7:
                out.append((d, 1, f"😴 {sleep:g} h of sleep"))
            scans = len([m for m in meals.get(d, []) if m.get("source") != "quick log"])
            if scans:
                out.append((d, min(scans, 3), f"📸 {scans} food scan{'s' if scans > 1 else ''}"))
            rode = sum(1 for c in cravings if c["when"][:10] == d and c.get("outcome") in ("swap", "passed"))
            if rode:
                out.append((d, rode, "🌊 Rode out a craving"))
        elif kind == "movement" and minutes >= 15:
            out.append((d, int(minutes // 15), f"🏃‍♀️ {minutes:.0f} min of movement"))
        elif kind == "water" and water:
            out.append((d, min(water, 12), f"💧 {water} glasses of water"))
        elif kind == "sleep" and sleep >= 6:
            out.append((d, 2 if sleep >= 7 else 1, f"😴 {sleep:g} h of sleep"))
        elif kind == "walking":
            km = journey.daily_km({d: r}).get(d, 0)
            if km >= 1:
                out.append((d, int(km), f"🚶 {km:.1f} km walked"))
    return out


def my_progress() -> dict | None:
    ch = storage.load_challenge()
    if not ch.get("start"):
        return None
    start, length = ch["start"], int(ch.get("length", 30))
    kind = ch.get("type", "walking")  # challenges started before types existed were walking ones
    evs = events(start, kind)
    earned = sum(n for _, n, _ in evs)
    done = habits_done(start)
    pos, climbed = min(earned, length), []
    for lad in ladders_for(length):
        if pos >= lad["bottom"] and lad["habit"] in done and pos < length:
            pos = min(length, pos + (lad["top"] - lad["bottom"]))
            climbed.append(lad["emoji"])
    week_ago = (date.today().toordinal() - 6)
    this_week = sum(n for d, n, _ in evs if date.fromisoformat(d).toordinal() >= week_ago)
    return {"start": start, "length": length, "type": kind, "km": earned, "points": earned, "pos": pos,
            "done": done, "climbed": climbed, "finished": pos >= length, "name": ch.get("name", "Me"),
            "events": evs, "this_week": this_week}


def _checksum(payload: str) -> str:
    """4 characters that change if any part of the code is mistyped or edited."""
    import hashlib
    return hashlib.sha1(payload.encode()).hexdigest()[:4].upper()


def make_code(name: str, prog: dict) -> str:
    data = {"n": name[:20], "p": prog["pos"], "k": prog["points"], "l": prog["length"], "s": prog["start"],
            "y": prog.get("type", "walking"), "t": date.today().isoformat()}
    payload = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"TULSI-{payload}-{_checksum(payload)}"


def read_code(code: str) -> dict:
    code = "".join(code.split())  # ignore spaces or line breaks added when copying from WhatsApp
    if not code.upper().startswith("TULSI-"):
        raise ValueError("A friend code starts with TULSI-")
    body = code[6:]
    payload, _, check = body.rpartition("-")
    if not payload or _checksum(payload) != check.upper():
        raise ValueError("This code seems incomplete or mistyped. Ask your friend to send it again.")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode())
    return {"name": str(data["n"])[:20], "pos": int(data["p"]), "km": float(data["k"]),
            "type": str(data.get("y", "walking")), "updated": str(data.get("t", "")), "manual": False}


def days_old(friend: dict) -> int | None:
    try:
        return (date.today() - date.fromisoformat(friend.get("updated", ""))).days
    except ValueError:
        return None


def whatsapp_link(name: str, code: str) -> str:
    from urllib.parse import quote
    text = (f"{name} is on Tulsi's Garden Path 🌿 Join me! Paste my friend code into FitBuddy's "
            f"Walk challenge page:\n{code}")
    return "https://wa.me/?text=" + quote(text)


def save_friend(friend: dict) -> None:
    ch = storage.load_challenge()
    ch.setdefault("friends", {})[friend["name"]] = friend
    storage.save_challenge(ch)


def remove_friend(name: str) -> None:
    ch = storage.load_challenge()
    ch.get("friends", {}).pop(name, None)
    storage.save_challenge(ch)


# ---------------- Drawing the board ----------------

TOKEN_COLORS = ["#E58FC7", "#F7A541", "#4DA3E0", "#3FAE74", "#C0504D"]


def board_svg(length: int, players: list[dict], me_pos: int, done: set[str]) -> str:
    """A winding board, 10 squares per row, numbered like snakes and ladders (bottom-left to top)."""
    cols = COLS
    rows = (length + cols - 1) // cols
    S, pad = 64, 12
    W, H = cols * S + pad * 2, rows * S + pad * 2

    def centre(n):  # square number (1..length) -> x, y
        i = n - 1
        r, c = divmod(i, cols)
        if r % 2 == 1:
            c = cols - 1 - c
        return pad + c * S + S / 2, pad + (rows - 1 - r) * S + S / 2

    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
    for n in range(1, length + 1):
        x, y = centre(n)
        fill = "#E9DCFA" if n <= me_pos else ("#FFFFFF" if n % 2 else "#F7F2FC")
        out.append(f'<rect x="{x - S / 2 + 2}" y="{y - S / 2 + 2}" width="{S - 4}" height="{S - 4}" rx="12" fill="{fill}" stroke="#E6DDF3"/>')
        label = "🌸" if n == length else str(n)
        out.append(f'<text x="{x - S / 2 + 9}" y="{y - S / 2 + 20}" font-size="{16 if n == length else 13}" fill="#9A90AE">{label}</text>')
    # ladders
    for lad in ladders_for(length):
        x1, y1 = centre(lad["bottom"])
        x2, y2 = centre(lad["top"])
        unlocked = lad["habit"] in done
        col = "#3FAE74" if unlocked else "#C9BEDA"
        y1, y2 = y1 + S * 0.36, y2 - S * 0.36  # make the ladder reach across both squares
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5 or 1
        ox, oy = -dy / L * 9, dx / L * 9
        out.append(f'<line x1="{x1 + ox}" y1="{y1 + oy}" x2="{x2 + ox}" y2="{y2 + oy}" stroke="{col}" stroke-width="5" stroke-linecap="round"/>')
        out.append(f'<line x1="{x1 - ox}" y1="{y1 - oy}" x2="{x2 - ox}" y2="{y2 - oy}" stroke="{col}" stroke-width="5" stroke-linecap="round"/>')
        steps = max(4, int(L // 16))
        for k in range(1, steps):
            px, py = x1 + dx * k / steps, y1 + dy * k / steps
            out.append(f'<line x1="{px + ox}" y1="{py + oy}" x2="{px - ox}" y2="{py - oy}" stroke="{col}" stroke-width="4"/>')
        bx, by = centre(lad["bottom"])
        bx, by = bx - S / 2 + 15, by + S / 2 - 15  # habit badge in the bottom-left corner of the ladder's square
        out.append(f'<circle cx="{bx}" cy="{by}" r="12" fill="#FFFFFF" stroke="{col}" stroke-width="2"/>'
                   f'<text x="{bx}" y="{by + 4.5}" text-anchor="middle" font-size="12">{lad["emoji"]}</text>')
    # player tokens (me last, on top)
    for i, p in enumerate(players):
        n = max(1, min(length, int(p["pos"]) or 1))
        x, y = centre(n)
        same = [q for q in players[:i] if max(1, min(length, int(q["pos"]) or 1)) == n]
        x += len(same) * 14 + 10
        color = "#7B3FBF" if p.get("me") else TOKEN_COLORS[i % len(TOKEN_COLORS)]
        initial = html.escape((p["name"] or "?")[0].upper())
        out.append(f'<g><circle cx="{x}" cy="{y + 6}" r="15" fill="{color}" stroke="#FFFFFF" stroke-width="3"/>'
                   f'<text x="{x}" y="{y + 11.5}" text-anchor="middle" font-size="15" font-weight="700" fill="#FFFFFF">{initial}</text>'
                   f'<title>{html.escape(p["name"])}: square {p["pos"]}</title></g>')
    out.append("</svg>")
    return "".join(out)
