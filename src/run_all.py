"""Builds every table and figure in plan §5 without an API key.

python -m src.run_all            # all
python -m src.run_all --only T2  # one ID
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src import apriori, clean  # noqa: E402

RESULTS = clean.RESULTS


def t1(b):
    """T1: rows per cleaning step (written by clean.load_lines on first build)."""
    log = pd.read_csv(RESULTS / "cleaning_log.csv")
    print(log.to_string(index=False))


def f1(b):
    """F1: baskets per month."""
    m = b.groupby(b.date.dt.to_period("M")).size()
    m.to_csv(RESULTS / "f1_monthly_baskets.csv", header=["baskets"])
    ax = m.plot(kind="bar", figsize=(10, 4), color="#4472c4")
    ax.set_xlabel("month")
    ax.set_ylabel("baskets (invoices)")
    ax.set_title("Baskets per month")
    plt.tight_layout()
    plt.savefig(RESULTS / "f1_monthly_baskets.png", dpi=150)
    plt.close()


def f2(b):
    """F2: Y1 vs Y2 confidence of the Y1 rule set. Rules whose items vanish in Y2 are drawn at conf2 = 0 as x."""
    y1, y2 = b[b.year == 1]["items"], b[b.year == 2]["items"]
    n1 = len(y1)
    r = apriori.run(y1, apriori.min_count(n1, 0.01))
    rules = apriori.rules(r["pairs"], r["item_counts"], n1)
    sets2 = [set(t) for t in y2]
    c2 = {}
    for t in sets2:
        for i in t:
            c2[i] = c2.get(i, 0) + 1
    conf2, gone = [], []
    for x, y in zip(rules.antecedent, rules.consequent):
        both = sum(1 for t in sets2 if x in t and y in t)
        conf2.append(both / c2[x] if c2.get(x) else 0.0)
        gone.append(x not in c2 or y not in c2)
    rules = rules.assign(conf2=conf2, gone=gone)
    rules.to_csv(RESULTS / "f2_conf_y1_y2.csv", index=False)
    fig, ax = plt.subplots(figsize=(5, 5))
    keep = ~rules.gone
    ax.scatter(rules.confidence[keep], rules.conf2[keep], s=12, alpha=0.6, label="rule")
    ax.scatter(rules.confidence[~keep], rules.conf2[~keep], s=24, marker="x", color="red",
               label=f"item gone in Y2 (n={int((~keep).sum())})")
    ax.plot([0, 1], [0, 1], color="grey", lw=0.8)
    ax.axhline(0.5, color="grey", ls="--", lw=0.8)
    ax.set_xlabel("confidence, year 1")
    ax.set_ylabel("confidence, year 2")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(RESULTS / "f2_conf_y1_y2.png", dpi=150)
    plt.close()


def t2(b):
    from src import pcy
    det, tim = pcy.compare(b[b.year == 1]["items"])
    det.to_csv(RESULTS / "pcy_compare.csv", index=False)
    tim.to_csv(RESULTS / "timings.csv", index=False)
    print(det.to_string(index=False))


def t3(b):
    """T3: H1 per seed and summary, plus the §3.3 chance-rule check (shuffle null + Fisher)."""
    from src import evaluate, null_model
    per, summary = evaluate.h1(b)
    per.to_csv(RESULTS / "h1_seeds.csv", index=False)
    pd.DataFrame([summary]).to_csv(RESULTS / "h1_summary.csv", index=False)
    print(json.dumps(summary, indent=1, default=str))
    rows = []
    for sp in null_model.SPACES:
        bs = null_model.space_baskets(b, sp)
        rows.append({"n_baskets": len(bs), **null_model.null_rule_ratio(bs, sp), **null_model.fisher_pass(bs, sp)})
    pd.DataFrame(rows).to_csv(RESULTS / "null_check.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


def t4(b):
    """T4: H2 HitRate@5, CIs, strata."""
    from src import evaluate
    per, strata = evaluate.h2(b)
    per.to_csv(RESULTS / "h2.csv", index=False)
    strata.to_csv(RESULTS / "h2_strata.csv", index=False)
    print(per.to_string(index=False))


def t5(b):
    """T5: §4 sensitivity rows (n_boot=100 per plan §6 fallback; switch to 1000 for the final run)."""
    from src import evaluate
    t = evaluate.sensitivity(b, n_boot=100)
    t.to_csv(RESULTS / "t5_sensitivity.csv", index=False)
    print(t.to_string(index=False))


def t6(b):
    """T6 is built from stored runs and grades; skipped until they exist (plan §3.4)."""
    runs, grades = RESULTS / "agent_runs.jsonl", RESULTS / "h3_grades.csv"
    if not (runs.exists() and grades.exists()):
        print("T6 skipped: results/agent_runs.jsonl or results/h3_grades.csv not present yet")
        return
    raise NotImplementedError("T6 table: add after grading format is fixed (12/1 sprint)")


STEPS = {"T1": t1, "F1": f1, "F2": f2, "T2": t2, "T3": t3, "T4": t4, "T5": t5, "T6": t6}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=STEPS)
    a = p.parse_args()
    RESULTS.mkdir(exist_ok=True)
    baskets = clean.load_baskets()
    for k, f in STEPS.items():
        if a.only in (None, k):
            print(f"== {k}")
            f(baskets)
