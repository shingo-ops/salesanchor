# 実装カード: 試しの導入台本の直し 3（3回目の審査 2026-11-26 への対応）

- 正の設計: `docs/handoff/ai-ops-247/server-agent-design.md` §12
- 元の台本: `docs/handoff/ai-ops-247/trial-install/`（7b8e1ddce）
- 触る: 01-prepare.sh・03b-put-discord-keys.sh・04-check-and-start.sh・05-daily-read.sh・このカード末尾の「結果」欄
- 触らない: 02・03-po-login.md・06・設計書・ほかのすべて。サーバーには繋がない。鍵の値を書かない

## 直すこと

### 1. 04-check-and-start.sh（重い: 道具を入れた後も制限が残っているか）

- 「G4: 道具の制限の設定がある」の `grep -q '"defaultMode": "dontAsk"'` の if を消し、`python3 -c` 1 本に置き換える。JSON を読み、次の全部が成り立てば ○、1 つでも欠ければ ×（中身は表示しない）:
  - `permissions.defaultMode == "dontAsk"`
  - `permissions.allow` に `mcp__plugin_discord_discord__reply`・`__react`・`__fetch_messages` の 3 つ
  - `permissions.deny` に `Bash`・`Write`・`Edit`・`NotebookEdit`・`WebFetch`・`WebSearch`・`Agent`・`mcp__plugin_discord_discord__download_attachment`・`__edit_message`・`__create_thread`・`Read(//home/ops-agent/.claude/**)`・`Read(//home/ops-agent/.claude.json)` の 12 個（01-prepare.sh の一覧と同じ）
  - 行の名前は `G4 settings.json の制限（dontAsk・許す 3・断る 12）`

### 2. 04-check-and-start.sh（軽い: G8 の証拠でない確かめ）

- 最後の `echo "（注）..."` から「G8 の Read の確認は、Discord で…読めないと返ること。」の部分を消す。代わりに「G8 の証拠は上の stat の確かめだけ（Read は作業の場所の外なので、守りが無くても dontAsk で断られ、証拠にならない）。」を書く。G4 の最終確認の文は残す。

### 3. 04-check-and-start.sh（軽い: docker のつなぎ口が無いと素通り）

- 「G1: sudo も docker も使えない」の docker.sock の 2 つの確かめの前に、`test -S /run/docker.sock` が成り立たなければ `report "G1 /run/docker.sock がある" "ある" "無い" ng` を出す（成り立てば ok）。

### 4. 01-prepare.sh（軽い: 止める処理が失敗扱いになる）

- `ExecStop=/usr/bin/tmux` を `ExecStop=-/usr/bin/tmux` にする（先頭の `-` は失敗を無視する。出どころ: systemd の load-fragment.c の注記「"-": Ignore if the path doesn't exist」と systemd.service の ExecStart= の説明）。

### 5. 01-prepare.sh（軽い: IPv6 の注記だけ）

- G7 の `IPAddressDeny=` の上の注記に 1 行足す: `# IPv6: localhost は ::1/128 も含む（systemd.resource-control）。prod2 には全体向けの IPv6 アドレスも既定の道も無い（2026-11-26 ip -6 で確認）。` 値は変えない。

### 6. 03b-put-discord-keys.sh（軽い: 貼り付けの前後の空白）

- 鍵を読んだ直後（空かどうかの判定の前）に `TOKEN="${TOKEN//[[:space:]]/}"` を足す。利用者番号にも同じく `UID_PO="${UID_PO//[[:space:]]/}"` を、形の判定の前に足す。

### 7. 05-daily-read.sh（軽い: 動いているかの確かめ）

- 「担当 ops-agent」の `NRestarts` の後に、読むだけの 1 行を足す: `printf 'tmux の部屋: '; if sudo -u ops-agent tmux -S /home/ops-agent/.tmux/ops-agent.sock has-session -t ops-agent 2>/dev/null; then echo ある; else echo "無い  ← 要確認"; fi`

## 採らないもの（理由）

- 「01 を導入後も流し直せるように、止めずに設定だけ飛ばす」: 採らない。止めるほうが安全で、直すときは 06 で戻して最初から入れる手順が既にある。

## 確かめ（実装役が行う）

- `bash -n` を 01・03b・04・05 で通す。`shellcheck` があれば流し、無ければ「未実施」。
- `grep -c 'ExecStop=-/usr/bin/tmux' 01-prepare.sh` が 1。
- `grep -c '"defaultMode": "dontAsk"' 04-check-and-start.sh` が 0（文字列一致の判定が消えた）。
- 台本の中に鍵の値・利用者番号の実際の値が 0 件。

## 結果

実装役が 2026-11-26 に実施。カードの 1〜7 をすべてそのとおりに直した（触ったのは 01・03b・04・05 とこの欄だけ）。

- `bash -n`: 01・03b・04・05 すべて通った。
- `shellcheck`: この実行環境に無いので「未実施」。
- G4 の python 部分: 単体で構文確認のみ（py_compile 通過）。サーバー上での実行は未実施。
- `grep -c 'ExecStop=-/usr/bin/tmux' 01-prepare.sh` = 1。
- `grep -c '"defaultMode": "dontAsk"' 04-check-and-start.sh` = 0。
- 鍵の値・利用者番号の実際の値: 台本に書いていない（コードに値の直書き無し）。
