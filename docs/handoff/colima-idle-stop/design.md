# Colima 使い終わり自動停止 設計（2026-10-15・v2.1・Fable 審査 APPROVE: /tmp/CC報告ファイル/ac-heavy/docker-idle/review-design3.md）

区分（ADR-1015）: **A**（危険パス scripts/・ops/launchd/ を触る feat）。PR は Draft・GO 記録必須（ADR-136）。recon: [recon.md](recon.md)。前例: [disk-janitor 設計](../disk-janitor/design.md)。
設計仕様書（docs/specs）: [docs/specs/colima-idle-stop/](../../specs/colima-idle-stop/README.md)。当初は「開発機（Mac）の保守道具で製品の機能領域ではない（前例 disk-janitor と同扱い）」として対象外と判断したが、2026-10-15 に PO が最終報告の「作らない判断でよいか（y/n）」に N と答えたため、別 PR で作成した。
v1 審査（Fable REVISE: /tmp/CC報告ファイル/ac-heavy/docker-idle/review-design1.md）の指摘 MEDIUM-1〜5・LOW-6〜10 を本版で反映。
PO 決定（2026-10-15 チャット、y）: 「15分ごとに見回り、DB 接続なし・CPU ほぼ0 が30分続いたら Docker を自動で止める」。

## 1. 目的と成功条件
- 目的: 使い終わった Colima（profile default、2GiB 確保）が動き続けて 8GB の Mac のメモリを圧迫するのを止める（recon「現在地」: VM 2060M、unused 149M）。
- KGI: 使われていない Colima default が、最後に使われた時刻から **60 分以内** に止まり、`colima status -p default` が停止を示す。内訳: 通常 45 分（最初に未使用を見つけるまで最大15分＋判定30分）。見回りの時刻ずれで 1800 秒にわずかに届かなかった回は次の見回りに回るため、最悪 60 分（LOW-6）。
- 使用中（DB 接続あり・CPU 使用・docker/colima/psql の操作中）の間は止まらない。判定に失敗したときも止めない。
- Mac のスリープ中も時計は進む。スリープ前に未使用を記録していれば、復帰直後の見回りで止まることがある（止めるのは未使用のときだけなので許容。§5）。

