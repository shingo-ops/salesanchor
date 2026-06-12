# Phase 3 設計 — gate-dangerous-require-approval

**対象ADR**: ADR-136  
**recon**: docs/handoff/gate-dangerous-require-approval/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 2026-06-12 PR #2063（hotfix: v_company_stats migration スキップガード）: 危険変更を含むにもかかわらず承認ゼロでマージ。原因は `check-process-artifacts.js:398` の `!hasAuth` ブランチが `runFullCheck` にフォールスルーし、成果物（recon/design）が揃っていると gate を通過してしまう実装バグ。今回の修正で即 `printFailure` に変更し同じ経路を封鎖。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 危険変更 PR に承認なしで gate が FAIL する | `MOCK_APPROVALS='' CHANGED_FILES=migrations/001.sql node scripts/check-process-artifacts.js` → exit 1 + 承認要求メッセージ確認 |
| 危険変更 PR ＋ 成果物完備 ＋ 承認なし でも FAIL（AC4-edge） | `node scripts/tests/test-process-artifacts.js` の `AC4-edge` テスト PASS 確認 |
| 危険変更 PR に承認ありで gate が PASS する（AC5 回帰） | `MOCK_APPROVALS=shingo-ops CHANGED_FILES=migrations/001.sql` → exit 0 確認 |
| docs-only PR は承認なしで PASS（AC6 回帰） | `CHANGED_FILES=docs/adr/ADR-001.md` → exit 0 + 自動スキップ確認 |
| 全テスト 31 件 PASS | `node scripts/tests/test-process-artifacts.js` → 31 PASS / 0 FAIL |

---

## 技術 How・KPI

- KPI: 危険変更 PR の 0-Approve マージを 100% ブロック
- 技術: `scripts/check-process-artifacts.js:398` の `!hasAuth` ブランチを `runFullCheck` フォールスルーから `printFailure` 即失敗に変更。1 行削除・5 行追加。
- Ruleset 変更なし（process-artifacts gate は既に Required Status Check として登録済み）

---

## 弊害・トレードオフ

- 5月20日の摩擦（Required approvals=1 → 相互依頼地獄）は ADR-136 で PR 作者が shingo-cc（bot）に固定されたことで解消済み。詳細は `docs/BRANCH_PROTECTION_SETUP.md §5-bis 5月20日摩擦が再発しない根拠` 参照。
- break-glass 時（本番障害）: bypass_actors が null のため admin もルール bypass 不可。緊急対応は「Shingo が EMERGENCY: PR を直接 Approve」で gate を通過させてからマージする経路を取る。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `check-process-artifacts.js:398` の `!hasAuth` ブランチを `printFailure` に変更 | Generator |
| 2 | テスト AC4 更新 ＋ AC4-edge 追加 | Generator |
| 3 | `docs/BRANCH_PROTECTION_SETUP.md §5-bis` に摩擦再発なし根拠を追記 | Generator |
| 4 | handoff docs 作成 ＋ PR 起票 | Generator |

---

## 継続

- 完了後の監視: 次回 migration PR の CI ログで gate が承認なし状態で FAIL することを確認
- 次フェーズへの引き継ぎ: break-glass（bypass_actors 追加）が必要になった場合は BRANCH_PROTECTION_SETUP.md §4-C に記録して PO 確認
