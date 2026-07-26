# ADR-150: エージェント担当領域を「窓」の明示リストで管理する

## Status
Proposed

## 背景

複数エージェント（設計パートナー／実装役／Codex）が同一リポジトリを触る体制で、担当領域が暗黙だと重複作業と抜けが生じる。recon 実測で、外部接続系ファイルが backend/app/services/ と backend/app/discord_gateway/ に分散し API 層と重複していることを確認した（担当の重なり）。窓同士は掲示板（正本文書）経由でのみ整合し、直接通信しない前提で体制を設計している。

## 決定

エージェントの担当領域を「8つの窓」に分け、各窓の担当パスを明示リストで持つ。除外規則も全窓共通で1箇所に置く。この割当を track-record 関所で機械検知する。設計の詳細は docs/specs/agent-complete-design/design.md。

## 根拠

- docs/handoff/agent-complete-design/recon.md:484-491 外部接続が services/ と discord_gateway/ に分散し API と重複
- docs/handoff/agent-complete-design/recon.md:598 窓同士は掲示板経由のみで整合・直接通信なし
- docs/specs/agent-complete-design/design.md #1「領域の窓」・#2「窓の除外規則」

## 関連

- docs/specs/agent-complete-design/design.md
- docs/specs/agent-complete-design/README.md
- docs/STANDARD-WORKFLOW.md
