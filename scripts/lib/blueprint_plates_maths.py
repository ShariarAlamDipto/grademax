"""Blueprint cover plates for the mathematics books (IAL P1-P4, M1, S1; IGCSE 4PM1, 4MB1).

Each plate shows four or five real topics from that unit's specification, laid
out in five zones around the shared rings: top-left, top-right, centre,
bottom-left, bottom-right. Formula captions sit on the outer margin.
"""
from __future__ import annotations

import math

from blueprint_svg import (arrow, axes, circle, curve, dot, ellipse, label, line, param,
                           path, poly, rect, svg, tag, text)


def _caption(x, y, s, size=16, anchor='middle', op=.5) -> str:
    return text(x, y, s, size, op=op, anchor=anchor)


# ---------------------------------------------------------------- IAL P1
def plate_wma11() -> str:
    o = []
    # centre: quadratic meets straight line
    ox, oy, sx, sy = 400, 360, 45, 25
    o.append(axes(ox, oy, 120, 230, 190, 120))
    o.append(poly(curve(lambda x: x * x - 2 * x - 3, -1.65, 4.3, ox, oy, sx, sy), 'm', 2.8))
    o.append(poly(curve(lambda x: x + 1, -2.2, 4.6, ox, oy, sx, sy, 2), 'a', 2.2))
    for x, y in [(-1, 0), (4, 5)]:
        o.append(dot(ox + x * sx, oy - y * sy, 5.5, 'a'))
    o.append(line(ox + sx, oy, ox + sx, oy + 4 * sy, 's', 1.2, .8, '4 4'))
    o.append(dot(ox + sx, oy + 4 * sy, 4, 'm'))
    o.append(text(ox + sx + 10, oy + 4 * sy + 22, '(1, −4)', 14, op=.75))
    o.append(text(ox + 4.3 * sx + 6, oy - 5.3 * sy + 26, 'y = x + 1', 15, 'a'))
    o.append(text(ox - 22, oy + 96, 'y = x² − 2x − 3', 15, op=.85, anchor='end'))
    # top-left: arc length and sector area in radians
    cx, cy, r = 100, 285, 125
    a0, a1 = math.radians(-12), math.radians(-58)
    p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
    p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
    o.append(path(f'M {cx} {cy} L {p0[0]:.1f} {p0[1]:.1f} A {r} {r} 0 0 0 {p1[0]:.1f} {p1[1]:.1f} Z',
                  'm', 2.2, fill='a', fill_op=.22))
    o.append(path(f'M {cx + 40 * math.cos(a0):.1f} {cy + 40 * math.sin(a0):.1f} '
                  f'A 40 40 0 0 0 {cx + 40 * math.cos(a1):.1f} {cy + 40 * math.sin(a1):.1f}', 'a', 1.6))
    o.append(text(cx + 50, cy - 22, 'θ', 17, 'a'))
    o.append(text(cx + 70, cy + 6, 'r', 16, op=.8))
    o.append(text(cx + 128, cy - 70, 's = rθ', 15, op=.75))
    o.append(text(cx + 10, cy + 40, 'A = ½ r²θ', 15, op=.75))
    # bottom-left: cubic sketch with its three roots
    ox2, oy2 = 200, 590
    o.append(axes(ox2, oy2, 110, 120, 70, 60, xl='', yl=''))
    o.append(poly(curve(lambda x: x * (x - 2) * (x + 2) / 1.0, -2.45, 2.45, ox2, oy2, 42, 9), 'm', 2.4))
    for x in (-2, 0, 2):
        o.append(dot(ox2 + x * 42, oy2, 3.6, 'a'))
    o.append(text(ox2, oy2 + 82, 'y = x(x − 2)(x + 2)', 14, op=.7, anchor='middle'))
    # bottom-right: y = sin x over one period
    ox3, oy3 = 500, 590
    o.append(axes(ox3, oy3, 10, 240, 60, 60, xl='x', yl=''))
    o.append(poly(curve(math.sin, 0, 2 * math.pi, ox3, oy3, 35, 48), 'm', 2.4))
    o.append(poly(curve(lambda x: math.sin(x - math.pi / 3), 0, 2 * math.pi, ox3, oy3, 35, 48),
                  's', 1.6, dash='5 5'))
    o.append(text(ox3 + 2 * math.pi * 35, oy3 + 22, '2π', 14, op=.7, anchor='middle'))
    o.append(text(ox3 + 120, oy3 - 66, 'y = sin x', 14, op=.8))
    o.append(tag(58, 150, '01', 'RADIAN MEASURE'))
    o.append(tag(500, 150, '02', 'QUADRATICS'))
    o.append(tag(58, 470, '03', 'CURVE SKETCHING'))
    o.append(tag(500, 470, '04', 'TRIGONOMETRY'))
    o.append(_caption(668, 300, 'b² − 4ac > 0', 15))
    o.append(_caption(668, 330, 'y − y₁ = m(x − x₁)', 15))
    o.append(_caption(400, 92, 'dy/dx = nxⁿ⁻¹', 17))
    o.append(_caption(400, 690, 'y = a(x − p)² + q', 15))
    return svg(''.join(o))


