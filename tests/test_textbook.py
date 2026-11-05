"""A-Priori and PCY on a small hand-counted example in the style of MMDS Example 6.1 / 6.7."""
from src import apriori, pcy

# 8 baskets over items a..e. Hand counts: a 5, b 5, c 4, d 3, e 2.
# Pairs: ab 4, ac 3, bc 3, ad 2, bd 2, cd 1, de 1.
BASKETS = [("a", "b", "c"), ("a", "b"), ("a", "c"), ("b", "c"),
           ("a", "b", "d"), ("d", "e"), ("a", "b", "c", "d"), ("e",)]
THRESHOLD = 3  # support count; e (2) is infrequent, so de is never counted in pass 2
EXPECTED_PAIRS = {("a", "b"): 4, ("a", "c"): 3, ("b", "c"): 3}


def test_apriori():
    r = apriori.run(BASKETS, THRESHOLD)
    assert r["frequent"] == ["a", "b", "c", "d"]
    assert r["pairs"] == EXPECTED_PAIRS
    assert r["n_candidates"] == 6  # C(4, 2) cells in the triangular array
    assert r["n_occurring"] == 6  # ab ac ad bc bd cd all appear at least once


def test_pcy_agrees():
    a = apriori.run(BASKETS, THRESHOLD)
    for b in (1, 2, 5, 101):  # B=1: every bucket frequent, PCY degenerates to A-Priori
        p = pcy.run(BASKETS, THRESHOLD, b)
        assert p["frequent"] == a["frequent"]
        assert p["pairs"] == a["pairs"] == EXPECTED_PAIRS, b


def test_rules():
    # n = 8. conf(a->b) = 4/5, lift = 0.8 / (5/8) = 1.28; conf(c->a) = 3/4, lift = 0.75 / (5/8) = 1.2
    r = apriori.rules(EXPECTED_PAIRS, apriori.run(BASKETS, THRESHOLD)["item_counts"], n=len(BASKETS))
    got = {(x, y): (round(c, 6), round(l, 6)) for x, y, c, l in zip(r.antecedent, r.consequent, r.confidence, r.lift)}
    assert got == {("a", "b"): (0.8, 1.28), ("b", "a"): (0.8, 1.28),
                   ("c", "a"): (0.75, 1.2), ("c", "b"): (0.75, 1.2),
                   ("a", "c"): (0.6, 1.2), ("b", "c"): (0.6, 1.2)}
    assert list(r.antecedent[:2]) == ["a", "b"]  # sorted by confidence, then support


if __name__ == "__main__":
    for t in (test_apriori, test_pcy_agrees, test_rules):
        t()
        print("ok", t.__name__)
