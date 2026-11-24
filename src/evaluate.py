"""H1 (time stability), H2 (masked-item prediction) and the T5 sensitivity rows. Definitions: plan_v0.6 §1, §3.2, §4."""
import math
import time

import numpy as np
import pandas as pd

from src import apriori, clean

S = 0.01  # main support (§1)


def year_rules(baskets):
    """Rule set of a basket table at the frozen criteria (support 1%, conf >= 0.5, lift > 1). Returns (rules, apriori result)."""
    n = len(baskets)
    r = apriori.run(baskets["items"], apriori.min_count(n, S))
    return apriori.rules(r["pairs"], r["item_counts"], n), r


# ---------- retention (§1 "유지 판정 공통 규칙") ----------

def eval_stats(rules_df, eval_baskets):
    """Per rule: antecedent / consequent / both counts and conf, lift in the evaluation baskets (no support condition)."""
    items = sorted(set(rules_df.antecedent) | set(rules_df.consequent))
    idx = {it: k for k, it in enumerate(items)}
    n = len(eval_baskets)
    M = np.zeros((n, len(items)), dtype=bool)  # basket x rule-item incidence
    for r, t in enumerate(eval_baskets["items"]):
        for it in t:
            if it in idx:
                M[r, idx[it]] = True
    xi = np.array([idx[x] for x in rules_df.antecedent], dtype=int)
    yi = np.array([idx[y] for y in rules_df.consequent], dtype=int)
    ante, cons = M[:, xi].sum(0), M[:, yi].sum(0)
    both = (M[:, xi] & M[:, yi]).sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        conf = np.where(ante > 0, both / ante, 0.0)
        lift = np.where(cons > 0, conf / (cons / n), 0.0)
    return pd.DataFrame({"ante": ante, "cons": cons, "both": both, "conf": conf, "lift": lift}, index=rules_df.index)


def _held(st, min_ante):
    # conf >= 0.5 implies both items present; antecedent in < min_ante baskets counts as "not held" (§1)
    return (st.ante >= min_ante) & (st.conf >= 0.5) & (st.lift > 1)


def holds(rules_df, eval_baskets, min_ante):
    """Boolean Series per rule: held in eval baskets (min_ante = 10 for halves, 20 for full size)."""
    return _held(eval_stats(rules_df, eval_baskets), min_ante)


# ---------- H1 (§1 H1 정의) ----------

def _units(df):
    """Unit id per basket: members (by customer number) first, then each guest basket (by invoice). Returns (ids, sizes)."""
    mem = (df.customer >= 0).to_numpy()
    cust = np.sort(df.customer[mem].unique())
    guest = np.sort(df.invoice[~mem].to_numpy())
    ids = np.empty(len(df), dtype=np.int64)
    ids[mem] = np.searchsorted(cust, df.customer[mem])
    ids[~mem] = len(cust) + np.searchsorted(guest, df.invoice[~mem].to_numpy())
    return ids, np.bincount(ids, minlength=len(cust) + len(guest))


def _split(ids, sizes, target, rng):
    """Permute units, take them in order until the basket count first reaches target. Returns basket mask."""
    perm = rng.permutation(len(sizes))
    stop = np.searchsorted(np.cumsum(sizes[perm]), target)  # first position with cum >= target
    return np.isin(ids, perm[:stop + 1])


