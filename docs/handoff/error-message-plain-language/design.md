# Phase 3 設計 — 失敗したときの文（便1: Discord 連携）＋アプリ全体の見張り

- 状態: 設計審査済み（2回目 APPROVE）・PO 承認済み（Discord の KGI と §4-3 の文の一覧。2026-11-07。PO が 5 と 7 の文を自分で書き直し、2 の文は Opus の言い換え案に「1」）。便1 の実装承認: 同日 PO「1」（選択肢「この文で決まり、全部の文がそろったので作り始めます」）。アプリ全体の KGI（§2-2）は PO 確認待ち
- 根拠: `docs/handoff/error-message-plain-language/recon.md`（Discord の事実・全体の件数）、`docs/handoff/error-message-plain-language/inventory.md`（全件一覧）、決まり本体 `docs/adr/ADR-1071-plain-language-error-messages.md`
- 土台: origin/main `67d7bbf87`

## 1. 目的（PO の言葉）

「失敗したときは非エンジニアでも分かるエラー内容とアクションプランを提示するようにしてくれ、例えば「時間切れにより連携できませんでした。もう一度お試しください。」のように。これはDisocrdに限らずエラー内容全ての要件定義になる」（2026-11-07）

## 2. KGI

### 2-1. 便1（Discord 連携）— PO「1」で承認済み

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | Discord 連携の失敗 12 種類（戻り口の 12 コード（reason= 9 個と Discord との確認の失敗 3 個。grep で全件）を画面の 11 種類にまとめたもの＋始めるときの権限の失敗。§4-2 の表）それぞれで、起きたことと次にすることの1文が出る | 画面の試験: 理由ごとに URL を与えて表示文が §4-3 の文と一致（12＋未知 1 = 13 件）。PO は §4-3 の一覧を読んで○× |
| K2 | 顧客用（/channels）と自社用（Discord 設定の自社タブ）で、同じ理由なら同じ文 | 2画面の試験が同じ対応表を通ることを確かめる（同じ理由コードで同じ文言キー）。両画面が同じ関数を import していることを grep で確かめる |
| K3 | 本番で PO が試し用の入口を開くと、時間切れの文が出る。入口は何も書き込まない | 前提: 本番の札の保管庫（Redis）が正常なとき。ログインは不要（戻り口は認証なし。discord_oauth.py:228）。`https://api.salesanchor.jp/api/v1/discord/oauth/callback?state=test-expired&guild_id=100000000000000000` を開く → /channels に「時間切れにより連携できませんでした。もう一度お試しください。」。保管庫が止まっていると 11 の文になる（oauth_state.py:153-156 → discord_oauth.py:248-250）。そのときは保管庫が戻ってから開き直す。書き込みが無いことは §4-5 |

### 2-2. アプリ全体 — PO 承認待ち（提案）

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 新しく足した失敗の文が決まりに合わないと、CI が落ちる | 試しの PR で悪い例（サーバーに日本語の文の直書きを1つ足す／次の行動の無い文言を1つ足す）を入れ、見張りが赤になることを確かめる |
| A2 | 決まりに合わない今の文の数が、便ごとに減り、最後は 0 | 基準値のファイルの数（サーバー直書き 662＋62、次の行動の無い文言 215。recon §4）を便ごとに記録 |

## 3. 外部・過去事例の参照と我々への応用

