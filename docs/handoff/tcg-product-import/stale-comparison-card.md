# CARD-STALE-WORK-COMPARE-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
状態: 実装役への引き継ぎ用。設計担当は製品を変更せず、実装役/agentを自動起動しない。
受領確認: CARD-STALE-WORK-COMPARE-01。開始HEADを報告する。
読んだ節: guards/00-common.md、guards/03-file.md、guards/05-pr.md。照合: 対象3ファイル、origin/main起点、ready PR、宛先、期待出力、停止条件を記載済み。
根拠: docs/handoff/tcg-product-import/design.md §25、recon.md、refresh-schema-20260914.json、refresh-pilot-design-proof.json。mode: handoff、ADR-113/ADR-154。
設計審査は同一AIの自己審査。A便非採用比較のみAPPROVE。採用B便/本番再解析全体はREVISE。
目的: 完了済み旧参照1ジョブ7明細を保持し、最新作品判断を本番へ採用せず比較する。
責任: 実装担当は明示指定後に着手する。他者と共同のリポジトリであり他者の変更を戻さない。
対象はbackend/app/services/tcg_work_comparison_svc.py、backend/tests/test_tcg_work_comparison.py、backend/tests/test_tcg_work_comparison_pg.pyの3ファイルのみ。
許可: 上記実装・人工モデル/隔離DB試験、既存design/recon/台帳への検証記録、専用ブランチcommit/push、ready PR起票。
禁止: 通常解析ガード/旧比較入口変更、migration/CI/運用スクリプト/認証/secrets変更、本番DB書込、実モデル呼出し、シート配信、PRマージ、agent追加起動。
実モデル比較は実装と正式CIの結果を設計担当へ返した後、先行1回を別の実行手順で具体化する。本カードから自動実行しない。
手順1 事前確認
現在のルール/preflight/台帳・最新mainを確認し、origin/main起点release/stale-work-comparison専用作業場所を公式手順で作成する。
期待する出力: 開始HEAD、対象ファイルの占有/未保存変更なし。衝突時は担当へ戻す。
手順2 実装
design§25-3のread_job_snapshot/compare_stale_job_snapshotを追加。完全性と現在との差を分け、旧ガードを維持。7件/1ジョブ上限、訂正ありは全体停止、常にadoptable=false/db_writes=0。
期待する出力: 旧参照比較結果、入力指紋、保存/診断/新判断を区別し、生原文と応答は公開ログへ出さない。
手順3 検証
design§25-4の9群を人工モデルで確認し、既存unit/PG回帰を実行。DockerがなければローカルDB試験は行わず、正式CIの既存PostgreSQLで必須試験を行う。
期待する出力: 余剰/欠落/重複ID0、RAW/ID/DB全表変更0、旧入口拒否維持、失敗再試行0、必要試験skip0。失敗時は条件を緩めず原因と出力を返す。
手順4 保存とPR
差分が3対象と必要文書のみであることを確認し、git diff --checkと正式カード/台帳チェックを実施。正規gh-pr-create-safe.shでbase mainのready PRを作成する。
期待する出力: PR番号/HEAD、実行した検証と他者報告を分離した結果、自己審査/独立レビューの区別、失敗/未実施事項。
完了報告先はPOと設計担当。PR起票と検証報告までで停止し、本番への採用成功とは報告しない。
END OF CARD
