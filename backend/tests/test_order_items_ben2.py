from __future__ import annotations

from sqlalchemy import text

from tests.helpers_txn import create_txn_chain


async def _create_product(client, name_ja: str) -> int:
    res = await client.post("/api/v1/products", json={"name_ja": name_ja})
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _create_supplier(client, name: str) -> int:
    res = await client.post("/api/v1/suppliers", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()["id"]


class TestOrderItemsBen2:
    async def test_order_multiple_items(self, client):
        txn = await create_txn_chain(client, order_number="ORD-BEN2-001")
        product_id = await _create_product(client, "便2商品A")

        res = await client.post(
            f"/api/v1/orders/{txn['order_id']}/items",
            json=[
                {
                    "product_id": product_id,
                    "product_name": "便2商品A",
                    "quantity": 1,
                    "unit_price": "1000.00",
                    "subtotal": "1000.00",
                    "sort_order": 0,
                },
                {
                    "product_id": product_id,
                    "product_name": "便2商品B",
                    "quantity": 2,
                    "unit_price": "500.00",
                    "subtotal": "1000.00",
                    "sort_order": 1,
                },
            ],
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert len(body) == 2
        assert all(item["order_id"] == txn["order_id"] for item in body)

        fetched = await client.get(f"/api/v1/orders/{txn['order_id']}/items")
        assert fetched.status_code == 200, fetched.text
        items = fetched.json()
        assert len(items) == 2
        assert [item["sort_order"] for item in items] == [0, 1]
        assert [item["order_id"] for item in items] == [txn["order_id"], txn["order_id"]]

    async def test_split_purchase_links(self, client, db_session):
        txn = await create_txn_chain(client, order_number="ORD-BEN2-LINK")
        product_id = await _create_product(client, "便2分割商品")
        supplier_id = await _create_supplier(client, "便2仕入先")

        order_item_res = await client.post(
            f"/api/v1/orders/{txn['order_id']}/items",
            json=[
                {
                    "product_id": product_id,
                    "product_name": "便2分割商品",
                    "quantity": 100,
                    "unit_price": "100.00",
                    "subtotal": "10000.00",
                    "sort_order": 0,
                }
            ],
        )
        assert order_item_res.status_code == 201, order_item_res.text
        order_item_id = order_item_res.json()[0]["id"]

        po_res = await client.post(
            "/api/v1/purchase-orders",
            json={
                "supplier_id": supplier_id,
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 60,
                        "unit_cost": "100.00",
                        "order_item_id": order_item_id,
                    },
                    {
                        "product_id": product_id,
                        "quantity": 40,
                        "unit_cost": "100.00",
                        "order_item_id": order_item_id,
                    },
                ],
            },
        )
        assert po_res.status_code == 201, po_res.text
        assert [item["order_item_id"] for item in po_res.json()["items"]] == [order_item_id, order_item_id]

        result = await db_session.execute(
            text("SELECT COALESCE(SUM(quantity), 0) FROM purchase_order_items WHERE order_item_id = :id"),
            {"id": order_item_id},
        )
        assert result.scalar_one() == 100

    async def test_po_item_rejects_missing_order_item(self, client):
        product_id = await _create_product(client, "便2NG商品")
        supplier_id = await _create_supplier(client, "便2仕入先NG")

        res = await client.post(
            "/api/v1/purchase-orders",
            json={
                "supplier_id": supplier_id,
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 1,
                        "unit_cost": "100.00",
                        "order_item_id": 999999,
                    }
                ],
            },
        )
        assert res.status_code == 404, res.text
