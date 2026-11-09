"""Two-pass A-Priori for pairs, using sparse counters rather than a dense triangle."""
from collections import Counter
from itertools import combinations

from ..models import BasketDataset, MiningResult, MiningStats
from ..thresholds import validate_min_count
from ..extensions.triples import extend_triples


def mine(dataset: BasketDataset, min_count: int, max_size: int = 2) -> MiningResult:
    validate_min_count(min_count)
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size not in (2, 3):
        raise ValueError("max_size must be 2 or 3")
    # Pass 1: each item contributes at most once per basket (input contract).
    item_counts = Counter(item for basket in dataset.baskets for item in basket)
    frequent = {item for item, count in item_counts.items() if count >= min_count}
    m = len(frequent)
    stats = MiningStats(frequent_singletons=m, possible_frequent_item_pairs=m * (m - 1) // 2)

    # Pass 2: an infrequent item cannot belong to a frequent pair (downward closure).
    pair_counts = Counter()
    for basket in dataset.baskets:
        retained = [item for item in basket if item in frequent]
        for pair in combinations(retained, 2):
            stats.pair_occurrences_examined += 1
            pair_counts[pair] += 1
            stats.pair_count_updates += 1
    stats.pair_candidates_observed = len(pair_counts)
    itemsets = {(item,): item_counts[item] for item in sorted(frequent)}
    itemsets.update({pair: count for pair, count in sorted(pair_counts.items()) if count >= min_count})
    result = MiningResult("apriori", len(dataset), min_count, max_size, dict(item_counts), itemsets, stats)
    if max_size == 3:
        extend_triples(dataset, result)
    return result
