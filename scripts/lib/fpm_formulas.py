"""
The formula sheet printed at the front of the Further Pure Maths workbook.

Every chapter of 4PM1 in the order the book uses, so a student can find the
result for the section they are working in. The groupings match the workbook's
own section titles rather than the specification's wording, because the reader
arrives here from a section heading and not from the syllabus.

TYPESET AS LATEX
----------------
Set with matplotlib's mathtext, which implements a LaTeX subset and needs no TeX
installation. That buys the things a formula sheet is judged on: fraction bars,
a radical with a proper vinculum, integrals and sums with their limits set above
and below, and italic variables against upright function names. The earlier HTML
version could only approximate those with slashes and Unicode.

Each line is an ordinary string; maths goes between $ signs, so a line can mix
prose and symbols the way a textbook does.

CONVENTIONS
-----------
Angles are in radians wherever calculus is involved; that is called out where it
matters rather than assumed. `c` is an arbitrary constant of integration.
"""

from __future__ import annotations

# (chapter number, [(group title, [line])]) -- maths inside $...$
SHEET: list[tuple[int, list[tuple[str, list[str]]]]] = [
    (1, [
        ("Indices", [
            r"$a^{m} \times a^{n} = a^{m+n}$      $a^{m} \div a^{n} = a^{m-n}$"
            r"      $(a^{m})^{n} = a^{mn}$",
            r"$a^{0} = 1$      $a^{-n} = \dfrac{1}{a^{n}}$"
            r"      $a^{m/n} = \sqrt[n]{a^{m}}$",
        ]),
        ("Surds", [
            r"$\sqrt{ab} = \sqrt{a}\,\sqrt{b}$"
            r"      $\sqrt{\dfrac{a}{b}} = \dfrac{\sqrt{a}}{\sqrt{b}}$",
            r"Rationalise:  $\dfrac{1}{a+\sqrt{b}} \times "
            r"\dfrac{a-\sqrt{b}}{a-\sqrt{b}}$",
        ]),
        ("Logarithms", [
            r"$\log_{a}(xy) = \log_{a}x + \log_{a}y$"
            r"      $\log_{a}\left(\dfrac{x}{y}\right) = \log_{a}x - \log_{a}y$",
            r"$\log_{a}(x^{n}) = n\log_{a}x$      $\log_{a}a = 1$"
            r"      $\log_{a}1 = 0$",
            r"$a^{x} = b \;\Leftrightarrow\; x = \log_{a}b$",
        ]),
        ("Change of base", [
            r"$\log_{a}x = \dfrac{\log_{b}x}{\log_{b}a}$"
            r"      $\log_{a}b = \dfrac{1}{\log_{b}a}$",
        ]),
    ]),
    (2, [
        (r"Roots of $ax^{2}+bx+c=0$", [
            r"$x = \dfrac{-b \pm \sqrt{b^{2}-4ac}}{2a}$",
        ]),
        ("Completing the square", [
            r"$ax^{2}+bx+c = a\left(x+\dfrac{b}{2a}\right)^{2} + c - \dfrac{b^{2}}{4a}$",
            r"Vertex at $x = -\dfrac{b}{2a}$;  minimum if $a>0$, maximum if $a<0$",
        ]),
        (r"Discriminant $\Delta = b^{2}-4ac$", [
            r"$\Delta > 0$ two distinct real roots      $\Delta = 0$ equal roots"
            r"      $\Delta < 0$ no real roots",
            r"$\Delta$ a perfect square (with $a,b,c$ rational) $\Rightarrow$ rational roots",
        ]),
        (r"Sum and product of roots $\alpha,\ \beta$", [
            r"$\alpha + \beta = -\dfrac{b}{a}$      $\alpha\beta = \dfrac{c}{a}$",
            r"New equation:  $x^{2} - (\alpha+\beta)x + \alpha\beta = 0$",
            r"$\alpha^{2}+\beta^{2} = (\alpha+\beta)^{2} - 2\alpha\beta$"
            r"      $(\alpha-\beta)^{2} = (\alpha+\beta)^{2} - 4\alpha\beta$",
            r"$\alpha^{3}+\beta^{3} = (\alpha+\beta)^{3} - 3\alpha\beta(\alpha+\beta)$"
            r"      $\dfrac{1}{\alpha}+\dfrac{1}{\beta} = \dfrac{\alpha+\beta}{\alpha\beta}$",
        ]),
    ]),
    (3, [
        ("Division", [
            r"$f(x) = (\mathrm{divisor})(\mathrm{quotient}) + \mathrm{remainder}$",
        ]),
        ("Remainder and factor theorems", [
            r"$f(x) \div (x-a)$ leaves remainder $f(a)$;"
            r"   $\div\,(ax-b)$ leaves $f\!\left(\dfrac{b}{a}\right)$",
            r"$(x-a)$ is a factor $\Leftrightarrow f(a) = 0$",
        ]),
        ("Identities", [
            r"An identity holds for every $x$ — compare coefficients, "
            r"or substitute convenient values",
        ]),
        ("Inequalities", [
            r"Multiplying or dividing by a negative reverses the inequality",
            r"Quadratic: find the critical values, then sketch or use a sign table",
            r"$|x| < a \;\Leftrightarrow\; -a < x < a$"
            r"      $|x| > a \;\Leftrightarrow\; x < -a$ or $x > a$",
        ]),
    ]),
    (4, [
        (r"Transformations of $y = f(x)$", [
            r"$y = f(x)+a$  translate $a$ up      $y = f(x+a)$  translate $a$ left",
            r"$y = af(x)$  stretch factor $a$ parallel to $y$"
            r"      $y = f(ax)$  stretch factor $\dfrac{1}{a}$ parallel to $x$",
            r"$y = -f(x)$  reflect in the $x$-axis"
            r"      $y = f(-x)$  reflect in the $y$-axis",
        ]),
        ("Intercepts and asymptotes", [
            r"$y$-intercept: put $x = 0$      $x$-intercepts: solve $y = 0$",
            r"Vertical asymptote where the denominator is zero;  "
            r"horizontal from the behaviour as $x \to \pm\infty$",
        ]),
        ("Graphical solution", [
            r"The roots of $f(x) = g(x)$ are the $x$-coordinates where "
            r"$y = f(x)$ meets $y = g(x)$",
        ]),
    ]),
    (5, [
        ("Arithmetic series", [
            r"$u_{n} = a + (n-1)d$",
            r"$S_{n} = \dfrac{n}{2}\left[\,2a + (n-1)d\,\right] "
            r"= \dfrac{n}{2}(a+l)$",
        ]),
        ("Geometric series", [
            r"$u_{n} = ar^{\,n-1}$",
            r"$S_{n} = \dfrac{a(1-r^{n})}{1-r} = \dfrac{a(r^{n}-1)}{r-1}, \quad r \neq 1$",
            r"$S_{\infty} = \dfrac{a}{1-r}$,  valid for $|r| < 1$",
        ]),
        ("Sigma notation", [
            r"$\sum_{r=1}^{n} r = \dfrac{n(n+1)}{2}$"
            r"      $\sum_{r=1}^{n} r^{2} = \dfrac{n(n+1)(2n+1)}{6}$"
            r"      $\sum_{r=1}^{n} r^{3} = \left[\dfrac{n(n+1)}{2}\right]^{2}$",
            r"$\sum (ar+b) = a\sum r + bn$",
        ]),
    ]),
    (6, [
        (r"Positive integer $n$", [
            r"$(a+b)^{n} = \sum_{r=0}^{n} \binom{n}{r} a^{\,n-r} b^{\,r}$",
            r"$\binom{n}{r} = {}^{n}C_{r} = \dfrac{n!}{r!\,(n-r)!}$",
            r"The $(r+1)$th term is $\binom{n}{r} a^{\,n-r} b^{\,r}$",
        ]),
        (r"Any $n$ — fractional or negative", [
            r"$(1+x)^{n} = 1 + nx + \dfrac{n(n-1)}{2!}x^{2} "
            r"+ \dfrac{n(n-1)(n-2)}{3!}x^{3} + \cdots$",
            r"Valid for $|x| < 1$",
            r"$(a+x)^{n} = a^{n}\left(1+\dfrac{x}{a}\right)^{n}$,  valid for $|x| < |a|$",
        ]),
    ]),
    (7, [
        ("Magnitude and direction", [
            r"$\mathbf{a} = x\mathbf{i} + y\mathbf{j}$"
            r"      $|\mathbf{a}| = \sqrt{x^{2}+y^{2}}$",
            r"Unit vector in the direction of $\mathbf{a}$ is "
            r"$\dfrac{\mathbf{a}}{|\mathbf{a}|}$",
        ]),
        ("Position vectors", [
            r"$\overrightarrow{AB} = \mathbf{b} - \mathbf{a}$",
            r"Midpoint of $AB$ has position vector "
            r"$\dfrac{1}{2}(\mathbf{a}+\mathbf{b})$",
            r"$P$ divides $AB$ in the ratio $m:n \;\Rightarrow\; "
            r"\overrightarrow{OP} = \dfrac{n\mathbf{a} + m\mathbf{b}}{m+n}$",
        ]),
        ("Parallel and collinear", [
            r"$\mathbf{a}$ is parallel to $\mathbf{b} \;\Leftrightarrow\; "
            r"\mathbf{a} = \lambda\mathbf{b}$",
            r"$A$, $B$, $C$ are collinear if $\overrightarrow{AB} = "
            r"\lambda\,\overrightarrow{BC}$ — parallel vectors sharing a point",
        ]),
    ]),
    (8, [
        (r"Two points $(x_{1},y_{1})$ and $(x_{2},y_{2})$", [
            r"Distance $= \sqrt{(x_{2}-x_{1})^{2} + (y_{2}-y_{1})^{2}}$",
            r"Midpoint $= \left(\dfrac{x_{1}+x_{2}}{2},\ "
            r"\dfrac{y_{1}+y_{2}}{2}\right)$",
            r"Gradient $m = \dfrac{y_{2}-y_{1}}{x_{2}-x_{1}}$",
        ]),
        ("Straight lines", [
            r"$y - y_{1} = m(x - x_{1})$      $y = mx + c$      $ax + by + c = 0$",
            r"Parallel: $m_{1} = m_{2}$      Perpendicular: $m_{1}m_{2} = -1$",
        ]),
        ("Area and the circle", [
            r"Triangle $= \dfrac{1}{2}\left|\,x_{1}(y_{2}-y_{3}) + x_{2}(y_{3}-y_{1}) "
            r"+ x_{3}(y_{1}-y_{2})\,\right|$",
            r"Circle, centre $(a,b)$ radius $r$: $(x-a)^{2} + (y-b)^{2} = r^{2}$",
        ]),
    ]),
    (9, [
        ("Differentiation", [
            r"$f'(x) = \lim_{h \to 0} \dfrac{f(x+h) - f(x)}{h}$",
            r"$\dfrac{d}{dx}(x^{n}) = nx^{\,n-1}$"
            r"      $\dfrac{d}{dx}(\sin x) = \cos x$"
            r"      $\dfrac{d}{dx}(\cos x) = -\sin x$   ($x$ in radians)",
            r"Product: $(uv)' = u'v + uv'$"
            r"      Quotient: $\left(\dfrac{u}{v}\right)' = "
            r"\dfrac{u'v - uv'}{v^{2}}$",
            r"Chain: $\dfrac{dy}{dx} = \dfrac{dy}{du} \times \dfrac{du}{dx}$",
        ]),
        ("Stationary points", [
            r"Stationary where $\dfrac{dy}{dx} = 0$",
            r"$\dfrac{d^{2}y}{dx^{2}} > 0$ minimum      $< 0$ maximum"
            r"      $= 0$ inconclusive, test the gradient either side",
        ]),
        ("Tangents, normals and rates", [
            r"Tangent gradient $m = \dfrac{dy}{dx}$;  "
            r"normal gradient $= -\dfrac{1}{m}$",
            r"Connected rates: $\dfrac{dy}{dt} = \dfrac{dy}{dx} \times \dfrac{dx}{dt}$",
        ]),
        ("Integration", [
            r"$\int x^{n}\,dx = \dfrac{x^{\,n+1}}{n+1} + c, \quad n \neq -1$",
            r"$\int \sin x\,dx = -\cos x + c$"
            r"      $\int \cos x\,dx = \sin x + c$",
            r"Area $= \int_{a}^{b} y\,dx$;  between curves "
            r"$\int_{a}^{b} (y_{1} - y_{2})\,dx$",
            r"Revolution about $x$: $V = \pi\int_{a}^{b} y^{2}\,dx$"
            r"      about $y$: $V = \pi\int_{c}^{d} x^{2}\,dy$",
        ]),
        ("Kinematics", [
            r"$v = \dfrac{ds}{dt}$      $a = \dfrac{dv}{dt} = \dfrac{d^{2}s}{dt^{2}}$"
            r"      $s = \int v\,dt$      $v = \int a\,dt$",
            r"At instantaneous rest $v = 0$;  maximum speed where $a = 0$",
        ]),
    ]),
    (10, [
        ("Exact values", [
            r"$\sin 30^{\circ} = \dfrac{1}{2}$"
            r"      $\cos 30^{\circ} = \dfrac{\sqrt{3}}{2}$"
            r"      $\tan 30^{\circ} = \dfrac{1}{\sqrt{3}}$",
            r"$\sin 45^{\circ} = \cos 45^{\circ} = \dfrac{1}{\sqrt{2}}$"
            r"      $\tan 45^{\circ} = 1$",
            r"$\sin 60^{\circ} = \dfrac{\sqrt{3}}{2}$"
            r"      $\cos 60^{\circ} = \dfrac{1}{2}$"
            r"      $\tan 60^{\circ} = \sqrt{3}$",
        ]),
        ("Triangles", [
            r"Sine rule:  $\dfrac{a}{\sin A} = \dfrac{b}{\sin B} = \dfrac{c}{\sin C}$"
            r"   (watch the ambiguous case)",
            r"Cosine rule:  $a^{2} = b^{2} + c^{2} - 2bc\cos A$"
            r"      $\cos A = \dfrac{b^{2}+c^{2}-a^{2}}{2bc}$",
            r"Area $= \dfrac{1}{2}ab\sin C$",
        ]),
        ("Identities", [
            r"$\sin^{2}\theta + \cos^{2}\theta = 1$"
            r"      $\tan\theta = \dfrac{\sin\theta}{\cos\theta}$",
            r"$\sin(A \pm B) = \sin A\cos B \pm \cos A\sin B$",
            r"$\cos(A \pm B) = \cos A\cos B \mp \sin A\sin B$",
            r"$\tan(A \pm B) = \dfrac{\tan A \pm \tan B}{1 \mp \tan A\tan B}$",
            r"$\sin 2A = 2\sin A\cos A$",
            r"$\cos 2A = \cos^{2}A - \sin^{2}A = 2\cos^{2}A - 1 = 1 - 2\sin^{2}A$",
            r"$\tan 2A = \dfrac{2\tan A}{1 - \tan^{2}A}$",
        ]),
        ("The R-formula", [
            r"$a\sin\theta \pm b\cos\theta = R\sin(\theta \pm \alpha)$",
            r"$a\cos\theta \pm b\sin\theta = R\cos(\theta \mp \alpha)$",
            r"$R = \sqrt{a^{2}+b^{2}}$,  $\tan\alpha = \dfrac{b}{a}$,  "
            r"with $R > 0$ and $\alpha$ acute",
        ]),
        ("Radians", [
            r"$\pi$ radians $= 180^{\circ}$",
            r"Arc length $s = r\theta$      Sector area $= \dfrac{1}{2}r^{2}\theta$"
            r"      Segment area $= \dfrac{1}{2}r^{2}(\theta - \sin\theta)$",
        ]),
    ]),
]


def flow_blocks(chapter_titles: dict[int, str]) -> list[dict]:
    """
    The sheet as blocks small enough to pack.

    A group is the smallest unit that still reads correctly on its own, so the
    chapter heading travels with its FIRST group and never sits alone at the
    foot of a page. Chapter-sized blocks stranded 40% of a sheet whenever a
    chapter would not fit the remainder.
    """
    out: list[dict] = []
    for number, groups in SHEET:
        for index, (heading, lines) in enumerate(groups):
            out.append({
                "chapter": f"{number}   {chapter_titles.get(number, '')}" if index == 0 else None,
                "heading": heading,
                "lines": lines,
            })
    return out
