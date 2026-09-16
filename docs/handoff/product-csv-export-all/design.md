# design.md — product-csv-export-all

参照: [recon.md](docs/handoff/product-csv-export-all/recon.md) / ADR-155（マージ済み）

---

## 目的

「更新用CSVを出力」ボタンが検索フィルタに関係なく全商品をCSVで出力する。

---

## 対象と対象外

| 区分 | 内容 | 理由 |
|------|------|------|
| **対象** | `TcgProductMasterPage.tsx` の `downloadExport()` | エクスポートAPIにフィルタパラメータを渡している箇所 |
| **対象** | `TcgProductMasterPage.test.tsx` のR10テスト | パラメータ検証の期待値 |
| **対象外** | バックエンドAPI・サービス | パラメータなしで全件返す仕様で変更不要 |
| **対象外** | 一覧表示の検索・ページング | エクスポートとは独立した機能 |

---

## 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx` | `downloadExport()`内のパラメータ送信3行を削除、パラメータなしでAPI呼び出し |
| `frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx` | R10テストのパラメータ検証を「パラメータなしで呼ばれる」検証に変更 |

---

## 検証基準

| 基準 | 検証方法 | 合格条件 |
|------|---------|---------|
| 全件出力 | 検索テキスト入力状態で「更新用CSVを出力」を押す | CSVの行数が全商品数+1（ヘッダー）と一致 |
| タブ絞り込み無視 | 作品タブを選択した状態で出力 | 同上 |
| 一覧表示無影響 | 検索・タブ・ページ送り操作 | 変更前と同じ挙動 |
| テスト合格 | `vitest run` | R10テスト含む全テストpass |

---

## リスクと対処

| リスク | 発生条件 | 対処 |
|--------|---------|------|
| CSV容量超過 | 商品数が大幅増加した場合 | バックエンドの `MAX_BYTES = 2MB` 制限でエラー返却。現在1,626件で約325KB |

---

## 外部・過去事例の参照と我々への応用

自プロジェクト内の既存設計のみ参照。CSVラウンドトリップ仕様（design §21）に準拠。
ADR-155 で商品マスタの更新手段をCSV取り込みとアプリ画面に一本化する方針が確定済み。

---

## 維持の仕組み（守り手）

守り手:
- バックエンドの `MAX_BYTES = 2MB` 制限が全件出力時のサイズ超過を防止（関所パス: `backend/app/services/tcg_product_roundtrip_svc.py`）
- `TcgProductMasterPage.test.tsx` のR10テストがエクスポートAPIの呼び出し方法を検証（関所パス: `frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx`）
- TypeScript コンパイルチェック（CI）
