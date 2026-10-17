---
mode: handoff
---
# 設計 — S1 段階②a（Google カレンダー・Drive 接続設定の 2 表に RLS）

> この文書は何か：会社ごとの Google 接続情報を、データベース自身が「自社の行だけ見せる・書かせる」状態にする作り方です。

親: [docs/specs/tenant-rls/README.md](../../specs/tenant-rls/README.md)
**対象ADR**: ADR-1018、ADR-145、ADR-072、ADR-131、ADR-135、ADR-136
**recon**: [recon.md](recon.md)
**日付**: 2026-10-16
**状態**: 設計案作成済み・設計審査済み（[review-opus.md](review-opus.md)）。KGI は PO 承認済み（2026-10-15「y」）。実行は PO の 2026-10-16 一任（[ideal-state.md](../../specs/tenant-rls/ideal-state.md)）に基づく。

---

## 1. 狙い

1. アプリの SQL に tenant_id の書き忘れや注入があっても、他社の Google トークン（暗号化済み）が読めない・書き換えられないようにする（recon §2）。
2. 今動いている画面・処理（接続・解除・予定の読み書き・伝票の Drive 保存）は変えない。
3. 段階②を 2 便に分け、本便は Google 2 表のみ。suppliers は②b（共通行 288 行があり書込経路が多いため別便）。

## 2. 変更内容

### 2-1. 新 migration migrations/20261016_010000_add_google_config_rls.sql（新規）

```sql
-- S1 段階②a（ADR-1018）: Google 接続設定 2 表を会社別 RLS にする（tenant_carrier_credentials と同じ型）
ALTER TABLE public.tenant_google_calendar_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_google_calendar_config FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_google_calendar_config_tenant ON public.tenant_google_calendar_config;
CREATE POLICY tenant_google_calendar_config_tenant ON public.tenant_google_calendar_config
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

ALTER TABLE public.tenant_google_drive_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_google_drive_config FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_google_drive_config_tenant ON public.tenant_google_drive_config;
CREATE POLICY tenant_google_drive_config_tenant ON public.tenant_google_drive_config
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
```

`scripts/run_all_migrations.sh` の末尾（`run_sql migrations/20261015_130000_add_permissions_rls.sql` の次）に `run_sql migrations/20261016_010000_add_google_config_rls.sql` を 1 行追加。

### 2-2. アプリの修正（文脈を張らずに書く・読む経路）

| # | 場所（origin/main 46bb2f690 の行） | 変更前 | 変更後 | 理由 |
|---|---|---|---|---|
| 1 | backend/app/routers/google_calendar.py:123-124（`try:` の直後、`await db.execute(` の前） | 文脈なしで INSERT | `await set_tenant_context(db, tenant_id)` を追加。import（:30-34）に set_tenant_context を加える | 認証前の戻り先は app.tenant_id が空 → RLS で INSERT が拒否される（recon §3） |
| 2 | backend/app/routers/integrations.py:128-129（同上） | 文脈なしで INSERT | `await set_tenant_context(db, result["tenant_id"])` を追加（import 済み :40） | 同上 |
| 3 | backend/app/services/google_calendar.py:287 の次 | commit 後に再設定なし | `await reset_tenant_context(db, tenant_id)` を追加 | 直後の get_calendar_id（:327-338）が別接続で 0 行 → 'primary' に化ける |
| 4 | backend/app/services/google_drive_oauth.py:317 の次 | 同上 | 同上 | 一貫性（Drive も commit 後に同表を読む経路がありうる） |
| 5 | backend/app/services/google_webhook.py:113 の次、:156 の次 | 同上 | 同上（import :33 に reset_tenant_context を加える） | stop_webhook の後に register_webhook が _get_service で両表を読む（routers/calendar.py:494, :496） |

- 3・4 の import は `from app.auth.dependencies import reset_tenant_context` をファイル先頭に置く（google_webhook.py:33 と同じ書き方）。循環 import になる場合は関数内 import にする（card 想定分岐）。
- tenant_id を信じてよい理由: OAuth state は認証済みの connect_start が Redis に保存し、1 回限り・10 分で消費される（recon §4）。

### 2-3. 試験 backend/tests/test_google_config_rls.py（新規）

test_permissions_rls.py と同じ作り（両 URL が無ければ skip、asyncio）。準備は試験ファイル内の関数で、`bootstrap_tenant_schema(admin_engine, A)`・`(…, B)` で tenants を用意し、`public_bootstrap_lock` の中で `_apply_migration` により 076・20260606_010000・新 migration を流す（rls_bootstrap.py の共通一覧は tenants 作成前に流れるため触らない。recon §5）。作った行は試験の最後に admin で消す。

