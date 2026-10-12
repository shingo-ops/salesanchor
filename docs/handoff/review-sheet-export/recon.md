# recon: 要確認の一覧を配信テストのスプレッドシートに出力する

- 基準: origin/main `f9a303f0cdf6452ca54655f788453bcea39ed1f8`（2026-10-12）。調査は Sonnet（読み取りのみ）、確認は Opus。生出力はリポジトリ外の記録に置く。
- PO の依頼（原文 2026-10-12）:「https://docs.google.com/spreadsheets/d/1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4/edit?gid=0#gid=0→このシートは配信テストを確認するためのシートなのでこのシートの"要確認"シートに出力できる？」

## 1. ADR の検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限る。要確認の一覧は配信ではなく、別のタブに出す。
- `docs/adr/ADR-1007-migration-structure-only-run-once.md`：migration は構造だけ。値は1回だけのデータ変更として記録した SQL で入れる。
- `docs/adr/ADR-027-ui-internationalization.md`：UI 文字列の正本は ja.json と en.json。
- ADR-135・ADR-136：migration を含む PR は、マージ前に GO が要る。

## 2. 配信の書き込み（同じ仕組みに乗せる）
- `backend/app/services/tcg_distribution_svc.py:73-149`：サービスアカウントの鍵は、環境変数 TCG_SHEETS_SA_KEY_FILE から読む（:81-88）。安全装置は次の3つ。
  - #1 spreadsheetId の一致（:92-127）
  - #3 Drive の権限をログに出す（:129-149）
- `backend/app/services/tcg_distribution_svc.py:493-557` `_write_to_target_sync`：
  - #2 タブを自動で作らない（:521-528）
  - #4 タブ名の一致（:530-535）
  - #5 行数の上限 DIST_ROW_LIMIT（:537-543）
  - そのうえで、clear してからヘッダーとデータを append_rows（RAW）する（:545-548）。
- `backend/app/services/tcg_distribution_svc.py:710-917` `run_distribution`：有効な配信先ごとに書き込み、リトライし、結果を記録し（:890-905）、失敗を通知する（:910）。
- 配信先の設定の表は `public.tcg_distribution_targets`。列は id, name, spreadsheet_id, sheet_name, is_active, sa_key_secret_name, last_distributed_at, last_distributed_count, last_result, created_at, updated_at。読み込みは `backend/app/services/tcg_distribution_svc.py:566-568`。
- 起動の経路は次の4つ。
  - 解析の完了時：`backend/app/tasks/tcg_extraction.py:455-458, 607-609, 842-856`
  - 人が直した60秒後：`backend/app/tasks/tcg_extraction.py:697-720, 866-879`
  - API：`backend/app/routers/tcg_distribution.py:167-184`
  - `backend/app/line_import_admin.py:163`

## 3. 本番の実測（読み取りのみ）
- 配信先は3行で、すべて有効。対象の ID 1unwFM3…rm4 は name「配信テスト」、sheet_name「在庫集計」。最終の配信は 2026-10-12 12:15:26Z、956件、ok。ほかの2行は「山崎涼太郎」「無料トライアルシート」。
- 対象のシートのタブは「在庫集計」（sheetId 0）と「要確認」（sheetId 1737631885、1000行×26列、1行目は空）。
- サービスアカウントの権限は writer。
- 要確認（status_tab=NEEDS_REVIEW）は 321件（2026-10-12 時点）。
- TCG_AUTO_DISTRIBUTE=1。

## 4. 要確認の一覧の唯一の定義
- 画面 API は `backend/app/routers/tcg_analysis_review.py:114-157`。中身は `backend/app/services/tcg_analysis_review_svc.py:149-336` の `fetch_analysis_results`。NEEDS_REVIEW の条件は :82-85（`NOT ar.pid_resolved OR NOT ar.unit_resolved OR ar.exclusion IS NOT NULL OR cr.needs_review`）。
- 返す項目（:264-310）に、投稿日時は無い。

## 5. 理由の日本語
- 正本は `frontend/src/locales/ja.json` の reviewReason（ADR-027）。
- backend のコンテナは backend/ だけを COPY する（`backend/Dockerfile` の `COPY . .`）。そのため ja.json は本番の backend から読めない。
- `backend/tests/test_review_reason_codes_consistency.py:17` は、試験のときにリポジトリの frontend/src/locales を読む前例。

## 6. 未確認
- 要確認タブの書式・保護範囲の有無。
- Sheets API の quota への影響（配信と合わせて1回あたり1タブ増える）。
