# design.md — 便B: 翻訳モデル切替（送信側 flash-lite）

## 参照

- recon: `docs/handoff/translation-model-flashlite/recon.md`
- ADR-110: `docs/adr/ADR-110-sa-translation-subsystem.md`（翻訳サブシステム設計）

## 目的

送信英訳モデル（`MODEL_SEND`）を `gemini-2.5-pro` → `gemini-2.5-flash-lite` へ切り替え、
LLM コストを削減する。翻訳品質は実機確認（基準 B2）で担保。

## 変更内容

### 変更1: `backend/app/services/message_translator.py:41`

```python
# 変更前
MODEL_SEND: str = os.getenv("TRANSLATION_MODEL_SEND", "gemini-2.5-pro")

# 変更後
MODEL_SEND: str = os.getenv("TRANSLATION_MODEL_SEND", "gemini-2.5-flash-lite")
```

- `MODEL_RECEIVE`（受信側）は変更なし（`gemini-2.5-flash` のまま）。
- 環境変数 `TRANSLATION_MODEL_SEND` で本番切り戻し可能（コード変更不要）。

### 変更2: `backend/app/services/llm_budget.py` — LLM_PRICING に flash-lite 追加

```python
"gemini-2.5-flash-lite": {
    # $0.10 / 1M input tokens
    "input_per_token": Decimal("0.10") / Decimal("1000000"),
    # $0.40 / 1M output tokens
    "output_per_token": Decimal("0.40") / Decimal("1000000"),
},
```

既存行との単位比較（同一スケール確認）:

| モデル | input_per_token（式） | output_per_token（式） |
|---|---|---|
| gemini-2.5-flash | `Decimal("0.075") / Decimal("1000000")` | `Decimal("0.30") / Decimal("1000000")` |
| gemini-2.5-pro | `Decimal("1.25") / Decimal("1000000")` | `Decimal("10.00") / Decimal("1000000")` |
| **gemini-2.5-flash-lite** | `Decimal("0.10") / Decimal("1000000")` | `Decimal("0.40") / Decimal("1000000")` |

すべて「1トークンあたりの USD コスト = 公式単価(USD/1M) ÷ 1,000,000」で統一。

## 弊害・リスク

| リスク | 対策 |
|---|---|
| flash-lite の翻訳品質が pro より低い可能性 | 基準 B2 で実機確認必須。品質不足なら env var で pro に切り戻し |
| エスカレート先（受信低確信度時）も flash-lite になる | 受信エスカレートは `MODEL_SEND` を参照（:540）。flash-lite で問題なら env var 調整 |
| `record_cost` が flash-lite 未登録でエラー | LLM_PRICING への追加（変更2）で対応済み |

## 外部・過去事例の参照と我々への応用

Gemini 2.5 Flash-Lite は Google DeepMind が 2025 年に公開した最軽量・低コストモデル。
定型文・短文英訳には実用上問題のない品質を持つとされる（公式ドキュメント基準）。
短い B2B メッセージ翻訳用途では採用事例あり。

## 検証基準

| 基準 | 検証方法 |
|---|---|
| B1 プレビューのモデル表示が flash-lite | 実機: 送信プレビューの `outbound_translation_drafts.model` 確認 |
| B2 英訳が実用品質（短い定型文で意味が通る） | 実機: 数件送って英訳を目視確認 |
| B3 英訳送信(K1-K4)・受信翻訳が従来どおり | 実機: 各経路が動作することを確認 |

## migration

不要（コード変更のみ）。
