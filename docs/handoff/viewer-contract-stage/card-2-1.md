# card: 便2-1 契約手続き中（contracting）の状態の土台（ADR-1061）

状態: カード発行（Opus、2026-11-12）。PO の設計承認と実装承認は 2026-11-12「1、推測は禁止して…確立したなら進める。」（ideal-state 54。review.md「2026-11-12 PO の設計承認」）。
設計: docs/handoff/viewer-contract-stage/design.md §3-1・§3-2・§3-3（:91 履歴の操作）・§8 の A4・A6・A13・A34・§9。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `e00216e2188f2174f6e188d4ccf4ce5e10bf2f57` で行番号を測った。`a26c89fda`（#5422 合流後）で P2・P5・P6 と 2-2 を測り直した（変わったのは run_all_migrations.sh の最後の登録だけ）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` と本番 `scripts/run_all_migrations.sh` を含む。CI の `.github/workflows/migration-test.yml` の前提の表も2か所変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 便2 を 2-1（状態の土台）と 2-2 以降（表・税率の画面・会社情報のページ）に分ける。理由: 1便1目的（design-partner.md §5.5 の4）。2-1 は状態を足す移行と、その状態を読む場所だけで閉じる。表の作成は別の移行にして、戻すときの範囲を小さくする。
- D2 この便では contracting へ入る道を作らない（「契約に進む」の API とボタンは便4、design.md §4）。だから本番で contracting の人は 0 人のまま。この便の効果は「入る道を作ったときに、どの入口でも止まらない」こと。
- D3 期限の自動延長（§3-2 フォーム送信）は contracting の人だけに行う。active の人は期限を判定に使わない（viewer_dependencies.py:87）。お試しの人にはフォームを送れない（409 のまま）。
- D4 form_sent の履歴は contracting と active の両方で残す（§3-2「履歴は viewer_status_changes に残す。actor は操作した人」）。from_status と to_status は同じ値。期限が動かないときは from_expires_at と to_expires_at が同じ値。actor は 'po'、actor_user_id は押した最高管理者。
- D5 延長（extend）は trial と contracting に許す（§3-3「手続き中の人にも『延長』を出す」）。ボタンは便4。API とコマンドはこの便で通す。
- D6 「本契約にする」（activate）は trial のままにする。お試しから本契約へ直接移す道を外すのは便4（§3-3 :92）。
- D7 一覧の行の色は Badge の金型の variant `warning` を使う（frontend/src/components/Badge.tsx:16 の BadgeVariant に在る）。色を直書きしない。
- D8 期限切れの理由の名前は viewer_contract_expired（§3-1 :53）。文は ja「閲覧期限が過ぎています。担当者にご連絡ください。」・en「Your viewing period has ended. Please contact your representative.」。案内の画面（NoticeView）の題は ja「閲覧期限が過ぎています」・en「Viewing period has ended」、説明は ja「担当者にご連絡ください。」・en「Please contact your representative.」。
- D9 触らないと決めた場所（全件 grep で見つかったが変えない）: backend/app/discord_gateway/viewer_interview_notice.py:3・:57（面談案内はお試しだけ。§3-1 :55）・backend/app/discord_gateway/viewer_trial.py:352（申込中から来た人だけ trial にする行。contracting の人は :348 の if に入らず状態を保つ）・backend/app/services/viewer_admin.py:340・:350（初回登録の取り込み。trial と active だけを受ける）・backend/app/services/tcg_distribution_svc.py:737（`va.status <> 'active'` で active 以外は配らない。§3-1 :54）・frontend/src/pages/super-admin/ViewerAccountsPage.tsx:441（お試しの行のボタン。便4）・同 :725（請求先の欄の active。便4）・backend/app/viewer_admin_cli.py:13（便4）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（contracting の状態を足し、その状態を読む全部の場所を揃える。D1） |
| 5 | 既存ブランチへの追記ではない | ○（Opus が origin/main から作った新しい枝 `release/viewer-contracting-bin2-1` にこのカードだけが載っている） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（状態を読む場所は origin/main で `git grep` した 30 行（§0-3 P6。うち閲覧者と無関係の3行は触らない）。掃除の境目は便1 と同じ 1090 日と 1100 日。鍵の期限の幅は今の試験 test_viewer_billing_form_pg.py:206 と同じ ±2 分） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-contracting-bin2-1 HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便2-1 契約手続き中の状態の土台 の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-2-1.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261112_120000_create_public_customer_statuses.sql`（a26c89fda で実測）。
- P3 `grep -c "ck_viewer_accounts_status CHECK (status IN ('pending', 'verified', 'trial', 'active', 'suspended'))" migrations/20261016_150000_add_viewer_accounts.sql` が 1。
- P4 `grep -c "BILLING_FORM_TTL = timedelta(days=7)" backend/app/services/viewer_billing_form.py` が 1。
- P5 `grep -rn "contracting" backend/app frontend/src migrations | wc -l` が 0。
- P6 次の全件 grep が 30 行で、行の場所が下の表と同じ（e00216e21 で実測）。

    git grep -n -E "status (=|IN) '(trial|active)'|status (==|!=) \"(trial|active)\"|\(\"(pending|suspended|trial)\", \"(trial|active)\"|\[\"pending\", \"trial\"|viewer_trial_expired|STOP_DETAILS =" -- backend/app frontend/src/pages frontend/src/locales/viewer

| ファイル:行 | この便で |
|---|---|
| backend/app/auth/viewer_dependencies.py:86・:88・:91 | 足す（2-4） |
| backend/app/discord_gateway/viewer_interview_notice.py:57 | 触らない（D9） |
| backend/app/discord_gateway/viewer_trial.py:318 | 直す（2-9） |
| backend/app/routers/companies.py:982 | 閲覧者と無関係。触らない |
| backend/app/routers/dashboard.py:148 | 閲覧者と無関係。触らない |
| backend/app/routers/viewer.py:65・:190・:195・:202 | 直す（2-5） |
| backend/app/services/discord_own_staff_sync.py:164 | 閲覧者と無関係。触らない |
| backend/app/services/viewer_admin.py:231 | 触らない（activate。D6） |
| backend/app/services/viewer_admin.py:255 | 直す（2-6 (a) 延長） |
| backend/app/services/viewer_admin.py:340・:350 | 触らない（D9） |
| backend/app/services/viewer_admin.py:381 | 直す（2-6 (b)） |
| backend/app/services/viewer_billing_form.py:97・:138・:167 | 直す（2-7） |
| backend/app/tasks/maintenance.py:217 | 直す（2-10） |
| frontend/src/locales/viewer/en.json:174・ja.json:174 | 足す（2-14） |
| frontend/src/pages/super-admin/ViewerAccountsPage.tsx:94・:451 | 直す（2-12） |
| frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx:9 | 直す（2-12 (d)） |
| frontend/src/pages/viewer/LoginView.tsx:24・:25 | 足す（2-13） |
| frontend/src/pages/viewer/ViewerApp.tsx:52・:60 | 直す（2-13） |

  30 行でない・表に無い場所が出た → 実装せず、出力を貼って `BLOCKED: P6`。ViewerAccountsPage.tsx:441（`row.status === "trial"`）は grep の形に合わないので出ないが、触らない（D9）。

## 1. 触るファイル

1. migrations/20261112_130000_add_viewer_contracting_status.sql（新規）
2. scripts/run_all_migrations.sh
3. backend/app/auth/viewer_dependencies.py
4. backend/app/routers/viewer.py
5. backend/app/services/viewer_admin.py
6. backend/app/services/viewer_billing_form.py
7. backend/app/routers/super_admin_viewers.py
8. backend/app/discord_gateway/viewer_trial.py
9. backend/app/tasks/maintenance.py
10. frontend/api-contract/openapi.json（手順6 の生成だけで変える。手で書かない）
11. frontend/src/pages/super-admin/ViewerAccountsPage.tsx
12. frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx
13. frontend/src/pages/super-admin/LoginRequestsPage.tsx
14. frontend/src/pages/viewer/ViewerApp.tsx
15. frontend/src/pages/viewer/types.ts
16. frontend/src/pages/viewer/NoticeView.tsx
17. frontend/src/pages/viewer/LoginView.tsx
18. frontend/src/locales/ja.json
19. frontend/src/locales/en.json
20. frontend/src/locales/viewer/ja.json
21. frontend/src/locales/viewer/en.json
22. backend/tests/test_super_admin_viewers.py
23. backend/tests/test_viewer_billing_form_pg.py
24. backend/tests/test_viewer_purge.py
25. backend/tests/test_viewer_api.py
26. backend/tests/test_viewer_tokens.py
27. backend/tests/test_tcg_distribution_viewer_link_pg.py
28. frontend/src/pages/viewer/ViewerApp.test.tsx
29. frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx（試験の題名だけ）
30. .github/workflows/migration-test.yml（CI の前提の表の最小定義だけ。2-2b）

触らない: これ以外のすべて。特に D9 の場所・`.github/` の migration-test.yml 以外（2-2b の2か所だけ変える）・`deploy.yml`・`backend/app/services/tcg_distribution_svc.py`・`backend/app/viewer_admin_cli.py`・`frontend/src/components/`（金型は変えない）・既存の migration。

## 2. 変更

### 2-1 migrations/20261112_130000_add_viewer_contracting_status.sql（新規。この全文で作る）

```sql
-- ADR-1061 便2-1: 閲覧者の状態に contracting（契約手続き中）を足し、
-- 状態の履歴の操作に start_contract・form_sent・invoice_issued・confirm_payment を足す
-- 足すだけ（今の行の値は変えない）。RLS は付けない（名簿は public の全体共通の表のまま）
-- 冪等（CHECK は DROP CONSTRAINT IF EXISTS → ADD で同じ名前のまま付け替え）
-- ロールバック: contracting の行と新しい操作の行が無いことを確かめてから、
--   20261016_150000_add_viewer_accounts.sql の2つの CHECK に付け替え直す（PO GO）

