"""Rule query API and demo page (standard library only).

    python -m src.api [--port 8000] [--host 127.0.0.1]

Then open http://127.0.0.1:8000 for the demo page.

GET  /api/health                                         model, key present, rule counts
GET  /api/rules_for?product=85123A                       same as the agent tool
GET  /api/top_rules?min_support=0.01&min_confidence=0.5&limit=10
GET  /api/season_filter?period=christmas
POST /api/ask   {"question": "...", "method": "tool" | "paste" | "router"}
                -> answer, tool calls with their outputs, answer check, seconds

The GET endpoints and method "router" need no API key. "tool" and "paste" call Solar (UPSTAGE_API_KEY).
The server binds to 127.0.0.1 by default. It only serves the product-level rule tables.
"""
import argparse
import json
import math
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src import agent, answer_check

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


def route(method, url, body=None):
    u = urlparse(url)
    q = parse_qs(u.query)
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
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self, method):
        if method == "GET" and urlparse(self.path).path in ("/", "/index.html"):
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        try:
            body = None
            if method == "POST":
                n = int(self.headers.get("Content-Length") or 0)
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
