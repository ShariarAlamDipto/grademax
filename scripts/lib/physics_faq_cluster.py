"""Turn parsed Edexcel IGCSE Physics question parts into recurring-question groups.

"Frequently asked" has to mean something measurable, so a question earns its place
by appearing in more than one paper. Stems are matched on their significant words:
"State the formula linking resistance, voltage and current" and "State the formula
linking voltage, current and resistance" are the same question and must land in
the same group, while "Explain why the resistance increases" must not.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# Words that carry no discriminating meaning in an exam stem.
STOPWORDS = frozenset("""
a an the this that these those of in on at to for from by with and or is are was were
be been being it its their there here you your student teacher shows show shown gives
given give diagram figure table graph picture image box below above following used use
uses using when where which what who how why some each other another one two three four
five six not no also then than as into out up down over under about during between
question marks mark answer space line lines write writes complete first second next
""".split())

_TOKEN_RE = re.compile(r"[a-z]+")
_MC_RE = re.compile(r"\bwhich of these\b|\bwhich one\b|^\s*A\b.*\bB\b.*\bC\b.*\bD\b", re.I)

# Edexcel alternates freely between these across sessions while asking exactly the
# same thing, so they are folded together before stems are compared.
# Deliberately minimal. Folding physics terms together ("velocity" into "speed",
# "difference" into "voltage") would merge questions that test different things --
# "state the difference between speed and velocity" is itself an exam question --
# so only pure wording variants of the same stem are folded.
SYNONYMS = {
    "equation": "formula",
    "equations": "formula",
    "formulae": "formula",
    "formulas": "formula",
}


@dataclass
class Cluster:
    key: frozenset
    stem: str
    members: list = field(default_factory=list)

    @property
    def papers(self) -> int:
        return len({m.paper_id for m in self.members})

    @property
    def years(self) -> list[int]:
        return sorted({m.year for m in self.members})


def significant(text: str) -> frozenset[str]:
    """The content words of a stem, with exam boilerplate removed."""
    words = _TOKEN_RE.findall(text.lower())
    return frozenset(
        SYNONYMS.get(w, w) for w in words if len(w) > 2 and w not in STOPWORDS
    )


def _similarity(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_parts(parts: list, threshold: float = 0.72, cap: int = 14) -> list[Cluster]:
    """Group parts whose stems say the same thing.

    Only the first `cap` significant words of a stem are compared. Edexcel wraps a
    question in a paragraph of context that changes every session -- the ball, the
    car, the student's name -- while the question itself is the short clause at the
    end. Comparing whole stems would therefore separate identical questions.
    """
    clusters: list[Cluster] = []
    for part in sorted(parts, key=lambda p: (-len(significant(p.stem)), p.paper_id)):
        words = significant(part.stem)
        if len(words) < 3:
            continue
        key = frozenset(list(words)[:cap]) if len(words) > cap else words

        best, best_score = None, threshold
        for cluster in clusters:
            score = _similarity(key, cluster.key)
            if score > best_score:
                best, best_score = cluster, score
        if best is None:
            clusters.append(Cluster(key=key, stem=part.stem, members=[part]))
        else:
            best.members.append(part)
    return clusters


def canonical_stem(cluster: Cluster) -> str:
    """The shortest member stem, which is the question with the least context bolted on."""
    return min((m.stem for m in cluster.members), key=len)


def is_multiple_choice(stem: str) -> bool:
    return bool(_MC_RE.search(stem))


def common_points(cluster: Cluster, min_share: float = 0.4) -> list[str]:
    """Mark scheme points that recur across the cluster's members."""
    counts: Counter = Counter()
    for member in cluster.members:
        for point in {p.lower() for p in member.points}:
            counts[point] += 1
    need = max(1, int(len(cluster.members) * min_share))
    return [p for p, n in counts.most_common() if n >= need]
