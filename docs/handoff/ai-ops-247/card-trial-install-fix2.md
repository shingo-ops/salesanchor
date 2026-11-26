# 実装カード: 試しの導入台本の直し 2（再審査 2026-11-26 REVISE への対応）

- 正の設計: `docs/handoff/ai-ops-247/server-agent-design.md` §12-3 の 2・4・§12-7（この便で直した版）
- 元の台本: `docs/handoff/ai-ops-247/trial-install/`（56eaac0c7）
- 触る: 01-prepare.sh・03-po-login.md・03b-put-discord-keys.sh・04-check-and-start.sh・このカード末尾の「結果」欄
- 触らない: 02-install.sh・05-daily-read.sh・06-rollback.sh・設計書・ほかのすべて。サーバーには繋がない。鍵の値を書かない

## 直すこと

### 1. 01-prepare.sh（重い 1: 設定の置き直しで道具の記録が消える）

- 「3/4 道具の制限」で `settings.json` を書く前に: ファイルがあり、中に `"enabledPlugins"` があれば、`NG: 道具を入れた後です。01 を流し直すと道具の記録が消えるので止めます。置き直すときは 06 で戻してから最初から。` と出して `exit 1`（書かない）。無ければ今のとおり書く。
- 頭の「2 回流しても壊れない」の行に「（03 の D の前まで）」を足す。
- tmux のつなぎ口を家の場所に置く: 「2/4」の後に `install -d -o ops-agent -g ops-agent -m 0700 /home/ops-agent/.tmux` を足す。unit の ExecStart と ExecStop の `tmux` の直後に `-S /home/ops-agent/.tmux/ops-agent.sock` を足す。注記 1 行: `PrivateTmp=yes` で /tmp の中が管理者から見えないため。

### 2. 03b-put-discord-keys.sh（軽い 3: すり替えの隙）

- 鍵を読む前に `pgrep -u ops-agent >/dev/null` が当たれば `NG: ops-agent の仕事が動いています。03 の窓を閉じてから流してください。` で `exit 1`。
- 書き方を、同じ場所 `$D` の一時ファイル（`mktemp "$D/.tmp.XXXXXX"`）に書く → `chown ops-agent:ops-agent`・`chmod 600` → `mv -fT <一時> "$D/.env"`（access.json も同じ）に変える。失敗時に一時ファイルを消す `trap`（`rm -f` で一時ファイルだけ）。
- 3 段の場所を作った後に、もう一度 3 段とも `test -L` で symlink でないことを確かめる。

### 3. 03-po-login.md（軽い 2）

- D-2 を「PO 本人が自分の端末で `sudo bash 03b-put-discord-keys.sh` を流す。画面の共有と端末の記録（録画・ログ）は切っておく」に直す。
- 止まって見えたときの画面の読み方 1 行: `sudo -u ops-agent tmux -S /home/ops-agent/.tmux/ops-agent.sock capture-pane -p -t ops-agent`（読むだけ）。

### 4. 04-check-and-start.sh（軽い 1・5）

- G4 の確かめに足す: `settings.json` の `enabledPlugins` に `discord@claude-plugins-official` が `true` であること。`python3 -c` で JSON を読んで判定（中身は表示しない。○×だけ）。`/home/ops-agent/.claude/plugins` の場所があること（`test -d`）。
- G1 の確かめに足す: `sudo -l -U ops-agent` の出力に `not allowed` が含まれること。`run_as_agent /usr/bin/test -w /run/docker.sock` が失敗すること（expect_fail）と、守りの外 `run_g2_only` でも失敗すること（組に入っていないため）。

## 確かめ（実装役が行う）

- `bash -n` を 01・03b・04 で通す。`shellcheck` があれば流し、無ければ「未実施」。
- `grep -c 'ops-agent.sock' 01-prepare.sh` が 2（ExecStart と ExecStop）。
- 台本の中に鍵の値・利用者番号の実際の値が 0 件。

## 結果

- カードの 1〜4 をそのとおり直した（01・03b・03・04）。触っていない: 02・05・06・設計書。
- `bash -n`: 01・03b・04 すべて通った。
- `shellcheck`: 未実施（この環境に無い）。
- `grep -c 'ops-agent.sock' 01-prepare.sh` = 2。
- 鍵の値・利用者番号の実際の値: 台本の中に 0 件。
- サーバーには繋いでいない。
