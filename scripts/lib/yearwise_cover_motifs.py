"""Bounded, native-vector science and English artwork for GradeMax covers.

Canvas coordinates use ReportLab's bottom-left origin. ``draw_motif`` saves
and restores the caller's graphics state, clips to the supplied square and
draws in a normalized coordinate system. No fonts or image assets are needed.
"""

from __future__ import annotations

import math

from reportlab.lib.colors import HexColor


# Light accents for the dark fronts; matching deeper ink for cream backs.
PALETTES = {
    "4BI1": {"accent": "#78D8B1", "secondary": "#D9B66F", "ink": "#27745F"},
    "4HB1": {"accent": "#EE9C94", "secondary": "#78C7CC", "ink": "#A45752"},
    "4CH1": {"accent": "#9DB0F3", "secondary": "#70D6C8", "ink": "#52629A"},
    "4PH1": {"accent": "#78CBE6", "secondary": "#E4B96D", "ink": "#32748A"},
    "4EB1": {"accent": "#D9BC88", "secondary": "#96BCC7", "ink": "#8E6B39"},
}


def _path(c, points, close=False):
    p = c.beginPath()
    p.moveTo(*points[0])
    for x, y in points[1:]:
        p.lineTo(x, y)
    if close:
        p.close()
    c.drawPath(p, stroke=1, fill=0)


def _bezier(c, start, segments, close=False, fill=False):
    p = c.beginPath()
    p.moveTo(*start)
    for segment in segments:
        p.curveTo(*segment)
    if close:
        p.close()
    c.drawPath(p, stroke=1, fill=int(fill))


def _circle(c, x, y, r, fill=False):
    c.circle(x, y, r, stroke=1, fill=int(fill))


def _polyline(c, fn, start, end, count=160):
    _path(c, [fn(start + (end - start) * i / count) for i in range(count + 1)])


def _ellipse(c, x, y, a, b, angle=0):
    ca, sa = math.cos(angle), math.sin(angle)
    _polyline(c, lambda t: (x + a * math.cos(t) * ca - b * math.sin(t) * sa,
                           y + a * math.cos(t) * sa + b * math.sin(t) * ca),
              0, 2 * math.pi)


def _node(c, x, y, r, bg, colour):
    c.setFillColor(bg)
    c.setStrokeColor(colour)
    _circle(c, x, y, r, True)


def _cell(c, x, y, r, accent, secondary, muted, bg, phase=0):
    c.setStrokeColor(accent)
    _polyline(c, lambda t: (x + r * (1 + .045 * math.sin(5*t + phase)) * math.cos(t),
                           y + r * (1 + .045 * math.sin(5*t + phase)) * math.sin(t)),
              0, 2 * math.pi)
    c.setStrokeColor(muted)
    _circle(c, x, y, r*.90)
    c.setStrokeColor(secondary)
    _circle(c, x-r*.12, y+r*.07, r*.31)
    _circle(c, x-r*.12, y+r*.07, r*.11)
    for dx, dy, angle in [(.40, .34, -.6), (-.46, -.30, .7), (.26, -.43, -.3)]:
        ex, ey = x + r*dx, y+r*dy
        c.setStrokeColor(accent)
        _ellipse(c, ex, ey, r*.17, r*.075, angle)
        c.setStrokeColor(muted)
        _polyline(c, lambda t: (ex + r*.11*t, ey + r*.027*math.sin(t*9)), -1, 1, 30)
    c.setStrokeColor(muted)
    for dx, dy in [(-.50,.40), (.58,-.12), (-.14,-.55), (.20,.60)]:
        _circle(c, x+dx*r, y+dy*r, r*.027)


