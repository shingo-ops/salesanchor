# 実装カード: prod2 での小さな試しの「導入の台本」（文書だけ）

- 正の設計: `docs/handoff/ai-ops-247/server-agent-design.md` §12（G1〜G8・段取り 1〜7・§12-4〜12-7）。食い違えば設計が正。迷ったら作らずに `NEEDS_DECISION:` で止まる。
- PO 承認: 2026-11-25「1」（守り方付きで prod2 で小さく試す）・2026-11-26「1」（入れる手順書を作り、別の AI に審査させてから、もう一度だけ確認する）。
- この便でサーバーには何もしない。台本を書いて commit・push するだけ。台本を流すのは、PO の同意を受けた Opus。
- 置き場: `docs/handoff/ai-ops-247/trial-install/`（新規）。本番の `scripts/` には置かない。
- 触るファイル: 下の 1〜7 と、このカード末尾の「結果」欄だけ。ほかのファイルは触らない。

## 0. 段取り 1 の結果（2026-11-25 15:18Z に Opus が読むだけで測った値。台本はこれを前提にする）

- 空きメモリ（available）2,579MB・CPU 4・スワップ 0・systemd 255・tmux あり・`ops-agent` は無い。
- IPv6 の全体の番地: 無し（`ip -6 addr show scope global` が空）。→ G7 に IPv6 は足さない。
- 名前を引く番地: `/etc/resolv.conf` は `nameserver 127.0.0.53`。上流は 210.224.163.3 と 210.224.163.4。→ `IPAddressAllow=127.0.0.53`。
- 監視の compose の置き場: `/opt/salesanchor-monitoring`（`.env` を含む）と `/opt/salesanchor-monitoring/gemini-egress`。→ G8 の `InaccessiblePaths=` に `/opt/salesanchor-monitoring` を足す。
- GitHub の実行役が動いている: `/home/ubuntu/actions-runner`（unit `actions.runner.shingo-ops-salesanchor.salesanchor-vps.service`・利用者 ubuntu）。`/home/ubuntu` は既に G8 で塞ぐ。
- 転送の鍵は `/home/ubuntu` の下（unit の `-i` の値。値は書かない）。
- G6 の基準: `salesanchor-monitoring-loki-1` の再起動 13 回・`salesanchor-monitoring-gha-exporter-1` 160 回・ほか 9 個は 0 回。OOMKilled は 11 個すべて false。

## 1. `01-prepare.sh`（段取り 2。管理者が `sudo bash` で流す）

- `set -euo pipefail`。2 回流しても壊れない（あれば作らない）。
- `ops-agent` を作る: `useradd --create-home --shell /bin/bash ops-agent`。sudo と docker の組に入れない。最後に `id ops-agent` を表示し、`sudo`・`docker` が含まれていれば失敗で止める（G1）。
- 作業の場所 `/home/ops-agent/work` を作る（空・持ち主 ops-agent）。担当はここで起動する。
- G4 の設定を `/home/ops-agent/.claude/settings.json` に置く（持ち主 ops-agent・600）。中身:
  - `permissions.defaultMode`: `"dontAsk"`（公式 https://code.claude.com/docs/en/permission-modes 「一覧に無い呼び出しは聞かずに断る」。2026-11-26 Context7 で確認）。
  - `permissions.allow`: Discord の道具のうち `reply`・`react`・`fetch_messages` の 3 つだけ。道具の正式な名前（`mcp__plugin_discord_discord__reply` の形か）は公式の説明 https://code.claude.com/docs/en/mcp か plugins の説明で確かめて書く。確かめられなければ `NEEDS_DECISION:` で止まる。
  - `permissions.deny`: `Bash`・`Write`・`Edit`・`NotebookEdit`・`WebFetch`・`WebSearch`・`Agent`・Discord の `download_attachment`・`edit_message`・`create_thread`。さらに `Read(/home/ops-agent/.claude/**)` と `Read(/home/ops-agent/.claude.json)`（ログインの札とボットの鍵 `~/.claude/channels/discord/.env` を Read で読ませないため）。deny の書き方は公式 https://code.claude.com/docs/en/permissions で確かめる。
- unit ファイル `/etc/systemd/system/ops-agent.service` を置く。`daemon-reload` だけして、enable も start もしない。中身は 2 のとおり。

## 2. unit の中身（`01-prepare.sh` が書く）

- `User=ops-agent`・`WorkingDirectory=/home/ops-agent/work`・`Restart=on-failure`・`RestartSec=30`。
- G2: `MemoryHigh=1200M`・`MemoryMax=1500M`・`MemorySwapMax=0`・`OOMScoreAdjust=1000`。
- G7: `IPAddressDeny=localhost link-local multicast 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 49.212.137.46 49.212.160.98`・`IPAddressAllow=127.0.0.53`。
- G8: `ProtectSystem=strict`・`ReadWritePaths=/home/ops-agent`・`InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring`・`PrivateTmp=yes`・`NoNewPrivileges=yes`。
- 起動の形（U-a・未確認）: `Type=forking` で `tmux new-session -d -s ops-agent` の中に `/home/ops-agent/.local/bin/claude --channels plugin:discord@claude-plugins-official` を動かす。止めるのは `tmux kill-session -t ops-agent`。tmux の書き方は `man tmux` の範囲で書き、確かめられない点は台本の注に「未確認」と書く。
- systemd の各設定の意味は公式 systemd.resource-control と systemd.exec（Context7 `/systemd/systemd` で確かめる）。