# ---------------------------------------------------------------- IAL P2
def plate_wma12() -> str:
    o = []
    # centre: circle, radius and tangent
    cx, cy, r = 400, 360, 112
    o.append(circle(cx, cy, r, 'm', 2.6))
    o.append(dot(cx, cy, 4.5, 'm'))
    ang = math.radians(-40)
    px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
    o.append(line(cx, cy, px, py, 's', 1.8))
    tx, ty = -math.sin(ang), math.cos(ang)
    o.append(line(px - 78 * tx, py - 78 * ty, px + 110 * tx, py + 110 * ty, 'a', 2.2))
    o.append(dot(px, py, 5, 'a'))
    o.append(text(cx - 14, cy + 26, 'C(a, b)', 14, op=.8, anchor='middle'))
    o.append(text((cx + px) / 2 - 8, (cy + py) / 2 - 10, 'r', 16, op=.8))
    o.append(text(cx, cy + r + 34, '(x − a)² + (y − b)² = r²', 15, op=.85, anchor='middle'))
    # top: Pascal's triangle for the binomial expansion
    rows = ['1', '1   1', '1   2   1', '1   3   3   1', '1   4   6   4   1']
    for i, row in enumerate(rows):
        o.append(label(400, 82 + i * 22, row, 13, op=.65 if i < 4 else 1,
                       role='a' if i == 4 else 't', anchor='middle'))
    o.append(_caption(400, 196, '(a + b)⁴', 15, op=.6))
    # top-left: trapezium rule under a curve
    ox, oy = 90, 300
    f = lambda x: 1.2 + .9 * math.sin(x * .9) + .25 * x
    xs = [0.4 + i * .8 for i in range(6)]
    for a_, b_ in zip(xs, xs[1:]):
        o.append(poly([(ox + a_ * 45, oy), (ox + a_ * 45, oy - f(a_) * 45),
                       (ox + b_ * 45, oy - f(b_) * 45), (ox + b_ * 45, oy)], 'a', 1.2,
                      fill='a', fill_op=.16, closed=True))
    o.append(axes(ox, oy, 0, 230, 150, 0, yl=''))
    o.append(poly(curve(f, 0, 4.9, ox, oy, 45, 45), 'm', 2.4))
    o.append(text(ox + 110, oy + 26, '∫ y dx ≈ ½h[y₀ + 2(y₁ + … ) + yₙ]', 13, op=.7, anchor='middle'))
    # top-right: geometric series bars
    bx, by = 520, 300
    for i in range(8):
        h = 130 * .72 ** i
        o.append(rect(bx + i * 27, by - h, 18, h, 'm', 1.2, fill='a' if i == 0 else 's',
                      fill_op=.55 if i == 0 else .22))
    o.append(line(bx - 6, by, bx + 222, by, 'm', 1.4, .6))
    o.append(text(bx + 110, by + 26, 'S∞ = a / (1 − r)', 14, op=.75, anchor='middle'))
    # bottom-left: exponential with asymptote
    ox2, oy2 = 200, 640
    o.append(axes(ox2, oy2, 110, 130, 150, 0, yl='y'))
    o.append(poly(curve(lambda x: 2 ** x, -2.6, 2.1, ox2, oy2, 42, 34), 'm', 2.4))
    o.append(dot(ox2, oy2 - 34, 3.8, 'a'))
    o.append(text(ox2 + 92, oy2 - 120, 'y = 2ˣ', 15, op=.8))
    o.append(text(ox2 + 10, 690, 'logₐ xy = logₐ x + logₐ y', 14, op=.6, anchor='middle'))
    # bottom-right: cubic with stationary points
    ox3, oy3 = 610, 585
    o.append(axes(ox3, oy3, 120, 120, 70, 70, xl='', yl=''))
    g = lambda x: (x ** 3 - 3 * x) / 1.0
    o.append(poly(curve(g, -2.05, 2.05, ox3, oy3, 52, 24), 'm', 2.4))
    for x in (-1, 1):
        o.append(dot(ox3 + x * 52, oy3 - g(x) * 24, 5, 'a'))
        o.append(line(ox3 + x * 52 - 30, oy3 - g(x) * 24, ox3 + x * 52 + 30, oy3 - g(x) * 24, 'a', 1.4))
    o.append(text(ox3, oy3 + 92, 'dy/dx = 0', 14, op=.75, anchor='middle'))
    o.append(tag(58, 112, '01', 'INTEGRATION'))
    o.append(tag(520, 112, '02', 'SERIES'))
    o.append(tag(58, 470, '03', 'LOGARITHMS'))
    o.append(tag(500, 470, '04', 'DIFFERENTIATION'))
    return svg(''.join(o))


