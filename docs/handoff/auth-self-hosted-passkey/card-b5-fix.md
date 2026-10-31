# 実装カード 便5 追補 — 自社ログインの監査記録が「会社の指定が空」で 500 になる不具合を直す（backend のみ）

> この文書は何か：便5（#4939）の本番反映後、PO がパスキーを登録したところ 500 になった。原因は、自社ログインの口 6 か所が「会社の指定（app.tenant_id）を空にした直後」に監査記録（tenant_NNN.audit_logs）を書いていること。監査記録の表の行の制限は空の値を整数に直そうとして失敗する。この 6 か所を、会社を指定してから書く形に直す指示書です。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md（調べ書きは docs/handoff/auth-self-hosted-passkey/recon.md）
- 元の指示書: docs/handoff/auth-self-hosted-passkey/card-b5.md
- PO の実装承認: 2026-10-31「1」（審査に通れば便5 と ADR-1048 便7a〜7d を止めずに本番まで進める）と、2026-10-31 PO「不具合とエラー部分を省略せずに確認をして…安全に進めてくれ」
- 危険便: いいえ（コードと試験のみ。migrations・deploy・compose・secrets に触れない）
- 担当: 実装 Sonnet（クラウド）／コード審査 Opus 審査役／マージ Opus

## 1. 範囲

入れる: 下の §4 だけ。入れない: 監査記録の表の行の制限（ポリシー）の変更・migration・ほかの router・リファクタ・文言変更。

## 2. 前提の事実（2026-10-31・origin/main 06030c0aa 基準。本番は読むだけで確認）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 本番で `POST /api/v1/auth/passkey/register/verify` が 500。`asyncpg.exceptions.InvalidTextRepresentationError: invalid input syntax for type integer: ""`。失敗した文は `INSERT INTO tenant_001.audit_logs (...)`、引数 `(1, 1, 'create', 'webauthn_credentials', 1, None, '{"event": "passkey_registered"}')` | 本番 backend の docker logs（2026-10-31 16:07 の入れ替え後。入れ替え後の Error 行はこの 1 件だけ） |
| F2 | 本番の全会社（tenant_001・003・004・005・006）の audit_logs の制限は `tenant_id = (current_setting('app.tenant_id', true))::integer`。NULLIF が無いので、空文字だと整数に直す段で失敗する。ENABLE は真・FORCE は偽 | 本番 pg_policies・pg_class（READ ONLY） |
| F3 | 本番で `SET LOCAL ROLE salesanchor_app` のうえ、`app.tenant_id = '1'` なら tenant_001.audit_logs を読めて、`app.tenant_id = ''` なら F1 と同じ `invalid input syntax for type integer: ""` が出る（失敗を再現） | 本番 psql（BEGIN READ ONLY … ROLLBACK） |
| F4 | `clear_tenant_context` は `app.tenant_id` を `''` にする。`get_db` は毎回の終わりにこれを呼ぶので、プールに戻った接続は `''` のまま | `backend/app/auth/dependencies.py:414-432`、`backend/app/database.py:46-61` |
| F5 | `record_audit_log` は `INSERT INTO tenant_{id:03d}.audit_logs` を書くだけで、会社の指定はしない | `backend/app/services/audit.py:277-322` |
| F6 | `backend/app/routers/auth.py` の `record_audit_log(` 6 か所すべてが、会社の指定が空の状態で呼ばれる：:120（利用者の追加。直前 :117 で clear）・:502（パスワード再設定。:494 で clear）・:589（パスワード変更。:581 で clear）・:739（パスキー登録。:738 で clear）・:822（パスキーの使用回数の巻き戻し。この口では一度も set しないため、プールの `''` のまま）・:905（パスキー削除。:904 で clear） | `git grep -n "record_audit_log(" origin/main -- backend/app/routers/auth.py` |
| F7 | 「clear の直後に record_audit_log」の並びは backend/app の中で auth.py の 5 か所だけ（:822 は clear 無しで空のまま） | `git grep -n -A8 "clear_tenant_context(" origin/main -- 'backend/app/*.py'` の結果を record_audit_log で絞った |
| F8 | 本番 public.users の制限は NULLIF 付きで空でも失敗しない。public.webauthn_credentials・auth_refresh_tokens・password_reset_tokens は行の制限なし。よって直すのは監査記録の 6 か所だけ | 本番 pg_policies・pg_class（READ ONLY） |
| F9 | 本番のパスワード再設定・招待の鍵は使われた跡が 0 件（invite 1・reset 1、used_at はどちらも空）。本番 webauthn_credentials は 0 件。パスワード変更・利用者の追加が本番で通ったかは記録が入れ替えで消えていて未確認 | 本番 password_reset_tokens・webauthn_credentials（READ ONLY） |
| F10 | 試験で気づけなかった理由：普段の試験は SQLite で、`set_tenant_context`・`clear_tenant_context` は何もしない。PostgreSQL の試験（test_users_rls.py:444・:490 ほか）は `app.routers.auth.record_audit_log` を AsyncMock に差し替えている | `backend/app/auth/dependencies.py:317-328`・`:346`・`:430`、`backend/tests/test_users_rls.py:444`・`:490`、`backend/tests/test_passkeys.py:75-78` |
| F11 | 自動の試験には PostgreSQL 16 と `salesanchor_app`（NOSUPERUSER・NOBYPASSRLS）があり、`RLS_TEST_DATABASE_URL`（アプリ権限）と `RLS_ADMIN_DATABASE_URL`（管理者）で行の制限の試験を回せる | `.github/workflows/test.yml:121-246`、手本 `backend/tests/test_rls_carrier_credentials.py` |
| F12 | 本番 tenant_001.audit_logs の列：id bigint（連番）・tenant_id integer NOT NULL・user_id integer NOT NULL・action varchar NOT NULL・table_name varchar NOT NULL・record_id integer・old_data jsonb・new_data jsonb・created_at timestamptz default now() | 本番 information_schema.columns（READ ONLY） |

