"""Answer check (plan §3.4 scoring rules, applied automatically).

Every number in an answer must come from one of three sources: the question text, the output of a tool
called for that answer, or (when grading) the answer key. Numbers from anywhere else count as invented.

This is a helper for the demo and for spotting bad runs early. It is NOT the H3 grade: the graders still
compare each answer against the answer key by hand.

    python -m src.answer_check results/agent_runs.jsonl [--questions QUESTIONS.csv]

New logs retain the actual tool outputs. Older logs fall back to querying the current tables,
which may differ from the tables used during the original run.
"""
import argparse
import csv
import json
import re
from collections import Counter

RATIO_TOL = 0.005  # plan §3.4: ratios within ±0.005, counts exact

# A number not glued to letters, so stock codes like 85123A and rule IDs like Y001 are skipped.
NUMBER = re.compile(r"(?<![A-Za-z0-9_.,])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?|\.\d+)(\s*%|\s*퍼센트)?(?![A-Za-z0-9_]|,\d)")
LIST_MARKER = re.compile(r"^\s*(?:[-*]\s*)?\d+[.)]\s", re.M)  # "1. ", "2) " at line start
REFUSAL = re.compile(
    r"cannot answer|can't answer|unable to answer|no (?:matching )?rules|not (?:in|available in) the data|"
    r"does not (?:exist|appear)|no data|답(?:변)?할 수 없|답변드릴 수 없|알 수 없|찾을 수 없|규칙이 없|데이터에 없|존재하지 않", re.I)


def numbers(text):
    """Numbers in text as (shown, value, is_percent). Leading list markers ("1. ") are skipped."""
    text = LIST_MARKER.sub(" ", text or "")
    out = []
    for m in NUMBER.finditer(text):
        raw, pct = m.group(1), bool(m.group(2))
        out.append((m.group(0).strip(), float(raw.replace(",", "")), pct))
    return out


def _walk(x):
    """All strings and numbers inside a tool output."""
    if isinstance(x, dict):
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _walk(v)
    elif x is not None:
        yield x


def allowed_values(outputs, question="", extra=()):
    """Values an answer may cite: every number in the tool outputs, the question and extra (e.g. the key)."""
    vals = set()
    for v in [*_walk(outputs), question, *extra]:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            vals.add(float(v))
        else:

            for _, n, pct in numbers(str(v)):
                vals.add(n / 100 if pct else n)
    return vals


def supported(value, is_percent, allowed):
    """Is a cited number backed by an allowed value? Percent and ratio forms are interchangeable."""
    forms = [value / 100] if is_percent else [value]
    if not is_percent and 1 < value <= 100 and value != int(value):
        forms.append(value / 100)  # "43.2" written without the % sign
    for f in forms:
        for a in allowed:
            if f == a:
                return True
            # ratios (both sides in [0, 1]) get the ±0.005 tolerance; counts must be exact
            if 0 <= a <= 1 and 0 <= f <= 1 and abs(f - a) <= RATIO_TOL + 1e-12:
                return True
    return False


def check(answer, outputs, question="", extra=()):
    """Check one answer. outputs: list of tool outputs (dicts) from this answer.

    verdict is one of
      ok          every cited number is backed by a source
      invented    at least one number is not in any source (counts as wrong under plan §3.4)
      no_numbers  the tools found rules but the answer cites no number (counts as wrong)
      refusal     the tools found nothing and the answer says it cannot answer (right for a trap question)
      unclear     the tools found nothing, no numbers, but no clear refusal either
    """
    allowed = allowed_values(outputs, question, extra)
    cited = numbers(answer)
    bad = [shown for shown, v, pct in cited if not supported(v, pct, allowed)]
    n_rules = sum(o.get("n_rules", 0) for o in outputs if isinstance(o, dict))
    refused = bool(REFUSAL.search(answer or ""))
    if bad:
        verdict = "invented"
    elif n_rules == 0 and not cited:
        verdict = "refusal" if refused else "unclear"
    elif not cited:
        verdict = "no_numbers"
    else:
        verdict = "ok"
    return {"verdict": verdict, "cited": [s for s, _, _ in cited], "unsupported": bad,
            "n_rules_from_tools": n_rules, "refused": refused, "n_tool_calls": len(outputs)}


# ---------- re-check a run log ----------

def rerun_outputs(tool_calls):
    from src import agent  # imported here so check() works without pandas
    outs = []
    for c in tool_calls:
        args = c["args"]
        try:
            args = json.loads(args) if isinstance(args, str) else args
            outs.append(agent.TOOLS[c["tool"]](**args))
        except Exception as e:  # the model sent a bad call; the agent got an error back too
            outs.append({"error": str(e)})
    return outs


def check_log(path, questions=None):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("method") == "ping":
                continue
            q = (questions or {}).get(r.get("question_id"), "")
            if r.get("method") == "paste":  # paste-in Solar reads the whole table, so its source is the table
                from src import agent
                y1, season = agent.tables()
                outs = [agent._result(y1), agent._result(season)]
            elif "tool_trace" in r:
                outs = [entry["output"] for entry in r["tool_trace"]]
            else:
                outs = rerun_outputs(r.get("tool_calls", []))
            res = check(r.get("answer", ""), outs, q)
            rows.append({"method": r.get("method"), "run": r.get("run"), "question_id": r.get("question_id"),
                         **res})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("log", help="agent_runs.jsonl")
    p.add_argument("--questions", help="questions CSV (id, question); numbers in the question become allowed")
    p.add_argument("--out", help="write per-answer results to this CSV")
    a = p.parse_args()
    qs = None
    if a.questions:
        with open(a.questions, newline="", encoding="utf-8") as f:
            qs = {r["id"]: r["question"] for r in csv.DictReader(f)}
    rows = check_log(a.log, qs)
    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["method", "run", "question_id", "verdict", "unsupported", "cited",
                                   "n_rules_from_tools", "refused", "n_tool_calls"])
            w.writeheader()
            for r in rows:
                w.writerow({**r, "unsupported": " ".join(r["unsupported"]), "cited": " ".join(r["cited"])})
    for (method, verdict), n in sorted(Counter((r["method"], r["verdict"]) for r in rows).items()):
        print(f"{method:7s} {verdict:11s} {n}")
    for r in rows:
        if r["verdict"] == "invented":
            print(f"  {r['method']} run {r['run']} {r['question_id']}: not in any source -> {r['unsupported']}")


if __name__ == "__main__":
    main()
