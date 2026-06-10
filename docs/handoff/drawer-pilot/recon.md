# Drawer パイロット recon

> 作成: 2026-06-10 | 読み取り専用

---

## 1. 既存 Modal 実装

### Modal.tsx props

`frontend/src/components/Modal.tsx:24-33`

| prop | 型 | デフォルト | 説明 |
|------|---|-----------|------|
| `open` | `boolean` | 必須 | 表示/非表示 |
| `onClose` | `() => void` | 必須 | 閉じるコールバック |
| `title` | `string` | 必須 | ヘッダータイトル |
| `size` | `"sm" \| "md" \| "lg" \| "xl"` | `"md"` | ダイアログ幅 |
| `dismissOnOverlay` | `boolean` | `true` | 背景クリックで閉じるか |
| `children` | `ReactNode` | 必須 | 本体コンテンツ |
| `footer` | `ReactNode` | 省略可 | フッター（省略時は非表示） |

**サイズバリアント**（`frontend/src/tokens.css:253-256,338`）:
- `sm` → `--modal-max-w-sm: 420px`
- `md` → `--modal-max-w-md: 600px`
- `lg` → `--modal-max-w-lg: 800px`
- `xl` → `--modal-wide-w: 880px`

**CSS クラス**（`frontend/src/components/Modal.css`）:
- `.comp-modal-overlay` — `position: fixed; inset: 0; z-index: var(--z-backdrop)` で背景暗幕
- `.comp-modal-dialog` — センター配置、`flex-direction: column`、`max-height: calc(100vh - var(--space-8))`
- `.comp-modal-header` / `.comp-modal-body` / `.comp-modal-footer` — ヘッダー・本体・フッター区画

**アニメーション**: 現状アニメーションなし（`Modal.css` に `@keyframes` 未定義。`open` が false のとき `return null` で即消える実装）。

**a11y**: `role="dialog"` / `aria-modal="true"` / `aria-labelledby={titleId}`、フォーカストラップ・Esc 閉鎖・フォーカス復帰あり。`ReactDOM.createPortal` で `document.body` にマウント。

---

### Drawer/Slide 既存コンポーネント

汎用 Drawer コンポーネントは存在しない。

`components/` 配下に Drawer / Slide 系の独立コンポーネントはない（`frontend/src/components/` を全件確認）。
「Panel」サフィックスのコンポーネントは `CommissionPanel.tsx`、`OrderFinancialPanel.tsx`、`PurchaseDetailPanel.tsx`、`ShippingDetailPanel.tsx` の 4 件があるが、いずれもモーダル内コンテンツブロックであり、スライドイン Drawer ではない。

**ユーザー Drawer の先行実装あり**（`frontend/src/components/Layout.tsx:109,394-453` / `frontend/src/topbar.css:137-261`）:
- ユーザーアカウントメニューが `user-drawer` として右スライドで実装済み
- `transform: translateX(100%)` → `translateX(0)` で `transition: transform var(--transition-slow)` （`280ms cubic-bezier(0.4, 0, 0.2, 1)` — `frontend/src/tokens.css:138`）
- `position: fixed; top: 0; right: 0; height: 100vh; width: var(--drawer-width);` （`--drawer-width: 300px` — `frontend/src/tokens.css:155`）

---

### CSS

**既存 `.modal-*` 定義**（`frontend/src/components.css:463-529`）:
- `.modal-overlay`, `.modal`, `.modal-header`, `.modal-header__title`, `.modal-header__actions`, `.modal-icon-btn`, `.modal-icon-btn--danger`
- これらは旧 raw-div モーダル用の CSS（ADR-122 の移行対象）

**既存 `.comp-modal-*` 定義**（`frontend/src/components/Modal.css`）:
- 新標準 Modal コンポーネント（Task 7C）専用の CSS 名前空間

**既存 `.user-drawer-*` 定義**（`frontend/src/topbar.css:137-261`）:
- ユーザードロワー専用 CSS。右スライドアニメーション実装済み

**`.drawer-*` の汎用定義**: 存在しない。

**z-index 体系**（`frontend/src/tokens.css:125-128`）:
- `--z-backdrop: 298`
- `--z-drawer: 299`
- `--z-modal: 400`
- Modal は Drawer より z-index が高い（Drawer の上に Modal を重ねることが可能）

**会社フォーム用 CSS**（`frontend/src/company-forms.css:140-186`）:
- `.modal-content-wide .form-row` を前提としたグリッドレイアウトが存在する

---

## 2. 編集フォームの現状

### SuppliersPage

ファイル: `frontend/src/pages/suppliers/SuppliersPage.tsx` (175行)

**編集フロー**:
- `handleEdit(s: Supplier)` — `frontend/src/pages/suppliers/SuppliersPage.tsx:59-63`
  - `setEditId(s.id)`, `setForm(...)`, `setShowForm(true)` の3行でモーダルを開く
