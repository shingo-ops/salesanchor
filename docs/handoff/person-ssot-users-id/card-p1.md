# 実装カード P1: companies.sales_rep_id の参照先を public.users(id) にする（ADR-1008）

- 設計: docs/handoff/person-ssot-users-id/design.md §4・§6（PO 承認 2026-10-13「y」）
- 根拠: docs/handoff/person-ssot-users-id/recon.md §3（P1 実物点検 a〜f）
- ブランチ / 作業場所: release/person-ssot-users-id / /Users/tanizawashingo/worktrees/salesanchor/release-person-ssot-users-id
- 実装役: Sonnet。設計者: Opus。

## 変更するファイル（これ以外は触らない）

1. 新規 `migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql`（構造のみ・値の INSERT/UPDATE/DELETE を書かない・2回流しても同じ結果）
   - 型は migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:18-60 に倣う。
   - `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname LOOP`
   - その schema に companies 表が無ければ CONTINUE。
   - companies の外部キーのうち `pg_get_constraintdef(oid)` が `FOREIGN KEY (sales_rep_id) REFERENCES` で始まり、参照先が `staff(id)` を含むもの（名前は fk_companies_sales_rep / companies_sales_rep_id_fkey の2種類ある）をすべて外す（`ALTER TABLE %I.companies DROP CONSTRAINT %I`）。
   - 名前 `fk_companies_sales_rep_user` の制約が無ければ `ALTER TABLE %I.companies ADD CONSTRAINT fk_companies_sales_rep_user FOREIGN KEY (sales_rep_id) REFERENCES public.users(id) ON DELETE SET NULL`。
   - 冒頭コメントに ADR-1008 と目的を書く。
2. `scripts/run_all_migrations.sh` 末尾（現在 912 行）に、説明コメント1行と `run_sql migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql` を追記。
3. `backend/app/services/tenant.py:650-661`（新規テナントの companies の外部キー付与）
   - 変更前: 名前 fk_companies_sales_rep で `{schema}.staff(id)` を参照。
   - 変更後: 名前 fk_companies_sales_rep_user で `public.users(id) ON DELETE SET NULL` を参照（存在確認して無ければ作る、の作りは同じ）。:224 のコメント「FK は staff 作成後に付与」も実態に合わせて直す。
4. `backend/app/routers/companies.py`
   - POST（:388-412 付近）と PATCH（:495-557 付近）で、sales_rep_id が指定され NULL でないとき、`SELECT id FROM public.users WHERE id = :uid AND tenant_id = :tid`（backend/app/routers/roles.py:500 と同じ形）で存在を確かめ、無ければ HTTP 422。メッセージの書き方は companies.py 内の既存の HTTPException に合わせる（新しい文言を作る場合は日本語1文、既存の流儀に揃える）。
   - 確認処理は1つの関数にまとめ、POST と PATCH から呼ぶ（重複を書かない）。
   - PATCH は sales_rep_id が更新対象に含まれるときだけ確かめる。
5. 試験 `backend/tests/`（既存の companies の試験ファイルに追加。無ければ新規 test_companies_sales_rep_users.py）
   - 同じテナントの users の id を sales_rep_id に指定 → POST 成功・PATCH 成功
   - 別テナントの users の id → 422（POST・PATCH）
   - 存在しない id → 422
   - sales_rep_id を null にする PATCH → 成功
6. 文書（設計者が用意済み。実装役は git add するだけ）: docs/adr/ADR-1008-person-ssot-users-id.md、docs/handoff/person-ssot-users-id/ の recon.md・design.md・card-p1.md・d1_link_roster.sql・d1_dryrun.sql・d1_rollback.sql
7. `node scripts/generate-adr-index.js` を実行し、docs/adr/README.md の差分をコミットに含める。
8. frontend/api-contract/openapi.json: API の形が変わらないなら触らない。CI「API contract is up to date」が差分を示したら、CI ログの差分の行だけを直す（全体の再生成はしない）。

## 触らない範囲

- backend/app/routers/analytics.py（すでに users.id として読んでいる）
- frontend/src（sales_rep_id を送る画面は 0 件）
- 本番 DB（値の付け替え D2 は設計者が別途行う）
- 他の staff 参照列（P2 で扱う）

## 手順

1. `./scripts/dev/executor-preflight.sh`（worktree で）を実行し、結果を報告に貼る。
2. 実装 → `cd <worktree>/backend && python -m pytest tests/<追加した試験> tests/test_companies*.py -q` の生出力を残す。
3. migration の静的確認: `{schema}` を書いていないこと、値の操作が無いことを `python3 scripts/check-migration-value-writes.py`（引数は scripts の usage に従う）で確かめる。使い方が分からなければ実行せず報告。
4. commit（メッセージ `feat: repoint companies.sales_rep_id to public.users (ADR-1008 P1)`、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）→ `git -C <worktree> push -u origin release/person-ssot-users-id`。
5. PR は作らない（設計者が作る）。

## 止まる条件

- フック・分類器に止められた → 言い換えず止まって報告。
- 実物がカードの行番号・内容と違う → 実装せず、違いを報告。
- 試験が失敗し、原因がカードの範囲外 → 止まって報告。

最終報告: 変更ファイル一覧（git diff --stat）、試験の生出力、push 結果、commit SHA。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <内容>。
