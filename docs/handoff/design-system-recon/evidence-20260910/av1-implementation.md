# AV-1 実装記録（SelectControl 本体拡張）

設計: docs/specs/design-system/design.md §AV。カード: CARD-AV1-SELECT-BODY-01（card-lint exit0、L24警告のみ）。担当: 設計/検収 Opus、実装 Sonnet。PR #3931。

## 対象と結果

- 実装commit a5899e4eb6cfe2618b160e043fd896f569962bba（土台 f42bc163d、origin/main 分岐点 55d99a97e）。
- 変更した製品ファイルは4つのみ: frontend/src/components/Select.tsx、FormField.css、Select.stories.tsx、Select.test.tsx（新規）。利用ページ・翻訳・依存・CI・backend・DB・API の変更0。
- SelectControl: options/children 排他 union 型、forwardRef（displayName=SelectControl）、indicator="default"|"none"（none で class comp-select--no-indicator）。options モードの出力・class 組立順は不変。Select（ラベル付き）の公開propsは children を受けない型にした（既存利用の非自己閉じタグ0件を AST で確認: Select 69、SelectControl 22 利用）。
- FormField.css: indicator=none の3規則のみ追加（var(--space-2/3/4) のみ、新規トークン0）。
- Story: ChildrenMode・NoIndicator を追加（設計者レビューで新規 story の幅直書き 18rem を除去）。

## 検証（実装担当の実行結果。設計者は差分全文と試験本文を直接読取して検収）

| 基準 | 結果 |
|---|---|
| options モード出力の固定 | 変更前コードで74試験を作成・成功→変更後も同試験成功（期待値不変）。innerHTML 完全一致の試験2件を含む |
| 新契約 | Select.test.tsx 合計92試験成功（children 4型、object/callback ref、native属性透過、indicator 両appearance、@ts-expect-error による型排他） |
| 型 | tsc --noEmit exit0、npm run build（tsc && vite build）exit0 |
| 品質 | eslint --max-warnings=0（所有3ファイル）exit0、npm run check:all exit0、build-storybook exit0、git diff --check exit0 |
| 全体試験 | npm run test:coverage 並列実行で20ファイル89件が主に 5000ms タイムアウト（Select.test.tsx 由来0）。--maxWorkers=1 で再実行し 66ファイル857試験全成功、exit0（§AU と同じ単一worker方式）。 |

## 経過・逸脱の記録

- 実装担当が tsc -b の生成物 tsbuildinfo 2件を rm で除去（設計者の mv 指示より前）。追跡対象外の生成物で成果物への影響なし。
- commit が worktree-only-guard に一度停止（cd 接頭辞のない複合コマンド）。guards/00-common.md の規定形（各コマンドを cd 作業台 && で開始）で再実行し成功。ガードの解除・迂回なし。
- 本番DBバックアップ確認: 本PRはDB/データ変更なしのため「該当なし」。制限鍵では確認不能（ForceCommand が監視4コマンド固定）と実測し、無制限鍵は不要と判断して使用していない。

## 未検証・限界

- 画面の目視・本番ログイン操作は未実施（利用ページ変更0のため本便で画面変化は想定しない）。
- 利用ページの生 select 80件は未移管（AV-2）。
