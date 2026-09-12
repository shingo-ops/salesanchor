CARD-PRODUCT-CSV-PUBLISH-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、05-pr.md、09-gh.md、11-lint.md。
照合: 実在worktree、8製品ファイルの既存差分、設計文書4本の取込、commit実在確認後push、PR番号照合、GO未発行を保持。

目的
POが「製品PR作成とCI検証」の次手に「進める」と指示した。実装済み8ファイルを保存し、承認済み設計文書4本をPRに添えて公開する。

出力の置き場
/tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01.txt。最初に排他的新規作成し、全操作の生出力と終了コードを直接追記する。
コマンド文字列に規則やログ本文を埋め込まない。REDACT: 認証情報/秘密の実値を [REDACTED] に置換し、秘密値自体を読み取らない。

禁止
マージ・本番変更・GO創作・保護設定/CI/運用スクリプト変更・新規サブエージェント。公開とCI確認だけを行う。
製品修正は設計§15/AC1〜7を満たすための同じ8ファイル内に限定。公開前に理由と必要検査を親へ報告する。
他者の変更は戻さない。独断の再設計禁止。HTTP/DB試験を未実行のまま成功としない。

停止条件
権限拒否、範囲外変更、製品競合、秘密露出、設計不一致は該当操作を停止し親へ生出力報告。
文書だけのmain追従競合は双方の独立追記を保持する解消を許可。判断不能なら停止。
GO記録待ちのCI失敗は予期される承認待ちとして区別し、GOを作成せず他の検査を確認する。

受領確認
「CARD-PRODUCT-CSV-PUBLISH-01を受領。製品PR公開とCI確認を行い、マージ・本番変更は行いません。」

手順1 報告作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && python3 -c 'from pathlib import Path; Path("/tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01.txt").open("x").close()'

手順2 既存差分確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git status --short --untracked-files=all
既存差分は前便の8製品ファイル。前便のparent-review.jsonのSHA256と照合する。相違は親へ戻す。

手順3 preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && ./scripts/dev/executor-preflight.sh
成功後に続行する。

手順4 製品の保存
design§15の8ファイルだけをgit addし、git diff --cached --check後にコミットすることを許可する。
前便検証は単体13/E2E7/build/check:all/lint-ci/対象Pythonruff成功。対象HTTP/DB試験は未実行。
コミットフックの範囲内指摘は同じ8ファイルで修正可。依存や他者ファイルを巻き込まない。

手順5 コミット実在
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git log -1 --oneline
コミット出力と一致を確認して次へ進む。

手順6 最新mainの取得
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git fetch origin

手順7 追従差分の確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git diff --name-only HEAD..origin/main
実装差分の逆方向表示をmainの追加と混同しない。merge-baseからorigin/mainの追加差分も確認する。
事前確認ではmain追加はLINE委任の文書4本のみ。製品に新変更があれば停止して設計照合を親へ依頼する。

手順8 main追従
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git merge --no-edit origin/main
製品競合は停止。実装8ファイルに予期しない変更がないことを親のSHA256と照合する。

手順9 レビュー済み設計文書の取込
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git restore --source origin/release/product-import-template-design -- docs/handoff/tcg-product-import/design.md docs/handoff/tcg-product-import/recon.md docs/handoff/tcg-product-import/card-template-impl.md docs/handoff/tcg-product-import/card-publish.md
上記4本だけをgit add/commitして根拠を製品PRへ添える。入力元は承認済み設計§15と実装報告であり実装変更ではない。
台帳とevidence-registryは設計担当が元の文書PRで更新するため取込不要。

手順10 保存の実在
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git log -3 --oneline
未保存差分0と、mainとの差が8製品＋4文書の12ファイルだけであることを確認する。

手順11 公開
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git push -u origin HEAD
終了0とremote HEAD一致を確認して次へ進む。

手順12 PR本文作成
/tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-body.mdを新規作成する。本文書式の組立は既存正規規則に沿って許可する。
内容: CSV空テンプレート＋日英入力説明、User属性修正、既存認証/DB/再送制御不変、design§15、対象8製品＋4文書、実行した検査とHTTP/DB未実行を記載。
GO欄は作らない。マージ承認待ちとする。scope/削除行を含む変更ファイルをgit diffで確認し本文に正確に列挙する。

手順13 正式PR作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && bash scripts/gh-pr-create-safe.sh --base main --title 'feat: 商品CSVの空テンプレート保存と登録者情報修正' --body-file /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-body.md

手順14 PR照合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && cat .pr-number
gh pr list --head release/product-import-template-impl --state open --limit 5 --json number,headRefName,url を同じcd接頭辞で実行し番号一致を確認する。

手順15 CI確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && gh pr checks
待機中は継続して確認し、成功・失敗・skip・GO待ちを区別する。全必須成功と偽らない。
CIの失敗詳細が必要な場合、当該PRの証拠に限定した通常読取経路のみ使用。拒否時は迂回せず親に生出力を渡す。
HTTP/DB回帰のCI結果と最新HEADを親へ報告する。修正が必要なら同じ8ファイル内で修正・該当検査・コミット/公開を許可し、理由と結果を記録する。

報告様式
PR URL、最新HEAD、CI成功/失敗/未実施、変更ファイル数、生報告パスを返す。停止時は手順/要求/生出力を優先する。
END OF CARD
