---
mode: handoff
---
CARD-PMG-ATTEMPT-RECORD-FIX-04
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、05-pr.md、07-migration.md、11-lint.md。
照合: PR3504所有権、番号付きGO、本便2製品のSSOT維持、CIと正式merge窓口。
受領確認: カード名をrootへ返す。rootの交付で実行開始。
担当error_visibility_recon。rootが文書と本番read-only確認を所有。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix
他者と共用しているため、他者の変更を戻さず、本便文書以外をstageしない。
根拠: PO本人原文「GO #3504」。承認時HEAD47f72ab3674eba06e28f1cef86b1757986995750。
技術検証: 正式Backend3746成功/95skip、coverage65.07%、実DB移行成功、別担当レビューAPPROVE。
許可: 本便承認記録文書のみcommit/push、PR本文更新、確認コメント、CI照合、正式merge commit、自動deploy読取監視。
製品コード/試験/CI/運用script/secretsの変更、本番手動DML/再抽出/配信、admin/force/guard迂回は禁止。
手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && ./scripts/dev/executor-preflight.sh
期待する出力: 正常。失敗なら理由をrootへ報告。
手順1
本カード交付直後は待機。rootがGO/backup/根拠を既存recon/evidence/todoへ保存し、明示してから次へ。
許可するcommit対象は上記3文書とcard-attempt-record-ci-fix.md、本カードの5ファイルだけ。
reports/attempt-integrity-local-validationは非公開のまま保護する。
手順2
指定5文書のdiff確認、正式card-lint/task-state/diff検査後、通常commit/push。
製品2/試験1のhashが47時点と同一であることを確認し、HEADをrootへ返す。
手順3
既存PR本文をbody-fileで更新。GO4要素はrootの記録を逐語転記、最新検証を正確に反映。
未受領/未実施の古い記載は現在の状態へ更新。削除ファイル欄は既存gateの定義と実差分で照合。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && gh pr checks
期待する出力: 最新HEADで必要CI成功。pending/skipを成功と捏造しない。
手順4
rootが最新HEAD/CIとbackup確認済みの開始合図を返すまでmergeしない。
合図後、実HEADが承認済みと一致するか再確認。main前進/差分増加/失敗はrootへ報告して停止。
PRに確認済みコメントを残し、正式窓口でmerge commitする。ブランチ削除指定は使わない。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && bash scripts/gh-pr-merge-safe.sh --merge
期待する出力: merge成功。自動cleanupの安全検査は維持、未保存ログを強制削除しない。
手順5
GitHub APIでmerge SHAと自動deployの対応HEAD/jobを照合。通常deployの成功とbackup生成を読取確認。
失敗は操作/ログの根拠とともにrootへ報告、手動配備/迂回はしない。
結果: PR/HEAD/merge SHA/CI/deploy job/backup/残件をrootへ返す。
END OF CARD
