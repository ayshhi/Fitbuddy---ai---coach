"""
garden.py - draws Tulsi growing in her pot, from a seed (stage 0) to full bloom (stage 5).
Pure SVG, so it needs no image files.
"""

import base64

POT = """
  <ellipse cx="100" cy="252" rx="62" ry="6" fill="#2A2140" opacity=".08"/>
  <path d="M48 196 L152 196 L140 250 Q100 256 60 250 Z" fill="#7B3FBF"/>
  <path d="M60 250 Q100 256 140 250 L142 240 Q100 246 58 240 Z" fill="#6A33A8" opacity=".6"/>
  <rect x="40" y="186" width="120" height="16" rx="8" fill="#9B6BD6"/>
  <ellipse cx="100" cy="189" rx="54" ry="5" fill="#5A3A2A"/>
  <path d="M78 222 q4 -6 8 0 q4 -6 8 0 q-4 6 -8 10 q-4 -4 -8 -10z" fill="#F1EAFB" opacity=".9"/>
"""

FACE = """
  <circle cx="{lx}" cy="{ey}" r="3.6" fill="#1E3B2C"/><circle cx="{rx}" cy="{ey}" r="3.6" fill="#1E3B2C"/>
  <circle cx="{lx2}" cy="{ey2}" r="1.2" fill="#fff"/><circle cx="{rx2}" cy="{ey2}" r="1.2" fill="#fff"/>
  <ellipse cx="{lc}" cy="{cy}" rx="5" ry="3" fill="#F59AA6" opacity=".85"/>
  <ellipse cx="{rc}" cy="{cy}" rx="5" ry="3" fill="#F59AA6" opacity=".85"/>
  <path d="M{m1} {my} Q100 {mq} {m2} {my}" stroke="#1E3B2C" stroke-width="2.8" fill="none" stroke-linecap="round"/>
"""


def _face(cx=100, cy=166, r=24):
    return FACE.format(lx=cx - 9, rx=cx + 9, ey=cy - 3, lx2=cx - 8, rx2=cx + 10, ey2=cy - 4.3,
                       lc=cx - 15, rc=cx + 15, cy=cy + 5, m1=cx - 6, m2=cx + 6, my=cy + 6, mq=cy + 12)


def _body(cy=166, r=26):
    return (f'<ellipse cx="100" cy="{cy}" rx="{r + 4}" ry="{r}" fill="#6CCB94"/>'
            f'<ellipse cx="100" cy="{cy + 6}" rx="{r - 4}" ry="{r - 10}" fill="#86D8A8" opacity=".55"/>'
            + _face(cy=cy, r=r))


def _leaf(x, y, side, size=1.0, color="#5CC08A"):
    s = size
    if side == "left":
        d = f"M{x} {y} C{x - 14 * s} {y - 16 * s} {x - 34 * s} {y - 12 * s} {x - 36 * s} {y - 2 * s} C{x - 22 * s} {y + 8 * s} {x - 8 * s} {y + 6 * s} {x} {y}Z"
    else:
        d = f"M{x} {y} C{x + 14 * s} {y - 16 * s} {x + 34 * s} {y - 12 * s} {x + 36 * s} {y - 2 * s} C{x + 22 * s} {y + 8 * s} {x + 8 * s} {y + 6 * s} {x} {y}Z"
    return f'<path d="{d}" fill="{color}"/>'


def _stem(top, bottom=142):
    return f'<path d="M100 {bottom} C98 {(top + bottom) / 2} 102 {(top + bottom) / 2} 100 {top}" stroke="#2F8F5B" stroke-width="5" stroke-linecap="round" fill="none"/>'


