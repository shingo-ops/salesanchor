# recon.md — 便B: 翻訳モデル切替（送信側 flash-lite）

base branch: origin/main @ 432831c6

## R-B1: モデル指定箇所

`backend/app/services/message_translator.py:40-41`

```python
MODEL_RECEIVE: str = os.getenv("TRANSLATION_MODEL_RECEIVE", "gemini-2.5-flash")
MODEL_SEND: str    = os.getenv("TRANSLATION_MODEL_SEND",    "gemini-2.5-pro")   # ← 変更対象
```

**結論**: モデルは環境変数で管理（コードはデフォルト値のみ）。
`TRANSLATION_MODEL_SEND` 環境変数が未設定の場合のデフォルトが `gemini-2.5-pro`。

ADR-110（`docs/adr/ADR-110-sa-translation-subsystem.md`）にて両変数が正式採用済み:

```
| `TRANSLATION_MODEL_RECEIVE` | `gemini-2.5-flash` | 受信和訳（安い）    |
| `TRANSLATION_MODEL_SEND`    | `gemini-2.5-pro`   | 送信英訳（最上位必須）|
```

## R-B2: 翻訳呼び出し本体

`backend/app/services/message_translator.py`

```
_call_gemini(prompt, model_name)   ← 単一の Gemini 呼び出し口（:391）

受信（inbound）:
  :517  model = MODEL_RECEIVE                    ← 安いモデルで初回
  :523  _call_gemini(prompt, model)
  :532  if confidence < threshold or is_long:    ← エスカレート条件
  :540    _call_gemini(prompt2, MODEL_SEND)       ← 高いモデルに格上げ

送信（outbound draft）:
  :665  model = MODEL_SEND                       ← 常に MODEL_SEND 固定
  :667  _call_gemini(prompt, model)
  :683  model=model → outbound_translation_drafts.model に記録される値
```

`outbound_translation_drafts.model` に保存される値 = `MODEL_SEND` 環境変数の値。

## R-B3: 触ってはいけない範囲の確認

| 区分 | 箇所 | 変更するか |
|---|---|---|
| **変更対象** | `message_translator.py:41` デフォルト値 | YES |
| **変更対象** | `llm_budget.py:60-67` LLM_PRICING テーブル | YES（flash-lite 行追加） |
| 触らない | `_call_gemini` / `translate_inbound` / `generate_outbound_draft` | NO |
| 触らない | `_build_inbound_prompt` / `_build_outbound_prompt` | NO |
| 触らない | `translation_glossary.py` | NO |
| 触らない | `MODEL_RECEIVE`（受信側） | NO |
| 触らない | `migrations/` / `scripts/` / `deploy.yml` | NO |

モデル指定を変えるだけ。翻訳ロジック・プロンプト・グロッサリへの手出しなし。
