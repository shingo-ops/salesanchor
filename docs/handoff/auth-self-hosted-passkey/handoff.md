# 引き継ぎ — auth-self-hosted-passkey

> この文書は何か：ログインの自社化とパスキー追加の設計を、次のセッションが続きから進めるための引き継ぎです。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**日付**: 2026-10-14
**書いた人**: 設計パートナー（Opus・ccopusgo セッション）

## 状態（2026-10-14 時点・証拠つき）

| 段階 | 状態 | 証拠 |
|---|---|---|
| 便0（設計・ADR-1013） | main にマージ済み | #4225（ADR 改名・カード b1 を含む） |
| 便1（DB の置き場・migration） | 本番反映済み | #4227 マージ 9b407b41f（2026-10-13 19:51 JST）。deploy run 38386226760 success。直前バックアップ salesanchor_db_20261013_195212.sql.gz（371M） |
| 便2（自社ログインの心臓部・backend） | main にマージ済み | #4231 マージ 6c8a5955a（2026-10-14 00:41 JST）。CI 42 pass・fail 0。Fable セキュリティ審査 APPROVE（HEAD 1436bb344）。本番反映の確認は下の「便2 本番確認」 |
| 便3〜便6 | 未着手 | 便3・便4・便6 は PO の作業（外部 GUI・秘密の追加・パスワード配布・Firebase 削除）が要る |

### 便1 本番確認（2026-10-13 19:57 JST 前後・読み取りのみ）

- 新 3 表（webauthn_credentials・password_reset_tokens・auth_refresh_tokens）が存在し、全て 0 行
- users 13 行。password_argon2_hash が入った行 0・failed_login_count が 0 以外の行 0（＝この 2 列は存在する）
- **未確認**: users の password_changed_at・locked_until の 2 列。information_schema の SELECT が自動の権限判定に拒否されたため。迂回はしていない。便3 のカード作成前に、PO の端末か許可を取った読み取りで `\d public.users` を確かめる
- HTTP: app /health 200、login（Origin 付き）404、トークンなしの logout 401（反映前の基準値と同じ）

### 便2 本番確認

- deploy run 38424242587 は success（2026-10-14 00:46 JST 完了）。Finalize の「Step 6: Health check passed」、FedEx smoke passed、設計図書サイト smoke ①〜⑤ 合格。ログに `##[error]` は 0 行。migrations は含まない
- HTTP（00:47 JST、`https://app.salesanchor.jp`）:
  - /health 200、トークンなしの /api/v1/auth/logout 401（反映前と同じ）
  - /api/v1/auth/login に正しい形の本文（存在しない宛先）を送ると、Origin の有無どちらも 404 `{"detail":"Not Found"}`。/api/v1/auth/refresh も 404。既定の `AUTH_PROVIDER=firebase` で発行の口が閉じていることを確認
  - 反映前との違い: 本文が空の login は 404 から 422 に変わった。口が新設されたため、入力の形の検査（FastAPI の本文検査）が 404 の判定より先に走る。DB には触れない（`backend/app/routers/auth.py:219-229`）
- 今の Firebase ログインを実際に試す確認はしていない（本番のパスワードを持たないため）。Firebase の経路のコードは変えていない（便2 審査）

## 便4 の前に直す残件（便2 審査の LOW 3 件・未確認 1 件）

1. `backend/app/routers/auth.py` の `_clear_refresh_cookie`（211-212 行目）が、Cookie を消すときに secure・httponly・samesite を付けていない。付けた時と同じ属性で消す
2. `backend/app/auth/dependencies.py` 105 行目の `fromtimestamp` が try の外にある。不正な時刻の値で 500 になりうるので、try の中へ入れて 401 にする
3. `backend/tests/test_self_auth.py` が httpx の「リクエストごとの cookies 指定」（非推奨）を使っている。クライアントの cookie に設定する形へ直す
4. **未確認**: 本番 `public.users.last_login` の型（タイムゾーン付きかどうか）。便4 で login が last_login を更新する（K1 の測り方）ため、便4 のカード作成前に確かめる

## 次の一手（順番どおり）

1. 便3 の実装カードを作る（design.md §6 便3）。その前に、上の未確認 2 列を確かめる
2. 便3 には PO の作業が要る。さくらで送信用アドレスを作り DKIM を有効にする。DNS に DMARC を追加する。SMTP の secrets を登録する。手順書は便3 のカードに付ける
3. 便4（切替・パスワード配布）・便6（Firebase 削除・不可逆）も PO の作業と GO が要る

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
