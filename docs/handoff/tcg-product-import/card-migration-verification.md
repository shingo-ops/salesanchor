# CARD-PRODUCT-MIGRATION-VERIFY-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、guards/02-db.md、guards/10-executor.md。
照合: 使い捨てCI DBのみ。本番接続・環境偽装・ガード解除なし。
受領確認を最初に返すこと。担当は検証専用実装役1名。他者の変更を戻さない。

## 許可と所有
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification
基点: 70d145f090e122dd36e4a39b4928e13cc0dae613 (PR3500後)。
所有する実装ファイルは backend/tests/test_tcg_migration_separation_pg.py の新規1本のみ。
設計根拠は /Users/tanizawashingo/worktrees/salesanchor/release-product-master-migration-design/docs/handoff/tcg-product-import/design.md の検証便V1–V6。
結果を /tmp/product-migration-verifier-result.json に保存することを許可する。
新規テスト作成・必要な限定読取・静的チェックのみを本カードで実行する。
commit/push/PRは親の差分確認後の追補カード。本番・既存migration・runner・CI・サービスコード・secrets変更は禁止。
サブエージェント追加は禁止。接続条件を外すことやGITHUB_ACTIONS偽装は禁止。

## 現在の実物に合わせた検証仕様（自己設計審査APPROVE、検証限定）
既存PG fixtureは本物のCI/localhost/jarvis_test_db/専用一時DBを要求する。これをそのまま再利用する。
V1: 本番の22制約と照合可能な構造を列挙し、初期DDLに検索/除外語unique2本がないことを実DBで検出する。
V2: 193の4FK部分、198のmark/English列追加部分を元SHA/固定境界で抽出し、CSV相当10項目編集後に2回実行して全列差0を検証。
V2追加: PR3500の現行198を実行し、非NULL編集値は維持、意図してNULLへした既存値は再充填されるか実測する。想定と違えば親へ戻す。
V3改訂: PR3500は商品名検査を除去済み。現行bundleは12対象中11名称を編集しても通ること、構造不正では失敗し当該transactionがrollbackされることを検証。旧PM0264失敗を現行期待値にしない。
V4: 205/230の元SQLで検索語9・除外語1の再追加を再現。分類193がCSV相当の分類変更を戻すことも実測する。
V4追加: 現行bundleがPM0264の除外「カードセット」を再追加する経路も、初回登録後→当該語を外す→再実行で測る。
V5: uniqueなしの初期構造と本番同等unique付き構造を別一時DBで比較し、205/232の明示conflict target成否を測る。
V6: 人工fixtureのdumpを別一時DBへ復元し、ID/全列/語順/参照/履歴が一致することを測る。実backup復元とは呼ばない。
過去と最新のSQLを混ぜない。基点の対象ファイルSHAを明記。現在コードの特性確認用テストであり、製品保全の合格とは区別する。
既存fixtureと元SQLを再利用し、無関係な全schemaのコピー定義を増やさない。
CSV相当と実CSV API往復を区別。全runnerは実行しない。検証対象のSQLのみを一時schemaへ置換して実行する。
新規DBは既存fixtureと同じ安全検査とライフサイクル。後始末目的の本番/共有DB操作をしない。
人工データは検証専用と明示。世代・分類等の意味を推測して本番データとして報告しない。
V6のclient不在/版不整合など実行条件不成立はskipせず停止・報告。勝手にCIを変更しない。
現行コードの問題を検出する試験は、その現象をassertする特性確認とする。xfail/skipで成功を偽装しない。

手順1: 受領と開始確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && ./scripts/dev/executor-preflight.sh
手順2: 基点と他者変更の確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git status --short --branch
手順3: 本カードの1ファイルだけを実装し、backend/AGENTS.mdと既存fixture・関連SQLを確認する。
手順4: 静的確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git diff --check
不明/前提違い/範囲外/ガード拒否で該当操作を停止し親へ事実と結果を報告する。
ローカルDockerが不在なのでpytestを偽装せず、実CIの実行は親の公開追補を待つ。
報告: 変更1ファイルのSHA、V1–V6の具体case名、実行した静的確認、未実行のPG試験を明確に分離。
END OF CARD

# 公開追補の前提記録

親は所有test1本を読み取り審査し、PM0276が分類補完対象外である点をPM0200へ是正、V2を空schemaから元187/192/193/198構造だけで作る試験へ補強した。V3の失敗処理も既存の明示ROLLBACKと接続状態確認に合わせる。修正版SHAの直接照合が済むまでcommitしない。公開対象はtest1本＋親所有設計8文書のみ。マージ・配備は引き続き禁止。

