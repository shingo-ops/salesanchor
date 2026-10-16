---
mode: handoff
---
# 設計 — S1 段階③便A（PayPal 設定・招待リンクの書込だけ RLS）

> この文書は何か：PayPal の接続設定と顧客への招待リンクを、他社の文脈から書き換え・削除できないようにデータベース自身で止めるための設計書です。読取はこれまでどおり全行可のままです。

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)、ADR-1018 段階③、ADR-072、ADR-145
**PO 決定**: 段階③は案 C（書込だけ RLS）— 2026-10-16 PO「y」
**状態**: 設計案作成済み → 審査は [review-opus.md](review-opus.md)

## 1. 目的と利用者に見える変化

- 目的: アプリ接続（salesanchor_app）から、自社以外の行を INSERT・UPDATE・DELETE できないようにする（自社の文脈 app.tenant_id と行の tenant_id が一致するときだけ書ける）。
- 利用者に見える変化: **なし**。
  - PayPal 接続の保存・削除、招待リンクの発行・使用はすべて自社の文脈で書く（recon §3 W1・W3〜W7）。
  - 読取は全行可のまま（招待リンクを開いた時点・PayPal の不服申立通知は会社が決まる前に全行から探すため。recon §4）。

## 2. 変更内容

### 2-1. migration（新規 1 本）

`migrations/20261016_160000_add_paypal_regtoken_write_rls.sql`（冪等。run_all_migrations.sh 末尾に登録）

各表に ENABLE / FORCE と 4 ポリシー。両表とも tenant_id は NOT NULL のため、②b の CASE（共通行）は不要。

```sql
-- 表ごとに <t> = tenant_paypal_config / registration_tokens
ALTER TABLE public.<t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.<t> FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS <t>_select ON public.<t>;
CREATE POLICY <t>_select ON public.<t> FOR SELECT USING (true);

DROP POLICY IF EXISTS <t>_insert ON public.<t>;
CREATE POLICY <t>_insert ON public.<t> FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS <t>_update ON public.<t>;
CREATE POLICY <t>_update ON public.<t> FOR UPDATE
  USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS <t>_delete ON public.<t>;
CREATE POLICY <t>_delete ON public.<t> FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
```

- 運営（app.is_operator）の通り道は**作らない**。2 表に運営が書く経路が 0 件のため（recon §3）。必要になったら別便で足す。
- 文脈なし（app.tenant_id 空）では NULLIF→NULL で比較が NULL＝書込不可（フェイルクローズ）。

### 2-2. アプリ修正（1 か所・1 行）

| 箇所 | 変更前 | 変更後 |
|---|---|---|
| backend/app/routers/integrations.py:561-562 | `if reg.get("ok") and reg.get("webhook_id"):` の直下で `await paypal_payments.save_webhook_id(...)` | その直前に `await reset_tenant_context(db, tenant_id)  # ADR-072: save_credentials の commit 後に文脈を張り直す` を 1 行追加 |

- 理由: W1 の commit 後に W2 を書くため、接続が替わると文脈が消え、RLS 導入後は webhook_id の保存が無言で 0 行になる（recon §3）。ADR-072 の既存規則（commit 直後に張り直す）に揃えるだけで、RLS が無くても挙動は同じ。
- `reset_tenant_context` は integrations.py で既に import 済み（:567 で使用）。
- 触らない: registration_tokens 側（W4〜W7 は文脈を張った後で commit 前に書く。recon §3）、読取経路、PayPal Webhook、Celery。

### 2-3. 試験（実 PostgreSQL・アプリ接続役。新規 backend/tests/test_paypal_regtoken_rls.py）

②b の backend/tests/test_suppliers_rls.py と同じ部品（実 migration を当てる・会社番号は 984/985 を使い他試験と重ねない）。

- ① 2 表とも RLS t/t・ポリシー 4 本ずつ
- ② 文脈なしでも全行を SELECT できる（招待リンク確認・不服申立通知の前提）
- ③ 会社 A の文脈で、会社 B の行への UPDATE・DELETE が 0 行、会社 B の tenant_id での INSERT が 42501。文脈なしの INSERT も 42501
- ④ 会社 A の文脈で自社行の INSERT・UPDATE・DELETE ができる
- ⑤ PUT /integrations/paypal/credentials の流れ（save_credentials → commit → 張り直し → save_webhook_id）で webhook_id が保存される。張り直しの 1 行を外すと失敗することを実測して記録する（接続の入れ替わりは、commit 後に別接続へ app.tenant_id を空で張った状態を作って再現する）
- ⑥ 会社 A の文脈で public.tenants の会社 B 行を DELETE すると、会社 B の 2 表の行も連鎖で消える（recon §5 の未確認を実測。消えなければ停止して Opus へ報告）
- ⑦ 招待リンクの公開 API 相当（verify_token → set_tenant_context → mark_token_used）で used_at が入る

