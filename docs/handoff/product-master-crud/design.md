# design.md — product-master-crud

参照: [recon.md](docs/handoff/product-master-crud/recon.md) / ADR-155（マージ済み）

---

## 目的

商品マスタ画面から商品の新規追加と既存商品の削除をできるようにし、
ADR-155 のアプリ画面経由の更新手段を完成させる。

---

## 対象と対象外

| 区分 | 内容 | 理由 |
|------|------|------|
| **対象** | 商品の新規追加（POST エンドポイント + UI） | ADR-155 要件 |
| **対象** | 商品の削除（DELETE エンドポイント + UI + 確認ダイアログ） | ADR-155 要件 |
| **対象外** | CSV 取り込み機能 | 既存で動作中 |
| **対象外** | 商品の編集機能 | 既存で動作中（PUT） |

---

## 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/routers/tcg_product_import.py` | GET /lookups, POST /create, DELETE /detail/{code} 追加 |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx` | 作成モード・削除ボタン・ConfirmModal 追加 |
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx` | 「新規追加」ボタン追加 |
| `frontend/src/locales/en.json` | i18n キー追加 |
| `frontend/src/locales/ja.json` | i18n キー追加 |

---

## 検証基準

| 基準 | 検証方法 | 合格条件 |
|------|---------|---------|
| 新規追加 | 「新規追加」ボタン→フォーム入力→作成 | 一覧に新商品が表示される |
| 削除 | 商品詳細→削除ボタン→確認→実行 | 一覧から商品が消える |
| 削除拒否 | 在庫参照中の商品を削除しようとする | エラーメッセージが表示され削除されない |
| 既存編集無影響 | 商品詳細で編集→保存 | 変更前と同じ挙動 |
| i18n | 英語・日本語で画面表示 | 全テキストが翻訳済み |
| テスト | CI の Frontend lint & custom checks | pass |

---

## リスクと対処

| リスク | 発生条件 | 対処 |
|--------|---------|------|
| FK 制約違反 | 在庫等が参照中の商品を削除 | 409 エラーでユーザーに通知、削除中止 |
| analysis_results 孤児 | 削除前に product_id を NULL 化 | DELETE 前に UPDATE で NULL 設定 |
| PM コード枯渇 | PM9999 到達時 | create_product 内で例外発生→エラー通知 |

---

## 外部・過去事例の参照と我々への応用

自プロジェクト内の既存設計のみ参照。
- ADR-155: 商品マスタ SSOT 方針（CSV + アプリ画面のみ）
- `backend/app/services/tcg_product_master_svc.py:308` の既存 `create_product()` を再利用

---

## 維持の仕組み（守り手）

守り手:
- migration-guard.yml チェック 7 が商品マスタテーブルへの migration 経由の値操作を CI でブロック（関所パス: `.github/workflows/migration-guard.yml`）
- `require_super_admin` 認証で作成・削除を管理者のみに制限（関所パス: `backend/app/routers/tcg_product_import.py`）
- FK 制約（RESTRICT/CASCADE）がデータ整合性を DB レベルで保護（関所パス: `migrations/20260915_120000_*.sql`）
