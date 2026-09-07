# Discordリアクション（discord-reaction）— 表紙

> この文書は何か（専門用語なしの1行）:
> 顧客とのやり取りに絵文字で反応する機能について、受信箱の側でDiscordと同じことができる状態を定めた設計仕様書の表紙。

配置: docs/specs/discord-reaction/README.md
日付: 2026-09-04
PO: しんご
ステータス: あるべき姿・KGI確定 2026-09-04

## なぜ新規テーマか（KGI⑪）

着手前に索引 docs/specs/README.md と docs/specs/ 配下を固定SHAで走査したが、リアクションに該当するあるべき姿は0件だった（2026-09-04 実測・SHA bff841f3a28958697c238cd87334fe98dff49025）。索引の「Discord連携」行は枠のみで仕様書が未作成であり、ぶら下げられる本体が存在しない。同型の attachment-storage が docs/specs/ 直下に置かれているため、同じ階層に並べる。

## 本テーマの範囲（境界）

- 対象: Discordのリアクションの受信・表示・送信・取り消し。
- 対象外: DM。ギルド内のチケットチャンネルのみを扱う（ADR-146 F7）。
- 対象外: 受信箱の画面全体の見せ方。受信箱（inbox）テーマが担当する。
- 対象外: 添付ファイルの保管。attachment-storage テーマが担当する。
- 対象外: Bot権限そのものの定義。ADR-091 が正本。

## 構成

- README.md（本ファイル・表紙）
- ./ideal-state.md — あるべき姿（PO自筆のみの正本。Planner・Generatorは書き換えない）
- ./kgi.md — KGI（○×条件・前提・設計送り事項）

差分設計（to-be）は本テーマではまだ作成していない。作成時は本欄に1行足す。

## 背景となる実測（2026-09-04・SHA bff841f3a28958697c238cd87334fe98dff49025）

- リアクションの実装は0件。backend/app/discord_gateway/ 配下、backend/app/routers/leads.py、frontend/src/pages/inbox/ のいずれもヒット0。
- backend/app/discord_gateway/client.py:54 で intents = discord.Intents.none() から開始し、guilds / guild_messages / message_content / members の4つのみ有効化している。リアクション用のintentは未設定。
- backend/app/discord_gateway/client.py:36 は class JarvisDiscordClient(discord.Client)。定義済みイベントは on_ready:103 / on_resumed:113 / on_disconnect:119 / on_interaction:122 / on_message:204 の5つ。
- 受信の稼働経路は client.py:204 の on_message から client.py:219 の _process_guild_message を経て ticket_channel_writer へ委譲する。inbound_writer 経路（client.py:252）は休眠中（ADR-146 案ア）。
- docs/adr/ADR-091-discord-bot-scope-definition.md:79 が Add Reactions を「将来機能として許容」に分類し、API呼び出し実装には別途ADR・PO承認を要すると定める。
- Discord公式仕様: リアクション付与は PUT /channels/{channel.id}/messages/{message.id}/reactions/{emoji}/@me。READ_MESSAGE_HISTORY 権限が必要で、その絵文字で誰も反応していない場合は ADD_REACTIONS 権限も必要。取り消しは同パスへのDELETE。他人の分の削除には MANAGE_MESSAGES が必要。押した人の一覧は最大100件ずつ取得する。出典: https://docs.discord.com/developers/resources/message

## 維持の仕組み

- 本表紙・ideal-state.md・kgi.md の変更はPR＋PO承認のみ。process-artifacts gate が通過を管理する。
- ideal-state.md はPO自筆の正本であり、設計パートナー・実装役は書き換えない。
