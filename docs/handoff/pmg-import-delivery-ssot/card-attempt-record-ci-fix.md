---
mode: handoff
---
CARD-PMG-ATTEMPT-RECORD-FIX-03
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、05-pr.md、11-lint.md。照合: 同じ試験fileのみ・定義SSOT・ガード不変更。
受領確認: カード名をrootへ返す。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix
担当error_visibility_recon。他者/rootの未commit文書とログをstageしない。
根拠: test-schema-dup gateの既存scriptが新testの補助親表DDL2箇所を0→2で拒否、rootもjobログ確認。
許可file: backend/tests/test_tcg_extraction_record_integrity_pg.pyのみ。製品2file/CI/guard変更禁止。
手順0
既存provisionでtenant_baseline/tenant_foreignの正規親表を作成する。独自DDL2箇所を除き、必要な合成データは正規列/親関連に従い準備する。
実在のsource fixture/DDLを照合して必要列を埋める。制約を外す・検査回避の別名へする・外部schema参照否定試験を削ることは禁止。
手順1
既存schema-dup検査、Ruff個別、diff --checkを実施。ローカルDockerは終了済みなのでpytest未実行を合格にしない。
製品hash2件不変・試験差分をrootへ返して編集停止、read-only再レビューを受ける。
手順2
root検収APPROVEを受けてから、当該test1fileのみstage/通常commit。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && git log -1 --oneline
期待する出力: 本便修正commit。
手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && git push origin release/attempt-record-integrity-fix
期待する出力: 同PRへの通常更新。force/ガード解除なし、拒否はrootへ報告。
手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-attempt-record-integrity-fix && gh pr checks
期待する出力: 新HEADの正式CI。実PG/Backend全体結果を待ち、他の本便不具合が出たら根拠をrootへ返す。
マージ/本番変更/GO原文作成は禁止。本カード自体とroot文書3件/追加ログは公開しない。
END OF CARD
