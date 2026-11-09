"""Team API adapter for Hyeonseop's independent A-Priori implementation.

Core: role2_algorithms/basket_mining/algorithms/apriori.py
This file preserves the interfaces used by evaluate.py, agent.py and run_all.py.
"""
import pandas as pd

from role2_algorithms.basket_mining import BasketDataset, MiningResult, mine_apriori
from role2_algorithms.basket_mining import generate_rules, support_to_count


def min_count(n, s):
    # Empty partitions have no frequent itemsets; retain a positive threshold.
    if n == 0:
        support_to_count(1, s)  # validate the ratio
        return 1
    return support_to_count(n, s)


def run(baskets, threshold, max_size=2):
    dataset = BasketDataset.from_rows(baskets)
    result = mine_apriori(dataset, threshold, max_size)
    m = result.stats.frequent_singletons
    return {
        "item_counts": result.item_counts,
        "frequent": sorted(i[0] for i in result.of_size(1)),
        "pairs": result.of_size(2), "triples": result.of_size(3),
        "n_candidates": result.stats.possible_frequent_item_pairs,
        "n_occurring": result.stats.pair_candidates_observed,
        "n_candidates_all": result.stats.possible_frequent_item_pairs,
        # Legacy field is the textbook 4-byte triangular-array MODEL, not actual RAM.
        "memory_bytes": 4 * m * (m - 1) // 2,
        "memory_kind": "textbook model only; implementation uses a sparse Counter",
        "stats": result.stats,
    }


def rules(pairs, item_counts, n, min_conf=0.5):
    columns = ["antecedent", "consequent", "count", "support", "confidence", "lift"]
    itemsets = {(item,): count for item, count in item_counts.items()}
    itemsets.update(pairs)
    result = MiningResult("apriori", n, 1, 2, dict(item_counts), itemsets)
    # Preserve the existing team's STRICT lift > 1 policy at the adapter boundary.
    rows = [(r.antecedent[0], r.consequent[0], r.count, r.support, r.confidence, r.lift)
            for r in generate_rules(result, min_conf, min_lift=0) if r.lift > 1]
    return pd.DataFrame(rows, columns=columns)
