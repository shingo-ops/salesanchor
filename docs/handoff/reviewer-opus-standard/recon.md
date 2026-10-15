# recon: 審査担当を Fable から Opus へ（2026-10-15）

origin/main 起点（release/reviewer-opus-standard）。生出力: /tmp/CC報告ファイル/reviewer-opus/grep-before.txt・grep-after.txt。

## 既存 ADR の検索
`git grep -i fable docs/adr/` で該当: ADR-1011、ADR-1015、ADR-1016。docs/adr/FEATURE-INDEX.md に審査担当の項目はない。

## 審査担当を Fable と定めていた規則（変更前）
- .claude/agents/architect.md:4 `model: fable`
- .claude/agents/reviewer.md:4 `model: fable`
- AGENTS.md:59 「Fable 審査 APPROVE で代える」
- docs/STANDARD-WORKFLOW.md:23 「Fable 審査 APPROVE で進む」
- docs/ai-agents/design-partner.md:106 「Fable 審査 APPROVE で代える」
- .github/PULL_REQUEST_TEMPLATE.md:37 「Fable 審査記録: review-fable.md」
- docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:24・30・40・72
- docs/adr/ADR-1011-permission-self-maintenance.md:60 「Reviewer（Fable）」

## 残すもの（過去の事実の記録）
- docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:51・56、docs/adr/ADR-1016-*.md:6（当時の審査の経緯）
- docs/specs/design-system/design.md の各便の審査記録、docs/handoff/ 配下の review-fable*.md、docs/specs/*/track-record.md
- docs/specs/agent-complete-design/（design.md:143-168、kgi.md:19・26・47、README.md:45）は「設計パートナー（Fable）」という別の役割の記述で、審査担当の規則ではないため本便の対象外
