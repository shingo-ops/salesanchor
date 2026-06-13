# design — UI標準化 PR-B (Company系3ファイル)

**対象ADR**: ADR-067  
**recon**: docs/handoff/ui-std-pr-b/recon.md  
**日付**: 2026-06-14  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

PR-A（feature/morimoto/ui-std-pr-a）で Contact系3ファイルに同方針を適用済み。
Button/TextField/Select/Textarea の置換パターンとcheckbox/radio残置方針はPR-Aで確立・検証済み。
Storybook カタログ（ADR-067）の全コンポーネント Stories が通過確認済みのため、今回は過去事例としてPR-Aの結果をそのまま適用する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| raw `<button>` が0件 | `rg "<button" frontend/src/components/MergeCompanyModal.tsx` |
| raw `<button>` が0件 | `rg "<button" frontend/src/pages/company-detail/CompanyAddressModal.tsx` |
| raw `<button>` が0件 | `rg "<button" frontend/src/pages/company-detail/CompanyDetailPage.tsx` |
| raw `<select>` が0件 | `rg "<select" frontend/src/pages/company-detail/CompanyAddressModal.tsx` |
| raw `<textarea>` が0件 | `rg "<textarea" frontend/src/components/MergeCompanyModal.tsx` |
| btn-* className直書きなし | `rg 'className.*btn-' 対象3ファイル` |
| TypeScript コンパイル成功 | `cd frontend && tsc --noEmit` |
| i18n キー変更なし | t() 呼び出し diff — 追加・削除なし |

---

## 技術 How・KPI

- KPI: raw HTML 要素 0件（Button/TextField/Select/Textarea で完全置換）
- 技術選択: Button variant マッピング（primary/secondary/ghost/danger）、Select の options 配列インライン定義

---

## 弊害・トレードオフ

- Button の comp-btn base class がタブ見た目を壊す可能性 → variant="ghost" は btn-ghost のみ付与、`.tab`/.`.tab.active` CSS は残存するため影響なし
- Select wrapping div が form-row レイアウトを崩す可能性 → label なし使用（PR-A検証済みパターン）で回避
- TextField wrapping div が既存 field-error span と二重表示になる可能性 → telephone の error prop 統合で解決

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Hikky-dev |
| 2 | MergeCompanyModal.tsx 置換（6要素） | Hikky-dev |
| 3 | CompanyAddressModal.tsx 置換（15要素） | Hikky-dev |
| 4 | CompanyDetailPage.tsx 置換（14要素） | Hikky-dev |
| 5 | rg 検証・PR作成 | Hikky-dev |

---

## 継続

- 完了後の監視: Visual Regression（Chromatic UI Tests）で目視確認
- 次フェーズへの引き継ぎ: checkbox/radio 標準コンポーネント実装時に残置箇所を置換
