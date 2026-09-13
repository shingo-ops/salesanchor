# Phase 3 設計 — dp-card-selfcheck-output

**対象ADR**: ADR-091  
**recon**: docs/handoff/dp-card-selfcheck/recon.md  
**日付**: 2026-08-31  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 過去事例: 2026-07-08 の一連の便で実測（`docs/ai-agents/design-partner.md:164`）——照合チェックリストを持っていても出力を義務化していなかったために省略が常態化した。
- 我々への応用: 照合の有無を「出力がなければ未実施」と定義することで、カード発行時点での省略を構造的に防ぐ。今回の8件不備（2026-08-31 Discord連携便）が同じパターンの再発であることを確認し、出力義務条項を §5.5 の先頭（項目 0）に明示した。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `docs/ai-agents/design-partner.md` §5.5 の先頭に項目 0「照合結果を出力する」が追加されている | `git show HEAD:docs/ai-agents/design-partner.md` で行 167 付近を目視確認 |
| `docs/ai-agents/lessons.d/20260831-card-design-failures.md` が新規追加されている | `git diff origin/main --name-only` に当該パスが含まれる |
| PR #3175 の `git diff --numstat` が `3  0  docs/ai-agents/design-partner.md` である | `git diff origin/main --numstat -- docs/ai-agents/design-partner.md` で確認 |

---

## 技術 How・KPI

- 変更対象: `docs/ai-agents/design-partner.md` §5.5 の先頭に3行追加（削除なし）
- 新規ファイル: `docs/ai-agents/lessons.d/20260831-card-design-failures.md`（33行）
- KPI: design-partner.md §5.5 に項目 0 が存在する（CI Process Artifacts Gate グリーン）

---

## 弊害・トレードオフ

- 設計パートナーへの出力義務追加により、カード発行時のメッセージ量が微増する
- 対策: 項目数は増やさず「出力する」義務のみを追加（既存チェックリストを削除しない）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `docs/ai-agents/design-partner.md` §5.5 先頭に項目 0 を3行挿入 | Generator |
| 2 | `docs/ai-agents/lessons.d/20260831-card-design-failures.md` を新規作成 | Generator |
| 3 | 本設計doc・recon.md を追加してコミット | Generator |
| 4 | PR #3175 本文の `設計:` と `recon:` を正しいパスに更新 | Generator |

---

## 継続

- 完了後: CI Process Artifacts Gate が全グリーンになることを確認
- 次フェーズ: PO GO 待ち → マージ
