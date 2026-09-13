本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02 — 草案・未発行

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、07-migration.md、10-executor.md、11-lint.md。
照合結果: 既存migrationはtenantスキーマ走査・追加専用、run_all_migrations.sh登録と実PG確認が必要。第1便は未検収。本カードは投入しない。

受領確認: 実装役がこの草案を受け取った場合は「第2便未発行」を返して停止する。以下は発行前に具体化する作業内容であり実行命令ではない。
開始条件: 第1便のコード/試験検収、最新mainとの統合済み作業台、次の3ファイルへの正式な権限、ローカル/CIの隔離PostgreSQL試験経路を設計担当が確認して発行版へ改訂した後。

変更予定の3ファイル:
- migrations/20260913_230000_tcg_stock_projection.sql（新規、採番再確認）
- scripts/run_all_migrations.sh（既存登録を保持、新SQLのrun_sql登録1行のみ）
- backend/tests/test_tcg_stock_schema_pg.py（新規、実PostgreSQL制約検証）

設計正本: docs/handoff/tcg-import-latest-only/design.md §20/21/27。
SQL責務: 6表と2追加列、FK/NOT NULL/CHECK/索引/不変トリガー、controlのlegacy初期行。既存構造の削除・型変更・大量データ補正はしない。初回shadowやprojectedへの移行もしない。
対象: 必須TCG親テーブルが揃うtenant_NNNだけ。必要な親が一部欠けるスキーマは無言成功にせず検証失敗として報告する。既存全対象と新規プロビジョニング後の再適用経路を検証する。

実PGで確認する試験群:
1. 2回適用後も新規6表/追加2列/control1行、既存行の業務値と既存登録行が不変。
2. available/null、sold_out/正数量、負数、不正enum、非object/array、非64桁digestを拒否する。
3. appliedに対象/時刻/revisionが欠けた行、別offer/channelの参照、終端イベント改変、原文削除の連鎖を拒否する。
4. 同一transaction内の循環参照は正しい場合だけ成功し、不正なcommitは全変更を戻す。
5. 予定の日付型/範囲、ready後のpayload/manifest不変、予約の対象一致を検証する。
6. controlのlegacy/paused-legacyを許可し、baselineなしshadowや承認版なしprojected、勝手なrollout_id変更を拒否する。
7. inboxのsource/seq二重登録と改変、別sourceのevent参照、未記録のsettledを拒否する。
8. 同一ローカル試験DBの複数テナントでFK/行が混ざらず、TCG未導入スキーマを対象にしない。

検証環境: 既存のCI専用fixtureはGITHUB_ACTIONS=true、localhost、jarvis_test_dbを検査して隔離DBを作る。ローカルで環境変数を偽装して利用しない。正式版では実際に使える隔離PG経路を固定し、環境不足/skipを成功としない。試験DB以外へのSQL実行は許可しない。

禁止: 本番/QAサービスへの接続、既存ジョブの起動、AI/Sheets、secrets、CI・guard変更、permit自己発行、deploy/マージ、未記載の運用スクリプト編集。
完了報告に必要: 実HEAD、3ファイル差分、適用対象、収集/成功/失敗/skip件数、実PG結果、登録検査結果。これらが揃っても本番GOにはしない。
停止条件: 前段未検収、採番衝突、既存登録差分、対象不明、検証失敗、権限拒否のいずれか。失敗した操作と出力を設計担当へ返す。
END OF CARD

## 草案の形式検査

card-lintは書式だけを確認する。実行コマンドを持たない未発行草案が形式検査を通っても、実装可能なカードへ昇格しない。正式版の作業台・検証コマンドは前段検収後に固定する。
