"""SVG primitives for the blueprint yearwise covers (M1/S1/P4 house style).

Every plate is drawn in an 800 x 800 box, y pointing down. Colours are never
written into the SVG: each element names a role ('m' main, 's' soft, 'a'
accent) and the page CSS maps the role to a colour through CSS variables, so
one drawing serves both the dark/bright front and the pale back-cover corner.
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

Point = tuple[float, float]

ROLE = {'m': 'var(--pm)', 's': 'var(--ps)', 'a': 'var(--pa)', 'g': 'var(--pg)',
        't': 'var(--pt)'}


def _style(stroke: str | None = 'm', width: float = 1.4, fill: str | None = None,
           op: float = 1.0, dash: str | None = None, fill_op: float | None = None) -> str:
    parts = [f'stroke:{ROLE[stroke]}' if stroke else 'stroke:none',
             f'stroke-width:{width}',
             f'fill:{ROLE[fill]}' if fill else 'fill:none']
    if op != 1:
        parts.append(f'opacity:{op}')
    if dash:
        parts.append(f'stroke-dasharray:{dash}')
    if fill_op is not None:
        parts.append(f'fill-opacity:{fill_op}')
    parts.append('stroke-linecap:round;stroke-linejoin:round')
    return 'style="' + ';'.join(parts) + '"'


def _pts(points: Iterable[Point]) -> str:
    return ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)


def line(x1, y1, x2, y2, role='m', w=1.4, op=1.0, dash=None) -> str:
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'{_style(role, w, op=op, dash=dash)}/>')


def poly(points: Sequence[Point], role='m', w=2.0, op=1.0, dash=None,
         fill=None, fill_op=None, closed=False) -> str:
    tag = 'polygon' if closed else 'polyline'
    return (f'<{tag} points="{_pts(points)}" '
            f'{_style(role, w, fill, op, dash, fill_op)}/>')


def path(d: str, role='m', w=2.0, op=1.0, dash=None, fill=None, fill_op=None) -> str:
    return f'<path d="{d}" {_style(role, w, fill, op, dash, fill_op)}/>'


def circle(cx, cy, r, role='m', w=1.4, op=1.0, dash=None, fill=None, fill_op=None) -> str:
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'{_style(role, w, fill, op, dash, fill_op)}/>')


def dot(cx, cy, r=4.0, role='m') -> str:
    return circle(cx, cy, r, role=None, w=0, fill=role)


def rect(x, y, w_, h_, role='m', w=1.4, op=1.0, dash=None, fill=None, fill_op=None, rx=0) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="{h_:.1f}" rx="{rx}" '
            f'{_style(role, w, fill, op, dash, fill_op)}/>')


def ellipse(cx, cy, rx, ry, role='m', w=1.4, op=1.0, dash=None, fill=None, fill_op=None,
            rot=0.0) -> str:
    tr = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ''
    return (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"{tr} '
            f'{_style(role, w, fill, op, dash, fill_op)}/>')


def esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text(x, y, s, size=15, role='t', op=1.0, anchor='start', math_=True,
         weight=400, spacing=0.0) -> str:
    fam = "font-family:MathSerif;font-style:italic" if math_ else "font-family:Mono"
    ls = f';letter-spacing:{spacing}px' if spacing else ''
    o = f';opacity:{op}' if op != 1 else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" xml:space="preserve" '
            f'style="{fam};font-size:{size}px;font-weight:{weight};fill:{ROLE[role]}{o}{ls}">'
            f'{esc(s)}</text>')


def label(x, y, s, size=12.5, role='t', op=.5, anchor='start') -> str:
    """Upper-case mono annotation (the '02 POLAR CURVES' voice of the series)."""
    return text(x, y, s, size, role, op, anchor, math_=False, spacing=1.5)


def tag(x, y, num: str, name: str) -> str:
    """Numbered topic tag: accent number, muted name."""
    return label(x, y, num, role='a', op=1) + label(x + 24, y, name)


def arrow(x1, y1, x2, y2, role='m', w=2.0, head=10.0, op=1.0) -> str:
    ang = math.atan2(y2 - y1, x2 - x1)
    a1, a2 = ang + math.radians(155), ang - math.radians(155)
    tip = [(x2, y2), (x2 + head * math.cos(a1), y2 + head * math.sin(a1)),
           (x2 + head * math.cos(a2), y2 + head * math.sin(a2))]
    return (line(x1, y1, x2, y2, role, w, op)
            + poly(tip, role=None, w=0, fill=role, closed=True, op=op))


def axes(ox, oy, left, right, up, down=0.0, role='m', op=.6, xl='x', yl='y') -> str:
    out = [line(ox - left, oy, ox + right, oy, role, 1.4, op),
           line(ox, oy + down, ox, oy - up, role, 1.4, op)]
    if xl:
        out.append(text(ox + right - 4, oy + 20, xl, 16, op=.75, anchor='end'))
    if yl:
        out.append(text(ox + 10, oy - up + 12, yl, 16, op=.75))
    return ''.join(out)


def curve(f: Callable[[float], float], x0: float, x1: float, ox: float, oy: float,
          sx: float, sy: float, n: int = 90) -> list[Point]:
    """Sample y=f(x) on [x0,x1] and map maths coords to plate coords."""
    pts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        pts.append((ox + x * sx, oy - f(x) * sy))
    return pts


def param(fx, fy, t0, t1, n=120) -> list[Point]:
    return [(fx(t0 + (t1 - t0) * i / n), fy(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]


def frame(cx=400.0, cy=378.0) -> str:
    """The shared backdrop: glow, 25-unit grid, and the two concentric rings."""
    out = ['<defs><radialGradient id="glow" cx="50%" cy="46%" r="60%">'
           '<stop offset="0%" style="stop-color:var(--pglow);stop-opacity:.30"/>'
           '<stop offset="55%" style="stop-color:var(--pglow);stop-opacity:.07"/>'
           '<stop offset="100%" style="stop-color:var(--pglow);stop-opacity:0"/>'
           '</radialGradient></defs>',
           f'<circle cx="{cx}" cy="{cy}" r="440" fill="url(#glow)"/>',
           '<g class="grid">']
    for v in range(0, 801, 25):
        op = .17 if v % 100 == 0 else .10
        out.append(line(v, 0, v, 800, 'g', .7, op) + line(0, v, 800, v, 'g', .7, op))
    out.append('</g>')
    out.append(circle(cx, cy, 330, 's', 1.2, .42))
    out.append(circle(cx, cy, 360, 's', .8, .22, dash='2 11'))
    return ''.join(out)


def svg(inner: str) -> str:
    return ('<svg viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg" class="plate">'
            + frame() + inner + '</svg>')
