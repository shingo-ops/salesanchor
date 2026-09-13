本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-SUBMIT-01

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: commit0c90de21の4ファイルは親がhash検算済み。PR本文は実在する固定ファイルを用いる。受領確認としてカードID・作業台・push/PRだけの範囲を返す。
担当: 同じstock_contract_01。他者と共有しているため他者の変更を戻さない。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract
ブランチ: release/line-stock-contract
許可: 読み取り、当該ブランチpush、main向け製品PRの提出、正規wrapperによる.pr-numberと自ブランチ台帳PR番号の自動登録。
禁止: 製品/設計/CI/scripts/DB/secretsの編集、新commit、独自のGO記録、merge/本番、第2便実装、新規エージェント。他者の変更を戻さない。
親は本カードと検証文書をcommitしてから渡し、受領後は編集しない。
手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: clean確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git status --short --branch
    期待する出力: release/line-stock-contractで未保存変更0。
手順3: 保存内容の実在
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git log -3 --oneline
    期待する出力: 親の検収文書commit、製品0c90de21、文書6c58d1c6。この順序が異なる場合は停止。
手順4: push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git push -u origin HEAD
    期待する出力: release/line-stock-contractへのpush成功。
手順5: remote実在
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git ls-remote origin refs/heads/release/line-stock-contract
    期待する出力: 手順3のHEADと一致。
手順6: PR提出
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && bash scripts/gh-pr-create-safe.sh --base main --head release/line-stock-contract --title 'feat(tcg): add source-grounded stock evidence and quantity components' --body-file /private/tmp/line-stock-product-pr.md
    期待する出力: main向けPR URLと.pr-number登録成功。本文の独断編集やGO作成は禁止。
手順7: PR実在検算
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && gh pr list --head release/line-stock-contract --state open --json number,url,headRefOid,baseRefName
    期待する出力: 1件、headがpushしたSHA、baseがmain。.pr-numberと番号一致を次で確認する。
手順8: 登録確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && cat .pr-number
    期待する出力: 手順7と同番号。ここで停止して親へURL/HEAD/各出力を返す。
失敗・不明・権限拒否・範囲外があればその操作で停止し生出力全文を親へ返す。自力で許可やGOを作らない。CIは親が読取確認し、番号付きGO未受領を回避しない。
END OF CARD