## 3. `02-install.sh`（段取り 3。管理者が `sudo bash` で流す）

- `systemd-run --uid=ops-agent --pty --wait --collect` に G2 と G8 と同じ値を `-p` で付け、その中で次を流す。G7 は付けない（設計 §12-3 段取り 3・4 は G7 なし）。
  - Claude Code の公式の入れ方 `curl -fsSL https://claude.ai/install.sh | bash`（公式 https://code.claude.com/docs/en/setup で確かめる）。
  - Bun の公式の入れ方（https://bun.sh の説明で確かめる）。
- 入れる前と後に `free -m` を表示する。空きが 600MB を切っていたら入れずに止める。
- `systemd-run` の `--uid`・`--pty`・`-p` の書き方は公式 systemd-run の説明で確かめる。

## 4. `03-po-login.md`（段取り 4。PO が手で行う順番。日本語の易しい言葉で）

- PO の手で行うこと: Discord の Developer Portal でボットを作る → 管理者が開いた窓で `claude` を開いてサブスクでログイン → `/plugin install discord@claude-plugins-official` → `/discord:configure`（ボットの鍵は PO が打つ）→ スマホから DM してペアにする → `/discord:access policy allowlist`。
- 窓の開き方は `02-install.sh` と同じ上限付きの `systemd-run` の 1 行を書く（G7 なし）。
- この段で担当に仕事を頼まないこと、鍵の値を AI に見せないことを書く。

## 5. `04-check-and-start.sh`（段取り 5。管理者が `sudo bash` で流す）

- G7 の確かめ: `systemd-run --uid=ops-agent --wait --collect --pipe` に unit と同じ G7・G8 の値を付けて、`curl -m 5 http://127.0.0.1:19187/metrics` と `curl -m 5 http://49.212.160.98:3000` が失敗すること、`getent hosts api.anthropic.com` が引けること、`curl -m 10 -sS -o /dev/null -w '%{http_code}' https://api.anthropic.com` が何かの数を返すことを見る。
- G8 の確かめ: 同じ形で `cat /opt/salesanchor-monitoring/.env`・`ls /home/ubuntu`・`ls /root` が読めないこと。
- G3 の確かめ: `/home/ops-agent` の下に SSH の鍵（`.ssh` の中身）が無いこと。ファイル名だけ表示し、中身は表示しない。
- 1 つでも期待と違えば、起動せずに止まる。全部合えば `systemctl enable --now ops-agent.service` し、`systemctl is-active` と `systemctl show -p MemoryHigh,MemoryMax,MemorySwapMax,IPAddressDeny,IPAddressAllow,InaccessiblePaths ops-agent` を表示する。
- 結果の各行に「期待」と「実際」を並べて出す。

## 6. `05-daily-read.sh`（段取り 7。読むだけ。Opus が毎日 1 回流す）

- 書き込みの命令を 1 つも含めない。
- `date -u`・`free -m`・各コンテナの名前と `RestartCount` と `OOMKilled`（段取り 1 と同じ `docker inspect -f` の形）・`systemctl is-active ops-agent`・`systemctl show -p NRestarts ops-agent`・担当の `memory.peak`（`/sys/fs/cgroup/system.slice/ops-agent.service/memory.peak`）・`journalctl -u ops-agent --since -24h` のうちメモリの上限・OOM に当たる行の数。
- 0 の基準の値（上の 0 の G6 の基準）と並べて、差を表示する。

## 7. `06-rollback.sh`（§12-6。管理者が `sudo bash` で流す）

- `systemctl disable --now ops-agent.service` → unit を消して `daemon-reload` → `userdel -r ops-agent`。監視の仕組みには触らない。
- ボットの鍵の作り直しと claude.ai のログインの外しは PO の手で行うと最後に表示する。

## 全体の決まり

- 鍵・トークン・パスワードの値を台本に書かない。表示もしない。
- 台本はどれも `bash -n` が通ること。`shellcheck` があれば流して、警告を「結果」欄に書く。
- サーバーには繋がない（クラウドからは繋がらない前提）。
- 公式資料で確かめた点は、台本の注に URL を書く。確かめられなかった点は「未確認」と書く。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 1〜7 のファイルがそろう | `ls docs/handoff/ai-ops-247/trial-install/` |
| 台本の文法が通る | `bash -n` を 5 本に流して 0 件 |
| unit の値が §12-2 と 0 の結果に一致 | G2・G7・G8 の値を設計と並べて照合 |
| 鍵の値が 0 件 | 鍵の形（`sk-ant`・`ghp_`・`PRIVATE KEY` など）で探して 0 件 |
| 日々の台本に書き込みの命令が無い | `05-daily-read.sh` に `rm`・`>`（書き出し）・`systemctl start/stop/restart`・`docker restart` が 0 件 |

## 結果（担当が書く）

- （ここに確かめた公式資料・未確認の点・shellcheck の結果を書く）
