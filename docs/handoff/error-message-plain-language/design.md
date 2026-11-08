# Phase 3 設計 — 失敗したときの文（便1: Discord 連携）＋アプリ全体の見張り

- 状態: 設計審査済み（2回目 APPROVE）・PO 承認済み（Discord の KGI と §4-3 の文の一覧。2026-11-07。PO が 5 と 7 の文を自分で書き直し、2 の文は Opus の言い換え案に「1」）。便1 の実装承認: 同日 PO「1」（選択肢「この文で決まり、全部の文がそろったので作り始めます」）。便1 は本番反映済み・K3 PO 目視合格（2026-11-07）。アプリ全体の KGI（§2-2）は PO 承認済み（2026-11-08「1」）。便0（見張り）の実装カード `docs/handoff/error-message-plain-language/card-guard.md`
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

### 2-2. アプリ全体 — PO「1」で承認済み（2026-11-08）

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 新しく足した失敗の文が決まりに合わないと、CI が落ちる | 試しの PR で悪い例（サーバーに日本語の文の直書きを1つ足す／次の行動の無い文言を1つ足す）を入れ、見張りが赤になることを確かめる |
| A2 | 決まりに合わない今の文の数が、便ごとに減り、最後は 0 | 基準値のファイルの数（W1・W2。2026-11-08 の数え直しで W1 は 739（106 ファイル・設計審査の実測。str と f 文字列だけなら 722）・W2 は 209。recon §4-2）を便ごとに記録 |

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

## 5. アプリ全体の見張り（A1。便0。実装カード card-guard.md）

| 見張り | 数えるもの | 基準値 | 置き場 |
|---|---|---|---|
| W1 サーバーの文の直書き | backend/app の HTTPException の detail のうち (a) 中の文字列に日本語がある（dict・f 文字列も含む）か (b) 文字列・f 文字列で識別子の形でないもの。数え方の全文は card-guard.md §3-2 | 739（106 ファイル。設計審査が §3-2 の決まりで数えた実測。str と f 文字列だけなら 722。正の値は台本が書く基準値のファイル） | `backend/tests/test_error_detail_guard.py`＋`backend/tests/error_detail_baseline.json`（ファイルごとの数）。backend の pytest で走る。増えたら赤・減ったら基準値の引き下げを求めて赤 |
| W2 次の行動の無い文言 | ja.json の葉の文字列で「失敗」「エラー」`できません`を含み、次の行動の語（もう一度・お試し・連絡・確認して・ください）を含まないキー | 209 | `frontend/scripts/check-error-text-next-action.js`＋`frontend/scripts/error-text-next-action-baseline.json`（キーの一覧と例外）。`npm run check:all` に入れる。新しいキーは赤・直ったキーが残っていたら赤 |
| G1 突き合わせ試験の穴 | サーバーの Discord 連携のファイルだけを変えた PR で、画面の突き合わせ試験が走らない | — | `.github/workflows/e2e.yml` の変更判定（detect-changes の frontend）に `backend/app/routers/discord_oauth.py` を足す |

- W2 は語の有無だけの機械判定。語があっても行動になっていない文は拾えない（限界）。人の審査（reviewer）で補う
- 画面で `e.message` をそのまま出す箇所（342 行）は、表示先を1行ずつ確かめないと正確に数えられない。便2 の recon で数え、見張り W3 にするか決める
- 置き場の決定（2026-11-08 Opus）: 新しい CI の流れは作らない。W1 は backend の pytest（既存の CI で毎回走る）に、W2 は前例 `frontend/scripts/check-loading-clear.js` と同じ形の台本を `check:all` に足す。基準値はファイルごとの数（W1）とキーの一覧（W2）。前例と同じく「増えても減っても赤」で、直したら基準値を下げることを強制する
- 数え方の差: 2026-11-07 の 662＋62 は数え方が少し違った（recon §4-2）。2026-11-08 に origin/main `857fa2721` で数え直した値を正とする。基準値の正の値は台本が書き出したファイル

## 6. 弊害・トレードオフ

- 2・3・4・6 を同じ文にするため、問い合わせを受けた側は画面の文だけでは理由を区別できない。理由はサーバーのログ（warning）と URL のコードで追える
- 古い3キーを消すため、他の画面が使っていれば壊れる。recon では使い所は 3-3 の箇所だけ（実装前に grep で 0 件を確かめる）
- 開始の 503 の detail を code に変えるため、文を読んで判定している他の呼び出し元があれば壊れる。呼び出し元は ChannelsPage:194 と DiscordOwnServerPanel:139 の2つ（実装前に grep で確かめる）

## 7. 計画票

| 便 | 中身 | 状態 |
|---|---|---|
| 便1 | Discord 連携（本書 §4） | 本番反映済み・PO 目視合格（2026-11-07） |
| 便0 | 見張り W1・W2・G1（§5。card-guard.md） | 本番反映済み（2026-11-08。基準値 W1 739・W2 209） |
| 便2 | サーバーの共通の2種類の文（項目の指定なし・重複や食い違い）92 件を理由コードに＋画面の共通の対応表（§11。card-bin2.md） | 本番反映済み（2026-11-08 12:54 JST・#5287・W1 739→647） |
| 便3 | 「（指定された）〇〇が見つかりません」の形の 198 件を `not_found:<対象>` に＋画面で名前を残した文（§12） | 設計案作成済み（2026-11-08） |
| 便4 以降 | 残りの「見つかりません」（f 文字列 11・案内つき 9・その他 7・英語 24。§12-2）、Meta・Google カレンダー・外部連携の戻り口、画面で e.message を出す箇所、残りのサーバーの直書き | 未着手 |

## 8. 継続（維持の仕組み）

- 便1: 戻り口のコードと表の突き合わせ試験（§4-6）で、新しい理由の入れ忘れを止める
- 全体: 見張り W1・W2 の基準値を便ごとに下げる。決まりは ADR-1071
- 理由コードの対応表を新しく作ったら、その理由コードを出すサーバーのファイルを `.github/workflows/e2e.yml` の detect-changes の frontend の一覧に足す（G1 と同じ形。サーバーだけ変えた PR でも突き合わせ試験を走らせるため）。ADR-1071 の維持の仕組みにも書く
- 守り手: CI（backend の pytest の W1・frontend の check:all の W2・e2e の突き合わせ試験）。基準値は直した PR の中で下げる（下げないと CI が赤）

## 9. 未確認

- （確認済み・2回目の審査）frontend の試験から ../backend は読める。根拠は §4-6
- （決定済み）en の文は Opus が ja の承認済みの文から作り、実装カード card-bin1.md §3-9 に全文を置いた（en は PO の承認対象外。ja と同じ意味・同じ順）

## 10. 設計審査の記録

| 回 | 日時 | 審査役 | 判定 | 指摘と対応 |
|---|---|---|---|---|
| 1 | 2026-11-07 14:01 UTC | クラウドの Sonnet（読むだけ。対象 commit 7643967a8） | REVISE | (1) 関数で返す文言キーは既存の i18n 検査 check-i18n-missing-keys.js:30 に見えない → §4-6 の i18n 行を「試験で ja/en 両方のキーを確かめる」に直した (2) 前例 discordSendError.ts は detail.reason で受ける → 開始の detail を `{"reason": ...}` にそろえた（§4-4・§4-6） (3) K3 は保管庫（Redis）が止まっていると別の文になる・ログイン不要 → K3 に前提と外れたときの扱いを書いた (4) K1 の「11 コード」は grep で 12 → 直した |