- `onRowClick={hasPermission("suppliers.update") ? (s) => handleEdit(s) : undefined}` — `frontend/src/pages/suppliers/SuppliersPage.tsx:121`
  - **DataTable の `onRowClick` を使用している唯一のページ**

**フォーム構造**:
- `<Modal>` コンポーネント（標準化済み）内にインラインフォームとして実装（`frontend/src/pages/suppliers/SuppliersPage.tsx:83-101`）
- 新規作成と編集で同一フォームを使用（`editId` の null チェックでタイトル・ボタン文言を切り替え）
- フォームフィールド: 6件（name, contact_name, email, phone, address, notes）
- 独立フォームコンポーネントなし（ページ内インライン）

**フルページ編集ルート**: なし（`/suppliers/:id/edit` は未定義）

---

### CompaniesPage

ファイル: `frontend/src/pages/companies/CompaniesPage.tsx` (585行)

**編集フロー**:
- `handleEdit(c: Company)` — `frontend/src/pages/companies/CompaniesPage.tsx:301-340`
  - `setEditId(c.id)`, `setForm(...)`, `setShowForm(true)`
- **DataTable に `onRowClick` は設定されていない** — `frontend/src/pages/companies/CompaniesPage.tsx:422-428`
  - 代わりに actions 列の「編集」ボタン、または会社名セルの `<Link to="/companies/:id">` から詳細ページへ遷移

**フォーム構造**:
- `<Modal size="lg">` コンポーネント（標準化済み）内にインラインフォームとして実装（`frontend/src/pages/companies/CompaniesPage.tsx:432-584`）
- タブ構成: basic / billing / delivery の3タブ
- フォームフィールド数: `form-row` が28件（多数）
- フルページ詳細ルートあり: `/crm/companies/:id` → `CompanyDetailPage`（`frontend/src/App.tsx:138`）

---

### ContactsPage

ファイル: `frontend/src/pages/contacts/ContactsPage.tsx` (521行)

**編集フロー**:
- `handleEdit(c: Contact)` — `frontend/src/pages/contacts/ContactsPage.tsx:198-215`
  - `setEditId(c.id)`, `setForm(...)`, `setShowForm(true)`
- **DataTable に `onRowClick` は設定されていない** — `frontend/src/pages/contacts/ContactsPage.tsx:357-364`
  - actions 列の「編集」ボタンからのみ編集フォームを開く

**フォーム構造**:
- `<Modal size="lg">` コンポーネント（標準化済み）内にインラインフォームとして実装（`frontend/src/pages/contacts/ContactsPage.tsx:367-481`）
- フォームフィールド数: `<input>/<select>/<textarea>` が約26件
- フルページ編集ルート: なし

---

### LeadsPage

ファイル: `frontend/src/pages/leads/LeadsPage.tsx` (432行)

**編集フロー**:
- `handleEdit(l: Lead)` — `frontend/src/pages/leads/LeadsPage.tsx:166-184`
  - `setEditId(l.id)`, `setForm(...)`, `setShowForm(true)`
- **DataTable に `onRowClick` は設定されていない** — `frontend/src/pages/leads/LeadsPage.tsx:402-408`
  - actions 列の「編集」ボタンからのみ編集フォームを開く
- フォームは `<Modal>` コンポーネントではなく、ページ内で `showForm` 状態で `<form>` を直接レンダリング（古い raw-div モーダルパターンの可能性あり。後続確認が必要）

**フォームフィールド数**: `<input>/<select>/<textarea>` が約31件（LeadsPage が最も多い）

**フルページ編集ルート**: なし

---

## 3. ルーティング現状

`frontend/src/App.tsx` の確認結果:

| パス | コンポーネント | 備考 |
|------|-------------|------|
| `/crm/leads` | `LeadsPage` | `frontend/src/App.tsx:135` |
| `/crm/companies` | `CompaniesPage` | `frontend/src/App.tsx:136` |
| `/crm/companies/:id` | `CompanyDetailPage` | `frontend/src/App.tsx:138` — 詳細ページあり |
| `/crm/contacts` | `ContactsPage` | `frontend/src/App.tsx:139` |
| `/suppliers` | `SuppliersPage` | `frontend/src/App.tsx:190` |
| `/admin/products/new` | `ProductEditPage` | `frontend/src/App.tsx:148` |
| `/admin/products/:id/edit` | `ProductEditPage` | `frontend/src/App.tsx:149` — フルページ編集の先行例 |

**詳細/編集ルートの有無**:
- `/crm/companies/:id` — CompanyDetailPage が存在（会社は詳細ページあり）
- `/suppliers/:id/edit`、`/crm/contacts/:id/edit`、`/crm/leads/:id/edit` — いずれも未定義

