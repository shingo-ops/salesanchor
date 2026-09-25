branch: release/dashboard-upload
date: 2026-09-25
recon: docs/handoff/dashboard-upload/recon.md

## 目標

ダッシュボード ImportTabContent に、TcgLineImportPage のアップロードフォームを移植し、インポートタブ内でファイルのアップロードが完結できるようにする。

## 参照 ADR

- ADR-027 (`docs/adr/ADR-027-ui-internationalization.md`): 全UI文字列は t("key") 経由
- ADR-144 (`docs/adr/ADR-144-ui-component-governance.md`): Button / Badge / Card 金型のみ使用、色直値禁止

## 変更内容

### 追加したUI要素 (ImportTabContent 内)

1. ドロップゾーン (drag-and-drop + file input ref)
2. ウィンドウ時間入力 (`window_hours`)
3. アップロードボタン (Button コンポーネント)
4. アップロード結果表示 (Badge でレビューステータス表示 + レビューページへの遷移)
5. 成功後のサマリー自動再取得

### SSOT

APIエンドポイントは既存 `/tcg/line-import` を共用。独自エンドポイントは追加しない。

### i18n キー追加

ja.json / en.json に同一キーを追加:
- `import.uploadTitle` / `import.dropZoneText` / `import.windowHours` / `import.uploadButton`
- `import.uploadSuccess` / `import.reviewStatus` / `import.goToReview` / `import.uploadError`
- `import.uploadHint` / `import.uploading`

### デザイントークン

CSS は `var(--color-*)` / `var(--space-*)` / `var(--radius-*)` のみ使用。色直値なし。

### 守り手

- `frontend/scripts/check-i18n-missing-keys.js` — i18nキー整合性
- `frontend/scripts/check-css-hardcoded-colors.js` — 色直値禁止
- `lint-staged` / ESLint — コード品質

## 基準・検証方法

| 基準 | 検証方法 |
|------|---------|
| ImportタブにドロップゾーンとアップロードボタンがUIに表示される | Playwright: ダッシュボード→Importタブを開き要素を確認 |
| ファイルアップロード成功後にレビューステータスが表示される | Playwright: ファイルをドロップしアップロードを実行 |
| 全UIテキストがi18nキー経由 | `node frontend/scripts/check-i18n-missing-keys.js` が 0 エラー |
| CSSがデザイントークンのみ | `node scripts/check-css-hardcoded-colors.js` が 0 エラー |

## 外部・過去事例の参照と我々への応用

- `frontend/src/pages/super-admin/TcgLineImportPage.tsx` — アップロードロジックの移植元（同一 /tcg/line-import API エンドポイント・ドロップゾーン・window_hours パラメータ）。ページを新設せず既存エンドポイントを共用することでSSOTを維持する。

## 維持の仕組み

守り手: frontend/scripts/check-i18n-missing-keys.js（i18nキー整合性）/ frontend/scripts/check-css-hardcoded-colors.js（色直値禁止）/ lint-staged（コード品質）