| 2 | 2026-11-07 14:07 UTC | クラウドの Sonnet（読むだけ。対象 commit 05fda8f27） | APPROVE（軽い直し付き） | (A) 1回目の4点はすべて直っている (B) ../backend は読める。根拠を frontend-check.yml から実際に試験を回す e2e.yml:92・95 に差し替え、§9 を確認済みにした (C1) 開始の失敗の `responseDetail` の形 → Opus が api.ts:131-133・164-171 を読み、POST は `body.detail` がそのまま入ると確かめ §4-4 に書いた。取り出しを1関数にまとめた (C2) 突き合わせの正規表現が曖昧 → §4-6 に3つの式と数の確かめを書いた (C3) 返事が途中で切れて読めなかった（実行記録の上限） |
| 3 | 2026-11-07 19:00 UTC | クラウドの Opus（読むだけ。対象 commit 1d54a5107。アプリ全体の見張り W1・W2・G1） | REVISE | 実測: W1 の自己点検は合計 6 で合う・backend/app は 739 件 106 ファイル・読めないファイル 0。W2 は 209 件・自己点検 0/1/1/2 で合う。G1 は e2e.yml:50-55 と :84-87 で効く。直し: (1) 指示書 §5 (1e) を switch -C ＋ rev-parse の一致確認に直した（前例 stageW-card.md） (2) 自己点検の b.0 を失敗の文にし、基準 keys に b.0 を足した（配列の道すじも数えることを確かめる） (3) W1 の目安を実測 739 にした（§2-2・§5・指示書 §5 手順4） |
| 4 | 2026-11-08 | クラウドの Opus（便2 §11 と card-bin2.md） | 止まった（判定なし） | 審査役が写しをフォルダごと消す命令を使い、クラウドの見張りに止められた → 依頼文に「消す命令は使わず、毎回新しい場所に mkdir と git archive で写しを作る」を足して出し直した |
| 5 | 2026-11-08 | クラウドの Opus（便2 §11 と card-bin2.md。カードどおりに写しで試しに置き換え） | REVISE | 実測: 置き換え 92 件 47 ファイル・基準値 647 件 105 ファイル・tsc の新しい誤り 0・vitest 14 緑・pytest の見張り3本と突き合わせ2本が緑。直し: (1) 必須: 試験2ファイルの日本語の名前と期待値が `local/no-japanese-literal` の警告 13 件になり、記録の前の点検（`--max-warnings=0`）で止まる → 試験の名前を英語にし、日本語の期待値は ja.json から読む形にした（§3-6・§3-8） (2) 手順3の「出力が空」は説明のコメント4行が残るので成り立たない → その4行だけ許す書き方にした (3) 手順 6d に `--config vitest.unit.config.ts --project unit` を足した |
| 6 | 2026-11-08 | Opus（自分の確かめ。対象 commit 098c59610 の実装と実行記録） | 直しの成立を確認 | 5回目の3つの直しが実装で成り立った: (1) eslint の警告 0（rc=0）・試験の名前は英語・ja の期待値は ja.json から読む (2) 手順3の残りは決めた説明のコメント4行だけ (3) vitest 14 緑（unit の設定で実行）。サーバー側の差分は置き換え 92 行だけ・基準値 647 件 105 ファイル。コードの審査はマージ前の reviewer（opus）が別に行う |
| 7 | 2026-11-08 | クラウドの Opus（読むだけ。便3 §12。対象 commit ab93c2eff） | REVISE | 実測: 198 行は実物と食い違い 0・既存コードとぶつかり無し・置き換え後 449 件 93 ファイルで 65 ファイルが減るだけ。直し: (1) 必須: C5 の e2e は `.github/workflows/e2e.yml:251` の `if: false` で CI で走らない → 判定を pytest と vitest にし、e2e の見本は合わせて直すだけにした (2) C6 の「Discord紐付け」は今の ja.json に既にある → 今の辞書に無い3つの文で確かめる形にした (3) en の名前が2組重なっていた → `supplier_master` を The supplier master entry、`notification_channel` を The notification channel にした (4) §12-3 に i18next の `:` の扱いを書いた |
| 8 | 2026-11-08 11:00 UTC | クラウドの Opus（読むだけ。便3 §12。対象 commit 9ff36fd07） | APPROVE | 実測: 1回目の4指摘はすべて直った。C6 の3つの文は ja.json・en.json・frontend/src で 0 件。en の名前 67 個の重なり 0 組。i18n.ts に nsSeparator・keySeparator の設定は無く初期値（`:` と `.`）で、§12-3 の書き方と合う。§12-5 と §12-10 はコード別の件数が一致（67 種類・198 件）。推奨: C5 にどの CI の仕事で判定するかを書く → 書き足した |

- 1回目の §9 の未確認（../backend を読めるか）は、2回目で確認済みになった

## 11. 便2: サーバーの共通の2種類の文を理由コードにする（A2 の1回目）

- 状態: 本番反映済み（2026-11-08 12:54 JST。#5287。B5 合格）。設計は 2026-11-08 Opus。PO の選択「2」（サーバーの文を直す作業から始める）と「PRマージ、デプロイまで完走」の委任に基づく。実装カード `docs/handoff/error-message-plain-language/card-bin2.md`。
- 調べた土台: origin/main `b6b89095c4d9cbedca3c17b66b0191ec96457413`。

### 11-1. 何が起きるか（利用者に見える変化）

- 保存の画面で「変えた項目が無いまま保存」したとき、または「同じものが既にある・関係するデータと合わない」ときに出る文が、日本語の画面では §11-4 の日本語、英語の画面では英語になる。
- 今は、サーバーが作った日本語の文（例「更新するフィールドを指定してください」「制約違反」）が、英語の画面でもそのまま出る。次にすることも書かれていない。

### 11-2. 現在地（事実）

- 対象の文と件数（W1 の数え方。backend/app の全 .py ファイル。文字どおりの一致の数と ast の数が同じ＝この文は `HTTPException` の detail 以外に使われていない）:

| 文（今） | 件数 | 新しい理由コード |
|---|---|---|
| 更新するフィールドを指定してください | 42 | `no_fields_to_update` |
| 更新するフィールドを少なくとも1つ指定してください | 5 | `no_fields_to_update` |
| 更新フィールドが指定されていません | 3 | `no_fields_to_update` |
| 制約違反 | 19 | `conflict_constraint` |
| 重複または制約違反 | 15 | `conflict_constraint` |
| 重複または FK 違反 | 6 | `conflict_constraint` |
| 会社の登録に失敗しました（company_code 重複または制約違反の可能性） | 1 | `conflict_constraint` |
| 担当者の登録に失敗しました（contact_code 重複または制約違反の可能性） | 1 | `conflict_constraint` |

  合計 92 件（`no_fields_to_update` 50 件・46 ファイル、`conflict_constraint` 42 件・21 ファイル）。状態番号（400・409・422）は変えない。
- 画面がサーバーの文を受ける所は `frontend/src/lib/api.ts` の2か所（`request` の 163-171 行・`requestForm` の 251-258 行）。detail が文字列ならそのまま `ApiError.message` にする。サーバーだけコードに変えると、画面にコードがそのまま出る → 画面とサーバーを同じ PR で変える。
- 対象の文に頼る所（`git grep`、origin/main、backend/app と docs を除く）: `backend/tests/test_super_admin_unit_ignore_phrases.py:124`（`"重複または制約違反"` と一致を見る）の1か所だけ。画面のコード・e2e・scripts には無い。
- `err.message` や detail を決まったコードと比べる画面のコード（`frontend/src/lib/api.ts:84`・`frontend/src/lib/auth/authErrorMessage.ts`・`frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:131`・`frontend/src/features/tcg-product-import/productDetailModel.ts:205`・`frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:145-146`・`frontend/src/pages/super-admin/ViewerAccountsPage.tsx:282`・`frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:139` ほか）は、今回の2つのコードを使っていない。表に無いコードは今までどおりそのまま `message` に入るので、動きは変わらない。
- 文言の表は `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の2つだけ（キー数は同じ）。`apiError` の区切りはまだ無い。
- 直接 `fetch` する画面（RegisterPage など 14 ファイル）は、今回の 47 ファイルの口を呼ばない（呼び先は public/register・erp・shipping・inbox など）。

### 11-3. 方針

- サーバー: 92 か所の detail を理由コードの文字列に置き換える（W1 は識別子の形の文字列を違反にしない）。
- 画面: 共通の理由コード → 文言キーの対応表を1か所 `frontend/src/lib/apiErrorReason.ts` に作る（便1 の `frontend/src/features/discord-connect/discordConnectError.ts` と同じ考え）。`frontend/src/lib/api.ts` の2か所は、detail がこの表のコードのときだけ `i18n.t(キー)` を `message` にする。表に無いときは今までどおり。`ApiError.responseDetail` には元のコードが残る。
- 選ばなかった案: (a) サーバーで言語を見て文を返す → 文がサーバーと画面の2か所に分かれる（ADR-1071 は表1か所）。(b) 画面ごとに直す → 47 ファイルの口を呼ぶ画面が多く、同じ対応を何十か所にも書くことになる。
- 「見つかりません」の種類（221 件・75 ファイル・文 92 種類）は便3 以降。何が見つからないかの名前を残す形を別に決める。

### 11-4. 文（ja は ADR-1071 の型。en は同じ意味）

| キー | ja | en |
|---|---|---|
| `apiError.noFieldsToUpdate` | 変わった項目がないため、保存しませんでした。内容を変えてから、もう一度保存してください。 | Nothing was saved because no fields were changed. Change something, then save again. |
| `apiError.conflictConstraint` | 同じものがすでに登録されているか、関係するデータと合わないため、保存できませんでした。入力した内容を確かめて、もう一度お試しください。 | This could not be saved because the same item already exists or it does not match related data. Check what you entered and try again. |

- W2（ja の失敗の文に次にすることがあるか）: 1つ目は失敗の語が無いので数えない。2つ目は W2 の失敗の語と次にすることの語の両方を含むので通る。W2 の基準値 209 は変わらない。

### 11-5. KGI（便2）と確かめ方

| 基準 | 検証方法 |
|---|---|
| B1: サーバーの決まりに合わない文が 739 → 647 に減る | `python tests/test_error_detail_guard.py --write-baseline` の出力が 647 件。W1 の試験3本が緑。基準値の表の差分が 47 ファイルの行の減りだけ |
| B2: 2つのコードを受けたとき、日本語の画面は §11-4 の ja、英語の画面は en を出す | `frontend/src/lib/api.httpError.test.ts` に足す試験: `request` と `requestForm` それぞれ、2コード × ja/en で `err.message` が §11-4 と一致。`responseDetail` は元のコード |
| B3: 表に無いコードと dict の detail は今までどおり | 同じ試験: `"viewer_already_linked"` はそのまま `message`。`{detail: "x"}` は `"x"` |
| B4: 表のコードがサーバーで使われ、ja・en に文がある | 突き合わせ試験を両側に置く: `frontend/src/lib/apiErrorReason.test.ts`（`../backend/app` を読む・ja/en のキーを確かめる）と `backend/tests/test_api_error_reason_sync.py`（`frontend/src/lib/apiErrorReason.ts` を読む）。サーバーだけ・画面だけを変えた PR のどちらでも走る |
| B5: 本番に入る | Deploy to VPS が成功。本番の画面の JS に en の文が入っている（`https://app.salesanchor.jp/` の読み込む JS を curl で取り、§11-4 の en 1つ目の文を grep）。サーバーの返事は認証が要るので本番では見ない（CI の B1・B2 で確かめる） |