BEGIN;

ALTER TABLE public.viewer_accounts DROP CONSTRAINT IF EXISTS ck_viewer_accounts_status;
ALTER TABLE public.viewer_accounts ADD CONSTRAINT ck_viewer_accounts_status
    CHECK (status IN ('pending', 'verified', 'trial', 'contracting', 'active', 'suspended'));
COMMENT ON COLUMN public.viewer_accounts.status IS 'pending／verified／trial／contracting／active／suspended。verified は将来用。contracting は契約手続き中（ADR-1061）';
COMMENT ON COLUMN public.viewer_accounts.trial_expires_at IS 'お試しと契約手続き中の、見られる期限';

ALTER TABLE public.viewer_status_changes DROP CONSTRAINT IF EXISTS ck_viewer_status_changes_action;
ALTER TABLE public.viewer_status_changes ADD CONSTRAINT ck_viewer_status_changes_action
    CHECK (action IN ('activate', 'suspend', 'unsuspend', 'extend', 'start_trial',
                      'start_contract', 'form_sent', 'invoice_issued', 'confirm_payment'));
COMMENT ON COLUMN public.viewer_status_changes.action IS 'activate／suspend／unsuspend／extend／start_trial／start_contract／form_sent／invoice_issued／confirm_payment';

COMMIT;
```

### 2-2 scripts/run_all_migrations.sh（最後の登録の後ろに2行足す）

変更前（a26c89fda の scripts/run_all_migrations.sh:1258-1259。#5422 の会社と連絡先の状態の表が最後）:
```bash
# 会社と連絡先の状態 便1: 状態の表 public.customer_statuses を作る（作るだけ・冪等）
run_sql migrations/20261112_120000_create_public_customer_statuses.sql
```
変更後:
```bash
# 会社と連絡先の状態 便1: 状態の表 public.customer_statuses を作る（作るだけ・冪等）
run_sql migrations/20261112_120000_create_public_customer_statuses.sql
# ADR-1061 便2-1: 閲覧者の状態に contracting と履歴の操作4つを足す（CHECK の付け替え・足すだけ・冪等）
run_sql migrations/20261112_130000_add_viewer_contracting_status.sql
```
`run_sql migrations/20261112_120000_create_public_customer_statuses.sql` の後ろに別の行が在るときは、実装せず `BLOCKED: P2`（main がまた進んだ。Opus が指示書を直す）。ファイル名の時刻を 130000 にしたのは、同じ日の 120000 を #5422 が先に使ったため（同じ時刻の名前を2つ作らない）。

### 2-2b .github/workflows/migration-test.yml（CI の「マイグレーションSQL 実行」の前提の表）

理由: このジョブは変わった移行だけを、前提の最小の表の上で流す。今の最小の表 public.viewer_accounts には trial_expires_at の列が無く、public.viewer_status_changes は無い。このままでは 2-1 の COMMENT と ALTER TABLE が失敗する。前例は同じ場所の viewer_login_tokens の最小定義（20261105_120000 のために足した）。審査 2026-11-12 の高の指摘で足した。

(a) 変更前:
```yaml
          -- public.viewer_accounts: 20261016_150000_add_viewer_accounts.sql で本番作成済み。
          --   20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql が外部キーで参照するため、
          --   前提として最小定義を登録する（id の型は本物と同じ BIGSERIAL）。
          CREATE TABLE IF NOT EXISTS public.viewer_accounts (
              id         BIGSERIAL   PRIMARY KEY,
              email      TEXT        NOT NULL,
              line_name  TEXT        NOT NULL,
              status     TEXT        NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
```
変更後:
```yaml
          -- public.viewer_accounts: 20261016_150000_add_viewer_accounts.sql で本番作成済み。
          --   20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql が外部キーで参照するため、
          --   前提として最小定義を登録する（id の型は本物と同じ BIGSERIAL）。
          --   trial_expires_at は 20261112_130000_add_viewer_contracting_status.sql が COMMENT を書くため（ADR-1061 便2-1）。
          CREATE TABLE IF NOT EXISTS public.viewer_accounts (
              id         BIGSERIAL   PRIMARY KEY,
              email      TEXT        NOT NULL,
              line_name  TEXT        NOT NULL,
              status     TEXT        NOT NULL,
              trial_expires_at TIMESTAMPTZ NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
```

(b) 変更前（viewer_login_tokens の最小定義の閉じ）:
```yaml
              CONSTRAINT ck_viewer_login_tokens_purpose CHECK (purpose IN ('signup_code', 'password_reset'))
          );
```
変更後:
```yaml
              CONSTRAINT ck_viewer_login_tokens_purpose CHECK (purpose IN ('signup_code', 'password_reset'))
          );
          -- public.viewer_status_changes: 20261016_150000_add_viewer_accounts.sql で本番作成済み。
          --   20261112_130000_add_viewer_contracting_status.sql が CHECK を付け替え COMMENT を書くため、
          --   前提として最小定義を登録する（操作の CHECK は付け替え前の5値）。
          CREATE TABLE IF NOT EXISTS public.viewer_status_changes (
              id        BIGSERIAL   PRIMARY KEY,
              viewer_id BIGINT      NOT NULL REFERENCES public.viewer_accounts(id) ON DELETE CASCADE,
              action    TEXT        NOT NULL,
              CONSTRAINT ck_viewer_status_changes_action CHECK (action IN ('activate', 'suspend', 'unsuspend', 'extend', 'start_trial'))
          );
