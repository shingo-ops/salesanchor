本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、07-migration.md、10-executor.md、11-lint.md。
照合結果: 既存migrationはtenantスキーマ走査・追加専用、run_all_migrations.sh登録と実PG確認が必要。第1便の部品検収は完了。製品PR3471への正式引き継ぎも完了。第2便の実装・検証・PR提出までPO委任受領済み。本カードは実装と静的検証まで。commit/push/PRは親の差分確認後に別カード。

再開範囲（2026-09-13、ガード拒否後の影響を受けない部分）:
- 保存済み新SQLのhashは08e7f6b375d4143eb81e67a75c9a278012884f5dfa022c6065b36cb4f0ece0a2。手順2はこの新規SQL1ファイルだけ未追跡が期待値。破棄・巻戻ししない。
- 拒否された原文削除の負例の保存は停止を維持する。その命令を別のAPI・文字列分割・別ツールで代替しない。許可チケット自己発行は禁止。
- 新SQLの原文参照ロック等の残る実装、登録1行、残りの負例/正常系を持つ8試験関数の保存と静的検査だけを続ける。原文削除拒否の受入条件は削除しない。未作成・未検証として報告する。
- 第3群にその削除負例を入れていない段階を全試験完了としない。偽の成功・skip・代用の文字列検査を加えない。その他の検査失敗時の停止は従前どおり。
- 拒否された負例の正確な追加予定コードを、コマンドとして実行せず最終報告のテキストで親へ返す。POが保存対象を確認できる材料とする。
- commit/push/PR/実DB実行は禁止のまま。未完了の削除負例を含めて親が確認し、必要な承認を求める。

受領確認: カードID・作業台・3ファイルだけの範囲を返す。担当は同じstock_contract_01。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
他者と共同の作業環境である。他者の変更を戻さない。親は受領後に作業台を編集しない。
許可: 以下3ファイルの実装・読み取り・静的検査。製品コードやDBの既存値を変更する呼出元は追加しない。
禁止: 文書/台帳/GO/依存/CI/secrets編集、新規エージェント、commit/push/PR/merge、本番/QA/ローカルDBへのSQL実行、全backend pytestのローカル実行。

変更ファイル（固定3ファイル）:
- migrations/20260913_230000_tcg_stock_projection.sql（新規、未使用を親確認済み）
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

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: release/line-stock-storageで上記hashの新SQL1ファイルだけ未追跡。親の文書commit後に開始。
手順3: 設計照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && shasum -a 256 docs/handoff/tcg-import-latest-only/design.md
    期待する出力: 6744f7a7e6f5cef0a716677f7b8ef2b5e5702a35131346b0c777b8dec6b5a1f3。
手順4: 実装
    design §15/20/21/24/27と本カードの8群を読み、§27を現行正本として3ファイルを実装する。
    migrationはDO/pg_namespace走査、追加専用、トランザクションで失敗を戻す。既存TCG親の欠落を無言成功にしない。
    最新mainのCN0011と訂正履歴の既存値を変えず、既存run_all_migrations.sh末尾の空箱migration登録の後へ新run_sqlを1行だけ追加する。
    循環参照・複数表整合・原文側変更の拒否は設計の対象として実装する。原文との不一致を数値の丸めやUUID変換で吸収しない。
    検査のためのヘルパー/fixtureは新規試験ファイル内だけに置く。既存テストのfixtureは変更しない。
    8関数名: test_repeat_and_existing_data、test_value_and_snapshot_constraints、test_event_integrity、test_deferred_transaction_integrity、test_plan_and_publication_integrity、test_control_integrity、test_inbox_integrity、test_existing_future_and_absent_tenants。
    設計契約の不明点は親へ返す。製品を独断再設計しない。実PGはPR提出後の本物のCIで実行するため、ローカル未実行を合格としない。
手順5: Python構文と試験群確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && python3 - <<'CHECK'
import ast
from pathlib import Path
p=Path('backend/tests/test_tcg_stock_schema_pg.py')
tree=ast.parse(p.read_text())
names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')}
expected={'test_repeat_and_existing_data','test_value_and_snapshot_constraints','test_event_integrity','test_deferred_transaction_integrity','test_plan_and_publication_integrity','test_control_integrity','test_inbox_integrity','test_existing_future_and_absent_tenants'}
assert names==expected,names
print('syntax valid; eight named groups present; NOT executed')
CHECK
    期待する出力: syntax valid; eight named groups present; NOT executed。
手順6: 試験コード静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 成功。失敗なら停止して親へ報告。
手順7: 登録スクリプト構文
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && bash -n scripts/run_all_migrations.sh
    期待する出力: exit0。実スクリプトは実行しない。
手順8: 登録1行と範囲検算
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && python3 - <<'CHECK'
import subprocess
from pathlib import Path
p='scripts/run_all_migrations.sh'
old=subprocess.check_output(['git','show','HEAD:'+p],text=True)
new=Path(p).read_text()
assert new==old+'run_sql migrations/20260913_230000_tcg_stock_projection.sql\n'
print('existing registry bytes unchanged; exactly one run_sql appended')
CHECK
    期待する出力: existing registry bytes unchanged; exactly one run_sql appended。
手順9: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --check
    期待する出力: 指摘0。新規2ファイル全文も親へ返す。
手順10: 範囲
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --untracked-files=all
    期待する出力: 指定3ファイルだけ。差分/新規全文/静的検証結果/実PG未実施を親へ返して停止。
失敗・不明・範囲外・権限拒否があればその操作で停止し生出力を報告する。検査変更や環境偽装で通さない。
END OF CARD
