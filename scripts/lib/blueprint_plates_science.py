"""Blueprint cover plates for IGCSE Physics, Chemistry, Biology, Human Biology, English B."""
from __future__ import annotations

import math

from blueprint_svg import (arrow, axes, circle, curve, dot, ellipse, label, line, path, poly,
                           rect, svg, tag, text)


def _caption(x, y, s, size=16, anchor='middle', op=.5) -> str:
    return text(x, y, s, size, op=op, anchor=anchor)


# ---------------------------------------------------------------- 4PH1
def plate_4ph1() -> str:
    o = []
    # centre: transverse wave with wavelength and amplitude
    ox, oy, A = 175, 418, 64
    lam = 180
    o.append(line(ox - 10, oy, ox + 460, oy, 's', 1.2, .6))
    o.append(poly(curve(lambda x: math.sin(2 * math.pi * x / lam), 0, 450, ox, oy, 1, A, 200), 'm', 3))
    c1, c2 = ox + lam / 4, ox + lam / 4 + lam
    o.append(line(c1, oy - A - 22, c2, oy - A - 22, 'a', 1.6))
    for c in (c1, c2):
        o.append(line(c, oy - A - 30, c, oy - A - 14, 'a', 1.6))
    o.append(text((c1 + c2) / 2, oy - A - 32, 'λ', 18, 'a', anchor='middle'))
    o.append(arrow(c1 - 24, oy, c1 - 24, oy - A + 2, 's', 1.6, 8))
    o.append(text(c1 - 34, oy - A / 2, 'A', 15, op=.8, anchor='end'))
    o.append(text(ox + 470, oy + 6, 'v = fλ', 16, op=.85))
    # top-left: velocity-time graph
    gx, gy = 95, 262
    o.append(axes(gx, gy, 0, 210, 150, 0, xl='t', yl='v'))
    vt = [(gx, gy), (gx + 70, gy - 110), (gx + 150, gy - 110), (gx + 200, gy)]
    o.append(poly(vt, None, 0, fill='a', fill_op=.18, closed=True))
    o.append(poly(vt, 'm', 2.6))
    o.append(text(gx + 110, gy - 50, 'distance', 13, 'a', anchor='middle'))
    # top-right: series circuit with cell, resistor and ammeter
    x0, y0, x1, y1 = 520, 120, 730, 270
    o.append(poly([(x0, y0 + 62), (x0, y0), (x0 + 75, y0)], 'm', 2))
    o.append(poly([(x0 + 135, y0), (x1, y0), (x1, y0 + 57)], 'm', 2))
    o.append(poly([(x1, y0 + 93), (x1, y1), (x0 + 121, y1)], 'm', 2))
    o.append(poly([(x0 + 89, y1), (x0, y1), (x0, y0 + 80)], 'm', 2))
    o.append(rect(x0 + 75, y0 - 12, 60, 24, 'm', 2.2, fill='a', fill_op=.3))
    o.append(line(x0 - 16, y0 + 62, x0 + 16, y0 + 62, 'm', 3))
    o.append(line(x0 - 8, y0 + 80, x0 + 8, y0 + 80, 'm', 3.6))
    o.append(circle(x1, y0 + 75, 18, 'm', 2.2))
    o.append(label(x1, y0 + 80, 'A', 13, op=1, anchor='middle'))
    o.append(circle(x0 + 105, y1, 16, 'm', 2))
    o.append(line(x0 + 94, y1 - 11, x0 + 116, y1 + 11, 'm', 1.6))
    o.append(line(x0 + 94, y1 + 11, x0 + 116, y1 - 11, 'm', 1.6))
    o.append(text(x0 + 105, y0 + 38, 'R', 15, 'a', anchor='middle'))
    o.append(text(x0 + 105, y1 + 44, 'V = IR', 15, op=.8, anchor='middle'))
    # bottom-left: radioactive decay from a nucleus
    nx, ny = 175, 590
    for i, (dx, dy) in enumerate([(0, 0), (12, -8), (-12, -6), (6, 12), (-8, 12), (16, 8), (-16, 6),
                                   (0, -16), (12, 18), (-4, 22)]):
        o.append(circle(nx + dx, ny + dy, 9, 'm', 1.4, fill='a' if i % 2 else 's', fill_op=.5))
    o.append(arrow(nx + 30, ny - 20, nx + 104, ny - 62, 'm', 2.2, 10))
    o.append(arrow(nx + 34, ny + 4, nx + 140, ny + 4, 'a', 2.2, 10))
    o.append(path(f'M {nx + 30} {ny + 26} q 15 -12 30 0 t 30 0 t 30 0', 's', 2))
    o.append(text(nx + 114, ny - 66, 'α', 17, op=.9))
    o.append(text(nx + 152, ny + 10, 'β', 17, 'a'))
    o.append(text(nx + 132, ny + 46, 'γ', 17, op=.85))
    # bottom-right: orbit around a star
    sx, sy = 615, 585
    o.append(ellipse(sx, sy, 120, 55, 'm', 1.8, .9))
    o.append(circle(sx - 25, sy, 20, 'a', 2, fill='a', fill_op=.35))
    for k in range(8):
        a = k * math.pi / 4
        o.append(line(sx - 25 + 26 * math.cos(a), sy + 26 * math.sin(a),
                      sx - 25 + 36 * math.cos(a), sy + 36 * math.sin(a), 'a', 1.6))
    o.append(dot(sx + 120, sy, 7, 'm'))
    o.append(arrow(sx + 120, sy, sx + 120, sy - 46, 's', 1.8, 8))
    o.append(text(sx, sy + 88, 'v = 2πr / T', 15, op=.8, anchor='middle'))
    o.append(tag(58, 100, '01', 'FORCES & MOTION'))
    o.append(tag(520, 86, '02', 'ELECTRICITY'))
    o.append(tag(58, 470, '03', 'RADIOACTIVITY'))
    o.append(tag(500, 500, '04', 'ASTROPHYSICS'))
    o.append(_caption(400, 692, 'F = ma        p = mv        ρ = m / V', 16))
    o.append(_caption(400, 536, 'ΔQ = mcΔT', 15))
    return svg(''.join(o))


