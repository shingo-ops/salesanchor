# recon: tcg-diagnostics-drawer

## タスク概要

TCG仕入元品質ページ（TcgSupplierQualityPage）のヘッダーにデータ健全性チェックボタンを追加し、
DiagnosticsDrawerコンポーネントを新規作成してDBデータ健全性チェック結果を表示する。

## 既存ADR検索結果

- `docs/adr/ADR-154-tcg-super-admin-readonly-diagnostics.md` — 既存: 診断APIの認可・固定SQLポリシー
- `docs/adr/ADR-144-ui-governance.md` — 既存: UIガバナンス（components/金型先確認）

## 実装対象ファイル

### 新規作成
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx` — 診断ドロワーコンポーネント

### 変更
- `frontend/src/pages/super-admin/TcgSupplierQualityPage.tsx:20` — ページコンポーネント（ボタン追加）
- `frontend/src/locales/ja.json:2267` — superAdmin.diagnostics キー群追加
- `frontend/src/locales/en.json:2267` — superAdmin.diagnostics キー群追加（ja対応）

## 既存パターン調査

### PageLayout headerAction パターン

- `frontend/src/components/PageLayout.tsx` — `headerAction?: React.ReactNode` prop を受け取り `<div className="page-layout-header-right">` に配置
- 例: `frontend/src/pages/super-admin/SupplierQualityList.tsx` — headerAction に Button を渡すパターン

### Drawer コンポーネント

- `frontend/src/components/Drawer.tsx` — props: `{open, onClose, title, children, onOpenFullPage?, footer?}`
- ReactDOM.createPortal でbody直下にレンダリング
- Esc/背景クリックで閉じる

### API呼び出しパターン

- `frontend/src/lib/api.ts` — `api.get<T>(path)` でFirebase JWT自動付与
- `.catch((e: unknown) => { setError(e instanceof Error ? e.message : String(e)); })` のパターンを踏襲

### 診断APIエンドポイント（バックエンド）

- `backend/app/routers/tcg_diagnostics.py:40` — `GET /tcg/diagnostics/{key}` エンドポイント（require_super_admin）
- `backend/app/services/tcg_diagnostics_svc.py:13` — `run_diagnostic(key)` サービス
- 対応キー: supplier-channels / suppliers / supplier-name-dupes / orphan-messages

## i18n キー構造

既存の `superAdmin` セクション（`frontend/src/locales/ja.json:2116`）に `diagnostics` サブセクション追加:
- `buttonLabel` / `drawerTitle` / `noRows`
- `sections.*` — 4セクション見出し
- `columns.*` — 9カラム見出し（APIレスポンスのキー名と対応）

## ハイライトロジック

- supplier-channels: `channel_count >= 2` の行を赤表示（複数チャンネル = 異常）
- orphan-messages: `null_channel_count !== 0` の行を赤表示