| 出典 | 中身 | 応用 | 適用限界 |
|---|---|---|---|
| GOV.UK Design System「Error message」（design-system.service.gov.uk/components/error-message/、最終変更の記録 2024年1月、2026-11-07 閲覧） | 「何が起きたかを説明し、どう直すかを伝える」 | ADR-1071 What 1 の2要素 | 入力欄の検査エラーが中心。連携の失敗の例は無い。効果の数値は書かれていない |
| Nielsen Norman Group「Error-Message Guidelines」（Tim Neusesser・Evan Sunwall、2023-05-14、2026-11-07 閲覧） | 普段の言葉で書く／エラーコードは隠す／問題を具体的に／直し方を提案する／利用者を責める語（invalid 等）を使わない | What 1・3（コード・仕組みの名前を出さない）。§4-3 の文で「不正」を使わない | 指針であり、数値の効果測定は載っていない |
| 自社の前例 ADR-159（Discord 送信の失敗）・`frontend/src/pages/inbox/discordSendError.ts` | 理由コード→文言キー＋行動。権限が無い人には「管理者に連絡」 | 便1 の対応表の形をそのまま使う | 送信の失敗4種のみ |
| 自社の前例 `channels.errorReason.*`（Meta 連携、ja.json 1508-1518） | 理由ごとの文。ほぼ「起きたこと＋もう一度」の形 | 同じ画面の文と言い方をそろえる（「サポートにお問い合わせください」） | 「セキュリティトークン」「Meta API」など仕組みの名前が残る。未知の理由で生のコードを出す（1517）。便2 以降の対象 |

成功を証明する外部の数値は見つけていない。本設計は数値の効果ではなく、PO の要件と指針の一致を根拠にする。

## 4. 便1 の技術 How

### 4-1. 方針

- サーバーは理由コードだけを返す。文は画面の1つの対応表から選ぶ。2画面はその表を共有する（SSOT）。
- 表示は今ある帯（ChannelsPage の banner）とお知らせ（DiscordOwnServerPanel の notice）をそのまま使う。新しい部品・新しい色は作らない。
- 行動ボタンは付けない。次にすることは「もう一度お試しください」等で、同じ画面の今の連携ボタンを押せばよいため。

### 4-2. 理由コードの一覧（12 種類＋未知）

| # | コード | どこで起きるか | 起きる条件（recon §3） |
|---|---|---|---|
| 1 | invalid_state | 戻り口 254 | 札が無い（期限 600 秒切れ・使い回し） |
| 2 | missing_state | 戻り口 234 | 戻りに札が無い |
| 3 | invalid_payload | 戻り口 261 / 265 | 札の中身が足りない |
| 4 | missing_code | 戻り口 274 | 戻りに code が無い |
| 5 | missing_guild_id | 戻り口 238 | サーバーが選ばれていない |
| 6 | invalid_guild_id | 戻り口 243 | サーバー番号の形が違う |
| 7 | guild_mismatch | 戻り口 284 | 選んだサーバーと Discord の答えが違う |
| 8 | guild_already_registered | 戻り口 328 | そのサーバーは既に登録済み |
| 9 | code_exchange_failed | 戻り口 278（136 / 146） | Discord との確認の通信が失敗・拒否 |
| 10 | missing_guild_in_token | 戻り口 278（154） | Discord の答えにサーバーが無い |
| 11 | service_unavailable | 戻り口 250（redis_error）・278（discord_not_configured）・開始 186-203 | こちらの仕組みの一時的な不具合・設定不足 |
| 12 | permission_denied | 開始 182-185 | 自社用で権限が無い |
| — | unknown | 上に無いコード・通信失敗・切断の失敗 | 予備 |

- 11 は、利用者にできることが同じ（時間をおいて試す・続けばサポート）なので1つの文にまとめる。サーバーのコード（redis_error・discord_not_configured）は記録のため今のまま残し、画面の対応表で 11 の文に写す。
- 切断（ChannelsPage 244）の失敗は unknown の切断版 `disconnectFailed` を使う（§4-3 の 14）。

### 4-3. 文の一覧（PO 確認待ち。ja。en は同じ意味で作る）

