# recon: 失敗したときの文を「何が起きたか＋次にすること」にする

- 土台: origin/main `67d7bbf87`（2026-11-07 取得）
- 依頼（PO 2026-11-07 原文）:「失敗したときは非エンジニアでも分かるエラー内容とアクションプランを提示するようにしてくれ、例えば「時間切れにより連携できませんでした。もう一度お試しください。」のように。これはDisocrdに限らずエラー内容全ての要件定義になる」
- 承認済み KGI（PO「1」2026-11-07）: Discord 連携の失敗 12 種類それぞれに「起きたこと＋次にすること」の1文／2画面で同じ理由なら同じ文／本番で PO が試し用の入口を開くと時間切れの文が出る（何も書き込まない）
- アプリ全体の棚卸し（数え上げ）は `docs/handoff/error-message-plain-language/inventory.md`（クラウドの読み取り調査）に置く。本書は Discord の事実と、全体に効く仕組みの事実を置く

## 1. 既存の決定記録（ADR）の検索

命令: `grep -rln 'エラーメッセージ\|エラー文言\|error message' docs/adr/*.md` → 6 件（027 / 037 / 041 / 074 / 126 / 159）

| 記録 | 行 | 中身 | 今回との関係 |
|---|---|---|---|
| docs/adr/ADR-159-staff-identity-on-discord.md | 23 | PO 原文「フロントにも非エンジニアである担当者が理解できる内容でエラーメッセージを表示させて対応方法までCTA，簡潔に」 | 同じ要件が Discord 送信の失敗に限って既にある。今回これをアプリ全体へ広げる |
| docs/adr/ADR-159-staff-identity-on-discord.md | 32 | 「エラーは非エンジニア向け短文＋行動ボタン（CTA）。既存金型・i18n・トークンのみ」 | 作り方の前例 |
| docs/adr/ADR-027-ui-internationalization.md | 17 | 翻訳対象に「エラーメッセージ・通知メッセージ」 | 文は t() 経由・ja/en 同一キー |
| docs/adr/ADR-126-registration-form-input-contract-v2.md | 150 / 158 / 176 | 公開フォームの全エラーを `registration.error.*` で出し、内部コード・日本語直書きを顧客に出さない。「データベースエラーが発生しました」の露出を検出した経緯 | 公開フォームに限った前例 |
| docs/specs/db-error-detail/ | （ideal-state.md / kgi.md） | サーバーの応答に例外の中身を出さない。`log_hidden_error` は backend/app で 87 か所 | 「中身を隠す」側の決まり。今回は「隠した後に何を見せるか」 |

アプリ全体の「エラーの文の書き方」を決めた記録は、上の6件の中には無い。

## 2. 全体に効く仕組み（事実）

- `frontend/src/lib/api.ts:162-171`: サーバーの応答の `detail` が文字列なら、その文字列をそのまま `ApiError.message` にする。dict なら `detail.detail`、無ければ `common.httpError`（番号入りの文）
  - つまり、サーバー側で `HTTPException(detail="…")` に書いた文が、画面がそれを表示すれば利用者にそのまま見える
- `frontend/src/lib/api.ts:221`: もう1つの道では、応答の本文そのもの、無ければ `common.httpError`
- 前例の型: `frontend/src/pages/inbox/discordSendError.ts:8-67` — 理由コード4つ → 文言キー（`inbox.sendError.*`）と行動ボタン（移動 or 再送）。権限が無い人には行動ボタンを出さず「管理者に連絡」の文にする（57-63 行）

## 3. Discord 連携の失敗（12 種類）

### 3-1. 戻り口がどこへ返すか（backend/app/routers/discord_oauth.py）

| 理由コード | 行 | 起きる条件（コードの事実） | 返す画面 |
|---|---|---|---|
| missing_state | 234 | 戻り URL に state が無い | 顧客用（/channels）のみ |
| missing_guild_id | 238 | guild_id が無い（コメント: サーバー選択の取り消し等） | 顧客用のみ |
| invalid_guild_id | 243 | guild_id が17〜19桁の数字でない | 顧客用のみ |
| redis_error | 250 | 札の保管庫（Redis）につながらない | 顧客用のみ |
| invalid_state | 254 | 札が無い（期限切れ・改ざん・使い回し）。札の有効時間は 600 秒（backend/app/services/oauth_state.py:41） | 顧客用のみ |
| invalid_payload | 261 / 265 | 札の中身の purpose が不正 / tenant_id が無い | 261 は顧客用のみ、265 は purpose どおり |
| missing_code | 274 | code が無い | purpose どおり（顧客用 or 自社用 /admin/discord-config?tab=own） |
| discord_not_configured | 278（122） | 鍵 DISCORD_CLIENT_SECRET が無い | purpose どおり |
| code_exchange_failed | 278（136 / 146） | Discord との通信失敗、または Discord が交換を拒否 | purpose どおり |
| missing_guild_in_token | 278（154） | 交換の応答にサーバーが無い | purpose どおり |
| guild_mismatch | 284 | URL のサーバーと Discord が答えたサーバーが違う | purpose どおり |
| guild_already_registered | 328 | 同じサーバーが既に別の登録にある | purpose どおり |
| （成功）connected | 334 | 保存できた | purpose どおり |

