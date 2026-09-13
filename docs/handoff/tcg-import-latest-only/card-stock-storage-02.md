本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02 — 草案・未発行

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、07-migration.md、10-executor.md、11-lint.md。
照合結果: 既存migrationはtenantスキーマ走査・追加専用、run_all_migrations.sh登録と実PG確認が必要。第1便の部品検収は完了。製品PR3471への正式引き継ぎも完了。第2便の実装委任は未受領。本カードは投入しない。

受領確認: 実装役がこの草案を受け取った場合は「第2便未発行」を返して停止する。以下は発行前に具体化する作業内容であり実行命令ではない。
開始条件: 第1便のコード/試験検収、最新mainとの統合済み作業台、次の3ファイルへの正式な権限、以下のCI専用隔離PostgreSQL試験経路を設計担当が確認して発行版へ改訂した後。

変更予定の3ファイル:
- migrations/20260913_230000_tcg_stock_projection.sql（新規、採番再確認）
- scripts/run_all_migrations.sh（既存登録を保持、新SQLのrun_sql登録1行のみ）
- backend/tests/test_tcg_stock_schema_pg.py（新規、実PostgreSQL制約検証）

設計正本: docs/handoff/tcg-import-latest-only/design.md §20/21/27。
SQL責務: 6表と2追加列、FK/NOT NULL/CHECK/索引/不変トリガー、controlのlegacy初期行。既存構造の削除・型変更・大量データ補正はしない。初回shadowやprojectedへの移行もしない。
対象: 必須TCG親テーブルが揃うtenant_NNNだけ。必要な親が一部欠けるスキーマは無言成功にせず検証失敗として報告する。既存全対象と新規プロビジョニング後の再適用経路を検証する。

実PGで確認する試験群:
1. 2回適用後も新規6表/追加2列/control1行、既存行の業務値と既存登録行が不変。
2. available/null、sold_out/正数量、負数、NaN/Infinity、不正enum、非object/array/JSON null/必須キー欠落、非64桁digest、訂正履歴IDのUUID/数値型/範囲外を拒否する。訂正IDは十進文字列として1/2/10/9007199254740993/9223372036854775807を保持する。
3. appliedに対象/時刻/revisionが欠けた行、別offer/channelの参照、終端イベント改変、原文削除の連鎖を拒否する。
4. 同一transaction内の循環参照は正しい場合だけ成功し、不正なcommitは全変更を戻す。
5. 予定の日付型/範囲と無限日付拒否、ready後のpayload/manifest不変、予約の対象一致を検証する。
6. controlのlegacy/paused-legacyを許可し、baselineなしshadowや承認版なしprojected、勝手なrollout_id変更を拒否する。
7. inboxのsource/seq二重登録と改変、別sourceのevent参照、未記録のsettledを拒否する。
8. 同一ローカル試験DBの複数テナントでFK/行が混ざらず、TCG未導入スキーマを対象にしない。

検証環境: .github/workflows/test.ymlのpytest-run-internalがPostgreSQL16の使い捨てserviceを提供する。backend/tests追加で既存の全pytest対象となる。CI変更なし。ローカルDockerは未起動なのでこの端末で実PGを実行しない。
試験専用fixtureを新規test_tcg_stock_schema_pg.py内に定義する。既存test_tcg_work_matching_integration.pyの隔離方法だけを踏襲し、その解析関数/monkeypatch/商品辞書seedはimportしない。
実際のGitHub Actions、RLS_ADMIN_DATABASE_URLの存在、host=localhostまたは127.0.0.1、管理DB=jarvis_test_dbを接続前に確認する。接続情報はログへ出さない。条件不一致はfailでありskipにしない。
UUID付きtcg_stock_test_名の新DBを作り、そのDB内だけにtenant_951/952/953/954を使う。他fixtureのDB/テナントへ接続しない。各試験fixtureは別DB、終了時は接続を閉じ、DBの廃棄はCIのservice終了に任せる。DB削除命令をテストへ追加しない。
親表準備は既存20260906_120000_create_tcg_tables_t001.sqlのtenant_001指定だけを試験スキーマへ置換して実行。新migration本文は書き換えず適用する。raw_work_name等の追加列を新migrationが参照する場合は既存の正規前提migrationを順に適用し、欠落を試験内の即席DDLで埋めない。
951/952はTCG導入済み、953は初回空で未導入→後から同じbootstrap適用→新migration再適用、954は親欠落の異常系として独立したfixtureで確認する。新規6表と追加2列だけを数える。
全pytestの成功件数だけで8群の実行を推定しない。8個のtest関数名、収集結果、失敗/skip0を実装担当が示す。SQL変更のmigration-testとmigration-full-dryrunの実行結果も別に確認する。文書PRのチェック成功はこれらの実行証拠ではない。

禁止: 本番/QAサービスへの接続、既存ジョブの起動、AI/Sheets、secrets、CI・guard変更、permit自己発行、deploy/マージ、未記載の運用スクリプト編集。
完了報告に必要: 実HEAD、3ファイル差分、適用対象、収集/成功/失敗/skip件数、実PG結果、登録検査結果。これらが揃っても本番GOにはしない。
停止条件: 採番衝突、既存登録差分、対象不明、検証失敗、権限拒否のいずれか。失敗した操作と出力を設計担当へ返す。
END OF CARD

## 草案の形式検査

card-lintは書式だけを確認する。実行コマンドを持たない未発行草案が形式検査を通っても、実装可能なカードへ昇格しない。正式版の作業台・検証コマンドは前段検収後に固定する。

## 発行前の具体化記録（2026-09-13）

参照mainは56a1661d03a583be53fc74507c7d428faa2f0b18（GitHub APIとローカルorigin/main一致）。予定SQL名は未使用。登録位置は既存の20260913_150000_tcg_empty_box_condition.sqlのrun_sql行の後。既存行は変更しない。
新規テナントへの試験は「TCG親表準備後に本SQLを再適用できる」の検証であり、全テナント作成経路への自動導入を実装済みとはしない。実サービス側でTCGを導入する運用は別の開始条件として残す。
同一AIの査定: CI試験経路の設計はAPPROVE。第2便カード全体は未発行。第1便の正式保存は完了。具体的な第2便専用作業台と担当への範囲付与がまだ必要。実PG結果は0件であり、実装前の試験成功を捏造しない。

## 実装委任案（3ファイル・第2便だけ）

担当候補は既存stock_contract_01。新規エージェントは起動しない。最新origin/main起点のrelease/line-stock-storageを専用候補にする。新規SQL1本・登録1行・実PG試験1ファイルの実装、検証、commit/push/PRと既存CIによる試験までをPOへ提示する。第1便の追加委任は本便へ流用しない。実装カードの発行版は作業台実在確認後に手順と設計hashを固定して再検査する。
SQL試験8群の関数名はtest_repeat_and_existing_data、test_value_and_snapshot_constraints、test_event_integrity、test_deferred_transaction_integrity、test_plan_and_publication_integrity、test_control_integrity、test_inbox_integrity、test_existing_future_and_absent_tenantsに固定。各群の収集と実行を証跡に残す。
最新mainの訂正履歴とEmpty boxの定義は書き換えない。第2便では数量/商品/状態を本サービスへ投影せず、control初期値legacyのまま。本番適用、既存処理接続、配信、マージ、第3便への自動移行は禁止。