| # | 理由 | 文（ja） |
|---|---|---|
| 1 | invalid_state | 時間切れにより連携できませんでした。もう一度お試しください。 |
| 2 | missing_state | Discordでの操作が途中で止まったため、連携できませんでした。もう一度お試しください。（PO 2026-11-07「1」で採用） |
| 3 | invalid_payload | 同上（2 と同じ文言キー） |
| 4 | missing_code | 同上（2 と同じ文言キー） |
| 5 | missing_guild_id | サーバーを選択していないため連携できませんでした。追加するサーバーを選んでください。（PO 2026-11-07 の文） |
| 6 | invalid_guild_id | 同上（2 と同じ文言キー） |
| 7 | guild_mismatch | 選択したサーバーが確認できませんでした。もう一度お試しください。（PO 2026-11-07 の文） |
| 8 | guild_already_registered | このサーバーはすでに登録されているため、連携できませんでした。別のサーバーを選んでください。 |
| 9 | code_exchange_failed | Discordとの確認がうまくいかず、連携できませんでした。時間をおいてもう一度お試しください。 |
| 10 | missing_guild_in_token | 同上（7 と同じ文言キー） |
| 11 | service_unavailable | システムの一時的な不具合で連携できませんでした。時間をおいてもう一度お試しください。続く場合はサポートにお問い合わせください。 |
| 12 | permission_denied | この操作をする権限がありません。会社の管理者に権限を付けてもらってください。 |
| 13 | unknown | 連携できませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。 |
| 14 | 切断の失敗 | 連携を外せませんでした。もう一度お試しください。続く場合はサポートにお問い合わせください。 |

- 2・3・4・6 は、利用者から見て同じ出来事（戻りの情報がおかしい）なので同じ文。7・10 も同じ。
- 文言キーは 10 個: stateExpired（1）・discordInterrupted（2・3・4・6）・serverNotSelected（5）・serverNotVerified（7・10）・serverAlreadyRegistered（8）・discordCheckFailed（9）・serviceUnavailable（11）・permissionDenied（12）・unknown（13）・disconnectFailed（14）。すべて `discordConnect.error.` の下。

### 4-4. 変えるファイル（変更前→後）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| backend/app/routers/discord_oauth.py:182-185 | `detail="権限が不足しています: tenant.profile.edit"` | `detail={"reason": "permission_denied"}` |
| backend/app/routers/discord_oauth.py:188-191 | `detail="一時的に Discord 連携を開始できません（設定不足）"` | `detail={"reason": "discord_not_configured"}` |
| backend/app/routers/discord_oauth.py:200-203 | `detail="一時的に Discord 連携を開始できません（Redis 接続失敗）"` | `detail={"reason": "redis_error"}` |
| frontend/src/features/discord-connect/discordConnectError.ts（新規） | — | `getDiscordConnectErrorKey(reason: string \| null): string`。§4-2 のコード→文言キーの表。表に無ければ `discordConnect.error.unknown`。ADR-159 の discordSendError.ts と同じ書き方（定数の配列＋switch） |
| frontend/src/pages/channels/ChannelsPage.tsx:135-137 | `t("channels.discordConnectError")` 固定 | `t(getDiscordConnectErrorKey(url.searchParams.get("reason")))` |
| frontend/src/pages/channels/ChannelsPage.tsx:226 | `e instanceof ApiError ? e.message : …` | discordConnectError.ts に `getDiscordConnectErrorReason(e: unknown): string \| null` を置き（`e` が `ApiError` で `responseDetail` が `reason` 文字列を持つときだけ返す。それ以外は null）、その結果を `getDiscordConnectErrorKey` に通す。取り出しはこの1関数だけにする |
| frontend/src/pages/channels/ChannelsPage.tsx:244 | 同上（切断） | `t("discordConnect.error.disconnectFailed")` |
| frontend/src/pages/admin/DiscordOwnServerPanel.tsx:121-126 | guild_already_registered だけ専用、他は connectError | `t(getDiscordConnectErrorKey(params.get("reason")))` |
| frontend/src/pages/admin/DiscordOwnServerPanel.tsx:144-145 | 開始の失敗で `discordOwnServer.requestFailed`（`catch {` で e を受けていない） | `catch (e)` にして 226 と同じ2関数を通す |
| frontend/src/locales/ja.json・en.json | `channels.discordConnectError`（1529）、`discordOwnServer.connectError`（3574）、`discordOwnServer.guildAlreadyRegistered`（3575） | 新しい `discordConnect.error.*` 10 キー（§4-3 の下の一覧）。古い3キーは使う所が無くなるので消す（同じ意味の文を2か所に置かない） |
| docs/handoff/discord-oauth-ownership-proof/design.md:45 | 「接続に失敗しました（理由: …）」 | 事実（recon §3-3）と、本設計で直したことを書く |

