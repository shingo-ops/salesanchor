# Phase 3 設計 — translation-double-lang-a1

**対象ADR**: ADR-110  
**recon**: docs/handoff/translation-double-lang-a1/recon.md  
**日付**: 2026-06-20  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 過去事例1: `backend/app/services/message_translator.py:477` の `translate_inbound_languages()` は、原文言語の判定結果を使って ja 先行 + 必要時 en 追加を 1 箇所に集約している。→ 我々への応用: Discord/手動の即時翻訳とバッチを同じルールに揃える。
- 過去事例2: `backend/app/tasks/translation.py:179` のバッチは、翻訳不足の受信メッセージを後追いで拾う安全網として機能する。→ 我々への応用: 即時翻訳が失敗しても 15 分バッチで ja/en を補完できる。
- 該当なし: 本増分は既存の翻訳基盤の拡張であり、外部導入事例の追加調査は設計判断に必須ではない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 英文 inbound で ja 翻訳のみが増え、en は原文扱いになる | `pytest backend/tests/test_message_translator.py -q --no-cov` |
| 非英語 inbound で ja/en の両方が保存される | `pytest backend/tests/test_message_translator.py -q --no-cov` |
| Discord 即時タスクが bilingual helper を使う | `pytest backend/tests/test_ticket_channel_translation.py -q --no-cov` |
| 手動 conv log も bilingual helper に揃う | `pytest backend/tests/test_conv_logs_router.py -q --no-cov` |
| pending 判定が ja/en の不足を拾う | `pytest backend/tests/test_translation_monitor.py -q --no-cov` |
| migration が不要である | `migrations/094_create_message_translations.sql:25-32` の UNIQUE 制約を確認 |

---

## 技術 How・KPI

- KPI: 新規 inbound で ja/en の必要行が数秒以内に揃う。
- 技術選択: `translate_inbound_languages()` を共通化し、Discord 即時・手動・バッチを同一の埋め方にする。

---

## 弊害・トレードオフ

- 原文が日本語でも ja 翻訳行を生成するため、ja 表示は原文採用に比べて冗長になる。→ 表示層で原文を優先する。
- en 再翻訳が増えるため、Gemini 呼び出し数は増加する。→ キャッシュ `(message_id, target_language)` で重複を抑える。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | bilingual helper を追加 | Generator |
| 2 | Discord 即時 / manual / batch を同一 helper に寄せる | Generator |
| 3 | helper と pending 判定のテストを追加 | Generator |

---

## 継続

- 完了後の監視: 15分バッチで ja/en 欠損が補完されることを確認。
- 次フェーズへの引き継ぎ: 表示切替（原文 or 翻訳行の選択）を別増分で実装する。