## 2. 変更（新規3ファイル＋手順書1節のみ・既存の動作は変えない）
1. `scripts/colima-idle-stop.sh`（新規。disk-janitor.sh の作法に揃える: 設定1か所・`CIS_` 環境変数で上書き・source 可能・ログ自前 1MB ローテーション）
   - 設定（冒頭1か所）: `CIS_PROFILE=default`、`CIS_IDLE_SECONDS=1800`、`CIS_CPU_BUSY=1.0`、`CIS_STATE_DIR=$HOME/Library/Application Support/colima-idle-stop`、`CIS_LOG=$HOME/Library/Logs/colima-idle-stop.log`、`CIS_LOCK_DIR=/tmp/colima-idle-stop.lock.d`、`CIS_LIMA_HOME=$HOME/.colima/_lima`、`CIS_LIMA_INSTANCE=colima`（profile default の Lima 名）。
   - 排他（MEDIUM-4）: `mkdir "$CIS_LOCK_DIR"` に成功したら中に `pid` ファイル（自分の PID）を書き、trap EXIT で消す。失敗したら `pid` を読み、`kill -0` で生きていれば `result=skip` をログして終了 0。死んでいる・pid が読めない場合は `stale lock removed (pid=…)` をログしてロックを消し、1回だけ取り直す（2回目も失敗なら終了 0）。
   - 判定は **次の順に1つずつ**（並列にしない）。結論が出たらそこで終わる（MEDIUM-2）。
     1. 状態: `colima status -p default` を実行。exit 0 → 起動中として次へ。exit 0 以外 **かつ** 出力に `is not running` を含む → 停止中: 状態ファイルを消し `result=stopped` を記録して終了 0。それ以外の失敗 → 判定失敗（reason=d）（LOW-9）。
     2. c. 操作中プロセス: 自分が docker を呼ぶ **前に** `pgrep -f` を実行する（自分の docker 呼び出しを数えないため。pgrep 自身とその祖先は pgrep が除外する）。パターンは3つ: `(^|/)docker(-compose)? (compose|run|exec|build|cp|pull|push|start|attach|logs|up)`（`docker-compose up` も当たる。v2 審査 LOW-11）、`(^|/)colima (start|ssh|restart)`、`(^|/)psql( |$)`（Mac 側の psql クライアント）。1件以上 → 使用中（reason=c）。pgrep の exit 1（0件）は「無し」、exit 2 以上は判定失敗（reason=d）。
     3. a. CPU: `docker ps --filter status=running --format '{{.Names}}<TAB>{{.Image}}'` で動いているコンテナを列挙する（exit 0 で出力空＝コンテナ0件。0件なら a・b は「無し」として 5 へ）。`docker stats --no-stream --format '{{.Name}}<TAB>{{.CPUPerc}}'` の CPU（`%` を外した数値）がどれか `CIS_CPU_BUSY` 以上 → 使用中（reason=a）。どちらかの exit が 0 以外、または数値として読めない行があれば判定失敗（reason=d）。
     4. b. DB 接続: 列挙したコンテナのうちイメージ名が `^postgres(:|@|$)` に当たるもの（例 `postgres:16`）それぞれで、次のコマンドの出力が 1 以上 → 使用中（reason=b）。出力が整数でない・exit 0 以外 → 判定失敗（reason=d）。  
        `docker exec <名前> sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atc "select count(*) from pg_stat_activity where backend_type = '"'"'client backend'"'"' and pid <> pg_backend_pid()"'`
     5. ここまで何も当たらない → 未使用。
   - 判定失敗（reason=d）は使用中と同じに扱う（止めない側に倒す）。ログに失敗したコマンドと exit コードを残す。
   - 使用中 → 状態ファイルを消して終了 0。
   - 未使用 → VM の同一性を確かめる（MEDIUM-3）: `$CIS_LIMA_HOME/$CIS_LIMA_INSTANCE/ha.pid`（Lima の hostagent の PID）を読む。読めない・数字でない場合は判定失敗（reason=d）。状態ファイル `$CIS_STATE_DIR/idle-since` は1行 `<epoch秒> <ha.pid の値>`。
     - 状態ファイルが無い・形が壊れている・記録の PID が今の ha.pid と違う → 今の時刻と PID で書き直して終了 0（1回目扱い。再起動した VM に古い記録を使わない）。
     - 同じ PID で、経過が `CIS_IDLE_SECONDS` 以上 → `colima stop -p default` を1回実行し、終了コード・所要秒・実行後の `colima status -p default` の exit コードを記録して状態ファイルを消す。stop が失敗したら exit 1（launchd の last exit code に出す）。
     - 未満 → 経過秒を記録して終了 0。
   - `--dry-run`: 判定と状態ファイルの更新までは同じに行い、`colima stop` だけ実行せず `result=would-stop` を記録する。
   - ログ: `$CIS_LOG`。各回1行以上、`<ISO時刻> result=<stopped|busy|idle|would-stop|stop-ok|stop-fail|skip> reason=<a|b|c|d|-> elapsed=<秒|-> detail=<短い説明>`。
   - 実装前の実物確認（Generator）: `ha.pid` が上記パスにあり、値が `limactl hostagent` の PID と一致すること。違えば BLOCKED で報告する（推測でパスを変えない）。