- 開始の失敗の受け取りの事実: 両画面とも `api.post("/discord/oauth/start")`（ChannelsPage.tsx:194・DiscordOwnServerPanel.tsx:139）。POST は送り直しをしない（frontend/src/lib/api.ts:131-133）ので、503 も 403 と同じく api.ts:164-171 で `new ApiError(message, status, body.detail)` になり、`responseDetail` は `{"reason": ...}` そのもの。通信そのものの失敗・時間切れは ApiError でないので unknown の文になる

触らない範囲:
- 戻り口の判定の順番・保存の処理・監査記録（discord_oauth.py 220-334 の処理は変えない。コードの文字列も変えない）
- Meta 連携の文（channels.errorReason.*）と ChannelsPage 161-164（便2 以降）
- discordOwnServer.requestFailed の他の使い所（削除・取り込み・適用。便1 の対象外）
- 帯・お知らせの部品・色

### 4-5. K3 の入口が何も書き込まないこと（事実）

- 戻り口は state が空でなく guild_id が 17〜19 桁なら `consume_state` を呼ぶ（discord_oauth.py:233-254）
- `consume_state` は Redis で GET と DEL を1つの取引で行う（backend/app/services/oauth_state.py:159-162）。無い鍵の DEL は何も変えない
- `payload is None` なら 254 で返り、DB の処理（289 以降）に入らない
- 書くのはサーバーのログ1行（256 行の warning）だけ

### 4-6. 試験

| 試験 | 中身 |
|---|---|
| frontend: discordConnectError.test.ts | 14 の理由（§4-3）すべてで期待の文言キーが返る。未知・null で unknown |
| frontend: 戻り口のコードと表の突き合わせ | 試験が `readFileSync("../backend/app/routers/discord_oauth.py", "utf8")` で読み、次の3つの正規表現でコードを取り出す: `/reason=([a-z_]+)/g`（278 行の `reason={e.reason}` は `{` で始まるので拾わない）、`/_ExchangeError\("([a-z_]+)"\)/g`、`/"reason":\s*"([a-z_]+)"/g`（開始の3か所）。重複を除いた集合が 13 個（戻り口 12＋permission_denied）であることと、全部が表にあることを確かめる（数の確かめで正規表現の壊れも止める）。読めることの根拠: CI の frontend 試験（.github/workflows/e2e.yml の unit-run）は 95 行の `actions/checkout@v5` を with なしで使い repo 全体を取り出し、92 行で `working-directory: frontend`。同じ読み方の前例 frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:127 |
| frontend: ChannelsPage・DiscordOwnServerPanel | `?discord_status=error&reason=invalid_state` で時間切れの文、`reason=guild_already_registered` で両画面が同じ文 |
| backend: test_discord_oauth.py | 開始の 403・503 の detail が `{"reason": ...}` で、日本語を含まない |
| i18n | discordConnectError.test.ts で、表が返し得る全キーが ja.json と en.json の両方にあることを確かめる（既存の i18n 検査 frontend/scripts/check-i18n-missing-keys.js:30 は t("…") に直書きされたキーしか見ないため。手本 src/components/CalendarView.test.tsx） |

## 5. アプリ全体の見張り（A1。PO の承認後に便0 として作る）

| 見張り | 数えるもの | 基準値 | 置き場 |
|---|---|---|---|
| W1 サーバーの文の直書き | backend/app の HTTPException で detail が文字列（識別子の形を除く）の数。数え方は recon §4 の ast と同じ | 724（日本語 662＋英語の文 62） | 新しい検査の台本＋基準値のファイル。CI で「基準値を超えたら落ちる・下がったら基準値の更新を促す」 |
| W2 次の行動の無い文言 | ja.json で「失敗」「エラー」`できません`を含み、次の行動の語を含まないキー | 215 | 同上 |

