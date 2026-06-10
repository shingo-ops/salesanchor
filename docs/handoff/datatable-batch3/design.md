# DataTable 標準化 バッチ3 設計書

> **参照: recon = docs/handoff/datatable-standardization/recon.md / ADR-067**
> **作成日**: 2026-06-10
> **担当**: Hikky-dev

---

## KGI・KPI

| 基準 | 検証方法 |
|------|---------|
| 対象5テーブルの `<table className="data-table">` が0件になること | `grep -r 'class.*data-table' frontend/src/pages/{deals,companies,contacts,teams}/` で0件確認 |
| TypeScript エラー 0件 | `./node_modules/.bin/tsc --noEmit` でエラーなし |
| `row-pending-dedup` ハイライトが CompaniesPage / ContactsPage で保持されること | `rowClassName` prop 確認 + `.comp-table__row.row-pending-dedup:hover .comp-table__td` CSS セレクタ存在確認 |
| DataTable `rowClassName` prop が既存利用に影響しないこと | 既存ページのテスト・動作確認 |

---

## 設計方針

バッチ1（PR #1863）・バッチ2（PR #1865）と同一パターンを踏襲し、追加で 1 点の DataTable 拡張を行う:

1. `<table className="data-table">` を `<DataTable<T>>` に置換
2. `DataTableColumn<T>[]` を component body 内 IIFE で定義（props/state/hooks クロージャ参照のため）
3. `emptyState` prop に既存 i18n キーを流用（新規キー追加なし）
4. `rowKey` は `(row) => String(row.id)` または各型の主キーを使用
5. API 呼び出し・状態管理・pagination UI は一切変更しない

**追加 (バッチ3 固有)**:
- `DataTable` に `rowClassName?: (row: T) => string` prop を追加。CompaniesPage / ContactsPage の `row-pending-dedup` ハイライトを維持するために必要。既存利用への影響ゼロ（省略時は空文字列）。
- `components.css` に `.comp-table__row.row-pending-dedup:hover .comp-table__td` セレクタを追加（既存 `.data-table tr` セレクタと並列、相互に独立）。

---

## ファイルごとの設計メモ

### DealsPage
- `fmt()` / `companyName()` は component 内関数 → renderCell クロージャで参照
- badge: `getStatusPresentation("deal", d.status).badgeVariant`

### CompaniesPage
- name 列: `<Link to={/companies/${c.id}}>{companyDisplayName(c)}</Link>`
- `status-badge status-{status}` クラスは ADR-067 の badge とは別系統（独自クラス）— そのまま保持
- `rowClassName={(c) => c.status === "pending_dedup_review" ? "row-pending-dedup" : ""}`

### ContactsPage
- isPrimary 列: `<STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />`
- channels 列: `c.contact_channels.length > 0 ? <ContactChannelLinks contactId={c.id} /> : null`
- `rowClassName` で `row-pending-dedup` を維持
- `confirmAsDistinct` ボタンは `pending_dedup_review` 行にのみ表示（actions 列の renderCell 内）

### TeamsPage
- 2テーブル（members + teams）を独立した IIFE パターンで実装
- members テーブルは `Modal` コンポーネント内に配置（変更対象外のモーダル構造は維持）

---

## 外部・過去事例の参照と我々への応用

参照: `docs/handoff/datatable-standardization/recon.md`（全ページ recon・バッチ1〜2のパターン定義）および `docs/adr/ADR-067-design-tokens.md`（デザイントークン強制ルール）。

バッチ1・2で確立した「component body 内 IIFE で columns 定義」パターンをバッチ3でも踏襲。`rowClassName` prop の追加は React の controlled component パターンに合致する最小限の DataTable 拡張であり、shadcn/ui・Ant Design Table など主要ライブラリが行単位クラスをサポートする標準的な設計。既存利用に対して後方互換性を持つ（省略時のデフォルト: `undefined` → row に追加クラスなし）。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| `rowClassName` prop が DataTable の将来の拡張と競合する | prop 名は明確なセマンティクスを持ち、他ライブラリでも使われる標準的な名前 |
| `.comp-table__row.row-pending-dedup:hover` の詳細度衝突 | `.data-table tr.row-pending-dedup:hover td` と並列配置。stylelint `no-descending-specificity` は既存の `/* intentional */` コメントと同様に対処 |
| TeamsPage の members テーブルが Modal 外に漏れる | Modal の open/close は `membersPanel` state で制御。DataTable 置換はレンダリング位置に影響しない |
