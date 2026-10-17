# AY-5d recon（UIガバナンス検出種別の説明の古い列挙）
基準: origin/main（2026-10-16 git fetch 後）。生出力: /tmp/CC報告ファイル/ssot-radio/ay5d/recon/
## 事実
- scripts/check-ui-governance.js:8-13 は検出対象を5種（select / text系input / checkbox / radio / 自作タブ）と記す。:341-349 countAll と :392 の比較ループも5キー。
- 5種が揃っている説明: docs/CC_UI_GOVERNANCE.md:23-27、docs/adr/ADR-144-ui-component-governance.md:132-145。
- 3種のままの現行説明: .github/workflows/ui-governance-gate.yml:3、docs/BRANCH_PROTECTION_SETUP.md:314、CLAUDE.md:119。
- frontend/CLAUDE.md・AGENTS.md・frontend/AGENTS.md・backend/AGENTS.md に種別列挙は無い（git grep 0件）。
- CLAUDE.md は120行で、check-claude-size.js により行を増やせない。
- 既存ADR検索: ADR-144（UI部品ガバナンス）が対象。新規ADRは不要。
## 対象外
- docs/handoff/ 配下の古い列挙は経緯記録のため直さない。
