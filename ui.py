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
html { font-size: 18px !important; }
/* the whole app is scaled to the window width by ui.auto_size() */
/* zoom the CONTENT inside the scroll area (not the scroll area itself), so scrolling keeps working */
.block-container, [data-testid="stMainBlockContainer"], [data-testid="stSidebarContent"],
div[role="dialog"], [data-testid="stPopoverBody"] { zoom: var(--fbz, 1); }
/* no page headers any more, so start content right at the top */
header[data-testid="stHeader"] { background: transparent !important; height: 2.6rem !important; pointer-events: none; }
header[data-testid="stHeader"] button, header[data-testid="stHeader"] a { pointer-events: auto; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 1.2rem !important; padding-bottom: 3rem !important; }
/* on computer screens, keep columns side by side instead of letting them wrap onto new lines */
@media (min-width: 900px) {
  [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
  [data-testid="stColumn"], [data-testid="column"] { min-width: 0 !important; }
}
.stApp { overflow-x: hidden; }
.block-container { padding-left: 3rem; padding-right: 3rem;
                   max-width: 100% !important; margin: 0 auto; }
/* the sidebar grows with the app's scale, so menu items don't wrap; you can still drag it wider */
section[data-testid="stSidebar"] { min-width: calc(16rem * var(--fbz, 1)) !important; max-width: none !important; }
section[data-testid="stSidebar"] label p { white-space: nowrap; }
/* Tulsi in the corner scales with the app too */
#tulsi-mascot { zoom: var(--fbz, 1); }
/* invisible blocks (style sheets, 0-height scripts) shouldn't take up space at the top of the page */
[data-testid="stElementContainer"]:has(iframe[height="0"]), .element-container:has(iframe[height="0"]),
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child),
.element-container:has([data-testid="stMarkdownContainer"] > style:only-child) { display: none !important; }
section[data-testid="stSidebar"] label p { font-size: 1.05rem !important; }
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
  position:relative; max-width: 60%; padding: .6rem .9rem; border-radius: 1.1rem;
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
    text = re.sub(r"(?im)^\s*\**PLAN\**\s*:.*$", "", text).strip()  # the app reads PLAN lines; people don't need to see them
    t = now_time()
    return [{"role": "assistant", "content": part, "time": t} for part in split_messages(text)]


# ---------- Cards, badges and Tulsi's voice ----------

