# 提供終了モデルによる翻訳・在庫解析の失敗 recon（2026-09-07）

対象: 本番（tenant_004 を含む全テナント共通の LLM 呼び出し）。調査は読み取りのみ。

## 1. 症状

Celery worker のログに、翻訳処理が 404 で失敗し続ける記録が多数ある。
エラー文は models/gemini-2.5-flash が新規利用者に提供終了であり
models/gemini-3.6-flash を使うよう促す内容。翻訳は成立していない。

## 2. 確定した事実

- 翻訳の既定モデルは環境変数で上書き可能だが、本番の celery worker と backend の
  どちらにも TRANSLATION_MODEL_RECEIVE / TRANSLATION_MODEL_SEND は設定されていない
  （2026-09-07 実測。printenv の出力が 0 件）。よってコードの既定値が使われている。
- 既定値は `backend/app/services/message_translator.py:40` が gemini-2.5-flash、
  `backend/app/services/message_translator.py:41` が gemini-2.5-flash-lite。
- 在庫解析も同じ系のモデルを直書きしている:
  `backend/app/services/inventory_parser_llm.py:89` と
  `backend/app/services/inventory_parser_llm.py:225`。
- 価格表は `backend/app/services/llm_budget.py:53` の LLM_PRICING に 2.5 系 3 件のみ。
  未知のモデル名を渡すと `backend/app/services/llm_budget.py:130` で ValueError を送出する。
  よってモデル名だけ変えるとコスト記録が落ちる。
- TCG 抽出は別系統で `backend/app/services/gemini_extraction_svc.py:126` が
  gemini-3.6-flash を指定しており、こちらは動作している。
- 本番の API キーで利用可能なモデル一覧を実測し、gemini-3.5-flash-lite が
  利用可能であることを確認した（2026-09-07）。
- 正本 `docs/adr/ADR-110-sa-translation-subsystem.md:139` の表も 2.5 系のまま。

## 3. 決定事項（PO 合意、2026-09-07）

- 翻訳・在庫解析とも gemini-3.5-flash-lite を使う。
- 対応は 2 段に分ける。第 1 段は本件（404 の止血）。
  第 2 段はモデル名の SSOT 化（用途とモデルと価格を 1 箇所に集約する）。

## 4. 未確認・要実測

- gemini-3.5-flash-lite の料金は公開情報の参照値であり、請求実績で裏を取っていない。
- 送信英訳に Flash-Lite を使うことによる訳質の変化。
- TCG 抽出（gemini-3.6-flash）を将来どう扱うか。
