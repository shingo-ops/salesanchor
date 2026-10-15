---
mode: handoff
---
# 設計 — S1 段階①（public.permissions に RLS）

> この文書は何か：権限の一覧表（permissions）を「誰でも読めるが、アプリからは書き換えられない」状態にする作り方です。

親: [docs/specs/tenant-rls/README.md](../../specs/tenant-rls/README.md)
**対象ADR**: ADR-1018（本テーマ・起案中）、ADR-145（手本）、ADR-072、ADR-131、ADR-135、ADR-136
**recon**: [recon.md](recon.md)
**日付**: 2026-10-15
**状態**: 設計案作成済み・設計審査済み（§10）。KGI は PO 承認済み（2026-10-15「y」）。実装未着手。

---

## 1. 狙い

1. アプリの接続役（salesanchor_app）から permissions を INSERT/UPDATE/DELETE できる穴を、DB 自身で塞ぐ（recon §2）。
2. 読み取りは今と同じ全 123 行を返す（画面・権限判定を変えない。recon §4）。
3. 表単位 REVOKE ではなく RLS を使う。理由：毎デプロイの全表再付与で REVOKE は戻る（recon §5）。

## 2. 変更内容

### 2-1. 新 migration `migrations/20261015_130000_add_permissions_rls.sql`

```sql
-- S1 段階①（ADR-1018）: public.permissions をアプリ接続から読み取り専用にする
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS permissions_read ON public.permissions;
CREATE POLICY permissions_read ON public.permissions
    FOR SELECT USING (true);

DROP POLICY IF EXISTS permissions_operator_write ON public.permissions;
CREATE POLICY permissions_operator_write ON public.permissions
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
```

- 何度流しても同じ結果（毎デプロイ全件再実行に耐える。recon §5）。
- 形は `migrations/20260628_170000_add_app_fx_rates.sql:46-63` と同じ。

### 2-2. `scripts/run_all_migrations.sh`

末尾（現 939 行の次）に 1 行追加:

```
run_sql migrations/20261015_130000_add_permissions_rls.sql
```

### 2-3. テスト `backend/tests/test_permissions_rls.py`（新規）

`backend/tests/test_countries_master.py:113-171` と同じ作りで、実 migration 適用後の DB に salesanchor_app で接続して確かめる。

| テスト | 期待 |
|---|---|
| SELECT 全件 | admin 接続で数えた行数と一致 |
| `app.is_operator` 未設定で INSERT / UPDATE / DELETE | INSERT は 42501（WITH CHECK 違反）。UPDATE / DELETE は 0 行（USING で見えない）かつ admin 接続で値不変 |
| `app.is_operator='true'` で INSERT | 成功（テスト内でロールバック） |
| pg_class | relrowsecurity = t、relforcerowsecurity = t、ポリシー 2 本 |

### 2-4. migration-guard チェック 8（PO 確認後に実施）

`scripts/check-migration-value-writes.py` の ALLOW_PATTERN に `CREATE\s+POLICY|DROP\s+POLICY|ALTER\s+POLICY` を追加し、同スクリプトのテストに許可・不許可の例を 1 件ずつ足す。

- 理由：POLICY は値を書く文ではなく構造の定義（ALTER TABLE と同じ扱い）。今のままだと保護表に RLS を付ける migration が全てブロックされる（recon §8）。
- ゲートの許可範囲を広げる変更のため、docs/STANDARD-WORKFLOW.md §8 により PO 確認必須。
- 不採用：行を分ける・EXECUTE 文字列で表名を隠す（ゲートの回避になる）。

## 3. 適用順と戻し方

