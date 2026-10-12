# ADR-081: 監視VPS分離の最終運用設計 — パケットフィルタ、UFW、proxy 経路、backend worker 数の固定

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-05-30 |
| 起案 | Codex |
| 承認 | しんごさん（PO） |
| 関連 ADR | ADR-080（監視スタックの管理室VPS分離）/ ADR-079（Claude Code 専用 VPS 読み取り専用監視アクセス）/ ADR-077（GitHub Actions CI メトリクス可視化）/ ADR-070（Grafana 監視統合）/ ADR-065（asyncpg プリペアドステートメントキャッシュ無効化） |

## What

監視スタックの管理室VPS分離を継続し、**外部公開の入口制御・VPS内 firewall・nginx proxy・backend worker 数**をひとつの最終運用設計として固定する。

本 ADR は、分離移行の途中で判明した「VPS 内 `ufw` を開けてもアプリVPSから監視VPSへ到達しない」事象を前提に、**さくらVPS のパケットフィルタと VPS 内 `ufw` を二重化して揃える**ことを決定する。

### 最終構成

**アプリVPS `49.212.137.46`**

| 要素 | 方針 |
|------|------|
| backend | `uvicorn --workers 1` を基本とする |
| frontend | 既存どおりアプリ表示を担う |
| nginx | `/grafana` / `/monitor` 系の proxy を維持 |
| PostgreSQL / Redis / Celery / Discord gateway | 既存同居を維持 |

**監視VPS `49.212.160.98`**

| 要素 | 方針 |
|------|------|
| Grafana | `app.salesanchor.jp/grafana/` の表示先 |
| Prometheus | アプリVPSの `/metrics` を scrape |
| Uptime Kuma | アプリ可用性監視の独立実行 |
| Loki | アプリVPS の promtail から log push を受信 |

## Why

### 1. 2 workers は 1.9GB VPS の常駐メモリ予算に対して重い

`uvicorn --workers 2` にした後、backend の常駐メモリが増え、swap 使用が継続した。  
Celery に重い I/O を逃がしている現在の構成では、backend の同時並列性を 2 倍にするより、**メモリ余力を確保して 1 worker で安定させる方が安全**である。

### 2. 監視分離は正しいが、入口制御が未完成だと部分障害になる

監視VPS 自体は正常稼働していても、アプリVPS からの TCP 接続が監視VPS まで届かなければ、`app.salesanchor.jp/grafana/...` は `nginx` 504 になる。  
今回の調査では、VPS 内 `ufw` を追加してもパケット到達が確認できず、**提供元側のパケットフィルタまで含めて許可を揃える必要**があることが分かった。

### 3. 監視系は「別VPSで独立稼働」が前提

監視をアプリVPSに同居させると、アプリVPS障害時に監視も一緒に落ちる。  
そのため、監視スタック分離の方針自体は維持し、**監視VPS側の受信経路だけを正しく完成させる**のが最終形である。

## Decision

### A. 入口制御は「さくらVPS パケットフィルタ + UFW」の二重化にする

監視VPS の公開ポートは、提供元側のパケットフィルタで先に絞り、その後 VPS 内 `ufw` でも同じ意図で絞る。

#### 監視VPS で許可する通信

| ポート | 用途 | 許可元 |
|------|------|------|
| 22/tcp | SSH | 管理者IPのみ |
| 80/tcp | HTTP | 0.0.0.0/0 または Cloudflare 経由の設計に合わせる |
| 443/tcp | HTTPS | 0.0.0.0/0 または Cloudflare 経由の設計に合わせる |
| 3000/tcp | Grafana | アプリVPS `49.212.137.46` / 管理者IPのみ |
| 3001/tcp | Uptime Kuma | アプリVPS `49.212.137.46` / 管理者IPのみ |
| 9090/tcp | Prometheus | 管理者IPのみ |

#### アプリVPS から見た監視VPS への疎通確認

- `http://49.212.160.98:3000/api/health`
- `http://49.212.160.98:3001/`
- `http://49.212.160.98:9090/-/healthy`

上記が通らない状態では、`app.salesanchor.jp/grafana/...` を本番扱いにしない。

### B. nginx の proxy は監視VPSの疎通確認後にのみ本番固定とする

`/grafana` や `/monitor` 系の reverse proxy は、監視VPS への direct access が確認できてから final とする。  
途中状態で proxy だけ切り替えると、画面は表示されても内部 API が `504` になる。

### C. backend は `workers=1` を基本設定とする

アプリVPS の backend は、現行のメモリ予算では `workers=1` を標準とする。  
`workers=2` へ戻す条件は、swap の恒常増加が止まり、p95/p99 と同時処理中リクエスト数が十分に余裕を示した場合に限る。

### D. worker 数の増加は、VPS 増強か別配置とセットでのみ再検討する

`workers=2` を恒常運用へ戻すのは、以下のどちらかが成立した後に限る。

1. アプリVPS のメモリを増強する
2. backend 以外の同居サービスを再分割し、常駐メモリを再設計する

単に「同時接続が少し増えた」だけでは、1.9GB VPS のまま 2 workers へ戻さない。

## Scope IN

