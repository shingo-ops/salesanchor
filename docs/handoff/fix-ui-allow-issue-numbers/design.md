# design: 書式が不正な ui-allow コメント2件の削除（便E1）

- 参照: docs/handoff/fix-ui-allow-issue-numbers/recon.md、ADR-144（`docs/adr/ADR-144-ui-component-governance.md:47-48`）
- 親テーマ: cross-dept-integrity-foundation の K4（金型にない例外・不正な ui-allow を0件にする）
- 承認: 2026-10-02、PO は設計の方向（便A→C→D→E）を承認し、実装・マージ・デプロイまでの完走を指示した（この会話で）。実装カードは親テーマの便E1。

## 変更前 → 変更後
| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/conditions/ConditionsPage.tsx:501` | `{/* ui-allow: alias table is a small inline form, not a data listing */}` | 行を削除 |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:361` | 上と同じ | 行を削除 |

- 選んだ理由: recon の分岐(a)にあたる（直後に生UI部品が無く、例外コメントそのものが不要）。番号を付けて残すと、存在しない例外を記録することになり、ADR-144 の趣旨（例外は実在する生部品にだけ付ける）に反する。
- 触らない範囲: 上の2行以外は一切変えない。同じファイルの有効な ui-allow（`(#3594)` 付き。ConditionsPage の 339・349 行付近）、checkbox、textarea も触らない。
- 画面の挙動: JSX コメントの削除なので、描画結果は変わらない。

## 受入基準
| 基準 | 検証方法 |
|---|---|
| 書式が不正な ui-allow が pages/ で0件 | `git grep -n 'ui-allow:' -- frontend/src/pages` の各行が `/ui-allow:\s+\S+.*\(#\d+\)/` に一致する（不一致0件） |
| 関所の件数が増えていない | `BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js` が成功する |
| 型・lint が通る | `cd frontend && npx tsc --noEmit` と `npm run lint` が成功する |
| 変更は2行の削除だけ | `git diff --stat origin/main...HEAD -- frontend` が 2 files changed, 2 deletions |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）: ADR-144 は「ui-allow は理由と番号の両方が必須」と定めて、例外が根拠なく増えるのを止めている（`docs/adr/ADR-144-ui-component-governance.md:47-48`）。我々への応用: 不要になった例外コメントは残さずに消し、例外の一覧を実態と一致させる。
- 外部事例は不要。理由: 2行のコメント削除で、技術的な選択を伴わないため。

## 維持の仕組み
- 守り手: `scripts/check-ui-governance.js`（ui-allow の書式と、生UI部品の増加を検査する）
- 守り手: `.github/workflows/ui-governance-gate.yml`（main の必須チェック「UI governance gate」）

## リスクと戻し方
- リスク: 実質なし。描画は変わらない。
- 戻し方: この PR を revert する。
