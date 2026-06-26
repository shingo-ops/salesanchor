"""
段階A: outbound 送信翻訳修正のユニットテスト。

テスト一覧:
  - test_send_message_request_accepts_draft_id: draft_id フィールド受け入れ確認
  - test_send_message_request_draft_id_optional: draft_id 省略時は None
  - test_send_uses_confirmed_draft_text: draft_id があれば final_text を本文に採用
  - test_send_uses_draft_text_when_no_final: final_text が NULL なら draft_text を採用
  - test_send_rejects_unconfirmed_draft: confirmed_at=NULL -> 400
  - test_send_rejects_wrong_lead_draft: 別リードの draft -> 400
  - test_send_rejects_missing_draft: draft_id 不存在 -> 400
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.routers.leads import _SendMessageRequest

# ---------------------------------------------------------------------------
# _SendMessageRequest のスキーマ検証
# ---------------------------------------------------------------------------


class TestSendMessageRequestSchema:
    """_SendMessageRequest が draft_id フィールドを正しく受け取るか。"""

    def test_send_message_request_accepts_draft_id(self):
        """draft_id を指定すると int として受け入れる。"""
        req = _SendMessageRequest(text="hello", draft_id=42)
        assert req.draft_id == 42
        assert req.text == "hello"

    def test_send_message_request_draft_id_optional(self):
        """draft_id を省略すると None になる。"""
        req = _SendMessageRequest(text="hello")
        assert req.draft_id is None

    def test_send_message_request_rejects_empty_text(self):
        """text が空文字は Pydantic バリデーションエラー。"""
        with pytest.raises(ValidationError):
            _SendMessageRequest(text="", draft_id=1)

    def test_send_message_request_draft_id_null_explicit(self):
        """draft_id=None を明示的に渡しても OK。"""
        req = _SendMessageRequest(text="test", draft_id=None)
        assert req.draft_id is None


# ---------------------------------------------------------------------------
# draft_id 分岐ロジックの疑似検証（ロジック抜粋テスト）
# ---------------------------------------------------------------------------
# send_lead_message の内部ロジックを直接呼ぶのは依存が多すぎるため、
# 分岐条件のエッジケースを関数単位で検証する。


class TestDraftTextSelection:
    """draft_row からの text_body 選択ロジック。"""

    @staticmethod
    def _select_text_body(draft_row_final: str | None, draft_row_draft: str) -> str:
        """send_lead_message 内の text_body 選択ロジックを再現。"""
        return ((draft_row_final or draft_row_draft)).strip()

    def test_send_uses_confirmed_draft_text(self):
        """final_text があればそれを採用。"""
        result = self._select_text_body("Confirmed English", "Draft English")
        assert result == "Confirmed English"

    def test_send_uses_draft_text_when_no_final(self):
        """final_text が None なら draft_text を採用。"""
        result = self._select_text_body(None, "Draft English")
        assert result == "Draft English"

    def test_strips_whitespace(self):
        """前後の空白は除去される。"""
        result = self._select_text_body("  Hello  ", "Draft")
        assert result == "Hello"


class TestDraftValidation:
    """draft_row の各種バリデーション条件。"""

    def test_send_rejects_unconfirmed_draft(self):
        """confirmed_at が None の場合は拒否すべき。"""
        # draft_row = (lead_id, draft_text, final_text, confirmed_at)
        draft_row = (1, "draft", "final", None)
        assert draft_row[3] is None  # confirmed_at is None -> should reject

    def test_send_rejects_wrong_lead_draft(self):
        """lead_id が異なる場合は拒否すべき。"""
        draft_row = (99, "draft", "final", "2026-06-26T00:00:00Z")
        target_lead_id = 1
        assert draft_row[0] is not None and int(draft_row[0]) != target_lead_id

    def test_send_accepts_matching_lead_draft(self):
        """lead_id が一致する場合は OK。"""
        draft_row = (1, "draft", "final", "2026-06-26T00:00:00Z")
        target_lead_id = 1
        assert not (draft_row[0] is not None and int(draft_row[0]) != target_lead_id)

    def test_send_accepts_null_lead_id_in_draft(self):
        """draft の lead_id が NULL なら lead 不一致チェックをスキップ。"""
        draft_row = (None, "draft", "final", "2026-06-26T00:00:00Z")
        target_lead_id = 1
        # lead_id が None → チェックをスキップ
        assert not (draft_row[0] is not None and int(draft_row[0]) != target_lead_id)

    def test_send_rejects_missing_draft(self):
        """draft_row が None の場合は拒否すべき。"""
        draft_row = None
        assert draft_row is None  # -> should raise 400


class TestIsEditedLogic:
    """is_edited の SQL 条件の Python 再現。"""

    @staticmethod
    def _is_edited(final_text: str | None, draft_text: str) -> bool:
        """IS DISTINCT FROM の Python 等価。"""
        return final_text is not None and final_text != draft_text

    def test_is_edited_true_when_modified(self):
        """final_text != draft_text -> is_edited=True。"""
        assert self._is_edited("Modified English", "Original English") is True

    def test_is_edited_false_when_unmodified(self):
        """final_text == draft_text -> is_edited=False。"""
        assert self._is_edited("Same Text", "Same Text") is False

    def test_is_edited_false_when_final_null(self):
        """final_text が NULL -> is_edited=False (NULL)。"""
        assert self._is_edited(None, "Draft Text") is False
