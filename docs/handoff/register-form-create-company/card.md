# 実装カード: 受信箱の登録フォームで会社を作る

- 区分: B-1（`backend/app/routers/registration_tokens.py` と試験 1 ファイルだけ。migration・フロント・deploy 設定は無し）
- 枝: `release/register-form-create-company`（設計 docs はこの枝に入っている。同じ枝に足す）
- 設計: `docs/handoff/register-form-create-company/design.md`・recon: 同 `recon.md`

## 1. 作業前の点検

- `git log --oneline -1` が設計のコミット（題に `register-form-create-company`）であること。
- `backend/app/routers/registration_tokens.py` が 568 行、241 行が `        text("SELECT id, billing_display_name FROM companies WHERE lead_id = :lead_id"),`、247 行が `            status_code=status.HTTP_404_NOT_FOUND,` であること。違えば止めて `BLOCKED:`。

## 2. 触るもの／触らないもの

- 触る: `backend/app/routers/registration_tokens.py`（import と `register_customer` の中だけ）、新しい `backend/tests/test_public_register_company.py`。
- 触らない: それ以外の全部。特に `add_address`・`change_billing`・`create_token`・`verify_registration_token`・`backend/app/routers/companies.py`・`backend/tests/conftest.py`・フロント・migrations。

## 3. 手順

### 3-1 import

- `from app.auth.dependencies import (...)` に `is_postgresql` を足す。
- `from app.cache import invalidate_dashboard_cache` と `from app.services.customer_statuses import STATUS_ACTIVE` を足す（どちらも `backend/app/routers/companies.py` 29 行・48-52 行と同じ書き方）。

### 3-2 `register_customer`（今の 236-251 行の「リードに紐づく会社 ID・請求先名を取得」から `billing_display_name_fallback` の行まで）を次の形にする

```python
    # 同じリードの会社作りを 2 本同時に走らせない（PostgreSQL のみ。試験の SQLite は FOR UPDATE 不可）
    lead_sql = "SELECT company_name, customer_name FROM leads WHERE id = :lead_id"
    if is_postgresql(db):
        lead_sql += " FOR UPDATE"
    lead_row = (await db.execute(text(lead_sql), {"lead_id": lead_id})).first()
    if not lead_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_not_found")

    # companies.lead_id が SSOT（leads に company_id 列はない）
    # billing_display_name は担当者名フォールバック用（ADR-126 §0）
    result = await db.execute(
        text("SELECT id, billing_display_name FROM companies WHERE lead_id = :lead_id ORDER BY id LIMIT 1"),
        {"lead_id": lead_id},
    )
    row = result.first()
    company_created = False
    if row and row[0]:
        company_id = row[0]
        billing_display_name_fallback: str = row[1] or ""
    else:
        # ADR-097 §3: 既存リード情報＋顧客入力で会社を自動生成する。CRM 属性は担当者が後付け（§4）
        name = next(
            (v.strip() for v in (lead_row[0], lead_row[1], data.billing_display_name) if v and v.strip()),
            "",
        )
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="company_name_required")
        created = await db.execute(
            text("""
                INSERT INTO companies (tenant_id, company_code, lead_id, name, status)
                VALUES (:tenant_id, :company_code, :lead_id, :name, :status)
                RETURNING id
            """),
            {
                "tenant_id": tenant_id,
                "company_code": f"CO-PEND-{uuid.uuid4().hex[:8]}",
                "lead_id": lead_id,
                "name": name,
                "status": STATUS_ACTIVE,
            },
        )
        company_id = created.scalar_one()
        await db.execute(
            text("UPDATE companies SET company_code = :code WHERE id = :id"),
            {"code": f"CO-{company_id:05d}", "id": company_id},
        )
        company_created = True
        billing_display_name_fallback = data.billing_display_name or ""
```

- 型の注釈 `billing_display_name_fallback: str` は 1 回だけにする（mypy が二重の注釈で怒るなら、上で `billing_display_name_fallback: str = ""` を宣言して両方で代入する形に直してよい）。
- 末尾の `await reset_tenant_context(db, tenant_id)` の直後に足す:

```python
    if company_created:
        await invalidate_dashboard_cache(tenant_id)
```

- それ以外の行（請求先名の UPDATE・住所の INSERT・担当者の INSERT・トークンの使用済み・commit）は 1 字も変えない。docstring に「会社が無ければ作る（ADR-097 §3）」を 1 行足してよい。

### 3-3 試験 `backend/tests/test_public_register_company.py`

- 前例: `backend/tests/test_companies.py`（`client` の fixture と `tests.helpers_txn.create_lead`）。リンクは `POST /api/v1/registration-tokens` に `{"lead_id": <id>, "type": "register"}` を送って `token` を受け取る。送信は `POST /api/v1/public/register`。
- 本文の例（RegisterPage.tsx 211-221 行と同じ形）: `addresses` に billing（`is_default: true`・`address_line_1`・`country_code: "US"`・`name`）と delivery（`is_default: true`）、`billing_display_name: "Acme Billing"`、`contact_email` など。
- 3 つの試験:
  1. 会社の無いリード（`company_name` あり）→ 200。`companies` にそのリードの行が 1 件・`name` がリードの `company_name`・`company_code` が `CO-` で始まり `CO-PEND` でない・`company_addresses` が 2 件・`contacts` が 1 件。
  2. 会社のあるリード（先に `tests.helpers_txn.create_company(client, lead_id)` で 1 件作る）→ 200。会社は 1 件のまま。住所と担当者はその会社に付く。
  3. `company_name` が空（None か ""）のリード → 会社の `name` がリードの `customer_name`。
- `create_lead` が `company_name` を受け取れないなら、作った後に `UPDATE leads SET company_name = ... WHERE id = ...` で整えてよい（`db_session` の fixture を使う）。conftest は触らない。

## 4. 確かめ（全部の生出力を残す）

- `cd backend && python -m pytest tests/test_public_register_company.py tests/test_viewer_isolation.py tests/test_registration_token_schema.py -q`
- `cd backend && ruff check app/routers/registration_tokens.py tests/test_public_register_company.py` と `mypy app/routers/registration_tokens.py`（設定は `backend/pyproject.toml` のまま）。
- `git diff --numstat`。
- 失敗したら直してよいのは 2 の「触る」の範囲だけ。範囲外が要るなら `BLOCKED:`。

## 5. 送り方

- 1 コミット。`git push origin release/register-form-create-company`。PR は作らない（Opus が作る）。
- 最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。
