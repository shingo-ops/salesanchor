# 実装カード 段階2 便2 — pages/super-admin の文字だけの読み込み中表示 31件を LoadingBlock へ

- 状態: 草案（Opus 作成）。PO の目視（要確認画面で回る丸）を受けてから実装に渡す
- 起点: origin/main（16000c2d5 以降の最新）。ブランチ `release/loading-mold-super-admin`
- 根拠: recon 生出力 /tmp/CC報告ファイル/loading-bin2-recon/（targets.tsv・context.txt・css.txt・tests.txt・gov-counts.txt）
- 対象ADR: ADR-144（金型）・ADR-067（トークン）・ADR-027（i18n）

## 1. やること（置換の規則）
- 規則A: 読み込み中の文字だけを持つ要素（`<p>` / `<div>`。インライン style や class を含む）を、要素ごと `<LoadingBlock />` に置き換える。label は渡さない（3つのキーは日英とも common.loading と同じ文言: recon 確認済み）
- 規則B: `role="status"` 付きの `<p>` も同じく置き換える（Spinner 側が role="status" を持つ）
- 規則C: 三項・`&&` の形はそのまま残し、表示部分だけ差し替える。`return <p ...>` は `return <LoadingBlock />`
- import は各ファイルで `import { LoadingBlock } from "<相対>/components/loading";` を1行（既存 import 群の末尾）
- 上の規則に当てはまらない形が出たら、その場で止めて BLOCKED: で報告する

## 2. 対象 31件（file:line は origin/main 16000c2d5 時点。ずれたら止まる）
| # | ファイル:行 | 今 | 後 |
|---|---|---|---|
| 1-4 | components/AnalysisDashboardPanel.tsx:539,557,673,1712 | `<p className="analysis-dashboard-empty">{t("analysisRules.dashboard.loading")}</p>` | `<LoadingBlock />` |
| 5 | components/LlmUsageSection.tsx:408 | 同上（return） | `return <LoadingBlock />;` |
| 6 | AnalysisRulesPage.tsx:119 | `<p style={{ padding: "var(--space-4)" }}>{t("common.loading")}</p>` | `<LoadingBlock />` |
| 7-11 | Condition/NoteMaster/StatusMaster/Supplier/Unit ImportPage.tsx:131 | `loading ? <p>{t("common.loading")}</p> : …` | `loading ? <LoadingBlock /> : …` |
| 12 | ProductCategoriesImportPage.tsx:137 | 同上 | 同上 |
| 13 | TcgProductImportPage.tsx:13 | 同上 | 同上 |
| 14 | ExtractionPromptConfigTab.tsx:113-115 | `<div style={{…}}>{t("common.loading")}</div>` | `<LoadingBlock />` |
| 15 | FxRatePage.tsx:72 | `return <div className="page">{t("common.loading")}</div>;` | `return <LoadingBlock />;` |
| 16 | FxRatePage.tsx:118 | `<div>{t("common.loading")}</div>` | `<LoadingBlock />` |
| 17-18 | ViewerAccountsPage.tsx:317 / :460 | FxRatePage と同じ2形 | 同上 |
| 19-20 | ViewerTemplatesPage.tsx:163 / :214 | 同上 | 同上 |
| 21 | SupplierExtractionRulesPage.tsx:540 | `loadingDetail && <p>{t("common.loading")}</p>` | `loadingDetail && <LoadingBlock />` |
| 22 | SupplierExtractionRulesPage.tsx:934 | `<p>{t("common.loading")}</p>` | `<LoadingBlock />` |
| 23-24 | components/DbViewerPanel.tsx:454-456 / :555-557 | style 付き `<p>` 3行 | `<LoadingBlock />` |
| 25 | components/ExtractionErrorLogPanel.tsx:〜374-383 | style 付き `<p>`（複数行） | `<LoadingBlock />` |
| 26 | components/ProductMasterPanel.tsx:116 | `loading ? <p>{t("common.loading")}</p> : …` | `loading ? <LoadingBlock /> : …` |
| 27-28 | components/SoldOutResultsPanel.tsx:79 / :91 | `<p role="status">{t("common.loading")}</p>` | `<LoadingBlock />` |
| 29-31 | TcgLineImportPage.tsx:251,510,597 | `<p style={{ color: "var(--text-secondary)" }}>{t("tcgLineImport.loading")}</p>` | `<LoadingBlock />` |

## 3. 試験の直し（1か所）
- `frontend/src/pages/super-admin/components/ProductMasterPanel.test.tsx:126`
  - 今: `expect(screen.queryByRole("status")).toBeNull();`
  - 後: `expect(screen.queryByText(/^Products: \d+/)).toBeNull();`
  - 理由: この試験（:112-128 AC7）の意図は「古い要求の失敗で alert も件数表示も出さない」こと。置換後は読み込み中の丸が role="status" を持つため、件数表示（:100 `findByText("Products: 2")` と同じ文面）を直接見る形に変える。:125 の alert なしの確認は残す

## 4. 触らない範囲
- ボタン内の三項13件・"uploading"・"errorLoading"・TcgDistributionPage:25（後の便）
- CSS（.analysis-dashboard-empty は空表示と共用、.page は共用。消さない）
- 辞書: `analysisRules.dashboard.loading`・`tcgLineImport.loading` は参照0になっても消さない（辞書の整理は別便）
- components/loading/ の金型・scripts/ の検査

## 5. 検証（生出力を /tmp/CC報告ファイル/loading-stage2-bin2/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象31件が0件になる | `node scripts/check-ui-governance.js` の loadingText 件数: super-admin 48→17 |
| 試験が通る | `npx vitest run src/pages/super-admin` 全件 pass |
| 型・lint | `npx tsc --noEmit` エラー0、`npx eslint` 変更ファイル 0 |
| i18n | `node scripts/check-i18n-missing-keys.js` exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象21ファイル＋試験1＋docs だけ |

## 6. 想定分岐
- 行番号がずれている → 文面で一致を確認し、一致すれば進めて報告に新旧行を書く。一致しなければ止まる
- 置換で他の試験が落ちる → 直さずに BLOCKED: で落ちた試験名と生出力を報告
- e2e tcg-product-import.spec.ts:63/:86 は排他の三項で重ならない（コード読み）。CI の e2e が落ちたら止まる
