"""Input-validation checks for the agent tools (change request '선택', post-merge guards).

    python -m tests.test_agent_tools

Covers the guards added with the goeun merge: rules_for rejects an empty query, and
top_rules clamps limit into 1..500 instead of trusting the caller's number.
"""
from src import agent


def test_rules_for_empty_query_returns_no_rules():
    res = agent.rules_for("")
    assert len(res["rules"]) == 0


def test_top_rules_limit_is_clamped():
    one = agent.top_rules(limit=0)
    three = agent.top_rules(limit=3)
    many = agent.top_rules(limit=10 ** 9)
    assert len(one["rules"]) == 1          # limit 0 clamps up to 1
    assert len(three["rules"]) == 3
    assert len(many["rules"]) <= 500       # huge limit clamps down to 500
    assert one["n_matching"] == many["n_matching"]  # clamp never changes the match count


def test_season_filter_reads_years_with_a_suffix():
    # a year outside the data must give no rules, also when it is written with 년 or next to a peak year
    for period, expected in {"2011년 크리스마스": False, "2010년 크리스마스": True, "christmas 2010 and 2011": False,
                             "Christmas 2010": True, "december 2010": False, "2009-12": True}.items():
        assert bool(agent.season_filter(period)["rules"]) == expected, period


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
