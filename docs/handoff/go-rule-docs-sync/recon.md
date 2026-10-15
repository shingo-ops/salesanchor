# recon: 規則文書の「GO は PO 単独・人がマージ」を今のルールにそろえる

基準: origin/main（2026-10-15 取得）。検索の生出力は手元の /tmp/CC報告ファイル/go-record-cleanup/（repo には載せない）。

## 既存 ADR の検索
- docs/adr/ADR-136-cc-bot-github-identity.md: 承認フロー v2。GO 権限は PO 単独（決定 2026-06-13）。
- docs/adr/ADR-1003-go-delegation-to-opus.md: GO 発行を例外を除き Claude Opus 設計担当へ常時委譲（2026-09-29 Accepted）。ADR-136 の「PO 単独」を上書きする。
- docs/handoff/go-record-transcription/opus-delegation.md: 委任の正式記録と GO 記録の書式（GO発行者: POの委任に基づくClaude Opus発行）。

## 現在地（食い違い・file:line は origin/main）
- docs/adr/ADR-136-cc-bot-github-identity.md:49・:69・:106 に「PO 単独」。ADR-1003 による上書きの注記が無い。
- docs/STANDARD-WORKFLOW.md:92・:135・:138・:140・:142 に「Shingo の GO 記録が必須」「認可された人間の承認」「PO の GO」「GO: Shingo」。
- docs/BRANCH_PROTECTION_SETUP.md:232 に「危険変更のみ人間承認必須」。
- .github/PULL_REQUEST_TEMPLATE.md:40 に「認可承認者のApprove」。
- docs/ai-agents/executor-preamble.md:54 に「PO の GO を受領」。
- docs/ai-agents/design-partner.md:215 に「POの GO #PR番号 発話を転記」。
- .claude/agents/governance.md:3・:9・:12 に「human merge」。

## 見つけた危険（この PR では直さない）
- scripts/check-process-artifacts.js:357-365 は GO発行者欄を部分一致（includes）で判定する。発行者欄に「Shingo」「shingo-ops」を含めると、ADR-1003 の例外（DROP を含む migration 等）でも PO 本人の GO と判定される見込み（コードを読んだ範囲。実行はしていない）。判定の修正は scripts の変更なので別便。当面は GO記録の発行者欄に委任の書式だけを書き、Shingo・shingo-ops を入れない運用で守る。

## 触らないもの（過去の記録）
- docs/specs/**（各テーマの kgi.md・過去便）、ADR-114・ADR-135・ADR-1006・ADR-1007、docs/specs/transaction-flow/design.md、evidence-registry。決定当時の記録として残す。
- docs/handoff/go-record-transcription/opus-delegation.md（別の PR #4293 が同じファイルを変更中のため。Approve の委任の追記は自動の安全判定に止められたため、この PR では扱わない）。
- docs/BRANCH_PROTECTION_SETUP.md:138 付近（緊急 break-glass の手順で、GO の権限の話ではない）。

## PO 発言
- 2026-10-15「古い記録でGO記録は人間に頼むという記録があるのであれば更新して古い記録は消しておいて、勘違いするかもしれないから」
- 2026-10-15「PR #4278 に shingo-ops 名義で Approve を付けてください。→この権限はOPUSに与えるのでOPUSが判断してつけるように指示を出してくれ　。恒久的に権限委譲する」
