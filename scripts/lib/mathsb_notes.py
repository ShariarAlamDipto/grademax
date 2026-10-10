"""
The Summary and Formulae section printed at the front of the Maths B workbook.

Every chapter of 4MB1 and every section of it, in the order the book uses, so a
student working section 6.3 can turn to 6.3 here and find both what the topic
asks of them and the results it needs. It replaces the formulae-only sheet: a
list of results tells a reader what to write down but not when, and the sections
where Maths B loses marks – reverse percentages, bounds, the ambiguous case,
without-replacement probability – are the ones where the method matters more
than the formula.

Each section carries:
  * a SUMMARY: what the topic is, how the standard question is answered, and
    the mistake that most often costs the marks
  * KEY RESULTS: the formulae themselves

Sections with no question in the 2016-2022 corpus are still included. This is a
revision reference, not an index of the book – 4MB1 examines cumulative
frequency and combined transformations even in years the papers here do not.

TYPESET AS LATEX
----------------
Set with matplotlib's mathtext through lib.formula_render, which implements a
LaTeX subset and needs no TeX installation: real fraction bars, radicals with a
vinculum, and italic variables against upright function names.

mathtext has NO `pmatrix`, `array`, `\\atop` or `\\big`. For the 2x2 matrices of
chapter 5 use the `matrix()` and `column()` helpers below, which build a
`\\genfrac` – its delimiters scale and its rule can be set to zero width. The
fourth `\\genfrac` argument MUST be `0` (display style) or every entry is set at
script size and the matrices come out half the height of the text beside them.

CONVENTIONS
-----------
Angles are in degrees throughout; 4MB1 does not use radians. `n(A)` is the
number of elements of A. Vectors are bold, and a position vector is measured
from the origin.
"""

from __future__ import annotations


def matrix(a: str, b: str, c: str, d: str) -> str:
    """A 2x2 matrix, entries padded so the columns line up under each other."""
    return (r"\genfrac{(}{)}{0}{0}{" + a + r" \;\;\; " + b + "}{"
            + c + r" \;\;\; " + d + "}")


def column(x: str, y: str) -> str:
    return r"\genfrac{(}{)}{0}{0}{" + x + "}{" + y + "}"


