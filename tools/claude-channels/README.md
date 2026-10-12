# tools/claude-channels

Discord の監視通知を Claude Code の受付役が受け取り、不具合ごとに担当を立てて、承認チャンネルで PO の承認を得ながら対応するための自前版チャンネルプラグインと、その運用部品。

設計: `docs/handoff/discord-ops-intake/design.md`、ADR-1009、委任表 `docs/specs/discord-ops-intake/delegation.md`。

## 中身

- `.claude-plugin/marketplace.json`（マーケット名 `sa-local`）と `discord-ops/`: 公式 discord 0.0.4 の複写。変更点は `discord-ops/CHANGES.md`（P0〜P9）
- `intake/`: 受付用の指示書・担当の型・許可設定の雛形・access.json の例
- `bin/`: 起動・停止・番人
- 番人の launchd 設定: `ops/launchd/jp.salesanchor.ops-intake-watchdog.plist`

## 配置手順（Mac 上・PO の確認操作を含む）

1. このディレクトリを `/Users/tanizawashingo/sa-ops-intake-tools` に配置する（plist の絶対パスと一致させる）。`discord-ops/` で `bun install --frozen-lockfile`
2. 受付用 worktree を origin/main から作り、`SA_OPS_INTAKE_DIR`（既定 `~/sa-ops-intake`）に置く
3. `intake/CLAUDE.md` を受付用ディレクトリの `CLAUDE.md` に、`intake/agents/ops-worker.md` を `.claude/agents/` に、`intake/settings.local.json.template` を `.claude/settings.local.json` にコピーする（local スコープだけで有効化。user スコープに入れない）
4. `~/.claude/channels/discord-ops/` に `.env`（ボットのトークン）と `access.json`（`intake/access.json.example` を元に、`<OPS_CHANNEL_ID>` を承認チャンネルの ID に置換）を置く（値は画面・ログに出さない）
5. マーケットを登録し、プラグインを local スコープで導入する
6. 番人用 webhook の URL を `~/.config/sa-ops-intake/watchdog-webhook`（権限 600）に置き、plist を `~/Library/LaunchAgents/` へ置いて `launchctl load` する

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
