# recon: Discord 連携の戻り口が持ち主の証明なしにサーバー番号を保存する件（G3）

- 基準: origin/main 5574bf327（2026-11-06 fetch）
- 前の設計: docs/handoff/cross-tenant-user-ref-guard/design.md 1・7・8 節（G3 を次の作業として積んだ）
- 生出力: /tmp/CC報告ファイル/g3/（recon1〜4.txt・discord_oauth.py）

## 0. 既存 ADR の検索

- `git grep -il discord origin/main -- docs/adr`（40件・/tmp/CC報告ファイル/g3/adr-hits.txt）と docs/adr/FEATURE-INDEX.md の discord / oauth の行（18・20・50・53 行。どれも連携の戻り口は扱わない）
- 該当する ADR:
  - ADR-091（docs/adr/ADR-091-discord-bot-scope-definition.md）: ボットの権限と招待の流れ。:104 で接続は `/discord/oauth/start` → `/discord/oauth/callback` と定める。:137-185 で `scope=bot` 単体では戻り口が呼ばれず、`scope=bot applications.commands` + `response_type=code`（PR #1483）で `redirect_uri?guild_id=GUILD_ID&code=CODE&state=STATE` に戻ると記録。:263「実証された」
  - ADR-075（docs/adr/ADR-075-github-secrets-only-policy.md:54）: 本番の秘密は GitHub Secrets だけで持ち、deploy.yml で VPS の .env に入れる
  - ADR-072: commit の後に reset_tenant_context
  - ADR-146: Discord は共通のボット1台・guild_id から会社を引く（前の設計の引用）
- 秘密の鍵 DISCORD_CLIENT_SECRET に触れる ADR は 0 件

## 1. 戻り口の今の動き（backend/app/routers/discord_oauth.py）

| 行 | 事実 |
|---|---|
| :51 | `_DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1499458730171961535")`。秘密の鍵の変数は無い |
| :80-83 | `_DISCORD_CALLBACK_URL` 既定 `https://api.salesanchor.jp/api/v1/discord/oauth/callback` |
| :94-101 | 招待の URL: `scope="bot applications.commands"`・`response_type="code"`・`redirect_uri`・`state` |
| :114-116 | 開始口は `channels.manage` 権限が要る。:126-132 自社用（own）は `tenant.profile.edit` も要る |
| :148-152 | 開始口は `invite_url` と一緒に `state` そのものを呼び手に返す |
| :160-165 | 戻り口の引数は `guild_id` と `state` だけ。`code` を受け取らない |
| :181 | guild_id は 17〜19 桁の数字かだけを確かめる |
| :186-194 | state を1回だけ使う（Redis から消す） |
| :196-209 | state の中身から tenant_id・staff_id・purpose を取る |
| :219-230 | URL の guild_id をそのまま `public.tenant_discord_config` に INSERT … ON CONFLICT (tenant_id, purpose) DO UPDATE |
| :241-248 | 他社が登録済みの番号は一意の決まりで IntegrityError → `reason=guild_already_registered` |

結論（事実の組み合わせ）: `channels.manage` 権限の人は開始口で state を受け取り（:150）、Discord を通らずに `GET /discord/oauth/callback?state=<それ>&guild_id=<任意の未登録番号>` を開けば、その番号が自社の行として保存される（:219-230）。持ち主かどうかを確かめる処理は無い。

## 2. Discord 公式の決まり（docs.discord.com/developers/topics/oauth2・2026-11-06 取得）

Context7 は月の上限で使えなかった（`Monthly quota exceeded`）。起動指示の代替手順で公式資料を直接読んだ。

- 「Advanced Bot Authorization」: 戻り先に `code` と一緒に `guild_id` と `permissions` が付く。`guild_id` は関係の hint（目安）としてだけ使うこと
- code を `POST https://discord.com/api/oauth2/token` で交換すると、応答に「ボットが入ったサーバー」の `guild` オブジェクト（`id`・`owner_id` など）が入る
- 交換の項目: `grant_type=authorization_code`・`code`・`redirect_uri`（招待の URL と同じ値）。本文は `application/x-www-form-urlencoded` だけ。client_id と client_secret は HTTP Basic 認証か本文で渡す
- bot と applications.commands 以外の scope を足すと完全な code grant の流れになる。ボットの設定で「code grant を必須」にもできる（公式の勧め）
- state は戻り先で確かめること（今の :186-194 で実施済み）

## 3. 秘密の鍵の配線（今は無い）