def h1(b, seeds=range(10), rule_filter=None):
    """Per-seed table and summary dict. rule_filter(rules, train_baskets) -> rules (used by the §4 customer row)."""
    y1 = b[b.year == 1].reset_index(drop=True)
    y2 = b[b.year == 2].reset_index(drop=True)  # incl. 1-item baskets
    u1, s1 = _units(y1)
    u2, s2 = _units(y2)
    rows = []
    for k in seeds:
        rng = np.random.default_rng(k)  # one generator per seed, used for both splits
        inA = _split(u1, s1, len(y1) // 2, rng)
        A, B = y1[inA], y1[~inA]
        Y = y2[_split(u2, s2, len(B), rng)]
        rules, _ = year_rules(A)
        if rule_filter:
            rules = rule_filter(rules, A)
        sB, sY = eval_stats(rules, B), eval_stats(rules, Y)
        hB, hY = _held(sB, 10), _held(sY, 10)
        aux = (sB.ante >= 10) & (sY.ante >= 10)
        cA = set(A.customer[A.customer >= 0])
        rows.append({"seed": k, "n_A": len(A), "n_B": len(B), "n_Y2k": len(Y), "n_rules": len(rules),
                     "R_split": hB.mean(), "R_time_half": hY.mean(), "D": hB.mean() - hY.mean(),
                     "n_rules_aux": int(aux.sum()), "D_aux": hB[aux].mean() - hY[aux].mean(),
                     "A_cust_in_Y2k": len(cA & set(Y.customer)) / len(cA)})
    per = pd.DataFrame(rows)
    # full-size auxiliary report (§1 보조 보고): Y1 rule set vs all of Y2, antecedent threshold 20
    rules, _ = year_rules(y1)
    if rule_filter:
        rules = rule_filter(rules, y1)
    st = eval_stats(rules, y2)
    conf1, conf2 = rules.confidence, st.conf  # conf2 = 0 when the antecedent is absent in Y2
    summary = {"mean_D": per.D.mean(), "min_D": per.D.min(), "max_D": per.D.max(),
               "mean_R_split": per.R_split.mean(), "mean_R_time_half": per.R_time_half.mean(),
               "mean_D_aux": per.D_aux.mean(), "H1_yes": bool(per.D.mean() <= 0.10),
               "n_rules_full": len(rules), "R_time_full": _held(st, 20).mean(),
               "spearman_conf": conf1.rank().corr(conf2.rank()),
               "share_conf_within_0.1": ((conf2 - conf1).abs() <= 0.1).mean()}
    return per, summary


# ---------- H2 (§3.2) ----------

def _index(x, y, conf, sup):
    """antecedent -> [(consequent, conf, support)] sorted by conf desc, support desc, code asc."""
    df = pd.DataFrame({"x": x, "y": y, "conf": conf, "sup": sup})
    df = df.sort_values(["x", "conf", "sup", "y"], ascending=[True, False, False, True])
    return {k: list(zip(g.y, g.conf, g.sup)) for k, g in df.groupby("x", sort=False)}


def recommend(visible, index, b0_order, k=5):
    """§3.2 rule recommender. Candidate score = max conf over rules from visible items (tie: larger support);
    rank by score, then support of that rule, then code; fill with B0 order. index={} gives B0 itself."""
    V = set(visible)
    best = {}
    for x in visible:
        got = 0
        for y, c, s in index.get(x, ()):
            if y in V:
                continue
            if y not in best or (c, s) > best[y]:
                best[y] = (c, s)
            got += 1
            if got == k:  # a top-k candidate is always within its best antecedent's top-k non-visible list
                break
    top = sorted(best, key=lambda y: (-best[y][0], -best[y][1], y))[:k]
    for y in b0_order:
        if len(top) == k:
            break
        if y not in V and y not in top:
            top.append(y)
    return top


def _ci(d, unit, n_boot, seed=0):
    """Percentile 95% CI of mean(d), resampling units with replacement (per-unit sums, then index resampling)."""
    codes, uniq = pd.factorize(unit)
    S, N = np.bincount(codes, weights=d), np.bincount(codes)
    rng = np.random.default_rng(seed)
    est = np.empty(n_boot)
    for r in range(n_boot):
        i = rng.integers(len(uniq), size=len(uniq))
        est[r] = S[i].sum() / N[i].sum()
    return np.percentile(est, [2.5, 97.5])


def h2(b, mask_seeds=range(5), n_boot=1000, rule_filter=None, b1=True):
    """Per-seed HitRate@5 table (with CIs) and size-quartile strata table."""
    y1 = b[b.year == 1]
    n1 = len(y1)
    rules, r = year_rules(y1)
    if rule_filter:
        rules = rule_filter(rules, y1)
    cnt = r["item_counts"]
    b0_order = sorted(cnt, key=lambda i: (-cnt[i], i))
    methods = {"rules": _index(rules.antecedent, rules.consequent, rules.confidence, rules.support), "b0": {}}
    if b1:  # B1: every Y1 pair seen >= 5 times, P(y|x), no support/conf/lift criteria
        p = apriori.run(y1["items"], 5)["pairs"]
        a, bb = np.array([k[0] for k in p]), np.array([k[1] for k in p])
        c = np.array(list(p.values()))
        ca, cb = np.array([cnt[i] for i in a]), np.array([cnt[i] for i in bb])
        methods["b1"] = _index(np.r_[a, bb], np.r_[bb, a], np.r_[c / ca, c / cb], np.r_[c, c] / n1)
    ev = b[(b.year == 2) & (b["items"].str.len() >= 2)]  # sorted by invoice
    items = list(ev["items"])
    size = np.array([len(t) for t in items])
    unit = np.where(ev.customer >= 0, "c" + ev.customer.astype(str), "g" + ev.invoice.astype(str))
    quart = pd.qcut(size, 4, duplicates="drop").astype(str)
    rows, strata = [], []
    for s in mask_seeds:
        rng = np.random.default_rng(s)
        m = [rng.integers(len(t)) for t in items]  # basket order = invoice order
        masked = np.array([t[i] for t, i in zip(items, m)])
        hits = {}
        for name, idx in methods.items():
            hits[name] = np.array([t[i] in recommend(t[:i] + t[i + 1:], idx, b0_order)
                                   for t, i in zip(items, m)])
        d = hits["rules"].astype(float) - hits["b0"]
        new = np.array([x not in cnt for x in masked])  # masked item never seen in Y1
        row = {"seed": s, "n": len(items)}
        row.update({f"hit_{k}": v.mean() for k, v in hits.items()})
        row["diff"] = d.mean()
        row["ci_cust_lo"], row["ci_cust_hi"] = _ci(d, unit, n_boot)
        row["ci_basket_lo"], row["ci_basket_hi"] = _ci(d, np.arange(len(d)), n_boot)
        row["new_item_share"] = new.mean()
        row.update({f"hit_{k}_excl_new": v[~new].mean() for k, v in hits.items()})
        rows.append(row)
        for q in sorted(set(quart), key=lambda q: float(q.split(",")[0][1:])):
            sel = quart == q
            strata.append({"seed": s, "size_quartile": q, "n": int(sel.sum()),
                           **{f"hit_{k}": v[sel].mean() for k, v in hits.items()}})
    per = pd.DataFrame(rows)
    per["H2_yes"] = bool((per.ci_cust_lo >= 0.02).all())  # all 5 customer-bootstrap lower bounds >= +2%p
    return per, pd.DataFrame(strata)


# ---------- §4 sensitivity (판정 rows only) ----------

def top5_filter(rules, train):
    """Drop rules whose top-5 customers make >= 50% of the rule's member baskets (guests excluded from both sides)."""
    mem = train[train.customer >= 0]
    want = set(rules.antecedent) | set(rules.consequent)
    pos = {i: set() for i in want}
    for r, t in enumerate(mem["items"]):
        for i in t:
            if i in want:
                pos[i].add(r)
    cust = mem.customer.to_numpy()
    keep = []
    for x, y in zip(rules.antecedent, rules.consequent):
        c = cust[list(pos[x] & pos[y])]
        top5 = np.sort(np.bincount(c))[::-1][:5].sum() if len(c) else 0
        keep.append(len(c) == 0 or top5 / len(c) < 0.5)
    return rules[np.array(keep, dtype=bool)]


def drop_top1pct(b):
    """Drop baskets above the 99th size percentile, per year."""
    size = b["items"].str.len()
    return b[size <= size.groupby(b.year).transform(lambda s: s.quantile(0.99))]


def merge_same_day(lines=None):
    """Basket table where one member's invoices on the same calendar day are one basket (guests unchanged)."""
    lines = clean.load_lines() if lines is None else lines
    m = lines.customer >= 0
    key = [lines.customer[m], lines.date[m].dt.normalize()]
    lines = lines.copy()
    lines.loc[m, "invoice"] = lines[m].groupby(key).invoice.transform("min")
    return clean.load_baskets(lines)


def sensitivity(b, lines=None, n_boot=1000, h1_seeds=range(10), mask_seeds=range(5)):
    """T5: rerun H1 and H2 per 판정 row (§4 재실행 방법) and flag 'changed' per the §4 definition."""
    variants = [("baseline", b, None),
                ("drop top 1% largest baskets per year", drop_top1pct(b), None),
                ("drop rules with top-5 customer share >= 50%", b, top5_filter),
                ("drop guests", b[b.customer >= 0], None),
                ("merge same customer same day", merge_same_day(lines), None),
                ("UK only", b[b.country == "United Kingdom"], None)]
    rows = []
    for name, bb, f in variants:
        t = time.time()
        p1, s1 = h1(bb, h1_seeds, rule_filter=f)
        p2, _ = h2(bb, mask_seeds, n_boot, rule_filter=f, b1=False)
        rows.append({"row": name, "n_Y1": int((bb.year == 1).sum()), "n_Y2": int((bb.year == 2).sum()),
                     "mean_n_rules_half": p1.n_rules.mean(), "n_rules_full": s1["n_rules_full"],
                     "mean_D": s1["mean_D"], "H1_yes": s1["H1_yes"], "mean_diff": p2["diff"].mean(),
                     "min_ci_cust_lo": p2.ci_cust_lo.min(), "H2_yes": bool(p2.H2_yes.iloc[0]),
                     "seconds": round(time.time() - t, 1)})
    df = pd.DataFrame(rows)
    base = df.iloc[0]
    df["changed"] = ((df.H1_yes != base.H1_yes) | (df.H2_yes != base.H2_yes)
                     | ((df.mean_D - base.mean_D).abs() >= 0.05) | ((df.mean_diff - base.mean_diff).abs() >= 0.02))
    df.loc[0, "changed"] = False
    return df


# ---------- §4 descriptive rows (서술 rows: numbers only, no verdict) ----------

def qty_overlap(rules, y1_lines, k=20):
    """How many of the top-k rules by support are also in the top-k by quantity-weighted support.
    Quantity weight of a rule = total units of its two products over the baskets that hold both."""
    q = y1_lines.groupby(["invoice", "code"]).quantity.sum()
    per_item = {c: g.droplevel("code") for c, g in q.groupby(level="code")}
    weight = []
    for x, y in zip(rules.antecedent, rules.consequent):
        both = per_item[x].index.intersection(per_item[y].index)
        weight.append(per_item[x][both].sum() + per_item[y][both].sum())
    r = rules.assign(weight=weight)
    key = lambda df: set(zip(df.antecedent, df.consequent))
    by_support = r.sort_values(["support", "antecedent", "consequent"], ascending=[False, True, True]).head(k)
    by_weight = r.sort_values(["weight", "antecedent", "consequent"], ascending=[False, True, True]).head(k)
    return len(key(by_support) & key(by_weight))


def coverage(b, mask_seed=0):
    """Distinct products recommended at least once to the Y2 evaluation baskets, per method (masking as in H2)."""
    y1 = b[b.year == 1]
    rules, r = year_rules(y1)
    cnt = r["item_counts"]
    b0_order = sorted(cnt, key=lambda i: (-cnt[i], i))
    p = apriori.run(y1["items"], 5)["pairs"]
    a, bb = np.array([k[0] for k in p]), np.array([k[1] for k in p])
    c = np.array(list(p.values()))
    ca, cb = np.array([cnt[i] for i in a]), np.array([cnt[i] for i in bb])
    methods = {"rules": _index(rules.antecedent, rules.consequent, rules.confidence, rules.support), "b0": {},
               "b1": _index(np.r_[a, bb], np.r_[bb, a], np.r_[c / ca, c / cb], np.r_[c, c] / len(y1))}
    items = list(b[(b.year == 2) & (b["items"].str.len() >= 2)]["items"])
    rng = np.random.default_rng(mask_seed)
    m = [rng.integers(len(t)) for t in items]
    return {name: len({y for t, i in zip(items, m) for y in recommend(t[:i] + t[i + 1:], idx, b0_order)})
            for name, idx in methods.items()}


def descriptive(b, lines, cancel_codes):
    """T5 서술 rows of plan §4 as a (row, value, note) table. cancel_codes: product codes of the cancelled order lines."""
    y1, y2 = b[b.year == 1], b[b.year == 2]
    rules, r = year_rules(y1)
    n1 = len(y1)
    y1_lines = lines[lines.invoice.isin(set(y1.invoice))]
    st = eval_stats(rules, y2)
    cov = coverage(b)
    loose = apriori.rules(r["pairs"], r["item_counts"], n1, min_conf=0.3)
    sl = eval_stats(loose, y2)
    multi = y1[y1["items"].str.len() >= 2]
    rules_multi, _ = year_rules(multi)
    rule_items = set(rules.antecedent) | set(rules.consequent)
    codes = pd.Series(cancel_codes).str.upper()
    rows = [
        ("quantity: top-20 by support also in top-20 by quantity weight", qty_overlap(rules, y1_lines), "of 20"),
        ("product turnover: rules with a product that is gone in year 2", int(((st.ante == 0) | (st.cons == 0)).sum()),
         f"of {len(rules)}"),
        ("long tail: distinct products recommended, rules", cov["rules"], "mask seed 0, includes B0 fill"),
        ("long tail: distinct products recommended, B0", cov["b0"], "mask seed 0"),
        ("long tail: distinct products recommended, B1", cov["b1"], "mask seed 0, includes B0 fill"),
        ("confidence 0.3: number of rules", len(loose), f"main set has {len(rules)}"),
        ("confidence 0.3: share held in year 2 (conf >= 0.3, lift > 1, antecedent >= 20)",
         float(((sl.ante >= 20) & (sl.conf >= 0.3) & (sl.lift > 1)).mean()), ""),
        ("1-item baskets left out of the support denominator: number of rules", len(rules_multi),
         f"{len(multi)} baskets, threshold {apriori.min_count(len(multi), S)}"),
        ("cancellations: share of cancelled order lines with a rule product", float(codes.isin(rule_items).mean()),
         f"{len(codes)} cancelled lines after exact-duplicate removal"),
        ("3-item sets: frequent triples at support 1%",
         apriori.count_frequent_triples(y1["items"], r["pairs"], apriori.min_count(n1, S)), "count only"),
    ]
    return pd.DataFrame(rows, columns=["row", "value", "note"])


# ---------- H3 table (§3.4) ----------

H3_GRADE_COLUMNS = ["method", "run", "question_id", "hard", "grader1", "grader2", "agreed", "answer_key_sha256"]


def wilson(k, n, z=1.959964):
    """Wilson 95% interval for k correct out of n."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    mid, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (mid - half) / (1 + z * z / n), (mid + half) / (1 + z * z / n)


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def h3_table(grades, runs, committed_key_sha):
    """T6 from the grading sheet and the stored runs. Returns (per-method table, verdict dict).

    grades: one row per graded answer with H3_GRADE_COLUMNS. method is tool, paste or router;
    hard is 1 for renamed-product and multi-call questions; grader1, grader2 and agreed are 0/1.
    runs: records of results/agent_runs.jsonl. committed_key_sha: answer-key SHA-256 committed before agent-v1.
    A question is correct when at least 2 of its 3 runs are (the router runs once, so 1 of 1).
    """
    shas = set(grades.answer_key_sha256)
    if shas != {committed_key_sha}:
        raise ValueError(f"grades use answer key {sorted(shas)}, committed is {committed_key_sha}: grade again")
    run_keys = {(r["method"], r["run"], r["question_id"]): r for r in runs if r.get("method") != "ping"}
    for key in zip(grades.method, grades.run, grades.question_id):
        if key not in run_keys:
            raise ValueError(f"graded answer {key} is not in agent_runs.jsonl")
        if run_keys[key].get("answer_key_sha256") != committed_key_sha:
            raise ValueError(f"run {key} was made with another answer key: run and grade again")
    rows, correct = [], {}
    for method, g in grades.groupby("method"):
        per_q = g.groupby("question_id").agg(right=("agreed", "sum"), n=("agreed", "size"), hard=("hard", "max"))
        ok = per_q.right * 2 > per_q.n
        correct[method] = ok
        lo, hi = wilson(int(ok.sum()), len(ok))
        rows.append({"method": method, "n_questions": len(ok), "n_correct": int(ok.sum()), "accuracy": ok.mean(),
                     "wilson_lo": lo, "wilson_hi": hi,
                     "n_split_questions": int(((per_q.right > 0) & (per_q.right < per_q.n)).sum()),
                     "n_grader_disagreements": int((g.grader1 != g.grader2).sum()),
                     "n_hard": int(per_q.hard.sum()), "n_hard_correct": int(ok[per_q.hard == 1].sum())})
    table = pd.DataFrame(rows).set_index("method")
    verdict = {}
    if "tool" in table.index:
        verdict["cond1_accuracy_ge_80"] = bool(table.accuracy["tool"] >= 0.8)
    if {"tool", "router"} <= set(table.index):
        verdict["cond2_hard_beats_router"] = bool(table.n_hard_correct["tool"] > table.n_hard_correct["router"])
        verdict["H3_yes"] = verdict["cond1_accuracy_ge_80"] and verdict["cond2_hard_beats_router"]
    if {"tool", "paste"} <= set(table.index):
        t, p = correct["tool"].align(correct["paste"], join="inner")
        verdict["mcnemar_p_tool_vs_paste"] = mcnemar_exact(int((t & ~p).sum()), int((~t & p).sum()))
    return table.reset_index(), verdict


if __name__ == "__main__":
    import sys
    n_boot = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    out = clean.RESULTS
    pd.set_option("display.width", 200, "display.max_columns", 30)
    b = clean.load_baskets()
    t = time.time()
    per, summ = h1(b)
    per.to_csv(out / "h1_seeds.csv", index=False)
    pd.DataFrame([summ]).to_csv(out / "h1_summary.csv", index=False)
    print(per.round(4).to_string(index=False), "\n", summ, f"\nH1 {time.time() - t:.1f}s")
    t = time.time()
    per, strata = h2(b, n_boot=n_boot)
    per.to_csv(out / "h2.csv", index=False)
    strata.to_csv(out / "h2_strata.csv", index=False)
    print(per.round(4).to_string(index=False), "\n", strata.round(4).to_string(index=False), f"\nH2 {time.time() - t:.1f}s")
    t = time.time()
    t5 = sensitivity(b, n_boot=1000)
    t5.to_csv(out / "t5_sensitivity.csv", index=False)
    print(t5.round(4).to_string(index=False), f"\nT5 {time.time() - t:.1f}s")
