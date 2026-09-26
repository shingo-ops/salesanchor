# Android取込から配信までの現在地
この文書は、受付後にどこで止まり、何を接続するかの記録です。
親: [商品マスタ](../../specs/product-master/README.md)
設計: [管理接続](design.md)

2026-09-12、origin/main e1ad3a4eを確認。既存テーマの延長。
- backend/app/routers/tcg_line_import.py:395 のresolveは管理者専用。createは新規仕入先、assignは既存名を変更するため同一性を推測して実行しない。
- backend/app/routers/tcg_line_import.py:558 のcommitは再照合し、未解決時409、確定後に抽出をenqueueする。
- backend/app/services/tcg_import_progress.py:49 は取込単位の観測結果を返す。解析実行の成功履歴は未記録であり、完了を捏造しない。
- backend/app/services/tcg_distribution_svc.py:183 は有効原文・確定商品・単位・価格等の配信行を取得する。
- backend/app/services/tcg_distribution_svc.py:628 のrun_distributionは全体の在庫集計を指定シートへ配信する。今回の取込だけの追記ではない。
- backend/app/services/tcg_distribution_svc.py:676 は未完了抽出が残る場合に配信を止める。
- .github/workflows/line-import-device.yml:1 は管理者限定の既存SSH運用を提供するが端末認可/取消しのみ。

PR #3445の本番deploy34676818835成功。端末保存の受付応答は2件ともpending_review（1129/1134メッセージ、各39名未照合）。これは現在DB再照会とは区別する。
この端末には本番SSH鍵がない。インポート専用キーは管理者APIを呼べない。接続制限を迂回せず、用途を限定した管理操作を既存手動workflowへ追加する。
ADR検索: ADR-072スキーマ明示、ADR-154既存解析移行、docs/handoff/tcg-product-master-growth/recon.mdの配信保留を確認。未登録者の扱い・配信先についてユーザーへ確認中。未知名の一括登録や自動配信はまだ実行していない。
