# design: fix-import-page-padding

## 変更概要
TcgLineImportPage の hub-content div に `padding: var(--space-6)` を追加する。

## 根拠
PR #3645 で AnalysisRulesPage の hub-content にパディングを適用したが、独立したページである TcgLineImportPage は対象外だった。同じサイドバーレイアウト（hub-shell / hub-content）を使うため、同一のデザイントークンを適用して視覚的一貫性を確保する。

## 変更ファイル
| ファイル | 変更内容 |
|--------|---------|
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:282` | hub-content の style に `padding: "var(--space-6)"` を追加 |

## ADR参照
- ADR-067: デザイントークン使用（`var(--space-6)`）
- ADR-144: 既存コンポーネント金型使用

## KGI/KPI
| 基準 | 検証方法 |
|-----|---------|
| インポートページのコンテンツが左端から `var(--space-6)` 離れて表示される | ブラウザでページを開き目視確認 |
| TypeScript コンパイルエラーなし | `npx tsc --noEmit` PASS |
| ESLint エラーなし | `npx eslint src/pages/super-admin/TcgLineImportPage.tsx` PASS |

## 外部事例
既存実装: AnalysisRulesPage.tsx（同リポジトリ）が同一パターンで実装済み。

## 弊害
なし（単一ファイルの style prop 追加のみ）

## 戻し方
`padding: "var(--space-6)"` を削除するだけで元に戻る。
