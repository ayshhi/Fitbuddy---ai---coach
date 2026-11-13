"""
ui.py - the look and feel of FitBuddy: colours, chat bubbles and Tulsi, the coach character.
"""

import base64
import html
import io
import re
from datetime import datetime

import streamlit as st

COACH_NAME = "Tulsi"

# Tulsi: a cheerful little sprout with two leaves. Drawn in SVG, so no image files are needed.
TULSI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <circle cx="60" cy="60" r="60" fill="#E7F4EC"/>
  <path d="M60 52 C60 40 60 34 60 28" stroke="#2F8F5B" stroke-width="5" stroke-linecap="round" fill="none"/>
  <path d="M60 34 C46 18 26 22 24 34 C38 44 52 42 60 34Z" fill="#5CC08A"/>
  <path d="M60 30 C72 12 94 14 97 27 C84 39 68 38 60 30Z" fill="#3FAE74"/>
  <path d="M33 33 C42 34 50 35 58 34" stroke="#2F8F5B" stroke-width="2" fill="none" stroke-linecap="round" opacity=".6"/>
  <ellipse cx="60" cy="78" rx="34" ry="30" fill="#6CCB94"/>
  <ellipse cx="60" cy="84" rx="26" ry="20" fill="#86D8A8" opacity=".6"/>
  <circle cx="48" cy="74" r="4.5" fill="#1E3B2C"/>
  <circle cx="72" cy="74" r="4.5" fill="#1E3B2C"/>
  <circle cx="49.5" cy="72.5" r="1.5" fill="#fff"/>
  <circle cx="73.5" cy="72.5" r="1.5" fill="#fff"/>
  <ellipse cx="40" cy="84" rx="6" ry="3.5" fill="#F59AA6" opacity=".8"/>
  <ellipse cx="80" cy="84" rx="6" ry="3.5" fill="#F59AA6" opacity=".8"/>
  <path d="M52 86 Q60 94 68 86" stroke="#1E3B2C" stroke-width="3.5" fill="none" stroke-linecap="round"/>
</svg>"""

AVATAR = "data:image/svg+xml;base64," + base64.b64encode(TULSI_SVG.encode()).decode()

CSS = """
<style>
:root {
  --purple: #7B3FBF; --purple-dark: #4E2A84; --lavender: #F1EAFB;
  --chat-bg: #EDE6F6; --me: #E4D4FA; --coach: #FFFFFF; --ink: #2A2140; --muted: #786E8C;
}
/* Bigger text everywhere (no more zooming), and content centred at a comfortable width */
/* Text and layout grow with the screen, so big / high-resolution monitors aren't tiny */
html { font-size: clamp(17px, 1.05vw, 30px); }
.stApp { overflow-x: hidden; }
.block-container { padding-top: 2.2rem; padding-left: 2rem; padding-right: 2rem;
                   max-width: min(58rem, 96vw) !important; margin: 0 auto; }
section[data-testid="stSidebar"] { min-width: 15rem !important; }
section[data-testid="stSidebar"] * { font-size: 1rem; }
.stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button { font-size: 1rem !important; }
h1 { font-size: 2.1rem !important; } h2 { font-size: 1.6rem !important; } h3 { font-size: 1.3rem !important; }
h1, h2, h3 { color: var(--ink); letter-spacing: -0.01em; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E6DDF3; }
.fb-brand { display:flex; align-items:center; gap:12px; margin-bottom: 6px; }
.fb-brand img { width:3.2rem; height:3.2rem; border-radius:50%; }
.fb-brand b { font-size: 1.15rem; color: var(--ink); }
.fb-brand span { display:block; font-size: .8rem; color: var(--muted); }

