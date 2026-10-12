# recon: 配信の「48時間以内」の定義（便AGE）

基準 origin/main（2026-10-11）。本番は読み取りのみ。生出力（手元）: /tmp/CC報告ファイル/is-current-48h/

## 既存 ADR
- ADR-158（is_current = 同じ仕入元×商品×状態の最新行。経過時間は見ない）。docs/adr を max_age・48時間・line_posted_at で git grep した結果、配信の経過時間を定める ADR は無し。

## is_current を読む箇所（backend/app・frontend/src・~/tcg-client-viewer）
| 場所 | 用途 | 48時間で絞るか |
|---|---|---|
| backend/app/services/tcg_distribution_svc.py:263 fetch_output_rows | 配信本体（Google シート「在庫集計」） | 絞る :220-224 |
| backend/app/services/tcg_distribution_svc.py:337 fetch_preview_data | 配信候補件数 | 絞る :322-326（:220-224 と同文の複製） |
| backend/app/services/tcg_distribution_svc.py:379 同関数の除外内訳 | プレビューの除外内訳の件数 | 絞らない |
| backend/app/services/tcg_analysis_dashboard_svc.py:713 | line_posted_at NULL の件数 | 絞らない（NULL を数えるだけ） |
- 書く側: backend/app/services/tcg_analyzer_svc.py:1735-1860 _merge_supplier_products（経過時間は見ない）。
- 在庫一覧 viewer（~/tcg-client-viewer/src/Code.js:25,52-60）は配信先シートを読む。index.html:286 FRESH_WINDOW_HOURS = 24 の既定チェックで24時間より前を隠す（別リポジトリ・本便では触らない）。

## 設定
- 値は public.tcg_distribution_settings.max_age_hours（本番 48）。読む所は tcg_distribution_svc.py:306（プレビュー）と :762（配信実行）、どちらも `int(settings.get("max_age_hours", "0"))`。キーが無いと 0 → 絞りが外れ全期間が配信される。
- 画面の説明 frontend/src/locales/ja.json:5135「LINE投稿からこの時間を超えた商品は配信から除外されます。0で無制限。」

## 配信先
- tcg_distribution_svc.py:519-522 worksheet.clear() → append_rows（毎回全置換）。

## 本番（2026-10-11 02:58 UTC）
- v102 の is_current は全て48時間以内（48時間より前 0件）。全エンジンの is_current のうち48時間より前は 11,258件（v7/v8/v9）。配信には出ていない。