## 3. 触るファイル（これ以外は触らない）

- `backend/app/routers/auth.py`
- `backend/tests/test_rls_auth_audit.py`（新設）
- `backend/tests/test_auth_audit_helper.py`（新設）
- `docs/handoff/auth-self-hosted-passkey/card-b5-fix.md`（このカード。直さない）

## 4. 作り方

### 4.1 routers/auth.py に共通の関数を 1 つ足す

`_issue_session_tokens` などの小さな共通関数が並ぶ位置（`def _invalid_credentials` の直前）に足す:

```python
async def _record_auth_audit(
    db: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    action: str,
    table_name: str,
    record_id: int | None,
    new_data: dict,
) -> None:
    """自社ログインの監査記録を書く。

    audit_logs の行の制限は app.tenant_id を整数に直すため、空のままだと 500 になる。
    会社を指定してから書き、書いたら空に戻す（便5 追補）。
    """
    await set_tenant_context(db, tenant_id)
    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        new_data=new_data,
    )
    await clear_tenant_context(db)
```

`record_audit_log` は今の import（`from app.services.audit import record_audit_log`）をそのまま使う。既存の試験は `app.routers.auth.record_audit_log` を差し替えるので、この関数の中の呼び出しも差し替わる。

### 4.2 6 か所の `record_audit_log(` を `_record_auth_audit(` に置き換える

- 対象は F6 の :120・:502・:589・:739・:822・:905 の 6 か所。渡す値（tenant_id・user_id・action・table_name・record_id・new_data）は今のまま変えない。
- :120 は `db=db` のキーワード渡しなので、`_record_auth_audit(db, tenant_id=..., ...)` に直す。
- 既存の `set_tenant_context`・`clear_tenant_context` の呼び出しは、消さない・動かさない（重複して空に戻すのは害が無い。差分を最小にする）。
- 置き換えたあと、`backend/app/routers/auth.py` の中で `record_audit_log(` が現れるのは `_record_auth_audit` の中の 1 か所だけになる。

### 4.3 試験 1（本物の PostgreSQL・`backend/tests/test_rls_auth_audit.py`）

手本 `backend/tests/test_rls_carrier_credentials.py` と同じ作り（`RLS_TEST_DATABASE_URL` が無ければ skip、管理者接続で DDL、アプリ接続で確かめる）。

