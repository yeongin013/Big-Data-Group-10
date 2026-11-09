"""빈발 항목집합에서 연관규칙을 계산한다."""
from dataclasses import dataclass
from itertools import combinations
import math


@dataclass(frozen=True)
class Rule:
    antecedent: tuple[str, ...]
    consequent: tuple[str, ...]
    count: int
    support: float
    confidence: float
    lift: float


def generate_rules(result, min_confidence=0.5, min_lift=1.0):
    """Inclusive thresholds. Use min_lift=1.0 to include independence (lift == 1)."""
    if not math.isfinite(min_confidence) or not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be in [0, 1]")
    if not math.isfinite(min_lift) or min_lift < 0:
        raise ValueError("min_lift must be finite and non-negative")
    rules = []
    if result.n_baskets == 0:
        return rules
    for union, count in result.frequent_itemsets.items():
        if len(union) < 2:
            continue
        for size in range(1, len(union)):
            for left in combinations(union, size):
                right = tuple(item for item in union if item not in left)
                conf = count / result.frequent_itemsets[left]
                lift = conf / (result.frequent_itemsets[right] / result.n_baskets)
                if conf >= min_confidence and lift >= min_lift:
                    rules.append(Rule(left, right, count, count / result.n_baskets, conf, lift))
    return sorted(rules, key=lambda r: (-r.confidence, -r.support, r.antecedent, r.consequent))
