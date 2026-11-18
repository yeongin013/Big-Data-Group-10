"""Grade the H3 keyword-router baseline against the answer key (plan §3.4, auxiliary metric).

    python scripts/grade_h3.py

Reads tests/h3_questions.csv, tests/h3_answer_key.csv and results/h3_router_runs.jsonl
(written by: python -m src.agent --router tests/h3_questions.csv --key tests/h3_answer_key.csv
 --out results/h3_router_runs.jsonl), then writes results/h3_grading.csv.

Grading: for each question, the router's recorded tool calls are replayed against the rule
tables. An answer row passes when the replayed rule ids cover every expected rule id in the
key. A trap row passes when the answer says the data cannot answer it.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import agent  # noqa: E402

QUESTIONS = ROOT / "tests/h3_questions.csv"
KEY = ROOT / "tests/h3_answer_key.csv"
RUNS = ROOT / "results/h3_router_runs.jsonl"
OUT = ROOT / "results/h3_grading.csv"

NO_ANSWER = "I cannot answer this from the rule tables."

key = defaultdict(list)
with KEY.open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        key[row["id"]].append(row)

answers = {}
with RUNS.open(encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        answers.setdefault(rec["question_id"], []).append(rec)

rows, misses = [], []
with QUESTIONS.open(encoding="utf-8", newline="") as f:
    for q in csv.DictReader(f):
        qid = q["id"]
        runs = answers.get(qid, [])
        expected = {rid for r in key[qid] for rid in r["rule_ids"].split(";") if rid}
        kind = key[qid][0]["kind"]
        tool_rows = []
        got = set()
        for rec in runs:
            for call in rec.get("tool_calls", []):
                tool_rows.append(f"{call['tool']}({json.dumps(call['args'], ensure_ascii=False)})")
                try:
                    got |= {x["rule_id"] for x in agent.TOOLS[call["tool"]](**call["args"])["rules"]}
                except Exception as e:  # bad call from the router: no rules from it
                    misses.append(f"{qid}: {call['tool']}(**{call['args']}) -> {e}")
        if not runs:
            misses.append(f"{qid}: no run recorded")
        trapped = all(NO_ANSWER in rec.get("answer", NO_ANSWER) for rec in runs)
        passed = (not trapped) and expected and expected <= got if kind == "answer" else trapped
        rows.append({
            "id": qid,
            "kind": kind,
            "n_runs": len(runs),
            "expected_tools": ";".join(sorted({r["tool"] for r in key[qid]})),
            "actual_calls": ";".join(tool_rows[:3]),
            "passed": bool(passed),
            "answer_preview": (runs[0]["answer"][:160].replace("\n", " ") if runs else ""),
        })

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

n_pass = sum(r["passed"] for r in rows)
print(f"H3 router baseline: {n_pass}/{len(rows)} passed ({n_pass / len(rows):.1%})")
for m in misses:
    print("warn:", m)
print(f"Wrote {OUT}")