**ProductEditPage の構造** (`frontend/src/pages/products/ProductEditPage.tsx:1-10`):
- `/admin/products/new` と `/admin/products/:id/edit` の両方を1コンポーネントで担う
- `const isNew = !id` で新規/編集を切り替え
- `navigate(-1)` で完了後に呼び出し元へ戻る
- 30超のフィールドを持つ大規模フォームのため、ページ化された前例

---

## 4. パイロット候補 選定

| ページ | 条件①中心業務 | 条件②フォーム既存 | 条件③フィールド20以内 | 条件④i18n済み | 評価 |
|--------|-------------|----------------|-------------------|------------|------|
| SuppliersPage | ○ 仕入先管理 | ○ Modal内インライン | ○ 6フィールド | ○ t()のみ・ハードコードなし | **推奨** |
| ContactsPage | ○ 担当者管理 | ○ Modal内インライン | △ 約26フィールド | ○ t()のみ | 候補 |
| LeadsPage | ○ リード管理 | △ rawフォームの可能性 | ✕ 約31フィールド | ○ t()のみ | 不適 |
| CompaniesPage | ○ 顧客管理 | ○ Modal内インライン | ✕ 28フィールド+3タブ | △ 既知負債あり(ADR-027) | 不適 |

**推奨: SuppliersPage**

理由:
1. **唯一 `onRowClick` が設定済み** — `frontend/src/pages/suppliers/SuppliersPage.tsx:121`。Drawer を開くフックが既に存在し、変更量が最小。
2. **フォームが最小** — 6フィールド（name, contact_name, email, phone, address, notes）。Drawer の幅（`--drawer-width: 300px`）でも収まるが、編集用は400-480px程度が適切。
3. **標準 Modal コンポーネント使用済み** — ADR-122 対応済み（`frontend/src/pages/suppliers/SuppliersPage.tsx:3`）。
4. **i18n 完全対応** — `no-japanese-literal` 違反ゼロ。
5. **ページ全体が175行** — 副作用追跡が容易。

---

## 5. 実装方針の判断材料

### スライドの実装方法

**選択肢A: 既存 Modal コンポーネントの拡張**

pros:
- 既存 a11y（フォーカストラップ・Esc・フォーカス復帰）をそのまま継承
- `portal` ですでに `document.body` にマウント済み
- `size` バリアントの追加（`"drawer"` など）で実装できる
- `comp-modal-*` CSS 名前空間を拡張するだけ

cons:
- Modal と Drawer の関心を1コンポーネントに混在させる（SRP 違反）
- モバイルでの表示制御（`@media (max-width: 640px)` にボトムシート挙動あり）が複雑化
- `dismissOnOverlay` の扱いが異なる（Drawer はオーバーレイなしの実装もある）

**選択肢B: Drawer コンポーネント新設**

pros:
- 関心分離が明確（Modal = センター配置, Drawer = 右スライド）
- `user-drawer` の CSS パターンが先行例として完全に存在（`frontend/src/topbar.css:151-169`）。`position: fixed; top: 0; right: 0; height: 100vh; transform: translateX(100%); transition: transform var(--transition-slow)` をそのまま踏襲可能
- `--z-drawer: 299` の CSS 変数が既に用意されている
- フルページ展開ボタン（`ArrowUpRight` 等）の追加が自然
- 将来的に幅・アニメーション・ポジション（左/右）を柔軟に変えやすい

cons:
- フォーカストラップ・Esc・フォーカス復帰を再実装する必要がある（Modal.tsx からコピー可能）
- 新規ファイル作成（`components/Drawer.tsx` + `components/Drawer.css`）

**判断**: 選択肢B（Drawer 新設）を推奨。`user-drawer` の CSS が実証済みであり、`--z-drawer: 299` 変数も整備済み。Modal と Drawer の職責は異なるため、コンポーネント分離が設計として正しい。

---

## 6. 不明事項

以下は推測せず、確認が必要な事項：

1. **Drawer の幅設計** — `--drawer-width: 300px` はユーザーメニュー用。仕入先フォームに適切な幅（例: 400px / 480px）は別途設計が必要。
2. **LeadsPage の Modal 実装** — `<Modal>` コンポーネントを使っているか、旧 raw-div モーダルかを `LeadsPage.tsx` の `showForm` 使用箇所（200行以降）で確認が必要（今回の recon では確認できていない）。
3. **フルページ遷移先のルート** — `/suppliers/:id` または `/suppliers/:id/edit` は未定義。「フルページで開く」を実装する際のルート設計は別途 ADR または設計ドキュメントが必要。
4. **Drawer 内フォームの送信後挙動** — Drawer を閉じて一覧を更新するか、フルページに遷移したままにするか、UX フロー定義が必要。
5. **モバイルでの Drawer 挙動** — ボトムシート化するか、全画面化するかは未定義。
