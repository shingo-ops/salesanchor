# 実装カード: 登録フォームの最初の配送先を「いつもの配送先」にする

- 区分: B-1（backend 1 ファイルの 1 関数と試験 1 ファイル。migration・フロント・deploy 設定なし）
- 枝: `release/register-delivery-default`（設計 docs はこの枝にある。同じ枝に足す）
- 設計: `docs/handoff/register-delivery-default/design.md`・recon: 同 `recon.md`

## 1. 作業前の点検

- `backend/app/routers/registration_tokens.py` が 607 行。305 行が `    # 住所を登録`、307 行が `    for addr in data.addresses:`、337 行が `                    "is_default": addr.is_default,` であること。違えば止めて `BLOCKED:`。

## 2. 触るもの／触らないもの

- 触る: `backend/app/routers/registration_tokens.py` の `register_customer` の 305-347 行だけ。`backend/tests/test_public_register_company.py`。
- 触らない: それ以外の全部。特に `add_address`（472 行の `addr.is_default` はそのまま）・`change_billing`・フロント・migrations・`backend/tests/conftest.py`。

## 3. 手順

### 3-1 305 行 `    # 住所を登録` の直前に足す

```python
    # 配送先の default はサーバーで決める: 会社にまだ default の配送先が無ければ、送られた中の最初の 1 件を default にする。
    # 請求先は送られた値のまま（already_registered の 409 判定を変えない）。
    has_default_delivery = (
        await db.execute(
            text(
                "SELECT 1 FROM company_addresses "
                "WHERE company_id = :cid AND address_type = 'delivery' AND is_default = TRUE LIMIT 1"
            ),
            {"cid": company_id},
        )
    ).first() is not None
```

### 3-2 `for addr in data.addresses:` の直後（`try:` の前）に足す

```python
        if addr.address_type == "delivery":
            is_default = not has_default_delivery
            has_default_delivery = True
        else:
            is_default = addr.is_default
```

### 3-3 337 行を `                    "is_default": is_default,` に変える（register_customer の中の 1 か所だけ）

### 3-4 試験 `backend/tests/test_public_register_company.py` の class の末尾に 2 件足す

```python
    async def test_separate_delivery_becomes_default(self, client, db_session):
        lead_id = await create_lead(client, "配送先別")
        token = await _issue_token(client, lead_id)
        form = _form(token)
        form["addresses"][1]["is_default"] = False

        res = await client.post("/api/v1/public/register", json=form)
        assert res.status_code == 200, res.text

        flags = (
            await db_session.execute(
                text(
                    "SELECT ca.is_default FROM company_addresses ca JOIN companies c ON c.id = ca.company_id "
                    "WHERE c.lead_id = :l AND ca.address_type = 'delivery'"
                ),
                {"l": lead_id},
            )
        ).scalars().all()
        assert [bool(f) for f in flags] == [True]

    async def test_existing_default_delivery_is_kept(self, client, db_session):
        lead_id = await create_lead(client, "配送先既存")
        cid = await create_company(client, lead_id)
        await db_session.execute(
            text(
                "INSERT INTO company_addresses (company_id, address_type, name, address_line_1, country_code, is_default) "
                "VALUES (:c, 'delivery', 'Old Dock', '9 Old Rd', 'US', TRUE)"
            ),
            {"c": cid},
        )
        await db_session.commit()
        token = await _issue_token(client, lead_id)

        res = await client.post("/api/v1/public/register", json=_form(token))
        assert res.status_code == 200, res.text

        rows = (
            await db_session.execute(
                text(
                    "SELECT name, is_default FROM company_addresses "
                    "WHERE company_id = :c AND address_type = 'delivery' ORDER BY id"
                ),
                {"c": cid},
            )
        ).all()
        assert [(r[0], bool(r[1])) for r in rows] == [("Old Dock", True), ("Acme Delivery", False)]
```

- INSERT が試験の DB の列の制約で失敗したら、足りない列を推測で足さず `BLOCKED:` で列名とエラー全文を返す。

## 4. 確かめ

- `cd backend && python -m pytest tests/test_public_register_company.py -q` が 5 passed。
- `cd backend && python -m ruff check app/routers/registration_tokens.py tests/test_public_register_company.py` が 0 件（ruff が無ければその旨を書く）。
- `git diff --stat origin/main...HEAD` が、台帳・docs 3 つ・上の 2 ファイルだけ。

## 5. 想定分岐

- pytest が DB 接続で動かない環境なら、無理に直さず `BLOCKED:` で生のエラーを返す（CI で確かめる）。
- 既存の 3 件が落ちたら止めて `BLOCKED:`。
