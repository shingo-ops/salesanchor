# 単位マスタ実装設計

## 概要

public.units / public.unit_aliases テーブルに対するCRUDインターフェース（バックエンド + フロントエンド）を実装する。
仕入元マスタ（suppliers）と同一パターンで実装。

## 設計方針

### DB
- public.units に tenant_id INTEGER REFERENCES public.tenants(id) を追加
- NULL = 共用（LINE解析用マスタ）、数値 = テナント個別
- 既存データ（8行）は tenant_id を変更しない（NULL のまま）

### バックエンド
- 共用マスタ: super_admin_units.py（require_super_admin）
- テナント用: units.py（require_permission("suppliers.view")、ADR-072 reset_tenant_context）
- Pydantic: central_masters.py に UnitBase/Create/Update/Response + UnitAliasBase/Create/Response 追加
- raw SQL（SQLAlchemy model なし、suppliers と同じパターン）

### フロントエンド
- 解析管理（スーパーアドミン）: UnitMasterPanel.tsx → AnalysisRulesPage に統合
- テナント管理: UnitsPage.tsx → /management-center/units ルート
- i18n: ja.json / en.json に unitMaster セクション + nav.units キー追加

## 外部・過去事例の参照と我々への応用

仕入元マスタ（#3400 台 PR 群）で確立した suppliers パターンを踏襲。
suppliers と同構造のため新たな外部事例を探すまでもなく既存内部事例が適用できる。

## 維持の仕組み

- 守り手: 既存の backend unit test suite（CI）+ TypeScript コンパイルチェック
- 新規権限なし（suppliers.view を流用）
- ADR-072 reset_tenant_context は units.py の write エンドポイント全箇所に適用済み