def _biology(c, accent, secondary, muted, bg):
    # DNA is a paired, antiparallel-looking projection: the rung endpoints
    # terminate on two sinusoidal sugar-phosphate rails, without stray bonds.
    c.setStrokeColor(muted)
    c.setDash(.012, .025)
    c.line(-.04, -.84, -.04, .84)
    c.setDash()
    for i in range(30):
        y = -.77 + i * 1.54 / 29
        s = math.sin((y + .77) * math.pi * 2 / .78)
        x1, x2 = -.04 + .255*s, -.04 - .255*s
        c.setStrokeColor(secondary if i % 3 else muted)
        c.setLineWidth(.005)
        c.line(x1, y, x2, y)
        if abs(s) > .2:
            c.setStrokeColor(accent)
            _circle(c, x1, y, .010)
            c.setStrokeColor(secondary)
            _circle(c, x2, y, .010)
    c.setLineWidth(.010)
    for sign, colour in [(1, accent), (-1, secondary)]:
        c.setStrokeColor(colour)
        _polyline(c, lambda y: (-.04 + sign*.255*math.sin((y+.77)*math.pi*2/.78), y), -.79, .79)
    c.setLineWidth(.0045)
    _cell(c, -.59, -.39, .23, accent, secondary, muted, bg, 1.4)
    _cell(c, .57, .38, .235, accent, secondary, muted, bg, .4)
    c.setStrokeColor(muted)
    c.setDash(.010, .022)
    _path(c, [(-.36,-.39),(-.29,-.39),(-.22,-.25)])
    _path(c, [(.34,.38),(.28,.38),(.17,.25)])
    c.setDash()
    for x, y, r in [(-.56,.52,.085),(.58,-.52,.11)]:
        c.setStrokeColor(muted)
        _circle(c,x,y,r)
        c.setStrokeColor(accent)
        _circle(c,x+.01,y-.005,r*.30)


def _human(c, accent, secondary, muted, bg):
    # A thoracic study: lobed lung silhouettes, cartilaginous trachea,
    # branching bronchi and an understated heart with its great vessels.
    c.setStrokeColor(accent)
    c.setLineWidth(.008)
    _bezier(c, (-.10,.41), [(-.20,.69,-.38,.62,-.48,.41),
             (-.60,.19,-.66,-.15,-.57,-.39),(-.46,-.54,-.18,-.47,-.12,-.31),
             (-.07,-.11,-.10,.14,-.10,.41)], close=True)
    _bezier(c, (.10,.41), [(.20,.67,.39,.61,.49,.38),
             (.62,.14,.65,-.17,.56,-.39),(.45,-.50,.31,-.45,.29,-.31),
             (.30,-.18,.13,-.14,.13,-.04),(.07,.09,.08,.27,.10,.41)], close=True)
    c.setStrokeColor(secondary)
    c.setLineWidth(.009)
    _path(c,[(-.035,.79),(-.035,.30),(-.18,.12)])
    _path(c,[(.035,.79),(.035,.30),(.19,.11)])
    c.setLineWidth(.004)
    for y in [.74,.69,.64,.59,.54,.49,.44,.39]:
        _bezier(c,(-.035,y),[(-.015,y-.012,.015,y-.012,.035,y)])
    # Two generations of airways in each lung.
    for side in [-1,1]:
        c.setStrokeColor(secondary)
        c.setLineWidth(.006)
        _path(c,[(side*.07,.26),(side*.26,.04),(side*.36,-.30)])
        for y,x in [(.14,.18),(.015,.27),(-.12,.31)]:
            _path(c,[(side*x,y),(side*(x+.11),y+.09),(side*(x+.18),y+.105)])
            _path(c,[(side*x,y),(side*(x+.10),y-.09),(side*(x+.14),y-.17)])
        c.setStrokeColor(muted)
        c.setLineWidth(.003)
        for x,y in [(.37,.24),(.46,.12),(.46,-.11),(.46,-.28),(.26,-.30)]:
            for dx,dy in [(-.023,0),(.019,.017),(.015,-.021)]:
                _circle(c,side*(x+dx),y+dy,.024)
    # Three-lobed right lung fissure and single left oblique fissure.
    c.setStrokeColor(muted)
    c.setLineWidth(.004)
    _bezier(c,(-.55,.015),[(-.40,.00,-.23,-.10,-.13,-.24)])
    _bezier(c,(-.57,-.14),[(-.42,-.16,-.30,-.12,-.24,-.09)])
    _bezier(c,(.55,.015),[(.43,-.02,.33,-.10,.29,-.21)])
    c.setStrokeColor(accent)
    c.setLineWidth(.006)
    _bezier(c,(-.04,-.06),[(-.17,-.10,-.20,-.31,-.05,-.46),
             (.02,-.54,.15,-.49,.20,-.30),(.25,-.15,.15,-.04,.06,-.08),
             (.015,-.13,-.015,-.13,-.04,-.06)],close=True)
    _bezier(c,(.06,-.08),[(.09,.00,.14,.025,.18,-.01)])
    _bezier(c,(.00,-.10),[(-.02,.015,.035,.07,.08,.05),(.12,.03,.09,-.015,.08,-.04)])
    c.setStrokeColor(muted)
    _bezier(c,(.025,-.17),[(.07,-.24,.035,-.36,-.025,-.43)])
    # A restrained electrocardiographic trace anchors the composition.
    c.setStrokeColor(secondary)
    c.setLineWidth(.0045)
    _path(c,[(-.72,-.68),(-.43,-.68),(-.37,-.65),(-.31,-.68),(-.20,-.68),
             (-.16,-.71),(-.11,-.56),(-.055,-.79),(.0,-.68),(.12,-.68),
             (.19,-.63),(.25,-.68),(.70,-.68)])


