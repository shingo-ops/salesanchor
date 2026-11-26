# 実装カード: 試しの導入台本の直し 1（審査 2026-11-26 REVISE への対応）

- 正の設計: `docs/handoff/ai-ops-247/server-agent-design.md` §12-3 の 2〜5（442ed09dd 以降の版）
- 元の台本: `docs/handoff/ai-ops-247/trial-install/`（8757d675e）
- 触る: 01-prepare.sh・03-po-login.md・04-check-and-start.sh・06-rollback.sh・新しく 03b-put-discord-keys.sh・このカード末尾の「結果」欄
- 触らない: 02-install.sh・05-daily-read.sh・設計書・ほかのすべて。サーバーには繋がない。鍵の値を書かない

## 直すこと

### 1. 01-prepare.sh（立ち上げ直し）

- 111 行 `Restart=on-failure` → `Restart=always`。112 行 `RestartSec=30` はそのまま。
- `[Unit]`（96 行）の中に `StartLimitIntervalSec=600` と `StartLimitBurst=5` を足す（`[Service]` ではなく `[Unit]` に置く。systemd の公式 systemd.unit「StartLimitIntervalSec=」）。
- 22 行付近の注記を「正常に終わっても立ち上げ直すため always。10 分に 5 回で止まり、毎日の確認で見つける」に直す。

### 2. 新しく 03b-put-discord-keys.sh（管理者が `sudo bash 03b-put-discord-keys.sh` で流す）

- `set -euo pipefail`・root でなければ止まる・`id ops-agent` が無ければ止まる。
- `read -rs -p "ボットの鍵を貼って Enter（画面に出ません）: " TOKEN`、空なら止まる。値は表示しない・ログに出さない・`set -x` を使わない。
- `read -r -p "PO の Discord の利用者番号（数字）: " UID_PO`。`^[0-9]{17,20}$` に合わなければ止まる。
- 場所: `D=/home/ops-agent/.claude/channels/discord`。`/home/ops-agent/.claude`・`.../channels`・`$D` のどれかが symlink なら止まる（`test -L`）。`install -d -o ops-agent -g ops-agent -m 700` で 3 段とも作る。
- `umask 077` の下で、`$D/.env` に 2 行 `DISCORD_BOT_TOKEN=<値>` と `DISCORD_ACCESS_MODE=static` を書く（`printf '%s\n'` で。ファイルが symlink なら先に止まる）。
- `$D/access.json` に `{"dmPolicy":"allowlist","allowFrom":["<番号>"],"groups":{},"pending":{}}` を書く。
- 両方 `chown ops-agent:ops-agent`・`chmod 600`。最後に `ls -l` で 2 つの持ち主と権限だけを表示（中身は出さない）。
- `unset TOKEN`。
- 出どころを台本の頭に書く: 道具の本体 `external_plugins/discord/server.ts`（anthropics/claude-plugins-official 668a0c65）39-56 行（.env の読み方・`DISCORD_ACCESS_MODE=static`）・183-200 行（static では名簿を書き換えない）、`ACCESS.md` の Config file 欄。

### 3. 03-po-login.md

- D を次の順に書き直す（`/discord:configure` と `/discord:access` は使わない。理由を 1 行: 中で Write の道具を使い、01 の制限で止まる・鍵が会話の記録に残る）:
  1. B の窓のシェル（`claude` の外）で `claude plugin install discord --marketplace anthropics/claude-plugins-official -s user`。
  2. 窓を閉じる。管理者が `sudo bash 03b-put-discord-keys.sh` を流し、PO が見えない入力にボットの鍵と自分の利用者番号を貼る。
  3. ここではペア（合言葉）も `/discord:access policy allowlist` も要らない（名簿は 03b で allowlist に置いた）。
- A に「Public Bot を切る」「Discord の設定 → 詳細設定 → 開発者モードを入れ、自分のアイコンを右クリックして『ユーザーIDをコピー』で番号を控える」を足す。
- C に「作業の場所を信頼するか聞かれたら『はい』」を足す。
- 「止まったとき」の D の項は、`claude plugin install` が失敗したら画面の言葉をそのまま設計担当へ、に直す。`settings.json` をゆるめない、は残す。

### 4. 04-check-and-start.sh（確かめに対照を足す）

- 確かめの前に `run_as_agent /bin/true`（G2・G7・G8 の同じ値）が 0 で終わることを確かめる。0 でなければ「上限の書き方が違う」として止まる（FAILS とは別に exit 1）。
- G7: 守りを外した窓（G2・G8 だけ・G7 なし）で `curl -m 5 -sS -o /dev/null http://127.0.0.1:19187/metrics` が 0 で終わることを先に確かめる。届かなければ「確かめにならない」として FAILS に足す。そのあと今の 71 行の expect_fail を流す。72 行（3000 番）も同じ対照を付ける。
- G8: 91〜93 行の expect_fail をやめ、`stat -c %a <場所>` に置き換える。守りの下（G2・G7・G8）で `/home/ubuntu`・`/root`・`/opt/salesanchor-monitoring` の 3 つとも `0` なら ○。守りの外（G2 だけ）で同じ 3 つが `0` 以外なら ○（どちらかが違えば FAILS に足す）。出どころ: systemd の CONTAINER_INTERFACE「all zero access mode」と namespace.c の MOUNT_INACCESSIBLE。
- G4 の確かめに、`~/.claude/channels/discord/.env` と `access.json` の持ち主が ops-agent・権限が 600 であること（`stat -c '%U %a'`）を足す。中身は読まない。

### 5. 06-rollback.sh

- 手で行うことの案内に「Discord の Developer Portal でボットを消すか鍵を作り直す」が既にあれば変えない。無ければ足す。`userdel -r` で `.env` も消えることを 1 行書く。

## 確かめ（実装役が行う）

- `bash -n` を 01・03b・04・06 で通す。`shellcheck` があれば流し、無ければ「未実施」と書く。
- `grep -n 'Restart=' 01-prepare.sh` が `Restart=always` 1 件。
- `grep -n -E 'discord:configure|discord:access' 03-po-login.md` が「使わない理由」の行だけ。
- 台本の中に鍵の値・利用者番号の実際の値が 0 件。

## 結果

- 直した: 01（always・[Unit] に StartLimit 2 行・注記）・03b 新規・03・04（/bin/true 対照・G7 対照・G8 を stat -c %a に・G4 の持ち主と権限）・06（userdel -r で .env も消える旨を 1 行。Developer Portal の案内は既にあったので変更なし）。
- bash -n: 01・03b・04・06 すべて通過。shellcheck: 未実施（この環境に無い）。
- grep 'Restart=' 01-prepare.sh: Restart=always の 1 件。
- grep discord:configure|discord:access 03-po-login.md: 「使わない理由」の 1 行のみ。
- 鍵の値・利用者番号の実際の値: 0 件。
- 未実施: 実機での動作確認（サーバーには繋いでいない）。
