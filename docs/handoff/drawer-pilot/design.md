# Drawer パイロット design

> 作成: 2026-06-10 | 担当: architect | パイロット: SuppliersPage のみ
> recon: docs/handoff/drawer-pilot/recon.md | ADR: ADR-122（Modal パターン踏襲）/ ADR-027（i18n）

---

## 外部・過去事例の参照と我々への応用

| プロダクト | パターン | 我々への応用 |
|-----------|---------|------------|
| **Notion** | ページをピーク（サイドピーク）で開き、↗ボタンでフルページ展開。一覧は左に残る | 同じ体験を目指す。Drawer = ピーク、`/suppliers/:id/edit` = フルページ |
| **Linear** | Issue 一覧で行クリック → 右ドロワーで詳細表示。フォームは共通コンポーネント | 行クリック→Drawer のインタラクションパターンを踏襲 |
| **GitHub** | PR 一覧で行クリック → 同一フォームを drawer/full-page 両方で編集可 | 共通フォームコンポーネントの設計を参照 |

---

## 1. KGI と受け入れ基準

| # | 基準 | 検証方法（Evaluator） |
|---|------|---------------------|
| AC1 | SuppliersPage で行クリック → 右 Drawer が開き仕入先情報を表示 | `browser_click` 行 → `data-testid="supplier-drawer"` visible |
| AC2 | Drawer 内フォームで編集・保存 → 一覧が更新される | 保存後 `data-testid="suppliers-table"` 内のセル値が更新 |
| AC3 | Drawer 表示中も一覧（DataTable）が背面に見えたまま | Drawer open 中に `data-testid="suppliers-table"` が DOM に存在 |
| AC4 | Drawer 内「フルページで開く↗」ボタン → `/suppliers/:id/edit` に遷移 | `browser_click` ↗ → URL が `/suppliers/\d+/edit` に変化 |
| AC5 | フルページ（`/suppliers/:id/edit`）でも同じフォームで編集・保存できる | ページ直アクセス → 保存 → 一覧に戻る（`/suppliers`） |
| AC6 | 編集フォームは共通化（SuppliersPage/SupplierEditPage で同一コンポーネント） | `SupplierFormFields.tsx` が1ファイル・両方でimport |
| AC7 | Esc キーで Drawer が閉じる | `browser_press_key("Escape")` → Drawer 非表示 |
| AC8 | `git revert` 可能（単一コミット or 連番コミット） | git log で確認 |

---

## 2. recon との相互参照

| 設計項目 | recon file:line |
|---------|----------------|
| SuppliersPage onRowClick 既存 | `pages/suppliers/SuppliersPage.tsx:121` |
| SuppliersPage handleEdit() | `pages/suppliers/SuppliersPage.tsx:59-63` |
| SuppliersPage 現行フォーム（6フィールド） | `pages/suppliers/SuppliersPage.tsx:83-101` |
| Modal.tsx props / a11y | `components/Modal.tsx:24-33` |
| user-drawer CSS パターン | `topbar.css:151-169` |
| --z-drawer CSS 変数 | `tokens.css:127` |
| --transition-slow | `tokens.css:138` |
| ProductEditPage ルート先行例 | `App.tsx:148-149` |

---

## 3. 技術設計

