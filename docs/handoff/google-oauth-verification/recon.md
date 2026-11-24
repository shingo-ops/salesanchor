# recon: Google カレンダー連携の審査（機密スコープの確認）準備

- 日付: 2026-11-24（JST）
- 調べた人: Claude Opus（設計担当）。Google の管理画面は Claude in Chrome で読むだけ（押す・打つ操作は 0 回。ADR-1085 区分1のみ）
- 基準: `origin/main` 9019d83e8

## 0. 既存 ADR・文書の検索

- `git grep -il calendar origin/main -- docs/adr` → ADR-1057（会社で1接続・本人の予定だけ）、ADR-1059（Google の予定の取り込み・最初は自分だけ）、ADR-1060（Google Meet）、ADR-1075（繰り返し）、ADR-1081（予定の色ラベル）ほか。Google の審査そのものを扱う ADR は 0 件。
- `docs/handoff/` に審査の文書は 0 件（`git grep -il "確認されていません\|未確認のアプリ" origin/main -- docs` は審査の設計に当たらない）。
- 経緯の覚え書き: PO 2026-11-05「設定が完了した後に審査に出す準備は進める、次便で」（自動メモリ google_oauth_verification）。

## 1. Google の管理画面の今の状態（Chrome で読んだ事実）

| 項目 | 観測した値 | 読んだ画面 |
|---|---|---|
| 連携の札がある箱 | `sales-ops-with-claude`（番号 730863365967）の札 `salesanchor-calendar`（2026/05/25 作成・ウェブ アプリケーション） | `/auth/clients?project=730863365967`。番号は `.env.example:72` の利用者番号の頭と一致 |
| 公開状態 | 本番環境・ユーザーの種類は外部 | `/auth/audience` |
| 利用者数 | 「6 人のユーザー / ユーザー数の上限 100」 | `/auth/audience` |
| ブランディング | 「ブランディングは検証済みで、ユーザーに表示されています」。アプリ名 Sales Anchor・ホーム `https://salesanchor.jp`・プライバシー `https://salesanchor.jp/privacy`・規約 `https://salesanchor.jp/terms`・サポートメールと連絡先は PO の会社アドレス | `/auth/branding`・`/auth/verification` |
| データアクセスに登録済みの権限 | 機密でない権限 `.../auth/drive.file` の1つだけ。機密・制限付きは「表示する行がありません」 | `/auth/scopes` |
| 検証センター | 「アプリは機密性の高いスコープや制限付きスコープをリクエストしていないため、検証は必要ありません」 | `/auth/verification` |
| 概要の診断 | ドメインの所有権の確認・請求先・連絡先・安全なフロー・クライアントの使用状況はすべて合格の表示。「アプリが Google によって検証されました」 | `/auth/overview` |
| Search Console | PO のアカウントで開くと「ようこそ」画面（「ウェブサイトを追加」）が出た。登録済みのサイトの一覧は出なかった | `search.google.com/search-console/welcome` |

## 2. アプリが求めている権限と使い方（コードの事実）

- 求める権限: `backend/app/services/google_calendar.py:42` `_SCOPES = ["https://www.googleapis.com/auth/calendar"]`（全権）。ドライブは `backend/app/services/google_drive_oauth.py:49` `drive.file`。
- 呼んでいる Google の操作（`backend/app/services/google_calendar.py`）:
  - `events().list`（:361）・`events().get`（:385）・`events().insert`（:462、Meet は `conferenceDataVersion=1` :458）・`events().patch`（:484）・`events().delete`（:496）
  - `calendars().get`（:400）で `labelProperties.eventLabels`（予定の色ラベル・ADR-1081）を読む
