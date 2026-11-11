"""Rule API and the tool loop, offline (no API key; Solar is replaced by a scripted fake).
Run: python -m tests.test_api
"""
import json
import threading
import urllib.error
import urllib.request

from src import agent, api


def _fake_chat(script):
    """Returns a chat() replacement that plays back the scripted assistant messages in order."""
    seen = []

    def chat(messages, tools=None):
        seen.append([m["role"] for m in messages])
        return script.pop(0)
    return chat, seen


def test_tool_loop_with_fake_solar():
    call = {"id": "c1", "type": "function", "function": {"name": "rules_for", "arguments": '{"product": "85123A"}'}}
    bad = {"id": "c2", "type": "function", "function": {"name": "no_such_tool", "arguments": "{}"}}
    chat, seen = _fake_chat([{"role": "assistant", "content": None, "tool_calls": [call, bad]},
                             {"role": "assistant", "content": "done"}])
    orig, agent.chat = agent.chat, chat
    try:
        trace = []
        answer, calls = agent.ask_tools("what goes with 85123A?", trace)
    finally:
        agent.chat = orig
    assert answer == "done" and [c["tool"] for c in calls] == ["rules_for", "no_such_tool"]
    assert trace[0]["output"] == agent.rules_for("85123A") and "error" in trace[1]["output"]
    assert seen[1] == ["system", "user", "assistant", "tool", "tool"]  # both tool results sent back


def _get(base, path):
    try:
        with urllib.request.urlopen(base + path) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def _post(base, path, body):
    req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_http_endpoints():
    srv = api.serve(port=0, quiet=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        s, h = _get(base, "/api/health")
        y1, season = agent.tables()
        assert s == 200 and h["n_rules_y1"] == len(y1) and h["n_rules_season"] == len(season)

        s, r = _get(base, "/api/rules_for?product=85123A")
        assert s == 200 and r == json.loads(json.dumps(agent.rules_for("85123A")))
        s, r = _get(base, "/api/top_rules?min_confidence=0.8&limit=3")
        assert s == 200 and len(r["rules"]) <= 3 and all(x["confidence"] >= 0.8 for x in r["rules"])
        s, r = _get(base, "/api/season_filter?period=summer")
        assert s == 200 and r["n_rules"] == 0

        assert _get(base, "/api/rules_for")[0] == 400
        assert _get(base, "/api/top_rules?limit=abc")[0] == 400
        assert _get(base, "/api/top_rules?min_support=nan")[0] == 400
        assert agent.season_filter("2011년 여름 성수기")["n_rules"] == 0
        assert agent.rules_for("")["n_rules"] == 0
        assert _get(base, "/api/nothing")[0] == 404
        assert _post(base, "/api/ask", {"question": ""})[0] == 400
        assert _post(base, "/api/ask", {"question": "x", "method": "gpt"})[0] == 400

        s, r = _post(base, "/api/ask", {"question": "What goes with 85123A?", "method": "router"})
        assert s == 200 and r["tool_calls"][0]["tool"] == "rules_for" and r["check"]["verdict"] == "ok"
        s, r = _post(base, "/api/ask", {"question": "blue elephant?", "method": "router"})
        assert s == 200 and r["check"]["verdict"] == "refusal"

        with urllib.request.urlopen(base + "/") as page:
            assert b"Basket Insight Agent" in page.read()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
