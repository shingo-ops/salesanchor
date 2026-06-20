# recon — translation-double-lang-a1

**仕事名**: translation-double-lang-a1  
**日付**: 2026-06-20  
**対象ADR**: ADR-110  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/094_create_message_translations.sql:25` | `message_translations` が `UNIQUE(message_id, target_language)` で ja/en 別行を許容する |
| `backend/app/services/message_translator.py:477` | `translate_inbound_languages()` が ja を先に翻訳し、必要なら en も追加する |
| `backend/app/tasks/translation.py:79` | 即時タスクが `translate_inbound_languages()` を呼ぶ |
| `backend/app/tasks/translation.py:182` | バッチが ja/en 両方の未完了メッセージを拾う |
| `backend/app/routers/conv_logs.py:145` | 手動記録も `translate_inbound_languages()` を使う |
| `backend/app/services/translation_monitor.py:59` | pending 判定が ja/en 両方の有無を見る |
| `backend/tests/test_message_translator.py:267` | 英文原文では en 再翻訳を省くテスト |
| `backend/tests/test_message_translator.py:296` | 非英語原文では en 翻訳を追加するテスト |
| `backend/tests/test_ticket_channel_translation.py:131` | worker タスクが bilingual helper を使うテスト |
| `backend/tests/test_translation_monitor.py:99` | pending 判定が ja/en 前提であることを検証するテスト |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 既存の ja-only 表示ロジックが残っていないか | display 側の別PRで確認 | ✅ 解消済み |
| 2 | Meta 即時翻訳を A1 で触るべきか | A1 は Discord/手動に限定 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み / 該当なし

---

## 補足

- migration は不要。`message_translations` は `message_id + target_language` で共存できる。
- 本PRの実装は、既存の翻訳本体を再利用して ja/en の両方を埋める。
