# 公式 discord 0.0.4 からの変更点（P0〜P9）

元: `claude-plugins-official/discord` 0.0.4（Apache-2.0。`LICENSE` は公式のまま）。
判定ロジックは `lib.ts` の純粋関数へ切り出し、`lib.test.ts`（`bun test`）で検査する。それ以外の行は公式のまま。
設計: `docs/handoff/discord-ops-intake/design.md` §2。

| # | 変更内容 |
|---|---|
| P0 | 状態ディレクトリの既定値を `~/.claude/channels/discord-ops` に変更（`.mcp.json` でも `DISCORD_STATE_DIR` を指定） |
| P1 | ボット投稿のうち `webhookId` があり、`access.monitorChannels[親チャンネルID].allowWebhooks` に含まれるものだけを通知にする（`lib.ts` `webhookVerdict`）。それ以外は捨て、webhook ID だけ stderr に 1 行出す |
| P2 | 新関数 `handleMonitorAlert`。`gate()` と承認返信の判定（`PERMISSION_REPLY_RE`）を通さず通知だけ送る。meta は `kind="alert"`・`monitor_channel`・`webhook_id` |
| P3 | 通知本文に `embeds` の title・description・fields（`name: value`）を連結し 4,000 文字で切る（`lib.ts` `buildBody`） |
| P4 | プラグイン名・MCP サーバー名を `discord-ops` に、指示文に `kind="alert"` / `kind="decision"` の説明を追加 |
| P5 | 60 秒ごとに `heartbeat` ファイルへ時刻を書く（番人が止まりを判定） |
| P6 | 送信先を DM・承認チャンネル（`opsChannel`）・その子スレッドに限定（`lib.ts` `isAllowedReplyTarget`）。`create_thread` を追加 |
| P7 | 許可確認の送り先を DM ではなく承認チャンネルに変更。ボタンを押せるのは `allowFrom` の人だけ（公式のまま） |
| P8 | 新ツール `propose`（`thread_id, proposal_id, summary, action`）。本文に summary と action 原文（コードブロック）を表示し、投稿成功後に `${STATE_DIR}/proposals/<proposal_id>.json`（600）へ保存（同じ ID は拒否）。ボタン押下時に保存分を読み、見つからなければ `Unknown proposal.`（本人にだけ表示）で何も送らない。見つかれば `kind="decision"` 通知（承認時のみ action 原文つき）を送る（`lib.ts` `saveProposal` / `loadProposal` / `decisionNotification`） |
| P9 | 新ツール `list_monitor_alerts`（`limit` 1〜50・既定 20）。登録済み監視チャンネルの直近メッセージのうち許可 webhook の投稿だけを `<ISO時刻> <channelId> <messageId> <firing/resolved/other>` ＋本文で返す（読むだけ） |
