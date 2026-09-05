# recon — ui-line-import-upload-button（アップロードボタン修正）

**仕事名**: TcgLineImportPage のアップロードボタンを生 `<button>` から `Button` コンポーネントに置き換え  
**日付**: 2026-09-05  
**対象ADR**: ADR-144, ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:303` | 変更前: 生 `<button>` + インライン style（`background: var(--color-primary)` 直書き） |
| `frontend/src/components/Button.tsx:1` | 金型定義。variant: primary/secondary/ghost/danger/outline/tab、size: sm/md/lg |
| `frontend/src/components/Button.tsx:20` | `ButtonVariant` / `ButtonSize` 型定義 |
| `frontend/src/pages/company-detail/CompanyContactsTab.tsx:219` | primary の実例: `<Button type="submit" size="sm" variant="primary" disabled={contactSubmitting}>` |
| `docs/adr/ADR-144-ui-component-governance.md` | 生 button 禁止・既存コンポーネント使用義務 |

---

## 1. 変更前のボタン実装（`TcgLineImportPage.tsx:303` 付近）

```tsx
<button
  onClick={handleUpload}
  disabled={uploading || !selectedFile}
  style={{
    padding: "0.5rem 1.5rem",
    background: uploading || !selectedFile ? "var(--color-disabled)" : "var(--color-primary)",
    color: "var(--on-accent)",
    border: "none",
    borderRadius: "4px",
    cursor: uploading || !selectedFile ? "not-allowed" : "pointer",
    fontSize: "0.9rem",
    fontWeight: 600,
  }}
>
  {uploading ? t("tcgLineImport.uploading") : t("tcgLineImport.uploadButton")}
</button>
```

**問題点**:
- ADR-144 違反: 生 `<button>` + インライン `style` で色値を直書き
- `var(--color-primary)` がデザイントークン外で解決されるリスク（透明背景・白文字の表示崩れ）
- `loading` 状態を `disabled` で代用しており `Spinner` が表示されない

---

## 2. Button コンポーネント金型確認

`frontend/src/components/Button.tsx` より:

- **variant**: `primary | secondary | ghost | danger | outline | tab`
- **size**: `sm | md | lg`（デフォルト `md`）
- **disabled**: props として受け取り `disabled || loading` で HTML disabled を設定 → CSS が自動でグレーアウト
- **loading**: `true` にすると `Spinner` が先頭に表示され `disabled` も true になる
- **loadingText**: loading 中の表示テキスト（省略時は children をそのまま表示）

---

## 3. 変更後の実装

```tsx
<Button
  onClick={handleUpload}
  variant="primary"
  size="sm"
  disabled={!selectedFile}
  loading={uploading}
  loadingText={t("tcgLineImport.uploading")}
>
  {t("tcgLineImport.uploadButton")}
</Button>
```

インポート追加:
```tsx
import { Button } from "../../components/Button";
```

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `Button` の `loading` + `disabled` 組み合わせ時の挙動 | `Button.tsx:52`: `disabled={disabled || loading}` — loading が true なら自動で disabled も true | ✅ 解消済み |
| 2 | `ui-allow` コメントの要否 | 生 `<input>` は既存の `ui-allow` コメントあり。`Button` への置き換えは金型使用のため `ui-allow` 不要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
