"""
Archetype clustering for IAL workbook questions.

Edexcel reuses question shapes heavily. The workbook clusters the repeats
together rather than deleting them: meeting the same shape four times in four
papers' clothing is how pattern recognition gets built, and it is also how a
student discovers that a paper is mostly familiar.

Deterministic on purpose -- TF-IDF over the stems plus a cosine threshold. No
model is involved, so the clusters do not drift between runs and a re-run after
re-segmentation produces the same book.

THRESHOLD IS TUNED BY INSPECTION, NOT BY A METRIC
-------------------------------------------------
The 4PM1 build settled on 0.45 by reading the clusters. At 0.38 one section
collapsed into a single 28-question blob that mixed related rates with implicit
differentiation and tangent/normal work; at 0.45 they separated properly. There
is no internal metric that would have told you that -- cluster-quality scores
are happy with the blob.

For the IAL subjects 0.45 was too high: WMA14's section 4.1 split into four
separate clusters that were all plainly the same binomial expansion. 0.32 merges
those correctly while keeping the sections apart, and was checked by reading the
three largest clusters -- all genuine single shapes. 0.26 begins to blob (11 of
section 7.2's 12 questions in one cluster is the section, not a shape).

WHY WST01 CLUSTERS WEAKLY, AND WHY THAT IS NOT A TUNING FAILURE
---------------------------------------------------------------
Statistics questions are CONTEXTUAL. All fifteen questions in WST01 section 4.2
set the same task -- compute and interpret the product moment correlation
coefficient -- but they are dressed as a price comparison website, blood volume,
milk and bread, foetal scans, caffeine, sea-level temperature, petrol
consumption, GDP, film takings, dissolving sugar, bears and rabbits. They share
almost no content words, so TF-IDF cannot see that they are one shape, and no
threshold recovers it: lowering it merges unlike questions on filler instead.

So for WST01 **the section is effectively the archetype**, and roughly 70% of
its questions come out as singletons. That is the honest result. A book
generator should not present those singletons as recurring shapes -- for this
subject the section heading carries the pattern, and for WMA14 the archetype
does.

Clustering runs WITHIN a section, never across the whole subject: two questions
from different sections are different shapes by definition, and letting them
merge produces labels that describe nothing.
"""

from __future__ import annotations

import math
import re
from collections import Counter

#: Per-subject in practice -- each entry-point script sets its own. 0.32 was
#: chosen for both IAL subjects by reading the clusters (see below).
DEFAULT_THRESHOLD = 0.32

#: Exam prose is full of words that carry no shape information. Without this the
#: similarity is dominated by "find", "give", "answer", "question".
STOPWORDS = frozenset(
    """
    the a an and or of to in for on at by with from is are be been being was were
    that this these those it its as if then than so such not no nor but
    find given give gives giving show shows shown state write down calculate
    work out determine hence otherwise deduce explain comment answer answers
    question questions marks mark total leave blank diagram figure above below
    following your you their they them there here where which who whom whose
    form terms term value values using use used each all any both other another
    correct exact simplest fully full complete completely nearest decimal places
    significant figures your own
    """.split()
)

TOKEN_RE = re.compile(r"[a-z]{3,}")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _tfidf(documents: dict[str, Counter]) -> dict[str, dict[str, float]]:
    n = len(documents)
    frequency: Counter = Counter()
    for counts in documents.values():
        frequency.update(counts.keys())

    vectors: dict[str, dict[str, float]] = {}
    for key, counts in documents.items():
        total = sum(counts.values()) or 1
        vector = {
            token: (count / total) * math.log((1 + n) / (1 + frequency[token]) + 1)
            for token, count in counts.items()
        }
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        vectors[key] = {token: v / norm for token, v in vector.items()}
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(token, 0.0) for token, value in a.items())


def _label(cluster: list[str], documents: dict[str, Counter]) -> str:
    """Name a cluster from the tokens its members share most strongly."""
    shared: Counter = Counter()
    for key in cluster:
        shared.update(set(documents[key].keys()))
    # A token every member uses describes the shape; one a single member uses
    # describes that member.
    common = [t for t, c in shared.most_common() if c >= max(2, len(cluster) // 2)]
    return " ".join(common[:4]) if common else "assorted"


def cluster_questions(
    questions: list[dict],
    section_of: dict[str, str],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict]:
    """
    Group questions into archetypes within each section.

    `section_of` maps slug -> section code. Questions with no section are
    skipped rather than pooled, since an unclassified question has no section
    to be a shape within.
    """
    by_section: dict[str, list[dict]] = {}
    for question in questions:
        section = section_of.get(question["slug"])
        if section:
            by_section.setdefault(section, []).append(question)

    archetypes: list[dict] = []

    for section in sorted(by_section, key=lambda c: [int(p) for p in c.split(".")]):
        members = by_section[section]
        documents = {q["slug"]: Counter(tokenize(q["stem"])) for q in members}
        vectors = _tfidf(documents)

        unassigned = [q["slug"] for q in members]
        clusters: list[list[str]] = []

        while unassigned:
            seed = unassigned.pop(0)
            cluster = [seed]
            rest = []
            for slug in unassigned:
                if _cosine(vectors[seed], vectors[slug]) >= threshold:
                    cluster.append(slug)
                else:
                    rest.append(slug)
            unassigned = rest
            clusters.append(cluster)

        marks = {q["slug"]: q["marks"] for q in members}
        for cluster in clusters:
            archetypes.append(
                {
                    "section": section,
                    "label": _label(cluster, documents),
                    "size": len(cluster),
                    "slugs": sorted(cluster),
                    # Print order inside a section runs cheapest archetype first,
                    # so a student meets the shape at its simplest.
                    "min_marks": min(marks[s] for s in cluster),
                }
            )

    return archetypes