| 試験 | 期待 |
|---|---|
| ① catalog | 両表 relrowsecurity=t・relforcerowsecurity=t、ポリシー各 1 本 |
| ② 見える範囲 | admin で A・B の行を入れる → app 接続で app.tenant_id=A は A の 1 行のみ、文脈なしは 0 行（両表） |
| ③ 書けない範囲 | A 文脈で tenant_id=B の INSERT は 42501（insufficient_privilege）、B 行への UPDATE は 0 行（両表） |
| ④ OAuth 戻り先 | exchange_code をモックし、app 接続（文脈なし）の session で connect_callback を呼ぶ → 行が保存される（カレンダー・Drive 両方）。修正 #1・#2 が無いと失敗する回帰試験 |
| ⑤ commit 後の読取 | NullPool の app エンジン、A 文脈、calendar_id を既定外の値で入れ、トークン期限切れ扱い＋refresh をモックして `_refresh_if_needed` の後に `get_calendar_id` が既定外の値を返す。修正 #3 が無いと 'primary' になる回帰試験 |

## 3. 適用順と戻し方

1. 1 PR（Draft）。CI 緑 → Opus コード審査 → GO 記録（ADR-136。発行者 Claude Opus、根拠は PO 2026-10-16 一任）→ main → Deploy to VPS で migration が流れる。
2. アプリ修正と migration は同じデプロイで入る。migration が先に流れアプリ再起動前の数十秒に OAuth 戻り先が来ると保存失敗しうる（本番 calendar 0 行・Drive は 6/8 以降接続操作なし＝発生しうる確率は低い。失敗時は利用者に「接続失敗」と出て再接続で回復）。
3. 戻し方（ADMIN 接続で実行し、run_all から行を外す Revert PR）:
   ```sql
   DROP POLICY IF EXISTS tenant_google_calendar_config_tenant ON public.tenant_google_calendar_config;
   ALTER TABLE public.tenant_google_calendar_config NO FORCE ROW LEVEL SECURITY;
   ALTER TABLE public.tenant_google_calendar_config DISABLE ROW LEVEL SECURITY;
   DROP POLICY IF EXISTS tenant_google_drive_config_tenant ON public.tenant_google_drive_config;
   ALTER TABLE public.tenant_google_drive_config NO FORCE ROW LEVEL SECURITY;
   ALTER TABLE public.tenant_google_drive_config DISABLE ROW LEVEL SECURITY;
   ```
   アプリ修正（文脈の追加）は RLS が無くても無害なので戻さなくてよい。

## 4. 受入基準

| 基準 | 検証方法 |
|---|---|
| 他社の行が見えない・書けない | CI の test_google_config_rls.py ②③ が緑 |
| OAuth 接続の保存が壊れない | CI の ④ が緑（修正前は失敗する作り） |
| トークン更新後も設定を正しく読む | CI の ⑤ が緑 |
| 既存の試験が壊れない | CI の backend 試験全体が緑（既知の不安定試験は再実行で緑） |
| 本番で RLS が有効 | 本番 pg_class の両表 relrowsecurity/relforcerowsecurity = t/t、pg_policies 各 1 本 |
| 本番の既存データ不変 | Drive の (tenant_id, updated_at) が適用前（4, 2026-06-08 02:33）と同じ。calendar 0 行のまま |
| 本番アプリ接続での見え方 | salesanchor_app として、文脈なしで Drive 0 行、app.tenant_id='4' で 1 行（BEGIN; SET LOCAL ROLE …; ROLLBACK） |
| 本番エラーが増えない | デプロイ前後の backend ログで permission denied / row-level security / 5xx の件数を比較（適用直前に基準値を取る） |

## 5. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16/ddl-rowsecurity（段階① recon §3 で確認済み）: FORCE で表所有者にも適用、superuser・BYPASSRLS は素通り、ポリシーの式が NULL なら行は対象外。→ 文脈なしは 0 行・書込拒否となり「漏れ」より「止まる」側に倒れる。jarvis の migration は止まらない。
- 社内先例: tenant_carrier_credentials（2026-06 から同じ型で本番稼働、OAuth に似た保存経路で set_tenant_context を先に張る integrations.py:406-409）。数値の外部事例は、2 表・計 1 行の本便の成否を左右しないため用いない。

## 6. 弊害と対策

| 弊害 | 対策 |
|---|---|
| 文脈を張らない新しい経路を将来作ると、読めない（0 行）・書けない | 試験 ②〜⑤ が CI で毎回動く。ADR-1018 に「Google 2 表は会社別 RLS」と記す |
| commit 後の再設定漏れで設定が既定値に化ける | 修正 #3〜#5 と試験 ⑤ |
| デプロイ中の数十秒の OAuth 保存失敗 | §3-2。再接続で回復 |

## 7. 触らない範囲

frontend/、.github/、suppliers に関わる全ファイル（②b）、google_webhook_subscriptions（対象外表）、scripts/migration-guard/protected-tables.txt、backend/tests/rls_bootstrap.py、他の migration。

## 8. 計画・継続

②a 実装 → CI → GO 記録 → マージ・デプロイ → §4 の本番確認 → ②b（suppliers）の設計へ。段階③は方針を PO と決めてから（ADR-1018）。

## 9. 未解決事項

- OAuth 接続の実機通し確認は PO の GUI 操作が必要（実施しないまま②a を完了とし、README に「未実施」と記す）。

## 維持の仕組み

- 守り手（新設）: backend/tests/test_google_config_rls.py（CI の pytest で RLS の見え方・OAuth 保存・commit 後の読取を毎回検証）。
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
