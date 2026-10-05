# ADR-1006 implementation card (DRAFT; docs only, no code changed by this PR)

Basis: origin/main a3438193795d26059dca4c7051a7fcc204df9a10. All path:line below refer to that commit. Line numbers shift once PR-1 lands: re-grep before editing.
Facts used: prod `public.product_code_seq` start 298, last_value NULL; `product_code` varchar(50), no DEFAULT, no CHECK; partial unique index `uq_public_products_code` exists; max id 458213 (社外秘のローカル作業メモ（リポジトリ外） §3).

## 0. Order of work (why it is split)
run_all_migrations.sh re-runs EVERY migration on EVERY deploy (set -e; header lines 12-15), so each migration must be idempotent and must never reset the sequence. migration-guard Check 7 blocks UPDATE on `products`, Check 8 blocks any non-structural line that mentions `products` (migration-guard.yml:394-593). Therefore:
1. PR-1 = migration A only (structure): legacy column + unique partial index. No app change. Safe to merge/deploy alone.
2. Data step (NOT a migration; PO-approved prod data-change procedure, DRY-RUN then COMMIT, one transaction, rollback ready): copy product_code to legacy_product_code, renumber all rows by id ascending to PM-00001.., then `SELECT setval('public.product_code_seq', <max assigned>)` (next value = max+1). Stop registrations during this step (see 6).
3. PR-2 = migration B (DEFAULT + CHECK) + all code changes below. Merged only after step 2 is verified (count 1347 rows match `^PM-[0-9]{5}$`, unique, legacy filled).
未確認: in deploy.yml, whether migrations run before or after the backend container is replaced. If after, the old `_next_pm_code` would run against the new DEFAULT/CHECK for a short time: old code inserts `PM0298` style -> CHECK violation (fails loud, no bad data). Confirm in .github/workflows/deploy.yml before PR-2.

## 1. Migration A (PR-1): `migrations/<YYYYMMDD_HHMMSS>_add_legacy_product_code.sql`
Registration: append at the END of scripts/run_all_migrations.sh (after the current last line `run_sql migrations/20261003_100000_create_app_fx_rate_history.sql`, re-check tail for newer entries):
```
# ADR-1006: products.legacy_product_code 追加（旧コード退避用・構造のみ・冪等）
run_sql migrations/<YYYYMMDD_HHMMSS>_add_legacy_product_code.sql
```
File content (every line that names `products` must contain ALTER TABLE / CREATE INDEX / COMMENT ON, else Check 8 fails; no `{schema}` literal; filename `^[0-9]{8}_[0-9]{6}_.*\.sql$`; unique timestamp; no DROP):
```
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS legacy_product_code VARCHAR(50);
CREATE UNIQUE INDEX IF NOT EXISTS uq_public_products_legacy_code ON public.products (legacy_product_code) WHERE legacy_product_code IS NOT NULL;
COMMENT ON COLUMN public.products.legacy_product_code IS 'ADR-1006: 振り直し前の旧 product_code（店頭シート・過去記録との対応用）。NULL 以外は一意';
```
Do NOT: touch `product_code_seq` here (re-run would reset it); add any INSERT/UPDATE/SELECT on products; use pg_constraint/pg_get_constraintdef lines that name products (Check 8). Add the table to migration-test.yml setup if that workflow lacks public.products (backend/CLAUDE.md:56). Update docs: `docs/adr/ADR-1006-...` already exists (draft); run `node scripts/generate-adr-index.js` and commit docs/adr/README.md (CLAUDE.md; lessons.d/20260902-data-durability.md:41-44).