/* Cards (forms, metrics, expanders) */
div[data-testid="stForm"], div[data-testid="stExpander"] {
  background:#FFFFFF; border:1px solid #E6DDF3; border-radius:16px;
}
div[data-testid="stMetric"] {
  background:#FFFFFF; border:1px solid #E6DDF3; border-radius:14px; padding:12px 14px;
}
.stButton button, .stFormSubmitButton button { border-radius: 999px; }
.stButton button { border: 1px solid #D9C8F2; background: #FFFFFF; color: var(--purple-dark); }
.stButton button:hover { border-color: var(--purple); color: var(--purple); background: var(--lavender); }
.section-label { font-size:.8rem; font-weight:600; color: var(--muted); text-transform: uppercase;
                 letter-spacing:.05em; margin: 14px 0 4px; }

/* ---------- Chat: messages flow on the page, bubbles pop in ---------- */
.chat-head { display:flex; align-items:center; gap:.8rem; margin: .2rem 0 1rem; }
.chat-head img { width:3rem; height:3rem; border-radius:50%; background:#E7F4EC;
                 box-shadow: 0 0 0 3px #FFFFFF, 0 0 0 5px #C38BEA; }
.chat-head b { font-size:1.25rem; color:var(--ink); }
.chat-head span { display:block; font-size:.82rem !important; color:var(--muted); }
.chat-head .dot { display:inline-block; width:.5rem; height:.5rem; border-radius:50%; background:#3FAE74; margin-right:.3rem; }
.chat-flow { padding: .2rem 0 .6rem; }
.day-chip { text-align:center; margin:.4rem 0 .8rem; }
.day-chip span { background:#F1EAFB; color:var(--muted); font-size:.72rem !important; padding:.2rem .7rem; border-radius:99px; }
.row { display:flex; align-items:flex-start; gap:.55rem; margin:.22rem 0; }
.row.me { justify-content:flex-end; }
.row.first { margin-top: .9rem; }
.av { width:2.1rem; height:2.1rem; flex-shrink:0; border-radius:50%; }
.av img { width:100%; height:100%; border-radius:50%; background:#E7F4EC; }
.bubble {
  position:relative; max-width: 72%; padding: .6rem .9rem; border-radius: 1.1rem;
  font-size: 1rem; line-height: 1.5; overflow-wrap:anywhere;
}
.row.coach .bubble { background:#FFFFFF; color:var(--ink); border:1px solid #EEE6F8;
                     box-shadow: 0 2px 10px rgba(78,42,132,.06); }
.row.me .bubble { background: linear-gradient(135deg, #7B3FBF 0%, #9B5DE5 100%); color:#FFFFFF;
                  box-shadow: 0 3px 12px rgba(123,63,191,.25); }
.row.coach.first .bubble { border-top-left-radius:.35rem; }
.row.me.first .bubble { border-top-right-radius:.35rem; }
.row.me .bubble b, .row.me .bubble li, .row.me .bubble p { color:#FFFFFF !important; }
.bubble .time { display:block; text-align:right; margin-top:.15rem; font-size:.66rem !important; opacity:.6; }
.bubble ul { margin: .3rem 0 .1rem 1.1rem; padding:0; }
.bubble li { margin: .15rem 0; }

/* the pop: new bubbles spring up one after another */
.pop { animation: pop .5s cubic-bezier(.2,.9,.3,1.25) both; animation-delay: var(--d, 0s); }
.row.coach.pop { transform-origin: top left; } .row.me.pop { transform-origin: top right; }
@keyframes pop { 0% { opacity:0; transform: translateY(12px) scale(.9); } 100% { opacity:1; transform:none; } }

.typing { display:inline-flex; gap:.25rem; padding:.85rem 1rem !important; }
.typing span { width:.5rem; height:.5rem; background:#B9A6D9; border-radius:50%; animation: bounce 1.1s infinite both; }
.typing span:nth-child(2) { animation-delay:.15s; } .typing span:nth-child(3) { animation-delay:.3s; }
@keyframes bounce { 0%,70%,100% { transform:translateY(0); opacity:.5 } 35% { transform:translateY(-.35rem); opacity:1 } }

/* the message bar sticks to the bottom of the screen */
.st-key-composer { position: sticky; bottom: 0; z-index: 50; background: linear-gradient(180deg, rgba(250,247,253,0) 0%, #FAF7FD 30%);
                   padding: 1.2rem 0 .8rem; }
.st-key-composer div[data-testid="stForm"] { background:#FFFFFF; border:1.5px solid #D9C8F2 !important;
                   border-radius: 999px; padding: .25rem .4rem .25rem 1rem; box-shadow: 0 6px 24px rgba(78,42,132,.12); }
.st-key-composer input { border:none !important; background:transparent !important; box-shadow:none !important; }
.st-key-composer div[data-baseweb="input"] { border:none !important; background:transparent !important; }
.st-key-composer .stFormSubmitButton button { border-radius:999px; }
.st-key-composer div[data-testid="stPopover"] button { border-radius:999px; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(
        f'<div class="fb-brand"><img src="{AVATAR}"><div><b>FitBuddy</b>'
        f'<span>with {COACH_NAME}, your judgement-free coach</span></div></div>',
        unsafe_allow_html=True,
    )


def now_time() -> str:
    return datetime.now().strftime("%I:%M %p").lstrip("0")


def split_messages(text: str) -> list[str]:
    """The coach separates its WhatsApp-style messages with a line containing only '---'."""
    parts = [p.strip() for p in re.split(r"\n\s*-{3,}\s*\n", "\n" + text.strip() + "\n")]
    parts = [p for p in parts if p]
    if len(parts) == 1 and len(parts[0]) > 350:  # model ignored the format: split by paragraph instead
        parts = [p.strip() for p in parts[0].split("\n\n") if p.strip()]
    return parts or [text.strip()]


def _md_to_html(text: str) -> str:
    """Safely turn the AI's simple markdown (bold, italics, bullet lists) into HTML."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    out, in_list = [], False
    for line in text.split("\n"):
        item = re.match(r"\s*(?:[-•*]|\d+[.)])\s+(.*)", line)
        if item:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{item.group(1)}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line + "<br>" if line.strip() else "<br>")
    if in_list:
        out.append("</ul>")
    result = "".join(out)
    while result.endswith("<br>"):
        result = result[:-4]
    return result


def _avatar_html() -> str:
    return f'<div class="av"><img src="{AVATAR}"></div>'


def chat_html(messages: list[dict], typing: bool = False, day_label: str | None = None,
              pop_from: int | None = None) -> str:
    """messages: [{"role": "user"|"assistant", "content": str, "time": "9:41 AM"}]
    Messages at index >= pop_from get the pop-in animation, one after another."""
    parts = [f'<div class="day-chip"><span>{html.escape(day_label)}</span></div>'] if day_label else []
    prev, delay = None, 0.0
    for i, m in enumerate(messages):
        who = "me" if m["role"] == "user" else "coach"
        first = who != prev
        pop = pop_from is not None and i >= pop_from
        style = f' style="--d:{delay:.2f}s"' if pop else ""
        if pop:
            delay += 0.45 if who == "coach" else 0.1
        avatar = (_avatar_html() if first else '<div class="av"></div>') if who == "coach" else ""
        parts.append(
            f'<div class="row {who}{" first" if first else ""}{" pop" if pop else ""}"{style}>{avatar}'
            f'<div class="bubble">{_md_to_html(m["content"])}<span class="time">{m.get("time", "")}</span></div></div>'
        )
        prev = who
    if typing:
        first = prev != "coach"
        avatar = _avatar_html() if first else '<div class="av"></div>'
        parts.append(f'<div class="row coach{" first" if first else ""} pop">{avatar}'
                     '<div class="bubble typing"><span></span><span></span><span></span></div></div>')
    return "".join(parts)


def chat_header(status: str = "online") -> str:
    return (f'<div class="chat-head"><img src="{AVATAR}"><div><b>{COACH_NAME} 🌿</b>'
            f'<span><span class="dot"></span>{status} · your judgement-free coach</span></div></div>')


def chat_window(messages: list[dict], typing: bool = False, header: bool = False,
                day_label: str | None = None, status: str = "online", pop_from: int | None = None) -> str:
    """The conversation, flowing on the page (no frame)."""
    head = chat_header(status) if header else ""
    return f'{head}<div class="chat-flow">{chat_html(messages, typing, day_label, pop_from)}</div>'


def scroll_to_bottom() -> None:
    """Scroll the page down to the newest message."""
    import streamlit.components.v1 as components
    components.html(
        """<script>
        const d = window.parent.document;
        const el = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main') || d.scrollingElement;
        setTimeout(() => { el.scrollTo({top: el.scrollHeight, behavior: 'smooth'});
                           window.parent.scrollTo({top: d.body.scrollHeight, behavior: 'smooth'}); }, 150);
        </script>""",
        height=0,
    )


def coach_bubbles(text: str) -> list[dict]:
    t = now_time()
    return [{"role": "assistant", "content": part, "time": t} for part in split_messages(text)]


# ---------- Cards, badges and Tulsi's voice ----------

CARD_CSS = """
<style>
.fb-card { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:16px; padding:.8rem 1rem; margin-bottom:.6rem; }
.fb-card .title { font-weight:700; color:var(--purple-dark); margin-bottom:.2rem; }
.fb-card .sub { color:var(--muted); font-size:.9rem !important; }
.water { font-size:1.5rem; letter-spacing:.1rem; }
.badges { display:grid; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); gap:.6rem; }
.badge { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:14px; padding:.7rem .5rem; text-align:center; }
.badge .e { font-size:2rem; line-height:2.4rem; }
.badge .n { font-weight:700; font-size:.85rem !important; color:var(--ink); }
.badge .d { font-size:.72rem !important; color:var(--muted); }
.badge.locked { background:#F4F1F8; }
.badge.locked .e { filter: grayscale(1); opacity:.35; }
.badge.locked .n { color:var(--muted); }
.growbar { height:.7rem; background:#EDE6F6; border-radius:99px; overflow:hidden; margin:.3rem 0 .2rem; }
.growbar div { height:100%; background: linear-gradient(90deg, #9B6BD6, #E58FC7); border-radius:99px; }
.win { background:#FFFFFF; border-left:4px solid #C38BEA; border-radius:10px; padding:.5rem .8rem; margin:.35rem 0; }
.win small { color:var(--muted); }
</style>
"""


def inject_card_css() -> None:
    st.markdown(CARD_CSS, unsafe_allow_html=True)


def card(title: str, body: str = "") -> str:
    return f'<div class="fb-card"><div class="title">{title}</div><div class="sub">{body}</div></div>'


def badges_html(badges: list[dict]) -> str:
    cells = "".join(
        f'<div class="badge{"" if b["earned"] else " locked"}"><div class="e">{b["emoji"]}</div>'
        f'<div class="n">{html.escape(b["name"])}</div><div class="d">{html.escape(b["desc"])}</div></div>'
        for b in badges
    )
    return f'<div class="badges">{cells}</div>'


def growbar(pct: float) -> str:
    return f'<div class="growbar"><div style="width:{max(2, min(100, pct)):.0f}%"></div></div>'


def speech(text: str) -> bytes | None:
    """Tulsi's voice: turns text into an MP3 with gTTS (Indian English accent).
    Returns None if gTTS isn't installed or there's no internet."""
    try:
        from gtts import gTTS
    except ImportError:
        return None
    clean = re.sub(r"[*_#>`]|---", " ", text)
    clean = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", clean)  # drop emojis
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return None
    try:
        buf = io.BytesIO()
        gTTS(clean, lang="en", tld="co.in").write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


# ---------- Page headers, stat tiles and charts ----------

PAGE_CSS = """
<style>
.hero { background: linear-gradient(135deg, #4E2A84 0%, #7B3FBF 60%, #C38BEA 100%); color:#fff;
        border-radius: 20px; padding: 1.1rem 1.4rem; margin-bottom: 1.2rem; display:flex; align-items:center; gap:1rem; }
.hero .e { font-size: 2.6rem; line-height:1; }
.hero h1 { color:#fff !important; margin:0 !important; padding:0 !important; font-size:1.7rem !important; }
.hero p { color:#EFE6FB !important; margin:.15rem 0 0 0 !important; font-size:.95rem !important; }
.tiles { display:grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap:.7rem; margin:.4rem 0 1rem; }
.tile { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:16px; padding:.8rem 1rem; }
.tile .l { font-size:.78rem !important; color:var(--muted); font-weight:600; }
.tile .v { font-size:1.6rem !important; font-weight:800; color:var(--ink); line-height:1.25; }
.tile .s { font-size:.75rem !important; color:var(--muted); }
.chart-card { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:18px; padding:.9rem 1rem .4rem; margin-bottom:.9rem; }
.chart-card .t { font-weight:700; color:var(--ink); }
.chart-card .st { font-size:.8rem !important; color:var(--muted); margin-bottom:.2rem; }
.chart-card svg { width:100%; height:auto; display:block; }
.foods { display:grid; grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); gap:.7rem; margin:.5rem 0; }
.food { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:16px; padding:.8rem .9rem; }
.food .n { font-weight:700; color:var(--ink); }
.food .p { font-size:.8rem !important; color:var(--muted); margin-bottom:.4rem; }
.food .k { font-size:1.35rem !important; font-weight:800; color:var(--purple-dark); }
.chips { display:flex; flex-wrap:wrap; gap:.3rem; margin-top:.35rem; }
.chip { font-size:.72rem !important; padding:.15rem .5rem; border-radius:99px; background:#F1EAFB; color:#4E2A84; font-weight:600; }
.chip.c { background:#FDF0E1; color:#8A4B0F; } .chip.f { background:#FDE8F2; color:#8A1F55; } .chip.fi { background:#E7F4EC; color:#1E6B45; }
.meal { display:flex; gap:.9rem; align-items:flex-start; background:#FFFFFF; border:1px solid #E6DDF3;
        border-radius:16px; padding:.7rem .9rem; margin:.45rem 0; }
.meal .i { font-size:1.6rem; width:2.6rem; height:2.6rem; border-radius:12px; background:#F1EAFB;
           display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.meal .m { flex:1; } .meal .m b { color:var(--ink); } .meal .m div { font-size:.85rem !important; color:var(--muted); }
.meal .kc { font-weight:800; color:var(--purple-dark); white-space:nowrap; }
.tip { background:#FFF8E6; border:1px solid #F6E2A8; border-radius:14px; padding:.6rem .9rem; margin:.5rem 0; }
</style>
"""


def inject_page_css() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def hero(emoji: str, title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="hero"><div class="e">{emoji}</div><div><h1>{html.escape(title)}</h1>'
                f'<p>{subtitle}</p></div></div>', unsafe_allow_html=True)


def tiles(items: list[tuple[str, str, str]]) -> str:
    """items: (label, value, small text)"""
    cells = "".join(f'<div class="tile"><div class="l">{l}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
                    for l, v, s in items)
    return f'<div class="tiles">{cells}</div>'


def line_chart_svg(points: list[tuple], unit: str = "", decimals: int = 0, color: str = "#7B3FBF",
                   wide: bool = False) -> str:
    """A soft area + line chart drawn in SVG. points: [(datetime, value), ...] sorted by date.
    Hover any dot to see its date and value."""
    pts = [(d, float(v)) for d, v in points if v == v]  # drop NaN
    if not pts:
        return ""
    W, H, L, R, T, B = (1180, 300, 50, 24, 24, 32) if wide else (580, 230, 46, 18, 22, 30)
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or max(abs(hi) * 0.1, 1)
    lo, hi = lo - pad, hi + pad
    if min(vals) >= 0 and lo < 0:
        lo = 0
    t0, t1 = pts[0][0].timestamp(), pts[-1][0].timestamp()
    span = (t1 - t0) or 1

    def x(d):
        return L + (W - L - R) * ((d.timestamp() - t0) / span if len(pts) > 1 else 0.5)

    def y(v):
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    fmt = lambda v: f"{v:,.{decimals}f}"
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">',
           f'<defs><linearGradient id="g{abs(hash(unit)) % 9999}" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{color}" stop-opacity=".28"/><stop offset="1" stop-color="{color}" stop-opacity="0"/>'
           '</linearGradient></defs>']
    # gridlines + y labels
    for i in range(4):
        v = lo + (hi - lo) * i / 3
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#EEE8F5" stroke-width="1"/>'
                   f'<text x="{L - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#9A90AE">{fmt(v)}</text>')
    # x labels (up to 6)
    step = max(1, len(pts) // 6)
    labelled = pts[::step]
    for i, (d, _) in enumerate(labelled):
        anchor = "start" if i == 0 else "end" if (i == len(labelled) - 1 and x(d) > W - R - 30) else "middle"
        out.append(f'<text x="{x(d):.1f}" y="{H - 8}" text-anchor="{anchor}" font-size="11" fill="#9A90AE">{d.strftime("%b %y" if span > 86400 * 120 else "%d %b")}</text>')
    line = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in pts)
    gid = f"g{abs(hash(unit)) % 9999}"
    if len(pts) > 1:
        out.append(f'<polygon points="{x(pts[0][0]):.1f},{H - B} {line} {x(pts[-1][0]):.1f},{H - B}" fill="url(#{gid})"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    for d, v in pts:
        out.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="{4 if len(pts) < 40 else 2.5}" fill="#fff" stroke="{color}" stroke-width="2">'
                   f'<title>{d.strftime("%d %b %Y")}: {fmt(v)} {unit}</title></circle>')
    # highlight latest value
    d, v = pts[-1]
    out.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="6" fill="{color}"/>'
               f'<text x="{min(x(d), W - R - 4):.1f}" y="{max(y(v) - 12, 12):.1f}" text-anchor="end" font-size="13" '
               f'font-weight="700" fill="#4E2A84">{fmt(v)} {unit}</text>')
    out.append("</svg>")
    return "".join(out)


def chart_card(title: str, subtitle: str, svg: str) -> str:
    return f'<div class="chart-card"><div class="t">{title}</div><div class="st">{subtitle}</div>{svg}</div>'


MEAL_ICONS = {"Breakfast": "🌅", "Lunch": "☀️", "Snack": "🍎", "Dinner": "🌙"}


def food_cards(items: list[dict]) -> str:
    cells = []
    for i in items:
        cells.append(
            f'<div class="food"><div class="n">{html.escape(str(i.get("name", "")))}</div>'
            f'<div class="p">{html.escape(str(i.get("portion", "")))}</div>'
            f'<div class="k">{int(float(i.get("calories") or 0))} kcal</div><div class="chips">'
            f'<span class="chip">Protein {float(i.get("protein_g") or 0):g}g</span>'
            f'<span class="chip c">Carbs {float(i.get("carbs_g") or 0):g}g</span>'
            f'<span class="chip f">Fat {float(i.get("fat_g") or 0):g}g</span>'
            f'<span class="chip fi">Fibre {float(i.get("fibre_g") or 0):g}g</span></div></div>')
    return f'<div class="foods">{"".join(cells)}</div>'


def meal_row(meal: dict) -> str:
    foods = ", ".join(html.escape(str(x.get("name", ""))) for x in meal.get("items", []))
    return (f'<div class="meal"><div class="i">{MEAL_ICONS.get(meal.get("meal"), "🍽️")}</div>'
            f'<div class="m"><b>{html.escape(str(meal.get("meal", "Meal")))}</b><div>{foods}</div></div>'
            f'<div class="kc">{int(meal.get("calories", 0))} kcal</div></div>')
