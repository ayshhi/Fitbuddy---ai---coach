"""
cards.py - images you can download:
  - a share card (PNG) to post on WhatsApp or Instagram, where you choose what's shown
  - a one-page doctor report (PDF) to take to your gynaecologist
Both are drawn with Pillow, so nothing extra needs installing.
"""

import io
from datetime import date, timedelta

from PIL import Image, ImageDraw, ImageFont

import journey
import storage

PURPLE_DARK, PURPLE, LAVENDER, INK, MUTED = (78, 42, 132), (123, 63, 191), (241, 234, 251), (42, 33, 64), (120, 110, 140)
GREEN, GREEN_DARK, PINK = (108, 203, 148), (47, 143, 91), (229, 143, 199)


def _font(size: int, bold: bool = False):
    names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _draw_tulsi(d: ImageDraw.ImageDraw, cx: int, cy: int, s: float, stage: int) -> None:
    """A simple Tulsi (round body, face, leaves, and a flower or bud at later stages)."""
    stem_top = cy - s * (0.9 + 0.35 * min(stage, 4))
    if stage >= 2:
        d.line([(cx, cy - s * 0.7), (cx, stem_top)], fill=GREEN_DARK, width=max(3, int(s * 0.09)))
        for i in range(min(stage, 4)):
            y = cy - s * 0.85 - i * s * 0.32
            d.ellipse([cx - s * 0.55, y - s * 0.12, cx - s * 0.04, y + s * 0.12], fill=(92, 192, 138))
            d.ellipse([cx + s * 0.04, y - s * 0.2, cx + s * 0.55, y + s * 0.04], fill=(63, 174, 116))
    else:
        d.line([(cx, cy - s * 0.7), (cx, cy - s * 1.0)], fill=GREEN_DARK, width=max(3, int(s * 0.09)))
        d.ellipse([cx - s * 0.6, cy - s * 1.15, cx - s * 0.02, cy - s * 0.88], fill=(92, 192, 138))
        d.ellipse([cx + s * 0.02, cy - s * 1.25, cx + s * 0.62, cy - s * 0.95], fill=(63, 174, 116))
    if stage == 4:
        d.ellipse([cx - s * 0.16, stem_top - s * 0.38, cx + s * 0.16, stem_top + s * 0.02], fill=PINK)
    if stage >= 5:
        for dx, dy in [(0, -0.28), (0.27, -0.09), (0.17, 0.23), (-0.17, 0.23), (-0.27, -0.09)]:
            px, py = cx + dx * s, stem_top + dy * s
            d.ellipse([px - s * 0.17, py - s * 0.17, px + s * 0.17, py + s * 0.17], fill=PINK if dy < 0 else (195, 139, 234))
        d.ellipse([cx - s * 0.12, stem_top - s * 0.12, cx + s * 0.12, stem_top + s * 0.12], fill=(247, 197, 72))
    d.ellipse([cx - s * 0.78, cy - s * 0.72, cx + s * 0.78, cy + s * 0.62], fill=GREEN)
    for ex in (-0.28, 0.28):
        d.ellipse([cx + ex * s - s * 0.09, cy - s * 0.22, cx + ex * s + s * 0.09, cy - s * 0.04], fill=(30, 59, 44))
        d.ellipse([cx + ex * s - s * 0.02, cy - s * 0.2, cx + ex * s + s * 0.04, cy - s * 0.14], fill="white")
        d.ellipse([cx + ex * s * 1.55 - s * 0.13, cy + s * 0.04, cx + ex * s * 1.55 + s * 0.13, cy + s * 0.15], fill=(245, 154, 166))
    d.arc([cx - s * 0.16, cy - s * 0.05, cx + s * 0.16, cy + s * 0.2], 20, 160, fill=(30, 59, 44), width=max(2, int(s * 0.06)))


def _gradient(w: int, h: int) -> Image.Image:
    """Purple diagonal gradient (drawn small, then smoothly enlarged, which is much faster)."""
    sw, sh = 54, 68
    img = Image.new("RGB", (sw, sh))
    px = img.load()
    a, b = PURPLE_DARK, (195, 139, 234)
    for y in range(sh):
        for x in range(sw):
            t = x / sw * 0.6 + y / sh * 0.4
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return img.resize((w, h), Image.BILINEAR)


