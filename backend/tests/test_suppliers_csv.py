"""
テナント用仕入元マスタ CSV エクスポート・インポート テスト（Sprint 2）。

対象:
  GET  /suppliers/export
  POST /suppliers/import/preview
  POST /suppliers/import/commit

テナント隔離テスト (test_import_tenant_isolation) を含む。
"""
from __future__ import annotations

import csv
import hashlib
import io

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_csv(rows: list[dict]) -> bytes:
    """Build UTF-8 CSV bytes from a list of dicts."""
    buf = io.StringIO()
    if not rows:
        return b""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _csv_row(
    *,
    supplier_code: str = "",
    name: str = "Test Supplier",
    supplier_type: str = "corporate",
    line_name: str = "",
    contact_name: str = "",
    email: str = "",
    phone: str = "",
    postal_code: str = "",
    prefecture: str = "",
    city: str = "",
    address1: str = "",
    address2: str = "",
    notes: str = "",
    is_active: str = "true",
) -> dict:
    return {
        "supplier_code": supplier_code,
        "name": name,
        "supplier_type": supplier_type,
        "line_name": line_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "postal_code": postal_code,
        "prefecture": prefecture,
        "city": city,
        "address1": address1,
        "address2": address2,
        "notes": notes,
        "is_active": is_active,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSupplierCsvExport:
    async def test_export_csv(self, client):
        """エクスポートで自テナントのアクティブ仕入元のみCSVが返る。"""
        # Create a supplier for this tenant
        create_res = await client.post(
            "/api/v1/suppliers",
            json={
                "name": "Export Test Supplier",
                "contact_name": "田中",
                "email": "export@test.example.com",
                "phone": "03-1234-5678",
                "address": "東京都",
                "notes": "",
            },
        )
        assert create_res.status_code == 201, create_res.text

        res = await client.get("/api/v1/suppliers/export")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers.get("content-disposition", "")
        assert "suppliers.csv" in res.headers.get("content-disposition", "")

        content = res.text
        reader = csv.DictReader(io.StringIO(content))
        assert reader.fieldnames is not None
        assert "supplier_code" in reader.fieldnames
        assert "name" in reader.fieldnames
        assert "is_active" in reader.fieldnames

        rows = list(reader)
        names = [r["name"] for r in rows]
        assert "Export Test Supplier" in names

    async def test_export_csv_only_active(self, client):
        """エクスポートはis_active=TRUEのみ返す。"""
        # Create supplier then soft-delete it
        create_res = await client.post(
            "/api/v1/suppliers",
            json={"name": "Inactive Supplier"},
        )
        assert create_res.status_code == 201
        supplier_id = create_res.json()["id"]
        del_res = await client.delete(f"/api/v1/suppliers/{supplier_id}")
        assert del_res.status_code == 204

        res = await client.get("/api/v1/suppliers/export")
        assert res.status_code == 200
        content = res.text
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        names = [r["name"] for r in rows]
        assert "Inactive Supplier" not in names


class TestSupplierCsvImportPreview:
    async def test_import_preview(self, client):
        """プレビューでバリデーション結果が返り、DBは変更されない。"""
        csv_data = _build_csv([_csv_row(name="Preview Supplier ABC", notes="preview test")])

        res = await client.post(
            "/api/v1/suppliers/import/preview",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert res.status_code == 200
        data = res.json()
        assert "digest" in data
        assert data["total"] == 1
        assert data["inserts"] == 1
        assert data["updates"] == 0
        assert data["errors"] == []
        assert len(data["preview_rows"]) == 1
        assert data["preview_rows"][0]["name"] == "Preview Supplier ABC"

        # Confirm DB was NOT written
        list_res = await client.get("/api/v1/suppliers", params={"search": "Preview Supplier ABC", "active_only": False})
        assert list_res.status_code == 200
        assert list_res.json() == []

    async def test_import_preview_update_detection(self, client):
        """既存supplier_codeはupdates=1で返る。"""
        # Create a supplier first
        create_res = await client.post(
            "/api/v1/suppliers",
            json={"name": "Existing Supplier"},
        )
        assert create_res.status_code == 201
        supplier_code = create_res.json()["supplier_code"]

        csv_data = _build_csv([_csv_row(supplier_code=supplier_code, name="Existing Supplier Updated")])
        res = await client.post(
            "/api/v1/suppliers/import/preview",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["inserts"] == 0
        assert data["updates"] == 1
        assert data["errors"] == []


class TestSupplierCsvImportCommit:
    async def test_import_commit(self, client):
        """確定でtenant_id=自テナントのデータが書き込まれる。"""
        csv_data = _build_csv([_csv_row(name="Commit Test Supplier", notes="committed")])
        digest = _sha256(csv_data)

        res = await client.post(
            "/api/v1/suppliers/import/commit",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"digest": digest},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["inserted"] == 1
        assert data["updated"] == 0
        assert data["errors"] == []

        # Verify supplier appears in list
        list_res = await client.get("/api/v1/suppliers", params={"search": "Commit Test Supplier", "active_only": False})
        assert list_res.status_code == 200
        results = list_res.json()
        assert len(results) == 1
        assert results[0]["name"] == "Commit Test Supplier"
        assert results[0]["supplier_code"].startswith("SP-")

    async def test_import_upsert(self, client):
        """supplier_code一致で更新、新規はINSERT。"""
        # Create existing supplier
        create_res = await client.post(
            "/api/v1/suppliers",
            json={"name": "Upsert Existing", "contact_name": "Before"},
        )
        assert create_res.status_code == 201
        existing_code = create_res.json()["supplier_code"]

        csv_data = _build_csv([
            # Update row
            _csv_row(supplier_code=existing_code, name="Upsert Existing", contact_name="After"),
            # Insert row
            _csv_row(name="Upsert New Supplier"),
        ])
        digest = _sha256(csv_data)

        res = await client.post(
            "/api/v1/suppliers/import/commit",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"digest": digest},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["inserted"] == 1
        assert data["updated"] == 1
        assert data["errors"] == []

        # Verify update
        list_res = await client.get("/api/v1/suppliers", params={"search": "Upsert Existing", "active_only": False})
        assert list_res.status_code == 200
        updated = [r for r in list_res.json() if r["supplier_code"] == existing_code]
        assert len(updated) == 1
        assert updated[0]["contact_name"] == "After"

        # Verify insert
        new_res = await client.get("/api/v1/suppliers", params={"search": "Upsert New Supplier", "active_only": False})
        assert new_res.status_code == 200
        assert len(new_res.json()) == 1

    async def test_import_validation_errors(self, client):
        """不正データで行番号付きエラーが返る。"""
        csv_data = _build_csv([
            # L2: missing name (no supplier_code either)
            _csv_row(supplier_code="", name=""),
            # L3: invalid supplier_type
            _csv_row(name="Bad Type", supplier_type="unknown_type"),
            # L4: invalid is_active
            _csv_row(name="Bad Active", is_active="maybe"),
        ])

        res = await client.post(
            "/api/v1/suppliers/import/preview",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["errors"]) == 3
        for err in data["errors"]:
            assert err.startswith("L"), f"Error must start with line number: {err}"
        error_text = " ".join(data["errors"])
        assert "L2" in error_text
        assert "L3" in error_text
        assert "L4" in error_text

    async def test_import_digest_mismatch(self, client):
        """プレビュー後にファイルを変更するとcommitが409を返す。"""
        original_csv = _build_csv([_csv_row(name="Digest Test Supplier")])
        modified_csv = _build_csv([_csv_row(name="Modified Supplier")])
        # Use original CSV digest but send modified CSV
        original_digest = _sha256(original_csv)

        res = await client.post(
            "/api/v1/suppliers/import/commit",
            files={"file": ("test.csv", modified_csv, "text/csv")},
            data={"digest": original_digest},
        )
        assert res.status_code == 409
        assert "DIGEST_MISMATCH" in res.json()["detail"]

    async def test_import_not_csv(self, client):
        """CSV以外のファイルは422。"""
        res = await client.post(
            "/api/v1/suppliers/import/preview",
            files={"file": ("data.xlsx", b"fake-xlsx", "application/octet-stream")},
        )
        assert res.status_code == 422

    async def test_import_empty_file(self, client):
        """空ファイルは422。"""
        res = await client.post(
            "/api/v1/suppliers/import/preview",
            files={"file": ("test.csv", b"", "text/csv")},
        )
        assert res.status_code == 422


class TestSupplierCsvTenantIsolation:
    async def test_import_tenant_isolation(self, client, db_session):
        """
        テナントAのサプライヤーがテナントBから見えない・書き換えられない。

        client fixture は tenant_id=999 で動作する。
        このテストでは DB に tenant_id=888 のサプライヤーを直接INSERT し、
        tenant_id=999 のエクスポートに含まれないこと、および
        commit で上書きできないことを確認する。
        """
        from sqlalchemy import text

        # Insert a supplier for tenant B (tenant_id=888) directly
        await db_session.execute(
            text(
                "INSERT INTO suppliers (tenant_id, name, supplier_code, is_active) "
                "VALUES (:tid, :name, :code, TRUE)"
            ),
            {"tid": 888, "name": "Tenant B Supplier", "code": "SP-B0001"},
        )
        await db_session.commit()

        # Tenant A (999) export must NOT include Tenant B's supplier
        export_res = await client.get("/api/v1/suppliers/export")
        assert export_res.status_code == 200
        content = export_res.text
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        names = [r["name"] for r in rows]
        assert "Tenant B Supplier" not in names, (
            "Tenant A export must not include Tenant B's supplier"
        )

        # Tenant A (999) import/commit with Tenant B's supplier_code must NOT update Tenant B
        csv_data = _build_csv([_csv_row(supplier_code="SP-B0001", name="Tampered Name")])
        digest = _sha256(csv_data)

        commit_res = await client.post(
            "/api/v1/suppliers/import/commit",
            files={"file": ("test.csv", csv_data, "text/csv")},
            data={"digest": digest},
        )
        assert commit_res.status_code == 200
        data = commit_res.json()
        # SP-B0001 is not found for tenant 999 → treated as INSERT (for tenant 999)
        # Tenant B's record must remain unchanged
        from sqlalchemy import text as t
        row = (await db_session.execute(
            t("SELECT name FROM suppliers WHERE supplier_code = :code AND tenant_id = :tid"),
            {"code": "SP-B0001", "tid": 888},
        )).fetchone()
        assert row is not None
        assert row[0] == "Tenant B Supplier", (
            "Tenant B supplier must not be modified by Tenant A import"
        )
