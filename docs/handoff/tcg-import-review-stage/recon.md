# recon: TCG LINE import 確認工程

## 実測（2026-09-05）

### 未解決推移（同日実作業ログ）
- 初回取り込み: 19名未解決（うち切り出しバグ起因が複数名）
- _split_sender バグ修正後の再取り込み: 15名未解決
- 15名登録後: 0名未解決 → 抽出エンキュー実行

### 現状の問題（修正前）
- 未解決名が 1 件以上あっても source_messages を書いてしまう
  → その回の在庫を取りこぼす（担当者が未解決に気づかず抽出に進んでしまう）
- 確認・登録フローがなく、毎回全件登録済みでないと意味のある取り込みにならない

### DIST-R3: 窓が UTC 基準で実質 33h だった
```
旧実装: backend/app/services/tcg_line_import_svc.py（修正前）:367
  cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
```
LINE エクスポートのタイムスタンプは JST。UTC を基準にすると
JST +9h が上乗せされ、cutoff が 9h 古くなる → 実質 33h ウィンドウになっていた。

## ファイル・行参照

### migration（既存）
- `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:362-374`
  → import_jobs CREATE TABLE（列一覧：id/filename/raw_sha256/message_count/provider_count/
    unresolved_count/uploaded_by/status/created_at）

### 取り込みサービス（変更前）
- `backend/app/services/tcg_line_import_svc.py:291-530`（変更前）
  → import_line_export の全処理（分岐なし）
- 同:367 → UTC 基準 cutoff（DIST-R3）

### ルーター（変更前）
- `backend/app/routers/tcg_line_import.py:70-218`（変更前）
  → POST /tcg/line-import, GET /history, GET /unresolved のみ

## 既存 ADR 検索結果
```
git grep -i "tcg.*import\|line.*import\|review.*stage" docs/adr/
```
- ADR-154: `docs/adr/ADR-154-tcg-line-import-phase2.md` — GAS移植先の設計（Phase 2）
  → GAS には確認工程なし。本 PR の確認工程は GAS に存在しない新規機能
  → 照合ロジック（tcg_analyzer_svc.py）には触れない

## 関連ブランチ
- `#3305 release/fix-tcg-received-at-jst`（未マージ）: 同一ファイルで JST 定数を追加予定
  → 本 PR で JST_TZ を独立定義し、マージ後に統合予定と recon に記録