### 11-6. 弊害・トレードオフ

- 「同じものが既にある」と「関係するデータと合わない」を1つの文にまとめる。今のサーバーも区別していない（同じ例外の受け口）ので、失われる情報は無い。
- 2つのコードの文は、どの画面でも同じ文になる。画面ごとに言い分けたいときは、その画面が `responseDetail` のコードを見て別の文を出せる。
- 画面が `err.message` を出さずに自分の文を出している所は、見た目が変わらない（悪くはならない）。

### 11-7. 戻し方

- PR の取り込みを戻す（revert）。DB・設定の変更は無い。

### 11-8. 継続

- 新しく理由コードを足すときは `frontend/src/lib/apiErrorReason.ts` の表に1行と ja/en の文を足す。突き合わせ試験（B4）が、表とサーバーのずれを両側の PR で止める。
- W1 の基準値は直した PR の中で下げる（下げないと CI が赤）。

## 12. 便3: 「〇〇が見つかりません」を、名前を残した理由コードにする（A2 の2回目）

- 状態: 設計案作成済み（2026-11-08 Opus）。PO の選択「1」（「見つかりません」の文を直す設計を始める）に基づく。PO 承認済み（2026-11-08 PO「1」＝「この文と名前で決まり、作り始める」）: §12-4 の文の型と §12-5 の名前。
- 調べた土台: `36ea9b7b2a1a38509ca1d6c82d9ba9847b6ed8dd` の写し（git archive）。その後の origin/main `986df80cd404f2edec89ce6476ee2fbe876fecd2` までの 10 commit は、`backend/app`・`frontend/src/lib/api.ts`・`frontend/src/lib/apiErrorReason.ts`・`frontend/src/locales/ja.json`・`frontend/src/locales/en.json`・`frontend/tests-e2e/order-*.spec.ts`・`backend/tests/test_staff_me.py`・W1 の基準値に触れていない（`git diff --name-only 36ea9b7b2 986df80cd` の絞り込みが 0 行）。

### 12-1. 何が起きるか（利用者に見える変化）

- 開いていたものが別の人に消されたときなどに出る「リードが見つかりません」のような文が、日本語の画面では「リードが見つかりませんでした。画面を読み込み直してから、もう一度お試しください。」、英語の画面では英語になる。
- 今は、サーバーが作った日本語の文が英語の画面でもそのまま出る。次にすることも書かれていない。「import_job」「routing」「staff レコード」など内部の名前が出る文もある。

### 12-2. 現在地（事実）

- 数え方: W1（`backend/tests/test_error_detail_guard.py`）が違反とする 647 件を1件ずつ書き出し、文の形で分けた（調べ用の台本は読むだけ。結果の数は下の表）。
- 形で選んだ数（A 群）: 文が `(指定された|指定の)?〇〇が見つかりません` の形だけ・状態番号が 404・括弧の案内なし → 201 件・65 ファイル（すべて `backend/app/routers`）。このうち PDF の3か所（下の対象外）を除いた 198 件・65 ファイルが便3 の対象。状態番号の書き方は `status.HTTP_404_NOT_FOUND` 136・`404` 64・`http_status.HTTP_404_NOT_FOUND` 1。名詞は 68 種類（`指定された`・`指定の` を外して数える）。
- 対象外（便4 以降。形が違い、1件ずつ文を決める必要がある）:
  - PDF の3か所: `backend/app/routers/invoices.py:825`（GET /invoices/{invoice_id}/pdf）・`backend/app/routers/invoices.py:921`（GET /invoices/{invoice_id}/paypal-copy-pdf）・`backend/app/routers/invoices.py:990`（GET /quotes/{quote_id}/pdf）。画面は `window.open` で新しいタブに開く（`frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:152`・`:156`、`frontend/src/pages/quote-detail/QuoteDetailPage.tsx:92`）ので、サーバーの返事がそのままタブに出る。コードにすると今より読めなくなるため、今の日本語の文のまま残す
  - f 文字列 11: `backend/app/routers/companies.py:754`・`:759`、`backend/app/routers/contacts.py:755`・`:760`、`backend/app/routers/leads.py:3088`・`:3093`（統合の id 入り）、`backend/app/routers/leads.py:615`（400）、`backend/app/routers/super_admin_link_templates.py:93`・`:157`、`backend/app/routers/tcg_distribution.py:227`、`backend/app/routers/tcg_line_import.py:476`
  - 括弧の案内つき 9: `backend/app/routers/leads.py:1676`・`:1928`・`:2731`（409・Meta 接続）、`backend/app/routers/meta_inbox.py:423`（400）、`backend/app/routers/note_master.py:228`・`:252`、`backend/app/routers/reports.py:125`、`backend/app/routers/translation.py:324`・`:357`
  - その他 7: `backend/app/routers/buddy.py:110`（400）、`backend/app/routers/companies.py:366`（422）、`backend/app/routers/leads.py:1825`（400）、`backend/app/routers/order_shipping_details.py:455`、`backend/app/routers/tcg_distribution.py:111`・`:145`（422）、`backend/app/routers/tenant_admin_inventory_visibility.py:124`
  - 英語 24（例 `backend/app/routers/meta.py:255` の `Confirmation code not found` は `lp/src/pages/deletion-status.astro:69` と `frontend/tests-e2e/scene8-data-deletion.spec.ts:171` が使う）
  - `backend/app/services/tenant_users.py:6` の `USER_NOT_IN_TENANT`（同じ文だが 422 で、変数なので W1 の数に入らない。`backend/tests/test_tenant_user_ref_guard_pg.py:61` が一致を見る）は変えない。
- 対象の文に頼る所（`git grep -F` で 1 文ずつ。`backend/app`・`docs`・`frontend/src/locales` を除く全体）:
  - `frontend/tests-e2e/order-commission.spec.ts:151`・`:158`・`:165`、`frontend/tests-e2e/order-financial.spec.ts:158`、`frontend/tests-e2e/order-purchase.spec.ts:129`・`:136`・`:150`、`frontend/tests-e2e/order-shipping.spec.ts:173`・`:187`: 404 の返事の見本に今の文を入れている。画面（`frontend/src/components/OrderFinancialPanel.tsx:124`・`frontend/src/components/PurchaseDetailPanel.tsx:171`・`frontend/src/components/ShippingDetailPanel.tsx:225`）は状態番号 404 だけで「未登録」と判断し、文は読まない。
  - `backend/tests/test_staff_me.py:81`: `"staff" in detail or "見つかりません" in detail`。
  - 画面のコード（`frontend/src/**`、locales を除く）で対象の文を比べる所は 0 件。`backend/app` の中で detail の文を比べる所も 0 件（`.detail ==`・`in .detail` などの grep）。
- 今ある「見つからない」系のコード（`not_found`・`company_not_found`・`template_not_found`・`viewer_not_found`・`passkey_not_found`・`attachment_not_found`・`request_not_found`）は、画面が文字どおりに比べている（例 `frontend/src/pages/super-admin/ViewerAccountsPage.tsx`）。新しいコードはこれらと重ならない形にする。
- 画面がサーバーの文を受ける所は `frontend/src/lib/api.ts` の2か所（`request` の 164-175 行・`requestForm` の 255-264 行。便2 の `apiErrorReasonKey`）。直接 `fetch` する画面のうち A 群の口を呼ぶものは無い（`ShippingDetailPanel` の elogi-csv は detail を読まず `common.downloadFailed` を出す。`StaffJoinPage` の呼び先は public/staff-join で A 群の `_load_open_invite` ではない。`frontend/src/pages/inbox/InboxMessageThread.tsx:318` は A 群の口 GET /leads/{lead_id}/messages/{message_id}/attachment-url（`backend/app/routers/leads.py:1557`・`:1573`）を直接 `fetch` するが、`res.ok` だけを見て本文の文を読まない（`:322-326`）ので見え方は変わらない）。
- 3つ目の受け口 `requestBlob`（`frontend/src/lib/api.ts:201`・`getBlob` は `:284`）は失敗した返事の本文をそのまま文にする。呼び先は書き出し15か所と受信箱の添付ファイル（`frontend/src/pages/inbox/InboxMessageThread.tsx:294` → GET /leads/{lead_id}/attachments/{attachment_id}・`backend/app/routers/leads.py:1467`）だけで、A 群の口を呼ばない（便3 の影響なし）。請求書・見積もりの PDF は `getBlob` を通らず `window.open` で開く（対象外の PDF 3か所）。
- 名前の言葉は、画面の文言（`frontend/src/locales/ja.json`）に同じ物を指す見出しがあるものはそれに合わせた（§12-5 の「変えた理由」）。

