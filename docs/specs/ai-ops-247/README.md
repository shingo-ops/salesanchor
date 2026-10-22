# AI 保守運用 24 時間化（ai-ops-247）

> この文書は何か：不具合が起きたら、システムが知らせて応急処置をし、AI が人の代わりに調べて直し、振り返りで賢くなっていく仕組みの表紙です。

親: [docs/specs/README.md](../README.md)

## 概要

監視（報知器）が不具合を見つけたら、①システムが Discord に知らせ、②システムが決まった応急処置を自動で行い、③AI（Claude Code）が呼ばれて調査・止血・修理を行い、④毎回の振り返りで報知器・応急処置・AI の手順を改善する。夜間・休日も PO の Mac に頼らずに動く。

## 既存の discord-ops-intake との関係

[discord-ops-intake](../discord-ops-intake/README.md)（ADR-1009）は「Discord の通知を PO の Mac 上の常駐セッションが受ける」仕組みで、Mac が眠ると動かない。本テーマはその上位にあたり、次を足す。

- 報知器そのものの感度と精度（今は計器の無いルールや、鳴りっぱなしのルールがある）
- 人を介さない応急処置（今は unhealthy の自動再起動が無い）
- Mac に頼らない AI の起動（Claude Code の公式クラウド routines を本命にする）
- 障害記録と月次成績表（PDCA）

discord-ops-intake は本テーマの「予備（C）」として残し、構築と動作確認まで完了させる（PO 条件）。

## 境界

- 対象: Sales Anchor 本番（prod1 アプリ・prod2 監視）の不具合の検知・応急処置・AI 対応・振り返り
- 対象外: 新機能の開発、LP、Legacy（jarvis-claude.uk）
- 越えない線: 不可逆操作（データ削除・secrets・お金）は AI が止まり、PO に承認を求める（[kgi.md](kgi.md)「変えない約束」）

## ステータス

| 日付 | 状態 |
|---|---|
| 2026-10-13 | あるべき姿・KGI 6 件 PO 承認（「Cも予備で構築して動作確認まで完結させる、その条件付きでy」）。recon・design・ADR-1012 草案作成。実装未着手 |
| 2026-10-22 | 延長: さくらメンテ停止（12:02〜12:54 JST）の再発防止 outage-recovery-watch。KGI 3件 PO 承認（PO 返信「1」）。設計済み・実装未着手 |

## 文書

- [ideal-state.md](ideal-state.md) — あるべき姿（PO の言葉）
- [kgi.md](kgi.md) — KGI（PO 承認済み）
- 子: [recon.md](../../handoff/ai-ops-247/recon.md) — 現状調査
- 子: [design.md](../../handoff/ai-ops-247/design.md) — 設計
- 子（延長）: [outage-recovery-watch/design.md](../../handoff/outage-recovery-watch/design.md) — さくら予告メール見張り・復旧後点検・時計ずれ警報
- ADR: [ADR-1012](../../adr/ADR-1012-ai-ops-247.md)