# ---------------------------------------------------------------- IAL P3
def plate_wma13() -> str:
    o = []
    # centre: e^x and ln x, mirror images in y = x
    ox, oy, s = 400, 430, 52
    o.append(axes(ox, oy, 200, 210, 250, 120))
    o.append(line(ox - 2.6 * s, oy + 2.6 * s / 1.3 * 1.3, ox + 3.9 * s, oy - 3.9 * s, 's', 1.4, .7, '6 6'))
    o.append(poly(curve(math.exp, -3.6, 1.42, ox, oy, s, s), 'm', 2.8))
    o.append(poly(curve(math.log, .035, 4.1, ox, oy, s, s, 160), 'a', 2.8))
    o.append(dot(ox, oy - s, 4.5, 'm'))
    o.append(dot(ox + s, oy, 4.5, 'a'))
    o.append(text(ox + 1.5 * s, oy - 4.2 * s, 'y = eˣ', 16, op=.9))
    o.append(text(ox + 3.4 * s, oy - .55 * s, 'y = ln x', 16, 'a', anchor='middle'))
    o.append(text(ox + 2.5 * s + 10, oy - 2.5 * s + 4, 'y = x', 14, op=.6))
    # top-left: modulus graph
    ox2, oy2 = 190, 270
    o.append(axes(ox2, oy2, 100, 130, 140, 0, xl='', yl=''))
    o.append(poly([(ox2 - 90, oy2 - 120), (ox2 + 30, oy2), (ox2 + 125, oy2 - 95)], 'm', 2.4))
    o.append(poly([(ox2 + 30, oy2), (ox2 + 90, oy2 + 60)], 's', 1.4, dash='4 5'))
    o.append(text(ox2 + 20, oy2 - 150, 'y = |2x − 1|', 14, op=.8, anchor='middle'))
    # top-right: R cos(θ − α)
    ox3, oy3 = 505, 200
    o.append(line(ox3, oy3, ox3 + 235, oy3, 'm', 1.4, .6))
    o.append(poly(curve(lambda x: math.cos(x), 0, 2 * math.pi, ox3, oy3, 37, 30), 's', 1.4, dash='5 5'))
    o.append(poly(curve(lambda x: 1.6 * math.cos(x - .9), 0, 2 * math.pi, ox3, oy3, 37, 30), 'm', 2.4))
    o.append(dot(ox3 + .9 * 37, oy3 - 48, 4.5, 'a'))
    o.append(text(ox3 + 175, oy3 - 58, 'R cos(θ − α)', 15, op=.8, anchor='middle'))
    # bottom-left: Newton-Raphson tangents converging on a root
    ox4, oy4 = 100, 640
    f = lambda x: .18 * x ** 2 - 1.2
    o.append(line(ox4, oy4 - 0, ox4 + 240, oy4, 'm', 1.4, .6))
    o.append(poly(curve(f, .6, 4.6, ox4, oy4 - 60, 45, 45), 'm', 2.4))
    x = 4.4
    for _ in range(3):
        y = f(x)
        x_next = x - y / (.36 * x)
        o.append(line(ox4 + x * 45, oy4 - 60, ox4 + x * 45, oy4 - 60 - y * 45, 'a', 1.2, .8, '3 4'))
        o.append(line(ox4 + x * 45, oy4 - 60 - y * 45, ox4 + x_next * 45, oy4 - 60, 'a', 1.8))
        o.append(dot(ox4 + x * 45, oy4 - 60 - y * 45, 3.6, 'a'))
        x = x_next
    o.append(line(ox4, oy4 - 60, ox4 + 245, oy4 - 60, 's', 1, .6))
    o.append(text(ox4 + 120, oy4 + 6, 'xₙ₊₁ = xₙ − f(xₙ) / f′(xₙ)', 13, op=.75, anchor='middle'))
    # bottom-right: composite function mapping
    for i, (cx, nm) in enumerate([(530, 'x'), (620, 'f(x)'), (710, 'gf(x)')]):
        o.append(ellipse(cx, 575, 30, 58, 'm' if i != 1 else 's', 1.8))
        o.append(text(cx, 655, nm, 14, op=.8, anchor='middle'))
    o.append(arrow(556, 552, 596, 552, 'a', 1.8, 8))
    o.append(arrow(646, 592, 686, 592, 'a', 1.8, 8))
    o.append(text(576, 540, 'f', 15, 'a', anchor='middle'))
    o.append(text(666, 580, 'g', 15, 'a', anchor='middle'))
    o.append(tag(58, 100, '01', 'FUNCTIONS'))
    o.append(tag(505, 100, '02', 'TRIGONOMETRY'))
    o.append(tag(58, 470, '03', 'NUMERICAL METHODS'))
    o.append(tag(500, 470, '04', 'EXPONENTIALS & LOGS'))
    o.append(_caption(400, 692, 'd/dx [f(g(x))] = f′(g(x)) g′(x)', 15))
    o.append(_caption(400, 70, 'sec²θ = 1 + tan²θ', 15))
    return svg(''.join(o))