1. ガード変更（2-4）を含めて 1 PR。CI 緑 → GO 記録（ADR-135/136、委任 ADR-1003）→ main → デプロイで migration が流れる。
2. 戻し方：次の SQL を ADMIN 接続で流し、migration 行を run_all から外す Revert PR。
   ```sql
   DROP POLICY IF EXISTS permissions_read ON public.permissions;
   DROP POLICY IF EXISTS permissions_operator_write ON public.permissions;
   ALTER TABLE public.permissions NO FORCE ROW LEVEL SECURITY;
   ALTER TABLE public.permissions DISABLE ROW LEVEL SECURITY;
   ```

## 4. 受入基準

| 基準 | 検証方法 |
|---|---|
| salesanchor_app で書き込めない | CI の `test_permissions_rls.py` が緑。本番で salesanchor_app として `BEGIN; UPDATE public.permissions SET display_order=display_order WHERE id=(SELECT min(id) FROM public.permissions); ROLLBACK;` が 0 行 |
| 読み取りは変わらない | 本番で salesanchor_app として `SELECT count(*)` が適用前と同じ（10/15 時点 123） |
| RLS が本番で有効 | 本番 `pg_class` の relrowsecurity / relforcerowsecurity が t、`pg_policies` が 2 本 |
| ログイン・権限画面が壊れない | 適用後に本番でログイン成功、ロール管理画面の権限一覧が表示、アプリログの permissions 関連エラーが適用前後で増えない |
| migration-guard が誤検知しない | 本 PR の migration-guard が緑。スクリプトのテストで `INSERT INTO public.permissions` は引き続きブロック |

## 5. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16/ddl-rowsecurity（recon §3）：superuser と BYPASSRLS 役は素通り、ポリシー無しは全拒否、permissive は OR。→ 読取用と運用者書込用の 2 本に分け、jarvis の migration は止まらない。
- 社内先例 ADR-145（products）・app_fx_rates：同じ型で本番稼働中。数値の外部事例は、本変更（読み取り専用化の 1 表）の成否を左右しないため用いない。

## 6. 弊害と対策

| 弊害 | 対策 |
|---|---|
| 将来アプリから permissions を書く機能を作ると拒否される | その時は `app.is_operator` を立てる経路に限定（app_fx_rates と同じ）。ADR-1018 に明記 |
| ADMIN 経路のスクリプト（sprint8/9）が止まる | jarvis は superuser で素通り（recon §2, §3）。影響なし |
| ガードの許可を広げると POLICY 行に紛れた値書込を見逃す | POLICY 文は値を書けない（構文上 INSERT/UPDATE を含められない）。テストで INSERT が引き続き止まることを確認 |

## 7. 触らない範囲

- 他 10 表（段階②・③）、`migrations/20260605_030000_create_salesanchor_app_role.sql`、`.github/workflows/*`、`protected-tables.txt`、frontend、backend のアプリコード。

## 8. 計画・継続

1. KGI の PO 承認（済）→ 2. ガード変更の PO 確認 → 3. 実装カード → Sonnet 実装 → CI → GO 記録 → マージ・デプロイ → §4 の本番確認 → 段階②へ。

## 9. 未解決事項

- 2-4 のガード変更の PO 確認。

## 10. 設計審査（Architect・同一 AI による自己審査）

**判定: APPROVE（条件付き）** — 条件は §9 の 2 件の PO 判断。

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | 適合。ADR-145 の型を踏襲、ADR-1013 の範囲に触れない | recon §1, §6 |
| 実物との整合 | 適合。アプリ書込 0 件、接続役 salesanchor_app | recon §2, §4 |
| CI との整合 | 条件付き。ガード変更なしでは migration-guard が赤 | recon §8 |
| 受入条件の検証可能性 | 適合。全行が SQL・テスト・画面で○×判定可 | §4 |
| 実装範囲の明確さ | 適合。ファイル 4 点（migration・run_all・テスト・ガード＋そのテスト） | §2, §7 |

## 維持の仕組み

- 守り手: `backend/tests/test_permissions_rls.py`（CI の pytest で salesanchor_app の書込拒否を毎回検証）
- 守り手: migration-guard チェック 8（保護表への値書込を引き続きブロック）
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
