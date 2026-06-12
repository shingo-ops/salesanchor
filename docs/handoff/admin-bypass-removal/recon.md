# recon: main保護ルール Admin bypass 除去

- 実施日: 2026-06-12
- 担当: Terminal Claude Code

---

## R1: Ruleset 15777895 現状全文

`gh api repos/shingo-ops/salesanchor/rulesets/15777895` 出力（抜粋・実証値）:

```
id: 15777895
name: "main branch protection"
target: branch
enforcement: active
conditions.ref_name.include: ["~DEFAULT_BRANCH"]  (= main)
bypass_actors: [
  { actor_id: 5, actor_type: "RepositoryRole", bypass_mode: "always" }
  ← Admin が常時バイパス可。これが今回の事故原因。
]
rules:
  - deletion
  - non_fast_forward
  - pull_request:
      allowed_merge_methods: ["merge"]  ← squash/rebase 禁止（正しい）
  - required_status_checks: [10件]
```

**変更前 Ruleset 全文（ロールバック材料）:**

```json
{
  "name": "main branch protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "exclude": [], "include": ["~DEFAULT_BRANCH"] }
  },
  "bypass_actors": [
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }
  ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["merge"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "pytest (SQLite + PostgreSQL RLS)", "integration_id": 15368 },
          { "context": "テナントスキーマ整合性チェック", "integration_id": 15368 },
          { "context": "マイグレーションSQL 実行テスト（実DB）", "integration_id": 15368 },
          { "context": "models.py に新 Column → deploy.yml にマイグレーション追記必須", "integration_id": 15368 },
          { "context": "ADR-072 tenant schema lint (strict mode)", "integration_id": 15368 },
          { "context": "Lint & Dark Mode Check (ADR-067)", "integration_id": 15368 },
          { "context": "Playwright E2E (chromium)", "integration_id": 15368 },
          { "context": "gitleaks（シークレット漏洩検出）", "integration_id": 15368 },
          { "context": "CLAUDE.md line count check", "integration_id": 15368 },
          { "context": "ADR index is up to date", "integration_id": 15368 }
        ]
      }
    }
  ]
}
```

復元コマンド（ロールバック時）:
```bash
TOKEN=$(gh auth token)
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  -d '上記JSONをbodyに' \
  "https://api.github.com/repos/shingo-ops/salesanchor/rulesets/15777895"
```

---

## R2: bypass_mode 仕様の突合（推測検証）

**判定: ハンドオフの分析が正確。bypass_mode 変更は不十分。**

- `bypass_mode: "always"` = push/PR どちらの経路でもバイパス可
- `bypass_mode: "pull_request"` = PR 経由ならバイパス可（UI での squash も PR 経由のため依然として事故可能）
- 正しい修正: Admin エントリを bypass_actors から **除去**する（mode 変更ではない）

---

## R3: squash 使用実態（I2 可否判定）

**判定: I2 見送り。squash は CI パイプラインで feature→develop に必須使用中。**

### ADR-050 squash 規定（docs/adr/ADR-050-release-pr-workflow-standardization.md:54-57）
```
feature/* → develop: --squash --delete-branch  ✅ squash 使用
main ← develop:      --merge                   ❌ squash 禁止
main ← hotfix/*:     --squash --delete-branch  ✅ squash 使用
```

### CI パイプライン（.github/workflows/claude-pipeline.yml:786-790）
```yaml
# feature branch → --squash --delete-branch --admin
gh pr merge "$PR_NUMBER" --repo "$REPO" --squash --delete-branch --admin
# non-feature branch → --squash --admin
gh pr merge "$PR_NUMBER" --repo "$REPO" --squash --admin
```
→ feature→develop の自動マージは全件 squash。直近 develop ログ20件も全件 squash を確認。

### リポジトリ設定
`allow_squash_merge / allow_merge_commit / allow_rebase_merge` の API 取得値が null（スコープ不足）。
ただし CI がsquash成功中のため allow_squash_merge=true であることは確実。

**結論: allow_squash_merge:false にするとパイプライン破壊。I2 は見送り。**

---

## R4: 自動化バイパス依存チェック

**判定: I1 は安全。自動化への影響なし。**

- `.github/workflows/claude-pipeline.yml:777` — `GH_TOKEN: ${{ github.token }}`
- automerge ジョブ（:764〜）はターゲットが **develop** のみ（feature→develop）
- develop 保護 Ruleset（ID:16619490）: bypass_actors=[] / merge method 制限なし
- main Ruleset（15777895）bypass_actors 変更は develop パイプラインに一切影響しない
- deploy.yml・release スクリプト・bot に「Admin bypass 前提」の main 直操作なし
