"""H3 answer key check (plan §3.4): answer rows return rules, trap rows return none.

    H3_ANSWER_KEY=/path/to/h3_answer_key.csv python -m tests.test_answer_key
Without H3_ANSWER_KEY it runs on tests/sample_answer_key.csv (SAMPLE, not the real key).
Key columns: id, kind (answer|trap), tool, args (JSON object of tool arguments).
"""
import csv
import json
import os
from pathlib import Path

from src import agent

SAMPLE = Path(__file__).with_name("sample_answer_key.csv")


def check_key(path):
    """Returns a list of failure messages (empty = pass)."""
    failures = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = len(agent.TOOLS[row["tool"]](**json.loads(row["args"]))["rules"])
            if row["kind"] == "answer" and n == 0:
                failures.append(f"{row['id']}: answer row returned no rules")
            elif row["kind"] == "trap" and n > 0:
                failures.append(f"{row['id']}: trap row returned {n} rules")
            elif row["kind"] not in ("answer", "trap"):
                failures.append(f"{row['id']}: unknown kind {row['kind']!r}")
    return failures


def test_answer_key():
    path = os.environ.get("H3_ANSWER_KEY") or SAMPLE
    failures = check_key(path)
    assert not failures, "\n".join(failures)
    print(f"ok: {path}")


if __name__ == "__main__":
    test_answer_key()
