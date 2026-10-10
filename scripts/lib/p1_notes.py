"""
Summary and Formulae for the IAL Pure Mathematics P1 (WMA11) chapterwise
workbook -- every chapter and section of migration 27's P1 tree, in book order.
Same shape as lib/mathsb_notes.py and set by the same renderer
(lib.formula_render): per section a short summary (what is asked, the method,
the mistake that costs the marks) and its key results.
"""

from __future__ import annotations

Section = tuple[int, str, list[str], list[str]]

NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Laws of indices", [
            r"Write every term as a power of $x$ before differentiating or integrating: "
            r"$\sqrt{x} = x^{1/2}$, $\dfrac{1}{x^2} = x^{-2}$.",
            r"A negative or fractional index applies to the whole bracket it follows.",
        ], [
            r"$a^m \times a^n = a^{m+n}$      $a^m \div a^n = a^{m-n}$      $(a^m)^n = a^{mn}$",
            r"$a^{-n} = \dfrac{1}{a^n}$      $a^{1/n} = \sqrt[n]{a}$      $a^{m/n} = (\sqrt[n]{a})^m$",
        ]),
        (2, "Surds and rationalising denominators", [
            r"Simplify by taking out the largest square factor. To rationalise "
            r"$\dfrac{1}{a+\sqrt{b}}$ multiply top and bottom by $a-\sqrt{b}$.",
        ], [
            r"$\sqrt{ab} = \sqrt{a}\sqrt{b}$      $(a+\sqrt{b})(a-\sqrt{b}) = a^2 - b$",
        ]),
        (3, "Quadratic equations and completing the square", [
            r"Completing the square gives the vertex directly: the turning point of "
            r"$a(x+p)^2 + q$ is $(-p,\ q)$.",
        ], [
            r"$x^2 + bx + c = \left(x + \dfrac{b}{2}\right)^2 - \dfrac{b^2}{4} + c$",
            r"$x = \dfrac{-b \pm \sqrt{b^2 - 4ac}}{2a}$",
        ]),
        (4, "The discriminant", [
            r"Two real roots, one repeated root or no real roots. When a line meets a "
            r"curve, substitute and apply the discriminant to the resulting quadratic; "
            r"a tangent gives a repeated root.",
        ], [
            r"$b^2 - 4ac > 0$: two real roots      $= 0$: equal roots      $< 0$: no real roots",
        ]),
        (5, "Simultaneous equations", [
            r"Linear with quadratic: make one variable the subject of the LINEAR "
            r"equation and substitute. Give the solutions as pairs.",
        ], []),
        (6, "Linear and quadratic inequalities", [
            r"Find the critical values, sketch the parabola, then read off the region. "
            r"Multiplying or dividing by a negative reverses the inequality.",
            r"Use set notation or 'and'/'or' correctly: $x < 1$ or $x > 4$ is two regions.",
        ], []),
        (7, "Polynomials: expanding, factorising and simplifying", [
            r"Factorise fully before simplifying a fraction; take out a common factor first.",
        ], []),
        (8, "Sketching curves and graphs of functions", [
            r"Mark where the curve crosses BOTH axes and any asymptotes. A repeated "
            r"factor gives a point where the curve touches the axis.",
        ], [
            r"$y = \dfrac{k}{x}$: asymptotes $x = 0$ and $y = 0$",
        ]),
        (9, "Transformations of graphs", [
            r"Changes INSIDE the function act on $x$ and do the opposite of what they look like.",
        ], [
            r"$y = f(x) + a$: up $a$      $y = f(x + a)$: left $a$",
            r"$y = af(x)$: stretch parallel to the $y$-axis, scale factor $a$",
            r"$y = f(ax)$: stretch parallel to the $x$-axis, scale factor $\dfrac{1}{a}$",
        ]),
    ]),
    (2, [
        (1, "Equation of a straight line", [
            r"Use $y - y_1 = m(x - x_1)$; give the form the question asks for, "
            r"e.g. $ax + by + c = 0$ with integers.",
        ], [
            r"$m = \dfrac{y_2 - y_1}{x_2 - x_1}$      $y - y_1 = m(x - x_1)$",
        ]),
        (2, "Parallel and perpendicular lines", [
            r"Parallel lines share a gradient; perpendicular gradients multiply to $-1$.",
        ], [
            r"$m_1 m_2 = -1$",
        ]),
    ]),
    (3, [
        (1, "The sine and cosine rules and the area of a triangle", [
            r"Use the cosine rule for SAS or SSS, the sine rule otherwise. The sine rule "
            r"for an angle can have two answers ($\theta$ and $180^\circ - \theta$).",
        ], [
            r"$\dfrac{a}{\sin A} = \dfrac{b}{\sin B} = \dfrac{c}{\sin C}$",
            r"$a^2 = b^2 + c^2 - 2bc\cos A$      Area $= \dfrac{1}{2}ab\sin C$",
        ]),
        (2, "Radian measure, arc length and sector area", [
            r"These formulae need $\theta$ in RADIANS; set your calculator accordingly.",
        ], [
            r"$\pi$ radians $= 180^\circ$      $s = r\theta$      $A = \dfrac{1}{2}r^2\theta$",
        ]),
        (3, "Trigonometric graphs, symmetry and periodicity", [
            r"$\sin$ and $\cos$ have period $360^\circ$ ($2\pi$); $\tan$ has period $180^\circ$ "
            r"($\pi$) with asymptotes at $90^\circ$, $270^\circ$, ...",
        ], []),
    ]),
    (4, [
        (1, "Differentiating powers of x and the gradient function", [
            r"Rewrite roots and fractions as powers first; differentiate term by term.",
        ], [
            r"$\dfrac{d}{dx}(x^n) = nx^{n-1}$",
        ]),
        (2, "Tangents and normals", [
            r"Gradient of the tangent = $\dfrac{dy}{dx}$ at the point; the normal's "
            r"gradient is the negative reciprocal.",
        ], [
            r"$m_{normal} = -\dfrac{1}{m_{tangent}}$",
        ]),
    ]),
    (5, [
        (1, "Indefinite integration and the constant of integration", [
            r"Every indefinite integral needs $+c$; use a given point to find $c$.",
        ], [
            r"$\int x^n\,dx = \dfrac{x^{n+1}}{n+1} + c$,  $n \neq -1$",
        ]),
    ]),
]


def flow_blocks(chapter_titles: dict[int, str],
                chapters: set[int] | None = None) -> list[dict]:
    """The reference section as blocks for lib.formula_render; see mathsb_notes."""
    out: list[dict] = []
    for number, sections in NOTES:
        if chapters is not None and number not in chapters:
            continue
        for index, (section, title, summary, results) in enumerate(sections):
            out.append({
                "chapter": (f"{number}   {chapter_titles.get(number, '')}"
                            if index == 0 else None),
                "heading": f"{number}.{section}   {title}",
                "notes": summary,
                "lines": results,
            })
    return out