- 254 行より前（234〜254 と 261）は、札を読む前なので自社用から始めても顧客用の画面へ返る

### 3-2. 連携を始めるときの失敗（同じファイル）

| 行 | 条件 | 画面に返る文（サーバーが直書き） |
|---|---|---|
| 182-185 | 自社用で権限 tenant.profile.edit が無い（403） | 「権限が不足しています: tenant.profile.edit」 |
| 186-191 | 鍵が無い（503） | 「一時的に Discord 連携を開始できません（設定不足）」 |
| 196-203 | 札を発行できない（503） | 「一時的に Discord 連携を開始できません（Redis 接続失敗）」 |

### 3-3. 画面の受け取り

- 顧客用 `frontend/src/pages/channels/ChannelsPage.tsx`
  - 129-136: `discord_status` が connected 以外なら、理由に関係なく `channels.discordConnectError` 1つだけを出す（理由を読んでいない）
  - 161-164: Meta 側は `reason` を読み `channels.errorReason.<理由>`、未知なら `channels.errorReason.unknown`（Discord には使っていない）
  - 226 / 244: 連携開始・切断の失敗で `ApiError.message`（= 3-2 のサーバー直書きの文）をそのまま帯に出す
- 自社用 `frontend/src/pages/admin/DiscordOwnServerPanel.tsx:116-127`: `guild_already_registered` だけ専用の文、ほかは全部 `discordOwnServer.connectError`
- 文（frontend/src/locales/ja.json、en.json も同じ行構成）
  - 1528 `channels.discordConnectedSuccess`「DiscordサーバーにBotを追加しました。」
  - 1529 `channels.discordConnectError`「Discord連携に失敗しました。もう一度お試しください。」— 何が起きたかが無い
  - 3574 `discordOwnServer.connectError`「登録できませんでした」— 何が起きたかも次にすることも無い
  - 3575 `discordOwnServer.guildAlreadyRegistered`「このサーバーは既に登録されています」— 次にすることが無い

### 3-4. 前の設計書の誤り

- docs/handoff/discord-oauth-ownership-proof/design.md:45 は「接続に失敗しました（理由: …）」（顧客用）と書くが、3-3 のとおり顧客用は理由を読まず「Discord連携に失敗しました。もう一度お試しください。」を出す。設計書の記述が事実と違う（便1で直す）

## 4. アプリ全体の件数（基準値）

全件の一覧は同じフォルダの `docs/handoff/error-message-plain-language/inventory.md`（クラウドの読み取り調査・commit `75524633d`・土台 `67d7bbf87`）。サーバー側だけは構文解析で数え直した。

| 何を数えたか | 数え方 | 件数 |
|---|---|---|
| サーバーのエラー（HTTPException）の総数 | Python の ast で backend/app の全 .py を読み、HTTPException の呼び出しを数える（解析失敗 0） | 1056 |
| うち detail に日本語の文を直書き（f 文字列含む） | 上のうち detail が文字列で、ひらがな・カタカナ・漢字を含む | 662（96 ファイル） |
| うち detail に英語の文を直書き | 文字列で、識別子の形（英数字と _ . : - だけ）でないもの | 62 |
| うち detail が識別子の形（例 `not_found`） | 同上で識別子の形 | 191 |
| うち detail が dict / 変数など | 文字列以外 | 141 |
| 画面の文言（ja.json）で「失敗」「エラー」`できません`を含むキー | inventory.md A（機械判定） | 267 |
| うち次の行動の語（もう一度・お試し・連絡・確認して・してください）が無い | 同上 | 215 |
| 画面でエラーの message / detail を参照する行 | inventory.md B（grep。表示先は全件未確認・console 等も混ざる） | 342 |
| 戻り口で理由コードを付けて返す所 | inventory.md D-1 | Discord 11・Google カレンダー 3・外部連携 3 |
| 理由コード→文言の対応表になっている既存ファイル | inventory.md E | 8（＋未確認 1 群） |

- 数え直しの道具: scratchpad の count_detail.py（Opus の手元の一時ファイル。リポジトリには置かない）、結果 `/tmp/CC報告ファイル/u2/C-exact.tsv`（1056 行）
- クラウドの数え方 C（646 行）は grep の前後行込みで、上の 662 とは数え方が違う。基準値は上の表を使う

## 5. 未確認

- 実際の画面で 3-3 の文が出ることは、コードを読んだだけで、画面ではまだ確かめていない
- 画面でエラーを参照する 342 行のうち、本当に利用者の画面に出る行の数（表示先を1行ずつ読む必要がある。便2以降の recon で行う）
- 「次の行動の語が無い 215 件」は語の有無だけの判定。文として行動になっているかは人が読んで判定していない
