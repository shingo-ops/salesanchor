# 実装カード ③：celery-worker のメモリ上限を 512M から 768M にする

- 設計：設計 PR #3909 の design-20261001.md（server-resource-optimization フォルダ）§4 便③。
- このカードは recon（現在地の確認）を兼ねる：`docs/handoff/server-resource-optimization/card-3-celery-768.md`
- 対象の ADR：`docs/adr/ADR-081-monitoring-vps-final-operational-design.md`（ADR-081-monitoring-vps-final-operational-design。アプリVPSのメモリ予算）
- PO の決定（2026-10-06）：③に進むことに「y」。
- 前提の便
  - ②（PR #3954、workers=1）は本番反映済み・受入済み。backend は 489MB → 266MB。

## 現在地（事実。Sonnet が 2026-10-06T02:32Z に取得。生の出力は /tmp/CC報告ファイル/ops-memory/20261006-card3/）
- 定義：`docker-compose.yml:254-258` の celery-worker の `deploy.resources.limits` が memory 512M / cpus 1.0。
- 反映の経路：`.github/workflows/deploy.yml:389-394` で、celery-worker は `docker compose up -d` により作り直される（上限の変更が反映される経路）。`scripts/blue-green-cutover.sh` は celery に関わらない。
- celery-worker の cgroup（作成 2026-10-06T01:55:21Z から約37分）：
  - memory.current 約376MiB、memory.peak 536989696（上限に到達）、memory.swap.current 約294MiB、memory.events の max 707、oom_kill 0。
- コンテナの中のプロセス：celery の親 35,888KB、子 168,808KB と 58,144KB。
  - それとは別に、`python -m app.tools.prompt_ab ...`（LINE 解析の比較テスト。RSS 213,964KB）が同じコンテナの中で動いていた。
  - このプロセスは同じ cgroup で数えられる。LINE 解析セッションの作業なので、このカードでは触らない。
- ホスト（Prometheus、instance="app-vps"）
  - ②の反映後の MemAvailable の最小は約569MiB、直近24時間の最小は約875MiB。
  - 現在は約1222MiB。
- 必要量の根拠（design §4-1・recon §4-1）：celery の親 約107MB と、子2つ（各 約257MB。google.genai の遅延 import を含む）で、合計約620MB。

## 変更（変更前 → 変更後）
| # | 箇所 | 変更前 | 変更後 |
|---|---|---|---|
| c1 | `docker-compose.yml` の celery-worker の `deploy.resources.limits.memory`（:254-258 の中） | `memory: 512M` | `memory: 768M` |

- cpus、concurrency（2）、ほかのサービスは変えない。
- compose の上限の合計は 3520M → 3776M になる。上限は使用量の予約ではなく、上限値である。

## 触らない範囲
- `backend/Dockerfile`、ほかのサービスの上限、`.github/workflows/deploy.yml`、`scripts/`。
- celery のコンテナの中で動く手動のツール（`app.tools.prompt_ab` など）の扱い。LINE 解析セッションの範囲のため。

## テスト
- コードの変更は無い。CI の compose 関連のチェック（監視スタック整合性チェック、CI設定整合性チェックなど）が通ること。

## 受入条件と、戻す条件（反映後24時間で判定する）
| 基準 | 検証方法 | 戻す条件 |
|---|---|---|
| celery の上限が 768M になっている | celery-worker の cgroup の `memory.max` = 805306368 | — |
| celery の swap と上限への衝突が減る | `memory.swap.current` と、`memory.events max` の増え方（作成からの経過時間あたり）。反映前は 37分で 707 回、swap は約294MiB | — |
| ホストの余力が保たれる | Prometheus の MemAvailable の最小 | 300MiB を下回ったら戻す |
| 強制終了が起きない | 全コンテナの `memory.events` の oom_kill、`journalctl -k` の OOM | 1件でも起きたら戻す |
| celery のタスクが動く | Loki の celery の succeeded の件数（反映前の同じ時間帯と比べる） | 0件になったら戻す |

## 外部・過去事例の参照と我々への応用
- 公式の仕様（Celery の optimizing、Context7 `/websites/celeryq_dev_en_stable`）：Python のプロセスは、使ったメモリの最高値を OS に返さない。今回の子プロセスの増加（遅延 import）は、これに当たる。上限を実際に必要な量より上にしておくのが、もっとも単純な対処になる。
- 社内の過去事例：便②（PR #3954）。必要量より小さい上限をやめたことで、`memory.events max` は 0、swap も 0 になった。
- 外部の一般事例は使わない。

## 維持の仕組み
- 守り手：`docker-compose.yml` の上限と、このカードの基準値。ADR-081 を改訂する便⑤で、メモリ予算の表に反映する。

## 戻し方
- PR を revert する（768M → 512M）。デプロイで、celery-worker が作り直される。
