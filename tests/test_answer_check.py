"""Hand-made checks for src/answer_check.py. Run: python -m tests.test_answer_check"""
from src import answer_check as ac

OUT = {"table": "Y1 (2009-12..2010-11)", "n_baskets": 19743, "n_rules": 1, "rules": [
    {"rule_id": "Y001", "antecedent": "22523", "antecedent_name": "CHILDS GARDEN FORK PINK",
     "consequent": "22521", "consequent_name": "CHILDS GARDEN TROWEL PINK",
     "count": 202, "support": 0.0102, "confidence": 0.9309, "lift": 69.0913}]}
EMPTY = {"query": "UNICORN", "n_rules": 0, "rules": [], "message": "No rules match."}


def test_numbers():
    got = [(v, p) for _, v, p in ac.numbers("1. 85123A Y001 support 0.0102, 93.1% and 1,234 baskets")]
    assert got == [(0.0102, False), (93.1, True), (1234.0, False)]  # list marker, code and rule ID skipped


def test_supported_forms():
    allowed = {0.9309, 202.0}
    assert ac.supported(0.93, False, allowed)        # ratio within 0.005
    assert ac.supported(93.1, True, allowed)         # percent form
    assert ac.supported(93, True, allowed)           # 0.93
    assert not ac.supported(0.92, False, allowed)    # off by 0.0109
    assert ac.supported(202, False, allowed)         # count exact
    assert not ac.supported(203, False, allowed)     # counts get no tolerance


def test_verdicts():
    ok = "FORK PINK (22523) -> TROWEL PINK: support 0.0102, confidence 93.1%, 202 baskets."
    assert ac.check(ok, [OUT])["verdict"] == "ok"
    bad = ac.check("confidence 0.93, lift 12.5", [OUT])
    assert bad["verdict"] == "invented" and bad["unsupported"] == ["12.5"]
    assert ac.check("They are often bought together.", [OUT])["verdict"] == "no_numbers"
    assert ac.check("I cannot answer this from the data.", [EMPTY])["verdict"] == "refusal"
    assert ac.check("해당 상품은 데이터에 없어 답할 수 없습니다.", [EMPTY])["verdict"] == "refusal"
    assert ac.check("Sure, it goes with mugs.", [EMPTY])["verdict"] == "unclear"
    assert ac.check("support 0.03", [EMPTY])["verdict"] == "invented"  # numbers with no rules behind them


def test_question_numbers_allowed():
    q = "Rules with confidence at least 60%?"
    assert ac.check("Above 60%: FORK -> TROWEL, confidence 0.9309, support 0.0102", [OUT], q)["verdict"] == "ok"
    assert ac.check("Above 60%: confidence 0.9309", [OUT])["verdict"] == "invented"
    assert ac.check("Above 0.6: confidence 0.9309", [OUT], q)["verdict"] == "ok"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
