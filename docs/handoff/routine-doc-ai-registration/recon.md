# recon — routine-doc-ai-registration

**仕事名**: routine-doc-ai-registration  
**日付**: 2026-10-14  
**対象ADR**: ADR-1011  
**担当**: Sonnet（実装役）。事実は Opus から受領した指示書による。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:6` | 見出しが「登録手順（PO）」のまま（変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:9` | 前提が agent-console v0.18.0 以上・導入済み 0.17.0 の記載（変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:10` | K15 が「合格済みであること」（未了前提の書き方・変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:12` | 「HTTP API は認証方式が未確認のため使わない」（変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:23` | 止めるときに ac-routine disable の記載なし（変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:32` | 確認画面の項目が未確認のまま（変更前） |
| `docs/handoff/design-approval-ticket/routine/ROUTINE.md:36` | 「指示文（ここから下を貼る）」。ここより下は変更しない |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | v0.25.0 導入・K15 合格・id 5d459653 の登録の事実 | Opus 確認済みの指示書で受領（本 PR では再検証しない） | 該当なし |

**未解決ゼロ確認**: 該当なし

---

## 補足

純粋な書類の変更。製品コードは触らない。
