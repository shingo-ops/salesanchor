# recon: 閲覧お試しのチケット部屋を LINE 名で作る

基準: `origin/main`（2026-10-20 fetch 後）。調査の生出力: `/tmp/CC報告ファイル/ticket-room-name-recon/`。

## PO の依頼（原文）
- 「チケット発行後のチャンネル名だけどLINE名で作成できる？すでに3名分作ってしまったが変更できるか？」
- 選択肢「1. 新しいチケット部屋をLINE名で作るように直し、片付けの仕組みも合わせて直す。その後、今の3部屋も名前を変える」に PO「1」（2026-10-20）。

## 既存 ADR・設計
- ADR-1019（閲覧ページ）。部屋の設計は `docs/handoff/gas-viewer-fresh-fast/design.md` D6。
- 【事実】D6 は「部屋の名前は `trial-<viewer_accounts.id>`（個人の名前を部屋の名前に入れない）」「部屋の名前 trial-<id> は片付けの判定 _ROOM_NAME_RE（viewer_trial.py:33）が使うので変えない」と書いている（前者は `docs/handoff/gas-viewer-fresh-fast/design.md:294`、後者は `:280`）。今回の PO 決定はこの方針を変える。
- `git grep -il "trial-" docs/adr/` に部屋名の決まりは無い（ADR では決めていない）。

## 現在のコード（file:line）
- `backend/app/discord_gateway/viewer_trial.py:33` `_ROOM_NAME_RE = re.compile(r"^trial-(\d+)$")`
- `backend/app/discord_gateway/viewer_trial.py:109-123` `_create_room`。部屋名は :120 `name=f"trial-{viewer_id}"` の1か所だけで決まる。
- 呼び出し元: `backend/app/discord_gateway/viewer_trial.py:165`（on_open：部屋が消えた人の作り直し。:143 の SELECT は id, email, discord_channel_id）、`:280`（on_code_submit：初回。:261-267 の SELECT は id, email, status, trial_expires_at, discord_user_id。line_name は取っていない）。
- `backend/app/discord_gateway/viewer_trial.py:366-404` `sweep_orphan_rooms`：カテゴリ内の TextChannel のうち名前が `trial-数字` のものだけを見て（:372-377）、`viewer_accounts` に行が無いものを消す（:383-399）。1回10件まで（:32）。DB 読取失敗なら0件（:389-391）。
- 呼ばれ方: `backend/app/discord_gateway/client.py:161-175` 起動時1回＋24時間ごと。呼び出し元はここだけ。
- 部屋の作成部品: `backend/app/discord_gateway/private_channel.py` `create_private_text_channel`（`guild.create_text_channel(name, category, overwrites, reason)`。Forbidden / HTTPException は None を返す）。topic 引数は無い。顧客用チケットも同じ部品を使う。
- bot の部屋ごとの権限は view / read_history / send のみ（`backend/app/discord_gateway/private_channel.py` `_bot_permission_overwrites`）。部屋の作成・削除はサーバー（またはカテゴリ）側の「チャンネルの管理」で行っている。
- `backend/app` に `channel.edit(` の使用例は無い（grep 0 件）。
- `public.viewer_accounts`（`migrations/20261016_150000_add_viewer_accounts.sql:6-22`）: `line_name TEXT NOT NULL`（:9）、`discord_channel_id VARCHAR(32) NULL`（:16）。line_name の空文字を防ぐ DB 制約は無い。申込（`backend/app/routers/viewer.py:428-429`）と管理画面の修正（`backend/app/services/viewer_admin.py:158-160`）は strip 後 1〜100 文字を要求。
- LINE 名の修正（`backend/app/services/viewer_admin.py:151-178`）は Discord の部屋名に触れない。
- テスト: `backend/tests/test_viewer_discord_trial.py`（627 行）。片付けのテスト :291-330 が `trial-1` 等の名前に依存。

## Discord の仕様（公式資料。Context7 は月の上限で使えなかったため、起動指示の代替として公式を直接確認）
- 出典: https://docs.discord.com/developers/resources/channel （2026-10-20 閲覧）
  - Modify Channel の `name`: "1-100 character channel name"
  - "Requires the `MANAGE_CHANNELS` permission for the guild."
  - 名前の変更の回数制限は、この頁には書かれていない（未確認）。

## 審査で分かった追加の事実（2026-10-20 審査役）
- `backend/app/discord_gateway/private_channel.py:106-112` は作成成功時に部屋名をそのまま info ログに出す。`backend/app/discord_gateway/viewer_trial.py:5` は「ログに email・コード・パスワード・表示名を出さない」。
- テストの部屋の作り物 `_text_channel` は `MagicMock(spec=discord.TextChannel)`（`backend/tests/test_viewer_discord_trial.py:64-70`）で、`ch.topic` は文字列でなく MagicMock になる。
- discord.py 2.4.0: `TextChannel.topic: Optional[str]`（discord/channel.py:174・:209）、`TextChannel.edit(*, reason, name, topic, ...)`（channel.py:299-317、manage_channels が必要）、`Guild.create_text_channel(..., topic=MISSING, ...)`（guild.py:1244-1253、MISSING のときは送らない :1358-1359）。
- 顧客用チケットのテスト `backend/tests/test_discord_ticket_channel.py:158-167`・`:214-217` は引数を1つずつ見ており、完全一致では比べない。

## 未確認
- 運用サーバーで bot の「チャンネルの管理」が名前の変更にも効くか（部屋の作成が本番で成功しているので、作成と同じ権限は付いている。変更が失敗したらログを出して飛ばす設計にする）。
- 今の3部屋の番号と LINE 名（reader 鍵では viewer_accounts を読めない）。
