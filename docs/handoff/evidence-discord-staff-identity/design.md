# design: PO 本番確認の証跡台帳記録

対象ADR: ADR-136（GO手順の対象外・台帳追記のみ）
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

## 外部・過去事例の参照と我々への応用
社内の既存エントリ EV-20260929-AU-ALL-BUTTONS（docs/ai-agents/evidence-registry.md）の書式に倣い、事実と未確認を分けて記録する。外部事例は該当なし（台帳への追記のみ）。

## 戻し方
当該PRを revert。

## 維持の仕組み
台帳の Entry Template（docs/ai-agents/evidence-registry.md:7-20）を書式の正とし、PO確認の都度追記する。
守り手: 人手で守る（PO確認の都度、実行役が追記するため）