```
この2か所以外の .github/ は変えない。字下げは前後の行に合わせる（YAML の run: の中の SQL）。

### 2-3 （欠番。2-4 から順に行う）

### 2-4 backend/app/auth/viewer_dependencies.py:86〜:94

変更前:
```python
    if row.status == "active":
        pass
    elif row.status == "trial":
        expires = _as_utc(row.trial_expires_at)
        if expires is None or expires <= now:
            raise _forbidden("viewer_trial_expired")
    elif row.status == "suspended":
```
変更後:
```python
    if row.status == "active":
        pass
    elif row.status == "trial":
        expires = _as_utc(row.trial_expires_at)
        if expires is None or expires <= now:
            raise _forbidden("viewer_trial_expired")
    elif row.status == "contracting":  # 契約手続き中（ADR-1061）。期限まで見られる
        expires = _as_utc(row.trial_expires_at)
        if expires is None or expires <= now:
            raise _forbidden("viewer_contract_expired")
    elif row.status == "suspended":
```

### 2-5 backend/app/routers/viewer.py

(a) :65 変更前:
```python
_RESET_MAIL_STATUSES = ("trial", "active")
```
変更後:
```python
_RESET_MAIL_STATUSES = ("trial", "contracting", "active")
```

(b) :190〜:202 変更前:
```python
    if row is not None and password_ok and row.status in ("suspended", "trial", "active"):
        if row.status == "suspended":
            await _record_event(db, row.id, "login_failed", ip, user_agent)
            await db.commit()
            raise HTTPException(status_code=403, detail="viewer_suspended")
        if row.status == "trial":
            expires = row.trial_expires_at
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires is None or expires <= datetime.now(timezone.utc):
                await _record_event(db, row.id, "login_failed", ip, user_agent)
                await db.commit()
                raise HTTPException(status_code=403, detail="viewer_trial_expired")
```
変更後:
```python
    if row is not None and password_ok and row.status in ("suspended", "trial", "contracting", "active"):
        if row.status == "suspended":
            await _record_event(db, row.id, "login_failed", ip, user_agent)
            await db.commit()
            raise HTTPException(status_code=403, detail="viewer_suspended")
        if row.status in ("trial", "contracting"):
            expires = row.trial_expires_at
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires is None or expires <= datetime.now(timezone.utc):
                await _record_event(db, row.id, "login_failed", ip, user_agent)
                await db.commit()
                detail = "viewer_trial_expired" if row.status == "trial" else "viewer_contract_expired"
                raise HTTPException(status_code=403, detail=detail)
```
:329・:391 の `_RESET_MAIL_STATUSES` を使う行は変えない。

### 2-6 backend/app/services/viewer_admin.py

(a) 延長（`else:  # extend` の中。e00216e21 で :254〜:256。:231 の activate の同じ形の行は変えない）変更前:
```python
    else:  # extend
        if from_status != "trial":
            raise ViewerAdminError("conflict")
```
変更後:
```python
    else:  # extend（お試しと契約手続き中。ADR-1061 §3-3）
        if from_status not in ("trial", "contracting"):
            raise ViewerAdminError("conflict")
```

(b) 申込コードの再発行（:381）変更前:
```python
    if row[0] not in ("pending", "trial", "active"):
        raise ViewerAdminError("conflict")
```
変更後:
```python
    if row[0] not in ("pending", "trial", "contracting", "active"):
        raise ViewerAdminError("conflict")
```
:231 付近の activate の `trial` の条件と :340・:350 は変えない（D6・D9）。

### 2-7 backend/app/services/viewer_billing_form.py