def _chemistry(c, accent, secondary, muted, bg):
    # Skeletal aromatic ring and extended bonds, paired with a projected
    # orbital study. The double bonds are inset to preserve clean vertices.
    cx, cy, r = -.17,-.18,.37
    vertices = [(cx+r*math.cos(math.pi/6+i*math.pi/3),
                 cy+r*math.sin(math.pi/6+i*math.pi/3)) for i in range(6)]
    c.setStrokeColor(accent)
    c.setLineWidth(.010)
    _path(c,vertices,True)
    c.setLineWidth(.0055)
    for i in [0,2,4]:
        p1,p2=vertices[i],vertices[(i+1)%6]
        _path(c,[(cx+.79*(p1[0]-cx)+.06*(p2[0]-p1[0]),
                   cy+.79*(p1[1]-cy)+.06*(p2[1]-p1[1])),
                  (cx+.79*(p2[0]-cx)+.06*(p1[0]-p2[0]),
                   cy+.79*(p2[1]-cy)+.06*(p1[1]-p2[1]))])
    c.setLineWidth(.007)
    c.setStrokeColor(secondary)
    _path(c,[vertices[0],(.40,.15),(.64,.01)])
    _path(c,[vertices[2],(-.69,.14),(-.78,.39)])
    _path(c,[vertices[4],(-.17,-.77)])
    _path(c,[(.40,.15),(.40,.36)])
    c.setLineWidth(.004)
    _path(c,[(.425,.16),(.425,.34)])
    for x,y,rn in [(.64,.01,.040),(-.78,.39,.040),(-.17,-.77,.035),(.40,.36,.036)]:
        _node(c,x,y,rn,bg,secondary)
    # Elliptic projections are orbital iconography rather than a claim that
    # electrons follow literal classical paths.
    ax,ay=.46,.57
    c.setLineWidth(.0045)
    for angle in [0,math.pi/3,-math.pi/3]:
        c.setStrokeColor(muted)
        _ellipse(c,ax,ay,.235,.084,angle)
    c.setStrokeColor(accent)
    _circle(c,ax,ay,.025)
    for t,angle in [(.70,0),(2.1,math.pi/3),(4.4,-math.pi/3)]:
        x=ax+.235*math.cos(t)*math.cos(angle)-.084*math.sin(t)*math.sin(angle)
        y=ay+.235*math.cos(t)*math.sin(angle)+.084*math.sin(t)*math.cos(angle)
        _node(c,x,y,.014,bg,secondary)
    # Small tetrahedral projection, separated from the aromatic structure.
    tx,ty=-.43,.62
    c.setStrokeColor(muted)
    c.setDash(.011,.018)
    c.line(tx,ty,tx-.12,ty+.15)
    c.setDash()
    c.setStrokeColor(accent)
    c.line(tx,ty,tx-.19,ty-.035)
    c.line(tx,ty,tx+.16,ty+.11)
    _path(c,[(tx-.014,ty-.012),(tx+.042,ty-.19),(tx+.075,ty-.17),(tx+.014,ty+.003)],True)
    for x,y in [(tx,ty),(tx-.12,ty+.15),(tx-.19,ty-.035),(tx+.16,ty+.11),(tx+.06,ty-.18)]:
        _node(c,x,y,.019,bg,secondary)


