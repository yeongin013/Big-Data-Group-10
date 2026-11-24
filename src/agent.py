"""Solar tool-calling agent for H3 (plan §3.4).

    python -m src.agent --ask "question"             one question, tool Solar (needs UPSTAGE_API_KEY)
    python -m src.agent --eval QUESTIONS.csv --key ANSWER_KEY.csv
                                                      tool Solar and paste-in Solar, 3 runs each
    python -m src.agent --router QUESTIONS.csv        keyword router baseline (no key, no LLM)
    python -m src.agent --ping                        Solar connection test (plain chat + one tool call)

Runs are appended to results/agent_runs.jsonl (change with --out).
Only product-level rule tables and the question text are sent to the API. No customer information.
"""
import argparse
import csv
import contextvars
import datetime
import functools
import hashlib
import json
import os
import re
import ssl
import time
import uuid
import urllib.error
import urllib.request

import certifi
import pandas as pd

from src import clean

MODEL = "solar-pro4"  # https://console.upstage.ai/docs/capabilities/function-calling (checked 2026-11-05)
URL = "https://api.upstage.ai/v1/chat/completions"
MAX_TOOL_ROUNDS = 5
RUNS = 3
SUPPORT, CONF = 0.01, 0.5  # fixed rule criteria (plan §1)
RULES_Y1 = clean.RESULTS / "rules_y1.csv"
RULES_SEASON = clean.RESULTS / "rules_season.csv"
SEASON_MONTHS = ("2009-12", "2010-11")
SEASON_WORDS = ("christmas", "xmas", "peak", "holiday", "season", "성수기", "크리스마스") + SEASON_MONTHS
REQUEST_META = contextvars.ContextVar("request_meta", default=None)
COLS = ["rule_id", "antecedent", "antecedent_name", "consequent", "consequent_name",
        "count", "support", "confidence", "lift"]


# ---------- rule tables (product-level aggregates only) ----------

def _mine(baskets, prefix, names):
    from src import apriori  # only required when rebuilding missing tables
    items = list(baskets["items"])
    n = len(items)
    res = apriori.run(items, apriori.min_count(n, SUPPORT))
    r = apriori.rules(res["pairs"], res["item_counts"], n, CONF)
    r.insert(0, "rule_id", [f"{prefix}{k + 1:03d}" for k in range(len(r))])
    r["antecedent_name"] = r.antecedent.map(names)
    r["consequent_name"] = r.consequent.map(names)
    r["n_baskets"] = n
    return r[COLS + ["n_baskets"]]


def build_tables():
    """Mine the Y1 rule set and the peak-season rule set; write both CSVs."""
    lines = clean.load_lines()
    b, names = clean.load_baskets(lines), clean.descriptions(lines)
    y1 = b[b.year == 1]
    season = y1[y1.date.dt.strftime("%Y-%m").isin(SEASON_MONTHS)]
    _mine(y1, "Y", names).to_csv(RULES_Y1, index=False)
    _mine(season, "S", names).to_csv(RULES_SEASON, index=False)


@functools.cache
def tables():
    if not (RULES_Y1.exists() and RULES_SEASON.exists()):
        build_tables()
    read = lambda p: pd.read_csv(p, dtype={"antecedent": str, "consequent": str})
    return read(RULES_Y1), read(RULES_SEASON)


def _records(df):
    out = df[COLS].copy()
    out[["support", "confidence", "lift"]] = out[["support", "confidence", "lift"]].round(4)
    return out.to_dict("records")


def _result(df, **info):
    res = {**info, "n_baskets": int(df.n_baskets.iloc[0]) if len(df) else None,
           "n_rules": len(df), "rules": _records(df)}
    if not len(df):
        res["message"] = "No rules match. The data cannot answer this."
    return res


# ---------- tools (read the tables only, never compute new numbers) ----------

def rules_for(product):
    """Y1 rules whose antecedent or consequent is the product (exact code or case-insensitive name substring)."""
    y1, _ = tables()
    q = str(product).strip()
    if not q:
        return _result(y1.iloc[0:0], query=q, table="year 1 (2009-12..2010-11)")
    hit = lambda code, name: (code == q.upper()) | name.str.contains(q, case=False, regex=False, na=False)
    a, c = hit(y1.antecedent, y1.antecedent_name), hit(y1.consequent, y1.consequent_name)
    return _result(y1[a | c], query=q, table="year 1 (2009-12..2010-11)")