- `backend/app/services/google_webhook.py`: `events().watch`（:98）・`channels().stop`（:145・:183）・`events().list`（:310 差分の取り込み）
- 取り込んだ予定はアプリの予定の表 `calendar_events` に保存（ADR-1059:16）。保存先はさくらの VPS（日本）。最初は「自分だけ」、持ち主が選んだときだけ社員に見せる（ADR-1059:17〜19）。
- 秘書のチャット（ADR-1056:16・ADR-1078:24）は AI（Gemini）に Google の予定のデータを渡さない。渡すのは利用者が書いた文・今の日時・会話中の予定の日時だけ。
- 連携を外す口 `backend/app/routers/google_calendar.py:219`〜`:231` は `tenant_google_calendar_config` の行を消すだけ。Google 側の許可の取り消し（revoke）は呼ばない（`backend/app/routers/google_calendar.py`・`backend/app/routers/integrations.py`・`backend/app/services/google_calendar.py`・`backend/app/services/calendar_service.py` を `revoke` で検索して 0 件）。取り込み済みの `calendar_events` の行も消さない。

## 3. 会社のサイトの個人情報のページ（事実）

- `https://salesanchor.jp/privacy`（`lp/src/pages/privacy.astro`）Version 1.8・Last Updated November 8, 2026。
- Google については「Authentication (Google Identity Platform)」「Gemini API」「Google Drive（請求書の保管）」の3つだけ（§7.2）。**Google カレンダーのデータの取得・使い方・保存・共有・削除の記載は 0 件**。
- §12.1: 大きな改定は 14 日以上前に知らせる約束がある。

## 4. Google の公式の決まり（2026-11-24 に Chrome で読んだ）

出典: developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification（日本語版）、developers.google.com/terms/api-services-user-data-policy（最終更新 2020-09-03）、developers.google.com/workspace/calendar/api/auth。

- 機密性の高い権限の例として「Google カレンダーに保存されている予定の読み取り」が挙がっている。審査は最長 10 日。
- アプリが使う権限はすべてデータアクセスの画面で宣言する。
- 準備: Search Console で承認済みドメインの所有権を確かめる（プロジェクトのオーナーか編集者のアカウントで）。
- プライバシー ポリシーはホームと同じドメインに置き、**Google ユーザーデータへのアクセス・使用・保存・共有の仕組みを開示**する。
- 権限ごとの理由（もっと狭い権限で足りない理由）を書く。
- デモ動画: YouTube に「限定公開」で上げる。同意の流れを英語で見せる。同意画面のアプリ名、アドレスバーの OAuth クライアント ID、権限ごとの機能を見せる。
- 関連ドキュメントへのリンクを 3 つまで。
- 求める権限は機能に必要な最小に限る。読むだけのアプリが書く権限を求めてはいけない。
- 未審査でも、知っている少人数の利用は例外。ユーザー数の上限（このアプリは 100）がかかる。

## 4-2. 手順1（権限を狭められるか）の公式の照合（2026-11-24 Chrome で読んだ）

アプリが呼ぶ Google の操作は `backend/app/services/google_calendar.py` と `backend/app/services/google_webhook.py` の9種だけ（`grep -rnoE "\.(events|calendars|calendarList|colors|settings|freebusy|acl|channels)\(\)\.[a-zA-Z]+\(" backend/app` と複数行の呼び出し :361・:527 を合わせて数えた）。各操作の公式ページ（developers.google.com/workspace/calendar/api/v3/reference/…?hl=en）の「Authorization」欄で、狭い権限が載っているかを照らした。

| 操作 | `calendar.events.owned` が載っているか | `calendar.calendars.readonly` が載っているか |
|---|---|---|
| events.list | ○ | — |
| events.get | ○ | — |
| events.insert（Meet 付き） | ○ | — |
| events.patch | ○ | — |
| events.delete | ○ | — |
| events.instances | ○ | — |
| events.watch | ○ | — |
| calendars.get（色ラベル） | × | ○ |
| channels.stop | 権限の欄なし | 権限の欄なし |

