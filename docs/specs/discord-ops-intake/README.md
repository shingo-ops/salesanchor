# Discord 監視通知 → AI 保守運用（discord-ops-intake）

> この文書は何か：Discord に届く知らせ・不具合の報告を、AI（Claude Code）が受け取って調べ、保守運用まで行う仕組みの表紙です。

> **今の決まり（2026-11-24 時点）**: 下の「概要」「境界」は ADR-1009（Superseded）の時代の文で、今は効いていない。今の正本は次の2つ。
> - [ADR-1039](../../adr/ADR-1039-discord-pdca-agent-console.md)（Accepted 2026-10-25）: 不具合受付・誤り報告の2チャンネルを agent-console が読み、件ごとに Opus が直して効果を測る。ADR-1009 の常駐の受付は全部置き換えた（Decision 11）。
> - [ADR-1088](../../adr/ADR-1088-discord-intake-bot-reads-alert-rooms.md)（Accepted 2026-11-24。ADR-1039 Decision 3 を改める）: 受付の Bot（SA Bug Intake）は、知らせの3部屋（🚨急ぎ・📋定期の報告・🛠開発の知らせ）を読むだけにする。AI はこの Bot の鍵の写しで知らせを読み、どの部屋にも書かない。受付が読むのは今までどおり2チャンネルだけ。
> - 2026-11-24 に PO の Mac で、ADR-1009 の常駐の受付（launchd の登録・動いているプロセス）が 0 件であることを確かめた（`launchctl list`・`ps` に discord・intake・channels の名前が無い）。

## 概要（ADR-1009 の時代の文。今は効いていない）

Sales Anchor の監視（Alertmanager・Grafana）は、異常を Discord の監視アラートチャンネルへ webhook で知らせている。そのチャンネルに AI 用の Discord ボットを参加させ、通知が来たら AI が原因を調べて同じチャンネルへ報告する。PO が任せた範囲（委任表）の中では、AI が自分で判断して対応まで行う。

## 境界（ADR-1009 の時代の文。今は効いていない）

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
| 2026-10-25 | ADR-1039 が Accepted。ADR-1009 は Superseded |
| 2026-11-24 | ADR-1088 が Accepted（ADR-1039 Decision 3 を改め、知らせの3部屋を読むだけにした）。Mac に前の受付が 0 件と確かめた |

## 文書

- [ideal-state.md](ideal-state.md) — あるべき姿（PO の言葉）
- [kgi.md](kgi.md) — KGI
- [delegation.md](delegation.md) — 委任表（AI が承認なしで実行してよい操作）
- 子: [recon.md](../../handoff/discord-ops-intake/recon.md) — 現状調査
- 子: [design.md](../../handoff/discord-ops-intake/design.md) — 設計