CARD_CSS = """
<style>
.fb-card { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:16px; padding:.8rem 1rem; margin-bottom:.6rem; }
.fb-card .title { font-weight:700; color:var(--purple-dark); margin-bottom:.2rem; }
.fb-card .sub { color:var(--muted); font-size:.9rem !important; }
.water { font-size:1.5rem; letter-spacing:.1rem; }
.badges { display:grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap:.7rem; }
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
                   wide: bool = False, trend: list[tuple] | None = None) -> str:
    """A soft area + line chart drawn in SVG. points: [(datetime, value), ...] sorted by date.
    Hover any dot to see its date and value.
    With `trend`, the points are shown as faint dots and the trend is the bold line (used for weight)."""
    pts = [(d, float(v)) for d, v in points if v == v]  # drop NaN
    if not pts:
        return ""
    raw_pts = pts
    if trend:
        pts = [(d, float(v)) for d, v in trend]
    W, H, L, R, T, B = (1180, 300, 50, 24, 24, 32) if wide else (580, 230, 46, 18, 22, 30)
    vals = [v for _, v in pts] + [v for _, v in raw_pts]
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
    if trend:  # the actual weigh-ins, as faint dots behind the trend line
        for d, v in raw_pts:
            out.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="4" fill="{color}" opacity=".25">'
                       f'<title>{d.strftime("%d %b %Y")}: weighed {fmt(v)} {unit}</title></circle>')
    for d, v in pts:
        label = "7-day average" if trend else ""
        out.append(f'<circle cx="{x(d):.1f}" cy="{y(v):.1f}" r="{4 if len(pts) < 40 else 2.5}" fill="#fff" stroke="{color}" stroke-width="2">'
                   f'<title>{d.strftime("%d %b %Y")}: {label} {fmt(v)} {unit}</title></circle>')
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
    """One card per food. Items can carry "servings" (shown if not 1) and "warn" (a sanity-check message)."""
    cells = []
    for i in items:
        servings = float(i.get("servings") or 1)
        serving_note = f' <span style="font-size:.8rem;color:#786E8C">× {servings:g} serving</span>' if servings != 1 else ""
        warning = (f'<div style="margin-top:.5rem;font-size:.8rem;color:#8A4B0F">⚠️ {html.escape(i["warn"])}</div>'
                   if i.get("warn") else "")
        cells.append(
            f'<div class="food"><div class="n">{html.escape(str(i.get("name", "")))}</div>'
            f'<div class="p">{html.escape(str(i.get("portion", "")))}</div>'
            f'<div class="k">{int(float(i.get("calories") or 0))} kcal{serving_note}</div><div class="chips">'
            f'<span class="chip">Protein {float(i.get("protein_g") or 0):g}g</span>'
            f'<span class="chip c">Carbs {float(i.get("carbs_g") or 0):g}g</span>'
            f'<span class="chip f">Fat {float(i.get("fat_g") or 0):g}g</span>'
            f'<span class="chip fi">Fibre {float(i.get("fibre_g") or 0):g}g</span></div>{warning}</div>')
    return f'<div class="foods">{"".join(cells)}</div>'


def meal_row(meal: dict) -> str:
    foods = ", ".join(html.escape(str(x.get("name", ""))) for x in meal.get("items", []))
    return (f'<div class="meal"><div class="i">{MEAL_ICONS.get(meal.get("meal"), "🍽️")}</div>'
            f'<div class="m"><b>{html.escape(str(meal.get("meal", "Meal")))}</b><div>{foods}</div></div>'
            f'<div class="kc">{int(meal.get("calories", 0))} kcal</div></div>')


# ---------- Tulsi the mascot: bounces in the corner, smiles when you click her ----------

MASCOT_SVG = """<svg viewBox="0 0 120 130" xmlns="http://www.w3.org/2000/svg">
  <ellipse class="t-shadow" cx="60" cy="124" rx="30" ry="5" fill="#2A2140" opacity=".12"/>
  <g class="t-body">
    <path d="M60 52 C60 42 60 36 60 30" stroke="#2F8F5B" stroke-width="5" stroke-linecap="round" fill="none"/>
    <path d="M60 36 C46 20 26 24 24 36 C38 46 52 44 60 36Z" fill="#5CC08A"/>
    <g class="t-wave"><path d="M60 32 C72 14 94 16 97 29 C84 41 68 40 60 32Z" fill="#3FAE74"/></g>
    <ellipse cx="60" cy="84" rx="38" ry="34" fill="#6CCB94"/>
    <ellipse cx="60" cy="92" rx="28" ry="20" fill="#86D8A8" opacity=".55"/>
    <g class="t-normal">
      <circle cx="47" cy="78" r="5" fill="#1E3B2C"/><circle cx="73" cy="78" r="5" fill="#1E3B2C"/>
      <circle cx="48.8" cy="76.2" r="1.7" fill="#fff"/><circle cx="74.8" cy="76.2" r="1.7" fill="#fff"/>
      <ellipse cx="37" cy="90" rx="6.5" ry="3.8" fill="#F59AA6" opacity=".8"/>
      <ellipse cx="83" cy="90" rx="6.5" ry="3.8" fill="#F59AA6" opacity=".8"/>
      <path d="M52 91 Q60 98 68 91" stroke="#1E3B2C" stroke-width="3.5" fill="none" stroke-linecap="round"/>
    </g>
    <g class="t-happy">
      <path d="M41 80 Q47 72 53 80" stroke="#1E3B2C" stroke-width="3.8" fill="none" stroke-linecap="round"/>
      <path d="M67 80 Q73 72 79 80" stroke="#1E3B2C" stroke-width="3.8" fill="none" stroke-linecap="round"/>
      <ellipse cx="36" cy="90" rx="8" ry="4.8" fill="#F27E93"/>
      <ellipse cx="84" cy="90" rx="8" ry="4.8" fill="#F27E93"/>
      <path d="M48 89 Q60 89 72 89 Q70 106 60 106 Q50 106 48 89Z" fill="#1E3B2C"/>
      <path d="M53 99 Q60 95 67 99 Q64 105 60 105 Q56 105 53 99Z" fill="#F59AA6"/>
    </g>
  </g>
</svg>"""

MASCOT_CSS = """
#tulsi-mascot { position: fixed; right: 1.6rem; bottom: 1.4rem; z-index: 9999; width: 7.5rem;
                cursor: pointer; user-select: none; -webkit-tap-highlight-color: transparent; }
