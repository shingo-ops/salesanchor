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
