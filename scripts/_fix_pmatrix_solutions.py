"""Re-write the three hand-authored pmatrix solutions whose row-separator "\\"
collapsed to a single "\" when they were first written through a shell heredoc.
Written as a file (backslashes preserved) and applied with the Write tool, so the
double-backslash matrix separators survive into the cache."""
import json
from pathlib import Path

P1 = Path("data/workbook/mathsb_worked_solutions_part1.json")
P2 = Path("data/workbook/mathsb_worked_solutions_part2.json")

Q058 = {
 "question_number": 5, "ms_questions_visible": "5",
 "ms_matches_question": True, "ms_math_correct": True, "ms_error": None,
 "steps": [
  {"step": r"(a) From the grid, triangle $A$ has vertices $(2,2),(4,2),(4,6)$ and triangle $B$ has vertices $(-2,1),(-1,1),(-1,3)$. Every side of $B$ is half the corresponding side of $A$ with the same orientation, so the transformation is an enlargement of scale factor $\tfrac12$.", "marks": "B1"},
  {"step": r"To find the centre, join each vertex of $A$ to its image on $B$ and extend to meet, i.e. solve $B=c+\tfrac12(A-c)$. Using $(4,2)\mapsto(-1,1)$ gives centre $c=(-6,0)$.", "marks": "B1"},
  {"step": r"(a) Enlargement, scale factor $\tfrac12$, centre $(-6,0)$.", "marks": "B1"},
  {"step": r"(b) Apply $\mathbf{M}=\begin{pmatrix}-1&0\\-3&-1\end{pmatrix}$ to the vertices of $B$: $\begin{pmatrix}-1&0\\-3&-1\end{pmatrix}\begin{pmatrix}-2&-1&-1\\1&1&3\end{pmatrix}=\begin{pmatrix}2&1&1\\5&2&0\end{pmatrix}$.", "marks": "B2"},
  {"step": r"So triangle $C$ has vertices $(2,5),(1,2),(1,0)$; plot and label $C$.", "marks": "B1"},
  {"step": r"(c) Apply $\mathbf{N}=\begin{pmatrix}3&-1\\-1&0\end{pmatrix}$ to the vertices of $C$: $\begin{pmatrix}3&-1\\-1&0\end{pmatrix}\begin{pmatrix}2&1&1\\5&2&0\end{pmatrix}=\begin{pmatrix}1&1&3\\-2&-1&-1\end{pmatrix}$.", "marks": "B2"},
  {"step": r"So triangle $D$ has vertices $(1,-2),(1,-1),(3,-1)$; plot and label $D$.", "marks": "B1"},
  {"step": r"(d) The single matrix mapping $B$ to $D$ is $\mathbf{N}\mathbf{M}=\begin{pmatrix}3&-1\\-1&0\end{pmatrix}\begin{pmatrix}-1&0\\-3&-1\end{pmatrix}=\begin{pmatrix}0&1\\1&0\end{pmatrix}$, which sends $(x,y)\mapsto(y,x)$.", "marks": "B1"},
  {"step": r"That is a reflection in the line $y=x$ (check $(-2,1)\mapsto(1,-2)$, matching $D$).", "marks": "B1"},
 ],
 "final_answer": r"(a) enlargement, scale factor $\tfrac12$, centre $(-6,0)$;  (b) $C=(2,5),(1,2),(1,0)$;  (c) $D=(1,-2),(1,-1),(3,-1)$;  (d) reflection in the line $y=x$",
 "answer_agrees_with_ms": True, "confidence": "high",
}

Q038 = {
 "question_number": 9, "ms_questions_visible": "9",
 "ms_matches_question": True, "ms_math_correct": True, "ms_error": None,
 "steps": [
  {"step": r"(a) Plot triangle $S$ with vertices $(4,2),(4,3),(6,3)$.", "marks": "B1"},
  {"step": r"(b) Reflect $S$ in $y=x$ by swapping coordinates $(x,y)\mapsto(y,x)$: $S=(4,2),(4,3),(6,3)\mapsto T=(2,4),(3,4),(3,6)$.", "marks": "B2"},
  {"step": r"(c) Rotate $T$ by $180^\circ$ about $(-2,2)$ using $(x,y)\mapsto(-4-x,\,4-y)$: $T\mapsto U=(-6,0),(-7,0),(-7,-2)$.", "marks": "M1 A2"},
  {"step": r"(d) Translate $U$ by $\begin{pmatrix}5\\-1\end{pmatrix}$: $U\mapsto V=(-1,-1),(-2,-1),(-2,-3)$.", "marks": "B2"},
  {"step": r"(e) Apply $\mathbf{P}=\begin{pmatrix}-3&1\\1&1\end{pmatrix}$ to $V$: $\begin{pmatrix}-3&1\\1&1\end{pmatrix}\begin{pmatrix}-1&-2&-2\\-1&-1&-3\end{pmatrix}=\begin{pmatrix}2&5&3\\-2&-3&-5\end{pmatrix}$, so $W=(2,-2),(5,-3),(3,-5)$.", "marks": "M1 A2"},
  {"step": r"(f) $\det\mathbf{P}=(-3)(1)-(1)(1)=-4$.", "marks": "B1"},
  {"step": r"(g) Reflection, rotation and translation preserve area, so area of $V=$ area of $S$. Multiplying by $\mathbf{P}$ scales area by $|\det\mathbf{P}|=4$, so area of $W=4\times$ area of $S$. Hence $S:W=1:4$.", "marks": "B1"},
 ],
 "final_answer": r"(b) $T=(2,4),(3,4),(3,6)$;  (c) $U=(-6,0),(-7,0),(-7,-2)$;  (d) $V=(-1,-1),(-2,-1),(-2,-3)$;  (e) $W=(2,-2),(5,-3),(3,-5)$;  (f) $\det\mathbf{P}=-4$;  (g) $1:4$",
 "answer_agrees_with_ms": True, "confidence": "high",
}

