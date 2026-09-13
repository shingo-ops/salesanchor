本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-COMMIT

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: 原文削除負例の保存ガード拒否を維持。残りの3ファイルは親が読取照合し、担当の静的検査成功と親のhash/定義コピー0確認が揃った。実PG未実施・全体検収はREVISE。既にPOが委任したPR/CI検証へ進むため、未完了を明記して現物をコミットする。本カードではpush/PRしない。

受領確認: カードID・同じ作業台・3ファイルのコミット限定を返す。
担当: 同じstock_contract_01。新規エージェント禁止。他者と共同作業中。他者の変更を戻さない。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 指定3ファイルの既存内容・hash確認、stage、commit、結果の読取。
禁止: 製品/文書/台帳の新規編集、拒否負例の保存、permit発行、DB実行、push/PR/merge/本番操作、ガードやチェックの変更。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --untracked-files=all
    期待する出力: scripts/run_all_migrations.sh変更、新SQL/新試験の未追跡の3件だけ。
手順3: 同一性
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && shasum -a 256 migrations/20260913_230000_tcg_stock_projection.sql backend/tests/test_tcg_stock_schema_pg.py scripts/run_all_migrations.sh
    期待する出力: 順に0c68042e6de9b2c205916cf7f8c2f9d138dbe845e74a6d38c2b0a7204f783efa、ec921a76d83e7011eb0a95dac6ee8ff97a5b153587c7a982890b87c54359cfab、742055fec3ccc17227ff1ce48a00a02ccd7be7bf47fd05867bc08fb9c6b0c7dc。
手順4: stage
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git add migrations/20260913_230000_tcg_stock_projection.sql backend/tests/test_tcg_stock_schema_pg.py scripts/run_all_migrations.sh
    期待する出力: exit0。
手順5: 範囲
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --stat
    期待する出力: 指定3ファイルだけ。SQL823行/試験456行/登録1行の追加。異なれば停止。
手順6: 形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --check
    期待する出力: 指摘0。
手順7: commit
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git commit -m 'feat: add stock projection storage pending PG acceptance'
    期待する出力: 成功。hook拒否なら停止、迂回しない。
手順8: 確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format=fuller --stat
    期待する出力: 今回の製品3ファイルのみのコミット。
手順9: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 未保存変更0。HEADと検査結果を報告し停止。

停止条件: hash/範囲不一致、検査失敗、権限拒否、契約不明。失敗した操作と生出力を返す。実PG・原文削除拒否の未検証を合格へ読み替えない。
END OF CARD
