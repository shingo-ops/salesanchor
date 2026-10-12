# tools/claude-channels

Discord の監視通知を Claude Code の受付役が受け取り、不具合ごとに担当を立てて、承認チャンネルで PO の承認を得ながら対応するための自前版チャンネルプラグインと、その運用部品。

設計: `docs/handoff/discord-ops-intake/design.md`、ADR-1009、委任表 `docs/specs/discord-ops-intake/delegation.md`。

## 中身

- `.claude-plugin/marketplace.json`（マーケット名 `sa-local`）と `discord-ops/`: 公式 discord 0.0.4 の複写。変更点は `discord-ops/CHANGES.md`（P0〜P9）
- `intake/`: 受付用の指示書・担当の型・許可設定の雛形・access.json の例
- `bin/`: 起動・停止・番人
- 番人の launchd 設定: `ops/launchd/jp.salesanchor.ops-intake-watchdog.plist`

## 配置手順（Mac 上・PO の確認操作を含む）

受付用ディレクトリは **main の専用クローン `~/sa-ops-intake`** です（worktree は merged 後に reaper が回収するため使わない）。plist のスクリプトパスはこの場所に固定されています。

1. 専用クローンを作る: `git clone https://github.com/shingo-ops/salesanchor.git ~/sa-ops-intake`（更新は `git -C ~/sa-ops-intake pull --ff-only`）
2. 依存を入れる: `cd ~/sa-ops-intake/tools/claude-channels/discord-ops && bun install --frozen-lockfile`
3. 受付の指示書・担当・許可設定を置く（local スコープだけで有効化。user スコープには入れない）
   - `cp ~/sa-ops-intake/tools/claude-channels/intake/CLAUDE.md ~/sa-ops-intake/CLAUDE.local.md`（リポジトリの CLAUDE.md と両方読まれる）
   - `mkdir -p ~/sa-ops-intake/.claude/agents && cp ~/sa-ops-intake/tools/claude-channels/intake/agents/ops-worker.md ~/sa-ops-intake/.claude/agents/ops-worker.md`
   - `cp ~/sa-ops-intake/tools/claude-channels/intake/settings.local.json.template ~/sa-ops-intake/.claude/settings.local.json`
   - 上の 3 ファイルはクローン側の未追跡ファイル（`CLAUDE.local.md`・`.claude/settings.local.json` は git が無視する）。`intake/` の中身を更新したら複写し直す
4. `~/.claude/channels/discord-ops/` に `.env`（ボットのトークン）と `access.json`（`intake/access.json.example` を元に、`<OPS_CHANNEL_ID>` を承認チャンネルの ID に置換）を置く（値は画面・ログに出さない）
5. マーケットとプラグインを登録する
   - 試作で登録済みの sa-local を外す: `claude plugin marketplace remove sa-local`（未登録ならエラーになるが無視してよい）
   - `claude plugin marketplace add ~/sa-ops-intake/tools/claude-channels`
   - `cd ~/sa-ops-intake && claude plugin install discord-ops@sa-local -s local -y`
6. 番人用 webhook の URL を `~/.config/sa-ops-intake/watchdog-webhook`（権限 600）に置き、plist を `~/Library/LaunchAgents/` へ置いて `launchctl load` する（PATH は plist の `EnvironmentVariables` と各スクリプト冒頭で明示済み）

## 起動と停止

- 起動: `bin/sa-ops-intake-start`（tmux セッション `sa-ops-intake`。起動確認画面は `tmux attach -t sa-ops-intake` で PO が 1 回答える）
- 停止: `bin/sa-ops-intake-stop`（tmux セッションと、discord-ops の `bun server.ts` の残りを終了）

## 番人

`bin/sa-ops-intake-watchdog` が 5 分ごとに ① tmux ② discord-ops の `bun server.ts` ③ `heartbeat` が 600 秒以内、を確認し、どれか欠けたら別 webhook で通知する（1 時間に 1 回まで）。再起動は自動にしない。

## 委任表の変え方

PO の言葉を起点に `docs/specs/discord-ops-intake/delegation.md` を更新し、同じ変更を `intake/settings.local.json.template` の `permissions.allow` に反映する（表と設定はツール単位で 1 対 1）。書き込み系は `permissions.ask` のまま。

## 戻し方

1. `bin/sa-ops-intake-stop` で止める
2. ボットをサーバーから外す
3. プラグインを外し、番人の launchd を `launchctl unload` する

監視側は無変更なので、監視通知は今までどおり届く。
