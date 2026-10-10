"""
Summary and Formulae for the IAL Statistics S1 (WST01) chapterwise workbook --
every section of migration 18's tree. Same shape and renderer as lib/p1_notes.py.
"""

from __future__ import annotations

Section = tuple[int, str, list[str], list[str]]

NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Modelling in probability and statistics", [
            r"A model simplifies the real world; refine it by comparing its predictions "
            r"with observed data. Comment in CONTEXT when asked if a model is suitable.",
        ], []),
    ]),
    (2, [
        (1, "Measures of location and dispersion", [
            r"Use the formula sheet's $S_{xx}$ form for the variance; quote standard "
            r"deviation, not variance, when asked for spread.",
        ], [
            r"$\bar{x} = \dfrac{\sum x}{n}$      $\sigma^2 = \dfrac{\sum x^2}{n} - \bar{x}^2 = \dfrac{S_{xx}}{n}$",
            r"$\bar{x} = \dfrac{\sum fx}{\sum f}$      $\sigma^2 = \dfrac{\sum fx^2}{\sum f} - \bar{x}^2$",
        ]),
        (2, "Coding", [
            r"Adding a constant changes the mean, not the spread; scaling changes both.",
        ], [
            r"$y = \dfrac{x - a}{b}$:  $\bar{x} = a + b\bar{y}$,  $\sigma_x = b\,\sigma_y$",
        ]),
        (3, "Quartiles, percentiles and linear interpolation", [
            r"For grouped data interpolate within the class: use the class BOUNDARIES.",
        ], [
            r"$Q = L + \dfrac{(\mathrm{position} - \mathrm{cf\ before})}{f} \times \mathrm{width}$",
        ]),
        (4, "Histograms and frequency density", [
            r"Area is proportional to frequency; use class boundaries for widths.",
        ], [
            r"$\mathrm{frequency\ density} = \dfrac{\mathrm{frequency}}{\mathrm{class\ width}}$",
        ]),
        (5, "Stem and leaf diagrams and box plots", [
            r"A stem and leaf needs a key. Plot outliers separately and end the whisker "
            r"at the most extreme value that is NOT an outlier.",
        ], [
            r"outlier: $< Q_1 - k(Q_3 - Q_1)$ or $> Q_3 + k(Q_3 - Q_1)$ (usually $k = 1.5$)",
        ]),
        (6, "Skewness, outliers and comparing distributions", [
            r"Compare a measure of location AND a measure of spread, in context.",
        ], [
            r"positive skew: $Q_3 - Q_2 > Q_2 - Q_1$, mean $>$ median",
        ]),
    ]),
    (3, [
        (1, "Sample space, elementary probability and the addition law", [
            r"Probabilities of all outcomes sum to 1.",
        ], [
            r"$P(A \cup B) = P(A) + P(B) - P(A \cap B)$      $P(A') = 1 - P(A)$",
        ]),
        (2, "Venn diagrams", [
            r"Fill the intersection first, then work outwards; the whole diagram sums to 1.",
        ], []),
        (3, "Conditional probability and independence", [
            r"To test independence, show $P(A \cap B) = P(A)P(B)$ (or that it does not) "
            r"with numbers, and conclude.",
        ], [
            r"$P(A \mid B) = \dfrac{P(A \cap B)}{P(B)}$      independent: $P(A \cap B) = P(A)P(B)$",
            r"mutually exclusive: $P(A \cap B) = 0$",
        ]),
        (4, "Tree diagrams and sampling with and without replacement", [
            r"Multiply along branches, add between branches. Without replacement the "
            r"second-stage denominators drop by one.",
        ], []),
    ]),
    (4, [
        (1, "Scatter diagrams and the summary statistics Sxx, Syy and Sxy", [], [
            r"$S_{xx} = \sum x^2 - \dfrac{(\sum x)^2}{n}$      $S_{xy} = \sum xy - \dfrac{\sum x \sum y}{n}$",
        ]),
        (2, "The product moment correlation coefficient", [
            r"$r$ lies between $-1$ and $1$; interpret its sign and strength in context. "
            r"Correlation is not causation.",
        ], [
            r"$r = \dfrac{S_{xy}}{\sqrt{S_{xx}S_{yy}}}$",
        ]),
        (3, "The least squares regression line, prediction and coding", [
            r"Predict only within the data range (interpolation); extrapolation is unreliable. "
            r"Interpret $b$ as the change in $y$ per unit increase in $x$.",
        ], [
            r"$y = a + bx$,  $b = \dfrac{S_{xy}}{S_{xx}}$,  $a = \bar{y} - b\bar{x}$",
        ]),
    ]),
    (5, [
        (1, "Probability distributions and the cumulative distribution function", [
            r"Use $\sum P(X = x) = 1$ to find an unknown constant.",
        ], [
            r"$F(x_0) = P(X \leq x_0)$",
        ]),
        (2, "Expectation and variance", [], [
            r"$E(X) = \sum xP(X = x)$      $\mathrm{Var}(X) = E(X^2) - [E(X)]^2$",
            r"$E(aX + b) = aE(X) + b$      $\mathrm{Var}(aX + b) = a^2\mathrm{Var}(X)$",
        ]),
        (3, "The discrete uniform distribution", [
            r"Each of $n$ values equally likely.",
        ], [
            r"$X \in \{1, \ldots, n\}$: $E(X) = \dfrac{n + 1}{2}$,  $\mathrm{Var}(X) = \dfrac{n^2 - 1}{12}$",
        ]),
    ]),
    (6, [
        (1, "Standardising, z-values and the Normal tables", [
            r"Sketch the curve and shade the region every time; use symmetry for negative $z$.",
        ], [
            r"$Z = \dfrac{X - \mu}{\sigma} \sim N(0, 1^2)$",
        ]),
        (2, "Finding an unknown mean or standard deviation", [
            r"Read $z$ from the percentage points table, form one equation per given "
            r"probability, and solve simultaneously.",
        ], [
            r"$\dfrac{x - \mu}{\sigma} = z$",
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