# ---------------------------------------------------------------- IAL P4
def plate_wma14() -> str:
    o = []
    # centre: lines in 3D, r = a + λb
    ox, oy = 395, 420
    o.append(arrow(ox, oy, ox, oy - 190, 's', 1.6, 9))
    o.append(arrow(ox, oy, ox + 175, oy + 70, 's', 1.6, 9))
    o.append(arrow(ox, oy, ox - 160, oy + 80, 's', 1.6, 9))
    for nm, x, y in [('z', ox + 10, oy - 192), ('y', ox + 182, oy + 86), ('x', ox - 172, oy + 100)]:
        o.append(text(x, y, nm, 16, op=.75))
    ax, ay = ox - 70, oy - 40
    o.append(arrow(ox, oy, ax, ay, 'a', 2.4, 11))
    o.append(text(ax - 30, ay + 8, 'a', 17, 'a'))
    o.append(line(ax - 80, ay + 70, ax + 150, ay - 132, 'm', 2.8))
    o.append(arrow(ax, ay, ax + 72, ay - 61, 'm', 3, 12))
    o.append(text(ax + 70, ay - 30, 'b', 17, op=.9))
    o.append(line(ox - 120, oy - 175, ox + 190, oy - 25, 's', 2, .9, '8 6'))
    o.append(text(ox + 62, oy + 66, 'r = a + λb', 17, op=.9, anchor='middle'))
    # top-left: parametric curve x = cos t, y = sin 2t
    cx, cy = 175, 200
    o.append(line(cx - 105, cy, cx + 105, cy, 's', 1.2, .5))
    o.append(line(cx, cy - 70, cx, cy + 70, 's', 1.2, .5))
    o.append(poly(param(lambda t: cx + 90 * math.cos(t), lambda t: cy - 58 * math.sin(2 * t),
                        0, 2 * math.pi, 160), 'm', 2.4))
    o.append(dot(cx + 90 * math.cos(.6), cy - 58 * math.sin(1.2), 5, 'a'))
    o.append(text(cx, cy + 96, 'x = cos t,  y = sin 2t', 14, op=.75, anchor='middle'))
    # top-right: volume of revolution about the x-axis
    ox2, oy2 = 520, 210
    o.append(line(ox2 - 10, oy2, ox2 + 220, oy2, 'm', 1.4, .6))
    f = lambda x: 26 * math.sqrt(max(x, 0))
    o.append(poly(curve(lambda x: f(x) / 1, 0, 4, ox2, oy2, 52, 1), 'm', 2.4))
    o.append(poly(curve(lambda x: -f(x), 0, 4, ox2, oy2, 52, 1), 'm', 1.4, .6, '5 5'))
    for x in (1.2, 2.4, 3.6):
        o.append(ellipse(ox2 + x * 52, oy2, 9, f(x), 'a', 1.4, .9))
    o.append(text(ox2 + 105, oy2 + 86, 'V = π ∫ y² dx', 15, op=.8, anchor='middle'))
    # bottom-left: slope field and a solution of dy/dx = ky
    ox3, oy3 = 90, 650
    for i in range(6):
        for j in range(4):
            x, y = ox3 + 20 + i * 40, oy3 - 25 - j * 38
            slope = .35 * (oy3 - y) / 38 + .2
            dx = 13 / math.sqrt(1 + slope * slope)
            o.append(line(x - dx, y + dx * slope, x + dx, y - dx * slope, 's', 1.3, .6))
    o.append(poly(curve(lambda x: 18 * math.exp(.62 * x), 0, 4.15, ox3 + 10, oy3, 56, 1), 'm', 2.6))
    o.append(text(ox3 + 120, oy3 + 28, 'dy/dx = ky', 14, op=.75, anchor='middle'))
    # bottom-right: implicit curve with a tangent
    cx2, cy2 = 620, 575
    o.append(ellipse(cx2, cy2, 95, 52, 'm', 2.4, rot=-35))
    t = math.radians(60)
    rx, ry, rot = 95, 52, math.radians(-35)
    ex, ey = rx * math.cos(t), ry * math.sin(t)
    px = cx2 + ex * math.cos(rot) - ey * math.sin(rot)
    py = cy2 + ex * math.sin(rot) + ey * math.cos(rot)
    dx_, dy_ = -rx * math.sin(t), ry * math.cos(t)
    vx, vy = dx_ * math.cos(rot) - dy_ * math.sin(rot), dx_ * math.sin(rot) + dy_ * math.cos(rot)
    n = math.hypot(vx, vy)
    o.append(line(px - 90 * vx / n, py - 90 * vy / n, px + 90 * vx / n, py + 90 * vy / n, 'a', 2))
    o.append(dot(px, py, 5, 'a'))
    o.append(text(cx2, cy2 + 92, 'x² + xy + y² = 7', 14, op=.75, anchor='middle'))
    o.append(tag(58, 100, '01', 'PARAMETRIC EQUATIONS'))
    o.append(tag(500, 100, '02', 'VOLUMES'))
    o.append(tag(58, 470, '03', 'DIFFERENTIAL EQUATIONS'))
    o.append(tag(588, 445, '04', 'VECTORS'))
    o.append(_caption(400, 692, '∫ u dv = uv − ∫ v du', 16))
    o.append(_caption(640, 320, '(1 + x)ⁿ = 1 + nx + …', 14))
    o.append(_caption(150, 335, 'A/(x + 1) + B/(x − 2)', 14))
    return svg(''.join(o))


