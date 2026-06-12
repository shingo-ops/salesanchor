# recon — gate-dangerous-require-approval

**仕事名**: gate-dangerous-require-approval  
**日付**: 2026-06-12  
**対象ADR**: ADR-136  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/check-process-artifacts.js:398` | `!hasAuth` ブランチ（旧: runFullCheck にフォールスルー → 今回修正箇所） |
| `scripts/check-process-artifacts.js:29` | `AUTHORIZED_APPROVERS = ['shingo-ops', 'Hikky-dev']` の定義 |
| `scripts/check-process-artifacts.js:46` | `DANGEROUS_PATTERNS` 定義（migrations/ / deploy.yml / 本番スクリプト） |
| `scripts/tests/test-process-artifacts.js:226` | AC4 テスト（旧: fallthrough 前提のメッセージ検証 → 今回修正） |
| `docs/BRANCH_PROTECTION_SETUP.md:128` | §4 break-glass ログ（4-A/4-B 手順追加箇所） |
| `docs/adr/ADR-136-cc-bot-github-identity.md:44` | ガードレール節（「承認必須」の記述、実装が追いついていなかった箇所） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | bypass_actors の実値（null か空配列か）| `gh api` で確認 → Python None（null）= bypass actor なし | ✅ 解消済み |
| 2 | 5月20日の Required approvals=1 摩擦が再発するか | ADR-136 で PR 作者が shingo-cc（bot）に固定済み → 摩擦構造が消滅 | ✅ 解消済み |
| 3 | break-glass 時の技術的経路（bypass_actors なしで緊急マージ可能か）| bypass_actors = null → admin もルールを bypass 不可。緊急時は Shingo が直接 Approve すれば gate 通過 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