def _physics(c, accent, secondary, muted, bg):
    # A simple waveform with a faint envelope; no decorative fake equations.
    c.setStrokeColor(muted)
    c.setLineWidth(.003)
    c.line(-.82,.07,.82,.07)
    for x in [-.8,-.6,-.4,-.2,0,.2,.4,.6,.8]:
        c.line(x,.055,x,.085)
    c.setDash(.01,.025)
    c.line(-.82,.28,.82,.28)
    c.line(-.82,-.14,.82,-.14)
    c.setDash()
    c.setStrokeColor(accent)
    c.setLineWidth(.009)
    _polyline(c,lambda x:(x,.07+.205*math.sin((x+.82)*math.pi*3.2)), -.82,.82)
    # A complete series circuit with source, resistor and capacitor.
    c.setLineWidth(.0055)
    c.setStrokeColor(secondary)
    _path(c,[(-.52,.505),(-.52,.69),(-.29,.69)])
    _path(c,[(-.29,.69),(-.265,.72),(-.225,.66),(-.185,.72),(-.145,.66),
             (-.105,.72),(-.065,.66),(-.04,.69),(.33,.69),(.33,.54)])
    _path(c,[(.33,.47),(.33,.36),(-.52,.36),(-.52,.395)])
    c.line(.26,.54,.40,.54)
    c.line(.26,.47,.40,.47)
    _circle(c,-.52,.45,.055)
    _polyline(c,lambda x:(x,.45+.018*math.sin((x+.55)*math.pi/.03)), -.55,-.49,30)
    # Glass prism and a white-light path, splitting at the exit surface.
    # The internal ray bends toward the first surface normal and the
    # outgoing rays bend away from the second surface normal.
    c.setStrokeColor(accent)
    c.setLineWidth(.006)
    _path(c,[(-.38,-.29),(-.65,-.76),(-.11,-.76)],True)
    c.setStrokeColor(muted)
    c.setLineWidth(.003)
    _path(c,[(-.38,-.29),(-.38,-.76)])
    c.setStrokeColor(secondary)
    c.setLineWidth(.008)
    c.line(-.82,-.49,-.495,-.49)
    c.line(-.495,-.49,-.245,-.525)
    for endy, colour in [(-.78,secondary),(-.81,accent),(-.84,muted)]:
        c.setStrokeColor(colour)
        c.setLineWidth(.005)
        c.line(-.245,-.525,.35,endy)
    c.setStrokeColor(muted)
    c.setDash(.01,.018)
    c.setLineWidth(.003)
    c.line(-.58,-.54,-.41,-.44)
    c.line(-.33,-.575,-.16,-.475)
    c.setDash()


