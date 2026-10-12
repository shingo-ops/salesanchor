# recon: 書式が不正な ui-allow コメント2件（便E1）

- 基準: origin/main（worktree の HEAD は `19712c906`、BASE_OK）
- 親テーマ: docs/handoff/cross-dept-integrity-foundation/（PR #3942、Draft）の便E1
- 調査: Sonnet（読み取りのみ）。判断: Opus

## 対象
- `frontend/src/pages/conditions/ConditionsPage.tsx:501` — `{/* ui-allow: alias table is a small inline form, not a data listing */}`（`(#番号)` が無い）
- `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:361` — 上と同じ文言（`(#番号)` が無い）

## 事実
- ADR-144 は、ui-allow を「理由と課題番号の両方が必須。番号なしは無効」と定めている（`docs/adr/ADR-144-ui-component-governance.md:47-48`）。
- 関所が使う書式判定は `/ui-allow:\s+\S+.*\(#\d+\)/` である（`scripts/check-ui-governance.js:106-108`）。上の2件はこれに一致しない。
- 除外規則は、検出した要素の開始行と、その直前1行だけを見る（`scripts/check-ui-governance.js:120-124`）。
- コメントの直後の行は、どちらも `<form`（`frontend/src/pages/conditions/ConditionsPage.tsx:502`、`frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:362`）。生 select・生 input（text/search/type 省略）・自作タブのどれにも当たらない（数え方は `scripts/check-ui-governance.js:153-275`）。
- フォームの中身は金型 `TextField`（`frontend/src/pages/conditions/ConditionsPage.tsx:507,513`、`frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:367,373`）と `HeaderButton` だけで、生部品は無い。直後の `<table className="data-table">` は、`/table/` に当たるため自作タブの判定から外れる。
- **結論（事実）: この2行のコメントは、何も除外していない。** 消しても関所の件数は変わらない。

## 未確認
- 関所を BASE と HEAD を指定して実際に走らせた結果は、実装の段階で取る。
