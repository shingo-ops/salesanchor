# design: 受信二言語化 第1便（言語先判定オーケストレータ）

**対象ADR**: ADR-110  
**recon**: docs/handoff/discord-ticket-lang-refactor/recon.md  
**日付**: 2026-06-21  
**担当**: Generator

---

## 1. 目的

受信メッセージの翻訳対象を翻訳前に自前判定し、必要な target だけを生成する。
即時 / batch / 監視で同じ判定を使い、`original_language` の保存値も安定させる。

---

## 2. 変更内容

1. `backend/app/services/message_translator.py` に `detect_inbound_language()` / `get_required_inbound_targets()` / `ensure_inbound_translations()` を追加する。
2. `backend/app/services/message_translator.py` の `translate_inbound()` に `original_language_override` を追加し、kana 系の保存値を固定できるようにする。
3. `backend/app/tasks/translation.py` の即時タスクと batch を同じ target 判定へ寄せる。
4. `backend/app/services/translation_monitor.py` の pending 判定を同じルールへ合わせる。
5. `backend/app/routers/conv_logs.py` の手動翻訳経路も同じ helper を使う。

---

## 3. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| kana-only 受信は `en` のみを作る | `backend/tests/test_message_translator.py:333-360` が通る |
| mixed 受信は `ja` と `en` を両方作る | `backend/tests/test_message_translator.py:363-400` が通る |
| kana なしで original が `en` なら `ja` のみで止まる | `backend/tests/test_message_translator.py:403-429` が通る |
| kana なしで original が `en` 以外なら `ja + en` を作る | `backend/tests/test_message_translator.py:431-465` が通る |
| 即時タスクが `ensure_inbound_translations()` を通す | `backend/tests/test_ticket_channel_translation.py:81-112` が通る |
| batch が不足分のみ補完する | `backend/tests/test_ticket_channel_translation.py:196-231` が通る |
| pending 判定が新ルールに追従する | `backend/tests/test_translation_monitor.py:115-141` が通る |
| `original_language` の保存上書きが可能 | `backend/tests/test_message_translator.py:287-329` が通る |

---

## 4. 外部・過去事例の参照と我々への応用

該当なし。

今回の変更は、外部実装の追随ではなく、既存の翻訳保存・即時 enqueue・batch 補完・監視の各経路を同一の target 判定に統一する内部整理が主眼である。
