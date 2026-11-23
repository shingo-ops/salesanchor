# recon: Discord の知らせを、強い鍵を使わずに AI が読む道

- 調べた日: 2026-11-23〜24（JST）。調べた人: Claude Opus（ccopusgo 設計担当）。
- 設計: [design.md](design.md)

## 1. 既存 ADR の検索
- `git grep -i discord origin/main -- docs/adr/FEATURE-INDEX.md` → ADR-009（Discord Gateway）・ADR-1012（24時間保守・Proposed）・ADR-159（webhook 送信）。読むだけの道を決めた ADR は無い。
- 近い前例: `docs/adr/ADR-079-claude-code-monitoring-access.md`（AI に読むだけの監視の鍵を渡す）・`docs/adr/ADR-1024-ai-readonly-db-path.md`（本番 DB を読むだけの道。監視の鍵への相乗りを断り、専用の道にした）。
- 受付の Bot の前の設計: `docs/handoff/discord-ops-intake/design.md:34`（「ボットは読むだけ（監視チャンネルには書き込まない）」）・`docs/handoff/discord-ops-intake/design.md:150`（監視チャンネルの投稿者に SA Bug Intake が 0 件）。

## 2. 事実（実測）
| # | 事実 | 根拠 |
|---|---|---|
| F1 | AI が Discord を読む道は、本番サーバーの `.env` の Bot「Sales Anchor」の鍵だけだった。本番サーバーに入るには manual-only の鍵（PO の許可が要る）が要る | `~/.ssh/config` の Host prod1・`CLAUDE.md`「VPS 直作業禁止」 |
| F2 | Bot「Sales Anchor」の役割は、部屋の管理・送り口の管理・役割の管理・追い出し・BAN・投稿の管理を持つ | 2026-11-23 `/guilds/{id}/roles` の読み取り（Sales Anchor の permissions） |
| F3 | Bot「SA Bug Intake」（1559210609382395924）の役割の権限は 0。@everyone の権限（見る・送る・履歴・招待）を受け継ぐ。部屋ごとの上書きで、不具合受付・不具合報告だけ見られる | 同日 `/guilds/{id}/roles` と `/guilds/{id}/channels` の permission_overwrites |
| F4 | 急ぎ・定期の報告・開発の知らせの3部屋で、SA Bug Intake の上書きは allow 67584（送る・履歴）deny 1024（見る）。見えないが「送る」は許されたままだった | 同日 permission_overwrites（変更前の記録） |
| F5 | SA Bug Intake の鍵は Mac のキーチェーン（service `agent-console`・account `discord-bot`） | agent-console v0.55.3 `server/keychain.ts:7`・`:28`・`:33`、`server/discord-credentials.ts:51` |
| F6 | AI がキーチェーンを読む操作は、見張り go-identity-guard がすべて止める（PO の GitHub の鍵を守るため） | `~/.claude/scripts/go-identity-guard/guard.py:212`〜`:218`（bash_blocked）。2026-11-23 に 2 回止められた |
| F7 | SA Bug Intake は「投稿の中身を読む」設定がオン（審査前の Bot の印 GATEWAY_MESSAGE_CONTENT_LIMITED） | 2026-11-24 PO の ! 実行で `/applications/@me` の flags 565248（1<<19 が立つ）。Discord 公式: Message Content Intent（Context7 /discord/discord-api-docs） |
| F8 | 監視の記録（Loki）・数値（Prometheus）・Uptime Kuma・さくらのメールの読み取りの記録は、ADR-079 の読む鍵ですでに読める | 2026-11-23 Grafana の proxy 経由の読み取り（7 本の見張りがすべて up・メールの最後の読み取り 16:54） |

## 3. 未確認
なし（F7 で解消）。
