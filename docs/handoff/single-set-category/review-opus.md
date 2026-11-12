# Opus 審査記録: シングルセット系の設計（同一 AI の自己審査・独立の審査ではない）

- 日時: 2026-11-11（1〜5 回目）
- 対象: `docs/handoff/single-set-category/recon.md`・`docs/handoff/single-set-category/design.md`・`docs/adr/ADR-1027-bundle-sale-reading.md`（追記）・`docs/adr/ADR-1031-single-and-promo-pack-conditions.md`（What 6 追補）
- 審査役: 手元の reviewer（model opus）。1 回ごとに新しく起動した。
- 判定: 1〜4 回目は REVISE、5 回目は APPROVE（便1 は実装可能）。各回の指摘と直しは `docs/handoff/single-set-category/design.md` §12 の表。
- 確かめたこと（origin/main の実物と本番の読み取り）:
  - 区分ごとの状態の群は `backend/app/services/gemini_raw_copy_v102_product_first.py:764-769` と `backend/app/services/line_analysis_v102_svc.py:690-695` の 2 つの表で決まる。
  - まとめ売りの読み取りは `backend/app/services/line_analysis_v102_svc.py:1184-1187` で全部の行に当たる。写しは `scripts/dev/bundle_replay.py` と `scripts/accuracy/llm_compare/fhd_snapshot.py:87-88`。
  - 本番に単位 Set（`line_units` の code UN0005、有効）が在る（reader、/tmp/CC報告ファイル/ssc-setunit.txt）。
  - 状態の群の列は本番の `line_conditions.value_group`（reader、/tmp/CC報告ファイル/ssc-condtbl.txt）。
  - 付け替える 13 商品の今の区分は 13 商品ともセット系（reader、/tmp/CC報告ファイル/ssc-p13.txt）。
  - `scripts/` を触るので process-artifacts gate が危険な道として扱う（`scripts/check-process-artifacts.js:1022`, `:1025`）。便1 は ADR-136 の GO の手順を通す。
- 未解決: K1b が偽の接続で `_unit_price_mismatches` を通るか（便1 の CI で決まる）。外した job の扱い（便3 の後に PO に聞く）。
- マージ前の審査（2026-11-12、手元の reviewer・model opus を新しく起動）: REVISE。必須は 1 件で、ブランチの土台が古く必須の確かめ guard-authoring/evaluation が赤（書類の中身の誤りではない）。main を取り込んで直した。推奨 5 件（ADR-1031 の「承認待ち」の古い記述、design §11 の古い記述、recon の商品表の数の読んだ時点、design §1 の具体の値段、リポジトリ外のパスのバッククォート）も同じ時に直した。