def top_rules(min_support=SUPPORT, min_confidence=CONF, limit=10):
    """Y1 rules with support >= min_support and confidence >= min_confidence, highest confidence first."""
    y1, _ = tables()
    df = y1[(y1.support >= float(min_support)) & (y1.confidence >= float(min_confidence))]
    res = _result(df.head(max(1, min(int(limit), 500))), min_support=min_support, min_confidence=min_confidence,
                  table="year 1 (2009-12..2010-11)")
    res["n_matching"] = len(df)
    return res


MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
          "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
OFF_SEASON_WORDS = ("summer", "spring", "autumn", "fall", "winter", "easter",
                    "여름", "봄", "가을", "겨울", "부활절")
PEAK_YEARS = (2009, 2010)
PEAK_ALIASES = ("christmas", "xmas", "peak", "holiday", "season", "성수기", "크리스마스", "연말") + SEASON_MONTHS


def _is_peak_period(p):
    """Team decision (2026-11-17, reviews/change_requests.md): a period names the peak season
    (Y1 months 2009-12 and 2010-11) when it is a peak phrase, or a month+year inside those
    months, with the year limited to 2009/2010 for bare season phrases ("christmas 2010" -> yes,
    "christmas 2011" -> no). Any other season or month/year ("summer season", "easter 2012",
    "december 2010") is not in the data."""
    words = [w for w in re.split(r"[\s,/]+", p) if w]
    if not words or any(w in OFF_SEASON_WORDS for w in words):
        return False
    # years anywhere in the text, so "2011년 크리스마스" is read as 2011 and not as a bare peak phrase
    years = [int(y) for y in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", p)]
    year = next((y for y in years if y not in PEAK_YEARS), years[0] if years else None)
    month = next((MONTHS[w] for w in words if w in MONTHS), None)
    if month is not None:  # a specific month: must be one of the peak months in the right year
        return (year is None and f"-{month:02d}" in " ".join(SEASON_MONTHS)) or \
               (year is not None and f"{year}-{month:02d}" in SEASON_MONTHS)
    if any(w in SEASON_MONTHS for w in words):  # literal "2009-12" / "2010-11"
        return True
    if any(w in PEAK_ALIASES for w in words):  # peak phrase; year, if any, must be a peak year
        return year is None or year in PEAK_YEARS
    return False


def season_filter(period):
    """Peak-season rules (Y1 baskets in 2009-12 and 2010-11). Other periods are not in the data -> empty.

    Accepts peak phrases ("christmas season", "peak", "연말 성수기"), the peak months
    ("2009-12", "december 2009", "november 2010") and season+peak-year phrases
    ("Christmas 2010"). Everything else (other years, other seasons, other months)
    returns no rules.
    """
    _, season = tables()
    p = str(period).strip().lower()
    if _is_peak_period(p):
        return _result(season, period=period, table="peak season (2009-12 and 2010-11)")
    return {"period": period, "n_rules": 0, "rules": [],
            "message": f"Unknown period. Only the peak season ({', '.join(SEASON_MONTHS)}) is available."}


TOOLS = {"rules_for": rules_for, "top_rules": top_rules, "season_filter": season_filter}

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "rules_for", "description": "Association rules (year 1) that involve a product, by stock code or name.",
        "parameters": {"type": "object", "required": ["product"], "properties": {
            "product": {"type": "string", "description": "Stock code (e.g. 85123A) or part of the product name"}}}}},
    {"type": "function", "function": {
        "name": "top_rules", "description": "Strongest rules (year 1) above a support and confidence threshold.",
        "parameters": {"type": "object", "properties": {
            "min_support": {"type": "number", "description": "fraction, e.g. 0.02"},
            "min_confidence": {"type": "number", "description": "fraction, e.g. 0.6"},
            "limit": {"type": "integer", "description": "max rules returned, default 10"}}}}},
    {"type": "function", "function": {
        "name": "season_filter", "description": "Rules mined only from the peak (Christmas) season baskets.",
        "parameters": {"type": "object", "required": ["period"], "properties": {
            "period": {"type": "string", "description": "Peak/Christmas season, 2009-12 or 2010-11 (also December 2009, November 2010). Other periods return no rules."}}}}},
]

SYSTEM = ("You answer questions about product association rules from a UK online gift retailer. "
          "A → B means baskets with A also contain B; there is no order. "
          "Answer only from tool outputs. Cite the support and confidence numbers you use. "
          "Do not compute or invent other numbers. If the tools return no rules, say you cannot answer. "
          "Answer in the language of the question.")


# ---------- Solar API ----------