(a) :20 変更前:
```python
BILLING_FORM_TTL = timedelta(days=7)
PURPOSE = "billing_form"
```
変更後:
```python
BILLING_FORM_TTL = timedelta(days=3)  # ADR-1061 §3-2
PURPOSE = "billing_form"
# フォームを送れる・開ける・保存できる状態（契約手続き中と本契約。ADR-1061 §3-1）
FORM_STATUSES = ("contracting", "active")
```

(b) issue_billing_form_token の全体（:84〜:112）変更前:
```python
async def issue_billing_form_token(db: AsyncSession, viewer_id: int) -> tuple[str, datetime]:
    """請求先フォームの鍵の唯一の作り口。本契約（active）の人だけ。

    名簿に無ければ ViewerAdminError("not_found")、active でなければ ViewerAdminError("conflict")。
    同じ人の古い billing_form の鍵を消してから1本作り、(鍵, 期限) を返す。
    """
    row = (
        await db.execute(
            text("SELECT status FROM public.viewer_accounts WHERE id = :id"), {"id": viewer_id}
        )
    ).first()
    if row is None:
        raise ViewerAdminError("not_found")
    if row.status != "active":
        raise ViewerAdminError("conflict")
    await db.execute(
        text("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id = :id AND purpose = 'billing_form'"),
        {"id": viewer_id},
    )
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + BILLING_FORM_TTL
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
            "VALUES (:id, :h, 'billing_form', :exp)"
        ),
        {"id": viewer_id, "h": token_sha256(raw), "exp": expires_at},
    )
    return raw, expires_at
```
変更後:
```python
async def issue_billing_form_token(db: AsyncSession, viewer_id: int, *, actor_user_id: int) -> tuple[str, datetime]:
    """請求先フォームの鍵の唯一の作り口。契約手続き中（contracting）と本契約（active）の人だけ。

    名簿に無ければ ViewerAdminError("not_found")、FORM_STATUSES でなければ ViewerAdminError("conflict")。
    同じ人の古い billing_form の鍵を消してから1本作り、(鍵, 期限) を返す。
    契約手続き中の人は、見られる期限を max(今の期限, 鍵の期限) にする（短くしない。ADR-1061 §3-2）。
    送った記録 form_sent を viewer_status_changes に残す（actor='po'・actor_user_id は押した人）。
    """
    row = (
        await db.execute(
            text("SELECT status, trial_expires_at FROM public.viewer_accounts WHERE id = :id FOR UPDATE"),
            {"id": viewer_id},
        )
    ).first()
    if row is None:
        raise ViewerAdminError("not_found")
    if row.status not in FORM_STATUSES:
        raise ViewerAdminError("conflict")
    await db.execute(
        text("DELETE FROM public.viewer_login_tokens WHERE viewer_account_id = :id AND purpose = 'billing_form'"),
        {"id": viewer_id},
    )
    now = datetime.now(timezone.utc)
    raw = secrets.token_urlsafe(32)
    expires_at = now + BILLING_FORM_TTL
    await db.execute(
        text(
            "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
            "VALUES (:id, :h, 'billing_form', :exp)"
        ),
        {"id": viewer_id, "h": token_sha256(raw), "exp": expires_at},
    )
    from_expires = row.trial_expires_at
    if from_expires is not None and from_expires.tzinfo is None:
        from_expires = from_expires.replace(tzinfo=timezone.utc)
    to_expires = from_expires
    if row.status == "contracting":
        to_expires = expires_at if from_expires is None else max(from_expires, expires_at)
        await db.execute(
            text("UPDATE public.viewer_accounts SET trial_expires_at = :exp, updated_at = :now WHERE id = :id"),
            {"exp": to_expires, "now": now, "id": viewer_id},
        )
    await db.execute(
        text(
            "INSERT INTO public.viewer_status_changes "
            "(viewer_id, action, from_status, to_status, from_expires_at, to_expires_at, "
            "extend_days, actor, actor_user_id, created_at) "
            "VALUES (:vid, 'form_sent', :st, :st, :from_expires, :to_expires, NULL, 'po', :uid, :now)"
        ),
        {
            "vid": viewer_id,
            "st": row.status,
            "from_expires": from_expires,
            "to_expires": to_expires,
            "uid": actor_user_id,
            "now": now,
        },
    )
    return raw, expires_at
```

(c) peek_token（:130〜:143）変更前の2行:
```python
    """鍵を使い切らずに確かめる。有効で本契約（active）の人なら viewer_account_id、それ以外は None。"""
```
```python
                "AND t.expires_at > :now AND a.status = 'active'"
            ),
            {"h": token_sha256(raw), "now": datetime.now(timezone.utc)},
```
変更後の2行:
```python
    """鍵を使い切らずに確かめる。有効で FORM_STATUSES の人なら viewer_account_id、それ以外は None。"""
```
```python
                "AND t.expires_at > :now AND a.status IN :statuses"
            ).bindparams(bindparam("statuses", expanding=True)),
            {"h": token_sha256(raw), "now": datetime.now(timezone.utc), "statuses": list(FORM_STATUSES)},
```
そして :15 の import を変える。変更前:
```python
from sqlalchemy import text
```
変更後:
```python
from sqlalchemy import bindparam, text
```

(d) is_active（:161〜:167）変更前:
```python
    return row is not None and row.status == "active"
```
変更後:
```python
    return row is not None and row.status in FORM_STATUSES
```
関数の名前 is_active は変えない（呼び出し元 backend/app/routers/viewer.py:564 を変えないため）。

### 2-8 backend/app/routers/super_admin_viewers.py

(a) :71〜:72 変更前:
```python
    status: str = Field(..., description="pending／verified／trial／active／suspended")
    trial_expires_at: datetime | None = Field(None, description="お試しの期限")
```
変更後:
```python
    status: str = Field(..., description="pending／verified／trial／contracting／active／suspended")
    trial_expires_at: datetime | None = Field(None, description="お試しと契約手続き中の、見られる期限")
```

