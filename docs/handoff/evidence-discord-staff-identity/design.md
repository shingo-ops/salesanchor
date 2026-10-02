# design: PO 本番確認の証跡台帳記録

対象ADR: 該当なし
recon: docs/handoff/evidence-discord-staff-identity/recon.md

## 変更
docs/ai-agents/evidence-registry.md の末尾に Entry Template 書式で2エントリを追記（既存行は変更しない）。

## 触らない範囲
コード、migrations、scripts、workflows、既存の台帳エントリ。

## 受け入れ基準
|基準|検証方法|
|---|---|
|既存行の変更・削除が0|`git diff origin/main...HEAD --numstat` の削除行が0|
|2エントリが Entry Template の全キーを持つ|目視（id/date/agent/task/scope/evidence/confidence/tradeoff/decision/follow_up）|
|未確認の #3885 を確認済みとして書いていない|台帳内の #3885 記述が「未確認」|

## 外部事例
該当なし（社内の証跡台帳への追記のみ。既存の同形式エントリに倣う）。

## 戻し方
当該PRを revert。
