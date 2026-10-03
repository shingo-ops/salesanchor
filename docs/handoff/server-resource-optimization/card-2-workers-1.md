# 実装カード ②：backend の uvicorn を workers=1 にする（ADR-081 に一致させる）

- 設計：設計 PR #3909 の design-20261001.md（server-resource-optimization フォルダ）§4 便②。
- 前提の便
  - ①（PR #3912）
  - ①b（PR #3934）
  - どちらも本番に反映済み。①b がコンテナ内に入っていることは、2026-10-03 に grep で確認した。
- このカードは recon（現在地の確認）を兼ねる：`docs/handoff/server-resource-optimization/card-2-workers-1.md`
- 対象の ADR：`docs/adr/ADR-081-monitoring-vps-final-operational-design.md`（ADR-081-monitoring-vps-final-operational-design。C 項「backend は workers=1 を標準」、Scope IN「worker 数を 1 に固定」）
- PO の決定（2026-10-02）：②の作業カードを作り、実装を始めることに「y」。2026-10-03 にも続行に「y」。

## 現在地（事実。Sonnet が 2026-10-02 に確認、origin/main）
- workers を指定しているのは `backend/Dockerfile:37` の1か所だけ。
  - docker-compose の各ファイル、.github/workflows 配下、scripts 配下、`backend/app/main.py` には指定が無い。
  - `scripts/blue-green-cutover.sh:80-105` は、イメージの CMD をそのまま使う。
- 本番の実物：`docker inspect` の Cmd は `["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","2"]`。
- メモリ
  - 子ワーカーの RSS は 269,032KB と 261,904KB。
  - backend の cgroup は `memory.peak` = `memory.max` = 536870912。上限に当たった回数は `memory.events max=37`（稼働4分40秒の時点）。
- 負荷
  - 直近24時間の `http_requests_in_flight` の最大は 1。
  - 7日の最大は 3（design §2-1）。
- デプロイは blue-green（`.github/workflows/deploy.yml:319-324`）。切り替えの間は、旧と新の backend が同時に動く。

## 変更（変更前 → 変更後）
| # | 箇所 | 変更前 | 変更後 |
|---|---|---|---|
| w1 | `backend/Dockerfile:35-36` | `# workers=2: 512MB VPSでの上限（メモリ制限による）`<br>`# workers=1に戻す場合はメモリ確認後に判断すること` | `# workers=1: ADR-081 C項（backend は workers=1 を標準）。`<br>`# ループを塞ぐ同期I/Oは #3912・#3934 でスレッドへ退避済み。2 に戻す条件は ADR-081 D項。` |
| w2 | `backend/Dockerfile:37` | `..., "--workers", "2"]` | `..., "--workers", "1"]` |

## 触らない範囲
- `docker-compose.yml` の上限（512M）：便③で扱う。
- celery の concurrency：2 のまま（実際に使い切っているため。design §2）。
- `scripts/blue-green-cutover.sh`、`.github/workflows/deploy.yml`。
- ADR-081 の改訂：便⑤で扱う。

## テスト
- 挙動のテストは無い（起動の引数だけの変更）。
- CI の通常のテスト（Backend Tests）と、イメージのビルド（deploy の build）が成功することで確認する。

## 受入条件（○×）と、本番での判定（反映から24時間後）
| 基準 | 検証方法 | 戻す条件 |
|---|---|---|
| 本番の Cmd が `--workers 1` | `docker inspect astro-webapp-backend-1 --format '{{json .Config.Cmd}}'` | — |
| backend の uvicorn の子が1つ | `docker top astro-webapp-backend-1` | — |
| backend の使用メモリが下がる | `docker stats` と、cgroup の `memory.current`、`memory.events max` の増え方 | — |
| ホストの available の最小が上がる | Prometheus（instance="app-vps"）の MemAvailable の最小。反映前の24時間と比べる | — |
| 応答時間が悪化しない | p95/p99 の中央値。反映前の基準値（`/tmp/CC報告ファイル/ops-memory/20261003-baseline2/`）と比べる | p99 の中央値が、基準値の1.5倍を超えたら戻す |
| エラーが増えない | backend の 5xx の件数、Loki の ERROR / Traceback | 5xx が、基準の窓より増えたら原因を調べ、①b の範囲外のループの塞ぎであれば戻す |
| SSE と取込が動く | `/api/v1/conversations/stream` と `/api/v1/tcg/line-devices/import` の件数が続いている | 件数が0になったら、すぐ戻す |

## 外部・過去事例の参照と我々への応用
- 過去の事例（社内）：ADR-081 の Why §1。workers=2 にした後、常駐メモリが増え、swap の使用が続いた。今回の実測でも、2ワーカー×約265MB が 512M の上限を超えている（design §2）。
- 外部の一般事例は使わない。効果は、上の表の本番での実測で判定する。

## 維持の仕組み
- 守り手: ADR-081（C 項・D 項）と、`backend/Dockerfile:35-36` のコメント。2 に戻すときは、ADR-081 D 項の条件を満たすことが必要。

## 戻し方
- PR を revert する（Dockerfile の1行とコメント）。デプロイで、旧の CMD に戻る。
