# design: fix-import-page-padding

- recon: docs/handoff/fix-import-page-padding/recon.md

## 変更概要
TcgLineImportPage の hub-content div に `padding: var(--space-6)` を追加する。

## 根拠
PR #3645 で AnalysisRulesPage の hub-content にパディングを適用したが、独立したページである TcgLineImportPage は対象外だった。同じサイドバーレイアウト（hub-shell / hub-content）を使うため、同一のデザイントークンを適用して視覚的一貫性を確保する。

## 変更ファイル
| ファイル | 変更内容 |
|--------|---------|
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:282` | hub-content の style に `padding: "var(--space-6)"` を追加 |

## ADR参照
- `docs/adr/ADR-067-design-token-enforcement.md` — デザイントークン使用（`var(--space-6)`）
- `docs/adr/ADR-144-ui-component-governance.md` — UIガバナンス

## KGI/KPI
| 基準 | 検証方法 |
|-----|---------|
| インポートページのコンテンツが左端から `var(--space-6)` 離れて表示される | ブラウザでページを開き目視確認 |
| TypeScript コンパイルエラーなし | `npx tsc --noEmit` PASS |
| ESLint エラーなし | `npx eslint src/pages/super-admin/TcgLineImportPage.tsx` PASS |

## 外部・過去事例の参照と我々への応用
- 同リポジトリ内の `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` が同一パターン（hub-content に var(--space-6)）を実装済み（PR #3645）。
- 同じ hub-shell / hub-content レイアウトを持つページ間での一貫性適用。

## 弊害
なし（単一ファイルの style prop 追加のみ）

## 戻し方
`padding: "var(--space-6)"` を削除するだけで元に戻る。

## 維持の仕組み
- 守り手: UI governance gate（`.github/workflows/`）、TypeScript/ESLint 静的チェック
- AnalysisRulesPage と同じ `var(--space-6)` を使用しているため、デザイントークン変更時は両ページへ自動適用される。
- ESLint + TypeScript による静的チェックで回帰防止。