- 使うカレンダー: `backend/app/services/google_calendar.py:335`〜`:346` の `get_calendar_id` は設定が無ければ `primary`（本人の主カレンダー）。アプリの中で `calendar_id` を書く文は 0 件（`tenant_google_calendar_config` への INSERT/UPDATE 3か所 `backend/app/routers/google_calendar.py:130`・`backend/app/routers/calendar.py:685`・`backend/app/services/google_calendar.py:284` はどれも `calendar_id` を書かない）。
- 公式の意味（developers.google.com/workspace/calendar/api/auth）: `calendar.events.owned` は「自分が持ち主の Google カレンダーの予定を見る・作る・変える・消す」。`calendar.calendars.readonly` は「カレンダーの題名・説明・時間帯などの設定を見る」。
- 書類の上での結論: `calendar.events.owned` と `calendar.calendars.readonly` の2つで、9種すべてが許可の欄に載る。

### 4-3. 実物の試し（2026-11-24・PO の主カレンダー・Google の練習用ページ OAuth 2.0 Playground の札）

アプリの札ではなく Playground の札（利用者番号の頭 407408718192）で試した。権限の効き方は札によらず権限ごとに決まるため、権限の試しとして使う。合鍵の値は画面にも記録にも出していない。

| 試し | 結果 |
|---|---|
| 1回目の同意（アカウントを選ぶ画面を長く開いたまま） | 同意の画面で `Error 400 (Bad Request)`。原因は未確認（受付の期限切れか）。何も許可されていない |
| 2回目の同意（開き直してすぐ） | 同意できた。戻りの住所の `scope=` に `calendar.calendars.readonly` と `calendar.events.owned` の2つ |
| calendars.get（`GET /calendar/v3/calendars/primary`） | `HTTP/1.1 200 OK`。中身に `"labelProperties"` と `"eventLabels"` がある（予定の色ラベル・ADR-1081 の読み取りが狭い権限で動く） |
| events.insert（Meet 付き・`POST .../calendars/primary/events?conferenceDataVersion=1`・id `sacheck20261124a`・招待者なし） | `HTTP/1.1 200 OK`。返りに `"conferenceData"` と meet.google.com の会議の住所がある（住所の値は個人の予定のため記録しない） |
| events.patch の1回目 | 送り方の選択で PATCH を押し損ね、`POST .../events/sacheck20261124a` で送った。`HTTP/1.1 404 Not Found`。予定は変わっていない（権限の試しにならないため数えない） |
| events.patch の2回目（`PATCH .../events/sacheck20261124a`） | `HTTP/1.1 401 Unauthorized`・`"Invalid Credentials"`・`"authError"`。手順2の表示は「The access token will expire in seconds.」で残り秒数が空。権限ではなく合鍵（1時間で切れる）の期限の問題と読む（未確認）。予定は変わっていない |
| 合鍵の更新（手順2 Refresh access token） | `HTTP/1.1 200 OK`（合鍵の値は読んでいない） |
| events.patch の3回目（`PATCH .../events/sacheck20261124a`・本文 `{"summary":"...(patched)...","colorId":"5"}`） | `HTTP/1.1 200 OK`。返りの `"summary"` が `"Sales Anchor scope test (patched) - safe to delete"`、`"colorId"` が `"5"`。名前と色の変更が狭い権限で動く |

## 5. 未確認

- `calendar.events.owned` と `calendar.calendars.readonly` の組み合わせで、実際に今の全機能が動くか（§4-2 は書類の上での照合だけ。他人から招待された予定を本人の主カレンダーで直す・消すときの動きも未確認）。
- 今の6人の連携の合鍵は全権で同意を取ったもの。狭い権限に変えたとき、連携のやり直しが要るか。
- `calendar`（全権）と `calendar.events` のそれぞれの区分（機密か制限付きか）。Google の権限の画面には区分の表示が無かった。データアクセスの画面で追加したときに出る区分で確かめる。
- Search Console で salesanchor.jp の所有権を確認済みか（ようこそ画面が出ただけで、別のアカウントで登録済みの可能性は消せていない）。
- データアクセスの画面に `calendar` を登録した時点で、審査が終わるまで利用者の画面や今の6人の連携に何か変わるか。