### 12-3. 方針

- サーバー: 198 か所の detail を `not_found:<対象>` の文字列に置き換える（§12-10）。状態番号は変えない。W1 は `:` を含む識別子の形を違反にしない。
- 画面: `frontend/src/lib/apiErrorReason.ts` に「対象 → 名前の文言キー」の表（67 行）を足し、`not_found:` で始まる detail を `apiError.notFound`（名前を差し込む型の文）にする。表に無い対象は `apiError.notFoundUnknown`（名前なしの文）にする。コードの生の値は画面に出さない（ADR-1071 What 3）。`frontend/src/lib/api.ts` の2か所は、この結果で文を作る（関数を1つにまとめ、2か所から呼ぶ）。
- i18next ではキーの中の `:` が名前空間の区切りになる。だから detail をそのまま `i18n.t` に渡さない。`not_found:` の後ろを対象として切り出し、表から名前のキーを引いてから `i18n.t("apiError.notFound", { target: i18n.t(<名前のキー>) })` で文を作る。
- `not_found`（`:` なし）や `company_not_found` などの今のコードは `not_found:` で始まらないので、今までどおりそのまま `message` に入る。
- 選ばなかった案: (a) 名前ごとに 67 個のコードを作る（`lead_not_found` など）→ 便2 の表に 67 行と文 67 個が増え、型の文を1か所で直せない。(b) 名前をサーバーから文字で送る（`{"reason": "not_found", "target": "リード"}`）→ 名前の言葉がサーバーに残り、英語にできない（ADR-1071 What 4）。(c) 「見つかりません」を全部同じ文にする → 何が見つからないかが分からなくなる（PO の目的「誰でも分かる」に反する）。

### 12-4. 文の型（PO 承認済み 2026-11-08「1」。ja は ADR-1071 の型。en は同じ意味）

| キー | ja | en |
|---|---|---|
| `apiError.notFound` | {{target}}が見つかりませんでした。画面を読み込み直してから、もう一度お試しください。 | {{target}} could not be found. Reload the page and try again. |
| `apiError.notFoundUnknown` | お探しのものが見つかりませんでした。画面を読み込み直してから、もう一度お試しください。 | What you were looking for could not be found. Reload the page and try again. |

- 例: `not_found:lead` → 「リードが見つかりませんでした。画面を読み込み直してから、もう一度お試しください。」／"The lead could not be found. Reload the page and try again."
- 名前の文言キーは `apiError.notFoundTarget.<対象>`（ja は §12-5 の「日本語の名前」、en は「英語の名前」。en は文頭に来るので The・Your を含めて書く）。
- W2（`frontend/scripts/check-error-text-next-action.js:28-29`）: 型の文は失敗の語に当たらず（「見つかりません」は失敗の語ではない）、次にすることの語（もう一度・お試し・ください）を含む。名前だけの値は失敗の語を含まない。W2 の基準値 209 は変わらない。
- 差し込みは i18next の `{{target}}`。`frontend/src/i18n.ts:38` は `escapeValue: false`（React が守る）。

### 12-5. 名前の表（67 種類・198 か所。PO 承認済み 2026-11-08「1」）

| コード | 日本語の名前 | 英語の名前 | か所 | 今の文 | 名前を変えた理由 |
|---|---|---|---|---|---|
| `not_found:lead` | リード | The lead | 16 | リードが見つかりません / 指定されたリードが見つかりません |  |
| `not_found:order` | 注文 | The order | 11 | 注文が見つかりません |  |
| `not_found:company` | 会社 | The company | 7 | 会社が見つかりません / 指定された会社が見つかりません / 指定の会社が見つかりません |  |
| `not_found:condition` | 状態 | The condition | 7 | 状態が見つかりません |  |
| `not_found:product` | 商品 | The product | 6 | 商品が見つかりません / 指定の商品が見つかりません |  |
| `not_found:contact` | 担当者 | The contact | 6 | 担当者が見つかりません / 指定された担当者が見つかりません |  |
| `not_found:alias` | 別名 | The alias | 5 | aliasが見つかりません / 別名が見つかりません | 内部の英語名 alias を、同じものの画面の言葉「別名」(unitMaster.aliases) にした |
| `not_found:invoice` | 請求書 | The invoice | 5 | 請求書が見つかりません |  |
| `not_found:supplier_master` | 仕入元 | The supplier master entry | 5 | 仕入元が見つかりません | 英語は仕入先 supplier と言い分けた（口 /super-admin/suppliers は共用の名簿） |
| `not_found:team` | チーム | The team | 5 | チームが見つかりません |  |
| `not_found:bot` | ボット | The bot | 4 | Botが見つかりません | 画面の見出し「ボット」(nav.bots) に合わせた |
| `not_found:my_staff_profile` | あなたのスタッフ情報 | Your staff profile | 4 | 現在のユーザに紐づく staff レコードが見つかりません / 現在のユーザーに紐づく担当者が見つかりません | 内部の言葉 staff レコード を日常語にした; 同じもの（ログイン中の人の名簿行）を同じ言葉にした |
| `not_found:calendar_event` | 予定 | The event | 4 | イベントが見つかりません | 画面の「予定を編集」等 (schedule.editEvent) に合わせた |
| `not_found:quote` | 見積もり | The quote | 4 | 見積もりが見つかりません |  |
| `not_found:order_purchase` | 仕入情報 | The purchase details | 4 | 仕入情報が見つかりません |  |
| `not_found:payment_fee_setting` | 決済手数料設定 | The payment fee setting | 4 | 決済手数料設定が見つかりません |  |
| `not_found:product_category` | 商品カテゴリ | The product category | 4 | 商品カテゴリが見つかりません |  |
| `not_found:supplier` | 仕入先 | The supplier | 4 | 仕入先が見つかりません / 指定された仕入先が見つかりません |  |
| `not_found:role` | ロール | The role | 4 | ロールが見つかりません |  |
| `not_found:status` | ステータス | The status | 4 | ステータスが見つかりません |  |
| `not_found:unit` | 単位 | The unit | 4 | 単位が見つかりません |  |
| `not_found:order_financial` | 売上情報 | The sales details | 3 | 売上情報が見つかりません |  |
| `not_found:order_shipping` | 発送情報 | The shipping details | 3 | 発送情報が見つかりません |  |
| `not_found:staff` | スタッフ | The staff member | 3 | スタッフが見つかりません |  |
| `not_found:condition_definition` | コンディション定義 | The condition definition | 3 | コンディション定義が見つかりません |  |
| `not_found:product_format` | フォーマット | The format | 3 | フォーマットが見つかりません |  |
| `not_found:quantity_unit` | 数量単位 | The quantity unit | 3 | 数量単位が見つかりません |  |
| `not_found:distribution_target` | 配信先 | The distribution target | 3 | 配信先が見つかりません |  |
| `not_found:line_import_job` | 取り込み作業 | The import job | 3 | import_job が見つかりません | 内部の英語名 import_job を日常語にした |
| `not_found:calendar_owner` | 担当者 | The person in charge | 2 | 担当者が見つかりません |  |
| `not_found:conv_log` | 会話ログ | The conversation log | 2 | 会話ログが見つかりません |  |
| `not_found:channel_master` | チャネル | The channel | 2 | チャネルが見つかりません |  |
| `not_found:goal` | 目標 | The goal | 2 | 目標が見つかりません |  |
| `not_found:inventory_offer` | オファー | The offer | 2 | 指定されたオファーが見つかりません |  |
| `not_found:message` | メッセージ | The message | 2 | メッセージが見つかりません |  |
| `not_found:notice` | お知らせ | The notification | 2 | 知らせが見つかりません | 画面の見出し「お知らせ」(notices.title) に合わせた |
| `not_found:notification_channel` | チャンネル | The notification channel | 2 | チャンネルが見つかりません | 英語はチャネル channel_master と言い分けた（口 /notification-channels） |
| `not_found:own_inventory` | 自社在庫 | The own inventory item | 2 | 自社在庫が見つかりません |  |
| `not_found:product_master` | 商品マスタ | The product master entry | 2 | マスタが見つかりません | 何のマスタか分からないため、口 /super-admin/product-masters と画面の見出し「商品マスタ」(nav.products) に合わせた |
| `not_found:dex_entry` | 図鑑エントリ | The dex entry | 2 | 図鑑エントリが見つかりません |  |
| `not_found:knowledge_rule` | ルール | The rule | 2 | ルールが見つかりません |  |
| `not_found:note_master` | 備考マスタ | The note master entry | 2 | 備考マスタが見つかりません |  |
| `not_found:product_kind` | 大分類 | The division | 2 | 大分類が見つかりません |  |
| `not_found:product_line` | 小分類 | The product line | 2 | 小分類が見つかりません |  |
| `not_found:tcg_series` | シリーズ | The series | 2 | シリーズが見つかりません |  |
| `not_found:tcg_type` | 種別 | The type | 2 | 種別が見つかりません |  |
| `not_found:tenant` | テナント | The tenant | 2 | テナントが見つかりません |  |
| `not_found:weight_class` | 重量クラス | The weight class | 2 | 重量クラスが見つかりません |  |
| `not_found:archive_target` | アーカイブする対象 | The item to archive | 1 | 対象レコードが見つかりません | 内部の言葉 レコード を日常語にした |
| `not_found:archive` | アーカイブ | The archive | 1 | アーカイブが見つかりません |  |
| `not_found:badge` | バッジ | The badge | 1 | バッジが見つかりません |  |
| `not_found:close_reason` | 理由 | The reason | 1 | 指定された理由が見つかりません |  |
| `not_found:deal` | 商談 | The deal | 1 | 指定された商談が見つかりません |  |
| `not_found:message_label` | ラベル | The label | 1 | ラベルが見つかりません |  |
| `not_found:meta_page` | 接続済みの Facebook ページ | The connected Facebook Page | 1 | 該当する接続済 Page が見つかりません | 内部の言葉 該当する接続済 Page を日常語にした |
| `not_found:role_commission` | このロールの報酬 | The commission for this role | 1 | 該当ロールの報酬レコードが見つかりません | 内部の言葉 レコード を日常語にした |
| `not_found:purchase_order` | 仕入注文 | The purchase order | 1 | 仕入注文が見つかりません |  |
| `not_found:order_item` | 受注明細 | The order line | 1 | 指定された受注明細が見つかりません |  |
| `not_found:user` | ユーザー | The user | 1 | 指定されたユーザーが見つかりません |  |
| `not_found:shift` | シフト | The shift | 1 | シフトが見つかりません |  |
| `not_found:shipping_zone` | ゾーン | The zone | 1 | ゾーンが見つかりません |  |
| `not_found:shipping_rate` | 料金 | The rate | 1 | 料金が見つかりません |  |
| `not_found:staff_join_invite` | 招待 | The invitation | 1 | 招待が見つかりません |  |
| `not_found:staff_report` | レポート | The report | 1 | レポートが見つかりません |  |
| `not_found:discord_routing` | Discord紐付け | The Discord routing | 1 | routing が見つかりません | 内部の英語名 routing を画面の言葉「Discord紐付け」(superAdmin.suppliersAdmin.discordRouting) にした |
| `not_found:knowledge_link` | リンク | The link | 1 | リンクが見つかりません |  |
| `not_found:team_member` | メンバー | The member | 1 | メンバーが見つかりません |  |