Q010 = {
 "question_number": 9, "ms_questions_visible": "9",
 "ms_matches_question": True, "ms_math_correct": True, "ms_error": None,
 "steps": [
  {"step": r"(a) $|\mathbf p|=\sqrt{98}$ gives $(2x-1)^2+y^2=98$.", "marks": "M1"},
  {"step": r"$\mathbf p+\mathbf q=\begin{pmatrix}(2x-1)+(y+3)\\ y+(-y)\end{pmatrix}=\begin{pmatrix}7\\0\end{pmatrix}$, so $(2x-1)+(y+3)=7$, giving $y=5-2x$.", "marks": "M1"},
  {"step": r"Substitute $y=5-2x$: $(2x-1)^2+(5-2x)^2=98$.", "marks": "M1"},
  {"step": r"Expand: $(4x^2-4x+1)+(4x^2-20x+25)=98\Rightarrow 8x^2-24x+26=98\Rightarrow 8x^2-24x-72=0$.", "marks": "M1"},
  {"step": r"Divide by $8$: $x^2-3x-9=0$ (shown).", "marks": "A1"},
  {"step": r"(b)(i) By the quadratic formula, $x=\dfrac{3\pm\sqrt{9+36}}{2}=\dfrac{3\pm\sqrt{45}}{2}=\dfrac{3\pm3\sqrt5}{2}$.", "marks": "M1"},
  {"step": r"Since $x>0$, $x=\dfrac{3+3\sqrt5}{2}$.", "marks": "A1"},
  {"step": r"(b)(ii) $y=5-2x=5-2\left(\dfrac{3+3\sqrt5}{2}\right)=5-(3+3\sqrt5)=2-3\sqrt5$ (shown).", "marks": "M1 A1"},
  {"step": r"(c) With $y=2-3\sqrt5$: $y+3=5-3\sqrt5$ and $-y=3\sqrt5-2$, so $|\mathbf q|^2=(y+3)^2+(-y)^2=(5-3\sqrt5)^2+(3\sqrt5-2)^2$.", "marks": "M1"},
  {"step": r"Expand: $(25-30\sqrt5+45)+(45-12\sqrt5+4)$.", "marks": "M1"},
  {"step": r"$=119-42\sqrt5\;(=7(17-6\sqrt5))$.", "marks": "A1"},
 ],
 "final_answer": r"(a) shown $x^2-3x-9=0$;  (b)(i) $x=\dfrac{3+3\sqrt5}{2}$;  (b)(ii) $y=2-3\sqrt5$;  (c) $|\mathbf q|^2=119-42\sqrt5=7(17-6\sqrt5)$",
 "answer_agrees_with_ms": True, "confidence": "high",
}


def apply(path, updates):
    c = json.loads(path.read_text(encoding="utf-8"))
    for slug, sol in updates.items():
        c[slug]["solution"] = sol
        c[slug]["model"] = "opus-hybrid"
    path.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(updates)} fixed in {path.name}")


apply(P1, {"MB.CH05.S04.Q058": Q058, "MB.CH08.S04.Q038": Q038})
apply(P2, {"MB.CH08.S01.Q010": Q010})

# verify double-backslashes now present
for path, slugs in [(P1, ["MB.CH05.S04.Q058", "MB.CH08.S04.Q038"]), (P2, ["MB.CH08.S01.Q010"])]:
    c = json.loads(path.read_text(encoding="utf-8"))
    for slug in slugs:
        blob = json.dumps(c[slug]["solution"])
        print(f"  {slug}: double-backslash count = {blob.count(chr(92) + chr(92))}")
