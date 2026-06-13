# design — UI標準化 PR-B (Company系3ファイル)

## 目的

PR-A（Contact系: ContactModal / ContactsTab / ConvLogModal）で確立した
Button / TextField / Select / Textarea 置換方針を Company系3ファイルへ横展開する。

参照: recon.md (同ディレクトリ)

## 変更スコープ

| ファイル | 変更種別 | 変更なし |
|---------|---------|---------|
| MergeCompanyModal.tsx | Button/TextField/Textarea import追加 + 6要素置換 | API・ロジック全て |
| CompanyAddressModal.tsx | Button/TextField/Select import追加 + 15要素置換 | API・ロジック全て |
| CompanyDetailPage.tsx | Button import追加 + 14要素置換 | API・ロジック全て |

## 判断基準テーブル

| 基準 | 検証方法 | 期待値 |
|------|---------|--------|
| raw `<button>` が残らない | `rg "<button" frontend/src/components/MergeCompanyModal.tsx` | 0件 |
| raw `<button>` が残らない | `rg "<button" frontend/src/pages/company-detail/CompanyAddressModal.tsx` | 0件 |
| raw `<button>` が残らない | `rg "<button" frontend/src/pages/company-detail/CompanyDetailPage.tsx` | 0件 |
| raw `<input` (text/email/etc.) が残らない | `rg "<input" ... \| grep -v "type=\"checkbox\"\|type=\"radio\""` | 0件 |
| raw `<select>` が残らない | `rg "<select" frontend/src/pages/company-detail/CompanyAddressModal.tsx` | 0件 |
| raw `<textarea>` が残らない | `rg "<textarea" frontend/src/components/MergeCompanyModal.tsx` | 0件 |
| `btn-primary`/`btn-sm` クラス直書きなし | `rg "className.*btn-" 対象3ファイル` | 0件 |
| TypeScript コンパイル成功 | `cd frontend && npx tsc --noEmit` | エラーなし |
| i18n キー変更なし | `rg "t(" 対象3ファイル` の diff | 追加・削除なし |

## 置換方針

### variant マッピング

| 旧クラス | Button variant |
|---------|---------------|
| `btn-primary` / `className="btn-sm btn-primary"` | default (primary) |
| `btn-sm` (secondary相当) | `variant="secondary"` |
| `btn-danger` | `variant="danger"` |
| `tab ...` (タブボタン) | `variant="ghost" className="tab ..."` |
| なし (plain button) | `variant="secondary"` |

### Select options定義

CompanyAddressModal の billing/delivery select は options 配列をインライン定義:
```tsx
options={[
  { value: "billing", label: t("companies.billing") },
  { value: "delivery", label: t("companies.delivery") },
]}
```

### telephone エラー表示統合

旧: `<input>` + `{addrPhoneError && <span className="field-error">...}` の2要素  
新: `<TextField error={addrPhoneError ?? undefined}>` の1要素（TextFieldの error prop に統合）

### style CSS変数の扱い

コピーリンクボタンの `style={{ marginLeft: "var(--spacing-2)" }}` は CSS変数（ADR-067準拠）のため保持。

### タブボタン

`<button className="tab active">` → `<Button variant="ghost" className="tab active">`  
Buttonが生成する `btn-ghost` と既存 `.tab` / `.tab.active` CSS が共存する（className merge済み）。

## 残置項目

| 要素 | ファイル | 理由 |
|------|---------|------|
| `<input type="checkbox">` | CompanyAddressModal.tsx:140 | Checkbox標準コンポーネント未実装 |
| `<input type="radio">` | MergeCompanyModal.tsx:217-225 | Radio標準コンポーネント未実装 |

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| Button の `comp-btn` base classがタブ見た目を壊す | `variant="ghost"` は `btn-ghost` のみ付与。`.tab` / `.tab.active` CSSは残存するため影響なし |
| Select wrapping div (`comp-field`) が form-row レイアウトを崩す | form-row内で Select を label なし使用（PR-A検証済みパターン）|
| TextField wrapping div が既存 field-error span と二重表示 | telephone のみ error prop 統合で span を削除 |

## 外部事例

PR-A (feature/morimoto/ui-std-pr-a) で同方針を Contact系3ファイルに適用済み。
Storybook カタログ（ADR-067）の Button/TextField/Select/Textarea Stories が通過確認済み。