# ---------------------------------------------------------------- IAL M1
def plate_wme01() -> str:
    o = []
    # centre: velocity-time graph, area = displacement
    ox, oy = 300, 450
    o.append(axes(ox, oy, 0, 230, 150, 0, xl='t', yl='v'))
    vt = [(ox, oy - 30), (ox + 60, oy - 120), (ox + 160, oy - 120), (ox + 215, oy)]
    o.append(poly([(ox, oy)] + vt + [(ox, oy)], None, 0, fill='a', fill_op=.2, closed=True))
    o.append(poly(vt, 'm', 2.8))
    o.append(text(ox + 108, oy - 50, 's = area', 14, 'a', anchor='middle'))
    o.append(text(ox - 12, oy - 26, 'u', 15, op=.8, anchor='end'))
    # top-left: pulley with two particles
    px, py = 175, 160
    o.append(line(px - 60, 100, px + 60, 100, 'm', 1.6, .7))
    o.append(line(px, 100, px, py - 22, 'm', 1.6))
    o.append(circle(px, py, 22, 'm', 2.2))
    o.append(dot(px, py, 3.5, 'm'))
    o.append(line(px - 22, py, px - 22, 245, 'm', 1.6))
    o.append(line(px + 22, py, px + 22, 215, 'm', 1.6))
    o.append(rect(px - 44, 245, 44, 40, 'm', 1.8, fill='s', fill_op=.18))
    o.append(rect(px + 4, 215, 36, 32, 'a', 1.8, fill='a', fill_op=.25))
    o.append(text(px - 22, 272, 'M', 15, anchor='middle'))
    o.append(text(px + 22, 237, 'm', 15, 'a', anchor='middle'))
    o.append(arrow(px - 52, 230, px - 52, 205, 's', 1.4, 7))
    o.append(text(px - 64, 222, 'T', 14, op=.75, anchor='end'))
    # top-right: moments on a beam
    bx, by = 500, 220
    o.append(rect(bx, by - 8, 230, 12, 'm', 1.8, fill='s', fill_op=.2))
    o.append(poly([(bx + 150, by + 4), (bx + 136, by + 34), (bx + 164, by + 34)], 'm', 1.8, closed=True))
    o.append(arrow(bx + 15, by - 80, bx + 15, by - 10, 'a', 2.2, 10))
    o.append(arrow(bx + 215, by - 70, bx + 215, by - 10, 'a', 2.2, 10))
    o.append(arrow(bx + 150, by + 90, bx + 150, by + 36, 's', 1.8, 9))
    o.append(text(bx + 15, by - 90, 'W₁', 14, 'a', anchor='middle'))
    o.append(text(bx + 215, by - 80, 'W₂', 14, 'a', anchor='middle'))
    o.append(text(bx + 162, by + 84, 'R', 14, op=.8))
    o.append(text(bx + 60, by + 56, 'Σ M = 0', 15, op=.75, anchor='middle'))
    # bottom-left: vectors, a particle moving with constant velocity
    gx, gy = 110, 650
    o.append(arrow(gx, gy, gx + 230, gy, 's', 1.4, 8))
    o.append(arrow(gx, gy, gx, gy - 165, 's', 1.4, 8))
    o.append(text(gx + 226, gy + 20, 'i', 16, op=.75))
    o.append(text(gx - 16, gy - 156, 'j', 16, op=.75))
    p0 = (gx + 30, gy - 25)
    step = (52, -36)
    for k in range(4):
        q = (p0[0] + k * step[0], p0[1] + k * step[1])
        o.append(dot(*q, 4.5, 'm'))
        o.append(text(q[0] + 10, q[1] + 18, f't = {k}', 12, op=.65))
    o.append(line(*p0, p0[0] + 3.4 * step[0], p0[1] + 3.4 * step[1], 'm', 1.6, .7, '6 5'))
    o.append(arrow(*p0, p0[0] + step[0], p0[1] + step[1], 'a', 2.8, 11))
    o.append(text(p0[0] + 18, p0[1] - 30, 'v', 17, 'a'))
    o.append(text(gx + 190, gy - 52, 'r = r₀ + vt', 15, op=.8, anchor='middle'))
    # bottom-right: particle on a rough inclined plane
    ix, iy = 450, 640
    o.append(poly([(ix, iy), (ix + 280, iy), (ix + 280, iy - 160)], 'm', 2, closed=True,
                  fill='s', fill_op=.12))
    ang = math.atan2(160, 280)
    cxp, cyp = ix + 160, iy - 160 * 160 / 280
    ux, uy = math.cos(ang), -math.sin(ang)
    nx_, ny_ = -uy, ux
    blk = [(cxp - 22 * ux, cyp - 22 * uy), (cxp + 22 * ux, cyp + 22 * uy),
           (cxp + 22 * ux - 30 * nx_, cyp + 22 * uy - 30 * ny_),
           (cxp - 22 * ux - 30 * nx_, cyp - 22 * uy - 30 * ny_)]
    o.append(poly(blk, 'm', 2, closed=True, fill='a', fill_op=.25))
    mx, my = cxp - 15 * nx_, cyp - 15 * ny_
    o.append(arrow(mx, my, mx, my + 85, 'a', 2.2, 10))
    o.append(arrow(mx - 30 * nx_, my - 30 * ny_, mx - 95 * nx_, my - 95 * ny_, 's', 2, 9))
    o.append(arrow(mx - 22 * ux, my - 22 * uy, mx - 85 * ux, my - 85 * uy, 's', 2, 9))
    o.append(text(mx + 8, my + 100, 'mg', 14, 'a'))
    o.append(text(mx - 100 * nx_ + 6, my - 100 * ny_, 'R', 14, op=.8))
    o.append(text(mx - 92 * ux - 8, my - 92 * uy + 18, 'F', 14, op=.8, anchor='end'))
    o.append(path(f'M {ix + 52} {iy} A 52 52 0 0 0 {ix + 52 * math.cos(ang):.1f} '
                  f'{iy - 52 * math.sin(ang):.1f}', 'm', 1.2, .8))
    o.append(text(ix + 62, iy - 10, 'α', 15, op=.8))
    o.append(tag(58, 330, '01', 'DYNAMICS'))
    o.append(tag(510, 340, '02', 'MOMENTS'))
    o.append(tag(58, 455, '03', 'VECTORS'))
    o.append(tag(570, 400, '04', 'STATICS'))
    o.append(_caption(400, 76, 'v = u + at    s = ut + ½at²    v² = u² + 2as', 15))
    o.append(_caption(400, 692, 'F = ma        I = mv − mu', 16))
    return svg(''.join(o))


