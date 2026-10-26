# Self-hosted Runner コマンドリファレンス

salesanchor の self-hosted runner（Hitoshi の Mac, agentName: `Hikky-dev-Mac`）操作に必要なコマンド集。

トラブル時・再登録時・日常確認に使う。背景は [`self-hosted-runner-credential-trap.md`](./self-hosted-runner-credential-trap.md)。

---

## 1. ローカル runner 操作（zsh エイリアス）

`~/.zshrc` に定義済（Hitoshi の Mac）:

| エイリアス | 実体 | 用途 |
|---|---|---|
| `runner-start` | `cd ~/actions-runner && nohup ./run.sh > runner.log 2>&1 &` | バックグラウンド起動 |
| `runner-status` | `ps aux \| grep -i Runner.Listener \| grep -v grep` | 稼働確認 |
| `runner-log` | `tail -f ~/actions-runner/runner.log` | ログ追従 |
| `runner-stop` | `pkill -f Runner.Listener` | 停止 |

## 2. ローカル runner 直接操作（生コマンド）

```bash
# 起動（対話モード／ターミナル占有）
cd ~/actions-runner && ./run.sh

# 起動（バックグラウンド）
cd ~/actions-runner && nohup ./run.sh > runner.log 2>&1 & disown

# 停止（gracefully）
kill -TERM <PID-of-run.sh>     # 親プロセスから順に伝播

# 強制停止（最後の手段）
pkill -9 -f Runner.Listener

# 状態詳細
ps aux | grep -E "Runner.Listener|run-helper.sh|/run\.sh" | grep -v grep
cat ~/actions-runner/.runner            # agentName, agentId, server URL
ls -la ~/actions-runner/_diag/ | head   # 直近 diag log
```

## 3. ログ確認・解析

```bash
# ローカル listener log
tail -f ~/actions-runner/runner.log
tail -100 ~/actions-runner/runner.log

# 最新の Worker (job 実行) ログ
ls -1t ~/actions-runner/_diag/Worker_*.log | head -1 | xargs tail -200

# Listener (接続) ログ
ls -1t ~/actions-runner/_diag/Runner_*.log | head -1 | xargs tail -100
```

## 4. GitHub 側状態確認（gh CLI）

```bash
# 直近 workflow run（status / conclusion）
gh run list --workflow="Claude Max Auto-Pipeline (Partner Subscription)" --limit 5 \
  --json databaseId,status,conclusion,createdAt,event,headBranch \
  -q '.[] | "\(.createdAt) | id=\(.databaseId) | \(.status)/\(.conclusion) | branch=\(.headBranch)"'

# 走行中ジョブ
gh run list --status in_progress --limit 5
gh run list --status queued --limit 5

# 特定 run の詳細
gh run view <RUN_ID> --json status,conclusion,jobs

# 特定 run のステップ別結果
gh run view <RUN_ID> --json jobs -q '.jobs[].steps[]|{name, conclusion}'

# 失敗ステップのみ生ログ取得
gh run view <RUN_ID> --log-failed

# 全ログ（grep 用）
gh run view <RUN_ID> --log | grep "Checkout Code"
gh run view <RUN_ID> --log | grep -E "Runner name|Machine name"
```

> **Note**: Hikky-dev は repo admin ではないため、`gh api .../runners` 系の admin API は 403。Runners 一覧などは Web UI (`https://github.com/shingo-ops/salesanchor/settings/actions/runners`) を使う。

## 5. Workflow dispatch（手動起動）

```bash
# 必ず --ref を指定（省略すると default branch = main で実行される！）
gh workflow run "Claude Max Auto-Pipeline (Partner Subscription)" \
  --ref develop \
  -f adr_files=docs/adr/ADR-NNN.md

# テスト用（no-op の ADR-999）
gh workflow run "Claude Max Auto-Pipeline (Partner Subscription)" \
  --ref develop \
  -f adr_files=docs/adr/ADR-999-pipeline-test.md

# 直前の dispatch 確認
gh run list --workflow="Claude Max Auto-Pipeline (Partner Subscription)" --limit 1

# dispatch 後にライブで進行をフォロー
gh run watch <RUN_ID>
```

## 6. 再登録 / 改名手順

