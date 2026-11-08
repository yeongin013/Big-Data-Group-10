import csv
import json
from pathlib import Path

questions = Path("tests/h3_questions.csv")
key_path = Path("tests/h3_answer_key.csv")
runs_path = Path("results/h3_router_runs_v2.jsonl")
out_path = Path("results/h3_grading.csv")

key = {}
with key_path.open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        key[row["id"]] = row

answers = {}
with runs_path.open(encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        answers[row["question_id"]] = row

rows = []
with questions.open(encoding="utf-8", newline="") as f:
    for q in csv.DictReader(f):
        expected = key[q["id"]]
        actual = answers.get(q["id"], {})
        text = actual.get("answer", "")
        has_rules = "I cannot answer this from the rule tables." not in text
        passed = has_rules if expected["kind"] == "answer" else not has_rules
        rows.append({
            "id": q["id"],
            "kind": expected["kind"],
            "expected_tool": expected["tool"],
            "actual_tools": ";".join(x["tool"] for x in actual.get("tool_calls", [])),
            "passed": passed,
            "answer_preview": text[:160].replace("\n", " "),
        })

with out_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

passed = sum(r["passed"] for r in rows)
print(f"H3 router baseline: {passed}/{len(rows)} passed")
print(f"Wrote {out_path}")