- 監視VPS の受信経路を、さくらVPS パケットフィルタと `ufw` で揃える
- 監視VPS の `3000/3001/9090` を適切な送信元だけに制限する
- アプリVPS から監視VPS への direct access を疎通確認する
- `app.salesanchor.jp/grafana/` の proxy を監視VPSへ固定する
- backend の標準 worker 数を `1` に固定する
- `http_requests_in_flight` と `sse_connections_active` を worker 余力判定の基準に使う

## Scope OUT（明示除外）

- 監視系の VPN 化
- 監視VPS の 2 台目追加
- Prometheus / Loki のマネージド移行
- backend の `workers=2` 恒久化
- 監視ポートの `0.0.0.0/0` 全開放

## Consequences

### Positive

- 監視VPS 分離の恩恵を維持しつつ、部分障害の原因を明確化できる
- パケットフィルタと `ufw` の責務が一致するため、誤設定を減らせる
- backend のメモリ圧迫を抑え、swap thrashing を避けやすい
- `workers=1` のまま監視指標で判断できるため、安定性重視の運用に合う

### Negative

- 入口制御が二重化されるため、設定漏れ時の切り分けコストが増える
- `workers=2` に戻すには、メモリ増強か構成再設計が必要になる
- 監視系の公開設定が増えるため、管理者の運用負荷が少し上がる

## 実施条件

以下が全て満たされたら、この設計を本番固定とする。

1. アプリVPS から監視VPS の `3000/3001/9090` に疎通できる
2. `https://app.salesanchor.jp/grafana/api/login/ping` が 504 ではなく応答する
3. Grafana で backend の `http_requests_in_flight` が確認できる
4. `workers=1` で p95/p99 とメモリが安定している
5. swap が継続的に増えない

## 改訂（2026-10-07）：workers=1 の実施と、実測にもとづく前提の追記

PO 承認：2026-10-07、PR #3909（原文「よい#3909 承認」）

### 経緯（事実）
- 本 ADR の C 項・Scope IN（workers を 1 に固定）は、2026-05-30 から 2026-10-03 まで実装に反映されていなかった。`backend/Dockerfile:37` は `--workers 2` のままだった（2026-05-22 のコミット 2850394a1）。
- 2026-10-01〜07 の見直し（記録：`docs/handoff/server-resource-optimization/recon-20261001.md`、`docs/handoff/server-resource-optimization/design-20261001.md`）で、次のことを実測した。
  - backend の1ワーカーは、起動した時点で約245MB（import の大きさ。長く動いて太ったものではない）。2ワーカーと親プロセスで、上限 512M を超えていた。cgroup の `memory.events max` は70分で354回。
  - celery-worker は、子が google.genai の遅延 import で約257MB になり、合計約620MBで上限 512M を超えていた。`memory.events max` は37分で707回。
  - async のエンドポイント（609件）の中に、同期の I/O でイベントループを塞ぐ箇所があった（SMTP、PDF の生成、Google API、LINE 取込のパース、Firebase の検証など）。1ワーカーにすると、その間は全員の要求が止まる。

### 追記する決定
- **C-1（前提条件）**：backend を1ワーカーで動かす前提として、async の経路で同期の I/O・CPU 処理を直接呼ばない。`asyncio.to_thread` / `run_in_threadpool` で逃がす。守り手は CI の `backend/tests/test_event_loop_nonblocking.py`（PR #3912・#3934）。
- **C-2（実施）**：`backend/Dockerfile:37` を `--workers 1` にした（PR #3954、2026-10-03 本番反映）。
- **E（メモリ上限）**：コンテナのメモリ上限は、実測の必要量より上に置く。celery-worker は 768M（PR #4005、2026-10-06 本番反映）。上限の見直しは、cgroup の `memory.events max` と swap.current を基準にする。

### 実施の後の実測（本番）
| 項目 | 前 | 後 |
|---|---|---|
| backend のメモリ | 489MiB / 512MiB | 266MiB / 512MiB |
| backend の `memory.events max` | 354（70分） | 0 |
| celery の `memory.events max` | 707（37分） | 0 |
| celery の swap | 約294MiB | 0 |
| ホストの MemAvailable の最小 | 約569MiB（②の後、③の前） | 約1359MiB（③の後） |
| backend の 5xx | 0 | 0 |
| p99 の中央値 | 2.06 秒 | 2.48 秒（戻す基準 3.08 秒の範囲内） |

### D 項について
- 2026-09-20 に、アプリVPSのメモリは 2GB から 4GB に増強された。D 項の条件1（増強）は満たしている。
- ただし、in_flight の実績（7日の最大3、1以上の時間は0.19%）からは、2ワーカーにする必要は無いと判断した。workers=1 を続ける。

## 関連ドキュメント

- 移行 runbook: `docs/runbooks/monitoring-vps-migration.md`
- 監視アクセス: `docs/runbooks/claude-monitor-access.md`
- 既存監視設計: `docs/adr/ADR-080-monitoring-vps-separation.md`
- backend 監視メトリクス: `monitoring/grafana/provisioning/dashboards/json/backend-metrics.json`
- alert rules: `monitoring/prometheus/alert_rules.yml`
