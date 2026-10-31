# 段1 §3 事前確認の結果（実装役 Sonnet・origin/main 2c3a4e389 を merge した枝）

| 項目 | 結果 | 根拠 |
|---|---|---|
| (a) 登録検査 | 問題なし | `.github/workflows/migration-guard.yml:123-125` は `migrations/<ファイル名>` が scripts/run_all_migrations.sh のどこかにあれば通す。ai_ro の作成 SQL と同じく `AI_CLOUD_CREATE_SQL="migrations/20261024_100300_create_ai_cloud_views.sql"` の変数行で通る。scripts/check-migration-registration-exists.sh は `^run_(sql\|py)` の行だけを見る |
| (c) 持ち主の RLS | 合格 | backend/tests/ops/test_ai_cloud_views.py `test_c_view_owner_passes_rls_like_ai_ro`。非 superuser・FORCE なしの持ち主 aic_owner が RLS つきの表を読むと 2 行、ai_cloud のビュー越しも 2 行（pytest-test_ai_cloud_views.txt:14）。ただし本番の jarvis が superuser かは未確認（superuser でも RLS は越えるので結果は同じ） |
| (d) 一覧の末尾 | 20261023_180000_create_accuracy_gold.sql（scripts/run_all_migrations.sh の旧 :1173）。その後ろに #1・#2 を足した。ほかの PR の追記なし |
| (e) CI の手順 | .github/workflows/test.yml「Run pytest (full suite + PostgreSQL RLS)」が backend で `pytest -q`。RLS_ADMIN_DATABASE_URL（jarvis・superuser）が入る。backend/tests/ops/ は自動で拾われるので #9 は同じ手順に載る |
| (f) ai-reader.env の置き方 | 記録は見つかった | docs/adr/ADR-1024-ai-readonly-db-path.md:90（便3b: ロールのパスワード設定・接続情報は VPS 上の別ファイル 600）、docs/handoff/ai-readonly-db-path/design.md:116（パスワード → `.env` に AI_READER_DATABASE_URL → 起動確認）。台本そのものはリポジトリに無い（PO の `!` で実行したため）。PO の `!` の台本は作っていない（§4 の PO の操作は行わない決まり） |
| (g) | Opus が本番で確認済み | 行わない |
| (i) (b) の 27 表の router 以外の書き込み | 見つからず | Grep `(INSERT INTO\|UPDATE)\s+(public\.)?<27 表>` を backend/app の router 以外に: 1 件のみ `backend/app/tasks/fx_rate_updater.py:74` が `app_fx_rate_history` に外部の為替（通貨記号・数・時刻）を書く。利用者の入力ではない。27 表の `__tablename__` を持つ ORM モデルは無し。動的な表名での書き込みは未確認 |
| (h) 試験 DB の列と分類表の差 | **0 ではない（9 列）→ 止めて Opus へ** | 下記 |

## (h) の生出力（pytest-test_ai_cloud_views.txt:20-29）

試験 DB は tests/rls_bootstrap.py の `bootstrap_tenant_schema`（既存の試験と同じ本番 migration 順の作り方）で作った。対象は deny に当たらない列で、「そのまま」でない型の列に分類が無いもの。

```
T10 gaps=9
T10 GAP ('public', 'tenants', 'company_name', 'varchar', '分類なし')
T10 GAP ('public', 'users', 'firebase_uid', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'supplier_code', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'name', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'contact_name', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'email', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'phone', 'varchar', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'address', 'text', '分類なし')
T10 GAP ('tenant_001', 'suppliers', 'notes', 'text', '分類なし')
```

見立て（未確認。本番の列は見ていない）:
- tenant_001.suppliers の 7 列: テナントの型紙 backend/app/services/tenant.py:964 `CREATE TABLE IF NOT EXISTS {schema}.suppliers` が作る。分類表 TSV には `tenant_*` の `suppliers` が無く（`tenant_suppliers`・`tcg_suppliers` はある）、仕入元は migration 056 で public に移された。本番のテナントに `suppliers` が残っているかは試験 DB からは分からない。
- public.users.firebase_uid・public.tenants.company_name: TSV に無い。試験の足場（tests/rls_bootstrap.py の `_ensure_public_users` と tenants の INSERT）が作る列で、本番に有るかは未確認。
- 分類表の行は足していない（カード §3(h)）。

## 決めてほしいこと（Opus）
1. 上の 9 列は本番に有るか（有るなら TSV が足りない＝行を足す。無いなら試験 DB 側の差）。
2. 差が試験の足場だけの場合の T10 の扱い: (A) 足場の差の列を試験の除外に明記する、(B) tenant の型紙から suppliers を除いた形で試験 DB を作る、(C) 分類表に行を足す（カード §2 は「足し引きは別の PR」）。
