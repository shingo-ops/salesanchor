# Discord 監視通知 → AI 保守運用（discord-ops-intake）

> この文書は何か：サーバー監視の通知が Discord に届いたら、AI（Claude Code）がそれを受け取って調べ、保守運用まで行う仕組みの表紙です。

## 概要

Sales Anchor の監視（Alertmanager・Grafana）は、異常を Discord の監視アラートチャンネルへ webhook で知らせている。そのチャンネルに AI 用の Discord ボットを参加させ、通知が来たら AI が原因を調べて同じチャンネルへ報告する。PO が任せた範囲（委任表）の中では、AI が自分で判断して対応まで行う。

## 境界

- 対象: 監視アラートチャンネルの、監視通知 webhook（第1段）
- 対象外: PR 通知・外部メール通知・アプリ内エラー通知（外部の人が書いた文字が入るため。第2段以降で個別に判断）
- AI が動く場所: PO の Mac 上の常駐セッション（Claude Code channels 機能・研究プレビュー）

## ステータス

| 日付 | 状態 |
|---|---|
| 2026-10-12 | 手順書 C-1（channels の利用可否）合格 |
| 2026-10-13 | C-3（DM 往復）合格。公式プラグインは webhook 投稿を捨てることを実測で確定 |
| 2026-10-13 | あるべき姿・KGI 提示（KGI-3 は PO 修正反映）・recon・design 草案作成 |
| 2026-10-13 | ADR-1009 の設計 PR #4185・実装 PR #4188 を main にマージ |
| 2026-10-22 | ADR-1039（Proposed）で全部置き換える予定。ADR-1039 が Accepted になったら受付をやめる |

## 文書

- [ideal-state.md](ideal-state.md) — あるべき姿（PO の言葉）
- [kgi.md](kgi.md) — KGI
- [delegation.md](delegation.md) — 委任表（AI が承認なしで実行してよい操作）
- 子: [recon.md](../../handoff/discord-ops-intake/recon.md) — 現状調査
- 子: [design.md](../../handoff/discord-ops-intake/design.md) — 設計