#tulsi-mascot svg { width: 100%; height: auto; display: block; overflow: visible; }
#tulsi-mascot .t-body { transform-origin: 60px 118px; animation: t-jump 2.2s ease-in-out infinite; }
#tulsi-mascot .t-shadow { transform-origin: 60px 124px; animation: t-shadow 2.2s ease-in-out infinite; }
#tulsi-mascot .t-wave { transform-origin: 60px 33px; animation: t-wave 1.1s ease-in-out infinite; }
#tulsi-mascot .t-happy { display: none; }
#tulsi-mascot.happy .t-normal { display: none; }
#tulsi-mascot.happy .t-happy { display: inline; }
#tulsi-mascot.happy .t-body { animation: t-joy .6s ease-in-out 2; }
#tulsi-mascot .t-bubble { position: absolute; right: 85%; bottom: 78%; white-space: nowrap; background: #FFFFFF;
  color: #2A2140; font: 600 1rem/1.3 "Source Sans Pro", sans-serif; padding: .55rem .9rem; border-radius: 1rem 1rem .25rem 1rem;
  box-shadow: 0 6px 20px rgba(78,42,132,.18); border: 1px solid #E6DDF3; animation: t-pop .5s cubic-bezier(.2,.9,.3,1.3) both; }
#tulsi-mascot .t-heart { position: absolute; font-size: 1.3rem; bottom: 70%; opacity: 0; pointer-events: none; }
#tulsi-mascot.happy .t-heart { animation: t-float 1.4s ease-out forwards; }
#tulsi-mascot .t-heart:nth-of-type(1) { left: 10%; animation-delay: 0s; }
#tulsi-mascot .t-heart:nth-of-type(2) { left: 45%; animation-delay: .15s; }
#tulsi-mascot .t-heart:nth-of-type(3) { left: 75%; animation-delay: .3s; }
@keyframes t-jump { 0%, 60%, 100% { transform: translateY(0) scale(1, 1); }
  8% { transform: translateY(0) scale(1.08, .9); } 25% { transform: translateY(-26px) scale(.95, 1.06); }
  42% { transform: translateY(0) scale(1.07, .93); } 50% { transform: translateY(0) scale(1, 1); } }
@keyframes t-shadow { 0%, 60%, 100% { transform: scale(1); opacity: .12; } 25% { transform: scale(.65); opacity: .06; } }
@keyframes t-wave { 0%, 100% { transform: rotate(0deg); } 50% { transform: rotate(-22deg); } }
@keyframes t-joy { 0%, 100% { transform: translateY(0) rotate(0); } 25% { transform: translateY(-14px) rotate(-6deg); }
  75% { transform: translateY(-14px) rotate(6deg); } }