## 2. Migration B (PR-2): `migrations/<later timestamp>_product_code_default_and_check.sql`
```
ALTER TABLE public.products ALTER COLUMN product_code SET DEFAULT ('PM-' || lpad(nextval('public.product_code_seq')::text, 5, '0'));
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = 'products' AND constraint_name = 'ck_products_product_code_format'
    ) THEN
        ALTER TABLE public.products ADD CONSTRAINT ck_products_product_code_format CHECK (product_code ~ '^PM-[0-9]{5}$');
    END IF;
END $$;
```
Notes: lines mentioning `products` inside the DO block: the `table_name = 'products'` line is covered only if it matches an allowed pattern (information_schema / table_name / table_schema continuation, migration-guard.yml:~520-530 allow list) - verify with a local run of the Check 8 grep before pushing. The CHECK allows NULL (a CHECK passes on NULL): 12 rows currently have NULL product_code; decide in the data step whether they get numbers (ADR says "all products" -> yes) and then optionally SET NOT NULL (not in ADR; do not add unless PO says). If sequence value exceeds 99999 the DEFAULT yields 6 digits and the CHECK rejects it: intended fail-loud.
Register after migration A in run_all_migrations.sh with the same comment style. Do NOT use `NOT VALID` unless the data step cannot be completed (then VALIDATE in a separate later migration).

