# Design: product_kinds CRUD API + 管理UI

## 概要

`public.product_kinds` テーブルの CRUD API と管理UIを追加する。
TCG中分類（type_master）の上位区分として機能する「大分類」マスタ。

## 受入基準

| 基準 | 検証方法 |
|------|---------|
| GET /api/v1/super-admin/product-kinds が200を返す | curl -H "Authorization: Bearer <token>" https://api.salesanchor.jp/api/v1/super-admin/product-kinds |
| POST で新規作成できる | curl -X POST ... body: {"code":"test","name":"テスト"} → 201 |
| PATCH で更新できる | curl -X PATCH .../1 body: {"name":"更新後"} → 200 |
| DELETE で soft delete される | curl -X DELETE .../1 → 204、DB: is_active=FALSE を確認 |
| type_master 参照中の DELETE は 409 を返す | kind_id が設定済みの type_master ID を持つ kind を DELETE → 409 |
| 全UI文字列が t() 経由 | grep でハードコード日本語がないこと（ProductKindsMasterPanel.tsx） |
| ja.json と en.json に同一キー | 両ファイルの productKindsMaster セクションが同一キー構造 |
| AnalysisRulesPage サイドバーに「大分類マスタ」が表示される | ブラウザで /super-admin/analysis-rules を開いて左メニューを確認 |

## 影響範囲

- **バックエンド新規**: product_kind.py スキーマ、super_admin_product_kinds.py ルーター
- **バックエンド変更**: central_masters.py の TcgTypeResponse/Update に kind_id を追加（既存フロントへの影響: kind_id フィールドが optional で追加されるだけなので破壊的変更なし）
- **フロントエンド新規**: ProductKindsMasterPanel.tsx
- **フロントエンド変更**: AnalysisRulesPage.tsx、AnalysisRulesSidebar.tsx（サイドバーに項目追加のみ）

## 外部事例

product_categories と type_master の既存パターンをそのまま踏襲。新規設計不要。

## 外部・過去事例の参照と我々への応用

既存の `backend/app/routers/super_admin_product_categories.py` および `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx` が直接適用可能な先行事例として存在。
API構造（soft delete、IntegrityError→409、生SQL+sqlalchemy.text）をそのまま踏襲。フロントは DataTable + Modal + ConfirmModal の金型パターンを流用。

## 維持の仕組み

守り手:
- `require_super_admin` dependency でアクセス制御を維持
- soft delete（is_active=FALSE）により削除ログが残る
- i18n: ja.json/en.json の同一キーを CI でチェック（ADR-027）

## 守り手

- ADR-027: i18n 強制 → ProductKindsMasterPanel.tsx で全文字列 t() 使用
- ADR-144: UIガバナンス → DataTable/Modal/HeaderButton/TextField 金型コンポーネント使用
- soft delete パターン: DELETE は is_active=FALSE（実レコード削除なし）
- 参照整合性: type_master.kind_id で参照中なら 409 を返す
