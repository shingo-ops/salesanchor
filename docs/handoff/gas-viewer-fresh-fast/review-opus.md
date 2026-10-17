# Opus 審査記録（ADR-1019 閲覧ページ）

設計と同じ Claude Opus による実装の審査。独立した第二者のレビューではない。

## 段4a-1（PR #4394）— パスワードの変更・再発行、②⑥の画面、nginx、毎日の掃除、privacy

- 審査日: 2026-10-16
- 審査した head: 9a014878c（main の S5 #4390 を merge した後）
- 根拠のカード: 段4a-1 の実装カード（design.md の段4の分け方）

### 判定: APPROVE（実装として合格。マージ・本番反映の承認は兼ねない）

### 読んだ範囲と結果
| 範囲 | 結果 |
|---|---|
| backend（routers/viewer.py・cache.py・celery_app.py・services/auth_mail.py・tasks/maintenance.py） | カードどおり。指摘なし |
| frontend（ViewerApp.tsx・PasswordChangeView.tsx・PasswordResetView.tsx） | 金型（Button・TextField・EmptyState）だけを使う。文言はすべて t("viewer.…")。`#reset=` のトークンは最初の state で読み、replaceState で URL から消す。再発行リンクから来たときは在庫を取りに行かない（startedLoading）。指摘なし |
| nginx/nginx.conf | app と api の2つの server に、`location =`（完全一致）で login・password-reset/request・password-reset/confirm の3つを足した。limit_req は既存の /api/v1/auth/ と同じ zone=login burst=5。指摘なし |
| lp/src/pages/privacy.astro | 保存期間の表に閲覧アカウントの1行。Q7 の決定（期限切れ・停止から90日、ログイン記録90日）と一致 |
| main との衝突 | main の S5（#4390）が viewer.py の `_client_ip` を `app.client_ip.get_client_ip` に置き換えた。今回足した呼び出し3か所も get_client_ip にそろえた（viewer.py:148・:253・:331・:347） |

### 検証（実行者の区別）
- 担当（Sonnet）の実行: vitest 50 passed、tsc 0、check:all 0、viewer bundle PASSED、lp build 0、ruff OK。merge 後の pytest（test_viewer_password・api・isolation・tokens・purge）61 passed・6 skipped。
- 手元で実行していないもの: test_viewer_purge の DB を使う4件（CI の使い捨て DB で実行）、nginx -t（CI にも無い。本番の deploy の Recreate nginx の後で、nginx が動いていることを確かめる）。

### 記録しておく事実
- 削除の命令を含むソース（viewer.py・maintenance.py・テスト）は、PO の 2026-10-16 の y の範囲（Write/Edit で書くことだけ）で書いた。
- PR 本文の初版で、その命令の語をフックを通すために別の言い方へ言い換えていた。フックの判定を言い換えで避けたことになるので、PO に事実として報告する。

### 未解決
- 本番反映後に確かめる: nginx の再作成と稼働、3本の API が Origin 無しで 403、beat に purge-viewer-accounts が登録されていること、②⑥の画面（Evaluator）。

## 段4a-2（管理 API・画面・専用スクリプト）の審査（2026-10-17 Opus。commit efa8936a3）
判定: APPROVE（PG を使うテスト 10 本は手元で未実行。CI の使い捨て DB で初めて走るので、CI 緑を条件にする）