```bash
# Step 0: 安全確認
gh run list --status in_progress      # 空であること
gh run list --status queued           # 空であること
ps aux | grep "Runner.Worker" | grep -v grep   # 空であること

# Step 1: registration token を Web UI から取得
# https://github.com/shingo-ops/salesanchor/settings/actions/runners/new
# → "AABBCC...XXXXX" の英数字部分をコピー（1時間で expire）

# Step 2: listener 停止
runner-stop

# Step 3: 旧登録解除
# ※ 同一 registration token を Step 4 でも再利用できる（remove と register で 2 回消費可）
cd ~/actions-runner
./config.sh remove --token <TOKEN>

# Step 4: 新名で再登録（Step 3 と同じ TOKEN でOK）
./config.sh \
  --url https://github.com/shingo-ops/salesanchor \
  --token <TOKEN> \
  --name "Hikky-dev-Mac" \
  --labels "self-hosted,macOS" \
  --unattended

# Step 5: 再起動
runner-start

# Step 6: 動作確認
cat ~/actions-runner/.runner | grep agentName    # "Hikky-dev-Mac" のはず
runner-status
gh workflow run "Claude Max Auto-Pipeline (Partner Subscription)" --ref develop \
  -f adr_files=docs/adr/ADR-999-pipeline-test.md
```

## 7. トラブル診断クイックチェック

```bash
# 「workflow が動かない」時の切り分け順序

# (1) リスナー生きてる？
runner-status
# → 出力なし: runner-start で起動

# (2) GitHub と接続されてる？
tail -20 ~/actions-runner/runner.log
# → "Listening for Jobs" があれば OK

# (3) ジョブを受け取った形跡は？
grep "Running job" ~/actions-runner/runner.log | tail -5

# (4) job 失敗の生ログ
gh run view <FAILED_RUN_ID> --log-failed

# (5) Checkout が失敗してる？
gh run view <FAILED_RUN_ID> --log | grep "Checkout Code" | grep -E "error|fatal" | head -10
```

## 8. PAT / Secret 関連

```bash
# PIPELINE_PAT rotation 期限チェック（90日サイクル, 2026-08-05 失効目安）
gh issue view 300 --repo shingo-ops/salesanchor

# secret の存在確認（中身は不可視）
gh api /repos/shingo-ops/salesanchor/actions/secrets --jq '.secrets[].name'

# secret 作成・更新は Web UI のみ:
# https://github.com/shingo-ops/salesanchor/settings/secrets/actions
```

---

## 9. Shingo-Mac-Temp: launchd 管理（svc.sh）

**実パス**: `~/actions-runner-shingo/`（`~/actions-runner` ではない）  
**agentName**: `Shingo-Mac-Temp`  
**管理方式**: svc.sh による LaunchAgent（ADR-029 Amendment 2026-06-18）

```bash
# --- runner 自動起動化（初回のみ）---
cd ~/actions-runner-shingo
ps aux | grep Runner.Listener | grep -v grep   # 手動起動プロセスがあれば停止
./svc.sh install    # ~/Library/LaunchAgents/actions.runner.*.plist を生成・登録
./svc.sh start
./svc.sh status     # "Started" + PID が表示されれば成功

# --- 日常確認 ---
./svc.sh status
launchctl list | grep actions.runner

# --- 停止・アンインストール（ロールバック）---
./svc.sh stop
./svc.sh uninstall
```

### 起動時 worktree 自動回収（起動時 reaper）

`ops/launchd/jp.salesanchor.reaper-onlogin.plist` を配置・load することで  
ログイン時に `reaper-worktree.sh --execute` が自動実行される（ADR-114 PR-C）。

```bash
# 配置（初回のみ）
cp ops/launchd/jp.salesanchor.reaper-onlogin.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist

# 動作確認
launchctl list | grep reaper
tail ~/Library/Logs/reaper-onlogin.log

# 無効化
launchctl unload ~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist
```

### 毎日の開発データ自動片付け（disk-janitor）