# CARD-PRODUCT-MIGRATION-VERIFY-PUBLISH
本公開追補の許可は初版のcommit/push/PR待機を上書きする。
受領確認後、migration_verifierが親所有8文書と自身のtest1本、下記9ファイルのみを公開する。
親はtest SHA256 4bc7e4c9e27866591f79ca77b940aa583deb4880fb6af296340cd071ac47f1eeと差分を直接確認済み。
guards/00-common.mdとguards/10-executor.mdを適用。文書内容を独断変更しない。
マージ・配備・本番接続・既存製品コード変更は禁止。想定外差分/失敗/拒否で停止して親へ報告する。
手順1: 状態を確認する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git status --short --branch
手順2: 指定ファイルのみstageする。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git add backend/tests/test_tcg_migration_separation_pg.py docs/ai-agents/evidence-registry.md docs/handoff/tcg-product-import/design.md docs/handoff/tcg-product-import/recon.md docs/handoff/tcg-product-import/migration-separation-evidence.json docs/handoff/tcg-product-import/migration-separation-inventory.json docs/handoff/tcg-product-import/card-migration-verification.md docs/specs/product-master/README.md tasks/todo.md
手順3: 状態を確認する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git diff --cached --stat
手順4: commitする。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git commit -m "test: characterize product migration replay in isolated PostgreSQL"
手順5: commit実在を確認する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git log -1 --format="%H %s"
手順6: 通常pushする。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && git push -u origin release/product-migration-verification
手順7: 正式PRを提出する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && bash scripts/gh-pr-create-safe.sh --base main --title "test: 商品CSVとmigration再実行の隔離検証（マージ対象外）" --body-file /tmp/product-migration-verification-pr-body.md
手順8: 状態を確認する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && cat .pr-number
手順9: 状態を確認する。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-migration-verification && gh pr view --json number,url,headRefOid,state
ここで親にPR URL/HEADを報告して待機する。実PG成功はCIログ確認まで主張しない。
END OF CARD

# CARD-PRODUCT-MIGRATION-VERIFY-SYNC
本追補は検証ブランチへのmain取り込みだけを許可する。PRのmainへのマージ・本番操作は禁止を維持する。
目的: PR #3502の競合とguard評価の祖先条件を解消し、実CIを起動する。
対象main: 5afb5af1ed28ea691ea93b04e4245afa8d744d85。別のHEADなら停止する。
実装役は単独ではない。他者の変更を取り消さない。製品コード・CI設定を編集しない。
手順1: preflightとgit statusを確認し、本カードのみ未commitであることを確認する。
手順2: git merge --no-commit --no-ff 5afb5af1ed28ea691ea93b04e4245afa8d744d85 を検証ブランチで実行する。
手順3: 競合パスとgit statusを親に報告して停止する。競合の文書編集は親が担当する。
既存PG fixtureに入ったmain変更は読み取り確認し、今回の9試験への影響を報告する。
本追補ではcommit/pushをまだ実行しない。
END OF CARD

# CARD-PRODUCT-MIGRATION-VERIFY-SYNC-PUBLISH
本追補は前追補のcommit/push待機だけを上書きする。mainへのPRマージ・配備は禁止。
親が文書3件の競合を双方の追記原文を一切削らず解消済み。取り込むmain SHAは前追補と同一。
実装役はgit addで競合解消3文書と本カードのみをstageし、git diff --checkを実施する。
対象test SHAとmainとの差分が当初9ファイルのみであることを確認する。main由来の製品変更は編集しない。
check-task-stateとcard-lintを実行し、成功したらmerge状態をcommitする。
commit message: chore: sync verification branch with reviewed main
通常のgit push origin release/product-migration-verificationを実施する。forceは禁止。
HEAD、PR状態、差分、検査結果を親へ報告し待機する。
END OF CARD

# CARD-PRODUCT-MIGRATION-VERIFY-REPAIR1
本追補はtest1本の検証不備修正を許可する。安全ガード/製品/CI/元SQL/期待値の緩和は禁止。
根拠: CI34806371166は3725pass/95skip/1fail、V2の360行executeでIndexError。LIKE内の%と引数schemaが混在する。
Psycopg公式usageの引数仕様（https://www.psycopg.org/docs/usage.html#passing-parameters-to-sql-queries）を確認済み。
V2のLIKEパターンを別の%s引数として渡す。期待するFK4件と編集10項目保持を変更しない。
数値ログはxdist下のcapsys.disabled出力がCIに現れなかった。emitで専用Warningを使い、pytestのwarnings summaryへ検証結果JSONを出す。
公式根拠: https://docs.pytest.org/en/stable/how-to/capture-warnings.html 。既存警告を隠す設定変更は禁止。
所有はbackend/tests/test_tcg_migration_separation_pg.pyのみ。他者の変更を戻さない。修正後ruff/format/compile/collect/diffを実施する。
親へ差分とSHAを報告して停止する。commit/pushは次の読取確認後に行う。
END OF CARD

# CARD-PRODUCT-MIGRATION-VERIFY-REPAIR1-PUBLISH
親が修正版test SHA256 99e30fc0095d89344a3c390b317104357275aa02e520b2754d5b262b408a712dと全差分を確認。
実装役のcompile/ruff/format/diff/9件collectは成功報告、実PGは未検証。
本追補は修正testと親のcard/recon/migration-separation-evidence.jsonの4ファイルのみstage/commit/通常pushを許可する。
commit message: test: fix migration verification query binding and observations
公開前にgit diff --check、card-lint、check-task-stateを通す。製品/CI/SQL変更禁止、PRのマージ・本番操作禁止は維持。
push後はHEADを親へ返して待機する。
END OF CARD

# CARD-PRODUCT-MIGRATION-VERIFY-RESULT-PUBLISH
親がCI34807228083の実ログを取得し9case成功/skip0を検算。今回の成果物は結果文書だけ。
対象はdocs/ai-agents/evidence-registry.md、docs/handoff/tcg-product-import/design.md、同recon.md、同migration-separation-evidence.json、本カード、tasks/todo.mdの6ファイル。
実装役は他者と共同作業中。test/製品/CI/元SQLを変更せず、上記6ファイルだけstage/commit/通常pushする。
事前検査はgit diff --check、card-lint、check-task-state。検証test SHA99e30fc0095d89344a3c390b317104357275aa02e520b2754d5b262b408a712d不変を確認。
commit message: docs: record isolated migration verification evidence
force/PRのmainマージ/本番操作は禁止。HEADを親へ返して停止する。
END OF CARD
