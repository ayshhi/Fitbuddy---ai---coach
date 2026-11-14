"""
cycle.py - period and cycle tracking: log each period day with its flow, see your cycle on a calendar,
and get predictions for your next period and phases (follicular, ovulation, luteal).
"""

import calendar
import html
from datetime import date, timedelta

import journey
import storage

FLOWS = {  # key: (emoji, label, colour)
    "heavy": ("🔴", "Heavy", "#C2334D"),
    "medium": ("🩸", "Medium", "#E0566F"),
    "light": ("💧", "Light", "#F08EA0"),
    "spotting": ("·", "Spotting", "#F6B8C4"),
}
TYPICAL_FLOW = ["medium", "heavy", "medium", "light", "spotting"]  # used until you've logged your own

PHASE_STYLE = {  # phase: (background, text colour, label)
    "Period": ("#FADDE3", "#9E1F3A", "Period"),
    "Follicular": ("#E3F4EA", "#1E6B45", "Follicular"),
    "Ovulation": ("#FFF0D6", "#A35A00", "Ovulation"),
    "Luteal": ("#EFE6FB", "#4E2A84", "Luteal"),
}

PHASE_GUIDE = {
    "Period": ("Days 1–5", "Hormones are at their lowest, so energy can dip.",
               "Iron-rich food (greens, dates, ragi, eggs), warm meals, ginger tea.",
               "Gentle: walking, stretching, the 🌸 period-friendly workout."),
    "Follicular": ("After your period", "Oestrogen rises, and energy and mood usually lift.",
                   "Fresh, light meals with protein: sprouts, eggs, fish, salads.",
                   "Great time for strength, HIIT and trying new workouts."),
    "Ovulation": ("Mid-cycle, ~3 days", "Often your strongest, most confident days.",
                  "Fibre and veg to help your body clear extra oestrogen.",
                  "Go for your hardest workout or a longer walk."),
    "Luteal": ("The ~2 weeks before your period", "Progesterone rises; cravings, bloating and tiredness are common.",
               "Keep protein and fibre high; magnesium (nuts, seeds, dark chocolate).",
               "Calmer workouts: walking, yoga, lower-body strength."),
}


def _starts() -> list[date]:
    return sorted(date.fromisoformat(d) for d in storage.load_periods())


def log_flow(day: str, flow: str) -> None:
    """Saves a period day. If the two days before it have no flow, it's a new period, so its start date is saved."""
    flows = storage.load_flow()
    d = date.fromisoformat(day)
    storage.set_flow(day, flow)
    before = [(d - timedelta(days=i)).isoformat() for i in (1, 2)]
    if not any(b in flows for b in before):
        storage.add_period(day)
        nxt = (d + timedelta(days=1)).isoformat()
        if nxt in storage.load_periods():  # this day now starts that period, not the day after
            storage.delete_period(nxt)


def remove_flow(day: str) -> None:
    storage.set_flow(day, None)
    if day in storage.load_periods():
        storage.delete_period(day)
        nxt = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        if nxt in storage.load_flow():
            storage.add_period(nxt)


def cycle_length() -> int:
    info = journey.cycle_info()
    return info["length"] if info else 28


def flow_pattern() -> list[str]:
    """Your usual flow on period day 1, 2, 3... from the periods you've logged (most common level each day)."""
    flows = storage.load_flow()
    by_day: dict[int, list[str]] = {}
    for s in _starts():
        for i in range(8):
            f = flows.get((s + timedelta(days=i)).isoformat())
            if f:
                by_day.setdefault(i, []).append(f)
    if not by_day:
        return TYPICAL_FLOW
    length = max(by_day) + 1
    return [max(set(by_day.get(i, ["light"])), key=by_day.get(i, ["light"]).count) for i in range(length)]


def predicted_starts(until: date) -> list[date]:
    starts = _starts()
    if not starts:
        return []
    length, out, nxt = cycle_length(), [], starts[-1]
    while True:
        nxt = nxt + timedelta(days=length)
        if nxt > until:
            return out
        if nxt > date.today() - timedelta(days=length):
            out.append(nxt)


def day_info(d: date) -> dict | None:
    """What a calendar day looks like: phase, flow (logged or predicted) and cycle day."""
    flows = storage.load_flow()
    starts = _starts()
    if not starts:
        f = flows.get(d.isoformat())
        return {"phase": "Period", "flow": f, "predicted": False, "cycle_day": None} if f else None
    every = starts + [p for p in predicted_starts(d + timedelta(days=1)) if p > starts[-1]]
    before = [s for s in every if s <= d]
    if not before:
        return None
    s = before[-1]
    predicted = s not in starts
    length = cycle_length()
    n = (d - s).days + 1
    if n > length + 10:
        return None
    ov = max(length - 14, 10)
    logged = flows.get(d.isoformat())
    pattern = flow_pattern()
    cycle_logged = any((s + timedelta(days=i)).isoformat() in flows for i in range(10))
    if logged:
        phase, flow = "Period", logged
    elif not cycle_logged and n <= len(pattern) and (predicted or d > date.today()):
        phase, flow = "Period", pattern[n - 1]
    elif not cycle_logged and n <= 5:
        phase, flow = "Period", None
    elif n < ov - 1:
        phase, flow = "Follicular", None
    elif n <= ov + 1:
        phase, flow = "Ovulation", None
    else:
        phase, flow = "Luteal", None
    return {"phase": phase, "flow": flow, "predicted": predicted or (d > date.today() and not logged), "cycle_day": n}


