# Design: 仕入元マスタ UI 分離

recon: `docs/handoff/supplier-master-ui-separation/recon.md`
ADR: ADR-093（在庫テーブル・商品マスタ再設計）

## 外部・過去事例の参照と我々への応用

該当なし：今回は既存の MasterListEditor 金型（ProductMastersTab 内部実装）を抽出・再利用する社内リファクタであり、外部事例の参照は不要と判断

## 目的

仕入元マスタを用途別に2画面に分離し、MasterListEditor 金型で統一する。

## 対象と対象外

| 対象 | 対象外 |
|------|--------|
| テナント側 `/management-center/suppliers` の改修 | DB スキーマ変更（済み） |
| SaaS管理者 `/super-admin/masters` ページ新設 | 仕入先データの移行 |
| バックエンド `tenant_id` フィルタ追加 | 権限モデルの変更 |
| MasterListEditor 金型の共有化 | Discord routing 機能の変更 |

## 変更前後

### テナント側（管理センター > データ管理 > 仕入先）

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| 表示データ | `public.suppliers` 全229件 | `tenant_id = 自テナント` の行のみ |
| レイアウト | 独自レイアウト | MasterListEditor 金型 |
| CRUD | 全件に対して可能 | 自テナント行のみ。作成時 `tenant_id` 自動セット |
| LINE解析用 | 見える | **見えない** |

### SaaS管理者（SaaS管理者メニュー > マスタ管理）

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| ページ | ルーティングなし（孤立） | `/super-admin/masters` に配置 |
| 表示データ | `public.suppliers` 全件 | `tenant_id IS NULL` の行のみ（LINE解析用） |
| レイアウト | 独自レイアウト | MasterListEditor 金型 |
| タブ構成 | なし | 商品マスタタブ + 仕入元マスタタブ |

## 実装方針

### Sprint 1: MasterListEditor 共有化

`MasterListEditor` を `frontend/src/pages/super-admin/ProductMastersTab.tsx` 内部から独立コンポーネントに抽出する。

- 抽出先: `frontend/src/components/master-list-editor/MasterListEditor.tsx`
- `MasterDataSource` インターフェースはそのまま維持
- `ProductMastersTab` は抽出後のコンポーネントを import して使用（動作変更なし）

### Sprint 2: SaaS管理者マスタ管理ページ

1. `/super-admin/masters` ルートを `App.tsx` に追加
2. 親ページ `SuperAdminMastersPage.tsx` を作成（タブ切り替え）
   - タブ1: 商品マスタ（`ProductMastersTab` そのまま）
   - タブ2: 仕入元マスタ（`SuppliersAdminTab` を MasterListEditor 金型に改修）
3. バックエンド: `/super-admin/suppliers` に `WHERE tenant_id IS NULL` フィルタ追加

### Sprint 3: テナント側仕入先ページ改修

1. `SuppliersPage.tsx` を MasterListEditor 金型に改修
2. バックエンド: `/suppliers` に `WHERE tenant_id = :current_tenant` フィルタ追加
3. `POST /suppliers` で `tenant_id` を自動セット
4. `PATCH/DELETE /suppliers/{id}` で `tenant_id` 一致チェック追加

## 影響範囲

| 影響先 | 内容 | リスク |
|--------|------|--------|
| `frontend/src/pages/suppliers/SuppliersPage.tsx` | MasterListEditor 化 + フィルタ | テナントユーザーの操作画面が変わる |
| `frontend/src/pages/super-admin/SuppliersAdminTab.tsx` | MasterListEditor 化 + フィルタ | SaaS管理者の操作画面が変わる（現在未使用） |
| `backend/app/routers/suppliers.py` | tenant_id フィルタ追加 | 既存データ（全 NULL）はテナント側で非表示になる |
| `backend/app/routers/super_admin_suppliers.py` | tenant_id IS NULL フィルタ | テナント作成の仕入先は SaaS 管理者に非表示 |
| `frontend/src/App.tsx` | `/super-admin/masters` ルート追加 | 新規追加のみ、既存破壊なし |

## 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | テナント側で自テナントの仕入先のみ表示される | テナントユーザーでログイン → `/management-center/suppliers` → 表示件数が `SELECT count(*) FROM public.suppliers WHERE tenant_id = N` と一致 |
| 2 | テナント側でLINE解析用仕入先が見えない | テナントユーザーでログイン → 仕入先一覧に `tenant_id IS NULL` の行が0件 |
| 3 | テナント側で新規作成した仕入先に tenant_id が自動セットされる | 新規作成 → DB で `SELECT tenant_id FROM public.suppliers WHERE id = 新ID` → テナントIDと一致 |
| 4 | SaaS管理者でLINE解析用仕入先のみ表示される | SaaS管理者でログイン → `/super-admin/masters` → 仕入元マスタタブ → 件数が `SELECT count(*) FROM public.suppliers WHERE tenant_id IS NULL` と一致 |
| 5 | SaaS管理者でテナント作成の仕入先が見えない | SaaS管理者で仕入元マスタタブ → テナント作成行が0件 |
| 6 | 両画面が MasterListEditor 金型で統一されている | 商品マスタタブと仕入元マスタタブのレイアウトが同一パターン |
| 7 | i18n 遵守 | `grep -r "仕入" frontend/src --include="*.tsx"` → ハードコード日本語0件 |
| 8 | 既存テスト通過 | CI 全チェック green |

## 代替案と選択理由

| 案 | 内容 | 採否 |
|----|------|------|
| A: MasterListEditor 統一（採用） | 金型を抽出して両画面で共用 | PO 指示。統一感あり。保守コスト低 |
| B: 各画面独自レイアウト維持 | 現状のまま tenant_id フィルタだけ追加 | 却下。PO が統一を指示 |

## リスクと対処

| リスク | 対処 |
|--------|------|
| 既存データ全229件が tenant_id=NULL のためテナント側で何も見えなくなる | 想定通り。テナントが新規作成すると tenant_id 付きで登録される |
| MasterListEditor 抽出で商品マスタの動作が変わる | 抽出は純粋なリファクタ。既存テストで回帰確認 |
| SuppliersAdminTab の Discord routing 機能が MasterListEditor に収まらない | MasterListEditor を拡張するか、Discord routing は別モーダルとして維持 |

## 維持の仕組み

- 守り手: `frontend/src/components/master-list-editor/MasterListEditor.tsx` — 共通金型。変更時は商品マスタ・仕入元マスタ両方を確認
- 守り手: `backend/app/routers/suppliers.py` — tenant_id フィルタをバックエンドで強制。フロントエンドに依存しない
- 守り手: CI の既存 i18n チェック・UI ガバナンスチェック・テナントスキーマ整合性チェックで継続監視