(b) send_billing_form_endpoint（:426〜:440）変更前:
```python
async def send_billing_form_endpoint(
    viewer_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
```
```python
        raw, expires_at = await viewer_billing_form.issue_billing_form_token(db, viewer_id)
```
変更後:
```python
async def send_billing_form_endpoint(
    viewer_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
```
```python
        raw, expires_at = await viewer_billing_form.issue_billing_form_token(
            db, viewer_id, actor_user_id=int(current_user.id)
        )
```
`# ② 古い鍵を消して新しい鍵を1本作る（本契約の人だけ）` の注記は `# ② 古い鍵を消して新しい鍵を1本作る（契約手続き中と本契約の人だけ。手続き中は期限を延ばす）` に変える。デコレータの `dependencies=[Depends(require_super_admin)]` は残す（:348〜:353 の activate_endpoint と同じ形）。

### 2-9 backend/app/discord_gateway/viewer_trial.py:318

変更前:
```python
                    or v[2] not in ("pending", "trial", "active")
```
変更後:
```python
                    or v[2] not in ("pending", "trial", "contracting", "active")
```
:352 は変えない（D9）。

### 2-10 backend/app/tasks/maintenance.py（purge_viewer_accounts）

(a) 説明の1行 変更前:
```python
    1. 見られる期限（trial_expires_at）から 3 年たった trial
```
変更後:
```python
    1. 見られる期限（trial_expires_at）から 3 年たった trial と contracting（契約手続き中）
```

(b) :217 変更前:
```python
                "WHERE status = 'trial' AND trial_expires_at < NOW() - make_interval(years => :y)"
```
変更後:
```python
                "WHERE status IN ('trial', 'contracting') AND trial_expires_at < NOW() - make_interval(years => :y)"
```
戻り値の名前 `trial_expired` は変えない（ログと既存の試験が読む）。

### 2-11 （欠番）

### 2-12 管理画面（最高管理者の閲覧者の画面）

(a) frontend/src/pages/super-admin/ViewerAccountsPage.tsx:77〜:94 変更前:
```tsx
const STATUS_VARIANT: Record<string, BadgeVariant> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  pending: "neutral",
  verified: "neutral",
};

const STATUS_KEY: Record<string, string> = {
  pending: "statusPending",
  verified: "statusVerified",
  trial: "statusTrial",
  active: "statusActive",
  suspended: "statusSuspended",
};

/** 左メニューに出す状態（この順）。verified・suspended は出さない（「すべて」には含まれる） */
const MENU_STATUSES = ["pending", "trial", "active"] as const;
```
変更後:
```tsx
const STATUS_VARIANT: Record<string, BadgeVariant> = {
  active: "success",
  trial: "info",
  contracting: "warning",
  suspended: "danger",
  pending: "neutral",
  verified: "neutral",
};

const STATUS_KEY: Record<string, string> = {
  pending: "statusPending",
  verified: "statusVerified",
  trial: "statusTrial",
  contracting: "statusContracting",
  active: "statusActive",
  suspended: "statusSuspended",
};

/** 左メニューに出す状態（この順）。verified・suspended は出さない（「すべて」には含まれる） */
const MENU_STATUSES = ["pending", "trial", "contracting", "active"] as const;
```

(b) 同 :451 変更前:
```tsx
          {["pending", "trial", "active"].includes(row.status) && !row.discord_channel_url && (
```
変更後:
```tsx
          {["pending", "trial", "contracting", "active"].includes(row.status) && !row.discord_channel_url && (
```

(c) 同 :474〜:479 変更前:
```tsx
  const menuCounts: Record<MenuKey, number> = {
    all: countOf("all"),
    pending: countOf("pending"),
    trial: countOf("trial"),
    active: countOf("active"),
  };
```
変更後:
```tsx
  const menuCounts: Record<MenuKey, number> = {
    all: countOf("all"),
    pending: countOf("pending"),
    trial: countOf("trial"),
    contracting: countOf("contracting"),
    active: countOf("active"),
  };
```
:441（`row.status === "trial"`）と :725（`active={detail.status === "active"}`）は変えない（D9）。

(d) frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx:9 変更前:
```tsx
export const USER_MENU_STATUSES = ["pending", "trial", "active"] as const;
```
変更後:
```tsx
export const USER_MENU_STATUSES = ["pending", "trial", "contracting", "active"] as const;
```

(e) frontend/src/pages/super-admin/LoginRequestsPage.tsx:15 変更前:
```tsx
const STATUS_KEY = { pending: "statusPending", trial: "statusTrial", active: "statusActive" } as const;
```
変更後:
```tsx
const STATUS_KEY = {
  pending: "statusPending",
  trial: "statusTrial",
  contracting: "statusContracting",
  active: "statusActive",
} as const;
```

(f) frontend/src/locales/ja.json（superAdmin.viewers の中。e00216e21 で :2965）変更前:
```json
      "statusTrial": "お試し",
      "statusActive": "本契約",
```
変更後:
```json
      "statusTrial": "お試し",
      "statusContracting": "契約手続き中",
      "statusActive": "本契約",
```
frontend/src/locales/en.json（同じ場所。:2965）変更前:
```json
      "statusTrial": "Trial",
      "statusActive": "Active",
```
変更後:
```json
      "statusTrial": "Trial",
      "statusContracting": "Contracting",
      "statusActive": "Active",
```

### 2-13 閲覧者の画面

(a) frontend/src/pages/viewer/ViewerApp.tsx:52〜:60 変更前:
```tsx
const STOP_DETAILS = new Set(["viewer_suspended", "viewer_trial_expired", "password_change_required"]);
```
```tsx
    if (err.detail === "viewer_trial_expired") return { name: "notice", kind: "expired" };
```
変更後:
```tsx
const STOP_DETAILS = new Set([
  "viewer_suspended",
  "viewer_trial_expired",
  "viewer_contract_expired",
  "password_change_required",
]);
```
```tsx
    if (err.detail === "viewer_trial_expired") return { name: "notice", kind: "expired" };
    if (err.detail === "viewer_contract_expired") return { name: "notice", kind: "contractExpired" };
```

(b) frontend/src/pages/viewer/types.ts:56 変更前:
```ts
export type ViewerNoticeKind = "preparing" | "suspended" | "expired" | "error";
```
変更後:
```ts
export type ViewerNoticeKind = "preparing" | "suspended" | "expired" | "contractExpired" | "error";
```

(c) frontend/src/pages/viewer/NoticeView.tsx:19〜:20 変更前:
```tsx
    case "expired":
      return { title: t("viewer.notice.expired.title"), description: t("viewer.notice.expired.description") };
```
変更後:
```tsx
    case "expired":
      return { title: t("viewer.notice.expired.title"), description: t("viewer.notice.expired.description") };
    case "contractExpired":
      return {
        title: t("viewer.notice.contractExpired.title"),
        description: t("viewer.notice.contractExpired.description"),
      };
```

