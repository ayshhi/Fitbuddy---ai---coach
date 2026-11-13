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


def tulsi_svg(stage: int) -> str:
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
        parts.append(_body())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 262">'
            + "".join(parts) + "</svg>")


def tulsi_img(stage: int, size: str = "12rem") -> str:
    data = base64.b64encode(tulsi_svg(stage).encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{data}" style="width:{size};height:auto;display:block;margin:0 auto">'
