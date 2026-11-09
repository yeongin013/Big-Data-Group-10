"""기존 프로젝트에서 사용하는 A-Priori 함수. 구현은 role2_algorithms에 있다."""
import pandas as pd

from role2_algorithms.basket_mining import BasketDataset, MiningResult, mine_apriori
from role2_algorithms.basket_mining import generate_rules, support_to_count


def min_count(n, s):
    # 빈 기간에서도 최소 횟수는 양수로 둔다.
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
        # 기존 보고서용 삼각 배열 추정치. 실제 메모리 사용량은 아니다.
        "memory_bytes": 4 * m * (m - 1) // 2,
        "memory_kind": "textbook model only; implementation uses a sparse Counter",
        "stats": result.stats,
    }


def rules(pairs, item_counts, n, min_conf=0.5):
    columns = ["antecedent", "consequent", "count", "support", "confidence", "lift"]
    itemsets = {(item,): count for item, count in item_counts.items()}
    itemsets.update(pairs)
    result = MiningResult("apriori", n, 1, 2, dict(item_counts), itemsets)
    # 팀 코드의 기존 기준인 lift > 1을 적용한다.
    rows = [(r.antecedent[0], r.consequent[0], r.count, r.support, r.confidence, r.lift)
            for r in generate_rules(result, min_conf, min_lift=0) if r.lift > 1]
    return pd.DataFrame(rows, columns=columns)
