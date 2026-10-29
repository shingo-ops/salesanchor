# 引き継ぎ — auth-self-hosted-passkey

> この文書は何か：ログインの自社化とパスキー追加の設計を、次のセッションが続きから進めるための引き継ぎです。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**日付**: 2026-10-14（便3 の反映と K5 の結果を 2026-10-29 に追記）
**書いた人**: 設計パートナー（Opus・ccopusgo セッション）

## 状態（2026-10-14 時点・証拠つき）

| 段階 | 状態 | 証拠 |
|---|---|---|
| 便0（設計・ADR-1013） | main にマージ済み | #4225（ADR 改名・カード b1 を含む） |
| 便1（DB の置き場・migration） | 本番反映済み | #4227 マージ 9b407b41f（2026-10-13 19:51 JST）。deploy run 38386226760 success。直前バックアップ salesanchor_db_20261013_195212.sql.gz（371M） |
| 便2（自社ログインの心臓部・backend） | 本番反映済み | #4231 マージ 6c8a5955a（2026-10-14 00:41 JST）。CI 42 pass・fail 0。Fable セキュリティ審査 APPROVE（HEAD 1436bb344）。本番反映の確認は下の「便2 本番確認」 |
| 便2 追補（審査 LOW 3 件の修正） | 本番反映済み | #4240 マージ 8faa13fd1（2026-10-14 06:19 JST）。必須 CI 15 pass。Fable コード審査 APPROVE（f86bd37b9）。deploy run 38469745118 success。06:23 JST に /health 200・login（正しい形の本文）404・トークンなしの logout 401（反映前と同じ） |
| 便3（メール送信の設定） | 本番反映済み・K5 合格（2026-10-29） | #4250 マージ 955e6e96f。設定の反映は #4841（deploy run 40722913338 success）。K5 の結果は下の「便3 K5 確認（2026-10-29）」 |
| 便4〜便6 | 未着手 | 便4・便6 は PO の作業（パスワード配布・Firebase 削除）が要る |

### 便3 PO 作業と設定の反映（2026-10-29）

手順の正本は card-b3.md §8。値（宛先・パスワード）はここに書かない。

- §8 ② PO の GUI 作業（観測は名前と時刻だけ）:
  - `gh secret list`: `SMTP_HOST`・`SMTP_PORT`・`SMTP_USER`・`SMTP_PASSWORD`・`MAIL_FROM` は 2026-10-15T15:47〜15:51Z、`AUTH_PASSWORD_RESET_ALLOWLIST` は 2026-10-28T15:55:56Z に登録。`CONTACT_NOTIFY_EMAIL` は未登録（空なら既定の宛先。card-b3 §8 ② 5）
  - DNS（`dig +short TXT`）: `_dmarc` に `v=DMARC1; p=none; ...`、DKIM セレクタ `rs20261029._domainkey` に `v=DKIM1; k=rsa; ...` が出る
- 反映前の基準値:
  - main への最後の deploy は run 40716816581（2026-10-28T15:31:26Z 開始・success）。`AUTH_PASSWORD_RESET_ALLOWLIST` の登録より前なので、本番にはまだ入っていない
  - 本番 DB（読み取り専用の道・2026-10-28T15:59〜16:00Z）: users 13 行・max(id) 84。tenant 6 は有効。試験用 Gmail と同じ email の行 0。password_reset_tokens 0 行
  - 本番コンテナの環境変数は、読み取り専用の道では見られない（未確認）
- §8 ③: この handoff 更新の PR（docs のみ）のマージで deploy を走らせる（deploy は main への push だけで動く。card-b3 F7）
  - 結果: #4841 マージ 0fa0055ed（2026-10-28T16:07:49Z）。deploy run 40722913338 success（16:10Z 完了）。ログに `##[error]` 0 行、「Step 6: Health check passed」と「FedEx smoke passed」あり。/health 200

### 便3 K5 確認（2026-10-29）

宛先の値はここに書かない（試験用 Gmail ＝ `AUTH_PASSWORD_RESET_ALLOWLIST` に登録した 1 件）。

- 試験用の利用者の追加（PO の同意で Opus が実行。台本は dryrun → apply の順。dryrun は PO が実行し ROLLBACK で 13 行のまま）:
  - 2026-10-29T00:45:43Z、tenant 6 に 1 行 INSERT（id 86・role user・is_active true・is_super_admin false・パスワード未設定）。実行後 users 14 行・max(id) 86。DO ブロックの件数ガード（前 13・後 14・同じ email 0 行）を通過
  - id 85 は dryrun の ROLLBACK で消費済み（連番の欠番）
