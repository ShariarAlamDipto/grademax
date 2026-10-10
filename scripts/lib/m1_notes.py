"""
Summary and Formulae for the IAL Mechanics M1 (WME01) chapterwise workbook --
every section of migration 34's tree. Same shape and renderer as lib/p1_notes.py.
The kinematics and momentum formulae are the ones the specification says students
must know (they are NOT in the formula booklet).
"""

from __future__ import annotations

Section = tuple[int, str, list[str], list[str]]

NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Modelling assumptions", [
            r"Particle: no size, so no rotation. Light: mass ignored, tension the same "
            r"throughout. Inextensible: connected particles share the same acceleration. "
            r"Smooth: no friction. Say how the assumption was USED in the working.",
        ], []),
    ]),
    (2, [
        (1, "Magnitude, direction and resultant of vectors", [
            r"Give a direction as an angle with $\mathbf{i}$ or as a bearing -- whichever "
            r"the question asks for.",
        ], [
            r"$|a\mathbf{i} + b\mathbf{j}| = \sqrt{a^2 + b^2}$      angle with $\mathbf{i}$: $\tan\theta = \dfrac{b}{a}$",
        ]),
        (2, "Vectors for displacement, velocity, acceleration and force", [
            r"Position at time $t$ is the start position plus $t$ times the velocity. "
            r"'Due north of' means the $\mathbf{i}$ components are equal.",
        ], [
            r"$\mathbf{r} = \mathbf{r}_0 + \mathbf{v}t$      $\mathbf{F} = m\mathbf{a}$      $\mathbf{v} = \mathbf{u} + \mathbf{a}t$",
        ]),
    ]),
    (3, [
        (1, "Constant acceleration formulae", [
            r"List $s, u, v, a, t$; pick the formula without the quantity you neither "
            r"know nor want. Choose a positive direction and keep signs consistent.",
        ], [
            r"$v = u + at$      $s = ut + \dfrac{1}{2}at^2$      $s = vt - \dfrac{1}{2}at^2$",
            r"$v^2 = u^2 + 2as$      $s = \dfrac{(u + v)}{2}t$",
        ]),
        (2, "Vertical motion under gravity", [
            r"Take up as positive so $a = -9.8$; at the highest point $v = 0$. Give answers "
            r"to 2 or 3 significant figures when $g = 9.8$ is used.",
        ], [
            r"$g = 9.8\ \mathrm{m\,s^{-2}}$",
        ]),
        (3, "Motion graphs", [
            r"On a velocity-time graph the gradient is the acceleration and the area is "
            r"the displacement. Label the axes and key values on any sketch.",
        ], []),
    ]),
    (4, [
        (1, "Forces and Newton's laws of motion", [
            r"Draw a force diagram; resolve along the direction of motion and use resultant = $ma$.",
        ], [
            r"$F = ma$      $W = mg$",
        ]),
        (2, "Connected particles, pulleys and inclined planes", [
            r"Write $F = ma$ for EACH particle (or the whole system). Tension is the same on "
            r"both sides of a smooth pulley; the force on the pulley is the resultant of the two tensions.",
            r"On a slope resolve parallel ($mg\sin\alpha$) and perpendicular ($mg\cos\alpha$).",
        ], []),
        (3, "Momentum and impulse", [
            r"Momentum is conserved in a collision; keep the sign of each velocity. "
            r"Impulse is the change in momentum and has a direction.",
        ], [
            r"momentum $= mv$      $I = mv - mu$",
            r"$m_1u_1 + m_2u_2 = m_1v_1 + m_2v_2$",
        ]),
        (4, "Friction in motion", [
            r"When the particle is moving, friction is at its maximum and opposes the motion.",
        ], [
            r"$F = \mu R$",
        ]),
    ]),
    (5, [
        (1, "Resolving forces", [
            r"Resolve every force into two perpendicular directions; the resultant is "
            r"found from the totals by Pythagoras.",
        ], [
            r"components of $F$ at $\theta$: $F\cos\theta$ and $F\sin\theta$",
        ]),
        (2, "Equilibrium of a particle", [
            r"In equilibrium the forces in each of two directions sum to zero; a closed "
            r"triangle of forces is an alternative for three forces.",
        ], []),
        (3, "Friction in equilibrium", [
            r"'Limiting' or 'on the point of moving' means $F = \mu R$; otherwise "
            r"$F \leq \mu R$. Friction acts against the way the particle would move.",
        ], [
            r"$F \leq \mu R$",
        ]),
    ]),
    (6, [
        (1, "Moments and equilibrium of rods", [
            r"Take moments about the point that removes the most unknowns. 'About to tilt' "
            r"about a support means the reaction at the OTHER support is zero.",
        ], [
            r"moment $=$ force $\times$ perpendicular distance",
            r"equilibrium: resultant force $= 0$ and clockwise moments $=$ anticlockwise moments",
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