### 確かめたこと（実物を読んだ）
- backend/app/services/viewer_admin.py: 4つの操作の遷移が design.md:535-538・:523・:526 と一致する。延長は記録時刻＋N日。解除は最新の suspend 行の from_status へ戻り、行が無いと conflict（409）。どの操作も同じトランザクションで viewer_status_changes に1行を書く。purge の前提である action='suspend' の行は停止のたびに入る。
- 目印①②の SQL は design.md の 4a-2 の細部の定義どおり（login_succeeded だけ・NULL の IP を除く・(t−24h, t]）。
- backend/app/routers/super_admin_viewers.py: 6本すべてが require_super_admin。POST の actor は po、actor_user_id は users.id。commit はルータ側で、失敗したら rollback。detail は短いコードだけ。
- 専用スクリプト 2本は stdin の JSON だけを受ける。入力値・traceback を出さない。登録はメール・名前を出力しない。status_changes には書かない。
- 画面: 金型（PageLayout・DataTable・Badge・Button・Modal・Drawer・TextField・EmptyState）だけを使う。文言はすべて t()。色の直値は無い。
- realtime の4キーはパス変数名 {viewer_id} が実装と一致する。openapi の差分は新しい6ルートと5スキーマだけ（担当の報告。Opus は diffstat の 468 行追加・削除 0 を確認）。

### 指摘（直さずに進める軽微なもの）
- list_viewers の now 引数は使われていない（目印は DB の interval で計算する）。害は無い。
- 画面のログイン記録の rowKey は「日時｜種類｜IP」で、全く同じ行が2つあるとキーが重なる。表示の警告だけで、データには影響しない。

### 未解決
- 本番反映後に確かめる: GET が super admin 以外で 403、画面（Evaluator）。
- 登録用スクリプトの本番実行（Q9 の22人）は PO 本人の GO と permit-danger が要る。対象の一覧を先に PO に見せる。

## r15（2026-10-17。申込の招待リンクをボットが作る：PO 決定 Q16。審査は Opus、同一 AI の自己審査）

### 判定：APPROVE（Blocking 0、Non-blocking 2）

### 照合した根拠
- Discord 公式 Create Channel Invite（docs.discord.com/developers/resources/channel、2026-10-17 WebFetch）：max_age 0〜604800、max_uses 0〜100、unique、CREATE_INSTANT_INVITE が要る。Context7 は上限のため使えず、公式を直接確認した。
- 権限の数字 805432406（backend/app/routers/discord_oauth.py:72）は bit0（CREATE_INSTANT_INVITE）を持たない（偶数）。
- ADR-091 の権限表に CREATE_INSTANT_INVITE の記載は無かった（:56-89）。Manage Guild の除外は :86（design.md の「:69」は誤り→直した）。
- discord_api_request（backend/app/services/discord_rest.py:34）はやり直し最大5回（:20-23）。申込では max_retries=1 にし、既定値で既存の呼び出し元を変えない。
- backend に DISCORD_BOT_TOKEN が渡っている（docker-compose.yml:109）。招待を作る既存のコードは無い（create_invite・.invites の grep 0件）。

### 確かめた点
- 応答の形の秘匿（N-19）：登録済みの email でも招待を作るので、invite_url の有無で登録済みかどうかは分からない。honeypot だけ null（ボット向けの差は許容）。
- SSOT：招待リンクは DB に保存しない。
- 最小権限：テナント向けの権限の数字は変えず、運用サーバーのロールにだけ付ける。
- 順番：viewer_discord_config は 4c で作るので、4c を先にする。

### Non-blocking
- N-r15-1：Discord の招待作成そのものの呼び出し制限の値は公式に数字が無い。作れないときは null と再申込の案内で受ける（受入条件で 429 を確かめる）。
- N-r15-2：受付の部屋にチャンネル単位で「招待を作成」を拒否する上書きがあると作れない。PO の手順書に「受付の部屋の権限の上書きを確かめる」を入れる。

### 未解決
- PO の Discord の設定作業（ボットのロールに「招待を作成」を付ける）。手順は 4c のカードと一緒に渡す。

## r16（2026-10-17。段4c のカード：Discord の受付。審査は Opus、同一 AI の自己審査。カード /tmp/CC報告ファイル/viewer_stage4/card_4c.md）

