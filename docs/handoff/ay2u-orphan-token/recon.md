# AY-2u recon（孤児トークン --input-select-min-w）

基準: origin/main 0661b6e5f。引用はリポジトリ相対。

## 事実
- 定義は frontend/src/tokens.css:355 `--input-select-min-w: 280px; /* セレクト最小幅 */` の1か所のみ。
- `git grep -n "input-select-min-w" -- frontend scripts .github` の結果は frontend/src/tokens.css:355 の1件のみ（参照元 0 件）。index.css 等に同名のダーク再定義は無い（同 grep が 1 件のため）。
- 参照元だった `.search-bar input` は AY-2r（docs/handoff/ay2r-search-bar-css/design.md:50 に孤児化の記録）で撤去済み。
- docs の言及: docs/specs/design-system/design.md:4010（「削除は別便で判断」）。
- 週次監査 frontend/scripts/check-unused-tokens.js（.github/workflows/design-token-audit.yml:26 で実行）が変更前に 31 件の未使用を報告し、うち 1 件が当該トークン。
- 生出力: docs/handoff/design-system-recon/evidence-20260910/ay2u-audit-before.txt