# ---------------------------------------------------------------- 4CH1
def plate_4ch1() -> str:
    o = []
    # centre: sodium atom, electron arrangement 2.8.1
    cx, cy = 400, 380
    o.append(circle(cx, cy, 24, 'a', 2, fill='a', fill_op=.35))
    o.append(label(cx, cy + 5, 'Na', 13, op=1, anchor='middle'))
    for r, n, ph in [(55, 2, 0), (98, 8, .2), (141, 1, -.9)]:
        o.append(circle(cx, cy, r, 'm', 1.8, .85))
        for k in range(n):
            a = ph + 2 * math.pi * k / n
            o.append(circle(cx + r * math.cos(a), cy + r * math.sin(a), 6.5, 'm', 1.6,
                            fill='a' if r == 141 else 'm', fill_op=1))
    o.append(text(cx, cy + 176, '2.8.1', 16, op=.85, anchor='middle'))
    # top-left: ethanol, displayed formula
    bx, by = 110, 200
    atoms = {'C1': (bx + 40, by), 'C2': (bx + 110, by), 'O': (bx + 180, by), 'H': (bx + 225, by)}
    for p, q in [('C1', 'C2'), ('C2', 'O'), ('O', 'H')]:
        o.append(line(atoms[p][0] + 14, by, atoms[q][0] - 14, by, 'm', 2))
    o.append(line(bx - 4, by, bx + 26, by, 'm', 2))
    for c in ('C1', 'C2'):
        x = atoms[c][0]
        o.append(line(x, by - 14, x, by - 44, 'm', 2))
        o.append(line(x, by + 14, x, by + 44, 'm', 2))
        o.append(label(x, by - 50, 'H', 14, op=.8, anchor='middle'))
        o.append(label(x, by + 62, 'H', 14, op=.8, anchor='middle'))
    o.append(label(bx - 16, by + 5, 'H', 14, op=.8, anchor='middle'))
    for nm, (x, y) in atoms.items():
        o.append(label(x, y + 5, nm[0], 15, role='a' if nm == 'O' else 't', op=1, anchor='middle'))
    o.append(text(bx + 110, by + 100, 'C₂H₅OH', 15, op=.8, anchor='middle'))
    # top-right: reaction profile with activation energy
    ox, oy = 515, 300
    o.append(axes(ox, oy, 0, 220, 180, 0, xl='', yl='E'))
    prof = [(ox + 10, oy - 90)] + curve(lambda x: math.exp(-((x - 1) ** 2) * 6), 0, 2, ox + 40, oy - 90, 70, 75, 60)
    prof = prof + [(ox + 215, oy - 30)]
    prof[-2] = (ox + 180, oy - 30)
    o.append(poly(prof, 'm', 2.6))
    o.append(arrow(ox + 25, oy - 90, ox + 25, oy - 160, 'a', 1.8, 8))
    o.append(text(ox + 32, oy - 128, 'Eₐ', 15, 'a'))
    o.append(arrow(ox + 200, oy - 90, ox + 200, oy - 34, 's', 1.8, 8))
    o.append(line(ox + 150, oy - 90, ox + 210, oy - 90, 's', 1.2, .7, '4 4'))
    o.append(text(ox + 214, oy - 104, 'ΔH', 15, op=.85))
    # bottom-left: titration, burette over a conical flask
    fx, fy = 200, 655
    o.append(rect(fx - 9, 455, 18, 120, 'm', 1.8))
    o.append(rect(fx - 9, 520, 18, 55, None, 0, fill='a', fill_op=.4))
    o.append(line(fx, 575, fx, 592, 'm', 1.8))
    o.append(line(fx - 22, 568, fx + 22, 568, 'm', 1.8))
    o.append(path(f'M {fx - 14} 600 L {fx - 14} 615 L {fx - 62} {fy} L {fx + 62} {fy} '
                  f'L {fx + 14} 615 L {fx + 14} 600', 'm', 2.2))
    o.append(path(f'M {fx - 40} {fy - 24} L {fx - 62} {fy} L {fx + 62} {fy} L {fx + 40} {fy - 24} Z',
                  None, 0, fill='a', fill_op=.3))
    for k in range(4):
        o.append(line(fx + 9, 470 + k * 24, fx + 18, 470 + k * 24, 'm', 1.2, .7))
    o.append(text(fx + 50, 500, 'c = n / V', 15, op=.8))
    # bottom-right: rate of reaction, volume of gas against time
    ox2, oy2 = 500, 665
    o.append(axes(ox2, oy2, 0, 235, 140, 0, xl='t', yl='V'))
    o.append(poly(curve(lambda t: 112 * (1 - math.exp(-t * 1.6)), 0, 4.5, ox2, oy2, 50, 1), 'a', 2.6))
    o.append(poly(curve(lambda t: 112 * (1 - math.exp(-t * .7)), 0, 4.5, ox2, oy2, 50, 1), 'm', 2.2))
    o.append(text(ox2 + 52, oy2 - 120, 'faster', 13, 'a'))
    o.append(text(ox2 + 150, oy2 - 58, 'slower', 13, op=.8))
    o.append(tag(58, 100, '01', 'ORGANIC CHEMISTRY'))
    o.append(tag(515, 100, '02', 'ENERGETICS'))
    o.append(tag(58, 440, '03', 'QUANTITATIVE'))
    o.append(tag(515, 498, '04', 'RATES OF REACTION'))
    o.append(_caption(400, 72, 'n = m / Mᵣ        CH₄ + 2O₂ → CO₂ + 2H₂O', 15))
    return svg(''.join(o))


