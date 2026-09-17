# recon.md — product-csv-export-all

## 問題

「更新用CSVを出力」ボタンが現在の検索フィルタ（テキスト検索・作品タブ）を
そのままエクスポートAPIに渡すため、絞り込み中は一部の商品しかCSVに含まれない。
更新用CSVは全商品マスタのラウンドトリップ用であり、常に全件出力が正しい動作。

## 根本原因

| 要因 | 詳細 |
|------|------|
| フロントエンドの実装 | `downloadExport()` が一覧表示用の `filter.query` と `filter.workId` をエクスポートAPIにも渡している |
| バックエンド | `export_csv()` は受け取ったパラメータでフィルタするため、空パラメータなら全件返す仕様で問題なし |

根拠: `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:46-48`（変更前）

## 影響範囲

| ファイル | 役割 | 影響 |
|---------|------|------|
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:40-52` | CSVエクスポート関数 | 修正対象 |
| `frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:20-40` | エクスポートテスト | 期待値修正 |
| `backend/app/routers/tcg_product_import.py:150-166` | エクスポートAPI | 変更なし |
| `backend/app/services/tcg_product_roundtrip_svc.py:94-118` | snapshots関数 | 変更なし |

## ADR 参照

- ADR-155: 商品マスタデータの更新手段をCSV取り込みとアプリ画面に一本化する
