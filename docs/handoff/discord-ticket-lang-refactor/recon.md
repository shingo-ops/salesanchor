# recon: 受信二言語化 第1便（言語先判定オーケストレータ）

**仕事名**: discord-ticket-lang-refactor
**調査日**: 2026-06-21
**対象ADR**: ADR-110
**目的**: 受信翻訳の必要 target 判定を自前化し、即時 / batch / 監視で同一ルールを使う根拠を残す

---

## 1. 事実

| 観点 | file:line | 事実 |
|---|---|---|
| 受信シグナル判定 | `backend/app/services/message_translator.py:114-139` | `detect_inbound_language()` が `has_kana` / `has_latin_word` を返し、`get_required_inbound_targets()` が必要 target を決める |
| 必要 target の補完 | `backend/app/services/message_translator.py:549-619` | `ensure_inbound_translations()` が kana-only / mixed / fallback の 3 分岐で `translate_inbound()` を呼ぶ |
| original_language の上書き | `backend/app/services/message_translator.py:449-545` | `translate_inbound()` は `original_language_override` を受け取り、保存前の `original_language` を固定できる |
| 即時タスクの入口 | `backend/app/tasks/translation.py:23-115` | `_run_translate_inbound_message()` が `ensure_inbound_translations()` を呼び、保存後に SSE を publish する |
| batch の入口 | `backend/app/tasks/translation.py:118-215` | `translate_pending_messages()` が `get_required_inbound_targets()` と既存 target を見て不足分のみ補完する |
| 監視の pending 判定 | `backend/app/services/translation_monitor.py:44-119` | `check_translation_health()` が同じ target 判定で failed/pending を数える |
| 手動 conv_logs | `backend/app/routers/conv_logs.py:128-173` | `_fire_translation()` が `ensure_inbound_translations()` を使って `conversation_logs` に書き戻す |
| kana / mixed / fallback の分岐テスト | `backend/tests/test_message_translator.py:107-465` | 言語判定、override、kana-only / mixed / non-kana の target 分岐を固定している |
| 即時 enqueue と batch 補完のテスト | `backend/tests/test_ticket_channel_translation.py:81-231` | Discord ticket の即時 enqueue と batch 補完の期待値を確認している |
| 監視ロジックのテスト | `backend/tests/test_translation_monitor.py:115-141` | pending の数え方が新ルールに追従している |

---

## 2. 結論

- 受信翻訳の single source of truth は `get_required_inbound_targets()` に寄せられる。
- kana-only は `en` のみ、mixed は `ja + en`、kana なしは Gemini の `original_language` を見て必要分だけ翻訳する。
- 同一言語への無駄な翻訳は避けられる。
- `original_language_override` により、少なくとも kana 系の原文言語は保存時に確実に `ja` として固定できる。
