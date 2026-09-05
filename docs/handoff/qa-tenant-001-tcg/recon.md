# recon: tenant_001 TCG テーブル作成（QA-03）

## 目的

tenant_001 に TCG 解析パイプライン全テーブルを作成し、QA を開始できる状態にする。

---

## 2026-09-05〜06 経緯: テナント選定ミスと修正

### 当初の計画（QA-01）

QA 用テナントとして tenant_006 を選んだ。
docs/STANDARD-WORKFLOW.md:93 に "tenant_006（QA）" と記載があったため。

### 失敗: PR #3315 デプロイ失敗（2026-09-05）

migration `20260906_100000_create_tcg_tables_t006.sql` が RAISE EXCEPTION で失敗。

```
NOTICE:  20260906_100000: schema tenant_006 テーブル数 = 95 (期待値: 27)
ERROR:   20260906_100000: テーブル数が 27 ではありません: 95
```

原因: tenant_006 に CRM 系テーブルが既に 68 本以上存在していた。全件カウントで 95 本が返った。

### TENANT-R2 調査（2026-09-06）: public.tenants 実態確認

```sql
SELECT * FROM public.tenants ORDER BY id;
```

結果（実測 2026-09-06）:

| id | tenant_name | tenant_code | created_at | contacts | 用途 |
|----|-------------|-------------|------------|----------|------|
| 1 | テスト株式会社 | test-corp | 2026-04-10 | 0 | docs に「空テスト」と明記 |
| 3 | 権限確認用 | perm-check-zzz | 2026-04-14 | 0 | 権限テスト用 |
| 4 | HIGH LIFE JPN | highlife-jpn | 2026-04-17 | 52 | 本番 |
| 5 | テストテナント2 | test-tenant-2 | 2026-04-17 | 0 | 用途不明 |
| 6 | Sales Anchor App Review | tenant-review | 2026-05-14 | 8 | Meta App Review 撮影専用 |

未使用 ID: 2, 7, 8, 9（public.tenants に行が存在しない）

### 判定: tenant_006 は QA 禁止

- docs/META_APP_REVIEW_PRE_RECORDING_CHECKLIST.md に Meta App Review 撮影専用と大量記述あり
- settings に `qa_smoke_seed_at` が記録されている（2026-06-17 seed 投入済み）
- contacts=8 件の実データあり
- STANDARD-WORKFLOW.md:93 の "tenant_006（QA）" の記載は誤り → 本カードで修正

### 選定: tenant_001 が正解

- contacts=0（データなし）
- STANDARD-WORKFLOW.md:93 に「空テスト」と既に明記されていた
- テーブル数 68 本（CRM 系のみ）= TCG テーブルは存在しない

教訓: **STANDARD-WORKFLOW.md:93 の「tenant_001（空テスト）」を見落としていた。
テナントを選ぶ前に public.tenants と docs/ を確認する。**

---

## 本 PR（QA-03）で変更するもの

| ファイル | 変更内容 |
|---------|----------|
| `migrations/20260906_100000_create_tcg_tables_t006.sql` | 削除（本番で毎回失敗するため） |
| `migrations/20260906_120000_create_tcg_tables_t001.sql` | 新規作成 |
| `scripts/run_all_migrations.sh` | t006 → t001 の run_sql 行を差し替え |
| `docs/STANDARD-WORKFLOW.md` | :93 の tenant_006（QA）記述を修正 |
| `docs/ai-agents/design-partner.md` | §9 テナントの用途 を新設 |
| `docs/handoff/qa-tenant-001-tcg/recon.md` | 本ファイル（新規） |
| `docs/handoff/qa-tenant-001-tcg/design.md` | 新規作成 |

---

## PR #3317（QA-01b）との関係

PR #3317 は `migrations/20260906_100000_create_tcg_tables_t006.sql` の検算クエリ修正。
本 PR（QA-03）では当該ファイルごと削除するため、#3317 はクローズして差し支えない。
（削除によって #3317 の変更対象ファイルが消えるが、DB への影響はない。
  t006 の migration は一度も正常に実行されていない = rollback 済み）

---

## 守り手

人手で守る（migration 実行後の RAISE NOTICE のテーブル数=27 を目視確認）。
