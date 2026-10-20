"""One-off: write Opus-verified worked solutions into the Part 1 cache for the
questions the free tier could not solve, plus corrections for the two questions
Gemini got wrong (Q057 exponent, Q059 enlargement). Run once; safe to re-run."""
import json
from pathlib import Path

CACHE = Path("data/workbook/mathsb_worked_solutions_part1.json")

def sol(steps, final, note=None):
    return {
        "ms_matches_question": True,
        "ms_math_correct": True,
        "ms_error": note,
        "steps": [{"step": s, "marks": m} for s, m in steps],
        "final_answer": final,
        "answer_agrees_with_ms": True,
        "confidence": 0.95,
    }

S = {}

S["MB.CH01.S03.Q160"] = sol([
    (r"(a) $240\,000\,000 = 2.4\times10^{8}$", "B1"),
    (r"(b) $2.56\times10^{-3} = 0.00256$", "B1"),
    (r"(c) Numerator: $2.5\times10^{8}-1.3\times10^{7}=25\times10^{7}-1.3\times10^{7}=2.37\times10^{8}$", "M1"),
    (r"(c) $\dfrac{2.37\times10^{8}}{1.5\times10^{-6}}=1.58\times10^{14}$", "M1 A1"),
], r"(a) $2.4\times10^{8}$  (b) $0.00256$  (c) $1.58\times10^{14}$")

S["MB.CH01.S03.Q188"] = sol([
    (r"(a) $(4x^{5})^{2}=4^{2}x^{10}=16x^{10}$", "B2"),
    (r"(b) $(27y^{9})^{\frac43}=27^{\frac43}y^{12}=(3^{3})^{\frac43}y^{12}=81y^{12}$", "B2"),
], r"(a) $16x^{10}$  (b) $81y^{12}$")

S["MB.CH02.S03.Q025"] = sol([
    (r"Sets: $A=\{1,3,5,7,9,11,13\}$, $B=\{1,2,3,4,6,12\}$, $C=\{3,6,9,12\}$ in $\varepsilon=\{1,\dots,14\}$", None),
    (r"(a) Place each value: $3$ in $A\cap B\cap C$; $6,12$ in $B\cap C$; $9$ in $A\cap C$; $1$ in $A\cap B$; $5,7,11,13$ in $A$ only; $2,4$ in $B$ only; $8,10,14$ outside", "B3"),
    (r"(b) $B\cup C=\{1,2,3,4,6,9,12\}$", "B1"),
    (r"(c) $A\cap B=\{1,3\}$", "B1"),
    (r"(d) $A\cup B\cup C=\{1,2,3,4,5,6,7,9,11,12,13\}$, so $(A\cup B\cup C)'=\{8,10,14\}$ and $n=3$", "B1"),
], r"(b) $\{1,2,3,4,6,9,12\}$  (c) $\{1,3\}$  (d) $3$")

S["MB.CH02.S03.Q034"] = sol([
    (r"Sets: $A=\{q,r,s\}$, $B=\{p,q,t\}$, $\varepsilon=\{p,q,r,s,t\}$", None),
    (r"(a)(i) $A\cap B=\{q\}$", "B1"),
    (r"(a)(ii) $A\cup B=\{p,q,r,s,t\}$", "B1"),
    (r"(a)(iii) $A'=\{p,t\}$, so $A'\cap B=\{p,t\}$", "B1"),
    (r"(b) $A\cap C=\{r\}$ means $C$ contains $r$ but not $q$ or $s$; so $C$ is any subset of $\{p,r,t\}$ containing $r$: $\{r\},\{p,r\},\{r,t\},\{p,r,t\}$", "B2"),
    (r"(c) $B\cap C=\varnothing$ only for $C=\{r\}$; the other three contain $p$ or $t$, so probability $=\dfrac{1}{4}$", "M1 A1"),
], r"(a) $\{q\}$, $\{p,q,r,s,t\}$, $\{p,t\}$  (b) $\{r\},\{p,r\},\{r,t\},\{p,r,t\}$  (c) $\tfrac14$")

S["MB.CH03.S02.Q084"] = sol([
    (r"$|\mathbf a|^{2}=(2x-1)^{2}+(-3)^{2}=5^{2}=25$", "M1"),
    (r"$(2x-1)^{2}=16\Rightarrow 2x-1=\pm4$", "M1"),
    (r"$x=\dfrac{5}{2}$ or $x=-\dfrac{3}{2}$", "A1"),
], r"$x=\dfrac{5}{2}$ or $x=-\dfrac{3}{2}$")

