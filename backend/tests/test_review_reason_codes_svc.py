"""理由コード表サービスの純関数（DB なし）。DB を使う検査は test_tcg_condition_review.py。"""
from app.services.review_reason_codes_svc import build_review_reason_details, non_ackable_codes, split_reason_codes

TABLE = {"pid_unresolved": ("system", "analysis"), "gemini_unsure": ("gemini", "extraction")}


def test_split_reason_codes_trims_drops_empty_and_dedupes_in_order():
    assert split_reason_codes(" b, a ,b,,a, c ") == ["b", "a", "c"]


def test_split_reason_codes_empty_inputs_give_empty_list():
    assert split_reason_codes("") == [] and split_reason_codes(None) == [] and split_reason_codes(" , ") == []


def test_build_details_known_and_unknown_codes():
    assert build_review_reason_details("pid_unresolved,zzz", TABLE) == [
        {"code": "pid_unresolved", "source": "system", "fix_stage": "analysis", "ackable": True},
        {"code": "zzz", "source": None, "fix_stage": None, "ackable": True},
    ]


def test_build_details_marks_condition_unknown_as_not_ackable():
    details = build_review_reason_details("condition_unknown,pid_unresolved", TABLE)
    assert [(d["code"], d["ackable"]) for d in details] == [("condition_unknown", False), ("pid_unresolved", True)]


def test_non_ackable_codes_returns_only_the_refused_ones_in_order():
    assert non_ackable_codes(["pid_unresolved", "condition_unknown", "condition_unknown"]) == ["condition_unknown"]
    assert non_ackable_codes(["pid_unresolved"]) == []


def test_build_details_empty_reason_gives_empty_list():
    assert build_review_reason_details("", TABLE) == []