`ops/launchd/jp.salesanchor.disk-janitor.plist` を配置すると、毎日 04:00 に道具専用の作業用コピー `/Users/tanizawashingo/.salesanchor-tools` を `origin/main` に更新してから `scripts/disk-janitor.sh --execute` が動く。
消すのは根5か所の中で、作り直せる物（散らばった `.npm-cache`、使っていない作業用コピーの `node_modules`、agent-console の旧版）と、
reaper の安全条件を満たす他リポジトリの作業用コピーだけ。設計: `docs/handoff/disk-janitor/design.md`（改訂 3・3a・3b）、ADR-114。

本体 `/Users/tanizawashingo/salesanchor` は古いまま・未コミットの変更が多いので、janitor は本体ではなく道具のコピーから動かす。

**道具のコピーでは作業しない**（人も AI も。編集・コミット・未追跡ファイルの作成も禁止）。plist は、コピーが完全にきれい（未コミット・未追跡が0）で、fetch と checkout の後に HEAD が `origin/main` と同じときだけ janitor を動かす。そうでなければ何も消さず、終了コード 1 で終わる。

```bash
# 道具のコピーの作成（手で1回だけ。new-worktree.sh は detached を作れない）
git -C /Users/tanizawashingo/salesanchor worktree add --detach /Users/tanizawashingo/.salesanchor-tools origin/main

# 作り直し（壊れた・きれいでなくなったとき。コピーの中身は捨ててよい物だけ）
git -C /Users/tanizawashingo/salesanchor worktree remove --force /Users/tanizawashingo/.salesanchor-tools
git -C /Users/tanizawashingo/salesanchor worktree add --detach /Users/tanizawashingo/.salesanchor-tools origin/main

# 事前: 何が消えるかを確認（dry-run。何も消えない）
cd /Users/tanizawashingo/.salesanchor-tools && bash scripts/disk-janitor.sh

# plist の確認（lint と、実行する1行の復元）
plutil -lint ops/launchd/jp.salesanchor.disk-janitor.plist
plutil -extract ProgramArguments.2 raw ops/launchd/jp.salesanchor.disk-janitor.plist

# 設置（初回のみ）
cp ops/launchd/jp.salesanchor.disk-janitor.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.salesanchor.disk-janitor.plist

# 確認（state・runs・last exit code。正常は 0）
launchctl print gui/$(id -u)/jp.salesanchor.disk-janitor
diff ops/launchd/jp.salesanchor.disk-janitor.plist ~/Library/LaunchAgents/jp.salesanchor.disk-janitor.plist

# すぐ1回動かす
launchctl kickstart -k gui/$(id -u)/jp.salesanchor.disk-janitor

# 停止（止めた後の再開は bootstrap）
launchctl bootout gui/$(id -u)/jp.salesanchor.disk-janitor
```

ログの見方:
- `~/Library/Logs/disk-janitor.log`: janitor 自身が書く。開始・規則ごとの結果・終了と前後の `df`。`tail -50` で見る（1MB 超で `.log.1` に1世代だけ退避）。
- `~/Library/Logs/disk-janitor.err`: 起動直後の異常。正常時は空。
- 失敗時: コピーの更新・確認に失敗すると janitor は動かず、`.err` に「disk-janitor: 道具のコピーの更新・確認に失敗したため実行しない」と出て、`launchctl print` の last exit code が 1 になる。原因（未追跡ファイル・未コミットの変更など）を確認し、必要なら上の「作り直し」を行う。

消された物の作り直し: salesanchor は `npm ci --prefix frontend`、agent-console は `npm ci`（pre-commit の lint-staged が node_modules を使うため）、agent-console の版は ac-install、作業用コピーは `git worktree add`。


### Docker（Colima）の自動停止（colima-idle-stop）

`ops/launchd/jp.salesanchor.colima-idle-stop.plist` を配置すると、15 分ごとに `scripts/colima-idle-stop.sh` が Colima（profile default）を見回る。
DB 接続なし・CPU ほぼ 0（コンテナごとに 1.0% 未満）・`docker compose` や `psql` などの操作中プロセスなしが 30 分続いたら `colima stop -p default` を 1 回だけ実行する（状態は保存される）。
判定に失敗したときは止めない。止めるのは default だけで、`colima delete` やディスク削除はしない。設計: `docs/handoff/colima-idle-stop/design.md`。

道具のコピー `/Users/tanizawashingo/.salesanchor-tools` は読み取りだけで使う（fetch・checkout はしない）。コピーが新しい版になるまでは動かない。disk-janitor が毎日 04:00 にコピーを更新するので、PR を main に入れた後は翌 04:00 以降に動き始める。