- 再設定の request（00:46:43Z、`POST https://app.salesanchor.jp/api/v1/auth/password-reset/request`、Origin `https://app.salesanchor.jp`）: HTTP 200 `{"status":"accepted"}`
- 読み取り専用の道（00:46:53Z）: password_reset_tokens 1 行（user_id 86・created_at 00:46:44Z・expires_at 01:16:44Z・used_at 空）
- 受信（PO の Gmail・画面の写しで確認）: 件名「【Sales Anchor】パスワード再設定 / Password reset」、差出人は便3 で作った送信用アドレス、受信トレイに 9:46 JST 着。迷惑メールではない
- SPF・DKIM・DMARC: PO が「原文を表示」で 3 つとも PASS と回答（PO の申告。Opus は原文の画面を見ていない）
- 判定: K5 合格。本番コンテナに `SMTP_HOST` と `AUTH_PASSWORD_RESET_ALLOWLIST` が入っていることも、メールが届いたことで裏づけられた
- 後片付け（PO の同意で Opus が実行）: 2026-10-29T01:02:39Z、id 86 を is_active false にした（行は消さない）。実行後 users 14 行・id 86 は is_active false。メールのリンクは押していない（01:05:52Z の読み取りで used_at 空・id 86 は is_active false。期限は 01:16:44Z）

### 便1 本番確認（2026-10-13 19:57 JST 前後・読み取りのみ）

- 新 3 表（webauthn_credentials・password_reset_tokens・auth_refresh_tokens）が存在し、全て 0 行
- users 13 行。password_argon2_hash が入った行 0・failed_login_count が 0 以外の行 0（＝この 2 列は存在する）
- users の password_changed_at・locked_until は存在し、型は timestamptz（2026-10-14、PO の委任による読み取り・`pg_typeof` で確認）
- HTTP: app /health 200、login（Origin 付き）404、トークンなしの logout 401（反映前の基準値と同じ）

### 便2 本番確認

- deploy run 38424242587 は success（2026-10-14 00:46 JST 完了）。Finalize の「Step 6: Health check passed」、FedEx smoke passed、設計図書サイト smoke ①〜⑤ 合格。ログに `##[error]` は 0 行。migrations は含まない
- HTTP（00:47 JST、`https://app.salesanchor.jp`）:
  - /health 200、トークンなしの /api/v1/auth/logout 401（反映前と同じ）
  - /api/v1/auth/login に正しい形の本文（存在しない宛先）を送ると、Origin の有無どちらも 404 `{"detail":"Not Found"}`。/api/v1/auth/refresh も 404。既定の `AUTH_PROVIDER=firebase` で発行の口が閉じていることを確認
  - 反映前との違い: 本文が空の login は 404 から 422 に変わった。口が新設されたため、入力の形の検査（FastAPI の本文検査）が 404 の判定より先に走る。DB には触れない（`backend/app/routers/auth.py:219-229`）
- 今の Firebase ログインを実際に試す確認はしていない（本番のパスワードを持たないため）。Firebase の経路のコードは変えていない（便2 審査）

## 便4 の前に直す残件

- 便2 審査の LOW 3 件は #4240 で解消（Cookie を消すときの属性・不正な iat で 401・テストの Cookie 指定）。カード: card-b2-fix.md
- 本番 `public.users.last_login` の型は timestamptz（2026-10-14 確認。users 13 行）

## 次の一手（順番どおり）

1. 便3 は完了（K5 合格・試験用の利用者は停止済み）。DMARC は `p=none`（観測だけ）のまま。強める時期は未定
2. 便4（切替・パスワード配布）・便6（Firebase 削除・不可逆）は PO の作業と GO が要る

## 途中で分かった注意

- 本番 DB の読み取りで `<>` を使うと、フック agent-danger-hook.sh の正規表現が「ssh＋psql＜ファイル」と誤検知して止める。`!=` を使う
- pr-body-guard は recon.md・design.md を作業ディレクトリ基準で探す。`gh pr edit --body-file` は worktree に移動してから実行する
- guard-authoring・guard-evaluation の state=error は、base が head の祖先でないときに起きる（`scripts/run-guard-evaluation.js:25`）。main を取り込めば消える
- main が速く進むため、マージ前に update-branch（merge commit）→ CI 待ち → GO 記録の HEAD 書き換え、を何度か繰り返した。rebase はフックで禁止
- 本番 backend は `docker run` で入れ替える作り（`scripts/blue-green-cutover.sh`）。コンテナ名 astro-webapp-backend-1 で読む
- ADR 索引のスクリプトは、状態の欄に「承認」の語があると Accepted と判定する（`scripts/generate-adr-index.js:59`）

## 最初の依頼（審査用アカウント）

- review@salesanchor.jp は Firebase と public.users（id=10・tenant 6）の両方に存在し、ログインできない原因はパスワード不一致だけ（recon P6・P13）
- 直し方は PO に案内済み（ログイン画面「パスワードをお忘れの方」→ さくらの Web メールで再設定）。PO が実施したかは未確認