@keyframes t-pop { 0% { opacity: 0; transform: translateY(8px) scale(.85); } 100% { opacity: 1; transform: none; } }
@keyframes t-float { 0% { opacity: 0; transform: translateY(0) scale(.6); } 20% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-70px) scale(1.2); } }
"""


def mascot(name: str = "", show: bool = True, lift: bool = False) -> None:
    """Puts Tulsi in the corner of the page. She bounces and waves; click her and she smiles.
    lift=True raises her a little (on the chat page, so she doesn't cover the message bar)."""
    import json
    import streamlit.components.v1 as components
    hello = f"Hi {name}! 👋" if name else "Hi there! 👋"
    cheers = ["Yay, you found me! 🌸", "You've got this! 💜", "Proud of you! 🌿", "Sip some water? 💧",
              "One step at a time 🌱", "You're doing amazing ✨", "Hehe, that tickles! 😄"]
    components.html(
        f"""<script>
        const d = window.parent.document;
        if (!d.getElementById('tulsi-mascot-style')) {{
          const s = d.createElement('style'); s.id = 'tulsi-mascot-style'; s.textContent = {json.dumps(MASCOT_CSS)};
          d.head.appendChild(s);
        }}
        let m = d.getElementById('tulsi-mascot');
        if (!m) {{
          m = d.createElement('div'); m.id = 'tulsi-mascot'; m.title = 'Click me!';
          m.innerHTML = '<div class="t-bubble"></div><span class="t-heart">💜</span><span class="t-heart">🌸</span>'
                      + '<span class="t-heart">💜</span>' + {json.dumps(MASCOT_SVG)};
          d.body.appendChild(m);
        }}
        // The click code is created in the MAIN page (w.Function), not in this helper frame. Streamlit replaces
        // this frame on every rerun, and code that belonged to an old frame stops working.
        const w = window.parent;
        m.onclick = new w.Function(`
          const m = this, b = m.querySelector('.t-bubble');
          const cheers = JSON.parse(m.dataset.cheers || '[]');
          m.classList.remove('happy'); void m.offsetWidth; m.classList.add('happy');
          b.textContent = cheers[Math.floor(Math.random() * cheers.length)] || 'Hehe! 😄';
          b.style.animation = 'none'; void b.offsetWidth; b.style.animation = '';
          clearTimeout(m._t);
          m._t = setTimeout(() => {{ m.classList.remove('happy'); b.textContent = m.dataset.hello; }}, 3000);
        `);
        m.dataset.hello = {json.dumps(hello)};
        m.dataset.cheers = {json.dumps(json.dumps(cheers))};
        if (!m.classList.contains('happy')) m.querySelector('.t-bubble').textContent = m.dataset.hello;
        m.style.display = {json.dumps("block" if show else "none")};
        m.style.bottom = {json.dumps("7.5rem" if lift else "1.4rem")};
        </script>""",
        height=0,
    )


# ---------- More breathing room between everything ----------

SPACING_CSS = """
<style>
.block-container [data-testid="stVerticalBlock"] { gap: 1.3rem; }
.block-container [data-testid="stHorizontalBlock"] { gap: 1.6rem; }
.hero { margin-bottom: 1.8rem !important; }
.section-label { margin: 1.6rem 0 .6rem !important; }
.fb-card, .tile, .chart-card, .food, .meal { margin-bottom: .4rem; }
div[data-testid="stForm"] { padding: 1.4rem 1.6rem !important; }
div[data-testid="stExpander"] details { padding: .3rem .4rem; }
.soft-panel { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:20px; padding:1.3rem 1.5rem; }
.soft-panel h3 { margin-top:0 !important; }
</style>
"""


def inject_spacing_css() -> None:
    st.markdown(SPACING_CSS, unsafe_allow_html=True)


def section(title: str, subtitle: str = "") -> None:
    """A clear section heading with space above it."""
    sub = f'<div style="color:var(--muted);font-size:.92rem;margin-top:.2rem">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div style="margin:1.8rem 0 .5rem"><div style="font-size:1.35rem;font-weight:800;color:var(--ink)">'
                f'{title}</div>{sub}</div>', unsafe_allow_html=True)


# ---------- Home page: Tulsi under a rainbow ----------

HOME_CSS = """
<style>
.home { position:relative; text-align:center; padding: .5rem 0 0; }
.home .sky { position:relative; width:min(40rem, 94%); margin:0 auto; }
.home .sky svg { width:100%; height:auto; display:block; overflow:visible; }
.home .arc { fill:none; stroke-linecap:round; stroke-dasharray: 1000; stroke-dashoffset: 1000;
             animation: draw-arc 1.6s ease-out forwards; }
.home .cloud { animation: drift 6s ease-in-out infinite alternate; }
.home .tulsi { position:absolute; left:50%; bottom:2%; width:30%; transform:translateX(-50%); }
.home .tulsi .t-body { transform-origin: 60px 118px; animation: home-jump 2.2s ease-in-out infinite; }
.home .tulsi .t-shadow { transform-origin: 60px 124px; animation: home-shadow 2.2s ease-in-out infinite; }
.home .tulsi .t-wave { transform-origin: 60px 33px; animation: home-wave 1.1s ease-in-out infinite; }
.home .tulsi .t-happy { display:none; }
.home h1 { font-size: 3rem !important; color: var(--ink) !important; margin: 1.2rem 0 .2rem !important;
           animation: rise .8s .9s both; }
.home p.lead { font-size: 1.3rem !important; color: var(--muted) !important; animation: rise .8s 1.1s both; }
.home .chips { display:flex; justify-content:center; gap:.8rem; flex-wrap:wrap; margin: 1rem 0 .4rem; animation: rise .8s 1.3s both; }
.home .chips span { background:#FFFFFF; border:1px solid #E6DDF3; border-radius:99px; padding:.55rem 1.2rem; font-weight:600; color:#4E2A84; font-size:1.05rem !important; }
@keyframes draw-arc { to { stroke-dashoffset: 0; } }
@keyframes drift { from { transform: translateX(-8px); } to { transform: translateX(8px); } }
@keyframes rise { from { opacity:0; transform: translateY(14px); } to { opacity:1; transform:none; } }
@keyframes home-jump { 0%, 60%, 100% { transform: translateY(0) scale(1,1); } 8% { transform: translateY(0) scale(1.08,.9); }
  25% { transform: translateY(-24px) scale(.95,1.06); } 42% { transform: translateY(0) scale(1.07,.93); } 50% { transform: translateY(0); } }
@keyframes home-shadow { 0%, 60%, 100% { transform: scale(1); opacity:.12; } 25% { transform: scale(.65); opacity:.06; } }
@keyframes home-wave { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(-22deg); } }
.st-key-letsgo, .st-key-letsgo .stButton, .st-key-letsgo [data-testid="stButton"] { display:flex; justify-content:center; width:100%; }
.st-key-letsgo button { width: 100% !important; font-size: 1.25rem !important; padding: .8rem 2.6rem !important; border-radius: 999px !important;
                        background: linear-gradient(135deg, #7B3FBF, #C38BEA) !important; border: none !important; color: #fff !important;
                        box-shadow: 0 10px 28px rgba(123,63,191,.35); animation: rise .8s 1.5s both; }
.st-key-letsgo button p { font-size: 1.25rem !important; color:#fff !important; font-weight:700; }
</style>
"""