2. `ops/launchd/jp.salesanchor.colima-idle-stop.plist`（新規）: **読み取りだけ**で動かす（MEDIUM-1）。fetch・checkout はしない。道具のコピーの更新は disk-janitor の毎日 04:00 に任せる。ProgramArguments は `/bin/bash`・`-lc`・次の1行:  
   `T=/Users/tanizawashingo/.salesanchor-tools; if [ -d /tmp/disk-janitor.lock.d ]; then echo "colima-idle-stop: disk-janitor 実行中のため今回は見送り"; exit 0; fi; test -z "$(git -C "$T" --no-optional-locks status --porcelain --untracked-files=all)" && git -C "$T" merge-base --is-ancestor HEAD origin/main && cd "$T" && bash scripts/colima-idle-stop.sh || { echo "colima-idle-stop: 道具のコピーが確認できないため実行しない" >&2; exit 1; }`  
   - `--no-optional-locks` で index.lock を取りにいかない。
   - HEAD が origin/main に含まれるコミット（main に入った版）であることだけを確かめる。完全一致にしない理由: origin/main は共有 .git への他セッションの fetch で1日数十回動き、道具のコピーは janitor が1日1回しか進めないため、一致条件ではほぼ常に実行されない（v2 審査 HIGH-1、実機 recon3/c-head-check.txt）。
   - janitor 実行中は exit 0 で見送る（.err を汚さない。v2 審査 LOW-12）。
   - オフラインでも fetch しないので失敗しない。
   - `StartInterval` 900、`RunAtLoad` false、`KeepAlive` false。EnvironmentVariables の PATH は disk-janitor の plist と同じ値。StandardOutPath `/Users/tanizawashingo/Library/Logs/colima-idle-stop.out`、StandardErrorPath `/Users/tanizawashingo/Library/Logs/colima-idle-stop.err`。
3. `scripts/tests/test-colima-idle-stop.sh`（新規。test-disk-janitor.sh の作法）: mktemp 領域に偽の colima/docker/pgrep と偽の ha.pid を置き、`CIS_*` を一時領域へ向けて次を確かめる。
   - T1 停止中（exit 1＋`is not running`）→ stop を呼ばない・状態ファイルなし・result=stopped
   - T1b colima status が exit 1 で `is not running` を含まない → reason=d・stop を呼ばない
   - T2 DB 接続1件 → reason=b・状態ファイルが消える
   - T3 CPU 5% → reason=a
   - T4 docker compose 実行中（pgrep が1件）→ reason=c、かつ偽 docker が一度も呼ばれていない（順序の確認）
   - T5 docker stats が失敗 → reason=d（止めない）
   - T5b psql の出力が整数でない → reason=d
   - T6 未使用1回目 → 状態ファイル作成（`<epoch> <pid>`）・stop を呼ばない
   - T7 未使用で状態ファイルが 1800 秒前・同じ PID → stop を `-p default` 付きで1回呼ぶ・状態ファイルが消える
   - T8 未使用で 1790 秒前 → stop を呼ばない（1799 だと試験中に秒をまたいで稀に 1800 になるため余裕を取る。コード審査 MEDIUM-1）
   - T9 `--dry-run` で T7 の条件 → stop を呼ばない・would-stop
   - T10 状態ファイルが 3600 秒前だが PID が違う → stop を呼ばず、新しい時刻と PID に書き直す
   - T11 コンテナ0件（docker ps が exit 0・出力空）→ 未使用として扱う
   - T12 ロックが死んだ PID で残っている → stale を記録して実行される／生きた PID なら skip
   - T13 ha.pid が無い → reason=d・stop を呼ばない
4. `docs/ops/runner-commands.md`: disk-janitor 節の後に「Docker（Colima）の自動停止」節を追加する。中身: 設置・確認・すぐ1回・dry-run・停止・ログの見方・「DB に繋がらないときは `colima start`」・道具のコピーは disk-janitor が毎日更新すること。

## 触らない
- disk-janitor.sh・その plist・docker-compose.yml・colima.yaml・他の profile（sa-private-ci 等）・CI・ADR。
- `colima delete` やディスク削除はしない（止めるだけ。`colima stop` は状態を保存する: recon「判定コマンドの実測」）。

## 3. 代替案と選択理由
- 案A（採用）: 見回り役が条件を見て `colima stop`。理由: 既存 disk-janitor と同じ作り方で増える仕組みが最小、止める判断を記録できる。
- 案B: Docker Desktop の Resource Saver に乗り換え。不採用: アプリ入替が大きく、既存の Colima 前提の手順（recon の docs 9件）を変える必要。
- 案C: コンテナの RestartPolicy を止める。不採用: VM（2GiB）自体は残るので効果が無い。
- 見回りのたびに fetch・checkout する案（v1）: 不採用。15 分ごとに janitor の 04:00 更新と index.lock を取り合い、オフライン時は毎回失敗するため（v1 審査 MEDIUM-1）。

