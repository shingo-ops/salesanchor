# ADR-124: SOP ヘルスレポーター（定量監視ダッシュボード）

## ステータス
採択（提案日: 2026-06-09）

## 文脈（なぜ）
- ADR-121 で process-artifacts gate を設置したが、「守られているか」を定量計測する仕組みがなかった。
- 外部エビデンス: 改善活動の約7割が持続しない原因は「遵守状況の可視化不足」（WHO 手術チェックリスト成功例と効果ゼロ例の対比）。
- 自社の recon（`docs/handoff/sop-kpi2-phase2/recon.md`）で「5 指標すべて GitHub API で取得可能」と確認済み。

## 決定（何を）
1. 週次 GitHub Actions ワークフロー（`sop-health-reporter.yml`）で 5 指標を収集する。
2. Prometheus Pushgateway 経由で self-hosted Grafana へ時系列データを流す。
3. ゼロ許容条件（宿題期限超過）を検知したら Discord `#scheduled-report` へ即通知する。
4. Grafana ダッシュボード `sop-health-reporter` に 5 パネルを設置し、常時参照可能にする。

## 5 指標の定義

| 指標 | メトリクス名 | 定義 |
|------|------------|------|
| 免除PR件数（週次） | `sop_exempt_pr_total` | 直近7日の closed PR で `- [x] 免除` を本文に含む件数 |
| 危険PR承認（週次） | `sop_dangerous_approved_total` | 直近7日の closed PR で DANGEROUS_PATTERNS ファイルを変更した件数 |
| 緊急PR累計 | `sop_emergency_total` | `sop-followup` ラベル Issue の alltime 件数（open + closed） |
| 宿題期限超過 | `sop_overdue_homework_count` | `sop-followup` open Issue で期限が過ぎた件数 |
| ゲート摩擦率 | `sop_gate_friction_rate` | 週次: (gate 失敗 run を持つ PR 数) / (全 closed PR 数)、0.0–1.0 |

## トレードオフ
- Pushgateway 追加でモニタリングスタック 1 コンテナ増加（メモリ影響: ~32MB）。
- GitHub API rate limit（5000/h）: 週次実行 × 最大 ~3000 req → 問題なし（recon 実証済み）。
- `PUSHGATEWAY_URL` secret の VPS 側設定は PO が担当（nginx リバースプロキシ推奨）。

## 参照
- recon: `docs/handoff/sop-kpi2-phase2/recon.md`
- 設計: `docs/handoff/sop-kpi2-phase2/design.md`
- 実装: `scripts/sop-health-collector.js`, `.github/workflows/sop-health-reporter.yml`
- 前提 ADR: ADR-121（process-artifacts gate）
