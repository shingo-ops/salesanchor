# design.md — SOP KPI2 Phase 2（sop-health-reporter 実装設計）

**ADR**: ADR-124-sop-health-reporter
**調査日**: 2026-06-09
**前提**: `docs/handoff/sop-kpi2-phase2/recon.md`

---

## 1. 目的

ADR-121（process-artifacts gate）の定着フェーズを定量可視化する。
GitHub API で週次 SOP 遵守指標 5 件を収集し、Prometheus/Grafana ダッシュボードで表示。
ゼロ許容条件（危険PR未承認・宿題期限超過）を検知したら Discord へ即通知する。

---

## 2. アーキテクチャ概要

```
GitHub Actions（毎週月曜 00:00 UTC = JST 09:00）
  └── scripts/sop-health-collector.js
        ├── gh API → 5 指標を計算（lookback: 直近7日 closed PR + alltime issues）
        ├── curl → Prometheus Pushgateway（pushgateway:9091 / 外部: PUSHGATEWAY_URL）
        │             └── Prometheus scrape（60s 間隔）
        │                   └── Grafana ダッシュボード sop-health-reporter
        └── ゼロ許容超過時 → Discord（DISCORD_WEBHOOK_SCHEDULED_REPORT）
```

---

## 3. 測定指標（5 指標）

| # | メトリクス名 | 収集方法 | ゼロ許容アラート |
|---|------------|---------|----------------|
| 1 | `sop_exempt_pr_total` | closed PR body scan（`- [x] 免除`） | なし |
| 2 | `sop_dangerous_approved_total` | DANGEROUS_PATTERNS ファイル変更 PR 件数（週次） | なし（集計のみ） |
| 3 | `sop_emergency_total` | sop-followup label issues（alltime 累計） | なし |
| 4 | `sop_overdue_homework_count` | sop-followup open + 期限超過 | **あり（>0 即通知）** |
| 5 | `sop_gate_friction_rate` | process-artifacts-gate failure run / 全 PR（週次, 0.0–1.0） | なし |

**ゼロ許容（Zero-Tolerance）**: `sop_overdue_homework_count > 0` のみ。
危険PR自体はゲートで承認必須のため「存在すること」は正常。未承認で抜けた場合のみ別途手動確認。

---

## 4. コンポーネント設計

### 4.1 Prometheus Pushgateway

- イメージ: `prom/pushgateway:v1.10.0`
- 追加先: `docker-compose.monitoring.yml`
- ポート: 9091（内部のみ、Prometheus からスクレイプ）
- 外部アクセス: nginx リバースプロキシ経由 or 直接ポート開放（VPS 設定）
- 必要 GitHub Secret: `PUSHGATEWAY_URL`（例: `https://app.salesanchor.jp/pushgateway`）

### 4.2 scripts/sop-health-collector.js

- Node.js 20 組み込み `fetch` のみ（外部 npm 依存なし）
- 入力環境変数:

| 変数 | 内容 |
|------|------|
| `GH_TOKEN` | GitHub Actions の `GITHUB_TOKEN` |
| `PUSHGATEWAY_URL` | Pushgateway への HTTP エンドポイント |
| `DISCORD_WEBHOOK_URL` | `DISCORD_WEBHOOK_SCHEDULED_REPORT` |
| `REPO` | `shingo-ops/salesanchor` |
| `LOOKBACK_DAYS` | 週次集計の対象日数（デフォルト 7） |

- Pushgateway への push 形式:

```
# TYPE sop_exempt_pr_total gauge
sop_exempt_pr_total{repo="shingo-ops/salesanchor"} 3
# TYPE sop_dangerous_approved_total gauge
sop_dangerous_approved_total{repo="shingo-ops/salesanchor"} 1
...
```

- Discord アラート条件: `sop_overdue_homework_count > 0`

### 4.3 .github/workflows/sop-health-reporter.yml

- スケジュール: `0 0 * * 1`（毎週月曜 00:00 UTC = JST 09:00）
- `workflow_dispatch` で手動実行可
- `permissions`: `pull-requests: read`, `issues: read`, `actions: read`
- `timeout-minutes: 10`

### 4.4 Grafana ダッシュボード

- uid: `sop-health-reporter`
- datasource: Prometheus（UID `PBFA97CFB590B2093`）
- 5 パネル構成（左→右、上→下）:

| Panel | 種別 | クエリ |
|-------|------|--------|
| 免除PR件数（週次） | bar chart | `sop_exempt_pr_total` |
| 危険PR承認（週次） | stat（赤 if >0） | `sop_dangerous_approved_total` |
| 緊急PR累計 / 宿題超過 | stat x2 | `sop_emergency_total` / `sop_overdue_homework_count` |
| ゲート摩擦率 | time series（%） | `sop_gate_friction_rate * 100` |
| SOP ヘルスサマリー | table | 5 指標の最新値 + 閾値 |

---

## 5. 変更ファイル一覧

| ファイル | 変更 | 理由 |
|---------|------|------|
| `docs/handoff/sop-kpi2-phase2/design.md` | 新規 | 本ファイル |
| `docs/adr/ADR-124-sop-health-reporter.md` | 新規 | 設計決定記録 |
| `scripts/sop-health-collector.js` | 新規 | 収集・push スクリプト |
| `.github/workflows/sop-health-reporter.yml` | 新規 | 週次ワークフロー |
| `monitoring/grafana/provisioning/dashboards/json/sop-health.json` | 新規 | Grafana ダッシュボード |
| `docker-compose.monitoring.yml` | 修正 | Pushgateway サービス追加 |
| `monitoring/prometheus/prometheus.yml` | 修正 | Pushgateway scrape job 追加 |
| `monitoring/grafana/nav-config.json` | 修正 | SOP Health タブ追加 |

---

## 6. 新規 GitHub Secrets（PO 設定必須）

| Secret 名 | 内容 |
|----------|------|
| `PUSHGATEWAY_URL` | Prometheus Pushgateway への外部 URL |

---

## 7. 危険変更チェック

| 対象 | 変更有無 | 備考 |
|------|---------|------|
| `migrations/` | なし ✅ | |
| `.github/workflows/deploy.yml` | なし ✅ | |
| 本番スクリプト（aeon-dispatch.sh 等） | なし ✅ | |
| `docker-compose.monitoring.yml` | あり（Pushgateway 追加のみ） | 不可逆操作リスト外 |
| `monitoring/prometheus/prometheus.yml` | あり（scrape job 追加のみ） | 不可逆操作リスト外 |

---

## 8. KPI 完了確認（受入基準）

- [ ] 5 指標が Grafana `sop-health-reporter` ダッシュボードに表示される
- [ ] `sop_overdue_homework_count > 0` 時に Discord アラートが発火する
- [ ] `sop-health-reporter.yml` を `workflow_dispatch` で手動実行してエラーなし