# ---------------------------------------------------------------- IAL S1
def plate_wst01() -> str:
    o = []
    # centre: the normal distribution, one standard deviation shaded
    mu, oy, sx, h = 400, 470, 58, 190
    pdf = lambda z: math.exp(-z * z / 2)
    band = curve(pdf, -1, 1, mu, oy, sx, h, 40)
    o.append(poly([(mu - sx, oy)] + band + [(mu + sx, oy)], None, 0, fill='a', fill_op=.22, closed=True))
    o.append(line(mu - 3.4 * sx, oy, mu + 3.4 * sx, oy, 'm', 1.4, .6))
    o.append(poly(curve(pdf, -3.3, 3.3, mu, oy, sx, h, 140), 'm', 2.8))
    o.append(line(mu, oy, mu, oy - h, 'a', 1.4, .9, '4 4'))
    for k, nm in [(-2, '−2σ'), (-1, '−σ'), (0, 'μ'), (1, 'σ'), (2, '2σ')]:
        o.append(line(mu + k * sx, oy, mu + k * sx, oy + 7, 'm', 1.2, .7))
        o.append(text(mu + k * sx, oy + 26, nm, 14, op=.75, anchor='middle'))
    o.append(text(mu + 1.25 * sx, oy - h + 52, 'N(μ, σ²)', 16, op=.9))
    # top-left: box plot
    bx, by = 90, 190
    o.append(line(bx, by, bx + 55, by, 'm', 1.6))
    o.append(rect(bx + 55, by - 22, 110, 44, 'm', 2, fill='s', fill_op=.18))
    o.append(line(bx + 100, by - 22, bx + 100, by + 22, 'a', 2.6))
    o.append(line(bx + 165, by, bx + 225, by, 'm', 1.6))
    for x in (bx, bx + 225):
        o.append(line(x, by - 12, x, by + 12, 'm', 1.6))
    o.append(dot(bx + 250, by, 4, 'a'))
    for x, nm in [(bx + 55, 'Q₁'), (bx + 100, 'Q₂'), (bx + 165, 'Q₃')]:
        o.append(text(x, by + 46, nm, 14, op=.75, anchor='middle'))
    # top-right: scatter with regression line
    ox, oy2 = 515, 290
    o.append(axes(ox, oy2, 0, 220, 170, 0, xl='x', yl='y'))
    pts = [(.3, .5), (.6, .9), (.9, .8), (1.2, 1.4), (1.5, 1.3), (1.8, 1.9), (2.1, 1.8),
           (2.4, 2.4), (2.7, 2.2), (3.0, 2.9), (3.3, 2.7), (3.6, 3.3)]
    for x, y in pts:
        o.append(dot(ox + x * 55, oy2 - y * 45, 4, 's'))
    o.append(line(ox + .1 * 55, oy2 - .5 * 45, ox + 3.85 * 55, oy2 - 3.45 * 45, 'a', 2.4))
    o.append(text(ox + 120, oy2 - 168, 'y = a + bx', 15, 'a', anchor='middle'))
    # bottom-left: Venn diagram
    o.append(rect(85, 520, 250, 150, 'm', 1.4, .7))
    o.append(circle(180, 595, 56, 'm', 2.2))
    o.append(circle(245, 595, 56, 'm', 2.2))
    o.append(path('M 212.5 548.6 A 56 56 0 0 1 212.5 641.4 A 56 56 0 0 1 212.5 548.6 Z', None, 0,
                  fill='a', fill_op=.35))
    o.append(text(150, 600, 'A', 16, op=.85, anchor='middle'))
    o.append(text(275, 600, 'B', 16, op=.85, anchor='middle'))
    o.append(text(98, 540, 'S', 14, op=.6))
    # bottom-right: histogram of a discrete distribution
    hx, hy = 505, 660
    for i, p in enumerate([.08, .2, .3, .22, .12, .06]):
        o.append(rect(hx + i * 36, hy - p * 420, 30, p * 420, 'm', 1.6,
                      fill='a' if i == 2 else 's', fill_op=.45 if i == 2 else .18))
    o.append(line(hx - 6, hy, hx + 222, hy, 'm', 1.4, .6))
    o.append(tag(58, 120, '01', 'MEASURES OF LOCATION & SPREAD'))
    o.append(tag(515, 100, '02', 'REGRESSION'))
    o.append(tag(85, 505, '03', 'PROBABILITY'))
    o.append(tag(505, 500, '04', 'DISTRIBUTIONS'))
    o.append(_caption(200, 300, 'x̄ = Σx / n', 16))
    o.append(_caption(420, 692, 'P(A | B) = P(A ∩ B) / P(B)', 15))
    o.append(_caption(400, 72, 'r = Sₓᵧ / √(SₓₓSᵧᵧ)', 15))
    o.append(_caption(400, 560, 'E(X) = Σ x P(X = x)', 14, op=.6))
    return svg(''.join(o))


