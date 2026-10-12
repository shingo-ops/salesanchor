# design: v102 の Gemini の思考要約を保存する

- 状態: 設計案（Opus 作成・自己審査済み。独立した第二者レビューではない）
- PO の指示（原文 2026-10-12）:「思考要約は、本番では保存されていません。プログラムが受け取った後に捨てています（line_analysis_v102_svc.py →捨てない仕組みにしてくれ」
- 現在地: [recon.md](recon.md)（docs/handoff/v102-thought-save/recon.md）
- 対象ADR: ADR-1004（思考はトークン数で記録済み）、ADR-1007（migration は構造だけ）、ADR-135・ADR-136（migration は PO の「GO #番号」）

## 1. 目的
- 本番の書き写しで、Gemini が「なぜその行を件に入れた・外したか」を、後から原文で確かめられるようにする。
- 指示書の直し（見出しの行を外す問題）の効果を、本番の思考で確かめる材料にする。

## 2. 対象と対象外
- 対象：v102 の本番の書き写し（`run_v102_extraction`）の、Gemini の呼び出し1回ごとの思考要約。
- 対象外：
  - 解析・要確認・配信・画面
  - v6 の経路
  - 試験の道具（すでにファイルに保存している）
  - 過去の試行（思考は残っていないので埋められない）

## 3. 置き場（SSOT）
- `public.extraction_attempts` に列 `thought_summaries JSONB`（文字列の配列）を1つ足す。
- 応答（response_text）と同じ試行の行に置くことで、「1回の呼び出しの記録は1行」を保つ。新しい表は作らない。
- 大きさ：thoughts_tokens は最大 12,139（recon §4）。既存の上限 `MAX_BYTES`（8MiB）を超えるときは NULL にする（input_payload と同じ扱い）。

## 4. 変更（PR を2つに分ける：コンテナの入れ替えが migration より先のため。段1 #4150/#4151 と同じ）
- PR①（migration だけ）：`migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql`
  ```sql
  ALTER TABLE public.extraction_attempts ADD COLUMN IF NOT EXISTS thought_summaries JSONB;
  COMMENT ON COLUMN ...;
  ```
  あわせて、`scripts/run_all_migrations.sh` に登録する。
- PR②（コードだけ。PR① の本番反映の後にマージ）：
  - `backend/app/services/tcg_extraction_record_svc.py` の `on_response(response, thought_summaries=None)`。同じ UPDATE で `thought_summaries = CAST(:thoughts AS jsonb)` を書く。None のとき・8MiB を超えるときは NULL。引数なしの既存の呼び出しは、今と同じ動き。
  - `backend/app/services/line_analysis_v102_svc.py` の `run_v102_extraction` で、`result.get("thought_summaries")` を渡す。
  - 試験：書く・NULL・大きすぎ・引数なし。PG の fixture に PR① の migration を当てる。

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. 本番に列がある（jsonb・既存行は NULL） | information_schema の読み取り |
| 2. 反映後の v102 の試行で thought_summaries が NULL でない（配列・要素は文字列） | 本番の読み取り SQL（jsonb_typeof・jsonb_array_length） |
| 3. 書き写しの結果（extraction_items・status・response_text）は変わらない | CI の既存の試験と、反映後の新しい投稿の status=done |
| 4. CI 全緑（PG の試験を含む） | gh pr checks |

## 6. 危険と対処
- 表の肥大：思考は1回あたり最大でも数十KB で、8MiB を超えるものは NULL。1日の投稿は数十件。保存期間の処理の有無は未確認（recon §6）のため、反映後 7日の表の大きさを記録する。
- 社外秘：思考には原文の引用が入る。置き場は、原文（response_text）と同じ表・同じ見られる人（super admin の診断 API のみ）。
- 戻し方：PR② の revert（列は NULL のまま残す。DROP しない）。

## 7. 維持の仕組み
- 守り手: `backend/tests/test_tcg_extraction_record.py` 等の on_response の試験（PR② で追加）。

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例：試験の道具（`backend/app/tools/prompt_ab.py:552`）は、思考を JSONL に保存している。2026-10-12 の原因調査（見出しの行が外される理由）は、この保存済みの思考で初めて事実として確かめられた。本番でも同じ材料を残す。
- 外部事例：該当なし（既存の表に列を1つ足すだけで、新しい技術の選択を含まないため）。

## 9. 審査（Opus 自己審査）
- 判定: APPROVE。置き場は既存の1行に寄せていて、分散しない。解析の結果は変えない。
- 未解決: 保存期間（recon §6）。
