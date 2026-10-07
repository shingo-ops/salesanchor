# design: prompt_ab の保存済み応答から後処理だけをやり直す道具

- 作成：2026-10-08 実装担当（カード：便2）。発行：Opus（設計）。
- PO 合意（原文）：「全て合意、1-6までを進めて完了させた後にどの用に変化するかを確認したい」
- recon：docs/handoff/prompt-ab-recompute/recon.md
- 関係する ADR：ADR-100、ADR-1004

## 1. 目的（KGI）
Gemini を呼ばずに、prompt_ab の JSONL の response_text から、今のコードで v102_items を作り直し、変化を確かめる。
本番 v6・試運転・prompt_ab の動きは変えない。

## 2. 変更
- 新規 backend/app/tools/prompt_ab_recompute.py（recompute / main）。
- 新規 backend/tests/test_prompt_ab_recompute.py。
- prompt_ab.py には足さない。理由：633 行あり、足すと 700 行台後半になり目安の 800 行に近づく。入口（CLI）も別なので、別ファイルが凝集度が高い。prompt_ab の関数（_v102_row_fields・_load_v10_masters・fetch_job_ids・load_extraction_context・_append_jsonl）は呼ぶだけで中身は変えない。

## 3. 動き
1. --from-jsonl の各行を読む。マスタは _load_v10_masters で1回だけ読み、必須の3つ（cond_entries・status_entries・unit_alias_to_info）のどれかが空ならエラーで止める。
2. 行ごとに run_id から job_id・原文・仕入元の文脈を読み（同じジョブは1回だけ）、_v102_row_fields を通して v102_items・v102_flags を作る。run_id・job_id・prompt_name・omitted_supplier_fields は元の行から写す。
3. 出力は <out-dir>/recompute-<入力ファイル名>.jsonl（実行のたびに作り直す）。
4. response_text が無い・空、JSON が壊れている、run が見つからない、取り出しの失敗（v102_items_error）はその行を error として記録し、次の行へ進む。最後に read・written・errors の件数を出し、errors があれば終了コード 1。
5. Gemini の関数・費用の台帳は呼ばない。DB は読むだけ。

## 4. 合格基準
|基準|検証方法|
|---|---|
|Gemini を呼ばない・台帳に書かない|テスト：Gemini と台帳のモックが呼ばれたら失敗する設定で、行を処理しても通る|
|同じ v102_items が出る|テスト：prompt_ab._v102_row_fields の結果と一致|
|response_text が無い行はエラーにして次へ|テスト：2行目の結果が出て、件数が read=2 written=1 errors=1|
|既存の prompt_ab は変わらない|tests/test_prompt_ab.py が全部通る・prompt_ab.py に差分なし|
|触るのは tools/ とテストのみ|git diff --name-only origin/main...HEAD|

## 5. 外部事例
特定のライブラリや外部事例の採用はない（既存関数の再利用のみ）。保存済みの出力から後処理だけを再計算する「リプレイ」方式は、LLM の評価で費用を抑える一般的なやり方。

## 6. 戻し方・測り方
- 戻し方：新規 2 ファイル（と docs）を消すだけ。他のコードに依存されない。
- 測り方：pytest の最終行 failed 0。