(d) frontend/src/pages/viewer/LoginView.tsx:24〜:25 変更前:
```tsx
      case "viewer_trial_expired":
        return t("viewer.error.viewer_trial_expired");
```
変更後:
```tsx
      case "viewer_trial_expired":
        return t("viewer.error.viewer_trial_expired");
      case "viewer_contract_expired":
        return t("viewer.error.viewer_contract_expired");
```

### 2-14 閲覧者の画面の文（frontend/src/locales/viewer/）

(a) ja.json:174 変更前:
```json
      "viewer_trial_expired": "お試し期間が終了しています。",
```
変更後:
```json
      "viewer_trial_expired": "お試し期間が終了しています。",
      "viewer_contract_expired": "閲覧期限が過ぎています。担当者にご連絡ください。",
```
ja.json の notice（:193〜:196）変更前:
```json
      "expired": {
        "title": "お試し期間が終了しました",
        "description": "ご利用期間が終了しています。"
      },
```
変更後:
```json
      "expired": {
        "title": "お試し期間が終了しました",
        "description": "ご利用期間が終了しています。"
      },
      "contractExpired": {
        "title": "閲覧期限が過ぎています",
        "description": "担当者にご連絡ください。"
      },
```

(b) en.json:174 変更前:
```json
      "viewer_trial_expired": "Your trial period has ended.",
```
変更後:
```json
      "viewer_trial_expired": "Your trial period has ended.",
      "viewer_contract_expired": "Your viewing period has ended. Please contact your representative.",
```
en.json の notice（:193〜:196）変更前:
```json
      "expired": {
        "title": "Trial period ended",
        "description": "Your usage period has ended."
      },
```
変更後:
```json
      "expired": {
        "title": "Trial period ended",
        "description": "Your usage period has ended."
      },
      "contractExpired": {
        "title": "Viewing period has ended",
        "description": "Please contact your representative."
      },
```

### 2-15 試験

(a) backend/tests/test_super_admin_viewers.py の `_prepare`（:188。この1行だけを old_string にする）変更前:
```python
    cur.execute((MIGRATIONS / "20261020_120000_create_viewer_message_templates.sql").read_text())
```
変更後:
```python
    cur.execute((MIGRATIONS / "20261020_120000_create_viewer_message_templates.sql").read_text())
    # ADR-1061 便2-1: 状態 contracting と履歴の操作4つ
    cur.execute((MIGRATIONS / "20261112_130000_add_viewer_contracting_status.sql").read_text())
```
すぐ下の `    if seed_templates:  # 送る側は…` の行は変えない。
同じファイルの test_conflicts_are_409 の後ろに、次の試験を足す:
```python
@needs_ci_pg
def test_extend_is_allowed_for_contracting(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare(conn, async_url)
    vid = _account(cur, "contracting-extend@x.com", "contracting", expires_in_days=2)
    # 本契約にする（activate）は、手続き中からはまだできない（D6）
    assert _error_code(async_url, vid, "activate") == "conflict"
    _change(async_url, vid, "extend", days=7)
    assert _state(cur, vid)[0] == "contracting"
    rows = _changes(cur, vid)
    assert [(r[0], r[1], r[2], r[5], r[6], r[7]) for r in rows] == [
        ("extend", "contracting", "contracting", 7, "po", ACTOR_ID)
    ]
```
（延長の起点は「今」。viewer_admin.py の `to_expires = current + timedelta(days=days)`。だから期限の差は確かめない。）

(b) backend/tests/test_viewer_purge.py の `_prepare`（:40〜:42）変更前:
```python
    cur.execute((MIGRATIONS / "20261105_120000_create_viewer_billing_profiles.sql").read_text())
    return cur
```
変更後:
```python
    cur.execute((MIGRATIONS / "20261105_120000_create_viewer_billing_profiles.sql").read_text())
    # ADR-1061 便2-1: 状態 contracting
    cur.execute((MIGRATIONS / "20261112_130000_add_viewer_contracting_status.sql").read_text())
    return cur
```
test_trial_is_kept_3_years_after_expiry の後ろに、次の試験を足す（A13）:
```python
@needs_ci_pg
def test_contracting_is_kept_3_years_after_expiry(pg):  # noqa: F811
    conn, engine, async_url = pg
    cur = _prepare(conn, async_url)
    _account(cur, "c1100@x.com", "contracting", trial_days_ago=1100)
    _account(cur, "c1090@x.com", "contracting", trial_days_ago=1090)
    result = _run_purge(engine)
    assert result["trial_expired"] == 1
    assert _emails(cur) == ["c1090@x.com"]
```

(c) backend/tests/test_viewer_billing_form_pg.py

