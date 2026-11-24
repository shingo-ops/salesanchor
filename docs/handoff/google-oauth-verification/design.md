# design: Google カレンダー連携の審査に出すまでの手順書（草案）

- 状態: **草案**（設計案作成済み・PO 承認前）。実装・Google の画面での保存・提出は、この手順書の PO 承認の後。
- 根拠: `docs/handoff/google-oauth-verification/recon.md`（以下 recon）
- 関連 ADR: ADR-1057・ADR-1059・ADR-1060・ADR-1081（予定の連携の作り）、ADR-1085（Chrome の操作の区分と同意票）、ADR-027（i18n・画面の文を足す場合）

## 1. 目的（KGI）

予定の画面の Google 連携で、お客さんに「このアプリは Google で確認されていません」の警告が出ないようにする。100 人の上限も外す。

| 基準 | 検証方法 |
|---|---|
| K1 検証センターの「データアクセス」の状態が、確認済み（審査合格）と表示される | PO か Opus が `/auth/verification?project=sales-ops-with-claude` を開いて目視（○×） |
| K2 連携したことの無い Google アカウントで予定の画面から連携すると、警告の画面が出ずに同意の画面になる | PO が別のアカウントで1回連携して目視（○×） |
| K3 個人情報のページに Google カレンダーのデータの扱いの節があり、Google の決まりの5点（取得・使用・保存・共有・削除）がそれぞれ1文以上ある | `https://salesanchor.jp/privacy` を開き、5点を表で数える（5/5） |
| K4 審査の後も、今の6人の連携と予定の同期が止まらない | 審査の前後で、予定の画面の「連携中」表示と、アプリで作った予定が Google に出ることを1件ずつ目視 |

## 2. 今の状態（recon の要約）

- 連携の札は Google の箱 `sales-ops-with-claude` にある。一般公開・外部・6人/上限100（recon §1）。
- アプリはカレンダーの全権 `auth/calendar` を求める（recon §2）。ところが管理画面のデータアクセスには登録されていない。だから管理画面は「審査は不要」と出るが、利用者には警告が出る（recon §1）。
- 個人情報のページにカレンダーの記載が無い（recon §3）。
- 連携を外しても Google 側の許可は取り消さず、取り込んだ予定も残る（recon §2）。

## 3. 手順（順番に意味がある）

| 順 | やること | 誰が | Google 側・本番への効き方 | 区分（ADR-1085） |
|---|---|---|---|---|
| 1 | 権限を狭められるか決める: `calendar` のままか、`calendar.events.owned`＋`calendar.calendars.readonly` に狭めるか（書類の照合は recon §4-2 で全9操作○。実物の試し recon §4-3 で色ラベル読み取り・作成（Meet 付き）・変更・削除が動いた） | Opus が確かめた → PO が決めた（2026-11-25「1」= 狭める。§3-1） | コードの変更が1便要る。今の6人はつなぎ直し不要の設計（§3-1） | — |
| 2 | Search Console で `salesanchor.jp` の所有権を確かめる（済んでいなければ DNS に確認の文字を足す） | 確認は Opus（読むだけ）。DNS の保存は同意票＋PO の「1」 | DNS に TXT が1行増える。サイトの表示は変わらない | 読む=1・保存=2 |
| 3 | 個人情報のページに「Google カレンダーのデータ」の節を足す（英語。§4 の文案） | Opus が設計 → クラウドの Sonnet が `lp/src/pages/privacy.astro` を直す → PR | 会社のサイトの文が増える。§12.1 の約束で、大きな改定は 14 日前に知らせる | — |
| 4 | 連携を外したときの扱いを決める（Google の許可の取り消しと、取り込んだ予定を消すか残すか）。ページに書く内容と実際の動きをそろえる | PO が決める → 必要ならコードの便 | 決め方しだい | — |
| 5 | デモ動画を撮る（英語の画面・同意の流れ・アドレスバーの利用者番号・予定の表示/作成/Meet/色/同期） | Opus が台本 → 撮影は PO（またはOpusが画面を操作し PO が録画） | なし | — |
| 6 | 動画を YouTube に「限定公開」で上げる | PO 本人（PO の YouTube アカウント） | 一般には一覧に出ない | 2（公開の操作） |
| 7 | データアクセスの画面に権限を登録する | Opus（同意票＋PO の「1」） | 審査中の見え方は recon §5 で未確認。3〜6 がそろってから行う | 2 |
| 8 | 理由の文・関連ドキュメント（3つまで）・動画の住所を入れて審査に出す | Opus（同意票＋PO の「1」） | Google に申請が届く | 2（申請・提出の送信） |
| 9 | Google からのメールに答える（最長 10 日） | PO の会社アドレスに届く → Opus が答えの下書き → PO が送る | — | — |
| 10 | K1〜K4 を確かめる | PO と Opus | — | 1 |