RAINBOW_COLORS = ["#F28B82", "#F7B267", "#F9DC5C", "#8BD3A0", "#7CC4F5", "#9B8CF0", "#C38BEA"]


def home_html(name: str, chips: list[str]) -> str:
    arcs = "".join(
        f'<path class="arc" d="M{60 + i * 16} 300 A{240 - i * 16} {240 - i * 16} 0 0 1 {540 - i * 16} 300" '
        f'stroke="{c}" stroke-width="15" style="animation-delay:{i * 0.12:.2f}s"/>'
        for i, c in enumerate(RAINBOW_COLORS))
    cloud = lambda x, y, s: (f'<g transform="translate({x} {y}) scale({s})"><g class="cloud" fill="#FFFFFF">'
                             '<ellipse cx="0" cy="0" rx="46" ry="26"/><ellipse cx="34" cy="-14" rx="34" ry="26"/>'
                             '<ellipse cx="-34" cy="-8" rx="30" ry="22"/><ellipse cx="62" cy="4" rx="28" ry="18"/></g></g>')
    sparkles = "".join(f'<text x="{x}" y="{y}" font-size="{s}" opacity=".9">✨</text>'
                       for x, y, s in [(110, 70, 22), (470, 60, 18), (300, 30, 16), (520, 170, 14)])
    sky = (f'<svg viewBox="0 0 600 330" xmlns="http://www.w3.org/2000/svg">{arcs}'
           f'{cloud(75, 300, 1.05)}{cloud(525, 300, 1.05)}{sparkles}</svg>')
    who = html.escape(name) if name else "there"
    chip_html = "".join(f"<span>{html.escape(c)}</span>" for c in chips)
    return (f'{HOME_CSS}<div class="home"><div class="sky">{sky}<div class="tulsi">{MASCOT_SVG}</div></div>'
            f'<h1>Hi {who}! Let\'s start 🌈</h1>'
            f'<p class="lead">I\'m Tulsi, and I\'m so happy to see you. Every small step counts today.</p>'
            f'<div class="chips">{chip_html}</div></div>')


# ---------- Symptoms: a 30-day grid and a by-phase grid ----------

def heat_grid_svg(row_labels: list[str], col_labels: list[str], values: list[list[float | None]],
                  max_value: float = 3.0, cell: int = 26, label_w: int = 110, col_every: int = 1) -> str:
    """Rows x columns of rounded squares; darker purple = stronger. None = not logged (dotted)."""
    lines = max(len(lab.split("|")) for lab in col_labels)  # "Period|5 days" = two lines
    top = 28 + 13 * (lines - 1)
    W = label_w + len(col_labels) * cell + 10
    H = top + len(row_labels) * cell + 10
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" '
           f'style="width:100%;max-width:{W * 1.6:.0f}px;height:auto;display:block">']
    for j, lab in enumerate(col_labels):
        if j % col_every == 0:
            spans = "".join(f'<tspan x="{label_w + j * cell + cell / 2}" dy="{0 if k == 0 else 13}">{html.escape(part)}</tspan>'
                            for k, part in enumerate(lab.split("|")))
            out.append(f'<text y="16" text-anchor="middle" font-size="10" fill="#9A90AE">{spans}</text>')
    for i, lab in enumerate(row_labels):
        y = top + i * cell
        out.append(f'<text x="{label_w - 10}" y="{y + cell / 2 + 4}" text-anchor="end" font-size="12" fill="#4E2A84">{html.escape(lab)}</text>')
        for j, v in enumerate(values[i]):
            x = label_w + j * cell
            if v is None:
                out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cell - 6}" height="{cell - 6}" rx="6" fill="none" stroke="#E6DDF3" stroke-dasharray="2 2"/>')
                continue
            t = max(0.0, min(1.0, v / max_value))
            r, g, b = (int(241 + (123 - 241) * t), int(234 + (63 - 234) * t), int(251 + (191 - 251) * t))
            out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cell - 6}" height="{cell - 6}" rx="6" fill="rgb({r},{g},{b})">'
                       f'<title>{html.escape(lab)} · {html.escape(col_labels[j])}: {v:.1f}</title></rect>')
    out.append("</svg>")
    return "".join(out)