S["MB.CH03.S02.Q089"] = sol([
    (r"(a) Draw a solid circle at $-3$ (as $-3\leqslant x$) and an open circle at $4$ (as $x<4$), joined by a line", "M1 A1"),
    (r"(b) Integer values: $-3,-2,-1,0,1,2,3$", "B1"),
], r"(b) $-3,-2,-1,0,1,2,3$")

S["MB.CH04.S03.Q025"] = sol([
    (r"(a) $g$ is undefined when $x-3=0$, so exclude $x=3$", "B1"),
    (r"(b) $f(5)=3(5)+4=19$", "B1"),
    (r"(c) $g(2)=\dfrac{5}{2-3}=-5$, so $fg(2)=f(-5)=3(-5)+4=-11$", "M1 A1"),
    (r"(d) Let $y=x^{2}-6x-8\Rightarrow x^{2}-6x-(8+y)=0$", "M1"),
    (r"(d) $x=\dfrac{6+\sqrt{36+4(8+y)}}{2}=3+\sqrt{y+17}$ (take $+$ since $x\geqslant3$)", "M1"),
    (r"(d) $h^{-1}:x\mapsto 3+\sqrt{x+17}$", "A1"),
], r"(a) $x=3$  (b) $19$  (c) $-11$  (d) $h^{-1}:x\mapsto 3+\sqrt{x+17}$")

S["MB.CH05.S01.Q002"] = sol([
    (r"$3\mathbf A=\begin{pmatrix}6&-3\\-9&15\end{pmatrix},\quad 2\mathbf B=\begin{pmatrix}-2&4\\6&-6\end{pmatrix}$", "M1"),
    (r"$3\mathbf A+2\mathbf B=\begin{pmatrix}4&1\\-3&9\end{pmatrix}$", "A1"),
], r"$\begin{pmatrix}4&1\\-3&9\end{pmatrix}$")

S["MB.CH05.S01.Q004"] = sol([
    (r"$4\mathbf A=\begin{pmatrix}20&-16\\8&-8\end{pmatrix},\quad 3\mathbf B=\begin{pmatrix}9&-6\\-6&15\end{pmatrix}$", "M1"),
    (r"$4\mathbf A-3\mathbf B=\begin{pmatrix}11&-10\\14&-23\end{pmatrix}$", "A1"),
], r"$\begin{pmatrix}11&-10\\14&-23\end{pmatrix}$")

S["MB.CH05.S01.Q007"] = sol([
    (r"$5\mathbf A+n\mathbf B=\begin{pmatrix}20+4n&15+nx\\10+2ny&-5+7n\end{pmatrix}=\begin{pmatrix}8&27\\1&-26\end{pmatrix}$", "M1"),
    (r"$-5+7n=-26\Rightarrow n=-3$; then $15+nx=27\Rightarrow x=-4$ and $10+2ny=1\Rightarrow y=1.5$", "A2"),
], r"$n=-3,\ x=-4,\ y=1.5$")

S["MB.CH05.S01.Q014"] = sol([
    (r"(a) $\mathbf A^{2}=\begin{pmatrix}-2&3\\5&-7\end{pmatrix}\begin{pmatrix}-2&3\\5&-7\end{pmatrix}=\begin{pmatrix}19&-27\\-45&64\end{pmatrix}$", "B2"),
    (r"(b) $\mathbf{BA}=\begin{pmatrix}-1&2\\-3&5\\4&-3\end{pmatrix}\begin{pmatrix}-2&3\\5&-7\end{pmatrix}=\begin{pmatrix}12&-17\\31&-44\\-23&33\end{pmatrix}$", "B2"),
], r"(a) $\begin{pmatrix}19&-27\\-45&64\end{pmatrix}$  (b) $\begin{pmatrix}12&-17\\31&-44\\-23&33\end{pmatrix}$")

S["MB.CH05.S01.Q016"] = sol([
    (r"(a) $3\mathbf A-2\mathbf B=\begin{pmatrix}9&-3\\-12&6\end{pmatrix}-\begin{pmatrix}4&-1\\4&-4\end{pmatrix}=\begin{pmatrix}5&-2\\-16&10\end{pmatrix}$", "M1 A1"),
    (r"(b) $\mathbf Q=(\mathbf{QP}^{-1})\mathbf P=\begin{pmatrix}0&1\\-10&-17\end{pmatrix}\begin{pmatrix}5&-3\\-3&2\end{pmatrix}=\begin{pmatrix}-3&2\\1&-4\end{pmatrix}$", "M1 A1"),
], r"(a) $\begin{pmatrix}5&-2\\-16&10\end{pmatrix}$  (b) $\mathbf Q=\begin{pmatrix}-3&2\\1&-4\end{pmatrix}$")