| 場所 | 事実 |
|---|---|
| backend | `git grep -n -i "DISCORD_CLIENT_SECRET\|discord.*client_secret" origin/main` は docs だけ。コードで読む所は 0 |
| .github/workflows/deploy.yml | :294 付近で .env の該当行を消し（sed）、:355 付近の heredoc で `DISCORD_BOT_TOKEN='${{ secrets.DISCORD_BOT_TOKEN }}'` を足す形。GOOGLE_CALENDAR_CLIENT_SECRET も同じ形。DISCORD_CLIENT_SECRET の行は無い |
| docker-compose.yml | backend の環境変数 :109 に `DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN:-}`。compose に書かない変数は .env にあっても backend に届かない（:110-112 のコメント） |
| GitHub Secrets | `gh secret list --repo shingo-ops/salesanchor`（名前だけ・2026-11-06）に DISCORD_CLIENT_SECRET は無い。DISCORD_BOT_TOKEN（2026-08-31 更新）・GOOGLE_CALENDAR_CLIENT_SECRET はある |
| backend/app/main.py:196-201 | META_APP_SECRET 等が空なら起動時に警告（ENFORCE_WEBHOOK_SECRETS=1 なら起動を止める）。同じ形の確かめ先 |

## 4. 外へのつなぎ方の手本

- backend/app/routers/discord_channel_invite.py:142 `httpx.AsyncClient(timeout=10.0)` で discord.com を呼ぶ（backend から discord.com へ出られる）
- 試験: backend/tests/test_meta_oauth_endpoints.py:243-309 `httpx.MockTransport` で外の応答を作り `patch("<module>.httpx.AsyncClient", side_effect=...)` で差し替える
- httpx 0.28.1（backend/requirements.txt:14）。respx は無い

## 5. 画面の受け取り

- frontend/src/pages/channels/ChannelsPage.tsx:64-69 `ERROR_REASON_KEYS` は Meta の reason だけ。Discord の reason（例 `guild_already_registered`）は :164 `channels.errorReason.unknown`（「接続に失敗しました（理由: {{reason}}）。」ja.json:1507）で出る
- frontend/src/pages/admin/DiscordOwnServerPanel.tsx:116-127 自社用は `guild_already_registered` だけ専用文、他は `discordOwnServer.connectError`

## 6. 既存の試験

- backend/tests/test_discord_oauth.py: 開始口 :186-295（:190 invite_url と state・:219 権限の数字・:246 招待の URL の項目）。戻り口 :302-（:306 正常＝state と guild_id で connected、:334・:344・:398 state なし／無効／guild_id なし、:363 set_tenant_context の順）
- backend/tests/test_discord_oauth_rls.py:122・:179 監査の記録と RLS

## 7. 本番の今の行（読み取りの道・2026-11-06 15:20Z・rows=4）

| 会社 | 用途 | 接続者 | 作成 |
|---|---|---|---|
| 1 | customer | 1 | 2026-11-06 14:32:43Z |
| 1 | own | 1 | 2026-11-06 14:33:13Z |
| 4 | customer | 3 | 2026-10-02 05:15:07Z |
| 6 | customer | 10 | 2026-08-31 17:08:53Z |

会社1の2行は PO が 11/6 に連携ボタンで解除→再接続した行（PO 発言「テナント001の接続を解除して再接続したが問題なく接続完了した」）。

## 8. 未確認

- U1 は 2026-11-07 に確かめ済み（PO「1」で Opus が Chrome の履歴を見た。値は読まず、項目の名前だけ）: 戻り口の記録 9 件すべてに `code` がある。会社1の 11/6 の2回（14:32:43Z・14:33:14Z。7 節の行の作成時刻と一致）は `code`・`guild_id`・`iss`・`permissions`・`state`。8/31〜10/2 の5件は `code`・`guild_id`・`permissions`・`state`。→ 今の招待のまま code は付く。開発者画面の設定は要らない

- U1: 今の招待（bot applications.commands + response_type=code）で、戻り先に `code` が実際に付くか。ADR-091:162-163・:263 は付くと記録するが、生の URL の記録は repo に無い。Discord 公式は bot と applications.commands だけのとき code が付くかを明言しない。2026-11-07 再取得: 公式は「bot と applications.commands だけなら利用者の access token を取る必要が無い」「response_type は、それ以外の scope を求めるときだけ必須」と書く（code が付かない可能性を否定できない）
- U2: 既存の4行のサーバーに、ボットが本当に入っているか（偽の登録が過去に無いか）。ボットの鍵が要るので読み取りの道では見られない
- U3: Discord 開発者画面に、すでに秘密の鍵が発行済みか（作り直すと前の鍵は使えなくなる。コードで使う所は 0 件なので影響先は repo の中には無い）
