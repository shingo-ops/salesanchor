# AY-2s recon: 生 input 6個（在庫フィルタ4・ナレッジ検索2）の現在地

- 基準: origin/main 5ef694629（実装時点）。測定: dev build、preview、DPR2、API モック、幅 1280/1440/375。
- 関連 ADR 検索: `git grep -i "TextField\|raw input" docs/adr/` の結果として ADR-027（i18n）・ADR-067（デザイントークン）・ADR-144（UI 金型ガバナンス）を対象とした。ADR-144 の「生 input 禁止」に沿う適用であり、ADR との食い違いはない。

## 事実（file:line）
- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:287-299`: 生 `<input type="number" min="0" inputMode="numeric" style={{width:"6rem"|"7rem"}} data-testid="inventory-{qty,price}-{min,max}">` が4個。className なし、label 関連付けなし（placeholder のみ）。
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:296`（rules-search）・`:375`（aliases-search）: 生 `<input>`（type 省略）が2個。`style={{ width: SEARCH_WIDTH, maxWidth: "100%" }}`（`frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:72` で SEARCH_WIDTH="30rem"）、onKeyDown で Enter→検索。
- `frontend/src/components/TextField.tsx:41`: TextFieldControl は forwardRef で rest を input へ渡す。type/min/inputMode/style/onKeyDown/data-testid/placeholder/value/onChange は通る。
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:19`: TextFieldControl は既に import 済み。
- 試験 `frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139` は testid 経由で DOM の input を操作する（要素は input のまま）。

## before 実測（6個とも）
border 2px inset rgb(118,118,118)、radius 0、height 19px、font 13.33px、色 黒・背景白＝ブラウザ既定。375 幅で inventory-qty-min / price-min の left が -11.83（既存のはみ出し。doc scrollWidth==clientWidth）。
生データ: `docs/handoff/design-system-recon/evidence-20260910/ay2s-before.json`、前後比較: `docs/handoff/design-system-recon/evidence-20260910/ay2s-diff.md`。

## 残件（今回やらない）
- `<input type="checkbox">` は両ファイルに計10件残る（対象外）。
- label 追加（a11y）は i18n キー新設を伴う別テーマ。
- `scripts/check-ui-governance.js:213-217` は type=number を対象外とする（既知の穴）。
- 375 幅の inventory-qty-min / price-min の left -11.83 は既存。
- GoalSettingPage（AY-2t）、DistributionTargetForm（AY-2u）は別便。