def calendar_html(year: int, month: int) -> str:
    """A month calendar coloured by phase, with flow dots on period days and dashed borders for predictions."""
    today = date.today()
    cells = []
    for wk in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        for d in wk:
            if d.month != month:
                cells.append('<div class="cal-d out"></div>')
                continue
            info = day_info(d)
            style, inner = "", ""
            if info:
                bg, fg, _ = PHASE_STYLE[info["phase"]]
                style = f"background:{bg};color:{fg};"
                if info["flow"]:
                    emoji, label, colour = FLOWS[info["flow"]]
                    style = f"background:{colour}22;color:#9E1F3A;"
                    size = {"heavy": 4, "medium": 3, "light": 2, "spotting": 1}[info["flow"]]
                    inner = '<div class="drops">' + "".join(f'<i style="background:{colour}"></i>' for _ in range(size)) + "</div>"
                if info["predicted"]:
                    style += "border:2px dashed currentColor;opacity:.85;"
                if info["phase"] == "Ovulation":
                    inner += '<div class="ov">✨</div>'
            cls = "cal-d today" if d == today else "cal-d"
            cells.append(f'<div class="{cls}" style="{style}"><b>{d.day}</b>{inner}</div>')
    heads = "".join(f'<div class="cal-h">{h}</div>' for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    return (CAL_CSS + f'<div class="cal"><div class="cal-title">{calendar.month_name[month]} {year}</div>'
            f'<div class="cal-g">{heads}{"".join(cells)}</div>{legend_html()}</div>')


def legend_html() -> str:
    phases = "".join(f'<span><i style="background:{bg};border:1px solid {fg}55"></i>{label}</span>'
                     for bg, fg, label in PHASE_STYLE.values())
    flows = "".join(f'<span><i style="background:{c}"></i>{lab}</span>' for _, lab, c in FLOWS.values())
    return (f'<div class="cal-leg">{phases}<span><i style="border:2px dashed #9A90AE;background:none"></i>Predicted</span></div>'
            f'<div class="cal-leg">Flow: {flows}</div>')


CAL_CSS = """<style>
.cal { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:26px; padding:1.3rem 1.4rem 1rem;
       box-shadow:0 8px 24px rgba(78,42,132,.06); }
.cal-title { font-weight:800; font-size:1.35rem; color:#2A2140; text-align:center; margin-bottom:.8rem; }
.cal-g { display:grid; grid-template-columns:repeat(7, 1fr); gap:.45rem; }
.cal-h { text-align:center; font-size:.85rem; font-weight:700; color:#9A90AE; padding-bottom:.2rem; }
.cal-d { position:relative; aspect-ratio: 1 / .82; border-radius:14px; background:#FAF7FD; color:#786E8C;
         display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.25rem; font-size:1.05rem; }
.cal-d.out { background:transparent; }
.cal-d.today { box-shadow:0 0 0 3px #7B3FBF; }
.cal-d .drops { display:flex; gap:3px; }
.cal-d .drops i { width:.45rem; height:.45rem; border-radius:50% 50% 50% 0; transform:rotate(-45deg); display:block; }
.cal-d .ov { position:absolute; top:.15rem; right:.3rem; font-size:.8rem; }
.cal-leg { display:flex; flex-wrap:wrap; gap:.9rem; justify-content:center; margin-top:.8rem; font-size:.85rem; color:#786E8C; }
.cal-leg span { display:flex; align-items:center; gap:.35rem; }
.cal-leg i { width:.9rem; height:.9rem; border-radius:5px; display:inline-block; }
</style>"""


def summary() -> dict | None:
    """Today's cycle day and phase, plus the next period and how many days away it is."""
    info = journey.cycle_info()
    if not info:
        return None
    nxt = [p for p in predicted_starts(date.today() + timedelta(days=120)) if p >= date.today()]
    nxt_date = nxt[0] if nxt else date.fromisoformat(info["next_period"])
    today = day_info(date.today()) or {}
    phase = today.get("phase", info["phase"])
    emoji, tip = journey.PHASES.get(phase, (info["emoji"], info["tip"]))
    return {**info, "phase": phase, "emoji": emoji, "tip": tip, "cycle_day": today.get("cycle_day", info["day"]), "next": nxt_date,
            "days_to_next": (nxt_date - date.today()).days, "pattern": flow_pattern()}
