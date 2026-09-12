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
