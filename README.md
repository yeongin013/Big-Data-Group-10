# Basket Insight Agent

**Mining Frequent Itemsets from Online Retail Transactions with an Upstage Solar Agent**

빅데이터개론 Group 10 project.

## Team

| Student ID | Name | Role |
|---|---|---|
| 2022270655 | 최영인 | TBD |
| 2022271329 | 정고은 | TBD |
| 2023270643 | 유찬 | TBD |
| 2023271305 | 이현섭 | TBD |

## Problem

An online retailer records hundreds of thousands of transactions. Finding which products customers buy together by hand is not feasible at that scale. Association-rule mining also has two problems of its own. It produces thousands of rules, which no one can read through. And when that many candidate rules are tested, many of them hold only by chance. This project finds product associations that hold over time and makes them easy to query in plain language.

## Data

We use the [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) dataset. It contains about 1 million transactions from a UK-based online retailer, recorded between December 2009 and December 2011, and is licensed under CC BY 4.0. We treat each invoice as one basket. We remove cancellations and non-product rows, and we hash the `Customer ID` field before any analysis.

Raw data is not committed to this repository. To download it, run:

```bash
python scripts/download_data.py
```

The script saves `data/raw/online_retail_II.xlsx` and checks its SHA-256 checksum. It needs only the Python standard library. If you get an SSL certificate error on macOS, run it as `SSL_CERT_FILE=/etc/ssl/cert.pem python scripts/download_data.py`.

## Method

1. **Frequent itemsets (MMDS Chapter 6):** Implement A-Priori and PCY to find frequent item pairs and triples. Derive association rules with support, confidence, and lift. Compare the two algorithms on memory use and run time.
2. **Validation:** Mine rules on an earlier time window and check whether they still hold on a later window. This addresses the risk of false discoveries (MMDS §1.2, Bonferroni's principle).
3. **Baseline:** Compare against a naive baseline that pairs the best-selling products.
4. **LLM agent:** Build an agent on Upstage Solar with tool calls such as `rules_for(product)`, `top_rules(min_support, min_confidence)`, and `season_filter(period)`. The agent answers questions such as "What should we bundle for the Christmas season?" and cites the supporting support and confidence values.

## Deliverables

- A reproducible pipeline with fixed seeds, runnable from a clean checkout, that covers preprocessing, A-Priori, and PCY
- A performance comparison of A-Priori and PCY (memory and time)
- A validated rule set with its out-of-period results
- A Solar-based agent that answers questions about the rules
- A final report and presentation that cover the rubric items: question and scope, method and justification, what the method discards, and reproducibility
