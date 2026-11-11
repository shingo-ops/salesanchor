branch: release/merge-queue-bin0-cards

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/merge-queue-bin0-cards | 便0（下準備）の作業指示書: 順番待ちの列へ移る前の workflow・台本の手当て（docs のみ） | 2026-11-11 | IN_PROGRESS | | | 設計 docs/handoff/merge-queue-org/design.md・PO 承認済み(2026-11-11)。カードA #5379 合流済(2026-11-11)。カードB1 card-bin0-b1.md 追加・#5381 合流済(2026-11-11)。B1 #5381: card-bin0-b1.md:7「危険便: いいえ」は誤記（process-artifacts-gate.yml は scripts/check-process-artifacts.js:1030 の DANGEROUS_PATTERNS に当たり GO記録が要った）→以後のカードは DANGEROUS_PATTERNS(:1023-1041)を照合して危険便を書く。#5380 で test.yml・e2e.yml・schema-check.yml・migration-test.yml・karte-gate.yml が変わったので、カードB2 は新しい origin/main を変更前として書く。B2 でまとめ役の workflow に merge_group を足すときは scripts/ci/check_ci_aggregators.py の真理値表（:199-200 が pull_request と workflow_dispatch だけ）に merge_group を足すかを決める（#5381 審査役の気付き）。U21 gitleaks は PO 2026-11-11「1」で本体を直接動かす形に決定（design §5-1・§5-2・カードB3） |
