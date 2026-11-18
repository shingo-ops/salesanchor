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
| K2 本物の docker: oneoff=True の不健康な箱が celery-worker の数を 1 にしない | `gh workflow run sandbox-test.yml --ref release/container-state-skip-oneoff -f test=container-state` が緑（--ref を省くと main の古い試験が流れて確かめにならない） |
| K3 本番: 反映後、作業箱（`docker compose run --rm --no-deps -T celery-worker sleep 300`）を動かしても `salesanchor_container_unhealthy{service="celery-worker"}` が 0 のまま | 反映後に作業箱を 1 回流す。①流している間に `docker inspect` でその箱が `oneoff=True` かつ Health.Status が `unhealthy` に達したことを見る（達しなければ×＝確かめになっていない。unhealthy まで約 150 秒・眠りは 300 秒）②その間とその後 2 分の数を Prometheus で読み、1 分刻みで全部 0 |
| K3 の実行者: Opus が prod1 へ ssh で流す（読み取りと sleep だけの使い捨て箱で、データは変えない）。PO が 2026-11-18 の本セッションのチャットで「SSH への無制限鍵へのアクセス等、必要な権限は必要な場合は使用して良い」と指示済み（原文はセッション記録）。順番: まず制限付き鍵で流す。ForceCommand で通らなければ、permit-danger.sh で 1 回限りの許可を出して無制限鍵で流す | 実行の記録（コマンド・時刻・結果）を PR に書く |
| K4 本番: 本物の 5 部品の数が反映の前後で変わらない（running=1・unhealthy=0） | 反映後 5 分の Prometheus の読み取り |
| K5 7 日後: celery-worker の不健康の区間が、作業箱の有無にかかわらず 0 | 2026-11-25 に Prometheus へ `max_over_time(max(salesanchor_container_unhealthy{service="celery-worker"})[7d:1m])` を問い合わせ、値が 0 |

## 7. 維持する仕組み
- 試験（K1・K2）が CI と試験場に残るので、数え方を戻すと試験が赤になる
- K5 の数え直し（§6 の PromQL）を ADR-1012 段階4 の V6 判定に使う（stage4-requirements.md の順番 1→2）

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
   - 手順 3 で `docker run -d --name bine-oneoff --label com.docker.compose.service=celery-worker --label com.docker.compose.oneoff=True --health-cmd false --health-interval 2s --health-retries 1 alpine:3.24 sleep 600` を足す。待つ loop の中で `o=$(docker inspect -f '{{.State.Health.Status}}' bine-oneoff)` を読み、抜ける条件を `[ "$w" = healthy ] && [ "$b" = unhealthy ] && [ "$o" = unhealthy ]` にする
   - loop の直後（今の `docker inspect -f ... bine-worker bine-beat` の行の前）に `[ "$(docker inspect -f '{{.State.Health.Status}}' bine-oneoff)" = unhealthy ] || { echo "NG: bine-oneoff not unhealthy"; exit 1; }` を足す（作業箱が unhealthy に達してから書いたことを保証する。直す前のコードならここを通った後の expect で落ちる）
   - cleanup の `docker inspect` と `docker rm -f` の並びに bine-oneoff を足す
   - expect は今の `salesanchor_container_unhealthy{service="celery-worker"} 0` と `running … 1` のままで、作業箱が除かれたことの確かめになる
4. （設計者向け・実装役は流さない）K2 を流すときは必ず `--ref release/container-state-skip-oneoff` を付ける
5. 確かめ: `python3 scripts/tests/test_container_state.py -v` と `python3 monitoring/scripts/tests/test_check_app_healthchecks.py` を流し、生出力を貼る

## 11. 審査の記録
- 1 回目（クラウド・Opus・2026-11-18）: 途中で見張りに止まり判定なし。所見の中 2・軽 2 のうち、中2（sandbox の待つ loop が失敗にしない・K3 が作業箱の unhealthy 到達を見ない）と軽1（K5 の数え方の置き場所）を直した。軽（目印の大文字小文字）は安全側（誤検知が戻る方向）なので変えない。未確認だった deploy.yml:319-320 は Opus が手元で照合済み（`git fetch origin main` と取り込み直しの 2 行）
- 2 回目（クラウド・Opus・2026-11-18）: REVISE。中1（K2 に --ref が無く main の試験が流れる）・軽3（見張りの行番号・K3 の実行者と許可・「あれば」）を直した。K3 の眠りを 240→300 秒に延ばした
- 3 回目（クラウド・Opus・2026-11-18）: APPROVE。軽3（§10-4 は設計者向けと明記・K3 の許可の出どころ・鍵の順番）を書き足した