## 3. v6 gate: backend/app/services/tcg_analyzer_svc.py
Before (:1209-1224):
```
    legacy_code_rows = session.execute(
        text("SELECT product_code, id FROM public.products WHERE is_active = TRUE AND product_code IS NOT NULL")
    ).fetchall()
    product_code_to_id: dict[str, str] = {str(r[0]): str(r[1]) for r in legacy_code_rows}
    ...
    mark_rows = session.execute(
        text("SELECT mark, id FROM public.products WHERE is_active = TRUE AND mark IS NOT NULL AND mark <> ''")
    ).fetchall()
    rawcode_to_id: dict[str, str] = {str(r[0]): str(r[1]) for r in mark_rows}
    rawcode_to_id.update(product_code_to_id)  # product_code が mark より優先
```
After: delete :1209-1215 (comment + legacy_code_rows + product_code_to_id; grep shows product_code_to_id has no other use) and replace :1217-1224 with a call to a new small module-level function (testable without the whole job):
```
def load_rawcode_to_id(session: Session) -> dict[str, str]:
    """有効な商品の中で一意な mark だけを raw_product_code の照合表にする（ADR-1006）。
    共有されている mark は載せない（品番では決めず、検索語の照合に回す）。product_code は使わない。"""
    rows = session.execute(text(
        "SELECT mark, MIN(id) FROM public.products "
        "WHERE is_active = TRUE AND mark IS NOT NULL AND mark <> '' "
        "GROUP BY mark HAVING COUNT(*) = 1"
    )).fetchall()
    return {str(r[0]): str(r[1]) for r in rows}
```
and at the old site: `rawcode_to_id = load_rawcode_to_id(session)`.
Keep exactly as is: the lookup `rawcode_to_id.get(_rawcode)` at :1431 (exact string, stripped); the Gemini-vs-rawcode branches :1433-1480 (RAWCODE / RAWCODE_OVERRIDE / RAWCODE_EXCLUDED basis strings are stored in analysis_results and read by dashboards - do not rename); `product_code_to_uuid` (misnamed, keyed by id; :1196,:1206,:1503); load_lookup_maps :68-100. Do not add normalization of marks (ST-01 vs ST01 stay different keys, as today).
Expected effect (社外秘のローカル作業メモ（リポジトリ外） §2): 103 old RAWCODE_OVERRIDE rows -> Gemini's own pick; 7 rows -> keyword path; others unchanged.
NEEDS_DECISION for the author: "unique among active products" = exact string (as above, matches the gate's exact lookup) or normalized? Card assumes exact.

## 4. v7: backend/app/services/extraction_judgement_svc.py
Before (:141-149):
```
def _code_candidate_basis(product: ProductEntry, nb: str, folded: str | None = None) -> str | None:
    """product_code または mark を正規化したもの（空でないもの）が nb に含まれれば 'RAWCODE'。..."""
    for raw in (product.product_code, product.mark):
        if raw and _value_hits(raw, nb, folded):
            return "RAWCODE"
    return None
```
After:
```
def _code_candidate_basis(product: ProductEntry, nb: str, folded: str | None = None) -> str | None:
    """mark を正規化したもの（空でないもの）が nb に含まれれば 'RAWCODE'（ADR-1006: product_code は使わない）。..."""
    if product.mark and _value_hits(product.mark, nb, folded):
        return "RAWCODE"
    return None
```
ProductEntry (:108-115): remove field `product_code` (and from the 3 loaders + 3 constructors) OR keep the field unused. Recommended: REMOVE, because a dead field invites regressions. Touch list if removed: extraction_judgement_svc.py:111; extraction_shadow_svc.py:94 (SELECT list), :107 (`product_code=r[1]` -> shift indexes: mark r[1], work_id r[2], search r[3], exclude r[4]); tcg_shadow_review_svc.py:204 (SELECT), :217 (`product_code=r.product_code`), :251 and :258 (`product_code=product.product_code`). Tests constructing ProductEntry(product_code=...): test_extraction_judgement_svc.py:111-119, test_extraction_shadow_svc.py:19-21, test_tcg_shadow_review_svc.py:135. Keep the two SELECTs textually identical (tcg_shadow_review_svc.py:197 says they must stay the same shape).
Do NOT touch: `_value_hits` / `_needs_boundary` / word-boundary logic, `_keyword_matches`, basis string "RAWCODE", `match_product` ordering.

## 5. Code generation: one source (DB DEFAULT)
a) backend/app/services/tcg_product_master_svc.py
- Delete :28 `_PM_CODE_RE` (check no other use; grep shows only :315) and the whole `_next_pm_code` :290-321.
- :371 delete `pm_code = await _next_pm_code(db)`.
- INSERT :391-400: remove `product_code` from the column list and `:code` from VALUES; remove `"code": pm_code` from params (:403). The DB DEFAULT fills it. Do NOT add `RETURNING product_code` unless a caller needs it: return value stays `{"ok": True, "product_id": str(product_id_int)}` (:466; tests assert exactly this dict; frontend ProductMasterDrawer.tsx:152 types `code?: string` but nothing sets it).
- Keep `SET LOCAL app.is_operator = 'true'` (:389) and the post-write gate (:455-464).
b) backend/app/routers/products.py (POST /products, :355-415)
- :379 INSERT list does not include product_code already. Delete :407-410 (`UPDATE ... SET product_code = :code` with `f"PD-{new_id:05d}"`). On PostgreSQL the DEFAULT now sets it; the later SELECT (:413) returns it.
- SQLite (pytest) branch: conftest.py:798 table has no DEFAULT and SQLite cannot call nextval. NEEDS_DECISION: (i) keep a SQLite-only fallback `if not is_postgresql(db): UPDATE products SET product_code = 'PM-%05d' % new_id` (tiny, test-only; slight SSOT leak) or (ii) leave product_code NULL on SQLite and change the test to not assert the code, with the PM format asserted in a PG test. Recommended (ii) to keep one source; the endpoint response type `product_code: str | None` (schemas/product.py:140) already allows NULL.
c) Other writers: scripts/seed_products_from_master.py:5,13,134,179-202 writes Mark as product_code with ON CONFLICT (product_code): after the CHECK it fails by design. ADR-155 already forbids seeding by script; add a top-of-file abort/deprecation note (separate decision, do not silently rewrite). tenant.py:719/748 (tenant-schema products table) and scripts/qa/seed-tenant.sql:191 target tenant_006.products, a different table: do NOT touch.
d) scripts/seed_inventory_from_output.py:181-185. Before:
```
            # product_code → product_id の lookup table を構築
            prod_rows = (await conn.execute(text(
                "SELECT id, product_code FROM public.products WHERE product_code IS NOT NULL"
            ))).all()
            prod_map = {r.product_code: r.id for r in prod_rows}
```
After (resolve by unique active mark; docstring :12 "Mark → product_id (products.product_code で resolve)" updated to "products.mark (有効・一意) で resolve"):
```
            # mark → product_id の lookup table（有効商品の中で一意な mark のみ。ADR-1006）
            prod_rows = (await conn.execute(text(
                "SELECT mark, MIN(id) AS id FROM public.products "
                "WHERE is_active = TRUE AND mark IS NOT NULL AND mark <> '' "
                "GROUP BY mark HAVING COUNT(*) = 1"
            ))).all()
            prod_map = {r.mark: r.id for r in prod_rows}
```
The unresolved branch (:~200, logs "product 未登録" and skips) already handles shared marks as skipped; leave it. Do not change supplier lookup or the INSERT.
e) Readers of product_code that stay as they are (display/sort only; values simply become PM-xxxxx): routers/buyback_prices.py:264,481,552,591; routers/inventory_offers.py:54,380; services/inventory_search.py:333; routers/products.py:131,193; tasks/reports.py:127; services/buyback_scraper/product_matcher.py:66-81 (ORDER BY product_code only affects iteration order; verify tie-break behaviour with a test run); tcg_product_detail_svc.py:74-75; tcg_product_roundtrip_svc.py:145. NOTE roundtrip `revision()` (:100-107) hashes snapshot["product"] which includes product_code, so every CSV exported before the renumber becomes ROUNDTRIP_STALE: tell the PO; do not change the hash.