def _english(c, accent, secondary, muted, bg):
    # An open, sewn book. Its ruled strokes are abstract typesetting marks,
    # not simulated prose, preserving a quiet and legible editorial motif.
    c.setStrokeColor(accent)
    c.setLineWidth(.008)
    _bezier(c,(0,-.47),[(-.18,-.33,-.53,-.33,-.78,-.42),
             (-.78,-.14,-.75,.17,-.72,.38),(-.48,.48,-.19,.40,0,.25),
             (.20,.40,.49,.48,.72,.38),(.75,.16,.78,-.15,.78,-.42),
             (.53,-.33,.19,-.33,0,-.47)],close=True)
    c.setStrokeColor(secondary)
    c.setLineWidth(.0045)
    _bezier(c,(0,-.47),[(-.02,-.22,-.02,.06,0,.25)])
    _bezier(c,(-.78,-.46),[(-.47,-.39,-.18,-.39,0,-.52),
             (.18,-.39,.48,-.39,.78,-.46)])
    _bezier(c,(-.78,-.50),[(-.49,-.44,-.19,-.44,0,-.56),
             (.19,-.44,.49,-.44,.78,-.50)])
    for i in range(9):
        y=.25-i*.057
        c.setStrokeColor(secondary if i in [0,5] else muted)
        c.setLineWidth(.0033 if i not in [0,5] else .006)
        length=.52 if i not in [3,8] else .35
        _bezier(c,(-.64,y),[(-.47,y+.052,-.24,y+.015,-.64+length,y-.075)])
        _bezier(c,(.11,y-.075),[(.27,y+.015,.46,y+.052,.11+length,y)])
    # A pair of punctuation-shaped ribbons float above the page. These are
    # drawn paths, so the illustration remains entirely font-independent.
    c.setStrokeColor(accent)
    c.setLineWidth(.013)
    for offset in [-.20,.03]:
        _bezier(c,(offset,.72),[(offset-.09,.76,offset-.18,.65,offset-.12,.59),
                 (offset-.075,.54,offset-.015,.59,offset-.025,.64),
                 (offset-.03,.67,offset-.07,.67,offset-.08,.64)])
    # Flowing editorial rules suggest language and cadence without words.
    c.setStrokeColor(muted)
    c.setLineWidth(.0035)
    _bezier(c,(-.67,.54),[(-.50,.72,-.25,.85,.08,.83),(.33,.81,.54,.69,.66,.55)])
    _bezier(c,(-.57,.57),[(-.43,.72,-.22,.78,.04,.76),(.29,.73,.44,.65,.52,.55)])
    c.setStrokeColor(secondary)
    c.setLineWidth(.004)
    _path(c,[(.20,-.40),(.20,-.66),(.27,-.61),(.34,-.66),(.34,-.39)])
    for x,y,r in [(-.62,-.70,.018),(.62,.70,.018),(-.72,.08,.012)]:
        c.setStrokeColor(secondary)
        _circle(c,x,y,r)


_DRAWERS = {"4BI1": _biology, "4HB1": _human, "4CH1": _chemistry,
            "4PH1": _physics, "4EB1": _english}


def draw_motif(c, code: str, cx: float, cy: float, radius: float, dark: bool = True):
    """Draw subject line art fully within ``cx +/- radius, cy +/- radius``.

    Unsupported codes raise ``ValueError``. All five artboards leave generous
    internal margins; the square clip is a final guarantee against overflow.
    ``radius`` should normally be at least 90 pt for the finest details.
    """
    code = code.upper().strip()
    if code not in _DRAWERS:
        raise ValueError(f"Unsupported science/English motif: {code}")
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("radius must be finite and positive")
    palette = PALETTES[code]
    accent = HexColor(palette["accent"] if dark else palette["ink"])
    secondary = HexColor(palette["secondary"] if dark else palette["ink"])
    muted = HexColor("#3E606F" if dark else "#ADA99E")
    bg = HexColor("#091827" if dark else "#F2EFE7")
    c.saveState()
    try:
        bounds = c.beginPath()
        bounds.rect(cx-radius, cy-radius, 2*radius, 2*radius)
        c.clipPath(bounds, stroke=0, fill=0)
        c.translate(cx,cy)
        c.scale(radius,radius)
        c.setLineWidth(.004)
        c.setLineCap(1)
        c.setLineJoin(1)
        _DRAWERS[code](c,accent,secondary,muted,bg)
    finally:
        c.restoreState()
