CARD-PRODUCT-NAME-SPACE-PUBLISH-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合: 実装6ファイル・実在作業場所・生報告SHA・正式カード・公開承認・通常wrapperを照合。L32自己確認。

承認と目的
POへの質問「製品PRを作成してCIで正式検証を進めてよいですか？」への原文「進める進める」を受領。
既存担当/root/csv_card_executorが6製品ファイルを保存し、設計根拠を添えて製品PRを公開、既存CIの正式pytest/隔離PGを確認する。

許可
対象6ファイルのcommit/push/PR、通常CI読取、実装に由来する失敗を6ファイル内で修正/再検査/再公開。
文書PR3466の確認済み版d11d27b7bd418c42186a3d000c3377556f613759に含む17文書差分を履歴ごと取込可。
その17ファイルは同版のorigin/main起点差分で確定済み（docs配下16とtasks/todo.md）。内容の再設計・新規加筆はしない。
最新origin/main取込可。台帳末尾の追記競合は双方の全文を保持する連結だけ許可。その他競合は設計担当へ戻す。
既存mainの空箱/状態再解析の保護は保持する。新規追加の検査前提が必要ならまず現物を照合し、6ファイル外の修正が必要なら停止。
PR本文は既存書式で組み立て可。GOは未受領とし、GO記録・代理GOを作らない。

禁止
main/developの直接変更、マージ/本番反映、DB/本番アクセス、データ登録/更新、再解析/配信、secrets/CI/運用スクリプト変更。
新規エージェント、他者差分の上書き、fixture安全条件の緩和、skip追加、検査無効化、ローカルGITHUB_ACTIONS偽装は禁止。
製品修正は下記6ファイルだけ。文書取込は上記固定版17ファイルだけ。その他の台帳/根拠更新は親が行う。

停止と報告
作業場所/初期SHA不一致、未知の未保存変更、権限拒否、秘密露出、範囲外/設計矛盾は該当操作を停止し生出力を親へ返す。
GO未記録によるprocess-artifacts gate失敗は予期した承認待ちとして記録し、他の通常CIの観測は続ける。GOを創作して通さない。
commitの後は実在を確認してからpush。失敗を成功と扱わない。
報告先 /tmp/reports/CARD-PRODUCT-NAME-SPACE-PUBLISH-01.txt を排他的新規作成し、全出力/終了コード/開始終了を直接追記する。秘密は[REDACTED]。
既存の実装報告を上書きしない。ローカルpytestはDocker接続不可のため実施せず、正式CIの実ジョブ結果を確認する。

受領確認
「CARD-PRODUCT-NAME-SPACE-PUBLISH-01を受領。6ファイルをPR公開しCIを確認します。マージ・本番変更は行いません。」

手順1 報告作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && python3 -c 'from pathlib import Path; Path("/tmp/reports/CARD-PRODUCT-NAME-SPACE-PUBLISH-01.txt").open("x").close()'
手順2 事前確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && ./scripts/dev/executor-preflight.sh
手順3 差分確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git status --short --untracked-files=all
期待値: 次の6ファイルのみ。初期実装SHAを /tmp/reports/CARD-PRODUCT-NAME-SPACE-PUBLISH-01-sha.json と照合する。
- backend/app/services/tcg_analyzer_svc.py
- backend/app/services/tcg_keyword_lint.py
- backend/tests/test_tcg_keyword_matching.py
- backend/tests/test_tcg_keyword_lint.py
- backend/tests/test_tcg_product_guards.py
- backend/tests/test_tcg_work_matching_integration.py
手順4 実装保存
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git add backend/app/services/tcg_analyzer_svc.py backend/app/services/tcg_keyword_lint.py backend/tests/test_tcg_keyword_matching.py backend/tests/test_tcg_keyword_lint.py backend/tests/test_tcg_product_guards.py backend/tests/test_tcg_work_matching_integration.py
手順5 コミット
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git commit -m 'fix(tcg): match complete Japanese product names across spaces'
手順6 コミット実在
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git log -1 --oneline
手順7 承認済み設計取込
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git merge --no-edit d11d27b7bd418c42186a3d000c3377556f613759
文書17ファイルを含む履歴取込。最新mainへ入っている他担当の製品変更を消さない。
手順8 最新取得
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git fetch origin
手順9 最新main取込
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git merge --no-edit origin/main
台帳の単純追記競合だけは許可範囲で解消しcommitする。製品の意味が変わる競合は停止して親へ戻す。
手順10 範囲と静的検査
mainとの最終差分を確認し、6製品+固定版17文書以外があれば停止。6ファイルの新規差分以外のmain内容を不変確認。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend && PATH="/Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl/backend/.venv/bin:$PATH" make lint-ci
4テストruffも既存venvで再確認可。CSVは規定BOM/CRLFの保存証拠なのでdiff --checkのCR検出と他文書/製品の不正空白を区別する。
手順11 公開
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && git push -u origin HEAD
手順12 PR本文
/tmp/reports/CARD-PRODUCT-NAME-SPACE-PUBLISH-01-body.md を作成する。書式組立を許可し、実在する設計/recon/ADR154/113/親仕様product-masterを参照。
問題は完全商品名の空白差で未確定になること、変更は通常一致優先+追加完全一致+共有候補選択+R5の意味合わせ。
触るファイル/削除するファイルは実diffから全列挙。PO設計/実装/公開承認、読取審査、ローカル静的検査、未実施の正式CIを区別。
空箱/状態再解析の既存main変更維持、B便の商品データ更新/44登録対象外、マージGO未受領を明記する。
手順13 正式PR
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && bash scripts/gh-pr-create-safe.sh --base main --title 'fix(tcg): 商品名全体のスペース差を限定して照合' --body-file /tmp/reports/CARD-PRODUCT-NAME-SPACE-PUBLISH-01-body.md
手順14 番号照合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && cat .pr-number
gh pr list --head release/product-name-space-match-impl --limit 3 --json number,url,headRefName と照合する。
手順15 正式CI
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-name-space-match-impl && gh pr checks
進行中は状態を確認し、当該PRの実backend pytest/PGの件数・失敗・skip・HEAD・coverageを生ログで確認する。
失敗詳細の通常読取経路と、同じ6ファイル内の実装/テスト誤り修正・静的再検査・commit/push/CI再検査を許可する。
CI設定/共通fixture/migrationの変更が必要なら停止して親へ戻す。GO待ちと技術検証失敗を区別する。
手順16 引き継ぎ
PR URL/最新HEAD/技術CI結果/GO待ち/6製品差分の変更有無/文書取込/生報告を親へ返す。マージしない。
END OF CARD