# ---------------------------------------------------------------- IGCSE 4PM1
def plate_4pm1() -> str:
    o = []
    # centre: cuboid with the angle between a diagonal and the base
    x0, y0, w, d, h = 285, 480, 170, 74, 138
    dx, dy = d * .9, -d * .55
    A, B, C, D = (x0, y0), (x0 + w, y0), (x0 + w + dx, y0 + dy), (x0 + dx, y0 + dy)
    up = lambda p: (p[0], p[1] - h)
    o.append(poly([A, B, C], 'm', 2.2))
    o.append(poly([C, D, A], 's', 1.4, .8, '5 5'))
    o.append(poly([up(A), up(B), up(C), up(D)], 'm', 2.2, closed=True))
    for p in (A, B, C):
        o.append(line(*p, *up(p), 'm', 2.2))
    o.append(line(*D, *up(D), 's', 1.4, .8, '5 5'))
    o.append(poly([A, C], 'a', 1.6, dash='6 5'))
    o.append(poly([A, up(C)], 'a', 2.8))
    o.append(poly([A, C, up(C)], None, 0, fill='a', fill_op=.18, closed=True))
    o.append(text(A[0] + 58, A[1] - 22, 'θ', 17, 'a'))
    o.append(text(A[0] - 14, A[1] + 22, 'A', 15, op=.8))
    o.append(text(C[0] + 10, C[1] - h - 6, 'G', 15, op=.8))
    # top-left: unit circle
    cx, cy, r = 175, 205, 92
    o.append(circle(cx, cy, r, 'm', 2.2))
    o.append(line(cx - r - 14, cy, cx + r + 14, cy, 's', 1.2, .6))
    o.append(line(cx, cy - r - 14, cx, cy + r + 14, 's', 1.2, .6))
    t = math.radians(38)
    px, py = cx + r * math.cos(t), cy - r * math.sin(t)
    o.append(line(cx, cy, px, py, 'm', 2.2))
    o.append(line(px, py, px, cy, 'a', 2))
    o.append(line(cx, cy, px, cy, 'a', 2))
    o.append(dot(px, py, 4.5, 'a'))
    o.append(text(px + 8, cy - 30, 'sin θ', 13, 'a'))
    o.append(text(cx + 30, cy + 22, 'cos θ', 13, 'a'))
    # top-right: arithmetic series staircase
    sx, sy = 520, 250
    for i in range(7):
        hh = 16 + i * 15
        o.append(rect(sx + i * 30, sy - hh, 22, hh, 'm', 1.2, fill='a' if i == 6 else 's',
                      fill_op=.5 if i == 6 else .2))
    o.append(line(sx - 6, sy, sx + 214, sy, 'm', 1.4, .6))
    o.append(text(sx + 104, sy + 28, 'Sₙ = ½n[2a + (n − 1)d]', 14, op=.75, anchor='middle'))
    # bottom-left: area between curve and line
    ox, oy = 110, 650
    f = lambda x: .55 * x * x
    o.append(axes(ox, oy, 0, 230, 160, 0))
    band = curve(f, 0, 3, ox, oy, 60, 30, 40)
    o.append(poly(band + curve(lambda x: 1.65 * x, 3, 0, ox, oy, 60, 30, 2), None, 0,
                  fill='a', fill_op=.25, closed=True))
    o.append(poly(curve(f, 0, 3.55, ox, oy, 60, 30), 'm', 2.4))
    o.append(poly(curve(lambda x: 1.65 * x, 0, 3.4, ox, oy, 60, 30, 2), 's', 2))
    o.append(text(ox + 205, oy - 105, '∫ₐᵇ y dx', 15, op=.8))
    # bottom-right: vector parallelogram
    O = (500, 650)
    a_, b_ = (150, -30), (60, -110)
    s_ = (O[0] + a_[0] + b_[0], O[1] + a_[1] + b_[1])
    o.append(arrow(*O, O[0] + a_[0], O[1] + a_[1], 'm', 2.4, 10))
    o.append(arrow(*O, O[0] + b_[0], O[1] + b_[1], 'm', 2.4, 10))
    o.append(line(O[0] + a_[0], O[1] + a_[1], *s_, 's', 1.4, .8, '5 5'))
    o.append(line(O[0] + b_[0], O[1] + b_[1], *s_, 's', 1.4, .8, '5 5'))
    o.append(arrow(*O, *s_, 'a', 2.8, 11))
    o.append(text(O[0] + 80, O[1] + 4, 'a', 16, op=.85))
    o.append(text(O[0] + 16, O[1] - 66, 'b', 16, op=.85))
    o.append(text(s_[0] + 10, s_[1] - 4, 'a + b', 15, 'a'))
    o.append(tag(58, 100, '01', 'TRIGONOMETRY'))
    o.append(tag(520, 100, '02', 'SERIES'))
    o.append(tag(58, 470, '03', 'CALCULUS'))
    o.append(tag(520, 470, '04', 'VECTORS'))
    o.append(_caption(400, 76, 'logₐ x = log x / log a        a / sin A = b / sin B', 15))
    o.append(_caption(400, 692, 'α + β = −b/a        αβ = c/a', 15))
    return svg(''.join(o))


