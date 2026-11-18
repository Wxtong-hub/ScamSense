import pytest
from app.services.training import analyze, is_sensitive, make_report


def turn(text, role="wang", presented=True):
    facts = analyze(role, text, "S0")
    return {
        **facts,
        "text": text,
        "role_id": role,
        "presented": presented,
        "message_id": "u1",
        "reply_id": "r1",
    }


@pytest.mark.parametrize(
    "sample",
    [
        "Test.User@example.invalid",
        "138 0000 0000",
        "1234-5678-9012-3456",
        "我住在某某路十二号",
    ],
)
def test_private_samples(sample):
    assert is_sensitive(sample)


def test_discussion_of_documents_is_allowed():
    assert not is_sensitive("为什么这个岗位需要身份证？我不愿提供真实信息。")


def test_no_turn_count_progression_or_implicit_termination():
    phase = "S0"
    for _ in range(5):
        phase = analyze("lin", "你好", phase)["next_phase"]
    assert phase == "S0"
    assert analyze("wang", "你亲自核实过吗？", phase)["next_phase"] == "S4"
    assert analyze("lin", "我想拒绝", "S4")["next_phase"] == "S4"


def test_disclosure_is_not_recognition_or_presentation():
    t = turn("你亲自核实过吗？", presented=False)
    assert t["disclosed"] == ["source"] and not t["recognized"]
    assert make_report([t], None)["dimensions"][0]["score"] is None
    t["presented"] = True
    assert make_report([t], None)["dimensions"][0]["score"] == 0


def test_unobserved_dimensions_do_not_get_invented_scores():
    r = make_report([], None)
    assert r["total"] is None and all(d["score"] is None for d in r["dimensions"])
    assert sum(d["weight"] for d in r["dimensions"]) == 100


def test_actual_evidence_survives_and_repeats_dont_inflate_score():
    q = turn("你是否亲自核实过消息来源？")
    claim = turn("群里只是转述，不能证明招聘主体已经授权。")
    d = {"choice": "verify_more", "reason": "消息来源和授权都需要核对。"}
    r = make_report([q, claim], d)
    again = make_report([q, q, claim], d)
    assert isinstance(r["total"], int) and r["total"] == again["total"]
    assert r["dimensions"][0]["evidence"][0]["excerpt"] == claim["text"]
    assert r["dimensions"][3]["score"] == 100
    assert make_report([q], d)["total"] < r["total"]
