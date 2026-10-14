# Phase 3 設計 — routine-doc-ai-registration

**対象ADR**: ADR-1011  
**recon**: docs/handoff/routine-doc-ai-registration/recon.md  
**日付**: 2026-10-14  
**担当**: Opus（設計）／Sonnet（実装）

---

## 外部・過去事例の参照と我々への応用

- 該当なし：既存の手順書を、確認済みの現状に合わせて直すだけの書類変更のため、外部事例の参照は不要と判断

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 「指示文（ここから下を貼る）」より下が1文字も変わっていない | origin/main 版と本ブランチ版の、見出し以下を diff して差が空であること（作業時に確認済み） |
| 登録手順の見出し・登録者・版・K15・登録済みの事実・止め方・確認状況が現状に合っている | `docs/handoff/design-approval-ticket/routine/ROUTINE.md` を読んで PO が ○× 判定 |

---

## 技術 How・KPI

- KPI: 指示文より上の古い記述 0 件、指示文より下の変更 0 文字
- 技術選択: 文書の部分置換のみ

---

## 弊害・トレードオフ

- 指示文を変えると登録済みの指示文とずれる → 対策: 指示文より下は変更しない

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | ROUTINE.md の冒頭〜確認状況欄を修正 | Sonnet |

---

## 維持の仕組み

- 守り手: 週次保守（id 5d459653）。ROUTINE.md の指示文を使って実行する
- 対象: docs/handoff/design-approval-ticket/routine/ROUTINE.md の登録手順と、agent-console に登録済みの promptText が一致していること
- 更新ルール: 手順書と登録済みの promptText がずれたら更新する。agent-console の版や登録内容が変わったときも本書と ROUTINE.md を更新する
- 関所なしの場合: 人手で守る。この一致を検査する CI ワークフローは無い
- 次フェーズへの引き継ぎ: なし
