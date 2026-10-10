"""
Summary and Formulae for the IAL Pure Mathematics P2 (WMA12) chapterwise
workbook -- every section of migration 27's P2 tree. Same shape and renderer as
lib/p1_notes.py.
"""

from __future__ import annotations

Section = tuple[int, str, list[str], list[str]]

NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Proof by exhaustion and disproof by counter-example", [
            r"Exhaustion: check EVERY case (e.g. odd and even $n$) and conclude. "
            r"One counter-example is enough to disprove a statement -- state it and show it fails.",
        ], []),
    ]),
    (2, [
        (1, "Algebraic division, the factor theorem and the remainder theorem", [
            r"Use the factor theorem to find one factor, then divide to factorise fully.",
        ], [
            r"$f(a) = 0 \Leftrightarrow (x - a)$ is a factor      remainder on dividing by $(x - a)$ is $f(a)$",
            r"remainder on dividing by $(ax - b)$ is $f\left(\dfrac{b}{a}\right)$",
        ]),
    ]),
    (3, [
        (1, "Equation of a circle and its geometry", [
            r"Complete the square in $x$ and $y$ to find the centre and radius. A tangent is "
            r"perpendicular to the radius; the perpendicular from the centre bisects a chord.",
        ], [
            r"$(x - a)^2 + (y - b)^2 = r^2$, centre $(a, b)$, radius $r$",
        ]),
    ]),
    (4, [
        (1, "Sequences, nth terms and recurrence relations", [
            r"Generate terms from $u_{n+1} = f(u_n)$ one at a time; say whether the "
            r"sequence is increasing, decreasing or periodic.",
        ], []),
        (2, "Arithmetic sequences and series", [
            r"Two unknowns $a$ and $d$ need two equations. Watch whether the question "
            r"asks for a term or a sum.",
        ], [
            r"$u_n = a + (n - 1)d$      $S_n = \dfrac{n}{2}\left[2a + (n - 1)d\right] = \dfrac{n}{2}(a + l)$",
        ]),
        (3, "Geometric sequences and series", [
            r"A sum to infinity exists only when $|r| < 1$ -- state it.",
        ], [
            r"$u_n = ar^{n-1}$      $S_n = \dfrac{a(1 - r^n)}{1 - r}$      $S_\infty = \dfrac{a}{1 - r},\ |r| < 1$",
        ]),
        (4, "Binomial expansion for positive integer n", [
            r"Keep the sign and the power of the second term inside the bracket: "
            r"$(2 - 3x)^5$ has $b = -3x$.",
        ], [
            r"$(a + b)^n = a^n + \binom{n}{1}a^{n-1}b + \binom{n}{2}a^{n-2}b^2 + \ldots + b^n$",
            r"$\binom{n}{r} = \dfrac{n!}{r!(n - r)!}$",
        ]),
    ]),
    (5, [
        (1, "Exponential functions and their graphs", [
            r"$y = a^x$ passes through $(0, 1)$ and has the $x$-axis as an asymptote.",
        ], []),
        (2, "Laws of logarithms", [
            r"Combine logs into a single log before solving; $\log$ of a sum does not split.",
        ], [
            r"$\log_a x + \log_a y = \log_a xy$      $\log_a x - \log_a y = \log_a\dfrac{x}{y}$",
            r"$k\log_a x = \log_a x^k$      $\log_a a = 1$      $\log_a 1 = 0$",
        ]),
        (3, "Solving equations of the form a^x = b", [
            r"Take logs of both sides; a hidden quadratic appears when $2^{2x} = (2^x)^2$.",
        ], [
            r"$a^x = b \Rightarrow x = \dfrac{\log b}{\log a}$",
        ]),
    ]),
    (6, [
        (1, "Trigonometric identities", [
            r"Use the identities to write an equation in ONE trig function.",
        ], [
            r"$\tan\theta = \dfrac{\sin\theta}{\cos\theta}$      $\sin^2\theta + \cos^2\theta = 1$",
        ]),
        (2, "Solving trigonometric equations in a given interval", [
            r"Adjust the interval for $\sin(2\theta + 30^\circ)$ BEFORE solving, then find "
            r"every solution in it; do not divide by a trig function (you lose roots).",
        ], []),
    ]),
    (7, [
        (1, "Stationary points, maxima and minima", [
            r"Solve $\dfrac{dy}{dx} = 0$; classify with the second derivative.",
        ], [
            r"$\dfrac{d^2y}{dx^2} > 0$: minimum      $< 0$: maximum",
        ]),
        (2, "Increasing and decreasing functions and optimisation", [
            r"Increasing where $f'(x) > 0$. In optimisation, form the expression in ONE "
            r"variable using the constraint, then differentiate.",
        ], []),
    ]),
    (8, [
        (1, "Definite integrals", [
            r"Integrate, then substitute the limits: upper minus lower.",
        ], [
            r"$\int_a^b f'(x)\,dx = f(b) - f(a)$",
        ]),
        (2, "Area under and between curves", [
            r"Area below the $x$-axis integrates to a negative value -- split at the roots.",
            r"Between two curves integrate (top $-$ bottom) between their intersections.",
        ], []),
        (3, "The trapezium rule", [
            r"$n$ strips need $n + 1$ ordinates. An over- or underestimate depends on "
            r"whether the curve is convex or concave.",
        ], [
            r"$\int_a^b y\,dx \approx \dfrac{h}{2}\left[y_0 + 2(y_1 + \ldots + y_{n-1}) + y_n\right],\ h = \dfrac{b - a}{n}$",
        ]),
    ]),
]


def flow_blocks(chapter_titles: dict[int, str],
                chapters: set[int] | None = None) -> list[dict]:
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