def bars_html(counts: dict, total: int | None = None) -> str:
    """Simple horizontal bars for small counts (e.g. cravings by time of day)."""
    if not counts:
        return ""
    top = max(counts.values()) or 1
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:.8rem;margin:.45rem 0">'
        f'<div style="width:9.5rem;color:var(--ink)">{html.escape(str(k))}</div>'
        f'<div style="flex:1;background:#F1EAFB;border-radius:99px;height:.8rem">'
        f'<div style="width:{v / top * 100:.0f}%;height:100%;border-radius:99px;background:linear-gradient(90deg,#9B6BD6,#E58FC7)"></div></div>'
        f'<div style="width:2.5rem;text-align:right;font-weight:700;color:#4E2A84">{v}</div></div>'
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    return f'<div class="soft-panel">{rows}</div>'


# ---------- Craving SOS: breathe with Tulsi ----------

BREATHE_HTML = """
<style>
.breathe { display:flex; flex-direction:column; align-items:center; gap:1rem; padding: 1.4rem 0; }
.breathe .ball { width: 9rem; height: 9rem; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #E9DCFA, #9B6BD6); box-shadow: 0 0 0 0 rgba(155,107,214,.35);
  animation: breathe 8s ease-in-out infinite; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; }
.breathe .ball { position: relative; }
.breathe .ball b { position:absolute; animation: say-in 8s steps(1) infinite; }
.breathe .ball b.out { animation-name: say-out; }
@keyframes breathe { 0%, 100% { transform: scale(.7); box-shadow: 0 0 0 0 rgba(155,107,214,.35); }
                     50% { transform: scale(1.1); box-shadow: 0 0 0 1.6rem rgba(155,107,214,0); } }
@keyframes say-in { 0% { opacity:1; } 50% { opacity:0; } }
@keyframes say-out { 0% { opacity:0; } 50% { opacity:1; } }
</style>
<div class="breathe"><div class="ball"><b class="in">Breathe in</b><b class="out">Breathe out</b></div>
<div style="color:var(--muted);text-align:center;max-width:22rem">Breathe with the circle for one minute.
Cravings rise and fall like a wave, so you don't have to act on this one straight away.</div></div>
"""


# ---------- Prettier controls: number boxes, sliders, choice pills, buttons, cards ----------
# These style Streamlit's own widgets. If a future Streamlit version renames something,
# the widget simply keeps its normal look, so nothing breaks.