@functools.cache
def api_key():
    key = os.environ.get("UPSTAGE_API_KEY", "").strip()
    for d in [clean.ROOT, *clean.ROOT.parents]:  # worktrees live under the main checkout
        if key:
            break
        env = d / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("UPSTAGE_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("UPSTAGE_API_KEY is not set (environment or .env). Add it to .env to use Solar.")
    return key


# certifi's CA bundle, so TLS works on any machine (python.org macOS builds ship without one)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def post(body):
    """POST one chat-completions request. Returns the full response JSON."""
    req = urllib.request.Request(URL, json.dumps(body).encode(), {
        "Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CONTEXT) as r:
                response = json.load(r)
            meta = REQUEST_META.get()
            if meta is not None:
                meta["models"].append(response.get("model"))
            return response
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            retryable = not isinstance(e, urllib.error.HTTPError) or e.code == 429 or 500 <= e.code <= 599
            if not retryable or attempt == 2:
                status = getattr(e, "code", None)
                raise SystemExit(f"Solar API request failed: HTTP {status}" if status else "Solar API unreachable") from e
            meta = REQUEST_META.get()
            if meta is not None:
                meta["http_retries"].append({"attempt": attempt + 1, "status": getattr(e, "code", None)})
            time.sleep(2 ** attempt)


def chat(messages, tools=None):
    body = {"model": MODEL, "messages": messages, "temperature": 0}
    if tools:
        body |= {"tools": tools, "tool_choice": "auto"}
    return post(body)["choices"][0]["message"]


def ping():
    """Connection test: one plain chat and one request with automatic tool selection."""
    t0 = datetime.datetime.now()
    plain = post({"model": MODEL, "temperature": 0,
                  "messages": [{"role": "user", "content": "Reply with the single word: ok"}]})
    tool = post({"model": MODEL, "temperature": 0, "tools": TOOL_SPECS, "tool_choice": "auto",
                 "messages": [{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": "Which products go with stock code 85123A?"}]})
    calls = tool["choices"][0]["message"].get("tool_calls") or []
    return {"method": "ping", "date": datetime.date.today().isoformat(), "model_requested": MODEL,
            "model_served": plain.get("model"), "plain_reply": plain["choices"][0]["message"].get("content"),
            "tool_call_ok": bool(calls),
            "tool_calls": [{"tool": c["function"]["name"], "args": c["function"]["arguments"]} for c in calls],
            "seconds": round((datetime.datetime.now() - t0).total_seconds(), 2)}


def ask_tools(question, trace=None):
    """Tool-calling loop. Returns (answer, tool_calls).
    If trace is a list, each call is also appended to it with its output (for the demo and answer check)."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    calls = []
    for _ in range(MAX_TOOL_ROUNDS):
        msg = chat(messages, TOOL_SPECS)
        if not msg.get("tool_calls"):
            return msg.get("content") or "", calls
        messages.append(msg)
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                out = TOOLS[name](**args)
            except Exception as e:  # bad tool name/arguments from the model: tell it, keep going
                args, out = tc["function"]["arguments"], {"error": str(e)}
            calls.append({"tool": name, "args": args})
            if trace is not None:
                trace.append({"tool": name, "args": args, "output": out})
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out)})
    return "(no answer: tool round limit reached)", calls


def paste_prompt():
    y1, season = tables()
    keep = ["rule_id", "antecedent", "consequent", "count", "support", "confidence", "lift"]
    both = pd.concat([y1, season])
    names = pd.concat([both[["antecedent", "antecedent_name"]].set_axis(["code", "name"], axis=1),
                       both[["consequent", "consequent_name"]].set_axis(["code", "name"], axis=1)])
    return (f"{SYSTEM}\n\nThe tables below are your only source.\n\n"
            f"Year-1 rules (2009-12..2010-11, {y1.n_baskets.iloc[0]} baskets):\n"
            f"{y1[keep].round(4).to_csv(index=False)}\n"
            f"Peak-season rules (2009-12 and 2010-11, {season.n_baskets.iloc[0]} baskets):\n"
            f"{season[keep].round(4).to_csv(index=False)}\n"
            f"Product codes and names:\n{names.drop_duplicates('code').sort_values('code').to_csv(index=False)}")


def ask_paste(question):
    msg = chat([{"role": "system", "content": paste_prompt()}, {"role": "user", "content": question}])
    return msg.get("content") or "", []


# ---------- keyword router baseline (no LLM) ----------

def route(question):
    """Regex/keyword -> one tool call. Returns (tool, args) or None."""
    q = question.lower()
    if any(w in q for w in SEASON_WORDS) or re.search(r"november|december|summer|spring|autumn|fall|여름|봄|가을|\b20\d{2}[-/.]\d{1,2}\b", q):
        return "season_filter", {"period": q}
    if re.search(r"\b(top|strongest|best|highest|above|over|least)\b", q):
        def threshold(label, default):
            match = re.search(label + r"[^\d]{0,30}(\d*\.?\d+)\s*(%?)", q)
            return (float(match[1]) / (100 if match[2] else 1)) if match else default
        return "top_rules", {"min_support": threshold("support", SUPPORT),
                             "min_confidence": threshold("confidence", CONF)}
    if m := re.search(r"\b\d{5}[a-z]*\b", q):
        return "rules_for", {"product": m.group().upper()}
    y1, _ = tables()
    names = set(y1.antecedent_name.dropna()) | set(y1.consequent_name.dropna())
    hits = sorted((n.strip() for n in names if n.strip() and n.strip().lower() in q), key=len, reverse=True)
    return ("rules_for", {"product": hits[0]}) if hits else None


def ask_router(question, trace=None):
    r = route(question)
    if r is None:
        return "I cannot answer this from the rule tables.", []
    tool, args = r
    out = TOOLS[tool](**args)
    if trace is not None:
        trace.append({"tool": tool, "args": args, "output": out})
    if not out["rules"]:
        return "I cannot answer this from the rule tables.", [{"tool": tool, "args": args}]
    lines = [f"{x['antecedent']} ({x['antecedent_name']}) -> {x['consequent']} ({x['consequent_name']}): "
             f"support {x['support']}, confidence {x['confidence']}" for x in out["rules"][:5]]
    return f"{out['n_rules']} rules found. " + "; ".join(lines), [{"tool": tool, "args": args}]


# ---------- CLI ----------

def read_questions(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["id"], r["question"]) for r in csv.DictReader(f)]


def run_eval(path, methods, out, key_path=None):
    key_sha = hashlib.sha256(open(key_path, "rb").read()).hexdigest() if key_path else None
    question_sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    execution_id = str(uuid.uuid4())
    qs = read_questions(path)
    with open(out, "a", encoding="utf-8") as f:
        for method, fn in methods.items():
            for run in range(1, (1 if method == "router" else RUNS) + 1):
                for qid, q in qs:
                    trace = []
                    meta = {"models": [], "http_retries": []}
                    token = REQUEST_META.set(meta)
                    try:
                        try:
                            answer, calls = fn(q, trace) if method != "paste" else fn(q)
                        except SystemExit as e:
                            failure = {"method": method, "run": run, "question_id": qid,
                                       "execution_id": execution_id, "questions_sha256": question_sha,
                                       "answer_key_sha256": key_sha, "date": datetime.date.today().isoformat(),
                                       "models_served": meta["models"], "http_retries": meta["http_retries"],
                                       "error": str(e)}
                            f.write(json.dumps(failure, ensure_ascii=False) + "\n")
                            f.flush()
                            raise
                    finally:
                        REQUEST_META.reset(token)
                    rec = {"model": meta["models"][-1] if meta["models"] else None,
                           "models_served": meta["models"], "http_retries": meta["http_retries"],
                           "execution_id": execution_id, "questions_sha256": question_sha,
                           "date": datetime.date.today().isoformat(),
                           "method": method, "run": run, "question_id": qid, "answer": answer,
                           "tool_calls": calls, "tool_trace": trace, "answer_key_sha256": key_sha}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(method, run, qid, answer[:100].replace("\n", " "))


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ask")
    g.add_argument("--eval", metavar="QUESTIONS_PATH")
    g.add_argument("--router", metavar="QUESTIONS_PATH")
    g.add_argument("--ping", action="store_true", help="Solar connection test; appends to --out (default results/agent_runs.jsonl)")
    p.add_argument("--key", metavar="ANSWER_KEY_PATH", help="answer key; its SHA-256 goes into each record")
    p.add_argument("--out", default=clean.RESULTS / "agent_runs.jsonl")
    a = p.parse_args()
    if a.ping:
        rec = ping()
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    elif a.ask:
        answer, calls = ask_tools(a.ask)
        print(json.dumps(calls, ensure_ascii=False), answer, sep="\n")
    elif a.eval:
        if not a.key:
            p.error("--eval requires --key")
        api_key()  # fail before writing anything
        run_eval(a.eval, {"tool": ask_tools, "paste": ask_paste}, a.out, a.key)
    else:
        run_eval(a.router, {"router": ask_router}, a.out, a.key)


if __name__ == "__main__":
    main()
