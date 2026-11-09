"""A-Priori join/prune for size 3. This is not a separate triple-hashing PCY variant."""
from collections import Counter, defaultdict
from itertools import combinations


def generate_triple_candidates(frequent_pairs):
    pairs = set(frequent_pairs)
    by_first = defaultdict(list)
    for a, b in sorted(pairs):
        by_first[a].append(b)
    candidates = set()
    for a, suffixes in by_first.items():
        for b, c in combinations(suffixes, 2):
            if (b, c) in pairs:  # ab, ac are present by construction; require bc too.
                candidates.add((a, b, c))
    return candidates


def extend_triples(dataset, result):
    candidates = generate_triple_candidates(result.of_size(2))
    result.stats.triple_candidates = len(candidates)
    if not candidates:
        return
    relevant = {item for triple in candidates for item in triple}
    counts = Counter()
    for basket in dataset.baskets:
        for triple in combinations([item for item in basket if item in relevant], 3):
            if triple in candidates:
                counts[triple] += 1
                result.stats.triple_count_updates += 1
    result.frequent_itemsets.update({t: c for t, c in sorted(counts.items()) if c >= result.min_count})