## 4. 受入と検証
| 基準 | 検証方法 |
|---|---|
| K1 T1〜T13 がすべて通る | `bash scripts/tests/test-colima-idle-stop.sh` の生出力で全件 PASS・FAIL 0 |
| K2 plist が正しい | `plutil -lint` が OK／`plutil -extract ProgramArguments.2 raw` が §2-2 の1行と完全一致／`StartInterval`=900・`RunAtLoad`=false・`KeepAlive`=false |
| K3a 設置環境で判定できる（LOW-9） | 設置前に plist と同じ条件（`env -i HOME=$HOME PATH=<plist の PATH> bash -lc '… bash scripts/colima-idle-stop.sh --dry-run'`）で実行し、ログの reason が d でない |
| K3 実機: 未使用なら止まる | 状態ファイルに「1900 秒前・今の ha.pid」を書いて `launchctl kickstart gui/$(id -u)/jp.salesanchor.colima-idle-stop` → ログに `result=stop-ok`、`colima status -p default` が exit 1＋`is not running`、`pgrep -f Virtualization.VirtualMachine` が0件（sa-private-ci が停止中のとき） |
| K4 実機: 止まった後に再開できる | `colima start` → `docker ps` に salesanchor-postgres-1 が healthy で戻る |
| K5 実機: 使用中は止まらない（LOW-8） | `docker exec salesanchor-postgres-1 psql -U <user> -d postgres -c "select pg_sleep(300)"` を裏で開いたまま、状態ファイルを 1900 秒前にして kickstart → ログに `result=busy`（reason=b、または docker exec を見つけた reason=c）、Colima は起動したまま |

## 5. 安全と戻し方
- 止めない側に倒す（判定失敗＝使用中）。止めるのは default だけ、`colima stop`（状態保存）だけ。
- 戻し方: `launchctl bootout gui/$(id -u)/jp.salesanchor.colima-idle-stop` と plist 削除。止まった Colima は `colima start` で戻る。
- 既知の制約: スリープ中も経過時間に数える（§1）。15 分ごとの見回りなので、見回りと見回りの間だけ短く使われた場合は見落とす（その場合も、次の見回りで CPU・接続が無ければ止まるだけで、データは失われない）。

## 6. 外部・過去事例の参照と我々への応用
- Docker 公式 Docker Desktop「Resource Saver mode」（https://docs.docker.com/desktop/use-desktop/resource-saver/ 、2026-10-15 取得）: 「no containers are running for a period of time」で Linux VM を自動停止、既定 5 分、必要時に 3〜10 秒で自動再開。応用: 「使っていなければ VM ごと止める」という考え方は同じ。ただし当方は postgres コンテナが常時動く（RestartPolicy unless-stopped）ため「コンテナ0件」は使えず、接続数と CPU で判定する。自動再開は無いので手順書に `colima start` を書く。
- 過去事例: disk-janitor（docs/handoff/disk-janitor/design.md）の道具専用コピー・試験の作り方を使う。ただし更新（fetch/checkout）は janitor に任せ、本件は読み取りだけにする。
- Context7 は月間上限で利用不可（2026-10-15）。Colima の仕様は実物 `colima stop --help`（0.10.3）で確認。

## 7. 維持の仕組み
- 見回り役自身のログ（毎回1行以上）で動作が見える。`launchctl print` の last exit code で異常が分かる。
- 試験 scripts/tests/test-colima-idle-stop.sh が判定の正しさを固定する。
- 手順の正本は docs/ops/runner-commands.md の新節。

## 関係する ADR
- ADR-136（scripts/・ops/launchd/ は危険パス＝GO 必須）。ADR-1015（区分 A）。ADR-135（PO GO まで main に入れない）。
- ADR の追加・改訂は **しない**。理由: ADR-114 は作業フォルダ回収の決定で、本件（Docker の停止）は範囲外。本件は既存の作り方（disk-janitor）の再利用で新しい技術判断を含まない。判断の正本は本 design.md と docs/ops/runner-commands.md の節とする。