```bash
# plist の確認（lint と、実行する1行の復元）
plutil -lint ops/launchd/jp.salesanchor.colima-idle-stop.plist
plutil -extract ProgramArguments.2 raw ops/launchd/jp.salesanchor.colima-idle-stop.plist

# 設置（初回のみ）
cp ops/launchd/jp.salesanchor.colima-idle-stop.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.salesanchor.colima-idle-stop.plist

# 確認（state・runs・last exit code。正常は 0）
launchctl print gui/$(id -u)/jp.salesanchor.colima-idle-stop
diff ops/launchd/jp.salesanchor.colima-idle-stop.plist ~/Library/LaunchAgents/jp.salesanchor.colima-idle-stop.plist

# すぐ1回動かす
launchctl kickstart -k gui/$(id -u)/jp.salesanchor.colima-idle-stop

# dry-run（判定と状態ファイル更新まで。colima stop だけ実行しない）
cd /Users/tanizawashingo/.salesanchor-tools && bash scripts/colima-idle-stop.sh --dry-run

# 停止（止めた後の再開は bootstrap）
launchctl bootout gui/$(id -u)/jp.salesanchor.colima-idle-stop
```

ログの見方:
- `~/Library/Logs/colima-idle-stop.log`: 見回り自身が書く。1回1行以上、`result=<stopped|busy|idle|would-stop|stop-ok|stop-fail|skip> reason=<a|b|c|d|->`（a=CPU、b=DB 接続、c=操作中プロセス、d=判定失敗）。`tail -50` で見る（1MB 超で `.log.1` に1世代だけ退避）。
- `~/Library/Logs/colima-idle-stop.err`: 起動直後の異常。正常時は空。「道具のコピーが確認できない」はコピーが未コミット・未追跡できれいでない、HEAD が `origin/main` に含まれない、のときだけでなく、スクリプトの `colima stop` 失敗でも出る。区別はログの `result=stop-fail` で行う。
- 状態ファイル: `~/Library/Application Support/colima-idle-stop/idle-since`（`<epoch秒> <ha.pid>`）。

止まった後に DB に繋がらないときは `colima start`（自動再開は無い）。起動後 `docker ps` で `salesanchor-postgres-1` が healthy で戻ることを確かめる。

### Mac の自動お手入れの見張り（mac-jobs-watch）

`ops/launchd/jp.salesanchor.mac-jobs-watch.plist` を配置すると、30 分ごと（とログイン時）に `scripts/mac-jobs-watch.sh` が、Docker の自動停止（colima-idle-stop）と毎日の自動片付け（disk-janitor）を見張る。止まった・読み込みから外れた・失敗した、のどれかが起きたら Discord へ知らせる（新しく起きたとき・24 時間続いたとき・直ったときの 3 種。同じ回の分は 1 通にまとまる）。再起動後の最初の回には「起動後の点検」を 1 通送る。設計: `docs/handoff/mac-jobs-watch/design.md`。

通知先は ADR-1009 の番人と同じ `~/.config/sa-ops-intake/watchdog-webhook`（読むだけ。作り直し・権限変更はしない）。URL は画面・ログ・引数に出さない。見張り役自身が止まったことは検知できない（Mac の外に見張りが無い）。

自動片付けの時刻（`ops/launchd/jp.salesanchor.disk-janitor.plist` の `Hour`）を変えたら、`scripts/mac-jobs-watch.sh` の設定 `MJW_DJ_HOUR` も合わせること（ずれると「毎日の自動片付けが動いていません」の誤報や見逃しが出る）。