順番の理由: 7 を先に行うと、審査に出すまで「機密の権限が未審査」の状態がどう見えるか分からない（recon §5）。3〜6 をそろえてから 7・8 を同じ日に行う。

## 3-1. 手順1の決定と、狭める便の設計（PO 2026-11-25「1」= 狭い2つに変える）

PO の決定: アプリが求める許可を `calendar` から `calendar.events.owned`＋`calendar.calendars.readonly` に狭める。以下は Opus の設計案（設計審査前）。

### 変更前と変更後（触るファイルの全部は実装カード `docs/handoff/google-oauth-verification/card-narrow-scope.md`。受け取り口と画面の文も変える）

| 場所（origin/main） | 変更前 | 変更後 | 理由 |
|---|---|---|---|
| `backend/app/services/google_calendar.py:42` | `_SCOPES = ["https://www.googleapis.com/auth/calendar"]` | `_SCOPES = ["https://www.googleapis.com/auth/calendar.events.owned", "https://www.googleapis.com/auth/calendar.calendars.readonly"]` | 新しくつなぐ人の同意の画面に出る許可を狭める（同意の URL と、合鍵の受け取りで使う） |
| `backend/app/services/google_calendar.py:227-239`（`scopes` は `:237`） `_build_credentials` | `scopes=_SCOPES` | `scopes=None` | 下の「今の6人」を参照 |
| `backend/app/services/google_calendar.py` `exchange_code` の `fetch_token` の後 | 受け取った許可を確かめない | 受け取った許可に2つが両方あるかを確かめ、欠けていれば「両方にチェックを入れて連携し直す」ことを伝える失敗にする | 許可が2つになると、Google の同意の画面で利用者が片方だけ外せる。外すと予定の作成か色ラベルの読み取りが後で失敗する |

触らない範囲: `backend/app/services/google_drive_oauth.py`（`drive.file` は機密の許可ではない）・予定の読み書きの処理・DB。画面は、片方だけ許可されたときの知らせの文を1つ足すだけ（今の知らせの帯を使う）。

### 今つないでいる6人（つなぎ直しは不要の設計）