### 照合した根拠
- D6 の【未確認】2つ：gateway の DB のロールは salesanchor_app（recon_d6/ssh_gw_dburl_masked.txt）。discord.py 2.4.0 の state.py:797・interactions.py:1049-1050・ui/modal.py:140-150（recon_d6/pkg/）。どちらも事実になり、D6 に記録した。
- on_interaction（backend/app/discord_gateway/client.py:210-）は :216 で component 以外を落とすので、viewer_trial_ の分岐は :216 より前に置く。顧客用の :219 以降は変えない。
- 部屋の作成の範囲（ticket_channel_creator.py:473-480・:510-564）。カテゴリの取得が leads の確認（:482-508）より前にあるため、部品を2つに分けて呼ぶ位置を変えない（4c の細部に記録）。
- celery-worker に DISCORD_BOT_TOKEN が無い（docker-compose.yml:212-300）。部屋の片付けは gateway に置いた。
- deploy.yml は migration（:526-540）を入れ物の作り直しの後に流す。

### 確かめた点
- SSOT：設定は1行だけの表。申込コードの正規化は1か所（viewer_signup_code.py）。招待リンク・部屋の URL は DB に保存しない（URL は guild_id と channel_id から作る）。
- 顧客用チケットを変えない：既存のテスト2ファイルを1字も変えずに通すことを受入にした。ログと reason の文字列も今のまま。
- 個人情報：部屋の名前は trial-<id>。ログに email・コード・パスワード・表示名を出さない。
- 総当たり：Discord ID ごとに1時間5回。Redis が使えなければ照合しない。

### Non-blocking
- N-r16-1：deploy の順（入れ物の作り直し → migration）のため、反映の数分は一覧の SQL が新しい表を引けず 500 になりうる（使うのは PO だけ）。ボタンはまだ置かないので受付への影響は無い。反映後に一覧が 200 になることを本番で確かめる。
- N-r16-2：片付けは「受付のカテゴリの中の trial-<数字> で、行が無いもの」を消す。PO の手順書で、受付のカテゴリをトライアル専用にすることを書く。

### 判定
APPROVE（Blocking 0、Non-blocking 2）。

### 未解決
- PO の Discord の設定作業（ボットのロールの権限、受付の部屋の上書き、4つの ID、set-config と post-button の GO）。

## r17（2026-10-17。段4c の実装のコード審査：commit 66104ef55。審査は Opus、同一 AI の自己審査。生出力 /tmp/CC報告ファイル/viewer_stage4/impl_4c/）

### 照合した範囲
- client.py：init_redis（setup_hook）・close_redis（close）・片付けの loop（on_ready）・on_interaction の先頭の viewer_trial_ 分岐。分岐は例外を握って return し、顧客用の処理に流れない。
- ticket_channel_creator.py：部品の呼び出しの位置は変わらない。_bot_permission_overwrites の名前は残る。private_channel.py のログの文字列は "[ticket] ..." のまま。
- migration：1行だけの表（CHECK id=1）、GRANT は salesanchor_app、run_all_migrations.sh に登録。
- viewer_trial.py の全文：DELETE…RETURNING で消費 → FOR UPDATE で pending を確かめる → 部屋 → UPDATE → 記録 → commit。IntegrityError のときは部屋を消す。
- viewer_discord_cli.py：action は3つだけ。ID は数字1〜32文字。トークンと traceback を出さない。DISCORD_BOT_TOKEN は backend の入れ物にある（docker-compose.yml:109）。
- 画面：ButtonLink（金型）・i18n の ja/en は同じキー。部屋の URL がある行だけにリンクを出す。

### 検証（手元）
- pytest：41 passed / 17 skipped / 1 failed。落ちた1件（test_non_super_admin_gets_403_on_all_six_routes）は、手元の venv に greenlet が無いため（環境の問題）。CI で確かめる。
- tsc の error 5件は今回触っていないファイル（generated schema・@xyflow）。CI で確かめる。

### 判定
APPROVE（Blocking 0）。マージの条件は CI が全部緑であること。