## 6. Data step notes (for the procedure, not for the PR)
- Renumber order: id ascending over ALL rows incl. 14 inactive and the 12 NULL-code rows (ADR decision 2). Fill legacy_product_code = old product_code (NULL stays NULL); the partial unique index requires old codes to be unique (they are: uq_public_products_code).
- The renumber must avoid transient unique collisions between old codes and new ones: new format `PM-00001` never equals an old code (old PM codes are `PM0007`), but verify with a SELECT before COMMIT.
- The `trigger_set_updated_at_public_products` trigger bumps updated_at on all rows; acceptable but say so in the GO text.
- After COMMIT: setval, then re-run the 3 checks (count, regex, uniqueness) and `SELECT last_value FROM public.product_code_seq`.

## 7. Tests (TDD: write first, expect RED, then implement)
Rewrite:
- backend/tests/test_extraction_judgement_svc.py:168-178 `test_matches_by_product_code` -> `test_does_not_match_by_product_code` (product_code="OP-01", mark=None, block "OP-01 ..." -> status unmatched) plus keep `test_matches_by_mark` (:180-190).
- :562-615 boundary tests that use `product_code="151"` / `"ONP01"` (:568, :583, :590, :609) -> use `mark=`; the assertions are unchanged.
- test_extraction_judgement_svc.py:105-120 `_product()` helper, test_extraction_shadow_svc.py:19-21, test_tcg_shadow_review_svc.py:135: drop product_code if the field is removed.
- test_tcg_shadow_accuracy_pg.py:132, test_tcg_shadow_review_pg.py:50: INSERTs keep working (fixture codes arbitrary) until the CHECK exists in the test DB; if the test DB runs migration B, these fixtures with codes like 'SENTINEL', 'DETAIL', 'RT..', 'P' violate the CHECK. Decision: apply migration B only in the migration test, NOT in the shared PG fixture, or change fixtures to PM-0000x (many files: test_tcg_product_detail_pg.py:40-131, test_tcg_product_list_pg.py:104-194, test_tcg_product_roundtrip_pg.py:40,230,322,359 use `LIKE 'RT%'`, test_tcg_work_matching_integration.py (104 PM literals) ). Recommended: keep CHECK out of the shared fixture.
- backend/tests/test_products.py:40 `startswith("PD-")` -> per 5b decision (ii) remove the assertion (or `data["product_code"] is None` on SQLite) and add the PG test below.
- backend/tests/test_tcg_product_import.py:359: delete the `monkeypatch.setattr(master, "_next_pm_code", ...)` line (function removed); `execute` call numbering in that test (:342-350, calls == 3 / 6) is unaffected because `_next_pm_code` was patched, but re-run to confirm.
- test_tcg_work_matching_integration.py:295-297 creates `product_code_seq START WITH 1` for the test DB: keep, and add the DEFAULT in the test fixture only for the new PG test below.
Add:
1. v6 gate unit test (new file backend/tests/test_tcg_rawcode_gate.py) for `load_rawcode_to_id` with a stub session returning rows, plus a PG test against a real table: (a) unique active mark -> id; (b) mark shared by 2 active products -> key absent; (c) mark shared by 1 active + 1 inactive -> present (inactive excluded by WHERE); (d) a string equal only to some product_code -> absent; (e) empty/NULL mark -> absent. Gate-level PG test (pattern of test_tcg_work_matching_integration.py :1083-1120): with a shared mark and Gemini id X, result pid == X and pid_basis == "GEMINI" (no RAWCODE_OVERRIDE); with unique mark and Gemini id Y != mark owner -> RAWCODE_OVERRIDE as before (regression guard); shared mark + Gemini empty -> keyword path basis, never "RAWCODE".
2. v7 mark-only: test above; plus the T2 regression pair from the recon: products (id 39 mark "PRB-02") and (id 199 code "ARD", empty mark) with block containing "CARD" -> matched 39, not ambiguous (社外秘のローカル作業メモ（リポジトリ外） §3).
3. Code generation (PG test, new): INSERT through `create_product` twice in one transaction -> both product_code match `^PM-[0-9]{5}$`, differ, second = first + 1; and a direct `INSERT ... (name) VALUES` without product_code gets the DEFAULT. Constraint test (migration B): inserting product_code 'PM0001' / 'PM-1' / 'pm-00001' fails; NULL passes. Idempotency test: running migration A and B files twice leaves one column / one index / one constraint (pattern: tests/test_inventory_sprint1_migrations.py).
4. Migration guard dry-run: run the Check 7/8 greps from migration-guard.yml locally on both new files (command: copy the loop; expect no violation).