- 【事実】合鍵の更新のとき、部品は `Credentials` に渡した `scopes` をそのまま Google に送る（Context7 `/googleapis/google-auth-library-python` の credentials.py の `refresh`）。
- 【事実】部品の更新の依頼は、`scopes` が空のときは許可の範囲を送らない（google/oauth2/_client.py の `refresh_grant` の `if scopes:`。出典: [googleapis/google-auth-library-python _client.py](https://www.github.com/googleapis/google-auth-library-python/blob/82293fe2caaf5258babb5df1cff0a5ddc9e44b38/google/oauth2/_client.py)）。
- 設計: `_build_credentials` で `scopes=None` にする。こうすると、今の6人は前に許した全部の許可のまま合鍵が更新され続ける。新しくつなぐ人とつなぎ直した人だけが狭い2つになる。
- 【未確認】`scopes=_SCOPES`（狭い2つ）のまま全部の許可の合鍵を更新したとき、Google が受け付けるか。`scopes=None` にすればこの問いに頼らずに済むので、試さない。

- 【事実】Google の公開の API 定義（`https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest`、2026-11-25 取得）で、`events` の watch・list・get・insert・patch・delete・instances と `channels.stop` は `calendar.events.owned` を、`calendars.get` は `calendar.calendars.readonly` を受け付ける。
- 【事実】本番の予定を入れる先は、2社とも `primary`（本人のカレンダー）だった（読むだけの鍵で `tenant_google_calendar_config` を読んだ。2026-11-25 01:45 JST、2行）。だから `events.owned`（本人が持つ予定だけ）で足りる。

### 実装カードの前に確かめること（未確認のまま実装しない）

- 【事実】`oauthlib` は、返ってきた許可の範囲が求めた範囲と違うとき、既定で `Warning`（"Scope has changed"）を出す。環境変数 `OAUTHLIB_RELAX_TOKEN_SCOPE` を立てると出さない。例外には `token` が付く（oauthlib 1.0.0 の変更記録。出典: [oauthlib 0.7.0 の変更](https://newreleases.io/project/github/oauthlib/oauthlib/release/0.7.0)・[oauthlib issue 809](https://github-redirect.dependabot.com/oauthlib/oauthlib/issues/809)）。Context7 の `requests-oauthlib` の資料には、この動きの記載が無かった。
- 【事実】今のコードは `fetch_token` の例外をすべて `RuntimeError("Google token 交換に失敗: …")` にする（`backend/app/services/google_calendar.py` の `exchange_code`）。だから片方だけの許可のときは、今のままでも連携は保存されない。ただし利用者には理由が分からない。
- 設計: 環境変数は立てない（アプリ全体に効くため）。`exchange_code` で "Scope has changed" の `Warning` だけを分けて受け、「両方にチェックを入れて連携し直してください」に当たる失敗にする。
- 【事実】審査1回目（枝 release/google-calendar-narrow-scope-review1 の review-architect-narrow-1.md §3）で、oauthlib 3.2.2・3.3.1・4.0.1 の実物を動かした。片方だけなら `Warning` が出て `token` が付く。2つ（順不同とも）なら出ない。ただし `Flow.fetch_token` 経由では `token["scope"]` がリストになる。受け取った範囲の読み方は実装カードの変更3に書いた。
- 失敗の文は画面の言葉の決まり（ADR-027・ADR-1071「起きたこと＋次にすること」）に合わせる。今の失敗の文の出し方（`backend/app/routers/google_calendar.py` の受け取り口）を読んでから決める。

### 受け入れの基準（この便）

| 基準 | 検証方法 |
|---|---|
| S1 同意の URL の `scope` が狭い2つだけ | 試験で `get_auth_url` の URL を分解して2つを数える（○×） |
| S2 合鍵の更新で `scopes` を送らない | 試験で `_build_credentials` が `scopes=None` で `Credentials` を作ることを確かめる（○×） |
| S3 片方だけ許可されたら、連携を保存せず次にすることを伝える | 試験で片方だけの答えを作って確かめる（○×） |
| S4 今の6人の予定の同期が、本番反映の後も止まらない | 反映の後 24 時間以内に、同期の失敗と変更の通知の登録（webhook）の失敗の記録が増えていないことと、PO のアカウントの「連携中」表示を確かめる |

## 4. 個人情報のページに足す節の文案（PO 承認前の草案）

`4. Meta Platform Integration` の後に新しい節を足す（番号の振り直しは実装カードで決める）。書く内容:

- What we access: 接続した人の Google カレンダーの予定（題名・日時・場所・説明・色・Meet の URL）と、カレンダーの色ラベルの設定。
- How we use it: アプリの予定の画面に表示し、アプリで作った・直した予定を Google カレンダーにそろえるためだけに使う。
- Storage: 取り込んだ予定はアプリの予定の表に保存する（日本のさくらの VPS）。合鍵（トークン）は暗号化して保存する。
- Sharing: 取り込んだ予定は最初は本人だけに見える。本人が選んだ予定だけ同じ会社の社員に見える。第三者に売らない・広告に使わない・AI の学習に使わない・AI（Gemini）に渡さない。
- Deletion: 手順4で決めた動きを書く。
- Limited Use の宣言: 「Sales Anchor's use and transfer of information received from Google APIs will adhere to the Google API Services User Data Policy, including the Limited Use requirements.」に当たる1文（文は Google の公式の文面を実装カードの前に確かめて写す）。

## 5. 代わりの案と選んだ理由

| 案 | 中身 | 選ばない/選ぶ理由 |
|---|---|---|
| A 審査に出す（本書） | 上の手順 | 100 人の上限と警告を外せる唯一の道（recon §4） |
| B 未審査のまま使う | 今のまま | 知っている少人数なら例外（recon §4）。お客さんが増えると上限100と警告が残る |
| C 社内専用にする | ユーザーの種類を内部へ | お客さんの会社のアカウントが使えなくなるので、目的に合わない |

## 6. 危ないところと対処

| 危ないところ | 対処 |
|---|---|
| 権限の登録だけ先に行い、審査中に何かが変わる | 手順7と8を同じ日に、3〜6 の後で行う |
| ページの文と実際の動き（連携を外したとき）が違う | 手順4で先に決め、文をそれに合わせる |
| 権限を狭めて機能が壊れる | 手順1を試験用の箱で確かめてから。狭めない選択も残す |
| 審査に落ちる | Google からのメールに答えて出し直す。今の連携はそのまま動く（未審査の今と同じ） |

## 7. 維持の仕組み

- K1〜K4 は §1 の表のとおり。
- 守り手: Opus（設計担当）。許可の範囲は backend/tests/test_google_calendar.py の S1 の試験が狭い2つ以外を求めたら落とす。
- 維持: 新しい Google の権限を足すときは、データアクセスの登録と個人情報のページの更新を同じ便に入れる。審査の状態は検証センターで年1回以上 Opus が読む（毎週の点検に足すかは便の中で決める）。

## 8. 外部・過去事例の参照と我々への応用

- 個別の会社の事例は使わない。理由: Google の公式の手順（recon §4）が審査の条件そのものであり、他社の通過事例は条件の証明にならない。

## 9. PO に決めてもらうこと（この草案の承認の後、1件ずつ）

1. 手順1: 権限を狭めるか → 決定済み（2026-11-25「1」= 狭める）。
2. 手順4: 連携を外したとき、取り込んだ予定を消すか残すか。
3. 手順5・6: 動画の撮影と YouTube への公開を誰がどう行うか。