def _flower(cx, cy, open_=True):
    if not open_:  # bud
        return (f'<path d="M{cx} {cy - 22} C{cx + 14} {cy - 10} {cx + 10} {cy + 6} {cx} {cy + 8} '
                f'C{cx - 10} {cy + 6} {cx - 14} {cy - 10} {cx} {cy - 22}Z" fill="#E58FC7"/>'
                f'<path d="M{cx} {cy - 16} C{cx + 6} {cy - 6} {cx + 4} {cy + 4} {cx} {cy + 6}" stroke="#C86FAE" stroke-width="2" fill="none"/>'
                f'<path d="M{cx - 9} {cy + 6} Q{cx} {cy + 14} {cx + 9} {cy + 6}" fill="#3FAE74"/>')
    petals = "".join(
        f'<ellipse cx="{cx}" cy="{cy - 16}" rx="9" ry="16" fill="{c}" transform="rotate({a} {cx} {cy})"/>'
        for a, c in zip(range(0, 360, 60), ["#E58FC7", "#C38BEA", "#E58FC7", "#C38BEA", "#E58FC7", "#C38BEA"])
    )
    sparkles = "".join(
        f'<path d="M{x} {y - 6} L{x + 1.6} {y - 1.6} L{x + 6} {y} L{x + 1.6} {y + 1.6} L{x} {y + 6} '
        f'L{x - 1.6} {y + 1.6} L{x - 6} {y} L{x - 1.6} {y - 1.6}Z" fill="#F7C548"/>'
        for x, y in [(cx - 42, cy - 18), (cx + 44, cy - 6), (cx + 30, cy - 40), (cx - 28, cy + 26)]
    )
    return petals + f'<circle cx="{cx}" cy="{cy}" r="10" fill="#F7C548"/><circle cx="{cx - 3}" cy="{cy - 3}" r="3" fill="#FBE29A"/>' + sparkles


def _small_flower(cx, cy):
    """A small flower on a leaf: one for every goal reached before the current one."""
    petals = "".join(f'<ellipse cx="{cx}" cy="{cy - 7}" rx="4.5" ry="8" fill="{c}" transform="rotate({a} {cx} {cy})"/>'
                     for a, c in zip(range(0, 360, 72), ["#E58FC7", "#C38BEA", "#E58FC7", "#C38BEA", "#F2A7D3"]))
    return petals + f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="#F7C548"/>'


FLOWER_SPOTS = [(68, 110), (132, 96), (72, 88), (128, 74), (70, 128), (130, 118), (76, 66), (124, 58)]


DEW = "".join(
    f'<path d="M{x} {y - 8} C{x + 5.5} {y} {x + 5.5} {y + 5} {x} {y + 6} C{x - 5.5} {y + 5} {x - 5.5} {y} {x} {y - 8}Z" '
    f'fill="#7CC4F5" stroke="#FFFFFF" stroke-width="1"/>'
    for x, y in [(70, 150), (132, 160), (60, 118), (146, 112), (128, 84)]
)


def tulsi_svg(stage: int, fresh: bool = False, flowers: int = 0) -> str:
    """fresh=True adds shiny water drops (after you've had 8 glasses today)."""
    stage = max(0, min(5, int(stage)))
    parts = [POT]
    if stage == 0:  # seed peeking out of the soil
        parts.append('<ellipse cx="100" cy="182" rx="20" ry="13" fill="#B07A4F"/>'
                     '<ellipse cx="96" cy="178" rx="8" ry="4" fill="#C89468" opacity=".7"/>'
                     + _face(cy=180).replace('r="3.6"', 'r="2.6"'))
        parts.append(_leaf(100, 168, "right", 0.35, "#86D8A8"))
        parts.append('<path d="M100 170 L100 166" stroke="#2F8F5B" stroke-width="3" stroke-linecap="round"/>')
    else:
        # stem height and leaves grow with each stage
        top = {1: 128, 2: 100, 3: 74, 4: 56, 5: 50}[stage]
        if stage >= 2:
            parts.append(_stem(top))
            pairs = {2: [118], 3: [124, 98], 4: [126, 104, 82], 5: [128, 106, 84]}[stage]
            for i, y in enumerate(pairs):
                size = 0.9 - i * 0.12
                parts.append(_leaf(100, y, "left", size, "#5CC08A"))
                parts.append(_leaf(100, y - 6, "right", size, "#3FAE74"))
        # the two little leaves on Tulsi's head (as in her avatar)
        if stage == 1:
            parts.append('<path d="M100 142 L100 130" stroke="#2F8F5B" stroke-width="5" stroke-linecap="round"/>')
            parts.append(_leaf(100, 132, "left", 0.7) + _leaf(100, 128, "right", 0.7, "#3FAE74"))
        if stage == 4:
            parts.append(_flower(100, top - 6, open_=False))
        if stage == 5:
            parts.append(_flower(100, top - 8, open_=True))
        for x, y in FLOWER_SPOTS[:max(0, flowers)]:
            parts.append(_small_flower(x, y))
        parts.append(_body())
    if fresh:
        parts.append(DEW)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 262">'
            + "".join(parts) + "</svg>")


