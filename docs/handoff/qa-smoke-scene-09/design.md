# design — QA Smoke Suite Scene 09: ADR-108 B-1 販売形態複数選択 検収

**対象ADR**: ADR-038 / ADR-108  
**recon**: docs/handoff/qa-smoke-scene-09/recon.md  
**日付**: 2026-06-14  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

**ADR-038（QA Smoke Suite）既存シーン設計**:  
scene-01〜08 で確立された「real Firebase login → psql assert → UI操作」パターンを踏襲。  
data-testid ベースのセレクタ（`sales-form-trigger` 等）を使い、i18n 言語設定に依存しない安定したテスト設計を採用（ADR-027 対応）。

**ADR-108 B-1 migration 設計との整合**:  
`tenant_sales_form_options` は tenant_004 のみに初期データあり。tenant_006（QA テナント）は空のため、  
`seed-tenant.sql` に `ON CONFLICT DO NOTHING` で冪等 seed を追加（ADR-045 additive-only 準拠）。  
本番稼働テナント(tenant_004)の seed には一切触れない。

---

## KGI

ADR-108 B-1（販売形態複数選択）の post-deploy 検収を機械化し、  
self-hosted runner + QA secrets 整備後に自動実行できる状態にすること。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| scene-09-A が PASS する | `npx playwright test scene-09.spec.ts --grep @scene-09` |
| data-testid が実装と一致する | `grep "data-testid" SalesFormMultiSelect.tsx:111` → `sales-form-trigger` |
| tenant_006 seed が冪等 | `seed-tenant.sql` の `ON CONFLICT DO NOTHING` 確認 |
| 秘匿情報がコードに含まれない | `grep -r "QA_ADMIN_PASSWORD\|DATABASE_URL" tests/qa-smoke/scene-09.spec.ts` → 0件 |
| B/C がデフォルトスキップ | `QA_RUN_SCENE_B/C` 未設定時に `test.skip` が呼ばれること |

---

## 技術 How

### Scene 09-A: 販売形態複数選択 UI（常時実行）

- tenant_006 の QA-LD-001〜003 リードを対象に、company タブの `SalesFormMultiSelect` 動作を確認
- `data-testid="sales-form-trigger"` をクリックしてドロップダウン開閉
- 複数選択 → PATCH → GET で復元されること（A-2）
- 「その他」選択時のみ `data-testid="sales-form-other-input"` が表示されること（A-3）
- DB で `lead_sales_form_selections` に保存されること（A-4、psqlCount 使用）
- `console.error` 0件を assert

### Scene 09-B: Redis tenant cache 無効化（`QA_RUN_SCENE_B=true` 必須）

- **デフォルトスキップ**（安全フラグ必須）
- tenant_006 限定。論理削除 API 呼び出し後に Redis cache が無効化され 403 を返すことを確認
- 本番稼働テナントへの実行禁止。実行後は `reset-tenant.sh` で復元すること
- 物理削除 API は実行しない

### Scene 09-C: Discord Auto Setup（`QA_RUN_SCENE_C=true` + `QA_SCENE_C_GUILD_ID` 必須）

- **デフォルトスキップ**（安全フラグ + guild ID 必須）
- 安全な対象 guild が確定するまで実行しない
- 2回実行で冪等性を確認（既存リソースを壊さないこと）

### 実行前提（runner / Secrets）

| 前提 | 内容 |
|------|------|
| runner | `[self-hosted, salesanchor-vps]` が起動していること |
| `QA_ADMIN_EMAIL` | CI secret。PRコメント・コードに記載禁止 |
| `QA_ADMIN_PASSWORD` | CI secret。PRコメント・コードに記載禁止 |
| `DATABASE_URL` | CI secret（`ADMIN_DATABASE_URL` とは別名に注意） |
| その他 QA secrets | `qa-smoke.yml` 参照 |

### QA Smoke Suite が queued/cancelled になる場合

self-hosted runner が停止中であれば queued → cancelled は正常動作。  
runner を復旧してから再 dispatch すること（`gh workflow run "QA Smoke Suite (ADR-038)"`）。  
GitHub-hosted runner では実行不可（DB 直接アクセスが必要なため）。

---

## 危険変更・制約

| 項目 | 内容 |
|------|------|
| Gate 上の分類 | `scripts/qa/seed-tenant.sql` は `scripts/` 配下のため Process Artifacts Gate 上は「危険変更」扱い。ただし実態は QA専用 tenant_006 seed のみで、本番 tenant_004 には影響なし。GO #2194 取得済み |
| migration 変更 | なし（deploy.yml/本番スクリプト変更なし） |
| 本番稼働テナント | tenant_004 への変更なし |
| 物理削除 API | 今回実行しない（B も論理削除のみ、物理削除禁止） |
| 秘匿情報 | QA認証情報・DATABASE_URLをコード/PR/GitHubコメントに記載しない |

---

## ロールバック方針

`scene-09.spec.ts` を削除し、`seed-tenant.sql` の追加分を revert するだけで影響なし。  
本番 DB・migration への影響ゼロ。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Hikky-dev |
| 2 | scene-09.spec.ts 作成・testid 修正 | Hikky-dev |
| 3 | seed-tenant.sql に tenant_006 seed 追加 | Hikky-dev |
| 4 | PR #2194 作成・CI 確認 | Hikky-dev |
| 5 | self-hosted runner 復旧 + QA secrets 整備 | Shingo-ops |
| 6 | QA Smoke Suite 実行 + scene-09 PASS 確認 | Hikky-dev / Shingo-ops |

---

## 継続

- scene-09-A: runner + QA secrets 整備後に即実行可能
- scene-09-B: 検証専用テナント操作フロー確立後に有効化
- scene-09-C: 安全な Discord guild 確定後に有効化
