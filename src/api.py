"""Rule query API and demo page (standard library only).

    python -m src.api [--port 8000] [--host 127.0.0.1]

Then open http://127.0.0.1:8000 for the demo page.

GET  /api/health                                         model, key present, rule counts
GET  /api/rules_for?product=85123A                       same as the agent tool
GET  /api/top_rules?min_support=0.01&min_confidence=0.5&limit=10
GET  /api/season_filter?period=christmas
POST /api/ask   {"question": "...", "method": "tool" | "paste" | "router"}
                -> answer, tool calls with their outputs, answer check, seconds
POST /api/jobs  {"dataset": "y1" | "all", "support": 0.01, "memory_budget_bytes": 67108864,
                 "strategy": "rules" | "solar_once" | "solar_pilot", "deadline": optional ISO 8601}
                -> the queued job (H4, see src/jobs.py)
GET  /api/jobs                                           the 20 newest jobs (no history)
GET  /api/jobs/3                                         status, chosen setting, selection history, stats
GET  /api/jobs/3/results[?format=csv][&limit=50]         frequent pairs of a completed job, with product names

The GET endpoints and method "router" need no API key. "tool" and "paste" call Solar (UPSTAGE_API_KEY).
The server binds to 127.0.0.1 by default. It only serves the product-level rule tables.
"""
import argparse
import csv
import io
import json
import math
import re
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src import agent, answer_check, jobs

PAGE = Path(__file__).resolve().parent.parent / "web" / "index.html"
METHODS = {"tool": agent.ask_tools, "router": agent.ask_router, "paste": agent.ask_paste}
MAX_QUESTION = 1000


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def has_key():
    try:
        agent.api_key()
        return True
    except SystemExit:
        return False


def health():
    y1, season = agent.tables()
    return {"model": agent.MODEL, "has_key": has_key(), "n_rules_y1": len(y1), "n_rules_season": len(season),
            "n_baskets_y1": int(y1.n_baskets.iloc[0]), "n_baskets_season": int(season.n_baskets.iloc[0]),
            "methods": {"router": True, "tool": has_key(), "paste": has_key()}}


def _num(params, name, default, cast=float):
    v = params.get(name, [None])[0]
    if v in (None, ""):
        return default
    try:
        value = cast(v)
        if not math.isfinite(value):
            raise ValueError()
        return value
    except ValueError:
        raise ApiError(400, f"{name} must be a number")


def ask(body):
    question = str(body.get("question", "")).strip()
    method = body.get("method", "tool")
    if not question:
        raise ApiError(400, "question is empty")
    if len(question) > MAX_QUESTION:
        raise ApiError(400, f"question is longer than {MAX_QUESTION} characters")
    if method not in METHODS:
        raise ApiError(400, f"method must be one of {sorted(METHODS)}")
    if method != "router" and not has_key():
        raise ApiError(503, "UPSTAGE_API_KEY is not set. Put it in .env, or use method 'router'.")
    trace = []
    t0 = time.perf_counter()
    try:
        answer, _ = METHODS[method](question, trace) if method != "paste" else METHODS[method](question)
    except SystemExit as e:  # agent.chat reports API errors with SystemExit
        raise ApiError(502, str(e))
    seconds = round(time.perf_counter() - t0, 2)
    if method == "paste":  # the whole table is the source
        y1, season = agent.tables()
        outputs = [agent._result(y1), agent._result(season)]
    else:
        outputs = [t["output"] for t in trace]
    return {"question": question, "method": method, "model": None if method == "router" else agent.MODEL,
            "answer": answer, "tool_calls": trace, "check": answer_check.check(answer, outputs, question),
            "seconds": seconds}


class Csv:
    """A CSV download instead of a JSON reply."""

    def __init__(self, text, filename):
        self.raw, self.filename = text.encode(), filename


