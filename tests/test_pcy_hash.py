"""PCY hash is deterministic and matches (i * 1_000_003 + j) % B by hand (plan §3.1)."""
import numpy as np

from src import pcy
from tests.test_textbook import BASKETS, THRESHOLD


def test_formula_by_hand():
    assert pcy.bucket(0, 1, 5) == 1  # (0 + 1) % 5
    assert pcy.bucket(1, 2, 5) == 0  # 1_000_005 % 5
    assert pcy.bucket(2, 3, 65_521) == 34_379  # 2_000_009 - 30 * 65_521
    assert pcy.bucket(np.array([0, 1]), np.array([1, 2]), 5).tolist() == [1, 0]  # vectorized form agrees


def test_bucket_counts_by_hand():
    # ids a0 b1 c2 d3 e4; 1_000_003 % 5 = 3, so bucket = (3i + j) % 5:
    # ab->1 ac->2 ad->3 bc->0 bd->1 cd->4 de->3. Bucket 0: bc 3; 1: ab 4 + bd 2; 2: ac 3; 3: ad 2 + de 1; 4: cd 1
    r = pcy.run(BASKETS, THRESHOLD, 5)
    assert r["bucket_counts"].tolist() == [3, 6, 3, 3, 1]
    assert r["frequent_bucket_ratio"] == 0.8
    # candidates: ab ac ad bc bd (cd's bucket is infrequent). ad is a false positive: its bucket is frequent via de
    assert r["n_candidates"] == r["n_candidates_all"] == 5
    assert r["memory_pass1_bytes"] == 20 and r["memory_pass2_bytes"] == (5 + 7) // 8 + 12 * 5


def test_deterministic():
    r1, r2 = pcy.run(BASKETS, THRESHOLD, 7), pcy.run(BASKETS, THRESHOLD, 7)
    assert np.array_equal(r1["bucket_counts"], r2["bucket_counts"])
    assert r1["n_candidates"] == r2["n_candidates"] and r1["pairs"] == r2["pairs"]


if __name__ == "__main__":
    for t in (test_formula_by_hand, test_bucket_counts_by_hand, test_deterministic):
        t()
        print("ok", t.__name__)