# ---------------------------------------------------------------- IGCSE 4MB1
def plate_4mb1() -> str:
    o = []
    # centre: angle at the centre is twice the angle at the circumference
    cx, cy, r = 400, 360, 122
    o.append(circle(cx, cy, r, 'm', 2.6))
    pt = lambda deg: (cx + r * math.cos(math.radians(deg)), cy - r * math.sin(math.radians(deg)))
    A, B, P = pt(215), pt(-35), pt(100)
    o.append(poly([A, (cx, cy), B], 'a', 2.4))
    o.append(poly([A, P, B], 'm', 2.2))
    o.append(path(f'M {cx - 22:.1f} {cy + 15:.1f} A 27 27 0 0 0 {cx + 22:.1f} {cy + 16:.1f}', 'a', 1.6))
    o.append(text(cx, cy + 44, '2θ', 16, 'a', anchor='middle'))
    o.append(text(P[0] + 4, P[1] + 42, 'θ', 16, op=.9, anchor='middle'))
    o.append(dot(cx, cy, 4, 'a'))
    tx = math.radians(-35)
    o.append(line(B[0] - 85 * math.sin(tx), B[1] - 85 * math.cos(tx),
                  B[0] + 34 * math.sin(tx), B[1] + 34 * math.cos(tx), 's', 1.6, .8))
    for p, nm in [(A, 'A'), (B, 'B'), (P, 'P')]:
        o.append(dot(*p, 4, 'm'))
    # top-left: Venn diagram in a universal set
    o.append(rect(80, 95, 240, 165, 'm', 1.6))
    o.append(text(92, 118, 'ξ', 16, op=.8))
    o.append(circle(170, 180, 58, 'm', 2))
    o.append(circle(235, 180, 58, 'm', 2))
    o.append(path('M 202.5 131.6 A 58 58 0 0 1 202.5 228.4 A 58 58 0 0 1 202.5 131.6 Z', None, 0,
                  fill='a', fill_op=.35))
    o.append(text(140, 186, 'A', 16, op=.85, anchor='middle'))
    o.append(text(265, 186, 'B', 16, op=.85, anchor='middle'))
    o.append(text(200, 288, 'n(A ∩ B)', 14, op=.75, anchor='middle'))
    # top-right: rotation by a matrix
    ox, oy = 620, 215
    o.append(line(ox - 110, oy, ox + 110, oy, 's', 1.2, .6))
    o.append(line(ox, oy - 110, ox, oy + 80, 's', 1.2, .6))
    tri = [(25, 15), (85, 15), (25, 60)]
    o.append(poly([(ox + x, oy - y) for x, y in tri], 'm', 2.2, closed=True, fill='s', fill_op=.2))
    o.append(poly([(ox - y, oy - x) for x, y in tri], 'a', 2.2, closed=True, fill='a', fill_op=.25))
    o.append(path(f'M {ox + 60} {oy - 30} A 60 60 0 0 0 {ox - 20} {oy - 60}', 'a', 1.2, .8, '4 4'))
    o.append(label(ox + 50, oy + 52, '( 0  −1 )', 13, op=.8, anchor='middle'))
    o.append(label(ox + 50, oy + 70, '( 1   0 )', 13, op=.8, anchor='middle'))
    # bottom-left: cone with its dimensions
    vx, vy, base, rr = 205, 470, 650, 78
    o.append(ellipse(vx, base, rr, 20, 'm', 2.2))
    o.append(poly([(vx - rr, base), (vx, vy), (vx + rr, base)], 'm', 2.4))
    o.append(line(vx, vy, vx, base, 'a', 1.6, dash='5 5'))
    o.append(line(vx, base, vx + rr, base, 'a', 1.8))
    o.append(text(vx + 8, (vy + base) / 2 + 4, 'h', 15, 'a'))
    o.append(text(vx + rr / 2, base + 18, 'r', 15, 'a', anchor='middle'))
    o.append(text(vx + rr / 2 + 14, (vy + base) / 2 - 8, 'l', 15, op=.85))
    o.append(text(vx - 118, base - 70, 'V = ⅓πr²h', 15, op=.75, anchor='middle'))
    # bottom-right: cumulative frequency curve
    ox2, oy2 = 500, 650
    o.append(axes(ox2, oy2, 0, 235, 165, 0, xl='', yl='cf'))
    cf = curve(lambda x: 150 / (1 + math.exp(-(x - 2.2) * 2.1)), 0, 4.4, ox2, oy2, 50, 1, 80)
    o.append(poly(cf, 'm', 2.6))
    o.append(line(ox2, oy2 - 75, ox2 + 2.2 * 50, oy2 - 75, 'a', 1.4, .9, '4 4'))
    o.append(line(ox2 + 2.2 * 50, oy2 - 75, ox2 + 2.2 * 50, oy2, 'a', 1.4, .9, '4 4'))
    o.append(dot(ox2 + 2.2 * 50, oy2 - 75, 4.5, 'a'))
    o.append(text(ox2 + 2.2 * 50, oy2 + 22, 'median', 13, 'a', anchor='middle'))
    o.append(tag(80, 82, '01', 'SETS'))
    o.append(tag(520, 82, '02', 'MATRICES'))
    o.append(tag(58, 455, '03', 'MENSURATION'))
    o.append(tag(500, 455, '04', 'STATISTICS'))
    o.append(_caption(400, 692, 'sin²θ + cos²θ = 1        a² = b² + c² − 2bc cos A', 14))
    o.append(_caption(620, 335, 'f⁻¹(x)      gf(x)', 14))
    return svg(''.join(o))


PLATES = {
    'WMA11': plate_wma11, 'WMA12': plate_wma12, 'WMA13': plate_wma13, 'WMA14': plate_wma14,
    'WME01': plate_wme01, 'WST01': plate_wst01, '4PM1': plate_4pm1, '4MB1': plate_4mb1,
}
