---
mode: handoff
---
CARD-PMG-ATTEMPT-RECORD-FIX-02
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、05-pr.md、07-migration.md、11-lint.md。
照合: 本便所有権、公開前差分検収、正式PR窓口、未受領番号付きGOの扱い。
受領確認: カード名をrootへ返す。rootの明示交付まで実行しない。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix
担当error_visibility_recon、他者の変更を戻さない。rootが文書を所有する。
前提: 別担当コードレビューAPPROVE、製品/試験freeze hashとRuff/diff検査をrootが検収済み。
ローカルPGは専用環境容量不足予防で中断・未完了。PR提出で正式CI全体試験を実行し、その完了を必須とする。ローカル未完了を合格と記載しない。
本カードは本便の明示対象のみcommit、通常push、PR起票、CI検証まで。
公開先は既存origin shingo-ops/salesanchor（公開repo）。顧客原文/secret/本番ログは含めない。
対象: backend/app/services/tcg_extraction_record_svc.py、migrations/20260914_010000_tcg_extraction_attempts.sql、backend/tests/test_tcg_extraction_record_integrity_pg.py。
既存PG試験に本便修正がある場合のみbackend/tests/test_tcg_extraction_record_pg.pyも対象。
文書: docs/adr/ADR-154-tcg-parity02-gas-python-migration.mdと生成索引、既存PMG design/recon、evidence-registry、tasks/todo、FIX01/02カード。
根拠: reports/pr3494-evidence-20260914のREADME/結果txt3/structure-expected.jsonだけ。
追加文書や本番照会スクリプト/ログの公開は禁止。対象外があればrootへ報告。
手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && git status --short
期待する出力: 本便対象のみ。
手順1
許可対象を個別にstageし、cached diffと対象一覧をroot最終検収と照合して通常commit。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && git log -1 --oneline
期待する出力: 本便commit。失敗時にhookを外さない。commitを確認後に次へ。
手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && git push -u origin release/attempt-record-integrity-fix
期待する出力: 正常push。forceは使わない。拒否時は理由をrootへ報告し停止。
手順3
/private/tmp/pmg-attempt-integrity-pr.mdにPR本文を作成。問題/結果/SSOT/実行した試験と限界/標準様式を記載。
触る/削除するファイルは実差分から記載。GO原文・バックアップ確認を捏造しない。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && bash scripts/gh-pr-create-safe.sh --base main --title 'fix: 抽出試行の構造検証と容量超過記録を補強' --body-file /private/tmp/pmg-attempt-integrity-pr.md
期待する出力: 本便PR URLと正式番号登録。draftにしない。
手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && cat .pr-number
期待する出力: 正式登録番号。
手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && gh pr checks
期待する出力: 最新HEADのCI状態。pending/skipを試験成功に換算しない。
CI失敗が本便の形式/実装由来ならCARD01範囲の修正候補をrootへ報告、検収後に通常更新。
マージ/本番変更/再抽出/配信/新GO作成/承認ゲート迂回は禁止。
PR番号・HEAD・CI結果・残件をrootへ返して停止。
END OF CARD
