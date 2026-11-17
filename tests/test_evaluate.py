"""Small hand-made checks for src/evaluate.py and src/null_model.py. Run: python -m tests.test_evaluate"""
import math
from collections import Counter
from unittest.mock import patch

import numpy as np
import pandas as pd

from src import evaluate as ev, null_model as nm


def _b(*baskets):
    return pd.DataFrame({"items": [tuple(sorted(t)) for t in baskets]})


def _r(*pairs):
    return pd.DataFrame(pairs, columns=["antecedent", "consequent"])


def test_holds_edge_cases():
    ev_b = _b("ab", "ab", "ab", "a", "c", "c")  # a in 4, b in 3, both 3 -> conf .75, lift .75/(3/6) = 1.5
    h = ev.holds(_r(("a", "b"), ("a", "z"), ("z", "a")), ev_b, min_ante=1)
    assert list(h) == [True, False, False]  # consequent z absent; antecedent z absent
    assert not ev.holds(_r(("a", "b")), ev_b, min_ante=5).iloc[0]  # antecedent in 4 < 5 baskets
    # consequent in every basket: conf 1 but lift = 1 -> not held
    assert not ev.holds(_r(("a", "b")), _b("ab", "ab", "b"), min_ante=1).iloc[0]


def test_recommend_and_hitrate():
    idx = {"a": [("b", 0.9, 0.1), ("c", 0.8, 0.2)], "d": [("c", 0.9, 0.3), ("e", 0.9, 0.1)]}
    b0 = ["z", "a", "y", "b"]
    # c: max conf .9 via d (support .3) beats b (.9, .1) and e (.9, .1); b < e by code; fill from B0 skipping visible
    assert ev.recommend(("a", "d"), idx, b0) == ["c", "b", "e", "z", "y"]
    assert ev.recommend(("a",), {}, b0) == ["z", "y", "b"]  # B0 alone, visible a removed
    # toy HitRate: mask one item per basket
    cases = [(("a",), "b"), (("a",), "q"), (("d",), "e")]
    hits = [m in ev.recommend(v, idx, b0, k=2) for v, m in cases]
    assert hits == [True, False, True] and abs(np.mean(hits) - 2 / 3) < 1e-12


def test_fisher_small_case():
    # N=10, K=4, m=4, a=3: P(X>=3) = [C(4,3)C(6,1) + C(4,4)C(6,0)] / C(10,4) = 25/210
    assert abs(nm.fisher_greater(3, 4, 4, 10) - 25 / 210) < 1e-12
    assert abs(nm.fisher_greater(0, 4, 4, 10) - 1.0) < 1e-12
    assert abs(nm.fisher_greater(4, 4, 4, 10) - 1 / math.comb(10, 4)) < 1e-12


def test_max_product_support():
    assert nm.max_product_support([]) == 0.0
    assert nm.max_product_support([(1, 2), (1,), (2,)]) == 2 / 3


def test_shuffle_keeps_margins():
    bs = [tuple("abc"), tuple("ab"), tuple("acd"), tuple("bd"), tuple("a")]
    out, left = nm.shuffle(bs, np.random.default_rng(0))
    assert left == 0 and all(len(set(t)) == len(t) for t in out)
    assert sorted(map(len, out)) == sorted(map(len, bs))
    assert Counter(i for t in out for i in t) == Counter(i for t in bs for i in t)


def test_split_reaches_target():
    df = pd.DataFrame({"customer": [3, 3, 1, -1, -1, 2], "invoice": ["6", "5", "4", "3", "2", "1"]})
    ids, sizes = ev._units(df)
    assert list(ids) == [2, 2, 0, 4, 3, 1] and list(sizes) == [1, 1, 2, 1, 1]  # members by number, then guests by invoice
    m = ev._split(ids, sizes, 3, np.random.default_rng(0))
    assert m.sum() >= 3 and m[0] == m[1]  # same customer stays on one side


def test_ci_is_reproducible():
    d = np.array([0.0, 1.0, 1.0, 0.0])
    unit = np.array(["a", "a", "b", "b"])
    assert np.array_equal(ev._ci(d, unit, 100, seed=7), ev._ci(d, unit, 100, seed=7))


def test_sensitivity_helpers():
    baskets = pd.DataFrame({
        "items": [("a", "b"), ("a", "c"), ("a", "b"), ("d",)],
        "year": [1, 1, 2, 2],
        "customer": [1, 2, 1, -1],
    })
    rules = pd.DataFrame({"antecedent": ["a"], "consequent": ["b"]})
    assert len(ev.top5_filter(rules, baskets)) <= 1
    trimmed = ev.drop_top1pct(baskets)
    assert set(trimmed.columns) == set(baskets.columns)


def test_merge_same_day_combines_member_invoices_but_not_guests():
    lines = pd.DataFrame({
        "invoice": ["m1", "m2", "g1", "g2"],
        "code": ["A", "B", "A", "B"],
        "description": ["a", "b", "a", "b"],
        "quantity": [1, 1, 1, 1],
        "date": pd.to_datetime(["2010-01-01 09:00", "2010-01-01 15:00",
                                 "2010-01-01 09:00", "2010-01-01 15:00"]),
        "price": [1.0] * 4,
        "customer": [7, 7, -1, -1],
        "country": ["UK"] * 4,
    })
    baskets = ev.merge_same_day(lines)
    member = baskets[baskets.customer == 7].iloc[0]
    assert tuple(member["items"]) == ("A", "B")
    assert len(baskets[baskets.customer == 7]) == 1
    assert len(baskets[baskets.customer == -1]) == 2


def test_sensitivity_changed_flag():
    b = pd.DataFrame({
        "items": [("a", "b"), ("a", "c")],
        "year": [1, 2],
        "customer": [1, 1],
        "country": ["UK", "UK"],
    })
    calls = {"h1": 0, "h2": 0}

    def fake_h1(*args, **kwargs):
        calls["h1"] += 1
        summary = {"mean_D": 0.10, "H1_yes": calls["h1"] == 1, "n_rules_full": 1}
        return pd.DataFrame({"n_rules": [1]}), summary

    def fake_h2(*args, **kwargs):
        calls["h2"] += 1
        per = pd.DataFrame({"diff": [0.05], "ci_cust_lo": [0.03],
                            "H2_yes": [calls["h2"] == 1]})
        return per, pd.DataFrame()

    with patch.object(ev, "h1", side_effect=fake_h1), \
         patch.object(ev, "h2", side_effect=fake_h2), \
         patch.object(ev, "merge_same_day", return_value=b):
        out = ev.sensitivity(b, lines=pd.DataFrame(), h1_seeds=range(1), mask_seeds=range(1), n_boot=1)
    assert not bool(out.loc[0, "changed"])
    assert out["changed"].iloc[1:].all()


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
