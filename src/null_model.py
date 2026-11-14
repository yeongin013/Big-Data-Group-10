"""Chance-rule check (plan_v0.6 §3.3, MMDS §1.2.3 Bonferroni): shuffle null and one-sided Fisher + Bonferroni."""
import math
import time

import numpy as np
import pandas as pd

from src import apriori, clean

SPACES = ["main", "support_0.25", "b1", "peak"]


def max_product_support(baskets):
    """Return the largest single-product support for these baskets."""
    baskets = list(baskets)
    if not baskets:
        return 0.0
    _, _, _, item_counts = count_space(baskets, "main")
    return max(item_counts.values(), default=0) / len(baskets)


def space_baskets(b, space):
    """Baskets of a search space: Y1 for all, peak = Y1 baskets in 2009-12 and 2010-11."""
    y1 = b[b.year == 1]
    if space == "peak":
        y1 = y1[y1.date.dt.month.isin([11, 12])]
    return list(y1["items"])


def count_space(baskets, space):
    """(number of 'rules', Bonferroni denominator, real rule/pair table with counts) for one space (§3.3 table)."""
    n = len(baskets)
    if space == "b1":  # B1 has no confidence criterion: count pairs seen >= 5 times
        r = apriori.run(baskets, 5)
        t = pd.DataFrame([(a, c, k) for (a, c), k in r["pairs"].items()], columns=["antecedent", "consequent", "count"])
        return len(t), len(t), t, r["item_counts"]
    s = 0.0025 if space == "support_0.25" else 0.01
    r = apriori.run(baskets, apriori.min_count(n, s))
    t = apriori.rules(r["pairs"], r["item_counts"], n)
    return len(t), r["n_occurring"], t, r["item_counts"]  # denominator: co-occurring pairs of frequent items


def shuffle(baskets, rng, retries=100):
    """Shuffle the item column over all (basket, item) slots; basket sizes and item counts stay fixed.
    Colliding slots (same item twice in a basket) are re-shuffled together with as many random slots, up to
    `retries` times. Leftover duplicates are dropped (baskets are sets). Returns (baskets, leftover)."""
    codes = np.array(sorted({i for t in baskets for i in t}))
    pos = {c: k for k, c in enumerate(codes)}
    bid = np.repeat(np.arange(len(baskets)), [len(t) for t in baskets])
    it = rng.permutation(np.array([pos[i] for t in baskets for i in t]))
    for _ in range(retries + 1):
        o = np.lexsort((it, bid))
        dup = o[1:][(bid[o][1:] == bid[o][:-1]) & (it[o][1:] == it[o][:-1])]
        if len(dup) == 0 or _ == retries:
            break
        slots = np.unique(np.r_[dup, rng.integers(len(it), size=len(dup))])
        it[slots] = rng.permutation(it[slots])
    o = np.lexsort((it, bid))
    keep = np.r_[True, (bid[o][1:] != bid[o][:-1]) | (it[o][1:] != it[o][:-1])]
    o = o[keep]
    cuts = np.flatnonzero(np.diff(bid[o])) + 1
    return [tuple(codes[it[g]]) for g in np.split(o, cuts)], len(dup)


def null_rule_ratio(baskets, space, seeds=range(100)):
    """Mean null rule count / real rule count. If one null run takes > 10 s, seeds are cut to the first 20 (§3.3)."""
    real = count_space(baskets, space)[0]
    counts, left, sec = [], [], None
    seeds = list(seeds)
    for k, s in enumerate(seeds):
        t = time.time()
        nb, lo = shuffle(baskets, np.random.default_rng(s))
        counts.append(count_space(nb, space)[0])
        left.append(lo)
        if k == 0:
            sec = time.time() - t
            if sec > 10:
                seeds = seeds[:20]
        if k + 1 >= len(seeds):
            break
    return {"space": space, "n_seeds": len(counts), "real_rules": real, "null_mean": np.mean(counts),
            "null_max": max(counts), "ratio": np.mean(counts) / real if real else np.nan,
            "leftover_collisions_mean": np.mean(left), "leftover_collisions_max": max(left), "sec_one_run": sec}


def _lfact(n, _cache={}):
    """log(i!) for i = 0..n via math.lgamma, cached."""
    if n not in _cache:
        _cache[n] = np.array([math.lgamma(i + 1) for i in range(n + 1)])
    return _cache[n]


def fisher_greater(a, K, m, N):
    """One-sided Fisher p = P(X >= a), X ~ Hypergeom(N baskets, K with x, m draws = baskets with y)."""
    lf = _lfact(N)
    k = np.arange(a, min(K, m) + 1)
    lp = lf[K] - lf[k] - lf[K - k] + lf[N - K] - lf[m - k] - lf[N - K - m + k] - (lf[N] - lf[m] - lf[N - m])
    top = lp.max()
    return float(math.exp(top) * np.exp(lp - top).sum())  # log-sum-exp


def fisher_pass(baskets, space, alpha=0.05):
    """Share of the space's real rules (pairs for b1) with Fisher p <= alpha / Bonferroni denominator."""
    n_rules, denom, t, cnt = count_space(baskets, space)
    N = len(baskets)
    p = np.array([fisher_greater(c, cnt[x], cnt[y], N) for x, y, c in zip(t.antecedent, t.consequent, t["count"])])
    return {"space": space, "denominator": denom, "fisher_alpha": alpha / denom, "fisher_pass_share": (p <= alpha / denom).mean()}


if __name__ == "__main__":
    import sys
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    b = clean.load_baskets()
    rows = []
    for sp in SPACES:
        t = time.time()
        bs = space_baskets(b, sp)
        row = {"n_baskets": len(bs), **null_rule_ratio(bs, sp, range(n_seeds)), **fisher_pass(bs, sp)}
        row["seconds"] = round(time.time() - t, 1)
        print(row, flush=True)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(clean.RESULTS / "null_check.csv", index=False)
    print(df.to_string(index=False))