# ---------------------------------------------------------------- 4BI1
def _helix(o, cx, top, bottom, amp, turns=2.2):
    n = 160
    a = [(cx + amp * math.sin(2 * math.pi * turns * i / n), top + (bottom - top) * i / n) for i in range(n + 1)]
    b = [(cx - amp * math.sin(2 * math.pi * turns * i / n), top + (bottom - top) * i / n) for i in range(n + 1)]
    for i in range(4, n, 7):
        o.append(line(a[i][0], a[i][1], b[i][0], b[i][1], 'a' if (i // 7) % 2 else 's', 2.2, .85))
    o.append(poly(a, 'm', 3))
    o.append(poly(b, 's', 3))


def plate_4bi1() -> str:
    o = []
    _helix(o, 400, 150, 600, 70)
    o.append(label(400, 630, 'A — T   ·   C — G', 13, op=.7, anchor='middle'))
    # top-left: plant cell
    x, y, w, h = 85, 105, 210, 150
    o.append(rect(x, y, w, h, 'm', 2.6, rx=18))
    o.append(rect(x + 8, y + 8, w - 16, h - 16, 's', 1.4, rx=14))
    o.append(rect(x + 70, y + 34, 105, 80, 's', 1.4, .9, fill='s', fill_op=.12, rx=30))
    o.append(circle(x + 42, y + 50, 20, 'm', 2, fill='m', fill_op=.18))
    o.append(dot(x + 42, y + 50, 6, 'm'))
    for cx, cy, rot in [(x + 40, y + 115, 20), (x + 190, y + 40, -30), (x + 185, y + 120, 15),
                        (x + 120, y + 132, 0)]:
        o.append(ellipse(cx, cy, 15, 8, 'a', 1.6, fill='a', fill_op=.4, rot=rot))
    o.append(text(x + 105, y + h + 26, 'plant cell', 13, op=.75, anchor='middle'))
    # top-right: enzyme activity against temperature
    ox, oy = 515, 290
    o.append(axes(ox, oy, 0, 220, 170, 0, xl='T', yl='rate'))
    act = lambda t: 140 * math.exp(-((t - 2.6) / 1.05) ** 2) if t > 2.6 else 140 * (t / 2.6) ** 1.6
    pts = curve(act, 0, 4.2, ox, oy, 50, 1, 100)
    o.append(poly(pts, 'm', 2.6))
    o.append(line(ox + 2.6 * 50, oy - 140, ox + 2.6 * 50, oy, 'a', 1.4, .9, '4 4'))
    o.append(dot(ox + 2.6 * 50, oy - 140, 5, 'a'))
    o.append(text(ox + 2.6 * 50, oy + 22, 'optimum', 13, 'a', anchor='middle'))
    # bottom-left: Punnett square
    px, py, s = 120, 505, 58
    for i in range(3):
        o.append(line(px, py + i * s, px + 2 * s, py + i * s, 'm', 1.8))
        o.append(line(px + i * s, py, px + i * s, py + 2 * s, 'm', 1.8))
    for (i, j), g in {(0, 0): 'BB', (1, 0): 'Bb', (0, 1): 'Bb', (1, 1): 'bb'}.items():
        o.append(rect(px + i * s + 3, py + j * s + 3, s - 6, s - 6, None, 0,
                      fill='a' if g == 'bb' else 's', fill_op=.35 if g == 'bb' else .12))
        o.append(text(px + i * s + s / 2, py + j * s + s / 2 + 6, g, 16, op=.9, anchor='middle'))
    for i, g in enumerate('Bb'):
        o.append(text(px + i * s + s / 2, py - 10, g, 16, 'a', anchor='middle'))
        o.append(text(px - 14, py + i * s + s / 2 + 6, g, 16, 'a', anchor='middle'))
    o.append(text(px + s, py + 2 * s + 32, '3 : 1', 15, op=.8, anchor='middle'))
    # bottom-right: food chain
    nodes = [(575, 655, 'producer'), (640, 590, 'primary'), (705, 525, 'secondary')]
    o.append(circle(515, 668, 13, 'a', 2, fill='a', fill_op=.35))
    for k in range(8):
        a = k * math.pi / 4
        o.append(line(515 + 18 * math.cos(a), 668 + 18 * math.sin(a),
                      515 + 25 * math.cos(a), 668 + 25 * math.sin(a), 'a', 1.6))
    o.append(arrow(543, 664, 553, 660, 'a', 1.6, 8))
    for i, (x, y, nm) in enumerate(nodes):
        o.append(circle(x, y, 20, 'm', 2, fill='s', fill_op=.18))
        o.append(text(x, y + 38, nm, 12, op=.75, anchor='middle'))
        if i < 2:
            nx, ny = nodes[i + 1][:2]
            o.append(arrow(x + 15, y - 14, nx - 15, ny + 14, 'm', 2, 9))
    o.append(tag(85, 92, '01', 'CELLS'))
    o.append(tag(515, 100, '02', 'ENZYMES'))
    o.append(tag(70, 470, '03', 'GENETICS'))
    o.append(tag(560, 470, '04', 'ECOSYSTEMS'))
    o.append(_caption(330, 692, '6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂', 15))
    o.append(_caption(400, 82, 'magnification = image size / actual size', 14))
    return svg(''.join(o))


# ---------------------------------------------------------------- 4HB1
def _branch(o, x, y, ang, length, depth):
    if depth == 0:
        o.append(dot(x, y, 3.2, 'a'))
        return
    x2, y2 = x + length * math.sin(ang), y + length * math.cos(ang)
    o.append(line(x, y, x2, y2, 'm', .9 + depth * .5))
    for da in (-.45, .45):
        _branch(o, x2, y2, ang + da, length * .72, depth - 1)


def plate_4hb1() -> str:
    o = []
    # centre: motor neurone, cell body, myelinated axon, terminals
    cx, cy = 210, 390
    o.append(circle(cx, cy, 34, 'm', 2.6, fill='s', fill_op=.18))
    o.append(dot(cx, cy, 10, 'a'))
    for k in range(7):
        a = math.pi / 2 + k * math.pi / 6.5
        x1, y1 = cx + 34 * math.cos(a), cy - 34 * math.sin(a)
        x2, y2 = cx + 82 * math.cos(a), cy - 82 * math.sin(a)
        o.append(line(x1, y1, x2, y2, 'm', 2))
        o.append(line(x2, y2, x2 + 16 * math.cos(a + .6), y2 - 16 * math.sin(a + .6), 'm', 1.4))
        o.append(line(x2, y2, x2 + 16 * math.cos(a - .6), y2 - 16 * math.sin(a - .6), 'm', 1.4))
    o.append(line(cx + 34, cy, 590, cy, 'm', 2.4))
    for k in range(6):
        o.append(rect(270 + k * 52, cy - 14, 40, 28, 'a', 1.6, fill='a', fill_op=.28, rx=12))
    for da in (-.6, -.2, .2, .6):
        ex, ey = 590 + 60 * math.cos(da), cy + 60 * math.sin(da)
        o.append(line(590, cy, ex, ey, 'm', 1.8))
        o.append(circle(ex, ey, 6, 'm', 1.6, fill='m', fill_op=.6))
    o.append(arrow(330, cy + 44, 470, cy + 44, 's', 1.6, 8))
    o.append(text(400, cy + 72, 'impulse', 14, op=.75, anchor='middle'))
    # top-left: trachea and bronchial tree
    o.append(line(235, 112, 235, 150, 'm', 3.4))
    for da in (-.55, .55):
        _branch(o, 235, 150, da, 50, 4)
    # top-right: ECG trace
    ox, oy = 500, 228
    ecg = []
    for beat in range(2):
        b = ox + beat * 118
        ecg += [(b, oy), (b + 18, oy), (b + 26, oy - 12), (b + 34, oy), (b + 44, oy), (b + 50, oy + 14),
                (b + 58, oy - 82), (b + 66, oy + 24), (b + 72, oy), (b + 86, oy), (b + 96, oy - 22),
                (b + 108, oy), (b + 118, oy)]
    o.append(poly(ecg, 'm', 2.4))
    o.append(dot(ox + 58, oy - 82, 4.5, 'a'))
    o.append(text(ox + 58, oy - 92, 'R', 14, 'a', anchor='middle'))
    o.append(text(ox + 118, oy + 60, 'heart rate = 60 / R–R interval', 13, op=.7, anchor='middle'))
    # bottom-left: red blood cells and one white cell
    for x, y in [(130, 560), (195, 535), (180, 610), (250, 590), (115, 630)]:
        o.append(circle(x, y, 26, 'a', 2, fill='a', fill_op=.22))
        o.append(circle(x, y, 11, 'a', 1.2, .8))
    o.append(circle(285, 650, 30, 'm', 2, fill='s', fill_op=.15))
    o.append(path('M 270 645 q 8 -16 18 -2 q 10 -14 16 4 q -6 14 -18 6 q -10 10 -16 -8', 'm', 1.8,
                  fill='m', fill_op=.35))
    # bottom-right: spirometer trace with tidal volume
    ox2, oy2 = 480, 600
    o.append(line(ox2, oy2 + 40, ox2 + 250, oy2 + 40, 's', 1.2, .6))
    sp = curve(lambda x: math.sin(x * 2.4) * (16 + 34 * math.exp(-((x - 3.9) / .55) ** 2)),
               0, 6.2, ox2, oy2, 40, 1, 200)
    o.append(poly(sp, 'm', 2.4))
    o.append(line(ox2 + 26, oy2 - 16, ox2 + 26, oy2 + 16, 'a', 1.6))
    o.append(text(ox2 + 34, oy2 - 26, 'tidal volume', 13, 'a'))
    o.append(text(ox2 + 196, oy2 - 50, 'vital capacity', 13, op=.75))
    o.append(tag(58, 100, '01', 'GAS EXCHANGE'))
    o.append(tag(500, 100, '02', 'CIRCULATION'))
    o.append(tag(58, 500, '03', 'BLOOD'))
    o.append(tag(500, 520, '04', 'BREATHING'))
    o.append(tag(250, 300, '05', 'COORDINATION'))
    o.append(_caption(400, 692, 'C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + energy', 15))
    o.append(_caption(615, 322, 'cardiac output = SV × HR', 14))
    return svg(''.join(o))


# ---------------------------------------------------------------- 4EB1
def plate_4eb1() -> str:
    o = []
    # centre: an open book, text lines, an annotated phrase
    cx, top, bottom = 400, 250, 520
    o.append(path(f'M {cx} {top + 20} Q {cx - 90} {top - 15} {cx - 230} {top + 5} L {cx - 230} {bottom} '
                  f'Q {cx - 90} {bottom - 20} {cx} {bottom + 12} Z', 'm', 2.4, fill='s', fill_op=.08))
    o.append(path(f'M {cx} {top + 20} Q {cx + 90} {top - 15} {cx + 230} {top + 5} L {cx + 230} {bottom} '
                  f'Q {cx + 90} {bottom - 20} {cx} {bottom + 12} Z', 'm', 2.4, fill='s', fill_op=.08))
    o.append(line(cx, top + 20, cx, bottom + 12, 'm', 2))
    for i in range(9):
        y = top + 45 + i * 26
        for side in (-1, 1):
            x1, x2 = cx + side * 26, cx + side * (200 if i % 4 != 3 else 130)
            o.append(line(x1, y, x2, y, 's', 2, .75))
    o.append(line(cx + 40, top + 123, cx + 170, top + 123, 'a', 3.2))
    o.append(path(f'M {cx + 170} {top + 123} q 40 -10 58 -60', 'a', 1.6, dash='4 4'))
    o.append(text(cx + 238, top + 52, 'tone', 15, 'a'))
    o.append(rect(cx - 205, top + 140, 120, 26, 'a', 1.8, rx=12))
    # top: large quotation marks
    o.append(text(400, 205, '“  ”', 90, 'a', op=.9, anchor='middle'))
    # top-left: proof-reading marks
    lx, ly = 90, 120
    for i, wd in enumerate([190, 160, 205, 120]):
        o.append(line(lx, ly + i * 30, lx + wd, ly + i * 30, 'm', 2, .8))
    o.append(path(f'M {lx + 70} {ly + 38} l 8 -14 l 8 14', 'a', 2))
    o.append(text(lx + 78, ly + 20, 'insert', 12, 'a', anchor='middle'))
    o.append(text(lx + 222, ly + 6, '¶', 22, 'a'))
    o.append(path(f'M {lx + 40} {ly + 90} c 10 -12 26 -12 34 0 c 8 12 24 12 34 0', 'a', 1.6))
    # top-right: summary checklist
    rx, ry = 520, 110
    for i in range(4):
        o.append(rect(rx, ry + i * 34, 18, 18, 'm', 1.8, rx=3))
        o.append(line(rx + 32, ry + i * 34 + 9, rx + 32 + (150 - i * 18), ry + i * 34 + 9, 's', 2, .75))
        if i < 3:
            o.append(path(f'M {rx + 4} {ry + i * 34 + 9} l 5 6 l 10 -14', 'a', 2.4))
    # bottom-left: fountain-pen nib
    nx, ny = 200, 640
    o.append(path(f'M {nx} {ny} L {nx - 46} {ny - 110} Q {nx - 30} {ny - 150} {nx} {ny - 160} '
                  f'Q {nx + 30} {ny - 150} {nx + 46} {ny - 110} Z', 'm', 2.4, fill='s', fill_op=.15))
    o.append(line(nx, ny, nx, ny - 100, 'm', 1.6))
    o.append(circle(nx, ny - 100, 7, 'a', 2, fill='a', fill_op=.6))
    o.append(path(f'M {nx + 20} {ny + 6} q 40 -18 70 6 t 70 -2', 'a', 2.2))
    # bottom-right: plan for a piece of directed writing
    bx, by = 500, 588
    for i, (w_, op) in enumerate([(220, 1), (170, .8), (195, .8), (140, .8)]):
        o.append(rect(bx, by + i * 26 - 10, 8, 8, None, 0, fill='a' if i == 0 else 'm'))
        o.append(line(bx + 18, by + i * 26 - 6, bx + 18 + w_, by + i * 26 - 6, 'm', 2, op * .8))
    o.append(tag(58, 100, '01', 'READING'))
    o.append(tag(520, 92, '02', 'SUMMARY'))
    o.append(tag(70, 465, '03', 'WRITING'))
    o.append(tag(500, 556, '04', 'DIRECTED WRITING'))
    o.append(_caption(400, 566, 'audience  ·  purpose  ·  form', 16, op=.65))
    o.append(_caption(400, 692, 'argue  ·  persuade  ·  advise  ·  inform', 15))
    return svg(''.join(o))


PLATES = {'4PH1': plate_4ph1, '4CH1': plate_4ch1, '4BI1': plate_4bi1, '4HB1': plate_4hb1,
          '4EB1': plate_4eb1}