import（:21〜:26）変更前:
```python
from tests.test_super_admin_viewers import (
    _account,
    _api,
    _prepare,
    needs_ci_pg,
)
```
変更後:
```python
from tests.test_super_admin_viewers import (
    ACTOR_ID,
    _account,
    _api,
    _changes,
    _prepare,
    needs_ci_pg,
)
```
:206〜:220 の試験の名前と期限を3日にする。変更前:
```python
def test_send_expiry_is_seven_days_and_room_and_mail_are_called(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "seven@x.com", "active")
```
```python
    assert timedelta(days=7) - timedelta(minutes=2) <= expires - before <= timedelta(days=7, minutes=2)
```
```python
    assert mail_mock.call_count == 1 and mail_mock.call_args.args[0] == "seven@x.com"
```
変更後:
```python
def test_send_expiry_is_three_days_and_room_and_mail_are_called(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "three@x.com", "active")
```
```python
    assert timedelta(days=3) - timedelta(minutes=2) <= expires - before <= timedelta(days=3, minutes=2)
```
```python
    assert mail_mock.call_count == 1 and mail_mock.call_args.args[0] == "three@x.com"
```
:248 の `@pytest.mark.parametrize("status", ["pending", "verified", "trial", "suspended"])` は変えない（お試しの人には送れないまま）。その試験の最後の assert の後ろに1行足す:
```python
    assert _changes(cur, vid) == []
```
test_send_to_non_contracted_is_409_with_no_key の後ろに、次の3つの試験を足す（A4・D3・D4）:
```python
@needs_ci_pg
def test_send_to_contracting_with_short_expiry_moves_it_to_key_expiry(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "c-short@x.com", "contracting", expires_in_days=-1)
    before = datetime.now(timezone.utc)
    resp, _, mail_mock = _send(async_url, vid)
    assert resp.status_code == 200 and mail_mock.call_count == 1
    cur.execute("SELECT expires_at FROM public.viewer_login_tokens WHERE viewer_account_id = %s", (vid,))
    key_expires = cur.fetchone()[0]
    cur.execute("SELECT status, trial_expires_at FROM public.viewer_accounts WHERE id = %s", (vid,))
    status, expires = cur.fetchone()
    assert status == "contracting" and expires == key_expires
    assert timedelta(days=3) - timedelta(minutes=2) <= expires - before <= timedelta(days=3, minutes=2)
    rows = _changes(cur, vid)
    assert [(r[0], r[1], r[2], r[5], r[6], r[7]) for r in rows] == [
        ("form_sent", "contracting", "contracting", None, "po", ACTOR_ID)
    ]
    assert rows[0][4] == key_expires and rows[0][3] < rows[0][4]


@needs_ci_pg
def test_send_to_contracting_with_long_expiry_keeps_it(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "c-long@x.com", "contracting", expires_in_days=10)
    cur.execute("SELECT trial_expires_at FROM public.viewer_accounts WHERE id = %s", (vid,))
    old = cur.fetchone()[0]
    resp, _, _ = _send(async_url, vid)
    assert resp.status_code == 200
    cur.execute("SELECT trial_expires_at FROM public.viewer_accounts WHERE id = %s", (vid,))
    assert cur.fetchone()[0] == old
    rows = _changes(cur, vid)
    assert [(r[0], r[3], r[4], r[6], r[7]) for r in rows] == [("form_sent", old, old, "po", ACTOR_ID)]


@needs_ci_pg
def test_send_to_active_records_form_sent_and_keeps_no_expiry(pg):  # noqa: F811
    conn, _, async_url = pg
    cur = _prepare_billing(conn, async_url)
    vid = _account(cur, "a-form@x.com", "active")
    resp, _, _ = _send(async_url, vid)
    assert resp.status_code == 200
    cur.execute("SELECT status, trial_expires_at FROM public.viewer_accounts WHERE id = %s", (vid,))
    assert cur.fetchone() == ("active", None)
    rows = _changes(cur, vid)
    assert [(r[0], r[1], r[2], r[3], r[4], r[6], r[7]) for r in rows] == [
        ("form_sent", "active", "active", None, None, "po", ACTOR_ID)
    ]
```

(d) backend/tests/test_viewer_api.py:308〜:322（test_login_suspended_and_expired_trial_with_correct_password）変更前:
```python
        make_viewer(vid=3, email="n@x.com", status="trial", trial_expires_at=None),
    )
    async with _Client(db) as http:
        suspended = await _login(http, email="s@x.com")
        expired = await _login(http, email="t@x.com")
        no_expiry = await _login(http, email="n@x.com")
    assert (suspended.status_code, suspended.json()["detail"]) == (403, "viewer_suspended")
    assert (expired.status_code, expired.json()["detail"]) == (403, "viewer_trial_expired")
    assert (no_expiry.status_code, no_expiry.json()["detail"]) == (403, "viewer_trial_expired")
    assert [e["event_type"] for e in db.events] == ["login_failed"] * 3
```
変更後:
```python
        make_viewer(vid=3, email="n@x.com", status="trial", trial_expires_at=None),
        make_viewer(vid=4, email="c@x.com", status="contracting", trial_expires_at=NOW - timedelta(days=1)),
    )
    async with _Client(db) as http:
        suspended = await _login(http, email="s@x.com")
        expired = await _login(http, email="t@x.com")
        no_expiry = await _login(http, email="n@x.com")
        contract_expired = await _login(http, email="c@x.com")
    assert (suspended.status_code, suspended.json()["detail"]) == (403, "viewer_suspended")
    assert (expired.status_code, expired.json()["detail"]) == (403, "viewer_trial_expired")
    assert (no_expiry.status_code, no_expiry.json()["detail"]) == (403, "viewer_trial_expired")
    assert (contract_expired.status_code, contract_expired.json()["detail"]) == (403, "viewer_contract_expired")
    assert [e["event_type"] for e in db.events] == ["login_failed"] * 4
```
同じファイルに、期限内の手続き中の人がログインできる試験を足す（test_login_success_returns_token_and_must_change_flag の後ろ）:
```python
async def test_login_contracting_within_expiry_succeeds(redis):
    db = FakeDb(make_viewer(status="contracting", trial_expires_at=NOW + timedelta(days=2)))
    async with _Client(db) as http:
        resp = await _login(http)
    assert resp.status_code == 200
```

(e) backend/tests/test_viewer_tokens.py の test_statuses（:138〜:156）の最後の2行の後ろに足す:
```python
    assert await _status_of(token, _row(status="contracting", trial_expires_at=now + timedelta(days=1))) == 200
    with pytest.raises(HTTPException) as exc:
        await _call(token, _row(status="contracting", trial_expires_at=now - timedelta(seconds=1)))
    assert exc.value.status_code == 403 and exc.value.detail == "viewer_contract_expired"
```

(f) backend/tests/test_tcg_distribution_viewer_link_pg.py:93 変更前:
```python
    for status in ("trial", "pending", "verified"):
```
変更後:
```python
    for status in ("trial", "contracting", "pending", "verified"):
```
その上の注記 `# お試し・pending・verified → not_contracted。本契約にすると配信される` は `# お試し・契約手続き中・pending・verified → not_contracted。本契約にすると配信される（A34）` に変える。

(g) frontend/src/pages/viewer/ViewerApp.test.tsx の T9（:98〜:104）の後ろ、`});`（describe の閉じ）の前に足す:
```tsx
  it("T9b: a 403 viewer_contract_expired on refresh shows the contract expired notice without clearing the token", async () => {
    await mountWithFirstData();
    fetchMock.mockRejectedValueOnce(new ViewerApiError(403, "viewer_contract_expired"));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(screen.getByTestId("viewer-notice-contractExpired")).toBeTruthy();
    expect(clearToken).not.toHaveBeenCalled();
  });
```

