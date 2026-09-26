# Android取り込みの現状と検証記録

この文書は、実ファイルで確認した形式の違いと実装の検証状況を残す。
親: [商品マスタ](../../specs/product-master/README.md)
設計: [design.md](design.md)

## 根拠

- backend/app/services/tcg_line_import_svc.py:42 の_DATE_REはPC形式。Androidはスラッシュ日付とタブ。既存パーサーで実ファイルを読むと0件だった。
- backend/app/routers/tcg_line_import.py:135 のPCアップロード関数は維持。専用POSTを追加した。
- backend/app/auth/dependencies.py のrequire_super_admin、backend/app/tcg_config.py のTCG_SCHEMAを共用。
- ADR検索: ADR-072／ADR-154／FEATURE-INDEXのLINE検索は該当なし。既存PMG設計の参照先と投稿同一性契約を確認した。
- origin/main 66b41766からrelease/line-android-importを作成。
- GitHub CLI shingo-cc認証成功、executor-preflight OK。

## 実データと検証範囲

受信済みAndroidファイルは2,048,526 bytes。1,129件、123送信者、複数行1,035件、最長6,633文字。原本を端末内で保持し、SHA256とバイト比較で保存時の無改変を確認。
パーサー単体6テスト、Termux側16テスト成功。組み込みAPIと共通サービスのテストを追加。本番送信・取引先確定・解析開始は未実施。

## 再開・導入

先にPR/CIとレビューを確認する。サーバーのAndroid専用API導入後、Termuxの認証設定・送信有効化を行う。既存のPC入口へAndroid原文を送らない。
Termuxクライアントの操作はtools/termux-line-import/README.mdを参照。

## 静的検査

Python 3.12.14でmake lint-ciを実行。ruff成功、banditの高重大度0件・検査スキップ0件。mypyは非ブロッキング検査で、既存コードと未導入依存関係にエラーが残る。変更した3つのappファイルにmypyエラーはない。Dockerを利用できないためpytestはCIで検証する。check-task-state.shとcheck-doc-heading-duplicates.shは成功。

## GitHubへの保存

PR: https://github.com/shingo-ops/salesanchor/pull/3443 （Draft）。PCのparse_line_exportとupload_line_exportはorigin/mainとのAST比較で不変。GitHubの静的検査成功。process-artifacts gateはPR番号付きPO GOの記録待ち（CLAUDE.md:57）。マージ・本番反映は未実施。

CI run 34672625832（コードcommit 6af78135）: PostgreSQLを含む全体pytestは2,608 passed / 95 skipped / 309 warnings、96.09秒。追加Android APIテストを含み成功。https://github.com/shingo-ops/salesanchor/actions/runs/34672625832 。端末から本番への送信試験とは区別する。

## 追補 2026-09-17：受信通知・経過履歴・定期点検・原本1件保持（release/termux-import-notify）

この追補は、Termuxで受け取ったtxtの送信結果をスマホに知らせ、詰まりを記録する変更の前に確かめた事実を残す。

### 実機で確かめた事実
- 端末の配置物（~/line-import/lib の client.py・android_parser.py・device_session.py と ~/bin の line-import・termux-file-editor）は、リポジトリの tools/termux-line-import と cmp で完全一致した（2026-09-17）。
- 端末の送信キューは5件で、すべて state=pending_review、import_job_id ありだった。最終送信は2026-09-17 09:33頃（retry_at から逆算）。自動送信は実運用で動いている。
- 容量：inbox に受信コピー6件（13MB）、state/originals に原本5件（11MB）。同じtxtが2か所に残る。
- Termux本体は F_DROID 版（termux-info の TERMUX_APK_RELEASE=F_DROID）。termux-api パッケージ 0.60.0 導入済み。Termux:API アプリが未導入の間は termux-notification が応答せず止まった。F-Droid版 Termux:API を導入後、Termux本体とUbuntu側の両方から通知が表示された（Ubuntu側は1秒で終了コード0）。
- termux-job-scheduler は --period-ms・--persisted・--job-id を持ち、Android N 以降の最短周期は900,000ms（15分）と表示された。登録済みの予定は0件。

### コードで確かめた事実
- tools/termux-line-import/client.py:34 の jobs テーブルは digest・state・attempts・retry_at・job_id・response・error だけで、受信時刻・送信開始/終了時刻・経過秒を持たない。
- tools/termux-line-import/client.py:60 は同一 digest を INSERT OR IGNORE で二重登録しない。古い原本を消す処理はない。
- tools/termux-line-import/client.py:74 の再送対象は queued/retry/auth_required で retry_at 経過分。再送が走るのは tools/termux-line-import/client.py:149 の共有時と、手動の send だけで、定期実行はない。
- tools/termux-line-import/client.py:92 / :94 / :96 が 401・403／404／400・413・415・422 を状態に分類する。通信不能（code=0）は既定の retry と「通信結果を確認できません」になる。
- tools/termux-line-import/client.py:110 の再送間隔は 30秒×2^試行回数（上限3600秒）。
- tools/termux-line-import/client.py:119 は window_hours=0 を送る（PCとの期間統一は別作業に分離。PO決定 2026-09-17）。
- tools/termux-line-import/client.py:143 は処理全体を flock で排他する。tools/termux-line-import/client.py:165 は例外時に原因を区別せず1文だけ出力し、どこで止まったかは残らない。
- tools/termux-line-import/termux-file-editor:14 は受信ごとに inbox/received-* を作り、tools/termux-line-import/termux-file-editor:15 でコピーする。消す処理はない。
- tools/termux-line-import/README.md:26 は「acceptedはAPI受付で解析完了とは区別する」と定める。端末トークンは送信と自身の認可確認だけに使える（tools/termux-line-import/README.md:25）。解析・シート反映の完了は端末から確認できない。

### ADR検索
- `git grep -il -E 'termux|line.?android|line-devices' docs/adr/` は該当なし。docs/adr/FEATURE-INDEX.md にも termux/android の記載なし。既存の対象ADRは ADR-072・ADR-154 のまま。backend・DB・APIは変更しない。

### PO決定（2026-09-17）
- 完了通知は「アプリへの取り込み（API受付）」まで。解析・シート反映の完了は対象外。
- 履歴は既存の outbox.sqlite3 に追加し、90日保持。
- 端末の原本は最新1件のみ保持。既存の古い原本・受信コピーは、一覧を提示してから消す。
- 詰まりと判断する時間は、実機で計測してから決める。反映は PR 作成後・マージ前に端末へ入れて計測する。
- スマホからの期間を24時間に揃える変更は別作業。