- 準備（管理者接続）: スキーマ `tenant_991` を作り、`tenant_991.audit_logs` を F12 と同じ列で作る。`ENABLE ROW LEVEL SECURITY` と、本番と同じ式のポリシー `USING (tenant_id = (current_setting('app.tenant_id', true))::integer)`（NULLIF を付けない）を作る。`salesanchor_app` に、スキーマの USAGE・表の SELECT/INSERT・連番の USAGE/SELECT を与える。後始末で `DROP SCHEMA tenant_991 CASCADE`。
- 試験 a（失敗の再現）: アプリ接続の `AsyncSession` で `clear_tenant_context` のあと `record_audit_log(tenant_id=991, ...)` を呼ぶと、`invalid input syntax for type integer` を含む例外になる。
- 試験 b（直したあと）: 新しいアプリ接続の `AsyncSession` で `clear_tenant_context` のあと `app.routers.auth._record_auth_audit(tenant_id=991, ...)` を呼ぶと例外にならない。commit 後、管理者接続で `tenant_991.audit_logs` に new_data の event が一致する行が 1 件ある。さらに呼び出し後のアプリ接続で `current_setting('app.tenant_id', true)` が `''` に戻っている。
- 試験 c（:822 の形）: `clear_tenant_context` を呼ばない新しい接続（app.tenant_id を一度も設定していない）でも `_record_auth_audit` が例外にならない。

### 4.4 試験 2（SQLite で動く・`backend/tests/test_auth_audit_helper.py`）

- `backend/app/routers/auth.py` の本文を読み、`ast` で関数ごとに見て、`record_audit_log` を呼ぶ関数が `_record_auth_audit` の 1 つだけであること。
- `_record_auth_audit` の中で `set_tenant_context` → `record_audit_log` → `clear_tenant_context` の順に呼ばれること（3 つを `unittest.mock` で差し替え、呼ばれた順を記録して比べる）。

既存の試験は消さない・弱めない。

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

1. 修正前（4.1・4.2 の前）に試験 2 の「record_audit_log を呼ぶ関数が 1 つだけ」が失敗することを確かめ、失敗の最終行を貼る（TDD の順）
2. 手元またはクラウドに PostgreSQL 16 を立てられる場合は、`.github/workflows/test.yml:121-205` と同じ手順で `salesanchor_app` を作り、`RLS_TEST_DATABASE_URL`・`RLS_ADMIN_DATABASE_URL` を付けて `python -m pytest -q tests/test_rls_auth_audit.py -v` を実行し、a・b・c の結果を貼る。立てられない場合はその事実を書き、CI の pytest の結果で確かめる（推測で通ったと書かない）
3. `cd backend && python -m pytest -q tests/test_passkeys.py tests/test_self_auth.py tests/test_password_reset.py tests/test_register_invite.py tests/test_auth_audit_helper.py` の最終行
4. `cd backend && ruff check app/routers/auth.py tests/test_rls_auth_audit.py tests/test_auth_audit_helper.py` の結果
5. `git diff origin/main...HEAD --name-only` が §3 のファイルだけ

## 6. 分岐ごとの対処

| 状況 | 対処 |
|---|---|
| 試験 2 が修正前でも通る | 試験が的外れ。実装に進まず `NEEDS_DECISION:` で返す |
| 試験 a が失敗を再現しない（例外にならない） | 試験の表・ポリシーが本番と違う。直さずに `NEEDS_DECISION:` で、作った DDL を貼って返す |
| 既存の試験が `_record_auth_audit` の追加で落ちる | 落ちた試験名と生の出力を貼って `NEEDS_DECISION:` |
| §3 以外のファイルを触る必要が出た | 止まって `NEEDS_DECISION:` |
| フックに止められた | 言い換えて再試行しない。`BLOCKED:` で返す |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 本番と同じ行の制限のもとで、会社の指定が空の接続からでも自社ログインの監査記録が書ける | 試験 1 の b・c が CI の PostgreSQL で成功 |
| 試験が本番の失敗を再現できている | 試験 1 の a が成功（例外を確かめる） |
| auth.py の監査記録がすべて共通の関数を通る | 試験 2 |
| 既存の挙動が変わらない | 既存の試験と CI がすべて成功 |
| 本番でパスキーの登録が通る | 反映後、PO の端末で登録して一覧に 1 件出る。本番の記録に register/verify の 201 が出て、tenant_001.audit_logs に passkey_registered の行が 1 件増える（読むだけで確認） |

## 8. PR

- ブランチ: release/auth-audit-tenant-fix（origin/main 起点）
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon・設計・このカード・ADR-1013・触るファイルを書く
- `backend/app/routers` を触るので `### GO記録` を書く（委任 GO。migration なし）
- マージは Opus が CI・審査役 APPROVE を確かめてから行う