WIDGET_CSS = """
<style>
/* soft pastel glow behind every page */
.stApp { background:
  radial-gradient(circle at 8% 0%, #F1E4FF 0, rgba(241,228,255,0) 38%),
  radial-gradient(circle at 95% 12%, #FDE6F3 0, rgba(253,230,243,0) 32%),
  radial-gradient(circle at 50% 100%, #E6F6EE 0, rgba(230,246,238,0) 40%), #FAF7FD; }

/* labels */
.stApp [data-testid="stWidgetLabel"] p { font-weight: 700 !important; color: #4E2A84 !important; }

/* ----- number boxes with big round - / + buttons ----- */
[data-testid="stNumberInputContainer"] { background:#FFFFFF !important; border:1.5px solid #E6DDF3 !important;
  border-radius: 18px !important; min-height: 3.4rem; align-items:center; padding-right:.3rem;
  box-shadow: 0 2px 10px rgba(78,42,132,.05); transition: border-color .2s, box-shadow .2s; }
[data-testid="stNumberInputContainer"]:focus-within { border-color:#9B6BD6 !important; box-shadow: 0 0 0 4px rgba(155,107,214,.15); }
[data-testid="stNumberInput"] input { background:#FFFFFF !important; font-size: 1.25rem !important; font-weight: 800 !important;
  color:#2A2140 !important; padding-left: 1rem !important; }
[data-testid="stNumberInput"] div[data-baseweb="input"] { background: transparent !important; border: none !important; }
button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"] {
  width: 2.7rem !important; height: 2.7rem !important; min-width: 2.7rem; margin: 0 .2rem !important; border-radius: 50% !important;
  border: none !important; background: #F1EAFB !important; color: #7B3FBF !important; transition: transform .12s, background .2s; }
button[data-testid="stNumberInputStepUp"] { background: linear-gradient(135deg, #7B3FBF, #9B5DE5) !important; color:#FFFFFF !important; }
button[data-testid="stNumberInputStepDown"]:hover { background:#E3D3F8 !important; }
button[data-testid="stNumberInputStepUp"]:hover { filter: brightness(1.1); }
button[data-testid="stNumberInputStepDown"]:active, button[data-testid="stNumberInputStepUp"]:active { transform: scale(.9); }
button[data-testid="stNumberInputStepDown"] svg, button[data-testid="stNumberInputStepUp"] svg { width: 1.25rem; height: 1.25rem; }

/* ----- text boxes ----- */
[data-testid="stTextInput"] div[data-baseweb="input"], [data-testid="stTextArea"] div[data-baseweb="textarea"],
[data-testid="stDateInput"] div[data-baseweb="input"], div[data-baseweb="select"] > div {
  background:#FFFFFF !important; border:1.5px solid #E6DDF3 !important; border-radius: 16px !important; min-height: 3.1rem; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stDateInput"] input {
  background:#FFFFFF !important; font-size: 1.05rem !important; }

/* ----- sliders: thick track, big glowing handle ----- */
[data-testid="stSlider"] { padding: .3rem .4rem 0; }
[data-testid="stSlider"] div[data-baseweb="slider"] > div > div:not([role="slider"]) { height: .6rem !important; border-radius: 99px !important; }
[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] { width: 1.9rem !important; height: 1.9rem !important; background: #FFFFFF !important;
  border: 5px solid #7B3FBF !important; box-shadow: 0 4px 14px rgba(123,63,191,.4) !important; transition: transform .15s; }
[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"]:hover { transform: scale(1.12); }
[data-testid="stSliderThumbValue"] { background: #7B3FBF; color: #FFFFFF !important; padding: .1rem .55rem; border-radius: 99px;
  font-weight: 800; top: -2.1rem !important; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { font-weight: 700; color: #9A90AE; }

/* ----- choices (radio) as pills, in the page (not the sidebar menu) ----- */
[data-testid="stMain"] [data-testid="stRadio"] div[role="radiogroup"] { gap: .55rem !important; flex-wrap: wrap; }
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] { background:#FFFFFF; border:1.5px solid #E6DDF3;
  border-radius: 999px; padding: .5rem 1.05rem !important; margin: 0 !important; cursor:pointer;
  transition: background .2s, border-color .2s, transform .12s, box-shadow .2s; }
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover { border-color:#C38BEA; transform: translateY(-1px); }
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child:not(:has([data-testid="stMarkdownContainer"])) { display:none; }
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
  background: linear-gradient(135deg, #7B3FBF, #9B5DE5); border-color: transparent; box-shadow: 0 6px 16px rgba(123,63,191,.3); }
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p { color:#FFFFFF !important; font-weight:700; }

/* ----- sidebar menu ----- */
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] { width:100%; padding:.55rem .8rem !important;
  border-radius: 14px; margin: .1rem 0 !important; transition: background .2s; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover { background:#F4EEFC; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child:not(:has([data-testid="stMarkdownContainer"])) { display:none; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) { background:#EDE2FB; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p { color:#4E2A84 !important; font-weight:800; }

/* ----- buttons ----- */
.stButton button, .stDownloadButton button, .stLinkButton a, [data-testid="stFormSubmitButton"] button {
  border-radius: 999px !important; padding: .55rem 1.3rem !important; min-height: 2.9rem; font-weight: 700 !important;
  transition: transform .12s, box-shadow .2s, filter .2s; }
.stButton button:active, [data-testid="stFormSubmitButton"] button:active { transform: scale(.97); }
button[kind="primary"], button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, #7B3FBF, #A66BE0) !important; border: none !important; color:#FFFFFF !important;
  box-shadow: 0 8px 20px rgba(123,63,191,.28) !important; }
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); }

/* ----- every bordered box becomes a soft white card ----- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
  background: rgba(255,255,255,.92); border: 1px solid #E6DDF3 !important; border-radius: 22px !important;
  box-shadow: 0 6px 24px rgba(78,42,132,.06); }
div[data-testid="stForm"] { background: rgba(255,255,255,.7) !important; border: 1px solid #E6DDF3 !important; border-radius: 24px !important; }
div[data-testid="stExpander"] { background:#FFFFFF; border: 1px solid #E6DDF3 !important; border-radius: 18px !important; }
div[data-testid="stExpander"] summary p { font-weight: 700 !important; color: #4E2A84 !important; }

/* coloured accent strip on the check-in cards */
.st-key-ck_sleep, .st-key-ck_food, .st-key-ck_feel, .st-key-ck_log { position: relative; overflow: hidden; }
.st-key-ck_log::before { content:""; position:absolute; left:0; top:0; right:0; height:6px; background: linear-gradient(90deg, #FFD23F, #FF9F1C); }
.st-key-ck_sleep::before, .st-key-ck_food::before, .st-key-ck_feel::before { content:""; position:absolute; left:0; top:0; right:0; height:6px; }
.st-key-ck_sleep::before { background: linear-gradient(90deg, #7CC4F5, #9B8CF0); }
.st-key-ck_food::before { background: linear-gradient(90deg, #F7B267, #F28B82); }
.st-key-ck_feel::before { background: linear-gradient(90deg, #E58FC7, #C38BEA); }

/* Tulsi's plan: each step is a tappable row that gets crossed off when ticked */
.st-key-ck_plan [data-testid="stCheckbox"] label { width: 100%; box-sizing: border-box; background: #FFFFFF; border: 1.5px solid #E6DDF3;
  border-radius: 16px; padding: .7rem .9rem; transition: background .2s, border-color .2s; }
.st-key-ck_plan [data-testid="stCheckbox"] label:hover { border-color: #C38BEA; }
.st-key-ck_plan [data-testid="stCheckbox"] label:has(input:checked) { background: #EEF8F2; border-color: #A8DDBE; }
.st-key-ck_plan [data-testid="stCheckbox"] label:has(input:checked) p { text-decoration: line-through; color: #6B8F7A !important; }
.st-key-ck_plan [data-testid="stCheckbox"] p { font-size: 1.05rem !important; font-weight: 600; }
.st-key-ck_plan::before { content:""; position:absolute; left:0; top:0; right:0; height:6px; background: linear-gradient(90deg, #9B6BD6, #3FAE74); }
.st-key-ck_tell::before { content:""; position:absolute; left:0; top:0; right:0; height:6px; background: linear-gradient(90deg, #E58FC7, #F7B267); }
.st-key-ck_confirm::before { content:""; position:absolute; left:0; top:0; right:0; height:6px; background: linear-gradient(90deg, #3FAE74, #7CC4F5); }
.st-key-ck_plan, .st-key-ck_tell, .st-key-ck_confirm { position: relative; overflow: hidden; }

/* card headers with an icon tile */
.ck-head { display:flex; align-items:center; gap:.9rem; margin: .2rem 0 .4rem; }
.ck-head .ic { width: 3rem; height: 3rem; border-radius: 16px; display:flex; align-items:center; justify-content:center; font-size: 1.6rem; }
.ck-head b { font-size: 1.25rem; color: #2A2140; display:block; }
.ck-head span { font-size: .88rem; color: #786E8C; }
</style>
"""


