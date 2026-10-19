"""
Phase 3b: cluster Maths A (4MA1) Higher workbook questions into recurring archetypes.

Edexcel reuses question shapes heavily -- "work out an estimate for the mean
from a grouped frequency table", "reverse percentage to find the original
price", "volume scale factor between two similar solids" recur most sessions
with different numbers. The workbook keeps every repeat (the brief is that no variety is left
undone) but prints them ADJACENT, so a student meets the same shape four times
in four papers' clothing. That turns what would read as padding into the most
useful page in the chapter.

WHY NOT JUST USE THE MODEL'S LABEL
----------------------------------
The classifier is asked for a short archetype phrase and told to reuse wording
for questions of the same shape. It cannot: each batch is an independent call
with no memory of the others, so 1042 questions produce ~1042 distinct
phrasings of far fewer real shapes. Clustering has to be done here, over the whole corpus
at once.

Deterministic on purpose -- no API, no cost, and the same input always gives the
same clusters, which matters because archetype ids end up in stable question
slugs.

METHOD
------
TF-IDF over each question's model-assigned archetype phrase (weighted heavily,
since it is already a distilled description) plus its stem, then single-linkage
clustering by cosine similarity WITHIN each section. Sections are never crossed:
two questions in different sections are different shapes by definition.

USAGE
-----
    python scripts/cluster_mathsa_archetypes.py
    python scripts/cluster_mathsa_archetypes.py --threshold 0.4
    python scripts/cluster_mathsa_archetypes.py --execute
    python scripts/cluster_mathsa_archetypes.py --show 4.9
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_classification_cache.json"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_archetypes.json"

# Similarity above which two questions in the same section are the same shape.
#
# Tuned by inspection on THIS corpus, not carried over. FPM and Maths B use
# 0.45; at that value Maths A section 2.2 collapsed into a single 68-question
# blob whose modal phrase was "complete square quadratic" but whose members were
# index laws, expanding brackets, factorising, making x the subject, algebraic
# fractions and surds -- six shapes, one cluster, and a label that described
# almost none of them.
#
# The cause is structural, not a bad threshold guess: 4MA1 Higher questions are
# SHORT and MULTI-PART ("(a) simplify (b) factorise (c) make t the subject"), so
# nearly every algebra question shares the same generic vocabulary and TF-IDF
# cosine stops discriminating. Longer FPM questions do not have this problem.
#
# Measured sweep (largest cluster / share of questions in a repeated shape):
#
#   0.45 -> 68 / 72%     0.62 -> 33 / 47%
#   0.55 -> 48 / 59%     0.70 -> 21 / 36%     0.78 -> 20 / 27%
#
# Chosen on coherence rather than on the numbers. At 0.70 the largest cluster is
# 21 questions that genuinely are "expand and simplify a product of brackets",
# and completing the square has separated out into its own group of 8. Below
# that, distinct shapes are still merged; above it, genuine repeats start
# splitting and the share in a repeated shape falls away for nothing.
#
# 36% in a repeated shape is lower than FPM's, and that is a real property of
# the subject rather than a clustering failure -- a compound question with three
# unrelated parts has no exact twin.
DEFAULT_THRESHOLD = 0.70

# The archetype phrase is already a distilled description of the shape, so it
# counts for more than raw stem wording.
ARCHETYPE_WEIGHT = 3

STOPWORDS = frozenset(
    """a an the and or of in on at to for with that this these those is are was were be been
    given find show state hence otherwise your you answer answers working question questions
    marks mark total continued write down all stages provided spaces must use used using
    where which such it its as by from not into if then than each other both any some
    diagram figure shows shown accurately drawn nearest correct decimal places significant
    figures value values form terms term expression equation equations solve solution
    solutions calculate determine deduce leaving giving exact""".split()
)

TOKEN_RE = re.compile(r"[a-z]{3,}")


def tokenize(text: str) -> list[str]:
    """Words only: digits and single symbols carry no shape information."""
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def build_document(question: dict, archetype: str) -> Counter:
    """Term counts for one question, with the archetype phrase weighted up."""
    counts = Counter(tokenize(question.get("stem", "")))
    for token in tokenize(archetype):
        counts[token] += ARCHETYPE_WEIGHT
    return counts


def tfidf_vectors(documents: dict[str, Counter]) -> dict[str, dict[str, float]]:
    """L2-normalised TF-IDF vectors, so cosine similarity is a plain dot product."""
    total_docs = len(documents)
    document_frequency: Counter = Counter()
    for counts in documents.values():
        document_frequency.update(counts.keys())

    vectors: dict[str, dict[str, float]] = {}
    for key, counts in documents.items():
        vector: dict[str, float] = {}
        for term, count in counts.items():
            idf = math.log((total_docs + 1) / (document_frequency[term] + 1)) + 1.0
            vector[term] = (1.0 + math.log(count)) * idf

        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        vectors[key] = {term: value / norm for term, value in vector.items()}

    return vectors


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(term, 0.0) for term, value in a.items())


def cluster_section(
    keys: list[str], vectors: dict[str, dict[str, float]], threshold: float
) -> list[list[str]]:
    """
    Single-linkage clustering via connected components.

    Sections hold at most ~40 questions, so the quadratic comparison is trivial
    and an exact method beats an approximate one.
    """
    parent = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i, key_a in enumerate(keys):
        for key_b in keys[i + 1 :]:
            if cosine(vectors[key_a], vectors[key_b]) >= threshold:
                union(key_a, key_b)

    groups: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        groups[find(key)].append(key)

    return sorted(groups.values(), key=len, reverse=True)


def label_for(cluster: list[str], archetypes: dict[str, str]) -> str:
    """The most common model phrase in the cluster, ties broken by length."""
    phrases = [archetypes[key] for key in cluster if archetypes.get(key)]
    if not phrases:
        return "unlabelled"
    counts = Counter(phrases)
    top = max(counts.values())
    return sorted([p for p, c in counts.items() if c == top], key=len)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--execute", action="store_true", help="write the archetypes file")
    parser.add_argument("--show", metavar="SECTION", help="print clusters for one section, e.g. 9.4")
    args = parser.parse_args()

    if not CACHE_PATH.is_file():
        print("No classifications yet. Run classify_mathsa_workbook_sections.py first.")
        return 1

    questions = {
        f"{q['paper_key']}:{q['question_number']}": q
        for q in json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    }
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    by_section: dict[str, list[str]] = defaultdict(list)
    archetypes: dict[str, str] = {}
    documents: dict[str, Counter] = {}

    for key, result in cache.items():
        if key not in questions:
            continue
        by_section[result["primary"]].append(key)
        archetypes[key] = result.get("archetype", "")
        documents[key] = build_document(questions[key], archetypes[key])

    if not documents:
        print("Nothing to cluster.")
        return 1

    vectors = tfidf_vectors(documents)

    clusters: list[dict] = []
    for section in sorted(by_section, key=lambda s: [int(p) for p in s.split(".")]):
        for cluster in cluster_section(by_section[section], vectors, args.threshold):
            clusters.append(
                {
                    "section": section,
                    "label": label_for(cluster, archetypes),
                    "size": len(cluster),
                    "question_ids": sorted(cluster),
                }
            )

    if args.show:
        selected = [c for c in clusters if c["section"] == args.show]
        if not selected:
            print(f"No clusters in section {args.show}")
            return 1
        print(f"\nSection {args.show} -- {len(selected)} archetypes\n")
        for cluster in selected:
            print(f"  [{cluster['size']}x] {cluster['label']}")
            for key in cluster["question_ids"]:
                stem = " ".join(questions[key]["stem"].split())[:96]
                print(f"        {key:<24} {stem}")
            print()
        return 0

    sizes = Counter(c["size"] for c in clusters)
    repeated = [c for c in clusters if c["size"] > 1]
    singletons = len(clusters) - len(repeated)

    print(f"{'=' * 74}\nARCHETYPE CLUSTERING  (threshold {args.threshold})\n{'=' * 74}")
    print(f"  questions clustered : {len(documents)}")
    print(f"  archetypes found    : {len(clusters)}")
    print(f"  with repeats        : {len(repeated)}")
    print(f"  singletons          : {singletons}")
    print(f"  largest cluster     : {max(sizes) if sizes else 0}")
    print(
        f"  questions in a repeated shape: "
        f"{sum(c['size'] for c in repeated)} ({sum(c['size'] for c in repeated) / len(documents):.0%})"
    )

    print("\n  Biggest archetypes")
    for cluster in sorted(repeated, key=lambda c: -c["size"])[:12]:
        print(f"    {cluster['size']:>3}x  [{cluster['section']:>4}]  {cluster['label']}")

    if args.execute:
        OUTPUT_PATH.write_text(json.dumps(clusters, indent=2), encoding="utf-8")
        print(f"\n  written: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    else:
        print("\n  Dry run -- nothing written. Re-run with --execute.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
