# recon: 要確認タブから旧解析版の行を外す

生出力: ~/CC報告ファイル-keep/review-hide-old/recon/（base: origin/main）

## 既存 ADR 検索
- ADR-158:63「レビュー画面は最新メッセージの抽出結果を表示する目的」— 矛盾しない（docs/adr/ADR-158*）。

## 現状（file:line）
- backend/app/services/tcg_analysis_review_svc.py:16 `V102_PROMPT_VERSION_PREFIX` を import 済み
- 一覧本体 fetch_analysis_results、条件は `_build_where`（変更前 87-151）
- NEEDS_REVIEW 条件: backend/app/services/tcg_analysis_review_svc.py:119-122（変更前）`(NOT ar.pid_resolved OR NOT ar.unit_resolved OR cr.needs_review)`
- review_only: backend/app/services/tcg_analysis_review_svc.py:138-141（変更前）同条件を重複記述
- 件数/仕入元一覧/ページ/本体が同じ where を使う: backend/app/services/tcg_analysis_review_svc.py:225-226, 229-236, 239-246, 302（変更前）
- 282 で既に `starts_with(ej.prompt_version, :v102_prefix)` を is_v102 として SELECT、305 で値を渡す（本体のみ）
- v102 判定の正: backend/app/services/line_analysis_v102_svc.py:82, :141
- 同じ fetch の他の呼び元: backend/app/services/tcg_review_csv_svc.py:75、backend/app/services/tcg_review_sheet_svc.py:108
- 本番: 旧版で is_active=t は 155 行、要確認の近似で 52 行
