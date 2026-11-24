"""Make an empty H3 grading sheet from stored runs (plan §3.4: two graders grade separately).

    python scripts/h3_grade_sheet.py RUNS.jsonl OUT.csv

One row per graded answer (method tool, paste or router; ping rows are skipped). Each grader
fills a copy: grader1 or grader2 with 0/1, and hard with 1 for renamed-product and multi-call
questions. Then put both graders' columns in one file, fill agreed, and save it as
results/h3_grades.csv. `python -m src.run_all --only T6` builds the H3 table from it.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluate import H3_GRADE_COLUMNS  # noqa: E402


def rows(records):
    """Sheet rows for the run records, sorted by method, question and run. Failed runs (no answer) are kept."""
    keep = [r for r in records if r.get("method") in ("tool", "paste", "router")]
    keep.sort(key=lambda r: (r["method"], r["question_id"], r["run"]))
    return [{**dict.fromkeys(H3_GRADE_COLUMNS, ""), "method": r["method"], "run": r["run"],
             "question_id": r["question_id"], "answer_key_sha256": r.get("answer_key_sha256") or ""} for r in keep]


if __name__ == "__main__":
    runs, out = sys.argv[1], sys.argv[2]
    with open(runs, encoding="utf-8") as f:
        sheet = rows([json.loads(line) for line in f if line.strip()])
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=H3_GRADE_COLUMNS)
        w.writeheader()
        w.writerows(sheet)
    print(f"Wrote {len(sheet)} rows to {out}")