def inject_widget_css() -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)


def card_header(icon: str, title: str, subtitle: str = "", tint: str = "#F1EAFB") -> None:
    st.markdown(f'<div class="ck-head"><div class="ic" style="background:{tint}">{icon}</div>'
                f'<div><b>{html.escape(title)}</b><span>{subtitle}</span></div></div>', unsafe_allow_html=True)


def auto_size() -> None:
    """Scales the whole app (text, buttons, cards) to the window width, like browser zoom done automatically.
    The page is designed for a 1450 px wide window; wider windows (or a zoomed-out browser) get scaled up,
    so text is never tiny. Streamlit controls the page's base font size, so zoom is used instead of font-size."""
    import streamlit.components.v1 as components
    components.html("""<script>
    const w = window.parent, d = w.document;
    d.documentElement.style.removeProperty('font-size');
    let s = d.getElementById('fb-autosize');
    if (!s) { s = d.createElement('style'); s.id = 'fb-autosize'; d.head.appendChild(s); }
    function fit() {
      const z = Math.max(1, Math.min(2.6, w.innerWidth / 1450));
      s.textContent = ':root { --fbz: ' + z.toFixed(3) + '; }';
    }
    fit();
    if (!w.__fbResize) { w.__fbResize = true; w.addEventListener('resize', fit); }
    </script>""", height=0)
