# design — nav-tcg-line-import（サイドメニューへのインポート追加）

**対象ADR**: ADR-027, ADR-144  
**recon**: docs/handoff/nav-tcg-line-import/recon.md  
**日付**: 2026-09-05  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 同種変更の直近事例: #3271（nav-tcg-supplier-quality）— `saasAdminItems` への1項目追加・翻訳キー追加のみで完結したPR。同一パターンで実装する。
- ADR-027（i18n強制）: UI文字列は必ず `t("key")` 経由。`labelKey` に直接文字列を入れず `nav.superAdminTcgLineImport` キーを使う。
- ADR-144（UIガバナンス）: 既存 `NavItem` 型を流用。生select/生inputなし。新コンポーネント新設なし。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| SaaS管理者メニューに「インポート」が先頭に表示される | Evaluator（Playwright: `nav[aria-label="saas-admin"] li:first-child` のテキストが「インポート」） |
| 既存2項目（解析精度管理・為替レート管理）が保持されている | Playwright: サイドバー要素に `superAdminTcgSupplierQuality` / `superAdminFxRate` が存在 |
| `frontend/scripts/check-i18n-missing-keys.js` が PASSED | `frontend/scripts/check-i18n-missing-keys.js` → 0エラー |
| `tsc --noEmit` が 0 エラーで完了する | CI `frontend-build` ジョブ green |
| `vite build` が成功する | CI `frontend-build` ジョブ green |
| ja.json / en.json に `superAdminTcgLineImport` キーが追加されている | `grep "superAdminTcgLineImport" frontend/src/locales/*.json` → 2件（ja/en） |

---

## 技術 How・KPI

- KPI: `tsc` エラー 0件 / ビルド成功 / i18n-missing-keys PASSED
- `DesktopShell.tsx:190`: `saasAdminItems` の先頭に1項目追加（ADR-144 UIガバナンス準拠・既存 `NavItem` 型を使用）
- `locales/ja.json`: `nav.superAdminTcgLineImport` = `"インポート"` を追加
- `locales/en.json`: `nav.superAdminTcgLineImport` = `"Import"` を追加
- `App.tsx` / backend / migration: **一切変更しない**（ルートは #3285 で追加済み）
- `frontend/src/config/routeTitles.ts`: **変更しない**（`frontend/scripts/check-nav-title-sync.js` の `EXCLUDE_DIRS: super-admin` により対象外）

---

## 弊害・トレードオフ

- なし: 既存2項目を削除・変更しない。新規1項目の追加のみ。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `DesktopShell.tsx` saasAdminItems 先頭に `tcg-line-import` 追加 | Generator |
| 2 | `locales/ja.json` / `en.json` に `superAdminTcgLineImport` キー追加 | Generator |
| 3 | `frontend/scripts/check-i18n-missing-keys.js` / `frontend/scripts/check-nav-title-sync.js` / `tsc` / `vite build` で確認 | Generator |

---

## 継続

- 完了後の監視: ビルド（`tsc`）がキー参照を静的に検証する。追加の監視設定不要
- 次フェーズへの引き継ぎ: インポートページの UI 実装は別カード

---

## 維持の仕組み

守り手: frontend/scripts/check-i18n-missing-keys.js（ja/en のキー数一致を検査）メニュー項目数をテストで固定する仕組みは現時点で存在しないため、項目増減はPRレビュー時に目視確認する。