## 3. 戻し方

```sql
DROP POLICY IF EXISTS tenant_paypal_config_select ON public.tenant_paypal_config;
DROP POLICY IF EXISTS tenant_paypal_config_insert ON public.tenant_paypal_config;
DROP POLICY IF EXISTS tenant_paypal_config_update ON public.tenant_paypal_config;
DROP POLICY IF EXISTS tenant_paypal_config_delete ON public.tenant_paypal_config;
ALTER TABLE public.tenant_paypal_config NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_paypal_config DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS registration_tokens_select ON public.registration_tokens;
DROP POLICY IF EXISTS registration_tokens_insert ON public.registration_tokens;
DROP POLICY IF EXISTS registration_tokens_update ON public.registration_tokens;
DROP POLICY IF EXISTS registration_tokens_delete ON public.registration_tokens;
ALTER TABLE public.registration_tokens NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.registration_tokens DISABLE ROW LEVEL SECURITY;
```
アプリ修正は Revert（張り直し 1 行のみ。RLS が無くても挙動は同じ）。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| CI で試験①〜⑦が実走して合格 | pytest-run-internal のログで test_paypal_regtoken_rls の passed 件数 |
| 試験⑤の張り直しを外すと失敗する | ローカル実 PG で 1 行外した複製を実行し失敗を記録 |
| 本番で 2 表が t/t・ポリシー 4 本ずつ | pg_class・pg_policies を SELECT |
| 本番の行数と内容が不変（tenant_paypal_config 1 行・registration_tokens 5 行） | 適用前後の count と md5(全行) |
| アプリ接続役で、別会社文脈・文脈なしから UPDATE すると 0 行、自社文脈では 1 行 | permit-danger 付き BEGIN…ROLLBACK |
| 反映後に backend ログの 42501 / row-level security / 5xx が 0 件 | docker compose logs を時間で絞って grep |
| 反映後に招待リンクの使用・PayPal 接続保存が起きたら成功している | registration_tokens.used_at・tenant_paypal_config.updated_at の反映後の更新（起きなければ「未観測」と記録） |

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| 書込経路の見落とし → 42501 で失敗 | recon で全リポジトリの参照を列挙（W1〜W8）。反映直後にログ確認、出たら §3 で即戻す |
| webhook_id が無言で保存されない | 2-2 の張り直し＋試験⑤ |
| 会社の物理削除で連鎖削除が止まる | 試験⑥で実測。PostgreSQL docs は参照整合の処理は RLS を通らないとする |
| 文脈が接続に別会社の値で残る | get_current_tenant・set_tenant_context は毎回上書き（dependencies.py:312・:358）。書込は必ずその後 |

## 6. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16 ddl-rowsecurity・sql-createpolicy（Context7 は月間上限のため公式を直接確認）: UPDATE/DELETE の USING 不一致は無言 0 行、INSERT の WITH CHECK 不一致は 42501、参照整合の処理は RLS を通らない → 試験③⑤⑥で無言 0 行と連鎖削除を明示的に確認する設計にした。
- 社内前例: 段階①（#4332）・②b（#4349）の「読取は広く・書込は文脈で絞る」型が本番で拒否エラー 0 件。今回はさらに共通行が無いため式が単純。
- 数値の外部事例は不要（社内前例と公式仕様で挙動を実測できるため）。

## 7. 触らない範囲

users・tenants・認証トークン 3 表（段階③の後続便。トークン 3 表は PO 質問 2 回答待ち）、PayPal Webhook・不服申立の読取、Celery、frontend。

## 維持の仕組み

- 守り手（新設）: backend/tests/test_paypal_regtoken_rls.py（CI の pytest で、他社行に書けない・自社行に書ける・webhook_id 保存・連鎖削除を毎回検証）。
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
- 状態は docs/specs/tenant-rls/README.md の段階③欄で管理する。