## 8. Frontend
No code change required: product code is displayed only from API fields and existing keys, and no string embeds a format.
- tcg-product-import/TcgProductDetailDrawer.tsx:16,224 renders `detail.product.code` read-only with `t("productDetail.code")`.
- buyback-prices/BuybackPricesPage.tsx:162-168 and BuybackPendingReviewModal.tsx:152 render `product_code`; header key `buybackPrices.byProduct.columnProductCode`.
- i18n parity checked on origin/main: `productDetail.code` ja "商品コード" / en "Product code"; `buybackPrices.byProduct.columnProductCode` ja "商品コード" / en "Code" (both files, same keys; locales/ja.json:384,1741, en.json:384,1741). No new key and no hardcoded string is introduced.
- Optional (only if PO wants it): none. Do NOT add new UI for legacy_product_code in this PR (not in ADR scope; would need new ja+en keys).
- e2e fixtures with old-style codes (tests-e2e/product-edit-tcg-type.spec.ts:16 "PD-00123", tcg-product-import.spec.ts:25 "PM01", quote-create-inventory-search.spec.ts:29,45, f11-ac11-5-...spec.ts:57) are mock payloads; leave untouched.

## 9. Out of scope / do NOT touch
- migrations already merged (esp. 20260915_120000_phase_b..., 20260914_140000_unify..., seeds): immutable and re-run on every deploy; their re-run safety after the renumber is 未確認 (needs prod check that public.products.tcg_uuid does not exist).
- docs/adr/ADR-1002 (amended by ADR-1006, edit only through the ADR PR).
- Gemini prompt / reference payload (tcg_work_reference.py:load_work_reference passes mark, not product_code; the reference digest changes on renumber only if product_code were in it: it is not).
- analysis_results history (pid_basis strings), tcg_product_import_rows.product_code (history column, keeps old text).
- GAS inventory sheet product_id sync (outside the repo; ADR says separate task).

## 10. Acceptance (maps to ADR-1006 受入条件)
|criterion|how verified|
|---|---|
|all products match ^PM-[0-9]{5}$, unique, legacy filled|prod read-only SELECT counts after the data step|
|new product gets next number from DB|PG test 7.3 + one prod create after deploy (PO)|
|v6/v7 do not read product_code|grep `product_code` in tcg_analyzer_svc.py gate region and extraction_judgement_svc.py returns none; tests 7.1/7.2|
|no regression in v9 mark-only sim|already measured: 5 ambiguous->matched, 0 regressions (社外秘のローカル作業メモ（リポジトリ外） §3); re-run the local rejudge tool after PR-2|
|re-analysis delta confirmed by PO|the 社外秘のローカル作業メモ（リポジトリ外） §2 (103 changed + 7 keyword-path rows; correctness of Gemini vs old gate pick is PO's check)|
|pytest + smoke green|CI|
