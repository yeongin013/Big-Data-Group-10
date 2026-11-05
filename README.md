# Basket Insight Agent

**Mining Frequent Itemsets from Online Retail Transactions with an Upstage Solar Agent**

빅데이터개론 Group 10 project.

## Team

| Student ID | Name | Role |
|---|---|---|
| 2022270655 | 최영인 | Data & reproducibility: `clean.py`, `run_all`, data section and discarded-information table, reproduction rehearsals, `test_slide_numbers`, H3 question set and grading |
| 2022271329 | 정고은 | Algorithms: `apriori.py`, `pcy.py`, textbook and hash tests, T2 |
| 2023270643 | 유찬 | Evaluation: `evaluate.py`, `null_model.py`, H1, H2, customer concentration, sensitivity analysis, H3 question set and grading |
| 2023271305 | 이현섭 | Agent: `agent.py`, Solar tools, paste-in and router baselines, H3 runs |

Changes from the role proposal in plan §7: reproduction rehearsals moved from evaluation to data, and the customer-concentration check (computed in `evaluate.py`) moved from data to evaluation.

## Problem

An online retailer records hundreds of thousands of transactions. Finding which products customers buy together by hand is not feasible at that scale. Association-rule mining also has two problems of its own. It produces thousands of rules, which no one can read through. And when that many candidate rules are tested, many of them hold only by chance. This project finds product associations that hold over time and makes them easy to query in plain language.

## Data

We use the [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) dataset. It contains about 1 million order lines (about 40,000 baskets) from a UK-based online retailer, recorded between December 2009 and December 2011, and is licensed under CC BY 4.0. We analyse 2009-12 to 2011-11 (year 1 against year 2) and drop the partial month 2011-12. We treat each invoice as one basket. We remove cancellations and non-product rows, and we replace the `Customer ID` with a local number only in the local cache. Result files keep only aggregates.

Citation: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. Used under CC BY 4.0. We removed rows and aggregated the data as described above.

Raw data is not committed to this repository. To download it, run:

```bash
python scripts/download_data.py
```

The script saves `data/raw/online_retail_II.xlsx` and checks its SHA-256 checksum. It needs only the Python standard library. If you get an SSL certificate error on macOS, run it as `SSL_CERT_FILE=/etc/ssl/cert.pem python scripts/download_data.py`.

## Method

1. **Frequent itemsets (MMDS Chapter 6):** Implement A-Priori and PCY to find frequent item pairs (triples reported as counts). Derive association rules with support, confidence, and lift. Compare the two algorithms on memory use and run time.
2. **Validation:** Mine rules on an earlier time window and check whether they still hold on a later window. This addresses the risk of false discoveries (MMDS §1.2, Bonferroni's principle).
3. **Baseline:** Compare HitRate@5 on held-out items against a popularity baseline (the five most common year-1 products) and against unfiltered pair rules.
4. **LLM agent:** Build an agent on Upstage Solar with tool calls such as `rules_for(product)`, `top_rules(min_support, min_confidence)`, and `season_filter(period)`. The agent answers questions such as "What should we bundle for the Christmas season?" and cites the supporting support and confidence values.

## Reproduce

No API key is needed. From a clean checkout:

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py && python -m src.run_all   # T3 (shuffle null) takes about 20 minutes
python -m src.run_all --only F2                           # one table or figure: T1 to T6, F1, F2
```

Run the tests (no pytest needed):

```bash
python -m tests.test_textbook && python -m tests.test_pcy_hash && python -m tests.test_evaluate && python -m tests.test_answer_key
```

| ID | Output in `results/` |
|---|---|
| T1 | `cleaning_log.csv` |
| T2 | `pcy_compare.csv`, `timings.csv` (machine-dependent) |
| T3 | `h1_seeds.csv`, `h1_summary.csv`, `null_check.csv` |
| T4 | `h2.csv`, `h2_strata.csv` |
| T5 | `t5_sensitivity.csv` |
| F1 | `f1_monthly_baskets.csv`, `f1_monthly_baskets.png` |
| F2 | `f2_conf_y1_y2.csv`, `f2_conf_y1_y2.png` |
| Agent tables | `rules_y1.csv`, `rules_season.csv` (built by `src.agent` when missing) |

All numbers are first-draft values. Open issues from review round 1 are listed in [`reviews/draft1_review.md`](reviews/draft1_review.md).

## Solar agent setup

The agent needs your own Upstage API key. Copy `.env.example` to `.env` and put the key after `UPSTAGE_API_KEY=`. Never commit `.env`. Then run:

```bash
pip install -r requirements.txt
python -m src.agent --ask "What goes with WHITE HANGING HEART T-LIGHT HOLDER?"
```

TLS uses the `certifi` CA bundle, so no certificate setup is needed.

## Plan

The project plan is in [`plan/plan_v0.6.md`](plan/plan_v0.6.md) (Korean). The evaluation criteria were frozen at tag `plan-v0.6` (commit `685efa9`). After the tag, the file changed only to drop rubric-point labels and internal review scores, and to add the agile process section in §6. The criteria in §1 are unchanged (check with `git diff plan-v0.6 HEAD -- plan/plan_v0.6.md`).

## Deliverables

- A reproducible pipeline with fixed seeds, runnable from a clean checkout, that covers preprocessing, A-Priori, and PCY
- A performance comparison of A-Priori and PCY (memory and time)
- A validated rule set with its out-of-period results
- A Solar-based agent that answers questions about the rules
- A final report and presentation that cover the rubric items: question and scope, method and justification, what the method discards, reproducibility, and delivery