def share_card(profile: dict, show_weight: bool = False, show_win: bool = True) -> bytes:
    """A 1080x1350 PNG (Instagram portrait size)."""
    rows = journey.all_days()
    g = journey.growth(profile, rows)
    badges = [b for b in journey.badges(profile, rows) if b["earned"]]
    month_start = date.today().replace(day=1).isoformat()
    walks_month = sum(float(r.get("workouts", 0) or 0) for d, r in rows.items() if d >= month_start)
    km_month = sum(v for d, v in journey.daily_km(rows).items() if d >= month_start)
    checkins = {d for d, r in rows.items() if r.get("checked_in")}

    W, H = 1080, 1350
    img = _gradient(W, H)
    d = ImageDraw.Draw(img)
    name = profile.get("name") or "My"
    d.text((80, 80), f"{name}'s journey with Tulsi" if profile.get("name") else "My journey with Tulsi", font=_font(54, True), fill="white")
    d.text((80, 150), date.today().strftime("%d %B %Y"), font=_font(32), fill=(239, 230, 251))

    d.rounded_rectangle([60, 230, W - 60, H - 130], radius=48, fill="white")
    d.ellipse([W / 2 - 190, 280, W / 2 + 190, 660], fill=LAVENDER)
    _draw_tulsi(d, W // 2, 545, 100, g["stage"])
    d.text((W / 2, 700), f"Tulsi is a {g['name'].lower()}" + (f" with {g['flowers']} flower{'s' if g['flowers'] > 1 else ''}" if g.get("flowers", 0) > 1 else ""), font=_font(44, True), fill=PURPLE_DARK, anchor="mm")

    tiles = [(f"{km_month:,.0f} km", "walked this month"), (f"{walks_month:.0f}", "walks this month"),
             (f"{len(badges)}", "badges earned"), (f"{journey._streak(checkins, date.today())}", "best check-in streak")]
    if show_weight and g["goal"]["lost"] > 0:
        tiles[3] = (f"{g['goal']['lost']:g} kg", "lost so far")
    tw, th, gap, x0, y0 = 410, 150, 36, 115, 755
    for i, (big, small) in enumerate(tiles):
        x, y = x0 + (i % 2) * (tw + gap), y0 + (i // 2) * (th + gap)
        d.rounded_rectangle([x, y, x + tw, y + th], radius=30, fill=LAVENDER)
        d.text((x + tw / 2, y + 62), big, font=_font(58, True), fill=INK, anchor="mm")
        d.text((x + tw / 2, y + 116), small, font=_font(29), fill=MUTED, anchor="mm")

    wins = storage.load_wins()
    if show_win and wins:
        text = wins[-1]["text"]
        text = text if len(text) <= 52 else text[:49] + "..."
        d.text((W / 2, 1148), f"Latest win: {text}", font=_font(34, True), fill=PURPLE, anchor="mm")
    d.text((W / 2, H - 65), "Made with Tulsi  ·  kind, judgement-free health coaching",
           font=_font(28), fill=(239, 230, 251), anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ---------------- Doctor report ----------------

def _wrap(d, text, font, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if d.textlength(trial, font=font) <= width:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def doctor_report(profile: dict) -> bytes:
    """A one-page A4 PDF summary for a doctor's appointment."""
    W, H, M = 1240, 1754, 90
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    rows = journey.all_days()
    today = date.today()
    y = M

    d.rectangle([0, 0, W, 150], fill=PURPLE_DARK)
    d.text((M, 45), "Health summary for my doctor", font=_font(44, True), fill="white")
    d.text((M, 102), f"Prepared {today.strftime('%d %B %Y')} with the Tulsi app (self-tracked data, not a medical record)",
           font=_font(22), fill=(239, 230, 251))
    y = 190

    def heading(text):
        nonlocal y
        d.text((M, y), text, font=_font(30, True), fill=PURPLE_DARK)
        y += 48

    def line(text, bold=False):
        nonlocal y
        for part in _wrap(d, text, _font(24, bold), W - 2 * M):
            d.text((M, y), part, font=_font(24, bold), fill=INK)
            y += 34

    heading("About me")
    p = profile
    line(f"Name: {p.get('name') or '-'}  ·  Age: {p.get('age') or '-'}  ·  Height: {p.get('height_cm') or '-'} cm")
    line(f"Conditions: {', '.join(p.get('conditions', [])) or '-'}")
    line(f"Medications: {p.get('medications') or '-'}")
    if p.get("report_summary"):
        line("Summary of uploaded reports: " + " ".join(p["report_summary"].split())[:400])
    y += 16

    heading("Weight")
    w = journey.weights(rows)
    if len(w) >= 2:
        line(f"{w[0][1]:g} kg on {w[0][0]}  →  {w[-1][1]:g} kg on {w[-1][0]}  (change {w[-1][1] - w[0][1]:+.1f} kg)")
        cx0, cy0, cw, ch = M, y + 10, W - 2 * M, 220
        d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=16, outline=(230, 221, 243), width=2)
        vals = [v for _, v in w]
        lo, hi = min(vals) - 1, max(vals) + 1
        t0 = date.fromisoformat(w[0][0]).toordinal()
        span = (date.fromisoformat(w[-1][0]).toordinal() - t0) or 1
        pts = [(cx0 + 30 + (cw - 60) * (date.fromisoformat(dd).toordinal() - t0) / span,
                cy0 + 20 + (ch - 40) * (1 - (v - lo) / (hi - lo))) for dd, v in w]
        d.line(pts, fill=PURPLE, width=4)
        for x, yy in pts:
            d.ellipse([x - 6, yy - 6, x + 6, yy + 6], fill="white", outline=PURPLE, width=3)
        y = cy0 + ch + 30
    else:
        line("Not enough weight records yet.")
    y += 10

    heading("Menstrual cycle")
    periods = storage.load_periods()
    cyc = journey.cycle_info()
    if periods:
        line(f"Period start dates (most recent last): {', '.join(periods[-8:])}")
        if cyc:
            line(f"Average cycle length: {cyc['length']} days" + ("  (looks irregular)" if cyc["irregular"] else "")
                 + f".  Today: cycle day {cyc['day']}.")
    else:
        line("No period dates logged.")
    y += 16

    heading("Last 30 days")
    start = (today - timedelta(days=30)).isoformat()
    recent = {dd: r for dd, r in rows.items() if dd >= start}

    def avg(key):
        vals = [float(r[key]) for r in recent.values() if r.get(key)]
        return sum(vals) / len(vals) if vals else None

    sleep, steps = avg("sleep_hours"), avg("steps")
    km = sum(v for dd, v in journey.daily_km(rows).items() if dd >= start)
    line(f"Average sleep: {f'{sleep:.1f} h' if sleep else '-'}  ·  Average steps: {f'{steps:,.0f}' if steps else '-'}"
         f"  ·  Distance walked: {km:.0f} km")
    stress = [int(c.get("stress", 0)) for dd, c in storage.load_checkins().items() if dd >= start and c.get("stress")]
    if stress:
        line(f"Average stress (1-5, self-rated): {sum(stress) / len(stress):.1f}")
    y += 16

    heading("PCOS symptoms (last 30 days)")
    sym = {dd: v for dd, v in journey.symptom_days().items() if dd >= start}
    if sym:
        for key, label in journey.SYMPTOMS.items():
            levels = [int(v.get(key, 0)) for v in sym.values()]
            days_with = sum(1 for lv in levels if lv > 0)
            if days_with:
                line(f"{label}: on {days_with} of {len(levels)} logged days, strongest: {journey.LEVELS[max(levels)].lower()}")
        for insight in journey.symptom_insights():
            line("Pattern: " + insight)
    else:
        line("No symptoms logged.")
    y += 16

    heading("Questions for my doctor")
    for _ in range(3):
        d.line([(M, y + 30), (W - M, y + 30)], fill=(220, 210, 235), width=2)
        y += 52

    d.text((M, H - 70), "Self-reported data from the Tulsi app. Not a diagnosis.", font=_font(20), fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=150)
    return buf.getvalue()