- 同じ日本語の名前でも、指す物が違うものはコードを分けた（担当者: 顧客の担当者 `contact` と予定の担当者 `calendar_owner`。チャネル `channel_master` とチャンネル `notification_channel`。仕入元 `supplier_master`（全社の仕入元）と仕入先 `supplier`（各社の仕入先））。言葉は今の文のまま。あとで言い分けたくなったら表の1行だけ直せる。
- 「変えた理由」が空の行は、今の文の名前のまま（`指定された`・`指定の` だけ外す）。

### 12-6. KGI（便3）と確かめ方

| 基準 | 検証方法 |
|---|---|
| C1: サーバーの決まりに合わない文が 647 → 449 に減る | `python tests/test_error_detail_guard.py --write-baseline` の出力が 449 件。W1 の試験3本が緑。基準値の表の差分が 65 ファイルの行の減り（0 になったファイルは行ごと消える）だけ |
| C2: 67 種類のコードを受けたとき、日本語の画面は §12-4 の型に §12-5 の日本語の名前を入れた文、英語の画面は英語の文を出す | `frontend/src/lib/apiErrorReason.test.ts` に足す試験: 表の全 67 行 × ja/en で、作った文が「型＋名前」と一致し、`{{` やコードの生の値（`not_found:`）を含まない。`frontend/src/lib/api.httpError.test.ts` に足す試験: `request` と `requestForm` それぞれ `not_found:lead` で ja/en の文、`responseDetail` は元のコード |
| C3: 表に無い対象・今のコードは壊れない | 同じ試験: `not_found:zzz` は `apiError.notFoundUnknown` の文。`not_found`・`company_not_found`・`viewer_already_linked` はそのまま `message`。便2 の2コードは便2 の文のまま |
| C4: サーバーと表がずれない | 突き合わせ試験を両側に置く（便2 と同じ形）: `backend/tests/test_api_error_reason_sync.py` に「`backend/app` の `"not_found:<x>"` の x がすべて表にある」「表の対象がすべて `backend/app` で使われている」を足す。`frontend/src/lib/apiErrorReason.test.ts` にも同じ2つ。サーバーだけ・画面だけを変えた PR のどちらでも走る |
| C5: 404 の状態番号で判断している画面の動きが変わらない | 判定は CI の pytest（`.github/workflows/test.yml:114` の pytest-run）と vitest（`.github/workflows/e2e.yml:87` の unit-run が `npm run test:coverage` で `src/**/*.test.{ts,tsx}` を流す）だけで行う: `backend/tests/test_staff_me.py:81` を `== "not_found:my_staff_profile"` にして緑。`frontend/src/lib/api.httpError.test.ts` に足す試験で、`not_found:lead` を受けた `ApiError` の `status` が 404 のまま。`frontend/tests-e2e/order-*.spec.ts` の見本の detail も新しいコードに直すが、e2e の仕事は `.github/workflows/e2e.yml:251` の `if: false` で止まっていて CI で走らないため、判定には使わない（試験は Mac で回さない決まり） |
| C6: 本番に入る | Deploy to VPS が成功。本番の画面の JS（`https://app.salesanchor.jp/` が読み込む JS を curl で取る）に en の型の文 `could not be found. Reload the page and try again.`・en の名前 `The Discord routing`・ja の名前なしの文「お探しのものが見つかりませんでした。」が入っている（3つとも今の辞書には無いことを 2026-11-08 に確かめた。ja の「Discord紐付け」は今の画面に既にあるので確かめに使わない）。サーバーの返事は認証が要るので本番では見ない（CI の C1・C2 で確かめる） |
| C7: PO が名前を確かめる | PO が §12-5 の表（特に「変えた理由」の 11 行）を読んで○× → ○（2026-11-08 PO「1」） |

### 12-7. 弊害・トレードオフ

- 文がどの画面でも同じ型になる。画面ごとに言い分けたいときは、その画面が `responseDetail` のコードを見て別の文を出せる。
- 「画面を読み込み直す」で直らない場合（URL を手で打った・消えた物を指す古いリンク）もある。読み込み直すと一覧に無いことが分かり、次にすることが分かる。
- このリポジトリの外のプログラムがサーバーの日本語の文を読んで判断していると、動きが変わる。リポジトリの中には 0 件（§12-2）。外のプログラムは未確認。状態番号 404 は変えないので、番号で判断するものは影響を受けない。
- 画面が `err.message` を出さずに自分の文を出している所（例 `frontend/src/pages/inbox/useInboxState.ts:432` の `inbox.noLead`）は、見た目が変わらない。

### 12-8. 戻し方

- PR の取り込みを戻す（revert）。DB・設定の変更は無い。

### 12-9. 継続

- 新しく「見つからない」を返すときは `not_found:<対象>` を使い、`frontend/src/lib/apiErrorReason.ts` の表に1行と ja/en の名前を足す。表に無い対象は C4 の突き合わせ試験が両側の PR で止める。日本語の文の直書きは W1 が止める。
- `.github/workflows/e2e.yml` の detect-changes には足さない。サーバーだけを変えた PR は backend の pytest の突き合わせ試験（C4）で止まる（便2 §11-5 B4 と同じ）。
- W1 の基準値は直した PR の中で下げる（下げないと CI が赤）。

### 12-10. 置き換える 198 か所（ファイル:行 → 新しい detail）