CAN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80"><g transform="translate(120 0) scale(-1 1)">
  <path d="M20 30 h52 a6 6 0 0 1 6 6 v30 a8 8 0 0 1 -8 8 h-48 a8 8 0 0 1 -8 -8 v-30 a6 6 0 0 1 6 -6z" fill="#9B6BD6"/>
  <path d="M30 30 q16 -26 34 0" stroke="#7B3FBF" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M78 46 L112 22 L116 28 L84 56 Z" fill="#9B6BD6"/>
  <ellipse cx="114" cy="24" rx="5" ry="7" fill="#7B3FBF" transform="rotate(-35 114 24)"/>
  <path d="M28 44 h36" stroke="#C9A8F0" stroke-width="4" stroke-linecap="round"/>
</g></svg>"""

WATER_CSS = """<style>
.tulsi-pot { position: relative; margin: 0 auto; }
.tulsi-pot .can { position:absolute; top:-10%; right:-30%; width:58%; transform-origin: 85% 85%;
                  animation: can-tilt 2.4s ease-in-out both; }
.tulsi-pot .drop { position:absolute; width:.55rem; height:.8rem; background:#7CC4F5; border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
                   opacity:0; animation: drop-fall 1.1s ease-in infinite; animation-iteration-count: 2; }
.tulsi-pot .thanks { position:absolute; top:-12%; left:50%; transform:translateX(-50%); white-space:nowrap;
                     background:#FFFFFF; border:1px solid #E6DDF3; border-radius:99px; padding:.2rem .7rem; font-weight:700;
                     color:#4E2A84; font-size:.85rem; box-shadow:0 4px 14px rgba(78,42,132,.15); animation: thanks 2.6s ease both; }
@keyframes can-tilt { 0% { opacity:0; transform: translateY(-20px) rotate(0); } 15% { opacity:1; transform: rotate(0); }
  30%, 80% { transform: rotate(-30deg); } 100% { opacity:0; transform: rotate(0); } }
@keyframes drop-fall { 0% { opacity:0; transform: translateY(0); } 15% { opacity:1; } 100% { opacity:0; transform: translateY(5.5rem); } }
@keyframes thanks { 0%, 40% { opacity:0; transform: translate(-50%, 8px); } 55%, 90% { opacity:1; transform: translate(-50%, 0); } 100% { opacity:0; } }
</style>"""


def tulsi_img(stage: int, size: str = "12rem", fresh: bool = False, watering: bool = False, flowers: int = 0) -> str:
    data = base64.b64encode(tulsi_svg(stage, fresh, flowers).encode()).decode()
    img = f'<img src="data:image/svg+xml;base64,{data}" style="width:100%;height:auto;display:block">'
    if not watering:
        return f'<div class="tulsi-pot" style="width:{size}">{img}</div>'
    can = base64.b64encode(CAN_SVG.encode()).decode()
    drops = "".join(f'<span class="drop" style="left:{x}%;top:{y}%;animation-delay:{d}s"></span>'
                    for x, y, d in [(46, 12, .5), (54, 8, .7), (62, 14, .9), (50, 18, 1.1), (58, 10, 1.3)])
    return (f'{WATER_CSS}<div class="tulsi-pot" style="width:{size}">{img}'
            f'<img class="can" src="data:image/svg+xml;base64,{can}">{drops}'
            f'<div class="thanks">Thank you! 💧</div></div>')
