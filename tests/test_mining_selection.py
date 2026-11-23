"""Offline H4 selection tests; no H3 questions or API calls."""
import json

from src.mining_job import MiningJob
from src.mining_selection import MiningSelector


def call(name, **args):
    return {"role": "assistant", "tool_calls": [{"id": "call", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}]}


def job(budget=10000000):
    return MiningJob([("a", "b"), ("a", "b"), ("a", "c"), ("b", "c")], 0.25, budget)


def test_solar_pilot_then_select():
    script = iter([call("pilot", setting="apriori"), call("choose", setting="apriori", reason="fits")])
    selector = MiningSelector(job(), chat=lambda messages, tools: next(script))
    assert selector.select() == "apriori"
    assert [x["event"] for x in selector.history] == ["profile", "pilot", "solar_choice", "selected"]
    assert selector.history[1]["scope"] == "sample"


def test_unavailable_choice_fallback_and_reselection():
    selector = MiningSelector(job(), chat=lambda messages, tools: call("choose", setting="invalid", reason="bad"))
    assert selector.select() == "apriori"
    assert selector.history[-1]["source"] == "rules_fallback"
    assert selector.reselect("apriori", "out of memory") == "pcy_small"
    try:
        selector.reselect("pcy_small", "again")
        assert False
    except ValueError:
        pass


def test_failed_api_uses_feasible_baseline():
    def failing(messages, tools):
        raise SystemExit("Solar API unreachable")
    selector = MiningSelector(job(), chat=failing)
    assert selector.select() == "apriori"
    assert any(x["event"] == "fallback" for x in selector.history)


def test_no_feasible_setting():
    selector = MiningSelector(job(1), strategy="rules")
    try:
        selector.select()
        assert False
    except ValueError:
        assert selector.history[-1]["event"] == "failed"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