```bash
# plist の確認（lint と、実行する1行の復元）
plutil -lint ops/launchd/jp.salesanchor.mac-jobs-watch.plist
plutil -extract ProgramArguments.2 raw ops/launchd/jp.salesanchor.mac-jobs-watch.plist

# 設置（初回のみ）
cp ops/launchd/jp.salesanchor.mac-jobs-watch.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.salesanchor.mac-jobs-watch.plist

# 確認（state・runs・last exit code。正常は 0）
launchctl print gui/$(id -u)/jp.salesanchor.mac-jobs-watch
diff ops/launchd/jp.salesanchor.mac-jobs-watch.plist ~/Library/LaunchAgents/jp.salesanchor.mac-jobs-watch.plist

# すぐ1回動かす
launchctl kickstart -k gui/$(id -u)/jp.salesanchor.mac-jobs-watch

# 送信の試験（Discord に「送信の試験です」を 1 通送る。状態は変えない）
cd /Users/tanizawashingo/.salesanchor-tools && bash scripts/mac-jobs-watch.sh --test-notify

# dry-run（判定してログに 1 行書くだけ。送らず、状態も変えない）
cd /Users/tanizawashingo/.salesanchor-tools && bash scripts/mac-jobs-watch.sh --dry-run

# 停止（止めた後の再開は bootstrap。状態を初期化するなら下の状態フォルダを消す）
launchctl bootout gui/$(id -u)/jp.salesanchor.mac-jobs-watch
```

ログの見方:
- `~/Library/Logs/mac-jobs-watch.log`: 見張り自身が書く。送った通知ごとに 1 行、何も送らなかった回は 1 行。`result=<ok|alert|repeat|recover|boot-notice|skip|no-webhook|test|dry-run> send=<ok|fail|-> problems=<今ある異常、無ければ -> events=<今回の出来事、無ければ -> awake=<1|0>`。`tail -50` で見る（1MB 超で `.log.1` に1世代だけ退避）。
- `~/Library/Logs/mac-jobs-watch.err`: 起動直後の異常。正常時は空。「道具のコピーが確認できない」は colima-idle-stop と同じ条件で出て、そのときだけ終了 1 になる（確認が通れば見張り本体の終了コードがそのまま launchd に返る）。`result=no-webhook`（終了 2）は通知先ファイルが読めない、`send=fail`（終了 3）は Discord への送信失敗（次の回にまた送る）。
- 状態フォルダ: `~/Library/Application Support/mac-jobs-watch/`（`state` と `problems`）。消すと初期化される（次の回が「初回」になり、点検が 1 通届く）。

---

## 10. 仮想マシンが要る試験（GitHub で行う）

この節が規則の正本（1 か所）。設計: [docs/handoff/vm-test-on-gha/design.md](../handoff/vm-test-on-gha/design.md)

規則: Mac で一時的な仮想マシン（colima profile の新規作成・limactl）を作らない。Docker が要る試験は sandbox-test で行う。

手順:
1. `tests/sandbox/<名前>.sh` を書いて push する（名前は英小文字・数字・ハイフン。置き方は tests/sandbox/README.md）
2. `gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>`
3. `gh run watch` で結果を見る

禁止: secrets・本番データ・本番への接続を使わない。公開リポジトリのためログは公開される。

例外: Mac 実機でしか試せないものは、その行に `vm-guard-allow: 理由` を付け、PR に理由を書く（no-mac-vm-guard が通す）。

開発用 DB（colima の profile default）は従来どおり使う。colima-idle-stop が自動停止する。

AI（Claude Code）は見張り mac-vm-guard（~/.claude/scripts/mac-vm-guard.py）で、default 以外の colima profile の作成・起動と limactl start/create/clone を実行前に止められる。（vm-guard-allow: 見張りの説明文。実行する命令ではない）
例外は PO が `! bash scripts/permit-danger.sh "mac vm"` で出す許可券だけ（1回限り・30分）。設計: [docs/handoff/mac-vm-hook/design.md](../handoff/mac-vm-hook/design.md)

---

## VPS コンテナの落とし穴

入口（CLAUDE.md・AGENTS.md）の同じ名前の節から、文を変えずに移しました（2026-10-23・ADR-1040 段3b）。

- `/app` は書込不可 → 出力先は `/tmp`
- `docker compose cp backend:/tmp/...` は使えない（tmpfs）→ `docker compose exec -T backend cat /tmp/xxx > host_file`
- コンテナ再起動で `/tmp` は消える

---

## 関連 doc

- [`self-hosted-runner-credential-trap.md`](./self-hosted-runner-credential-trap.md) — 2026-05-07 の事故と PIPELINE_PAT 導入の経緯
- Issue #300 — PAT rotation リマインダー
- PR #299 — checkout に PIPELINE_PAT 明示渡し
