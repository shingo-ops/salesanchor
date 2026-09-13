本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-BASE

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 製品commit3250e829を親確認済み。最新main7dcb9ce9は別便の商品辞書/比較処理と正式台帳更新を含む。登録ファイルの先行2行追加は自分の末尾1行と競合しないが、根拠台帳末尾の競合をgit merge-treeで実測。未公開の自ブランチを最新mainへ追従する必要がある。現在の製品コードは同一hashのまま保持し、競合時は親が文書だけを解決する。
受領確認: 同じ担当・作業台・未公開自ブランチの追従だけであることを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 未公開の自ブランチを指定mainへrebaseして既存の承認済み変更を取り込む。手書きの製品/文書変更はしない。別便のコードの再設計はしない。
禁止: 他ブランチ操作、force push、通常push/PR/merge、本番/DB実行、拒否負例保存、permit発行、ガード変更。競合を自動でours/theirs選択しない。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ・未保存0。
手順3: 基点
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git show -s --format='%H %s' 7dcb9ce982af39b3b6ef9c1089fe1255952ae37a
    期待する出力: PR3474のmainマージ済みコミット。
手順4: 追従
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git rebase 7dcb9ce982af39b3b6ef9c1089fe1255952ae37a
    期待する出力: 成功または文書競合。競合/失敗は停止し、そのファイルと生出力を親へ報告。自己解決・continueしない。
手順5: 成功した場合の確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 未保存0。HEADを報告して停止。
END OF CARD