# (chapter, [(section, title, [summary lines], [key result lines])])
Section = tuple[int, str, list[str], list[str]]
NOTES: list[tuple[int, list[Section]]] = [
    (1, [
        (1, "Fractions, decimals and percentages", [
            r"A percentage change is always measured against the ORIGINAL amount, "
            r"not the new one.",
            r"Work with a MULTIPLIER wherever you can: a 15 per cent rise is "
            r"$\times 1.15$, a 15 per cent fall is $\times 0.85$. Repeated changes "
            r"then multiply, so a rise followed by a fall is not a return to the start.",
            r"REVERSE percentage questions give you the value AFTER the change and "
            r"ask for the value before. Divide by the multiplier – subtracting the "
            r"percentage back off is the commonest error in this section.",
        ], [
            r"Percentage change $= \dfrac{\text{change}}{\text{original}} \times 100$",
            r"After a rise of $r$ per cent:  $\text{new} = \text{original} "
            r"\times \left(1 + \dfrac{r}{100}\right)$",
            r"Reverse:  $\text{original} = \dfrac{\text{new}}{1 + r/100}$",
            r"Compound growth over $n$ years:  $A = P\left(1+\dfrac{r}{100}\right)^{n}$"
            r"      Depreciation:  $A = P\left(1-\dfrac{r}{100}\right)^{n}$",
        ]),
        (2, "Ratio, proportion and rates of change", [
            r"To share in a ratio, add the parts to get the number of shares, then "
            r"find one share. If a question gives you the DIFFERENCE between two "
            r"portions, that difference is also a whole number of shares.",
            r"In proportion questions always find the constant $k$ first, from the "
            r"pair of values you are given, and only then answer the question asked.",
            r"Read whether the proportion is to $x$, to $x^{2}$ or to $\sqrt{x}$ – "
            r"and whether it is direct or inverse. Doubling $x$ multiplies $y$ by 4 "
            r"when $y \propto x^{2}$.",
        ], [
            r"Share $T$ in the ratio $a:b$:  $\dfrac{a}{a+b}T$ and $\dfrac{b}{a+b}T$",
            r"Direct:  $y \propto x^{n} \Rightarrow y = kx^{n}$"
            r"      Inverse:  $y \propto \dfrac{1}{x^{n}} \Rightarrow y = \dfrac{k}{x^{n}}$",
            r"$\text{speed} = \dfrac{\text{distance}}{\text{time}}$"
            r"      $\text{density} = \dfrac{\text{mass}}{\text{volume}}$"
            r"      $\text{pressure} = \dfrac{\text{force}}{\text{area}}$",
        ]),
        (3, "Indices, surds and standard form", [
            r"Index laws only combine powers of the SAME base, so rewrite $8$ as "
            r"$2^{3}$ or $27$ as $3^{3}$ before comparing indices.",
            r"A negative index means a reciprocal and a fractional index means a "
            r"root; neither ever makes a number negative.",
            r"Simplify a surd by taking out the largest square factor, and "
            r"rationalise a denominator by multiplying by its conjugate.",
        ], [
            r"$a^{m} \times a^{n} = a^{m+n}$      $a^{m} \div a^{n} = a^{m-n}$"
            r"      $(a^{m})^{n} = a^{mn}$      $a^{0} = 1$",
            r"$a^{-n} = \dfrac{1}{a^{n}}$      $a^{1/n} = \sqrt[n]{a}$"
            r"      $a^{m/n} = \sqrt[n]{a^{m}}$",
            r"$\sqrt{ab} = \sqrt{a}\,\sqrt{b}$"
            r"      $\sqrt{\dfrac{a}{b}} = \dfrac{\sqrt{a}}{\sqrt{b}}$"
            r"      $\dfrac{1}{a+\sqrt{b}} \times \dfrac{a-\sqrt{b}}{a-\sqrt{b}}$",
            r"Standard form $a \times 10^{n}$ with $1 \leq a < 10$",
        ]),
        (4, "Accuracy, bounds and estimation", [
            r"A measurement given to the nearest unit $u$ lies within half a unit "
            r"either side of the stated value.",
            r"To make a calculation as LARGE as possible, use the largest numerator "
            r"and the SMALLEST denominator – dividing by the lower bound gives the "
            r"upper bound. Subtraction reverses in the same way.",
            r"An estimate rounds every number to one significant figure before any "
            r"arithmetic, not after.",
        ], [
            r"To the nearest $u$:  bounds are $x - \dfrac{u}{2}$ and $x + \dfrac{u}{2}$",
            r"$(a+b)_{\max} = a_{\max} + b_{\max}$"
            r"      $(a-b)_{\max} = a_{\max} - b_{\min}$",
            r"$(ab)_{\max} = a_{\max}b_{\max}$"
            r"      $\left(\dfrac{a}{b}\right)_{\max} = \dfrac{a_{\max}}{b_{\min}}$",
        ]),
    ]),
    (2, [
        (1, "Set notation and Venn diagrams", [
            r"$\cup$ is union – everything in either set. $\cap$ is intersection – "
            r"only what is in both. $A'$ is everything in the universal set that is "
            r"NOT in $A$.",
            r"Shade the regions asked for before counting; a description in words "
            r"such as 'in $A$ but not in $B$' is safer written as $A \cap B'$.",
        ], [
            r"$\xi$ universal set      $\varnothing$ empty set"
            r"      $x \in A$      $x \notin A$      $A \subset B$",
            r"$\mathrm{n}(A)$ is the number of elements of $A$"
            r"      $\mathrm{n}(A) + \mathrm{n}(A') = \mathrm{n}(\xi)$",
        ]),
        (2, "Two-set problems", [
            r"Fill the INTERSECTION first, then subtract it from each set total to "
            r"get the parts that belong to one set only. Whatever is left over from "
            r"the universal set lies outside both.",
            r"If an unknown appears in more than one region, form an equation from "
            r"the fact that all four regions total $\mathrm{n}(\xi)$.",
        ], [
            r"$\mathrm{n}(A \cup B) = \mathrm{n}(A) + \mathrm{n}(B) "
            r"- \mathrm{n}(A \cap B)$",
            r"Only $A$:  $\mathrm{n}(A) - \mathrm{n}(A \cap B)$"
            r"      Neither:  $\mathrm{n}(\xi) - \mathrm{n}(A \cup B)$",
        ]),
        (3, "Three-set problems", [
            r"Always start in the CENTRE, with $\mathrm{n}(A \cap B \cap C)$, and "
            r"work outwards. Each pairwise overlap you are given includes the centre, "
            r"so subtract the centre before writing the region that is in exactly two "
            r"sets.",
            r"The eight regions of the diagram must add to $\mathrm{n}(\xi)$; that "
            r"total is what gives you the equation when a region is unknown.",
        ], [
            r"$\mathrm{n}(A \cup B \cup C) = \mathrm{n}(A) + \mathrm{n}(B) "
            r"+ \mathrm{n}(C)$",
            r"$\qquad - \;\mathrm{n}(A \cap B) - \mathrm{n}(A \cap C) "
            r"- \mathrm{n}(B \cap C) \; + \;\mathrm{n}(A \cap B \cap C)$",
        ]),
    ]),
    (3, [
        (1, "Expanding, factorising and simplifying", [
            r"Expanding two brackets gives four terms before collecting; expanding "
            r"three means expanding two first and then multiplying by the third.",
            r"Always take out the common factor BEFORE anything else – "
            r"$2x^{2}-8 = 2(x^{2}-4) = 2(x+2)(x-2)$ is a mark lost if the 2 is left "
            r"behind.",
            r"Recognising the difference of two squares saves most of the work "
            r"whenever both terms are squares and the sign is a minus.",
        ], [
            r"$(a+b)^{2} = a^{2} + 2ab + b^{2}$      $(a-b)^{2} = a^{2} - 2ab + b^{2}$",
            r"$a^{2} - b^{2} = (a+b)(a-b)$",
            r"$(x+p)(x+q) = x^{2} + (p+q)x + pq$",
        ]),
        (2, "Linear equations and inequalities", [
            r"Solve an inequality exactly as you would an equation, with ONE "
            r"exception: multiplying or dividing by a negative number reverses the "
            r"sign.",
            r"Give the answer in the form the question asks for – a list of "
            r"integers, an inequality, or a number line with an open circle for a "
            r"strict inequality and a filled one where equality is allowed.",
        ], [
            r"$-2x > 6 \;\Rightarrow\; x < -3$   (the sign turns)",
            r"$|x| < a \;\Leftrightarrow\; -a < x < a$",
        ]),
        (3, "Simultaneous equations", [
            r"Elimination is quickest when a variable already matches or can be made "
            r"to match; substitution is the one to use when one equation is already "
            r"solved for a variable, and the only one that works when an equation is "
            r"not linear.",
            r"Having found one variable, substitute back into the SIMPLER equation, "
            r"and check in the other – that check is free and catches sign slips.",
            r"A linear and a quadratic equation together give a quadratic with up to "
            r"two solution PAIRS; pair each $x$ with its own $y$.",
        ], [
            r"Elimination: make the coefficients of one variable equal, then add or "
            r"subtract",
            r"Substitution: make one variable the subject, then replace it in the "
            r"other equation",
        ]),
        (4, "Quadratic equations", [
            r"Try factorising first; use the formula when it will not factorise, and "
            r"complete the square when asked for a turning point or an exact form.",
            r"The discriminant $b^{2}-4ac$ answers 'how many roots' without solving, "
            r"and is what a question means by 'show that the equation has equal "
            r"roots'.",
            r"Reject a solution that the context forbids – a negative length or a "
            r"negative number of people.",
        ], [
            r"$x = \dfrac{-b \pm \sqrt{b^{2}-4ac}}{2a}$   for $ax^{2}+bx+c=0$",
            r"$ax^{2}+bx+c = a\left(x+\dfrac{b}{2a}\right)^{2} + c - \dfrac{b^{2}}{4a}$"
            r"      Vertex at $x = -\dfrac{b}{2a}$",
            r"$b^{2}-4ac > 0$ two roots,  $= 0$ equal roots,  $< 0$ no real roots",
        ]),
        (5, "Algebraic fractions", [
            r"Add and subtract over a common denominator; factorise every numerator "
            r"and denominator before attempting to cancel.",
            r"A FACTOR may be cancelled, a TERM may not: "
            r"$\dfrac{x+2}{x}$ does not simplify to $\dfrac{2}{1}$.",
            r"Solving an equation with fractions starts by multiplying every term by "
            r"the common denominator.",
        ], [
            r"$\dfrac{a}{b} \pm \dfrac{c}{d} = \dfrac{ad \pm bc}{bd}$"
            r"      $\dfrac{a}{b} \div \dfrac{c}{d} = \dfrac{a}{b} \times \dfrac{d}{c}$",
        ]),
        (6, "Rearranging formulae and changing the subject", [
            r"Undo the operations in reverse order, doing the same thing to both "
            r"sides each time.",
            r"When the new subject appears TWICE, collect those terms on one side, "
            r"factorise it out, and divide by the bracket. That is the step the "
            r"harder marks are for.",
            r"Squaring or square-rooting is done to the whole side, never term by "
            r"term.",
        ], [
            r"$ax + b = cx + d \;\Rightarrow\; x(a-c) = d-b \;\Rightarrow\; "
            r"x = \dfrac{d-b}{a-c}$",
        ]),
        (7, "Sequences and the nth term", [
            r"A constant FIRST difference means the sequence is linear and the "
            r"$n$th term is $dn + c$, where $d$ is that difference.",
            r"A constant SECOND difference means it is quadratic, and that second "
            r"difference is $2a$ in $an^{2}+bn+c$.",
            r"A constant RATIO between terms means it is geometric. Always test your "
            r"$n$th term on $n=1$ and $n=2$ before using it.",
        ], [
            r"Arithmetic, first term $a$, common difference $d$:  "
            r"$n\text{th term} = a + (n-1)d$",
            r"Geometric, first term $a$, common ratio $r$:  "
            r"$n\text{th term} = ar^{\,n-1}$",
            r"Quadratic:  second difference $= 2a$ in $an^{2}+bn+c$",
        ]),
        (8, "Factor and remainder theorem", [
            r"Substituting $x=a$ into $f(x)$ gives the remainder on division by "
            r"$(x-a)$; a remainder of zero means $(x-a)$ is a factor.",
            r"Two unknown coefficients need two equations – usually one factor and "
            r"one remainder, or two factors – solved simultaneously.",
            r"Having found one factor, divide to get a quadratic and factorise that; "
            r"do not hunt for the remaining roots by trial.",
        ], [
            r"$f(a) = 0 \;\Leftrightarrow\; (x-a)$ is a factor of $f(x)$",
            r"$f(x) \div (x-a)$ leaves remainder $f(a)$",
            r"$f(x) \div (ax-b)$ leaves remainder $f\!\left(\dfrac{b}{a}\right)$",
            r"$f(x) = (\text{divisor})(\text{quotient}) + \text{remainder}$",
        ]),
    ]),
    (4, [
        (1, "Function notation, domain and range", [
            r"$f(x)$ is a rule: whatever replaces $x$ on the left is substituted "
            r"everywhere on the right, brackets and all.",
            r"The DOMAIN is the set of allowed inputs and the RANGE is the set of "
            r"outputs it produces. A domain excludes anything that would divide by "
            r"zero or square-root a negative.",
            r"For a range, think about the shape: a quadratic's range starts at its "
            r"turning point.",
        ], [
            r"$f: x \mapsto 2x+1$ and $f(x) = 2x+1$ say the same thing",
            r"$\dfrac{1}{x-a}$ is undefined at $x=a$;  $\sqrt{x-a}$ needs $x \geq a$",
        ]),
        (2, "Composite functions", [
            r"$fg(x)$ means do $g$ FIRST and then $f$. Reading it left to right is "
            r"the standard error here.",
            r"Substitute the whole of $g(x)$ into $f$, in brackets, and only then "
            r"simplify.",
            r"$fg$ and $gf$ are different functions; solving $fg(x) = k$ usually "
            r"leads to a linear or quadratic equation.",
        ], [
            r"$fg(x) = f\left(g(x)\right)$ – apply $g$ first",
            r"In general $fg(x) \neq gf(x)$      $(fg)^{-1} = g^{-1}f^{-1}$",
        ]),
        (3, "Inverse functions", [
            r"To find $f^{-1}$: write $y = f(x)$, rearrange to make $x$ the subject, "
            r"then swap the letters.",
            r"The inverse undoes the function, so $ff^{-1}(x) = x$; its graph is the "
            r"graph of $f$ reflected in the line $y = x$.",
            r"The domain of $f^{-1}$ is the range of $f$.",
        ], [
            r"$ff^{-1}(x) = f^{-1}f(x) = x$",
            r"$y = f^{-1}(x)$ is $y = f(x)$ reflected in $y = x$",
        ]),
        (4, "Graphs of functions and graphical solutions", [
            r"Solve $f(x) = g(x)$ from a graph by reading the $x$-coordinates where "
            r"the two curves cross.",
            r"To solve $f(x) = k$ from a drawn curve, draw the horizontal line "
            r"$y = k$ and read off the intersections.",
            r"If the equation to solve is not the one plotted, rearrange it into "
            r"'plotted curve = a straight line' and draw that line.",
        ], [
            r"Intersections of $y = f(x)$ and $y = g(x)$ solve $f(x) = g(x)$",
        ]),
    ]),
    (5, [
        (1, "Matrix arithmetic", [
            r"Add and subtract entry by entry; matrices must be the same size.",
            r"Multiplication is ROW into COLUMN: the entry in row $i$, column $j$ "
            r"comes from row $i$ of the first matrix and column $j$ of the second. "
            r"The inner dimensions must match.",
            r"Order matters. $\mathbf{AB}$ and $\mathbf{BA}$ are usually different, "
            r"and may not both exist.",
        ], [
            r"$(m \times n)(n \times p) = (m \times p)$ – the inner numbers must match",
            r"$\mathbf{I} = " + matrix("1", "0", "0", "1")
            + r"$      $\mathbf{AI} = \mathbf{IA} = \mathbf{A}$",
        ]),
        (2, "Determinants and inverse matrices", [
            r"The determinant of a 2x2 matrix is $ad-bc$. If it is zero the matrix "
            r"is singular and has no inverse.",
            r"For the inverse, swap the leading diagonal, negate the other two "
            r"entries, and divide every entry by the determinant.",
            r"A question giving you $\det\mathbf{M}$ and an unknown entry is asking "
            r"you to solve $ad-bc = k$.",
        ], [
            r"$\mathbf{M} = " + matrix("a", "b", "c", "d")
            + r"$      $\det\mathbf{M} = ad - bc$",
            r"$\mathbf{M}^{-1} = \dfrac{1}{ad-bc}\," + matrix("d", "-b", "-c", "a")
            + r"$      $\mathbf{MM}^{-1} = \mathbf{I}$",
        ]),
        (3, "Solving simultaneous equations with matrices", [
            r"Write the pair of equations as a matrix equation, then multiply both "
            r"sides on the LEFT by the inverse.",
            r"The order matters: $\mathbf{M}^{-1}$ must go in front, not behind.",
        ], [
            r"$\mathbf{M}" + column("x", "y") + r" = " + column("e", "f")
            + r" \;\Rightarrow\; " + column("x", "y") + r" = \mathbf{M}^{-1}"
            + column("e", "f") + r"$",
        ]),
        (4, "Matrix transformations", [
            r"The COLUMNS of the matrix are the images of "
            r"$" + column("1", "0") + r"$ and $" + column("0", "1") + r"$. That is "
            r"how you read a matrix off a described transformation, and how you "
            r"describe the transformation a given matrix performs.",
            r"To transform a shape, write its vertices as columns of one matrix and "
            r"multiply once.",
            r"Combining transformations multiplies the matrices in the reverse of "
            r"the order performed: first $\mathbf{A}$, then $\mathbf{B}$, is "
            r"$\mathbf{BA}$.",
        ], [
            r"Rotation about $O$:  $90^{\circ}$ anticlockwise $"
            + matrix("0", "-1", "1", "0") + r"$      $180^{\circ}$ $"
            + matrix("-1", "0", "0", "-1") + r"$      $90^{\circ}$ clockwise $"
            + matrix("0", "1", "-1", "0") + r"$",
            r"Reflection in the $x$-axis $" + matrix("1", "0", "0", "-1") + r"$"
            r"      in the $y$-axis $" + matrix("-1", "0", "0", "1") + r"$",
            r"Reflection in $y=x$ $" + matrix("0", "1", "1", "0") + r"$"
            r"      in $y=-x$ $" + matrix("0", "-1", "-1", "0") + r"$",
            r"Enlargement centre $O$, factor $k$:  $" + matrix("k", "0", "0", "k") + r"$"
            r"      Area scale factor $= \left|\,\det\mathbf{M}\,\right|$",
        ]),
    ]),
    (6, [
        (1, "Angles, parallel lines and polygons", [
            r"On parallel lines: corresponding angles are equal, alternate angles are "
            r"equal, and co-interior angles add to $180^{\circ}$.",
            r"Quote the reason for every step – these questions are marked on the "
            r"reasoning as much as the number.",
            r"For polygons the exterior angles always total $360^{\circ}$, which is "
            r"usually the quicker route into a regular polygon.",
        ], [
            r"Angles: on a line $180^{\circ}$, at a point $360^{\circ}$, "
            r"in a triangle $180^{\circ}$, in a quadrilateral $360^{\circ}$",
            r"$n$-gon: interior sum $= (n-2) \times 180^{\circ}$"
            r"      exterior sum $= 360^{\circ}$",
            r"Regular $n$-gon: exterior $= \dfrac{360^{\circ}}{n}$"
            r"      interior $= 180^{\circ} - \dfrac{360^{\circ}}{n}$",
        ]),
        (2, "Triangles, congruence and similarity", [
            r"Congruent means identical in shape and size; name the case (SSS, SAS, "
            r"ASA, RHS) to earn the mark.",
            r"Similar means equal angles and sides in the same ratio. Identify the "
            r"pair of corresponding sides you know BOTH of, and use it to find the "
            r"scale factor before anything else.",
            r"Write corresponding vertices in matching order – triangle $ABC$ "
            r"similar to $PQR$ means $A$ corresponds to $P$.",
        ], [
            r"Congruence: SSS,  SAS,  ASA (or AAS),  RHS",
            r"Similar triangles: $\dfrac{a_{1}}{a_{2}} = \dfrac{b_{1}}{b_{2}} "
            r"= \dfrac{c_{1}}{c_{2}} = k$",
        ]),
        (3, "Circle theorems", [
            r"Look first for a diameter (angle in a semicircle), then for a tangent "
            r"(right angle to the radius), then for two angles standing on the same "
            r"arc.",
            r"Name the theorem you are using at each step; 'angles in the same "
            r"segment' is worth a mark on its own.",
            r"The alternate segment theorem is the one most often missed: the angle "
            r"between a tangent and a chord equals the angle in the alternate "
            r"segment.",
        ], [
            r"Angle at the centre $= 2 \times$ angle at the circumference on the "
            r"same arc",
            r"Angles in the same segment are equal      "
            r"Angle in a semicircle $= 90^{\circ}$",
            r"Cyclic quadrilateral: opposite angles sum to $180^{\circ}$",
            r"Tangent $\perp$ radius      Two tangents from a point are equal",
            r"Alternate segment: tangent-chord angle $=$ angle in the alternate segment",
            r"Intersecting chords: $AX \cdot XB = CX \cdot XD$"
            r"      Tangent and secant: $PT^{2} = PA \cdot PB$",
        ]),
        (4, "Pythagoras' theorem", [
            r"Only for right-angled triangles, and only with the hypotenuse opposite "
            r"the right angle.",
            r"Add the squares to find the hypotenuse, subtract to find a shorter "
            r"side.",
            r"In three dimensions apply it twice: once in the base, then in the "
            r"vertical triangle.",
        ], [
            r"$a^{2} + b^{2} = c^{2}$, with $c$ the hypotenuse",
        ]),
        (5, "Constructions and loci", [
            r"Use compasses, not measurement, and LEAVE ALL THE ARCS showing – they "
            r"are the evidence the mark is given for.",
            r"A locus at a fixed distance from a point is a circle; from a line, a "
            r"pair of parallels with semicircular ends.",
            r"For a region satisfying two conditions, construct each boundary and "
            r"then shade the overlap.",
        ], [
            r"Equidistant from two POINTS: the perpendicular bisector",
            r"Equidistant from two LINES: the angle bisector",
        ]),
        (6, "Coordinate geometry: gradient, length and midpoint", [
            r"The midpoint averages the coordinates; the length comes from "
            r"Pythagoras on the differences.",
            r"Subtract the coordinates in the SAME order in numerator and "
            r"denominator when finding a gradient.",
            r"Given a midpoint and one endpoint, work backwards: the other endpoint "
            r"is twice the midpoint minus the one you have.",
        ], [
            r"Midpoint $= \left(\dfrac{x_{1}+x_{2}}{2},\; "
            r"\dfrac{y_{1}+y_{2}}{2}\right)$",
            r"Length $= \sqrt{(x_{2}-x_{1})^{2} + (y_{2}-y_{1})^{2}}$"
            r"      Gradient $m = \dfrac{y_{2}-y_{1}}{x_{2}-x_{1}}$",
        ]),
        (7, "Equations of straight lines, parallel and perpendicular", [
            r"Find the gradient first, then use one point in "
            r"$y - y_{1} = m(x - x_{1})$.",
            r"Parallel lines share a gradient; perpendicular gradients multiply to "
            r"$-1$, so take the negative reciprocal.",
            r"Give the answer in the form asked for – $y = mx+c$ or "
            r"$ax+by+c=0$ with integer coefficients.",
        ], [
            r"$y = mx + c$      $y - y_{1} = m(x - x_{1})$",
            r"Parallel: $m_{1} = m_{2}$      Perpendicular: $m_{1}m_{2} = -1$",
        ]),
    ]),
    (7, [
        (1, "Perimeter and area of plane shapes", [
            r"Split a compound shape into rectangles and triangles, or subtract a "
            r"missing piece from a larger rectangle.",
            r"The height of a triangle or parallelogram is the PERPENDICULAR height, "
            r"not the slant side.",
            r"Check the units: an area in $\mathrm{cm}^{2}$ needs both lengths in cm.",
        ], [
            r"Triangle $= \dfrac{1}{2}bh$      Parallelogram $= bh$"
            r"      Trapezium $= \dfrac{1}{2}(a+b)h$",
            r"Circle: circumference $= 2\pi r = \pi d$      area $= \pi r^{2}$",
        ]),
        (2, "Circles, arcs and sectors", [
            r"An arc and a sector are both the fraction "
            r"$\dfrac{\theta}{360}$ of the whole circle – of the circumference for "
            r"an arc, of the area for a sector.",
            r"The PERIMETER of a sector is the arc plus two radii; forgetting the "
            r"radii is the usual slip.",
            r"A segment is the sector with the triangle cut off.",
        ], [
            r"Arc $= \dfrac{\theta}{360} \times 2\pi r$"
            r"      Sector $= \dfrac{\theta}{360} \times \pi r^{2}$",
            r"Segment $= \dfrac{\theta}{360}\pi r^{2} - \dfrac{1}{2}r^{2}\sin\theta$",
        ]),
        (3, "Volume and surface area of solids", [
            r"Any prism is its cross-sectional area times its length.",
            r"For surface area, count every face: a closed cylinder has two circles "
            r"and a rectangle, an open one has a single circle.",
            r"A cone's curved surface uses the SLANT height $l$, found by Pythagoras "
            r"from $r$ and $h$.",
        ], [
            r"Prism: $V = (\text{cross-section}) \times \text{length}$",
            r"Cylinder: $V = \pi r^{2}h$      curved surface $= 2\pi rh$",
            r"Cone: $V = \dfrac{1}{3}\pi r^{2}h$      curved surface $= \pi r l$"
            r"      $l = \sqrt{r^{2}+h^{2}}$",
            r"Sphere: $V = \dfrac{4}{3}\pi r^{3}$      surface $= 4\pi r^{2}$"
            r"      Pyramid: $V = \dfrac{1}{3}(\text{base})h$",
        ]),
        (4, "Similar shapes: length, area and volume", [
            r"If lengths are in the ratio $k$, areas are in $k^{2}$ and volumes in "
            r"$k^{3}$.",
            r"Work in that order: get the LENGTH scale factor first, even when the "
            r"question gives you two areas or two volumes – take the square or cube "
            r"root to recover $k$.",
            r"Mass and capacity behave like volume when the material is the same.",
        ], [
            r"Length $k$  $\Rightarrow$  area $k^{2}$  $\Rightarrow$  volume $k^{3}$",
            r"$k = \sqrt{\text{area ratio}} = \sqrt[3]{\text{volume ratio}}$",
        ]),
    ]),
    (8, [
        (1, "Vector arithmetic and magnitude", [
            r"Add vectors by adding components; a scalar multiple stretches a vector "
            r"and keeps its direction, and a negative reverses it.",
            r"The magnitude is Pythagoras on the components.",
            r"Two vectors are parallel exactly when one is a scalar multiple of the "
            r"other – that statement is what a 'show that they are parallel' "
            r"question wants.",
        ], [
            r"$\mathbf{a} = " + column("x", "y") + r"$      "
            r"$\left|\,\mathbf{a}\,\right| = \sqrt{x^{2}+y^{2}}$"
            r"      $\overrightarrow{BA} = -\overrightarrow{AB}$",
            r"$\mathbf{a} \parallel \mathbf{b} \;\Leftrightarrow\; "
            r"\mathbf{a} = k\mathbf{b}$",
        ]),
        (2, "Position vectors and geometric proof", [
            r"Travel around the shape: $\overrightarrow{AB}$ is 'back to the origin "
            r"then out to $B$', which is $\mathbf{b}-\mathbf{a}$.",
            r"For a point dividing a line in a given ratio, go to the start of the "
            r"segment and then the right fraction of the way along it.",
            r"To prove three points COLLINEAR, show one vector between them is a "
            r"multiple of another and say that they share a common point. Both halves "
            r"are needed.",
        ], [
            r"$\overrightarrow{AB} = \mathbf{b} - \mathbf{a}$"
            r"      Midpoint of $AB$: $\dfrac{1}{2}(\mathbf{a}+\mathbf{b})$",
            r"$P$ divides $AB$ in $m:n$:  $\overrightarrow{OP} = \mathbf{a} "
            r"+ \dfrac{m}{m+n}(\mathbf{b}-\mathbf{a})$",
        ]),
        (3, "Single transformations", [
            r"Describing a transformation fully is what earns the marks: a reflection "
            r"needs its mirror line, a rotation needs angle, direction AND centre, a "
            r"translation needs a column vector, an enlargement needs scale factor "
            r"and centre.",
            r"Find a centre of rotation by joining corresponding points and "
            r"constructing perpendicular bisectors.",
            r"A negative enlargement factor puts the image on the other side of the "
            r"centre, turned through $180^{\circ}$.",
        ], [
            r"Translation by $" + column("a", "b") + r"$"
            r"      Enlargement, centre $C$, factor $k$",
        ]),
        (4, "Combined and inverse transformations", [
            r"Perform combined transformations in the order stated, and describe the "
            r"single equivalent transformation of the FINAL image from the ORIGINAL "
            r"object.",
            r"In matrix form the order reverses: doing $\mathbf{A}$ then "
            r"$\mathbf{B}$ is the matrix $\mathbf{BA}$.",
            r"The inverse transformation is given by the inverse matrix, and undoes "
            r"the original exactly.",
        ], [
            r"First $\mathbf{A}$, then $\mathbf{B}$  $\Rightarrow$  $\mathbf{BA}$",
            r"Inverse transformation: $\mathbf{M}^{-1}$",
        ]),
    ]),
    (9, [
        (1, "Right-angled triangle trigonometry", [
            r"Label the sides relative to the angle you are using – opposite, "
            r"adjacent, hypotenuse – and then choose sine, cosine or tangent.",
            r"To find an angle, use the inverse function; to find a side, multiply or "
            r"divide as the rearrangement requires.",
            r"Keep full accuracy through the working and round only at the end.",
        ], [
            r"$\sin\theta = \dfrac{\text{opp}}{\text{hyp}}$      "
            r"$\cos\theta = \dfrac{\text{adj}}{\text{hyp}}$      "
            r"$\tan\theta = \dfrac{\text{opp}}{\text{adj}}$",
            r"$\sin 30^{\circ} = \cos 60^{\circ} = \dfrac{1}{2}$      "
            r"$\sin 60^{\circ} = \cos 30^{\circ} = \dfrac{\sqrt{3}}{2}$      "
            r"$\tan 45^{\circ} = 1$",
        ]),
        (2, "The sine rule", [
            r"Use the sine rule when you have a side and its OPPOSITE angle, plus "
            r"one more piece of information.",
            r"Put the unknown on top when finding a side, and invert the rule when "
            r"finding an angle.",
            r"The AMBIGUOUS case: if you are given two sides and a non-included "
            r"angle, there may be a second, obtuse answer – $180^{\circ}$ minus the "
            r"first. Check whether the question allows it.",
        ], [
            r"$\dfrac{a}{\sin A} = \dfrac{b}{\sin B} = \dfrac{c}{\sin C}$",
            r"Obtuse alternative: $180^{\circ} - A$",
        ]),
        (3, "The cosine rule and the area of a triangle", [
            r"Use the cosine rule when you have three sides, or two sides and the "
            r"INCLUDED angle – the cases the sine rule cannot start.",
            r"Rearrange it to find an angle from three sides.",
            r"The area formula needs the angle BETWEEN the two sides.",
        ], [
            r"$a^{2} = b^{2}+c^{2}-2bc\cos A$      "
            r"$\cos A = \dfrac{b^{2}+c^{2}-a^{2}}{2bc}$",
            r"Area $= \dfrac{1}{2}ab\sin C$",
        ]),
        (4, "Bearings and three-dimensional problems", [
            r"A bearing is measured clockwise from NORTH and always written with "
            r"three figures.",
            r"Draw the north line at each point; the angle between a bearing and its "
            r"reverse differs by $180^{\circ}$.",
            r"In three dimensions, find the right-angled triangle you need first. The "
            r"angle between a line and a plane sits between the line and its "
            r"projection onto that plane.",
        ], [
            r"Bearings: three figures, clockwise from north – $072^{\circ}$",
            r"Back bearing $=$ bearing $\pm 180^{\circ}$",
        ]),
        (5, "Trigonometric graphs and equations", [
            r"Sine and cosine repeat every $360^{\circ}$ and tangent every "
            r"$180^{\circ}$.",
            r"A trigonometric equation has more than one solution in a given range. "
            r"Find the first from the calculator, then use the symmetry of the graph "
            r"to find the rest.",
            r"Sketch the graph and the horizontal line – counting intersections is "
            r"the reliable way to be sure none is missed.",
        ], [
            r"$\sin(180^{\circ}-x) = \sin x$      $\cos(360^{\circ}-x) = \cos x$"
            r"      $\tan(180^{\circ}+x) = \tan x$",
            r"$\sin^{2}\theta + \cos^{2}\theta = 1$      "
            r"$\tan\theta = \dfrac{\sin\theta}{\cos\theta}$",
        ]),
    ]),
    (10, [
        (1, "Presenting and interpreting data", [
            r"Read the scale on every axis before answering; a bar chart's frequency "
            r"axis rarely goes up in ones.",
            r"When asked to compare two distributions, comment on an AVERAGE and on "
            r"the SPREAD, and say what each means in the context of the question.",
        ], [
            r"Compare: one measure of average, one measure of spread, both in context",
        ]),
        (2, "Averages and measures of spread", [
            r"From a frequency table the mean is $\sum fx \div \sum f$, not the mean "
            r"of the $x$ column.",
            r"With grouped data use the class MIDPOINT, and say that the answer is an "
            r"estimate because the original values are unknown.",
            r"The median of $n$ values is the $\frac{1}{2}(n+1)$th of the ORDERED "
            r"list; for a frequency table, count along the cumulative totals.",
        ], [
            r"$\bar{x} = \dfrac{\sum fx}{\sum f}$"
            r"      Median: the $\dfrac{n+1}{2}$th ordered value",
            r"Range $=$ largest $-$ smallest",
        ]),
        (3, "Cumulative frequency and box plots", [
            r"Cumulative frequency is plotted against the UPPER boundary of each "
            r"class, and the points are joined with a smooth curve.",
            r"Read the median at $\frac{n}{2}$, the quartiles at $\frac{n}{4}$ and "
            r"$\frac{3n}{4}$ up the cumulative axis.",
            r"The interquartile range measures spread and ignores extreme values, "
            r"which is why it is preferred to the range.",
        ], [
            r"$\mathrm{IQR} = Q_{3} - Q_{1}$",
            r"Box plot: minimum, $Q_{1}$, median, $Q_{3}$, maximum",
        ]),
        (4, "Histograms and frequency density", [
            r"A histogram has unequal class widths, so the vertical axis is FREQUENCY "
            r"DENSITY, never frequency.",
            r"The frequency is the AREA of the bar. To find the frequency in part of "
            r"a class, take that fraction of the bar's area.",
        ], [
            r"Frequency density $= \dfrac{\text{frequency}}{\text{class width}}$",
            r"Frequency $=$ frequency density $\times$ class width $=$ area of the bar",
        ]),
        (5, "Probability of single and combined events", [
            r"Probabilities of all outcomes total 1, which is how a missing "
            r"probability is found.",
            r"AND means multiply, OR means add. Only add directly when the events "
            r"cannot both happen.",
            r"For 'at least one', it is nearly always quicker to find the probability "
            r"of NONE and subtract from 1.",
        ], [
            r"$\mathrm{P}(A') = 1 - \mathrm{P}(A)$"
            r"      Mutually exclusive: $\mathrm{P}(A \cup B) = \mathrm{P}(A) "
            r"+ \mathrm{P}(B)$",
            r"Independent: $\mathrm{P}(A \cap B) = \mathrm{P}(A)\mathrm{P}(B)$",
            r"In general: $\mathrm{P}(A \cup B) = \mathrm{P}(A) + \mathrm{P}(B) "
            r"- \mathrm{P}(A \cap B)$",
            r"Expected number $= n \times \mathrm{P}(\text{success})$",
        ]),
        (6, "Tree diagrams and conditional probability", [
            r"Multiply ALONG the branches and add BETWEEN the separate outcomes that "
            r"satisfy the event.",
            r"WITHOUT replacement, the second set of branches changes: both the "
            r"numerator and the denominator fall, and the denominator falls by one "
            r"every time.",
            r"Label every branch with its probability before calculating; the "
            r"branches at each node must sum to 1.",
        ], [
            r"Along the branches: multiply      Between outcomes: add",
            r"Without replacement: the denominator falls by one each draw",
        ]),
    ]),
    (11, [
        (1, "Differentiating polynomials", [
            r"Multiply by the power, then reduce the power by one. The derivative of "
            r"a constant is zero.",
            r"Rewrite every term as a power of $x$ FIRST: $\dfrac{1}{x^{2}}$ becomes "
            r"$x^{-2}$ and $\sqrt{x}$ becomes $x^{1/2}$. Expand any brackets before "
            r"differentiating.",
        ], [
            r"$y = ax^{n} \;\Rightarrow\; \dfrac{dy}{dx} = nax^{\,n-1}$"
            r"      $y = c \;\Rightarrow\; \dfrac{dy}{dx} = 0$",
        ]),
        (2, "Gradients, tangents and normals", [
            r"The derivative evaluated at a point gives the gradient of the curve "
            r"there.",
            r"For a tangent, use that gradient with the point in "
            r"$y - y_{1} = m(x-x_{1})$; for the normal, use the negative reciprocal.",
            r"If only the $x$-coordinate is given, substitute into the original "
            r"equation to get $y$ before writing the line.",
        ], [
            r"Gradient at $x=a$:  $\left.\dfrac{dy}{dx}\right|_{x=a}$",
            r"Tangent gradient $m$;  normal gradient $-\dfrac{1}{m}$",
        ]),
        (3, "Turning points and their nature", [
            r"Set $\dfrac{dy}{dx} = 0$ and solve to find the $x$-coordinates, then "
            r"substitute back for $y$ – a turning point is a POINT and needs both "
            r"coordinates.",
            r"Determine the nature with the second derivative: positive means a "
            r"minimum, negative a maximum.",
            r"In a maximum or minimum problem, form the expression from the context "
            r"first, using any constraint to reduce it to one variable.",
        ], [
            r"Turning point: $\dfrac{dy}{dx} = 0$",
            r"$\dfrac{d^{2}y}{dx^{2}} > 0$ minimum      "
            r"$\dfrac{d^{2}y}{dx^{2}} < 0$ maximum",
            r"Increasing where $\dfrac{dy}{dx} > 0$;  decreasing where "
            r"$\dfrac{dy}{dx} < 0$",
        ]),
        (4, "Kinematics: displacement, velocity and acceleration", [
            r"Differentiating displacement gives velocity, and differentiating "
            r"velocity gives acceleration.",
            r"'At rest' or 'momentarily stationary' means $v = 0$; maximum or minimum "
            r"velocity means $a = 0$.",
            r"Distance from the origin is displacement; be careful when the object "
            r"changes direction, because distance TRAVELLED is then larger.",
        ], [
            r"$v = \dfrac{ds}{dt}$      $a = \dfrac{dv}{dt} = \dfrac{d^{2}s}{dt^{2}}$",
            r"At rest: $v = 0$      Maximum or minimum velocity: $a = 0$",
        ]),
    ]),
]


def flow_blocks(chapter_titles: dict[int, str],
                chapters: set[int] | None = None) -> list[dict]:
    """
    The reference section as blocks small enough to pack.

    A section is the smallest unit that still reads correctly on its own, so the
    chapter heading travels with its FIRST section and never sits alone at the
    foot of a page.

    `chapters` restricts the section to the chapters a volume actually contains,
    for the two-part print edition: a reader holding Part 2 should not be given
    eleven pages of summary of which half belong to a book they do not have.
    Passing None keeps every chapter, which is what the one-volume book does.
    """
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