- W2 は語の有無だけの機械判定。語があっても行動になっていない文は拾えない（限界）。人の審査（reviewer）で補う
- 画面で `e.message` をそのまま出す箇所（342 行）は、表示先を1行ずつ確かめないと正確に数えられない。便2 の recon で数え、見張り W3 にするか決める
- 見張りの置き場（既存の CI の流れに足すか、新しい流れか）と台本の言語は、審査で既存の見張り（lint-tenant-schema.yml 等）の形に合わせて決める

## 6. 弊害・トレードオフ

- 2・3・4・6 を同じ文にするため、問い合わせを受けた側は画面の文だけでは理由を区別できない。理由はサーバーのログ（warning）と URL のコードで追える
- 古い3キーを消すため、他の画面が使っていれば壊れる。recon では使い所は 3-3 の箇所だけ（実装前に grep で 0 件を確かめる）
- 開始の 503 の detail を code に変えるため、文を読んで判定している他の呼び出し元があれば壊れる。呼び出し元は ChannelsPage:194 と DiscordOwnServerPanel:139 の2つ（実装前に grep で確かめる）

## 7. 計画票

| 便 | 中身 | 状態 |
|---|---|---|
| 便1 | Discord 連携（本書 §4） | PO 承認済み・実装カード作成へ |
| 便0 | 見張り W1・W2（§5） | アプリ全体の KGI の承認待ち |
| 便2 以降 | Meta・Google カレンダー・外部連携の戻り口、画面で e.message を出す箇所、サーバーの直書き（多い画面から） | 未着手 |

## 8. 継続（維持の仕組み）

- 便1: 戻り口のコードと表の突き合わせ試験（§4-6）で、新しい理由の入れ忘れを止める
- 全体: 見張り W1・W2 の基準値を便ごとに下げる。決まりは ADR-1071
- 守り手: frontend の CI の試験（突き合わせ・文の一致）。基準値の引き下げは便ごとに Opus

## 9. 未確認

- （確認済み・2回目の審査）frontend の試験から ../backend は読める。根拠は §4-6
- （決定済み）en の文は Opus が ja の承認済みの文から作り、実装カード card-bin1.md §3-9 に全文を置いた（en は PO の承認対象外。ja と同じ意味・同じ順）

## 10. 設計審査の記録

| 回 | 日時 | 審査役 | 判定 | 指摘と対応 |
|---|---|---|---|---|
| 1 | 2026-11-07 14:01 UTC | クラウドの Sonnet（読むだけ。対象 commit 7643967a8） | REVISE | (1) 関数で返す文言キーは既存の i18n 検査 check-i18n-missing-keys.js:30 に見えない → §4-6 の i18n 行を「試験で ja/en 両方のキーを確かめる」に直した (2) 前例 discordSendError.ts は detail.reason で受ける → 開始の detail を `{"reason": ...}` にそろえた（§4-4・§4-6） (3) K3 は保管庫（Redis）が止まっていると別の文になる・ログイン不要 → K3 に前提と外れたときの扱いを書いた (4) K1 の「11 コード」は grep で 12 → 直した |

| 2 | 2026-11-07 14:07 UTC | クラウドの Sonnet（読むだけ。対象 commit 05fda8f27） | APPROVE（軽い直し付き） | (A) 1回目の4点はすべて直っている (B) ../backend は読める。根拠を frontend-check.yml から実際に試験を回す e2e.yml:92・95 に差し替え、§9 を確認済みにした (C1) 開始の失敗の `responseDetail` の形 → Opus が api.ts:131-133・164-171 を読み、POST は `body.detail` がそのまま入ると確かめ §4-4 に書いた。取り出しを1関数にまとめた (C2) 突き合わせの正規表現が曖昧 → §4-6 に3つの式と数の確かめを書いた (C3) 返事が途中で切れて読めなかった（実行記録の上限） |

- 1回目の §9 の未確認（../backend を読めるか）は、2回目で確認済みになった
