# design: 状態書き係が使い捨ての作業箱を数えないようにする（ADR-1012 段階4 順番1）

- recon: docs/handoff/container-state-oneoff/recon.md
- 対象 ADR: ADR-1012（段階3 便E の状態書き係の不具合直し）
- PO 承認: 2026-11-17「1」（原因調べ）→ 2026-11-18 PO の指示（直し方の案 1「作業箱を数えないように直す」を、合流・本番反映まで進める）

## 1. 目的（KGI）
本物の部品が元気なのに「調子が悪い」と知らせる誤検知を 0 にする。本物の部品が本当に止まったときの知らせは今のまま鳴らす。

## 2. 対象と対象外
- 対象: `scripts/ops/container_state.py`（数え方）・`scripts/tests/test_container_state.py`（試験）・`tests/sandbox/container-state.sh`（本物の docker での試験）
- 対象外（触らない）: docker-compose.yml の健康診断・backend/app/celery_alive.py・monitoring/prometheus/alert_rules.yml・cron・deploy.yml・作業箱を流す手順書

## 3. 変更前 → 変更後
- 変更前: `read_states()` は service の目印が付いた箱を全部返す（`docker compose run` の作業箱も入る）
- 変更後: `docker inspect` の `Config.Labels["com.docker.compose.oneoff"]` が `"True"` の箱を除いて返す。目印が無い箱・`"False"` の箱は今までどおり数える
  - 除いた作業箱は unhealthy・running・healthcheck_missing の 3 つすべてから外れる（3 つとも read_states() の結果から作るため）
  - 目印が無い箱を数え続けるのは、目印の付け方が変わっても本物の箱を見落とさないため（見落とすより誤検知の方が安全）

## 4. 代替案と選んだ理由
| 案 | 中身 | 判断 |
|---|---|---|
| A（採用） | inspect の目印を読み、`"True"` だけ除く | 本物の箱は目印が無くても数え続ける。変更は 1 か所 |
| B | `docker ps` に `--filter label=com.docker.compose.oneoff=False` を足す | 目印が無い箱まで消える。本物を見落とす道ができるので不採用 |
| C | 作業箱を流すときに健康診断を止める決まりにする | 人の注意に頼る。止め忘れで再発するので不採用 |
| D | 健康診断を「worker として動いているか」で見るように変える | 本物の箱の健康診断を変えることになり、影響が大きいので不採用 |

## 5. リスクと対処
- 本物の箱に誤って `oneoff=True` が付く → 数えられなくなる。対処: 本番の 5 つは `oneoff=False` を実測済み（recon 観測事実 6）。`up` は常に `False` を付ける（Docker Compose の作り）
- 作業箱が本当に固まっても知らせない → 作業箱は手で流して手で見る作業なので、見張りの対象にしない（もともと見張りの目的は本物の部品）

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 試験: oneoff=True の箱だけ除かれ、False・目印なし・Config なしは数える | `python3 scripts/tests/test_container_state.py`（CI の deploy-script-test・monitoring-check）が緑 |
| K2 本物の docker: oneoff=True の不健康な箱が celery-worker の数を 1 にしない | `gh workflow run sandbox-test.yml -f test=container-state` が緑 |
| K3 本番: 反映後、作業箱（`docker compose run --rm --no-deps -T celery-worker sleep 240`）を動かしても `salesanchor_container_unhealthy{service="celery-worker"}` が 0 のまま | 反映後に作業箱を 1 回流し、その間とその後 2 分の数を Prometheus で読む（1 分刻みで全部 0） |
| K4 本番: 本物の 5 部品の数が反映の前後で変わらない（running=1・unhealthy=0） | 反映後 5 分の Prometheus の読み取り |
| K5 7 日後: celery-worker の不健康の区間が、作業箱の有無にかかわらず 0 | 2026-11-25 に v6ep.sh と同じ読み方で 7 日分を数える |

## 7. 維持する仕組み
- 試験（K1・K2）が CI と試験場に残るので、数え方を戻すと試験が赤になる
- K5 の数え直しを ADR-1012 段階4 の V6 判定に使う（stage4-requirements.md の順番 1→2）

## 8. 外部事例
- Docker Compose 自身が、普段の箱を数えるときに one-off の箱を外している（pkg/compose/containers.go getDefaultFilters の oneOffExclude）。同じ目印で外すのは作り手と同じ扱い。数値の事例は不要（不具合直しで、効果は K3・K5 の実測で確かめる）

## 9. 戻し方
PR を revert して main に合流 → deploy で戻る。cron・textfile の場所は変えないので、戻した次の分から元の数え方で書く。

## 10. 実装カード（クラウドの Sonnet 向け）
1. `scripts/ops/container_state.py`
   - 定数 `ONEOFF_LABEL = "com.docker.compose.oneoff"` を `DOCKER_TIMEOUT_SECONDS` の下に足す
   - 関数 `is_oneoff(container: dict) -> bool` を read_states の前に足す: `labels = (container.get("Config") or {}).get("Labels") or {}` を作り、`labels.get(ONEOFF_LABEL) == "True"` を返す。docstring は 1 行「docker compose run で作った使い捨ての箱なら True（目印が無い箱は False＝数える）。」
   - read_states の return を `[c.get("State") or {} for c in data if not is_oneoff(c)]` に変える。docstring に「docker compose run の使い捨ての箱（oneoff=True）は除く。」を足す
   - それ以外は変えない
2. `scripts/tests/test_container_state.py` に class `OneoffTest` を足す
   - is_oneoff: `{"Config": {"Labels": {ONEOFF: "True"}}}`→True、`"False"`→False、Labels 無し→False、Config 無し→False、`Labels: None`→False
   - main: ps が "a b\n"、inspect が [oneoff=True で Running・unhealthy, oneoff=False で Running・healthy] を返す差し替えで main()==0、`salesanchor_container_unhealthy{service="celery-worker"} 0` と `salesanchor_container_running{service="celery-worker"} 1` がある
   - main: inspect が [oneoff=True で Running・unhealthy] だけ → `salesanchor_container_running{service="celery-worker"} 0` と `salesanchor_container_unhealthy{service="celery-worker"} 0`
3. `tests/sandbox/container-state.sh`
   - 手順 3 で `docker run -d --name bine-oneoff --label com.docker.compose.service=celery-worker --label com.docker.compose.oneoff=True --health-cmd false --health-interval 2s --health-retries 1 alpine:3.24 sleep 600` を足す。待つ loop の条件に `bine-oneoff` が unhealthy を足す
   - cleanup の `docker inspect` と `docker rm -f` の並びに bine-oneoff を足す
   - expect は今の `salesanchor_container_unhealthy{service="celery-worker"} 0` と `running … 1` のままで、作業箱が除かれたことの確かめになる
4. 確かめ: `python3 scripts/tests/test_container_state.py -v` と `python3 monitoring/scripts/tests/test_check_app_healthchecks.py`（あれば）を流し、生出力を貼る
