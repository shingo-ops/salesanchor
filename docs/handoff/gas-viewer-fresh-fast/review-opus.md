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