(h) frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx:206 の試験の題名だけ変える（判定の中身は変えない。左のメニューは5つになる）。変更前:
```tsx
it("shows a left menu with 4 entries (no Suspended) and counts, and filters by trial with ?status=trial", async () => {
```
変更後:
```tsx
it("shows a left menu with 5 entries (no Suspended) and counts, and filters by trial with ?status=trial", async () => {
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contracting-bin2-1 && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P6 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-1.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && grep -c "ck_viewer_accounts_status CHECK (status IN ('pending', 'verified', 'trial', 'active', 'suspended'))" migrations/20261016_150000_add_viewer_accounts.sql
    cd ~/sa && grep -c "BILLING_FORM_TTL = timedelta(days=7)" backend/app/services/viewer_billing_form.py
    cd ~/sa && grep -rn "contracting" backend/app frontend/src migrations | wc -l
    cd ~/sa && git grep -n -E "status (=|IN) '(trial|active)'|status (==|!=) \"(trial|active)\"|\(\"(pending|suspended|trial)\", \"(trial|active)\"|\[\"pending\", \"trial\"|viewer_trial_expired|STOP_DETAILS =" -- backend/app frontend/src/pages frontend/src/locales/viewer | tail -30

手順3 §2 の変更をする（2-1 から 2-15 の順。新規の migration は Write ツール、それ以外は Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    python3.12 --version 2>&1 | tail -1
    python3.12 -m venv ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    ~/venv312/bin/ruff --version | tail -1
  python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）:
    uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形（期待: ruff は All checks passed!、残りの grep は順に 1・1・1・1・1・2・2）
    cd ~/sa && ~/venv312/bin/ruff check backend/app/auth/viewer_dependencies.py backend/app/routers/viewer.py backend/app/services/viewer_admin.py backend/app/services/viewer_billing_form.py backend/app/routers/super_admin_viewers.py backend/app/discord_gateway/viewer_trial.py backend/app/tasks/maintenance.py backend/tests/test_super_admin_viewers.py backend/tests/test_viewer_billing_form_pg.py backend/tests/test_viewer_purge.py backend/tests/test_viewer_api.py backend/tests/test_viewer_tokens.py backend/tests/test_tcg_distribution_viewer_link_pg.py 2>&1 | tail -10
    cd ~/sa && grep -c "BILLING_FORM_TTL = timedelta(days=3)" backend/app/services/viewer_billing_form.py
    cd ~/sa && grep -c "^run_sql migrations/20261112_130000_add_viewer_contracting_status.sql" scripts/run_all_migrations.sh
    cd ~/sa && grep -c "viewer_contract_expired" backend/app/auth/viewer_dependencies.py
    cd ~/sa && grep -c "viewer_contract_expired" backend/app/routers/viewer.py
    cd ~/sa && grep -c "status IN ('trial', 'contracting')" backend/app/tasks/maintenance.py
    cd ~/sa && grep -c "viewer_contract_expired" frontend/src/locales/viewer/ja.json frontend/src/locales/viewer/en.json | tail -2
    cd ~/sa && grep -c "statusContracting" frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
    cd ~/sa && grep -c "trial_expires_at TIMESTAMPTZ NULL,\|ck_viewer_status_changes_action CHECK" .github/workflows/migration-test.yml
  最後から2つ目と3つ目は各ファイル 1（ファイルごとに `ファイル名:1` と出る）。最後の grep は 2。

手順6 API の形を作り直す（openapi.json は手で書かない）
    cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -3
    cd ~/sa && git diff --stat frontend/api-contract/openapi.json | tail -3
    cd ~/sa && grep -c "お試しと契約手続き中の、見られる期限" frontend/api-contract/openapi.json
  期待: diff は openapi.json の数行。最後の grep は 1 以上。

手順7 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_viewer_api.py tests/test_viewer_tokens.py tests/test_super_admin_viewers.py tests/test_viewer_billing_form_pg.py tests/test_viewer_purge.py tests/test_tcg_distribution_viewer_link_pg.py 2>&1 | tail -15

手順8 frontend の点検と試験
    cd ~/sa/frontend && npm ci 2>&1 | tail -3
    cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -3
    cd ~/sa/frontend && npx tsc --noEmit 2>&1 | tail -15
    cd ~/sa/frontend && npx eslint src/pages/viewer src/pages/super-admin/ViewerAccountsPage.tsx src/pages/super-admin/LoginRequestsPage.tsx src/pages/super-admin/users 2>&1 | tail -15
    cd ~/sa/frontend && npm run check:i18n-missing-keys 2>&1 | tail -5
    cd ~/sa/frontend && npm run check:error-text-next-action 2>&1 | tail -5
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/viewer src/pages/super-admin/ViewerAccountsPage.test.tsx src/pages/super-admin/LoginRequestsPage.test.tsx src/pages/super-admin/users 2>&1 | tail -15
  期待: tsc と eslint は何も出ない（または 0 problems）。2つの check は成功。vitest は failed 0。

手順9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -40
    cd ~/sa && git diff --stat | tail -40
  期待: §1 の 30 ファイル（新規の migration は `??` で1行）だけ。frontend/src/api/generated の変化は git に載らない（追跡されていない）。

手順10 記録と送り出し
    cd ~/sa && git add migrations/20261112_130000_add_viewer_contracting_status.sql scripts/run_all_migrations.sh .github/workflows/migration-test.yml backend/app frontend/api-contract/openapi.json frontend/src/pages frontend/src/locales backend/tests && git status --short | tail -40
    cd ~/sa && git commit -q -m "feat(viewer): add contracting status foundation and 3-day billing form with expiry extension (ADR-1061 bin2-1)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/viewer-contracting-bin2-1 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contracting-bin2-1 -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P6 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順6 の生成が失敗した → 最後の 3 行を貼って `BLOCKED: openapi`。
  - 手順7 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - 手順8 の tsc・eslint・check・vitest が失敗した → 最後の 15 行を貼って `BLOCKED: frontend`。書き写し間違いの扱いは上と同じ。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - 手順7 で skipped が多い → そのまま書く（実 PostgreSQL の試験は CI で動く）。
  - 手順8 の npm ci で警告（WARN）が出た → そのまま書く。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-contracting-bin2-1 HEAD=…`。2 行目: 「本報告はカード 便2-1 契約手続き中の状態の土台 の実行結果である」。
- 手順2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の migration だけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