### 新規ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/src/components/Drawer.tsx` | 汎用右スライドコンポーネント |
| `frontend/src/components/Drawer.css` | Drawer 専用スタイル |
| `frontend/src/pages/suppliers/SupplierFormFields.tsx` | 仕入先フォームフィールド（共通） |
| `frontend/src/pages/suppliers/SupplierEditPage.tsx` | フルページ編集（`/suppliers/:id/edit`） |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/suppliers/SuppliersPage.tsx` | Modal → Drawer に置換、SupplierFormFields 使用 |
| `frontend/src/App.tsx` | `/suppliers/:id/edit` ルート追加 |
| `frontend/src/locales/ja.json` | Drawer 関連キー追加 |
| `frontend/src/locales/en.json` | 同上 |

### Drawer コンポーネント設計

```tsx
// props
interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;          // デフォルト: "480px"
  onOpenFullPage?: () => void;  // ↗ボタンのコールバック（省略時はボタン非表示）
  footer?: ReactNode;
}
```

- `ReactDOM.createPortal` で `document.body` にマウント（Modal と同じ）
- `position: fixed; top: 0; right: 0; height: 100dvh`（topbar.css パターンを踏襲）
- `z-index: var(--z-drawer)` = 299（z-index 体系準拠）
- `transform: translateX(100%)` → `translateX(0)`（`transition: transform var(--transition-slow)`）
- オーバーレイ: 半透明背景（z-index: var(--z-backdrop) = 298）、クリックで閉じる
- Esc キー: `useEffect` で keydown を購読 → onClose()
- フォーカストラップ: Modal.tsx の実装を移植
- モバイル（≤640px）: `width: 100%`（全画面）

### 共通フォームコンポーネント

```tsx
// SupplierFormFields.tsx
interface SupplierFormFieldsProps {
  form: SupplierFormState;
  onChange: (field: keyof SupplierFormState, value: string) => void;
}
```

SuppliersPage の現行フォーム（`SuppliersPage.tsx:83-101`）を抽出。新規/編集の切り替えはフォームフィールドの責務ではなく呼び出し元（SuppliersPage / SupplierEditPage）が持つ。

### ルート追加

```
/suppliers/:id/edit  →  SupplierEditPage
```

（`App.tsx:190` 付近の `/suppliers` ルートの直下に追加）

SupplierEditPage は `useParams()` で `:id` を取得し、`GET /api/suppliers/:id` で初期値をフェッチ。保存後 `navigate('/suppliers')` で一覧に戻る。

### i18n キー（新規追加）

```json
// ja.json
"suppliers": {
  "openFullPage": "フルページで開く",
  "editDrawerTitle": "仕入先を編集",
  "editPageTitle": "仕入先を編集"
}
// en.json
"suppliers": {
  "openFullPage": "Open full page",
  "editDrawerTitle": "Edit Supplier",
  "editPageTitle": "Edit Supplier"
}
```

---

## 4. 不明事項（Shingo 確認待ち）

| # | 不明事項 | 設計での仮置き |
|---|---------|-------------|
| U1 | Drawer の幅（300px では仕入先フォーム6フィールドが狭いが、480px でよいか） | **480px** で実装（ユーザーメニューの 300px とは別の CSS 変数 `--supplier-drawer-width` で管理） |
| U2 | モバイル（≤640px）で Drawer をどう見せるか | 全画面（width: 100%）で実装 |
| U3 | 新規作成もDrawerで行うか、現行「+追加」ボタンはそのまま残すか | **現行の Modal をそのまま残す**（Drawer はrowクリック=編集のみ）。新規作成 UI は今回変更しない |

---

## 5. 弊害・トレードオフ

| 観点 | 内容 |
|------|------|
| z-index | Drawer(299) の上に Modal(400) を重ねることは可能。「Drawer内の保存確認ダイアログ」等の将来ユースケースも対応可 |
| フォーカストラップ | Drawer と Modal が同時に開く場合の挙動は今回スコープ外（SuppliersPage には Drawer内 Modal は存在しない） |
| git revert | 新規ファイル4件 + 既存3件変更。revert は `git revert <commit>` 1コマンドで完全元戻し可能 |
| SSR | Vite + React SPA のため SSR 考慮不要 |

---

## 6. 実装計画

| ステップ | 内容 |
|---------|------|
| 1 | `Drawer.tsx` + `Drawer.css` 新設（スタンドアロン・既存変更なし） |
| 2 | `SupplierFormFields.tsx` 抽出（SuppliersPage のフォーム部分を分離） |
| 3 | `SuppliersPage.tsx` の Modal を Drawer に置換・SupplierFormFields 使用 |
| 4 | `SupplierEditPage.tsx` 新設（フルページ）+ `App.tsx` にルート追加 |
| 5 | i18n キー追加 |
| 6 | Evaluator / Reviewer / CI |
