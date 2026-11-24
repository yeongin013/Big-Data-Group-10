"""Grade the H3 keyword-router baseline against the answer key (plan §3.4, auxiliary metric).

    python scripts/grade_h3.py                    defaults read and write OUTSIDE the repo
    python scripts/grade_h3.py --questions Q.csv --key K.csv --runs R.jsonl --out G.csv

Each path comes from the CLI argument first, then the H3_QUESTIONS / H3_ANSWER_KEY / H3_RUNS /
H3_OUT environment variable, then a default file name under H3_DIR (environment, else the
folder that contains this repository). Per the 2026-11-20 team decision the questions, answer
key and grading results stay outside every branch until the agent-v1 tag, so the defaults
point at that outside folder and writing inside the repo prints a warning.

Router runs to grade are produced the same way, also outside:

    python -m src.agent --router ../h3_questions.csv --key ../h3_answer_key.csv \
        --out ../h3_router_runs.jsonl

Grading: for each question, the router's recorded tool calls are replayed against the rule
tables. An answer row passes when the replayed rule ids cover every expected rule id in the
key. A trap row passes when the answer says the data cannot answer it. The key SHA-256 used
is recorded in every output row (plan §3.4).
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import agent  # noqa: E402

NO_ANSWER = "I cannot answer this from the rule tables."


def _path(arg_value, env_name, default_name, h3_dir):
    """CLI argument > environment variable > default file name under the H3 folder."""
    raw = arg_value or os.environ.get(env_name) or (h3_dir / default_name)
    return Path(raw).expanduser()


def main():
    g = argparse.ArgumentParser(description="Grade H3 router runs against the outside-repo answer key.")
    g.add_argument("--questions", metavar="CSV", help="question file (env H3_QUESTIONS)")
    g.add_argument("--key", metavar="CSV", help="answer key file (env H3_ANSWER_KEY)")
    g.add_argument("--runs", metavar="JSONL", help="router/tool run records (env H3_RUNS)")
    g.add_argument("--out", metavar="CSV", help="grading result file (env H3_OUT)")
    g.add_argument("--h3-dir", metavar="DIR", help="base folder for the defaults (env H3_DIR)")
    a = g.parse_args()

    h3_dir = Path(a.h3_dir or os.environ.get("H3_DIR") or ROOT.parent).resolve()
    questions = _path(a.questions, "H3_QUESTIONS", "h3_questions.csv", h3_dir)
    key_path = _path(a.key, "H3_ANSWER_KEY", "h3_answer_key.csv", h3_dir)
    runs_path = _path(a.runs, "H3_RUNS", "h3_router_runs.jsonl", h3_dir)
    out_path = _path(a.out, "H3_OUT", "h3_router_grading.csv", h3_dir)

    if out_path.resolve().is_relative_to(ROOT.resolve()):
        print(f"warn: --out {out_path} is inside the repo; grading results stay outside until the agent-v1 tag")

    for label, p in (("questions", questions), ("answer key", key_path), ("runs", runs_path)):
        if not p.is_file():
            g.error(f"{label} file not found: {p}")

    key_sha = hashlib.sha256(key_path.read_bytes()).hexdigest()

    key = defaultdict(list)
    with key_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key[row["id"]].append(row)

    answers = {}
    with runs_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            answers.setdefault(rec["question_id"], []).append(rec)

    rows, misses = [], []
    with questions.open(encoding="utf-8", newline="") as f:
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
                "key_sha256": key_sha,
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    n_pass = sum(r["passed"] for r in rows)
    print(f"H3 router baseline: {n_pass}/{len(rows)} passed ({n_pass / len(rows):.1%})")
    for m in misses:
        print("warn:", m)
    print(f"Wrote {out_path}")
    print(f"Answer key SHA-256: {key_sha}")


if __name__ == "__main__":
    main()