S["MB.CH05.S01.Q017"] = sol([
    (r"(a) $\mathbf A-\mathbf B=\begin{pmatrix}3-(-2)&-2-5\\4-4&1-3\end{pmatrix}=\begin{pmatrix}5&-7\\0&-2\end{pmatrix}$", "B2"),
    (r"(b) $3\mathbf A+2\mathbf B=\begin{pmatrix}9&-6\\12&3\end{pmatrix}+\begin{pmatrix}-4&10\\8&6\end{pmatrix}=\begin{pmatrix}5&4\\20&9\end{pmatrix}$", "B2"),
], r"(a) $\begin{pmatrix}5&-7\\0&-2\end{pmatrix}$  (b) $\begin{pmatrix}5&4\\20&9\end{pmatrix}$")

S["MB.CH05.S01.Q018"] = sol([
    (r"(a) $\mathbf A+2\mathbf B=\begin{pmatrix}3&-2\\-6&-1\end{pmatrix}+\begin{pmatrix}-2&2\\6&2\end{pmatrix}=\begin{pmatrix}1&0\\0&1\end{pmatrix}$", "B2"),
    (r"(b) $\mathbf{AB}=\begin{pmatrix}3&-2\\-6&-1\end{pmatrix}\begin{pmatrix}-1&1\\3&1\end{pmatrix}=\begin{pmatrix}-9&1\\3&-7\end{pmatrix}$", "B2"),
], r"(a) $\begin{pmatrix}1&0\\0&1\end{pmatrix}$  (b) $\begin{pmatrix}-9&1\\3&-7\end{pmatrix}$")

S["MB.CH05.S01.Q020"] = sol([
    (r"$\mathbf A^{2}=\begin{pmatrix}a&3\\4&-1\end{pmatrix}^{2}=\begin{pmatrix}a^{2}+12&3a-3\\4a-4&13\end{pmatrix}$", "B2"),
    (r"$\mathbf A^{2}-\mathbf B=\begin{pmatrix}a^{2}-1&3a-6\\4a-8&3\end{pmatrix}=\lambda\mathbf I$", "M1"),
    (r"Off-diagonals $=0$: $3a-6=0\Rightarrow a=2$; diagonals give $\lambda=3$ (and $a^{2}-1=3$)", "A1 A1"),
], r"$a=2,\ \lambda=3$")

S["MB.CH05.S02.Q040"] = sol([
    (r"$\mathbf A$ is ``$\mathbf B$ then $\mathbf C$'', so $\mathbf A=\mathbf{CB}\Rightarrow \mathbf C=\mathbf{AB}^{-1}$", "M1"),
    (r"$\det\mathbf B=3(-2)-(-1)(2)=-4$, so $\mathbf B^{-1}=-\tfrac14\begin{pmatrix}-2&1\\-2&3\end{pmatrix}$", "B1 B1"),
    (r"$\mathbf C=\begin{pmatrix}3&4\\-1&2\end{pmatrix}\left(-\tfrac14\right)\begin{pmatrix}-2&1\\-2&3\end{pmatrix}=-\tfrac14\begin{pmatrix}-14&15\\-2&5\end{pmatrix}$", "M1"),
    (r"$\mathbf C=\begin{pmatrix}3.5&-3.75\\0.5&-1.25\end{pmatrix}$", "A1"),
], r"$\mathbf C=\begin{pmatrix}3.5&-3.75\\0.5&-1.25\end{pmatrix}$")

S["MB.CH05.S02.Q044"] = sol([
    (r"$\mathbf A^{2}=\begin{pmatrix}-11&9\\-15&-14\end{pmatrix}$", "M1"),
    (r"$\mathbf{AB}=\begin{pmatrix}11&2k-3\\-19&-5k-1\end{pmatrix}$", "M1"),
    (r"$\mathbf A^{2}-\mathbf{AB}=\begin{pmatrix}-22&12-2k\\4&5k-13\end{pmatrix}$", "A1"),
    (r"$\det=(-22)(5k-13)-4(12-2k)=-102k+238$", "M1"),
    (r"$-102k+238=3k+28\Rightarrow 105k=210\Rightarrow k=2$", "M1 A1"),
], r"$k=2$")

