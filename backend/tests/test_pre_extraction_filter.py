"""
事前フィルタ機能の単体テスト。

対象:
  - _match_rule: pattern_type 別マッチング
  - _apply_pre_extraction_filter: 2層フィルタロジック
  - _run_extraction: filtered ステータスが正しく返ること
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tasks.tcg_extraction import (
    _apply_pre_extraction_filter,
    _match_rule,
)


# ─────────────────────────────────────────────────────────────────────────────
# _match_rule
# ─────────────────────────────────────────────────────────────────────────────


class TestMatchRule:
    def test_exact_match(self):
        assert _match_rule("hello", "exact", "hello") is True

    def test_exact_no_match(self):
        assert _match_rule("hello", "exact", "hello world") is False

    def test_exact_strips_text(self):
        assert _match_rule("hello", "exact", "  hello  ") is True

    def test_substring_match(self):
        assert _match_rule("グループに参加しました", "substring", "田中さんがグループに参加しました") is True

    def test_substring_no_match(self):
        assert _match_rule("グループに参加しました", "substring", "普通のメッセージ") is False

    def test_prefix_match(self):
        assert _match_rule("アナウンス", "prefix", "アナウンスしました") is True

    def test_prefix_no_match(self):
        assert _match_rule("アナウンス", "prefix", "公式アナウンス") is False

    def test_regex_match(self):
        assert _match_rule(r"\d+人がグループに参加", "regex", "5人がグループに参加しました") is True

    def test_regex_no_match(self):
        assert _match_rule(r"\d+人がグループに参加", "regex", "グループに参加しました") is False

    def test_regex_invalid_pattern(self):
        # 不正な正規表現はマッチしない（例外は内部で握り潰す）
        assert _match_rule(r"[invalid", "regex", "テキスト") is False

    def test_unknown_pattern_type_returns_false(self):
        assert _match_rule("hello", "unknown_type", "hello") is False


# ─────────────────────────────────────────────────────────────────────────────
# _apply_pre_extraction_filter ヘルパー
# ─────────────────────────────────────────────────────────────────────────────


def _make_filter_session(rules: list[tuple]) -> MagicMock:
    """
    knowledge_rules クエリ結果をスタブするセッションモックを作る。

    rules: list of (category, pattern_type, pattern)
    """
    mock_rows = []
    for category, pattern_type, pattern in rules:
        row = MagicMock()
        row.__getitem__ = lambda self, idx, c=category, pt=pattern_type, p=pattern: (
            c if idx == 0 else pt if idx == 1 else p
        )
        mock_rows.append(row)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows

    mock_session = MagicMock()
    mock_session.execute.return_value = mock_result
    return mock_session


class TestApplyPreExtractionFilter:
    def test_message_exclude_matches_unconditionally(self):
        """message_exclude はマッチしたら数字の有無に関わらず除外。"""
        session = _make_filter_session([
            ("message_exclude", "substring", "グループに参加しました"),
        ])
        result = _apply_pre_extraction_filter(session, "田中さんがグループに参加しました")
        assert result is not None
        assert "message_exclude" in result

    def test_message_exclude_with_digit_still_filtered(self):
        """message_exclude は数字があっても除外する（即除外ルール）。"""
        session = _make_filter_session([
            ("message_exclude", "substring", "グループに参加しました"),
        ])
        result = _apply_pre_extraction_filter(session, "5人がグループに参加しました 100円")
        assert result is not None
        assert "message_exclude" in result

    def test_message_exclude_no_digit_filtered_when_no_digit(self):
        """message_exclude_no_digit はマッチ + 数字なし → 除外。"""
        session = _make_filter_session([
            ("message_exclude_no_digit", "substring", "個別"),
        ])
        result = _apply_pre_extraction_filter(session, "個別でご連絡ください")
        assert result is not None
        assert "message_exclude_no_digit" in result

    def test_message_exclude_no_digit_not_filtered_when_digit_present(self):
        """message_exclude_no_digit はマッチでも数字あり → Geminiに送る（フィルタしない）。"""
        session = _make_filter_session([
            ("message_exclude_no_digit", "substring", "個別"),
        ])
        result = _apply_pre_extraction_filter(session, "個別 BOX 2個 5000円")
        assert result is None

    def test_no_rules_returns_none(self):
        """knowledge_rules が空のとき全メッセージ Gemini に送る。"""
        session = _make_filter_session([])
        result = _apply_pre_extraction_filter(session, "普通のメッセージ")
        assert result is None

    def test_no_match_returns_none(self):
        """いずれのキーワードにもマッチしない → フィルタしない。"""
        session = _make_filter_session([
            ("message_exclude", "substring", "グループに参加しました"),
            ("message_exclude_no_digit", "substring", "個別"),
        ])
        result = _apply_pre_extraction_filter(session, "ポケモン BOX 5000円 3個")
        assert result is None

    def test_multiple_rules_first_match_wins(self):
        """複数ルールがある場合、最初にマッチしたルールが返る。"""
        session = _make_filter_session([
            ("message_exclude", "substring", "参加しました"),
            ("message_exclude", "substring", "退出しました"),
        ])
        result = _apply_pre_extraction_filter(session, "田中さんが退出しました")
        assert result is not None
        assert "message_exclude" in result


# ─────────────────────────────────────────────────────────────────────────────
# _run_extraction integration: filtered ステータス
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_schema_checks(monkeypatch):
    monkeypatch.setattr("app.tasks.tcg_extraction.work_schema_ready", lambda _: True)
    monkeypatch.setattr("app.tasks.tcg_extraction.schema_ready", lambda _: True)
    monkeypatch.setattr(
        "app.tasks.tcg_extraction.load_work_reference",
        lambda *_: {"works": [], "products": []},
    )


def _make_mock_session_with_filter(raw_text: str, filter_rows: list[tuple]) -> MagicMock:
    """
    _run_extraction 用セッションモック。

    最初の execute (pending job取得) は mock_row を返し、
    それ以降の execute (knowledge_rules取得等) は filter_rows を返す。
    """
    # pending job row
    main_row = MagicMock()
    main_row.__getitem__ = lambda self, idx: "test-ej-id" if idx == 0 else raw_text

    # knowledge_rules rows
    kr_rows = []
    for category, pattern_type, pattern in filter_rows:
        row = MagicMock()
        row.__getitem__ = lambda self, idx, c=category, pt=pattern_type, p=pattern: (
            c if idx == 0 else pt if idx == 1 else p
        )
        kr_rows.append(row)

    call_count = [0]

    def side_effect(query, *args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # 最初の execute = pending job クエリ
            result.fetchone.return_value = main_row
        else:
            # 2回目以降 = knowledge_rules クエリ / その他
            result.fetchone.return_value = None
            result.fetchall.return_value = kr_rows
        return result

    mock_session = MagicMock()
    mock_session.execute.side_effect = side_effect
    return mock_session


def test_run_extraction_returns_filtered_when_pre_filter_matches(monkeypatch):
    """message_exclude ルールにマッチしたとき status='filtered' を返す。"""
    raw_text = "田中さんがグループに参加しました"
    mock_session = _make_mock_session_with_filter(
        raw_text,
        [("message_exclude", "substring", "グループに参加しました")],
    )

    extract_called = []

    def mock_extract(*args, **kwargs):
        extract_called.append(True)
        return {"status": "done", "items": [], "prompt_version": "v1", "error_message": None}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract):
        from app.tasks.tcg_extraction import _run_extraction
        result = _run_extraction(mock_session, "test-sm-id")

    assert result["status"] == "filtered"
    assert result["items_count"] == 0
    assert result["error_message"] is None
    assert extract_called == [], "フィルタ除外時は Gemini を呼ばない"


def test_run_extraction_sends_to_gemini_when_no_filter_match(monkeypatch):
    """フィルタにマッチしない場合は Gemini に送る。"""
    raw_text = "ポケモン BOX 5000円 3個"
    mock_session = _make_mock_session_with_filter(
        raw_text,
        [("message_exclude_no_digit", "substring", "個別")],
    )

    recorder = MagicMock()
    recorder.prepare_items.return_value = []
    monkeypatch.setattr("app.tasks.tcg_extraction.AttemptRecorder", lambda *a: recorder)

    extract_called = []

    def mock_extract(*args, **kwargs):
        extract_called.append(True)
        return {"status": "empty", "items": [], "prompt_version": "v1", "error_message": None}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract):
        from app.tasks.tcg_extraction import _run_extraction
        _run_extraction(mock_session, "test-sm-id")

    assert len(extract_called) == 1, "フィルタにマッチしない場合は Gemini を呼ぶ"


def test_run_extraction_no_digit_condition(monkeypatch):
    """message_exclude_no_digit は数字ありなら Gemini に送る。"""
    raw_text = "個別でご連絡ください 100円"
    mock_session = _make_mock_session_with_filter(
        raw_text,
        [("message_exclude_no_digit", "substring", "個別")],
    )

    recorder = MagicMock()
    recorder.prepare_items.return_value = []
    monkeypatch.setattr("app.tasks.tcg_extraction.AttemptRecorder", lambda *a: recorder)

    extract_called = []

    def mock_extract(*args, **kwargs):
        extract_called.append(True)
        return {"status": "empty", "items": [], "prompt_version": "v1", "error_message": None}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract):
        from app.tasks.tcg_extraction import _run_extraction
        _run_extraction(mock_session, "test-sm-id")

    assert len(extract_called) == 1, "数字あり = Gemini に送る"


def test_run_extraction_no_digit_no_digit_filtered(monkeypatch):
    """message_exclude_no_digit は数字なしならフィルタ。"""
    raw_text = "個別でご連絡ください"
    mock_session = _make_mock_session_with_filter(
        raw_text,
        [("message_exclude_no_digit", "substring", "個別")],
    )

    extract_called = []

    def mock_extract(*args, **kwargs):
        extract_called.append(True)
        return {"status": "done", "items": [], "prompt_version": "v1", "error_message": None}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract):
        from app.tasks.tcg_extraction import _run_extraction
        result = _run_extraction(mock_session, "test-sm-id")

    assert result["status"] == "filtered"
    assert extract_called == []


def test_run_extraction_empty_rules_all_pass_to_gemini(monkeypatch):
    """knowledge_rules が空のとき全メッセージ Gemini に送る（既存動作）。"""
    raw_text = "ポケモン BOX 5000円 3個"
    mock_session = _make_mock_session_with_filter(raw_text, [])

    recorder = MagicMock()
    recorder.prepare_items.return_value = []
    monkeypatch.setattr("app.tasks.tcg_extraction.AttemptRecorder", lambda *a: recorder)

    extract_called = []

    def mock_extract(*args, **kwargs):
        extract_called.append(True)
        return {"status": "empty", "items": [], "prompt_version": "v1", "error_message": None}

    with patch("app.tasks.tcg_extraction.extract_message", mock_extract):
        from app.tasks.tcg_extraction import _run_extraction
        _run_extraction(mock_session, "test-sm-id")

    assert len(extract_called) == 1, "ルールなし = Gemini に送る"