| ファイル:行 | 口 | 今の文 | 新しい detail |
|---|---|---|---|
| backend/app/routers/archives.py:93 | POST /archives | 対象レコードが見つかりません | `not_found:archive_target` |
| backend/app/routers/archives.py:135 | POST /archives/{archive_id}/restore | アーカイブが見つかりません | `not_found:archive` |
| backend/app/routers/badges.py:105 | POST /badges/award | バッジが見つかりません | `not_found:badge` |
| backend/app/routers/bots.py:118 | GET /bots/{bot_id} | Botが見つかりません | `not_found:bot` |
| backend/app/routers/bots.py:218 | PATCH /bots/{bot_id} | Botが見つかりません | `not_found:bot` |
| backend/app/routers/bots.py:262 | POST /bots/{bot_id}/rotate-key | Botが見つかりません | `not_found:bot` |
| backend/app/routers/bots.py:298 | DELETE /bots/{bot_id} | Botが見つかりません | `not_found:bot` |
| backend/app/routers/buyback_prices.py:774 | GET /buyback-prices/{shop_product_id}/history | 指定の商品が見つかりません | `not_found:product` |
| backend/app/routers/buyback_prices.py:842 | POST /buyback-prices/{shop_product_id}/link | 指定の商品が見つかりません | `not_found:product` |
| backend/app/routers/calendar.py:234 | GET /calendar/owners | 現在のユーザーに紐づく担当者が見つかりません | `not_found:my_staff_profile` |
| backend/app/routers/calendar.py:330 | PATCH /calendar/owners/{user_id} | 担当者が見つかりません | `not_found:calendar_owner` |
| backend/app/routers/calendar.py:381 | PATCH /calendar/owners/{user_id} | 担当者が見つかりません | `not_found:calendar_owner` |
| backend/app/routers/calendar.py:471 | PATCH /calendar/events/{event_id} | イベントが見つかりません | `not_found:calendar_event` |
| backend/app/routers/calendar.py:478 | PATCH /calendar/events/{event_id} | イベントが見つかりません | `not_found:calendar_event` |
| backend/app/routers/calendar.py:551 | DELETE /calendar/events/{event_id} | イベントが見つかりません | `not_found:calendar_event` |
| backend/app/routers/calendar.py:555 | DELETE /calendar/events/{event_id} | イベントが見つかりません | `not_found:calendar_event` |
| backend/app/routers/close_reasons.py:116 | PATCH /close-reasons/{reason_id} | 指定された理由が見つかりません | `not_found:close_reason` |
| backend/app/routers/companies.py:353 | GET /companies/{company_id} | 会社が見つかりません | `not_found:company` |
| backend/app/routers/companies.py:389 | POST /companies | 指定されたリードが見つかりません | `not_found:lead` |
| backend/app/routers/companies.py:467 | POST /companies | 指定された商談が見つかりません | `not_found:deal` |
| backend/app/routers/companies.py:530 | PATCH /companies/{company_id} | 会社が見つかりません | `not_found:company` |
| backend/app/routers/companies.py:642 | DELETE /companies/{company_id} | 会社が見つかりません | `not_found:company` |
| backend/app/routers/conditions.py:200 | GET /conditions/{condition_id} | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/conditions.py:288 | PATCH /conditions/{condition_id} | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/conditions.py:341 | DELETE /conditions/{condition_id} | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/conditions.py:544 | GET /conditions/{condition_id}/aliases | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/conditions.py:579 | POST /conditions/{condition_id}/aliases | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/conditions.py:621 | DELETE /conditions/aliases/{alias_id} | 別名が見つかりません | `not_found:alias` |
| backend/app/routers/contact_channel_links.py:138 | GET /contacts/{contact_id}/channel-links | 担当者が見つかりません | `not_found:contact` |
| backend/app/routers/contacts.py:330 | GET /companies/{company_id}/contacts | 会社が見つかりません | `not_found:company` |
| backend/app/routers/contacts.py:402 | GET /contacts/{contact_id} | 担当者が見つかりません | `not_found:contact` |
| backend/app/routers/contacts.py:425 | POST /contacts | 指定の会社が見つかりません | `not_found:company` |
| backend/app/routers/contacts.py:536 | PATCH /contacts/{contact_id} | 担当者が見つかりません | `not_found:contact` |
| backend/app/routers/contacts.py:626 | DELETE /contacts/{contact_id} | 担当者が見つかりません | `not_found:contact` |
| backend/app/routers/conv_logs.py:391 | PATCH /leads/{lead_id}/conv-logs/{log_id} | 会話ログが見つかりません | `not_found:conv_log` |
| backend/app/routers/conv_logs.py:465 | DELETE /leads/{lead_id}/conv-logs/{log_id} | 会話ログが見つかりません | `not_found:conv_log` |
| backend/app/routers/conv_logs.py:554 | PUT /admin/channel-masters/{master_id}/visibility | チャネルが見つかりません | `not_found:channel_master` |
| backend/app/routers/conv_logs.py:594 | DELETE /admin/channel-masters/{master_id} | チャネルが見つかりません | `not_found:channel_master` |
| backend/app/routers/customer_priority.py:103 | POST /leads/{lead_id}/priority-score/override | リードが見つかりません | `not_found:lead` |
| backend/app/routers/customer_priority.py:250 | PATCH /leads/{lead_id}/message-labels/{label_id}/override | ラベルが見つかりません | `not_found:message_label` |
| backend/app/routers/discord_channel_invite.py:90 | POST /discord/channel-invite/{lead_id} | リードが見つかりません | `not_found:lead` |
| backend/app/routers/discord_remove.py:54 | (関数 _get_lead_discord_info) | リードが見つかりません | `not_found:lead` |
| backend/app/routers/discord_role_resync.py:62 | POST /discord/sync-role/{lead_id} | リードが見つかりません | `not_found:lead` |
| backend/app/routers/goals.py:203 | PATCH /goals/{goal_id} | 目標が見つかりません | `not_found:goal` |
| backend/app/routers/goals.py:243 | DELETE /goals/{goal_id} | 目標が見つかりません | `not_found:goal` |
| backend/app/routers/inventory_offers.py:700 | PATCH /super-admin/inventory-offers/{offer_id} | 指定されたオファーが見つかりません | `not_found:inventory_offer` |
| backend/app/routers/inventory_offers.py:762 | DELETE /super-admin/inventory-offers/{offer_id} | 指定されたオファーが見つかりません | `not_found:inventory_offer` |
| backend/app/routers/invoices.py:230 | GET /invoices/{invoice_id} | 請求書が見つかりません | `not_found:invoice` |
| backend/app/routers/invoices.py:256 | POST /invoices/from-quote/{quote_id} | 見積もりが見つかりません | `not_found:quote` |
| backend/app/routers/invoices.py:353 | POST /invoices | 指定された担当者が見つかりません | `not_found:contact` |
| backend/app/routers/invoices.py:462 | PATCH /invoices/{invoice_id} | 請求書が見つかりません | `not_found:invoice` |
| backend/app/routers/invoices.py:574 | POST /invoices/{invoice_id}/void | 請求書が見つかりません | `not_found:invoice` |
| backend/app/routers/invoices.py:644 | POST /invoices/{invoice_id}/paypal-link | 請求書が見つかりません | `not_found:invoice` |
| backend/app/routers/invoices.py:751 | POST /invoices/{invoice_id}/paypal-confirm | 請求書が見つかりません | `not_found:invoice` |
| backend/app/routers/leads.py:386 | GET /leads/{lead_id} | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:505 | PATCH /leads/{lead_id} | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:777 | DELETE /leads/{lead_id} | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:820 | POST /leads/{lead_id}/convert | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:993 | GET /leads/{lead_id}/messages | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:1195 | POST /leads/{lead_id}/messages/mark-read | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:1294 | POST /leads/{lead_id}/messages/mark-unread | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:1402 | POST /leads/{lead_id}/messages/{message_id}/translate | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:1418 | POST /leads/{lead_id}/messages/{message_id}/translate | メッセージが見つかりません | `not_found:message` |
| backend/app/routers/leads.py:1557 | GET /leads/{lead_id}/messages/{message_id}/attachment-url | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:1573 | GET /leads/{lead_id}/messages/{message_id}/attachment-url | メッセージが見つかりません | `not_found:message` |
| backend/app/routers/leads.py:1799 | POST /leads/{lead_id}/messages | リードが見つかりません | `not_found:lead` |
| backend/app/routers/leads.py:2451 | POST /leads/{lead_id}/messages/image | リードが見つかりません | `not_found:lead` |
| backend/app/routers/meta_inbox.py:586 | DELETE /meta/connect/{page_id} | 該当する接続済 Page が見つかりません | `not_found:meta_page` |
| backend/app/routers/notice_fallback_recipients.py:93 | PUT /notice-fallback-recipients | 会社が見つかりません | `not_found:company` |
| backend/app/routers/notices.py:98 | POST /notices/{notice_id}/read | 知らせが見つかりません | `not_found:notice` |
| backend/app/routers/notices.py:107 | POST /notices/{notice_id}/read | 知らせが見つかりません | `not_found:notice` |
| backend/app/routers/notifications.py:139 | PATCH /notification-channels/{channel_id} | チャンネルが見つかりません | `not_found:notification_channel` |
| backend/app/routers/notifications.py:155 | DELETE /notification-channels/{channel_id} | チャンネルが見つかりません | `not_found:notification_channel` |
| backend/app/routers/order_commissions.py:105 | (関数 _ensure_order_exists) | 注文が見つかりません | `not_found:order` |
| backend/app/routers/order_commissions.py:360 | DELETE /orders/{order_id}/commissions/{role} | 該当ロールの報酬レコードが見つかりません | `not_found:role_commission` |
| backend/app/routers/order_financials.py:96 | (関数 _ensure_order_exists) | 注文が見つかりません | `not_found:order` |
| backend/app/routers/order_financials.py:203 | GET /orders/{order_id}/financial | 売上情報が見つかりません | `not_found:order_financial` |
| backend/app/routers/order_financials.py:225 | PATCH /orders/{order_id}/financial | 売上情報が見つかりません | `not_found:order_financial` |
| backend/app/routers/order_financials.py:282 | DELETE /orders/{order_id}/financial | 売上情報が見つかりません | `not_found:order_financial` |
| backend/app/routers/order_purchase_details.py:112 | (関数 _ensure_order_exists) | 注文が見つかりません | `not_found:order` |
| backend/app/routers/order_purchase_details.py:211 | GET /orders/{order_id}/purchase | 仕入情報が見つかりません | `not_found:order_purchase` |
| backend/app/routers/order_purchase_details.py:233 | PATCH /orders/{order_id}/purchase | 仕入情報が見つかりません | `not_found:order_purchase` |
| backend/app/routers/order_purchase_details.py:293 | DELETE /orders/{order_id}/purchase | 仕入情報が見つかりません | `not_found:order_purchase` |
| backend/app/routers/order_purchase_details.py:335 | PATCH /orders/{order_id}/purchase/status | 仕入情報が見つかりません | `not_found:order_purchase` |
| backend/app/routers/order_shipping_details.py:82 | (関数 _ensure_order_exists) | 注文が見つかりません | `not_found:order` |
| backend/app/routers/order_shipping_details.py:203 | GET /orders/{order_id}/shipping | 発送情報が見つかりません | `not_found:order_shipping` |
| backend/app/routers/order_shipping_details.py:225 | PATCH /orders/{order_id}/shipping | 発送情報が見つかりません | `not_found:order_shipping` |
| backend/app/routers/order_shipping_details.py:282 | DELETE /orders/{order_id}/shipping | 発送情報が見つかりません | `not_found:order_shipping` |
| backend/app/routers/order_shipping_details.py:365 | GET /orders/{order_id}/shipping/elogi-csv | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:355 | GET /orders/{order_id} | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:376 | GET /orders/{order_id}/items | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:402 | POST /orders/{order_id}/items | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:537 | PATCH /orders/{order_id} | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:593 | PATCH /orders/{order_id}/paid | 注文が見つかりません | `not_found:order` |
| backend/app/routers/orders.py:638 | DELETE /orders/{order_id} | 注文が見つかりません | `not_found:order` |
| backend/app/routers/own_inventory.py:165 | GET /own-inventory/{own_inventory_id} | 自社在庫が見つかりません | `not_found:own_inventory` |
| backend/app/routers/own_inventory.py:193 | PATCH /own-inventory/{own_inventory_id} | 自社在庫が見つかりません | `not_found:own_inventory` |
| backend/app/routers/payment_fee_settings.py:156 | PATCH /payment-fee-settings/{setting_id} | 決済手数料設定が見つかりません | `not_found:payment_fee_setting` |
| backend/app/routers/payment_fee_settings.py:181 | DELETE /payment-fee-settings/{setting_id} | 決済手数料設定が見つかりません | `not_found:payment_fee_setting` |
| backend/app/routers/product_categories.py:320 | PATCH /product-categories/{category_id} | 商品カテゴリが見つかりません | `not_found:product_category` |
| backend/app/routers/product_categories.py:345 | DELETE /product-categories/{category_id} | 商品カテゴリが見つかりません | `not_found:product_category` |
| backend/app/routers/product_masters.py:138 | PATCH /super-admin/product-masters/{master_id} | マスタが見つかりません | `not_found:product_master` |
| backend/app/routers/product_masters.py:157 | DELETE /super-admin/product-masters/{master_id} | マスタが見つかりません | `not_found:product_master` |
| backend/app/routers/products.py:338 | GET /products/{product_id} | 商品が見つかりません | `not_found:product` |
| backend/app/routers/products.py:460 | PATCH /products/{product_id} | 商品が見つかりません | `not_found:product` |
| backend/app/routers/products.py:663 | DELETE /products/{product_id} | 商品が見つかりません | `not_found:product` |
| backend/app/routers/products.py:763 | GET /products/{product_id}/check-inventory | 商品が見つかりません | `not_found:product` |
| backend/app/routers/purchase_orders.py:84 | (関数 _resolve_tenant_supplier_id) | 指定された仕入先が見つかりません | `not_found:supplier` |
| backend/app/routers/purchase_orders.py:155 | GET /purchase-orders/{po_id} | 仕入注文が見つかりません | `not_found:purchase_order` |
| backend/app/routers/purchase_orders.py:197 | POST /purchase-orders | 指定された受注明細が見つかりません | `not_found:order_item` |
| backend/app/routers/quotes.py:140 | GET /quotes/{quote_id} | 見積もりが見つかりません | `not_found:quote` |
| backend/app/routers/quotes.py:165 | POST /quotes | 指定された会社が見つかりません | `not_found:company` |
| backend/app/routers/quotes.py:175 | POST /quotes | 指定された担当者が見つかりません | `not_found:contact` |
| backend/app/routers/quotes.py:280 | PATCH /quotes/{quote_id} | 見積もりが見つかりません | `not_found:quote` |
| backend/app/routers/quotes.py:414 | DELETE /quotes/{quote_id} | 見積もりが見つかりません | `not_found:quote` |
| backend/app/routers/roles.py:277 | PATCH /roles/{role_id} | ロールが見つかりません | `not_found:role` |
| backend/app/routers/roles.py:349 | DELETE /roles/{role_id} | ロールが見つかりません | `not_found:role` |
| backend/app/routers/roles.py:400 | GET /roles/{role_id}/permissions | ロールが見つかりません | `not_found:role` |
| backend/app/routers/roles.py:430 | PUT /roles/{role_id}/permissions | ロールが見つかりません | `not_found:role` |
| backend/app/routers/roles.py:517 | GET /users/{user_id}/roles | 指定されたユーザーが見つかりません | `not_found:user` |
| backend/app/routers/shifts.py:114 | DELETE /shifts/{shift_id} | シフトが見つかりません | `not_found:shift` |
| backend/app/routers/shipping.py:151 | DELETE /shipping/zones/{zone_id} | ゾーンが見つかりません | `not_found:shipping_zone` |
| backend/app/routers/shipping.py:253 | DELETE /shipping/rates/{rate_id} | 料金が見つかりません | `not_found:shipping_rate` |
| backend/app/routers/staff.py:205 | GET /staff/me | 現在のユーザに紐づく staff レコードが見つかりません | `not_found:my_staff_profile` |
| backend/app/routers/staff.py:290 | PATCH /staff/me/profile | 現在のユーザに紐づく staff レコードが見つかりません | `not_found:my_staff_profile` |
| backend/app/routers/staff.py:351 | (関数 _my_staff_id_and_token) | 現在のユーザに紐づく staff レコードが見つかりません | `not_found:my_staff_profile` |
| backend/app/routers/staff.py:497 | GET /staff/{staff_id} | スタッフが見つかりません | `not_found:staff` |
| backend/app/routers/staff.py:561 | PATCH /staff/{staff_id} | スタッフが見つかりません | `not_found:staff` |
| backend/app/routers/staff.py:646 | DELETE /staff/{staff_id} | スタッフが見つかりません | `not_found:staff` |
| backend/app/routers/staff_join.py:165 | (関数 _load_open_invite) | 招待が見つかりません | `not_found:staff_join_invite` |
| backend/app/routers/staff_reports.py:158 | POST /staff-reports/{report_id}/review | レポートが見つかりません | `not_found:staff_report` |
| backend/app/routers/status_master.py:207 | PATCH /status-master/{entry_id} | ステータスが見つかりません | `not_found:status` |
| backend/app/routers/status_master.py:232 | DELETE /status-master/{entry_id} | ステータスが見つかりません | `not_found:status` |
| backend/app/routers/super_admin_aliases.py:171 | PATCH /super-admin/aliases/{alias_id} | aliasが見つかりません | `not_found:alias` |
| backend/app/routers/super_admin_aliases.py:187 | DELETE /super-admin/aliases/{alias_id} | aliasが見つかりません | `not_found:alias` |
| backend/app/routers/super_admin_condition_defs.py:129 | PATCH /super-admin/condition-definitions/{def_id} | コンディション定義が見つかりません | `not_found:condition_definition` |
| backend/app/routers/super_admin_condition_defs.py:162 | DELETE /super-admin/condition-definitions/{def_id} | コンディション定義が見つかりません | `not_found:condition_definition` |
| backend/app/routers/super_admin_condition_defs.py:182 | GET /super-admin/condition-definitions/{def_id}/links | コンディション定義が見つかりません | `not_found:condition_definition` |
| backend/app/routers/super_admin_conditions.py:265 | PATCH /super-admin/conditions/{condition_id} | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/super_admin_conditions.py:289 | DELETE /super-admin/conditions/{condition_id} | 状態が見つかりません | `not_found:condition` |
| backend/app/routers/super_admin_conditions.py:507 | DELETE /super-admin/conditions/aliases/{alias_id} | 別名が見つかりません | `not_found:alias` |
| backend/app/routers/super_admin_dex.py:153 | PATCH /super-admin/dex/{dex_kind}/{entry_id} | 図鑑エントリが見つかりません | `not_found:dex_entry` |
| backend/app/routers/super_admin_dex.py:173 | DELETE /super-admin/dex/{dex_kind}/{entry_id} | 図鑑エントリが見つかりません | `not_found:dex_entry` |
| backend/app/routers/super_admin_knowledge.py:158 | PATCH /super-admin/knowledge/{rule_id} | ルールが見つかりません | `not_found:knowledge_rule` |
| backend/app/routers/super_admin_knowledge.py:174 | DELETE /super-admin/knowledge/{rule_id} | ルールが見つかりません | `not_found:knowledge_rule` |
| backend/app/routers/super_admin_note_master.py:222 | PATCH /super-admin/note-master/{note_id} | 備考マスタが見つかりません | `not_found:note_master` |
| backend/app/routers/super_admin_note_master.py:244 | DELETE /super-admin/note-master/{note_id} | 備考マスタが見つかりません | `not_found:note_master` |
| backend/app/routers/super_admin_payment_fee_settings.py:146 | PATCH /super-admin/payment-fee-settings/{setting_id} | 決済手数料設定が見つかりません | `not_found:payment_fee_setting` |
| backend/app/routers/super_admin_payment_fee_settings.py:168 | DELETE /super-admin/payment-fee-settings/{setting_id} | 決済手数料設定が見つかりません | `not_found:payment_fee_setting` |
| backend/app/routers/super_admin_product_categories.py:318 | PATCH /super-admin/product-categories/{category_id} | 商品カテゴリが見つかりません | `not_found:product_category` |
| backend/app/routers/super_admin_product_categories.py:341 | DELETE /super-admin/product-categories/{category_id} | 商品カテゴリが見つかりません | `not_found:product_category` |
| backend/app/routers/super_admin_product_formats.py:141 | PATCH /super-admin/product-formats/{format_id} | フォーマットが見つかりません | `not_found:product_format` |
| backend/app/routers/super_admin_product_formats.py:164 | PUT /super-admin/product-formats/{format_id}/games | フォーマットが見つかりません | `not_found:product_format` |
| backend/app/routers/super_admin_product_formats.py:234 | DELETE /super-admin/product-formats/{format_id} | フォーマットが見つかりません | `not_found:product_format` |
| backend/app/routers/super_admin_product_kinds.py:123 | PATCH /super-admin/product-kinds/{kind_id} | 大分類が見つかりません | `not_found:product_kind` |
| backend/app/routers/super_admin_product_kinds.py:156 | DELETE /super-admin/product-kinds/{kind_id} | 大分類が見つかりません | `not_found:product_kind` |
| backend/app/routers/super_admin_product_lines.py:123 | PATCH /super-admin/product-lines/{line_id} | 小分類が見つかりません | `not_found:product_line` |
| backend/app/routers/super_admin_product_lines.py:166 | DELETE /super-admin/product-lines/{line_id} | 小分類が見つかりません | `not_found:product_line` |
| backend/app/routers/super_admin_quantity_units.py:140 | PATCH /super-admin/quantity-units/{unit_id} | 数量単位が見つかりません | `not_found:quantity_unit` |
| backend/app/routers/super_admin_quantity_units.py:186 | DELETE /super-admin/quantity-units/{unit_id} | 数量単位が見つかりません | `not_found:quantity_unit` |
| backend/app/routers/super_admin_quantity_units.py:206 | GET /super-admin/quantity-units/{unit_id}/links | 数量単位が見つかりません | `not_found:quantity_unit` |
| backend/app/routers/super_admin_status_master.py:249 | PATCH /super-admin/status-master/{entry_id} | ステータスが見つかりません | `not_found:status` |
| backend/app/routers/super_admin_status_master.py:272 | DELETE /super-admin/status-master/{entry_id} | ステータスが見つかりません | `not_found:status` |
| backend/app/routers/super_admin_suppliers.py:220 | PATCH /super-admin/suppliers/{supplier_id} | 仕入元が見つかりません | `not_found:supplier_master` |
| backend/app/routers/super_admin_suppliers.py:245 | DELETE /super-admin/suppliers/{supplier_id} | 仕入元が見つかりません | `not_found:supplier_master` |
| backend/app/routers/super_admin_suppliers.py:624 | DELETE /super-admin/suppliers/discord-routing/{routing_id} | routing が見つかりません | `not_found:discord_routing` |
| backend/app/routers/super_admin_suppliers.py:731 | GET /super-admin/suppliers/{supplier_id}/extraction-rules | 仕入元が見つかりません | `not_found:supplier_master` |
| backend/app/routers/super_admin_suppliers.py:802 | PATCH /super-admin/suppliers/{supplier_id}/extraction-rules | 仕入元が見つかりません | `not_found:supplier_master` |
| backend/app/routers/super_admin_suppliers.py:971 | POST /super-admin/suppliers/{supplier_id}/knowledge-links | 仕入元が見つかりません | `not_found:supplier_master` |
| backend/app/routers/super_admin_suppliers.py:1025 | DELETE /super-admin/suppliers/{supplier_id}/knowledge-links/{link_id} | リンクが見つかりません | `not_found:knowledge_link` |
| backend/app/routers/super_admin_tcg.py:130 | PATCH /super-admin/tcg/series/{series_id} | シリーズが見つかりません | `not_found:tcg_series` |
| backend/app/routers/super_admin_tcg.py:146 | DELETE /super-admin/tcg/series/{series_id} | シリーズが見つかりません | `not_found:tcg_series` |
| backend/app/routers/super_admin_tcg.py:231 | PATCH /super-admin/tcg/types/{type_id} | 種別が見つかりません | `not_found:tcg_type` |
| backend/app/routers/super_admin_tcg.py:250 | DELETE /super-admin/tcg/types/{type_id} | 種別が見つかりません | `not_found:tcg_type` |
| backend/app/routers/super_admin_tenants.py:61 | DELETE /super-admin/tenants/{tenant_id} | テナントが見つかりません | `not_found:tenant` |
| backend/app/routers/super_admin_tenants.py:124 | DELETE /super-admin/tenants/{tenant_id}/physical | テナントが見つかりません | `not_found:tenant` |
| backend/app/routers/super_admin_units.py:203 | PATCH /super-admin/units/{unit_id} | 単位が見つかりません | `not_found:unit` |
| backend/app/routers/super_admin_units.py:226 | DELETE /super-admin/units/{unit_id} | 単位が見つかりません | `not_found:unit` |
| backend/app/routers/super_admin_units.py:300 | DELETE /super-admin/units/aliases/{alias_id} | 別名が見つかりません | `not_found:alias` |
| backend/app/routers/super_admin_weight_classes.py:123 | PATCH /super-admin/weight-classes/{class_id} | 重量クラスが見つかりません | `not_found:weight_class` |
| backend/app/routers/super_admin_weight_classes.py:156 | DELETE /super-admin/weight-classes/{class_id} | 重量クラスが見つかりません | `not_found:weight_class` |
| backend/app/routers/suppliers.py:256 | GET /suppliers/{supplier_id} | 仕入先が見つかりません | `not_found:supplier` |
| backend/app/routers/suppliers.py:299 | PATCH /suppliers/{supplier_id} | 仕入先が見つかりません | `not_found:supplier` |
| backend/app/routers/suppliers.py:330 | DELETE /suppliers/{supplier_id} | 仕入先が見つかりません | `not_found:supplier` |
| backend/app/routers/tcg_distribution.py:124 | GET /tcg/distribution/targets/{target_id} | 配信先が見つかりません | `not_found:distribution_target` |
| backend/app/routers/tcg_distribution.py:147 | PUT /tcg/distribution/targets/{target_id} | 配信先が見つかりません | `not_found:distribution_target` |
| backend/app/routers/tcg_distribution.py:162 | DELETE /tcg/distribution/targets/{target_id} | 配信先が見つかりません | `not_found:distribution_target` |
| backend/app/routers/tcg_line_import.py:371 | GET /tcg/line-import/{import_job_id} | import_job が見つかりません | `not_found:line_import_job` |
| backend/app/routers/tcg_line_import.py:443 | (関数 _resolve_supplier_impl) | import_job が見つかりません | `not_found:line_import_job` |
| backend/app/routers/tcg_line_import.py:603 | POST /tcg/line-import/{import_job_id}/commit | import_job が見つかりません | `not_found:line_import_job` |
| backend/app/routers/teams.py:93 | GET /teams/{team_id} | チームが見つかりません | `not_found:team` |
| backend/app/routers/teams.py:159 | PATCH /teams/{team_id} | チームが見つかりません | `not_found:team` |
| backend/app/routers/teams.py:208 | DELETE /teams/{team_id} | チームが見つかりません | `not_found:team` |
| backend/app/routers/teams.py:234 | GET /teams/{team_id}/members | チームが見つかりません | `not_found:team` |
| backend/app/routers/teams.py:266 | POST /teams/{team_id}/members | チームが見つかりません | `not_found:team` |
| backend/app/routers/teams.py:328 | DELETE /teams/{team_id}/members/{user_id} | メンバーが見つかりません | `not_found:team_member` |
| backend/app/routers/units.py:177 | PATCH /units/{unit_id} | 単位が見つかりません | `not_found:unit` |
| backend/app/routers/units.py:202 | DELETE /units/{unit_id} | 単位が見つかりません | `not_found:unit` |
