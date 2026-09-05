# design — ui-line-import-upload-button（アップロードボタン修正）

**対象ADR**: ADR-144, ADR-027  
**recon**: docs/handoff/ui-line-import-upload-button/recon.md  
**日付**: 2026-09-05  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 同種変更の直近事例: PR #3271（nav-tcg-line-import）— 同じ super-admin エリアで `Button` コンポーネントを使った実装パターン
- ADR-144（UIガバナンス）: 生 `<button>` / 生 `<select>` / 生 `<input>` を禁止し、既存金型（`Button` 等）の使用を義務付け
- ADR-027（i18n強制）: テキスト表示は `t("key")` 経由。今回は変更なし（既存キー使用）
- `company-detail/CompanyContactsTab.tsx:219`: `<Button size="sm" variant="primary" disabled={contactSubmitting}>` — 同一パターン・同一 size の先行事例

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| アップロードボタンがネイビー系（primary）で表示される | Playwright: `button.btn-primary` が存在し visible |
| ファイル未選択時にボタンがグレーアウトされる | Playwright: `button.btn-primary[disabled]` が存在 |
| ファイル選択後はボタンが有効になる | Playwright: `.btn-primary:not([disabled])` が存在 |
| アップロード中は Spinner が表示される | Button の `loading` prop が Spinner を自動表示（Button.tsx:52 実装済み） |
| `tsc --noEmit` が 0 エラーで完了する | CI `frontend-build` ジョブ green |
| `vite build` が成功する（BUILD_EXIT: 0 確認済み） | CI `frontend-build` ジョブ green |
| `check:css-colors` PASSED（hex・rgba 違反なし） | `node scripts/check-css-hardcoded-colors.js` → 0エラー（ローカル確認済み） |

---

## 技術 How・KPI

- KPI: tsc 0エラー / ビルド成功 / CSS色チェック PASSED / guard-hex-increase 増加なし
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx`: `Button` import 追加 + 生 `<button>` を `<Button variant="primary" size="sm">` に置き換え
- インライン style の色値（`var(--color-primary)` / `var(--color-disabled)` / `var(--on-accent)`）を完全削除
- `loading={uploading}` + `loadingText` で uploading 状態を Spinner 表示に昇格
- 上記以外のファイル（index.css / tokens.css / backend / migration）: **一切変更しない**

---

## 弊害・トレードオフ

- なし: `Button` コンポーネントは既存テスト済み金型。ロジック変更なし。
- `size="sm"` を採用した根拠: `CompanyContactsTab.tsx:219` の先行事例と一致。`md`（デフォルト）でも機能するが、ページ内の既存フォームスタイルとの一貫性を優先。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `Button` import 追加 | Generator |
| 2 | 生 `<button>` → `<Button variant="primary" size="sm">` 置き換え | Generator |
| 3 | `check:css-colors` / `check:i18n-missing-keys` / `check:jsx-emoji` / `tsc --noEmit` / `vite build` で確認 | Generator |
| 4 | recon.md / design.md 作成・commit | Generator |
| 5 | PR 起票（--base main） | Generator |

---

## 継続

- 完了後の監視: CI の `guard-hex-increase` がインライン color 増加を検知する。今回は削除のみのため増加なし。
- 次フェーズへの引き継ぎ: なし（単独修正カード）

---

## 維持の仕組み

守り手: `frontend/scripts/check-css-hardcoded-colors.js`（hex・rgba 直書き検査）、ADR-144 UIガバナンスレビュー（PRレビュー時に目視確認）。`Button` コンポーネント自体は `frontend/src/components/Button.tsx` で型定義により規格外 variant/size をコンパイルエラーにする。