S["MB.CH05.S02.Q047"] = sol([
    (r"$\det\mathbf A=(-2)(4)-(-3)(2)=-2$, so $\det(\mathbf{BA})=\det\mathbf B\det\mathbf A=10(-2)=-20$", "M1"),
    (r"$\det(\mathbf{BA})=(4x)(-1)-(-14)(x)=10x=-20\Rightarrow x=-2$", "M1 A1"),
    (r"$\mathbf{BA}=\begin{pmatrix}-8&-14\\-2&-1\end{pmatrix},\quad \mathbf A^{-1}=-\tfrac12\begin{pmatrix}4&3\\-2&-2\end{pmatrix}$", "B1"),
    (r"$\mathbf B=\mathbf{BA}\,\mathbf A^{-1}=-\tfrac12\begin{pmatrix}-4&4\\-6&-4\end{pmatrix}=\begin{pmatrix}2&-2\\3&2\end{pmatrix}$", "M1 A1"),
], r"$x=-2,\ \mathbf B=\begin{pmatrix}2&-2\\3&2\end{pmatrix}$")

S["MB.CH06.S07.Q135"] = sol([
    (r"(a) Draw the line $y=2$ (horizontal)", "B1"),
    (r"(a) Draw the line $x+y=5$ (through $(5,0)$ and $(0,5)$)", "B1"),
    (r"(a) Draw the line $y=2x+1$ (through $(0,1)$ and $(2,5)$)", "B1"),
    (r"(b) Shade the region with $y\geqslant2$, $x+y\leqslant5$ and $y\leqslant2x+1$: the triangle with vertices $(0.5,2)$, $(3,2)$, $\left(\tfrac43,\tfrac{11}{3}\right)$; label it $R$", "B1"),
], r"$R$ is the triangle bounded by $y=2$, $x+y=5$ and $y=2x+1$")

S["MB.CH06.S07.Q144"] = sol([
    (r"Boundary $y-x=2$ with $R$ below it: $y-x\leqslant2$", "B1"),
    (r"Boundary $3x+y=15$ with $R$ above it: $3x+y\geqslant15$", "B1"),
    (r"Boundary the $x$-axis with $R$ above it: $y\geqslant0$", "B1"),
], r"$y-x\leqslant2,\quad 3x+y\geqslant15,\quad y\geqslant0$")

# ---- corrections to Gemini's wrong solutions ----
S["MB.CH03.S01.Q057"] = sol([
    (r"$y$ varies inversely as $x^{3}$: $y=\dfrac{k}{x^{3}}$", "M1"),
    (r"$y=3a$ when $x=2a$: $3a=\dfrac{k}{(2a)^{3}}=\dfrac{k}{8a^{3}}\Rightarrow k=24a^{4}$", "A1"),
    (r"At $x=4a^{2}$: $y=\dfrac{24a^{4}}{(4a^{2})^{3}}=\dfrac{24a^{4}}{64a^{6}}$", "M1"),
    (r"$y=\dfrac{3}{8a^{2}}$", "A1"),
], r"$y=\dfrac{3}{8a^{2}}$")

S["MB.CH05.S04.Q059"] = sol([
    (r"(a) Plot triangle $A$: $(1,1),(3,1),(4,3)$", "B1"),
    (r"(b) $\mathbf M=\begin{pmatrix}-2&0\\0&2\end{pmatrix}$ gives $(x,y)\mapsto(-2x,2y)$: $B=(-2,2),(-6,2),(-8,6)$", "M1 A2"),
    (r"(c) Reflect $B$ in $y=0$: $(x,y)\mapsto(x,-y)$: $C=(-2,-2),(-6,-2),(-8,-6)$", "B1"),
    (r"(d) $\mathbf N=\begin{pmatrix}1&0\\0&-1\end{pmatrix}\begin{pmatrix}-2&0\\0&2\end{pmatrix}=\begin{pmatrix}-2&0\\0&-2\end{pmatrix}$", "M1 A1"),
    (r"(e) Rotate $C$ by $180^{\circ}$ about $(1,1)$: $(x,y)\mapsto(2-x,2-y)$: $D=(4,4),(8,4),(10,8)$", "M1 A1"),
    (r"(f) $D\to A$: e.g. $(4,4)\mapsto(1,1)$, $(8,4)\mapsto(3,1)$ give scale factor $\tfrac12$ and centre $(-2,-2)$", "B1 B1 B1"),
], r"(d) $\mathbf N=\begin{pmatrix}-2&0\\0&-2\end{pmatrix}$  (f) Enlargement, scale factor $\tfrac12$, centre $(-2,-2)$")

cache = json.loads(CACHE.read_text(encoding="utf-8"))
n = 0
for slug, s in S.items():
    if slug not in cache:
        print("SKIP unknown", slug); continue
    cache[slug]["solution"] = s
    cache[slug]["model"] = "opus-hybrid"
    n += 1
CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"applied {n} hybrid solutions")
