CARD-PRODUCT-CSV-ATOMIC-IMPL-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、10-executor.md、11-lint.md。
照合: 実在する専用worktree/HEAD/preflight/設計SHA/4ファイル境界を親が直接確認。L32自己照合済み。
受領確認: 「CARD-PRODUCT-CSV-ATOMIC-IMPL-01を受領。承認された4ファイルの実装とローカル静的検査を行います。」

承認と担当
PO原文「進める」を受領。design§20の方式採用と4ファイル修正を既存/root/csv_card_executorへ委任する承認。
担当は既存/root/csv_card_executor。設計担当は文書と読取レビューを行う。新規エージェント/別セッションは起動しない。
他者も同じリポジトリで作業している。他者編集を戻さず、衝突は親へ報告する。

許可と禁止
手順内の4製品ファイル実装・試験追加・範囲内失敗の修正と、必要な既存コード/テスト/公式資料の読取を許可。
文書/台帳/GO記録は親が担当。commit/push/PR作成/PR本文更新/マージは禁止。
DB/本番接続、商品値/CSV変更、再解析/配信、CI/依存lock/運用script/secrets/ガード/認証設定変更は禁止。
backend/.venvへの既存依存導入と/tmpの一時検証資料は許可。環境変数一覧や秘密を出力しない。

停止条件
初期status非空、基点/設計SHA不一致、先約/他者変更、範囲外修正、仕様矛盾、権限拒否は停止して親へ報告。
4ファイル内の実装由来失敗は自力修正可。既存問題は勝手に範囲を広げず親へ返す。
親がDocker daemon未稼働を確認済み。本カードでpytest/実PGを実行しない。通常CIはPR提出許可後へ引き継ぐ。
GITHUB_ACTIONS偽装、PG fixture条件の緩和、追加PGのskip化、外部DB代用は禁止。

報告
/tmp/reports/CARD-PRODUCT-CSV-ATOMIC-IMPL-01.txt を排他的新規作成。パスはそのまま使い、既存なら停止。
全コマンド出力/終了コード/開始終了を直接追記し、10MB超は停止。秘密は[REDACTED]。
停止時は手順、コマンド、終了コード、最後の生出力を親へ返す。未実行試験を成功にしない。

手順1 報告作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && python3 -c 'from pathlib import Path; p=Path("/tmp/reports/CARD-PRODUCT-CSV-ATOMIC-IMPL-01.txt"); p.parent.mkdir(parents=True,exist_ok=True); p.open("x").close()'
手順2 初期状態
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && git status --short --untracked-files=all
期待値空。branchはrelease/product-csv-atomicity。
手順3 基点
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && git rev-parse HEAD origin/main
期待値は両方1a8eed69a8d4e1c17cefc7dcef579f63493b17dd。別SHAなら親へ戻す。
手順4 preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && ./scripts/dev/executor-preflight.sh
手順5 規則/設計
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && cat AGENTS.md backend/AGENTS.md
読取設計: /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-registration-preflight/docs/handoff/tcg-product-import/design.md
SHA256: 0806d0eb64d9d81c364f871e84e75952012794b851585952823d011457e5a8f6
§19は課題証拠、§20全体が実装契約。§20-7はPO承認。SHAを照合してから実装する。
同じフォルダのrecon、keyword-import-atomic-design-evidence.json、keyword-import-partial-audit.json/.py.txtを読取可。
Context7利用不可は親が確認済み。ライブラリ仕様確認は設計記載の公式資料/使用版2.0.38公式ソースへ代替アクセス可。
手順6 既存依存
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity/backend && /usr/local/bin/python3.12 -m venv .venv
手順7 依存導入
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity/backend && .venv/bin/python -m pip install -r requirements-dev.txt
手順8 忠実実装
許可4ファイル:
- backend/app/services/tcg_product_master_svc.py
- backend/app/services/tcg_product_import_svc.py
- backend/tests/test_tcg_product_import.py
- backend/tests/test_tcg_product_import_atomicity_pg.py
create_product/record_rowのkeyword-only commit: bool = Trueを追加。Trueは既存動作、Falseは内部commit0。
CSV正常行だけ商品/全語/確認/created履歴を同じsessionで未確定保存し、callerのcommit1回で確定する。
ValueErrorを行errorにして続行する捕捉範囲はcreate_productだけ。rollback成功後にerror履歴を別途確定する。
履歴INSERT/commitのValueErrorを上記へ混ぜない。SQL例外/取消/rollback失敗は成功扱いせず停止、元の原因を保持する。
created/skippedは当該履歴/商品確定の成功後に加算。commit応答不明は自動再送せず、rollbackで未保存と断定しない。
単品router/force/採番/既存分類・解析制約/返却型を維持。4ファイル外へ実装を広げない。
C1–C11に対応する試験を追加。実PGは既存work_matching_integration.pgの一時DB/別接続を使う設計に従う。
実テストコードに隔離条件と実体/語/履歴の照合を入れ、追加skipで通さない。DBはこのカードでは起動しない。
手順9 静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity/backend && PATH="/Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity/backend/.venv/bin:$PATH" make lint-ci
手順10 変更試験のruff
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity/backend && .venv/bin/ruff check tests/test_tcg_product_import.py tests/test_tcg_product_import_atomicity_pg.py
手順11 差分検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && git diff --check
手順12 範囲
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && git status --short --untracked-files=all
手順13 結果
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-atomicity && git diff --stat
4ファイルのSHA、C1–C11対応箇所、実行検査/未実行pytestと実PG、生報告パスを返す。新規ファイルもSHA/範囲に含める。
親が読み取りレビューを行う。PR直前停止を維持し、製品commit/push/PR提出は行わない。
END OF CARD
