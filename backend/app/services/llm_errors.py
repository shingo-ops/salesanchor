"""LLM 呼び出し共通エラー型。

2026-10-02: Discord 在庫取り込み機能（inventory_parser_llm.py）削除に伴い、
message_translator.py / leads.py / translation.py（router・task）が共通で使う
LLMConfigError / LLMParseError をこの独立モジュールへ移設した。
経緯: docs/handoff/remove-discord-inventory-parse/design.md
"""

from __future__ import annotations


class LLMParseError(Exception):
    """Gemini 呼び出し失敗、API キー欠落、JSON パース失敗等を表す。

    呼び出し側がこれを catch してフォールバック処理を行う。
    """


class LLMConfigError(LLMParseError):
    """GEMINI_API_KEY が未設定 / 空。"""


__all__ = [
    "LLMConfigError",
    "LLMParseError",
]