def job_route(method, path, q, body):
    """The three H4 job routes. Returns None when the path is not a job route."""
    m = re.fullmatch(r"/api/jobs(?:/(\d{1,9})(/results)?)?", path)
    if not m:
        return None
    job_id, want_results = m.group(1), m.group(2)
    try:
        if method == "POST" and job_id is None:
            return jobs.submit(body or {})
        if method == "GET" and job_id is None:
            return {"jobs": jobs.recent()}
        if method == "GET" and job_id and not want_results:
            return jobs.get(int(job_id))
        if method == "GET" and want_results:
            job, rows = jobs.results(int(job_id))
            if q.get("format", [""])[0] == "csv":
                out = io.StringIO()
                w = csv.DictWriter(out, fieldnames=["a", "a_name", "b", "b_name", "count"], lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
                return Csv(out.getvalue(), f"job_{job_id}_pairs.csv")
            limit = max(1, min(_num(q, "limit", len(rows) or 1, int), len(rows) or 1))
            return {"id": job["id"], "setting": job["setting"], "n_frequent_pairs": len(rows),
                    "csv": f"/api/jobs/{job_id}/results?format=csv", "pairs": rows[:limit]}
    except jobs.JobError as e:
        raise ApiError(e.status, str(e))
    return None


def route(method, url, body=None):
    u = urlparse(url)
    q = parse_qs(u.query)
    job_reply = job_route(method, u.path, q, body)
    if job_reply is not None:
        return job_reply
    if method == "GET" and u.path == "/api/health":
        return health()
    if method == "GET" and u.path == "/api/rules_for":
        product = q.get("product", [""])[0].strip()
        if not product:
            raise ApiError(400, "product is required")
        return agent.rules_for(product)
    if method == "GET" and u.path == "/api/top_rules":
        return agent.top_rules(_num(q, "min_support", agent.SUPPORT), _num(q, "min_confidence", agent.CONF),
                               max(1, min(_num(q, "limit", 10, int), 500)))
    if method == "GET" and u.path == "/api/season_filter":
        return agent.season_filter(q.get("period", ["christmas"])[0])
    if method == "POST" and u.path == "/api/ask":
        return ask(body or {})
    raise ApiError(404, f"no route {method} {u.path}")


class Handler(BaseHTTPRequestHandler):
    server_version = "BasketInsight/1"

    def _send(self, status, data, ctype="application/json; charset=utf-8"):
        filename = None
        if isinstance(data, Csv):
            data, ctype, filename = data.raw, "text/csv; charset=utf-8", data.filename
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self, method):
        try:
            host = self.headers.get("Host", "")
            if not re.fullmatch(r"(?:127\.0\.0\.1|localhost)(?::\d{1,5})?", host, re.I):
                raise ApiError(403, "Host must be localhost or 127.0.0.1")
            if method == "GET" and urlparse(self.path).path in ("/", "/index.html"):
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            body = None
            if method == "POST":
                if self.headers.get_content_type() != "application/json":
                    raise ApiError(415, "Content-Type must be application/json")
                raw_length = self.headers.get("Content-Length", "")
                if not re.fullmatch(r"[0-9]+", raw_length):
                    raise ApiError(400, "Content-Length must be a non-negative integer")
                n = int(raw_length)
                if n > 64 * 1024:
                    raise ApiError(413, "request body too large")
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except json.JSONDecodeError:
                    raise ApiError(400, "body must be JSON")
                if not isinstance(body, dict):
                    raise ApiError(400, "body must be a JSON object")
            self._send(200, route(method, self.path, body))
        except ApiError as e:
            self._send(e.status, {"error": str(e)})
        except Exception:
            traceback.print_exc()
            self._send(500, {"error": "internal error (see server log)"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def log_message(self, fmt, *args):
        if not self.server.quiet:
            super().log_message(fmt, *args)


def serve(host="127.0.0.1", port=8000, quiet=False):
    agent.tables()  # load (or build) the rule tables before the first request
    jobs.start_worker()
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.quiet = quiet
    return srv


def main():
    p = argparse.ArgumentParser(description="Basket Insight rule API and demo page")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    srv = serve(a.host, a.port)
    print(f"Demo: http://{a.host}:{srv.server_port}  (Solar key: {'yes' if has_key() else 'no, router only'})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
