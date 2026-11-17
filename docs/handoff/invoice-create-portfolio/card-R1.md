# card-R1: 発送先の6項目をサーバーで返し、請求書の PDF の宛名に出す（invoice-create-portfolio 便 R1）

作成: Opus（Planner）2026-11-17。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第6版 §3-2・§4 R1・K3・K4（設計審査 5回目 APPROVE）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」、発送先を「書き換えない」と決め、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。
枝: release/invoice-portfolio-r1-shipto（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R1 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 写し（`_fetch_address_snapshot`・backend/app/routers/invoices.py:66-106）に6項目 `recipient_name`（住所の name）・`email`・`tax_id`・`address_line_1`・`address_line_2`・`address_line_3` を足す。今の `address`（1と2をつないだ文字）は残す（design-v2 §3-2）。担当者の名前やメールで埋めるのは画面の便 R5 で行い、ここではしない。
- D2 draft-context の ship_to・bill_to に、上の6項目と `country_name` を足す。`country_name` は国の表 public.countries の name を code で引く（backend/app/routers/countries.py:25-26 と同じ表）。写しには入れない。
- D3 請求書の PDF は、写しに `address_line_1` のキーがあるときだけ新しい並び（受取人・住所1〜3・「都市, 州, ZIP」）にする。キーが無い古い請求書は今と同じ行（design-v2 §3-2）。材料は請求書の `_to_addr` だけが渡す。見積の `_to_addr` は変えない。
- D4 見積の PDF の道（invoices.py:1229-1230）だけは、描く前に写しから6項目を除く関数 `_quote_pdf_address` を通す（見積の `_to_addr` は tax_id・email を読むため。invoice_renderer.py:595-606）。
- D5 試験: PDF は DB なしの新しい試験ファイル、draft-context は今の実 PostgreSQL の試験（backend/tests/test_invoice_totals_pg.py の `_check_routes`）に足す。国名は表から引いた値と比べる（直書きしない）。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 `def _fetch_address_snapshot(` が invoices.py に 1。
- P2 `ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")` が invoices.py に 2（:441 見積から請求書を作る道と :1229 見積の PDF の道。2-3 で変えるのは後ろの1か所だけで、`company_id = row["company_id"]` が直前に続く方）。
- P3 `class DraftContextAddress(BaseModel):` が backend/app/schemas/invoice.py に 1。
- P4 `def _addr_lines(addr: AddressSnapshot) -> list[str]:` が invoice_renderer.py に 1。
- P5 `def _to_addr(snap: dict | None) -> Optional[AddressSnapshot]:` が invoice_renderer.py に 2。
- P6 `address_line_3` が migrations/030_create_company_contact_subtables.sql に 1 以上。
- P7 `assert "ZZT" in ctx.currencies and ctx.currencies[0] == "JPY"` が test_invoice_totals_pg.py に 1。
- P8 backend/tests/test_invoice_pdf_address.py が無い。

## 1. 触るファイル

- backend/app/routers/invoices.py（2-1・2-2・2-3）
- backend/app/schemas/invoice.py（2-4）
- backend/app/services/invoice_renderer.py（2-5）
- backend/tests/test_invoice_totals_pg.py（2-6）
- backend/tests/test_invoice_pdf_address.py（2-7・新規）
- frontend/api-contract/openapi.json（手順6 で作る）

## 2. 変更

### 2-1. invoices.py の写し（`_fetch_address_snapshot` の中）

変更前:
```
            SELECT a.branch_name, a.zip, a.address_line_1, a.address_line_2,
                   a.city, a.state, a.country_code, a.telephone,
                   c.name AS company_name, c.billing_display_name
```
変更後:
```
            SELECT a.branch_name, a.zip, a.address_line_1, a.address_line_2,
                   a.address_line_3, a.city, a.state, a.country_code, a.telephone,
                   a.name AS recipient_name, a.email, a.tax_id,
                   c.name AS company_name, c.billing_display_name
```
変更前:
```
        "country": row["country_code"],
        "phone": row["telephone"],
    }
```
変更後:
```
        "country": row["country_code"],
        "phone": row["telephone"],
        # invoice-create-portfolio R1（design-v2 §3-2）: 発送先12欄と請求書の PDF の宛名の材料
        "recipient_name": row["recipient_name"],
        "email": row["email"],
        "tax_id": row["tax_id"],
        "address_line_1": row["address_line_1"],
        "address_line_2": row["address_line_2"],
        "address_line_3": row["address_line_3"],
    }


# 見積の PDF は宛名を変えない（design-v2 §3-2）。写しに足した6項目を描く前に除く。
_QUOTE_PDF_HIDDEN_KEYS = (
    "recipient_name", "email", "tax_id", "address_line_1", "address_line_2", "address_line_3",
)


def _quote_pdf_address(snap: dict | None) -> dict | None:
    if snap is None:
        return None
    return {k: v for k, v in snap.items() if k not in _QUOTE_PDF_HIDDEN_KEYS}


async def _country_name(db: AsyncSession, code: str | None) -> str | None:
    """国の表 public.countries の name（GET /countries と同じ表）。無ければ None。"""
    if not code:
        return None
    res = await db.execute(text("SELECT name FROM public.countries WHERE code = :cc"), {"cc": code.upper()})
    return res.scalar_one_or_none()
```
（`    }` の後の空行の数は、その下の `_INVOICE_COLUMNS = """` との間が空行 2 つになるようにする。）

### 2-2. invoices.py の draft-context

変更前:
```
    ship_to = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, company_id, "billing")
    if stored is not None:
```
変更後:
```
    ship_to = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, company_id, "billing")
    for addr in (ship_to, bill_to):
        if addr is not None:
            addr["country_name"] = await _country_name(db, addr.get("country"))
    if stored is not None:
```
（変更前の3行は draft-context の中に 1 か所だけ。preview の道の同じ2行は `if stored is not None:` が続かないので当たらない。）

### 2-3. invoices.py の見積の PDF の道

変更前:
```
    company_id = row["company_id"]
    ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")
```
変更後:
```
    company_id = row["company_id"]
    ship_to_snap = _quote_pdf_address(await _fetch_address_snapshot(db, company_id, "delivery"))
    bill_to_snap = _quote_pdf_address(await _fetch_address_snapshot(db, company_id, "billing"))
```

### 2-4. schemas/invoice.py

変更前:
```
    country: str | None = None
    phone: str | None = None


class DraftContextFx(BaseModel):
```
変更後:
```
    country: str | None = None
    phone: str | None = None
    # invoice-create-portfolio R1（design-v2 §3-2）
    recipient_name: str | None = None
    email: str | None = None
    tax_id: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    address_line_3: str | None = None
    country_name: str | None = None


class DraftContextFx(BaseModel):
```

### 2-5. services/invoice_renderer.py

(1) 変更前:
```
@dataclass
class AddressSnapshot:
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    address: Optional[str] = None
```
変更後:
```
@dataclass
class AddressSnapshot:
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    address: Optional[str] = None
    # invoice-create-portfolio R1: 写しに address_line_1 のキーがある請求書だけが渡す（None なら今の1行の住所）
    recipient_name: Optional[str] = None
    address_lines: Optional[list[str]] = None
    city_line: Optional[str] = None
```
(2) `_addr_lines` の中。変更前:
```
    if addr.company_name:
        lines.append(addr.company_name)
    if addr.contact_name:
        lines.append(addr.contact_name)
    if addr.address:
        lines.append(addr.address)
```
変更後:
```
    if addr.company_name:
        lines.append(addr.company_name)
    if addr.recipient_name:
        lines.append(addr.recipient_name)
    if addr.contact_name and addr.contact_name != addr.recipient_name:
        lines.append(addr.contact_name)
    if addr.address_lines is not None:
        lines.extend(line for line in addr.address_lines if line)
        if addr.city_line:
            lines.append(addr.city_line)
    elif addr.address:
        lines.append(addr.address)
```
(3) 請求書の `_to_addr`（`render_invoice_pdf` の中の 1 つ目。見積の `render_quote_pdf` の中の 2 つ目は触らない）。変更前:
```
        return AddressSnapshot(
            company_name=snap.get("billing_display_name") or snap.get("company_name"),
            contact_name=snap.get("contact_name"),
            address=snap.get("address"),
            country=snap.get("country"),
            tax_id=snap.get("tax_id"),
            phone=snap.get("phone"),
            email=snap.get("email"),
        )

    def _to_fx(snap: dict | None) -> Optional[FxRateSnapshot]:
```
変更後:
```
        split = "address_line_1" in snap
        city_line = ", ".join(p for p in (snap.get("city"), snap.get("state"), snap.get("postal_code")) if p)
        return AddressSnapshot(
            company_name=snap.get("billing_display_name") or snap.get("company_name"),
            contact_name=snap.get("contact_name"),
            address=snap.get("address"),
            country=snap.get("country"),
            tax_id=snap.get("tax_id"),
            phone=snap.get("phone"),
            email=snap.get("email"),
            recipient_name=snap.get("recipient_name") if split else None,
            address_lines=[snap.get("address_line_1"), snap.get("address_line_2"), snap.get("address_line_3")]
            if split else None,
            city_line=(city_line or None) if split else None,
        )

    def _to_fx(snap: dict | None) -> Optional[FxRateSnapshot]:
```
（変更前の塊は `def _to_fx(` が続く方の 1 か所だけ。見積の方は `data = InvoiceRenderData(` が続くので当たらない。）

### 2-6. backend/tests/test_invoice_totals_pg.py の `_check_routes`

変更前:
```
    assert "ZZT" in ctx.currencies and ctx.currencies[0] == "JPY"
```
変更後:
```
    assert "ZZT" in ctx.currencies and ctx.currencies[0] == "JPY"

    # invoice-portfolio R1 K3: 住所の6項目と国名を返す（請求先の行だけがある会社なので届け先は None）
    await db.execute(
        text(
            "UPDATE company_addresses SET name = 'Recv 953', email = 'a953@example.com', tax_id = 'TX953', "
            "address_line_1 = 'L1', address_line_2 = 'L2', address_line_3 = 'L3', "
            "city = 'C953', state = 'S953', zip = 'Z953' "
            "WHERE company_id = :c AND address_type = 'billing'"
        ),
        {"c": company_id},
    )
    jp_name = (await db.execute(text("SELECT name FROM public.countries WHERE code = 'JP'"))).scalar_one_or_none()
    k3 = await get_invoice_draft_context(
        company_id=company_id, contact_id=None, invoice_id=None, db=db, tenant_id=_TENANT_ID, current_user=None,
    )
    assert k3.ship_to is None and k3.bill_to is not None
    b = k3.bill_to
    assert (b.recipient_name, b.email, b.tax_id) == ("Recv 953", "a953@example.com", "TX953")
    assert (b.address_line_1, b.address_line_2, b.address_line_3) == ("L1", "L2", "L3")
    assert (b.address, b.city, b.state, b.postal_code) == ("L1 L2", "C953", "S953", "Z953")
    assert b.country == "JP" and b.country_name == jp_name
    assert k3.issuer_region == "domestic"
```

### 2-7. backend/tests/test_invoice_pdf_address.py（新規・Write ツール）

```
"""請求書の PDF の宛名（invoice-portfolio R1・design-v2 K4。DB なし）。

reportlab の Canvas の drawString を包み、描かれた文字を集めて確かめる。
"""
from __future__ import annotations

import pytest
from reportlab.pdfgen import canvas as rl_canvas

from app.routers.invoices import _quote_pdf_address
from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf

_OLD = {
    "company_name": "Old Co", "billing_display_name": None, "label": None, "postal_code": "100-0001",
    "address": "Line A Line B", "city": "Chiyoda", "state": "Tokyo", "country": "JP", "phone": "03-0000",
}
_NEW = dict(
    _OLD,
    recipient_name="Recv Person", email="r@example.com", tax_id="TX-1",
    address_line_1="Line A", address_line_2="Line B", address_line_3="Line C",
)


@pytest.fixture
def drawn(monkeypatch):
    texts: list[str] = []
    orig = rl_canvas.Canvas.drawString

    def _string(self, x, y, text, *a, **k):
        texts.append(str(text))
        return orig(self, x, y, text, *a, **k)

    monkeypatch.setattr(rl_canvas.Canvas, "drawString", _string)
    return texts


def _invoice(snap: dict) -> dict:
    return {
        "invoice_code": "IN-0001-01", "issued_at": "2026-11-17T00:00:00",
        "ship_to_snapshot": snap, "bill_to_snapshot": None,
        "items": [{"name_en": "Test Item", "quantity": 1, "unit_price": 1000.0, "subtotal": 1000.0, "hs_code": None}],
        "subtotal": 1000.0, "shipping_fee": 0.0, "tax_amount": 0.0, "total_amount": 1000.0,
        "currency": "JPY", "duty_amount": None, "fx_rate_snapshot": None, "notes": None,
    }


def _quote(snap: dict) -> dict:
    return {
        "quote_code": "QT-0001", "created_at": "2026-11-17T00:00:00",
        "ship_to_snapshot": snap, "bill_to_snapshot": None,
        "items": [{"name_en": "Test Item", "quantity": 1, "unit_price": 1000.0, "subtotal": 1000.0, "hs_code": None}],
        "subtotal": 1000.0, "shipping_fee": 0.0, "total_amount": 1000.0, "currency": "JPY", "notes": None,
    }


def test_k4_new_copy_prints_split_address(drawn):
    render_invoice_pdf(_invoice(_NEW), {})
    for want in ("Recv Person", "Line A", "Line B", "Line C", "Chiyoda, Tokyo, 100-0001", "Tax ID: TX-1", "Email: r@example.com"):
        assert want in drawn, want
    assert "Line A Line B" not in drawn


def test_k4_old_copy_prints_as_before(drawn):
    render_invoice_pdf(_invoice(_OLD), {})
    assert "Line A Line B" in drawn
    assert "Chiyoda, Tokyo, 100-0001" not in drawn
    assert not any(t.startswith("Tax ID:") or t.startswith("Email:") for t in drawn)


def test_k4_quote_pdf_is_unchanged(drawn):
    stripped = _quote_pdf_address(_NEW)
    assert stripped == _OLD
    assert _quote_pdf_address(None) is None
    render_quote_pdf(_quote(_OLD), {})
    before = list(drawn)
    drawn.clear()
    render_quote_pdf(_quote(stripped), {})
    assert drawn == before
```

## 3. 手順

手順1 作業場所を公式の台本で作る（ホームに clone した別の場所は使わない。`MAIN` はクラウドが最初に置いたリポジトリの場所。例 `/home/user/salesanchor`）。1 つずつ流し、出力を報告に書く。
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r1-shipto
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r1-shipto
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある` で停止）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r1-shipto` が出る（出なければ `BLOCKED: 手順1 作業場所`）。5行目 `is-ancestor exit=0`。リポジトリの場所が `/home/user/salesanchor` でないときは、実際の場所に読み替えて同じ命令を流し、読み替えたことを書く。台本が作る .claude-pipeline/active-work.d/ の未追跡ファイルは add しない。

手順2 実装前点検 P1〜P8
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c "def _fetch_address_snapshot(" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c 'ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")' backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c "class DraftContextAddress(BaseModel):" backend/app/schemas/invoice.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c "def _addr_lines(addr: AddressSnapshot) -> list\[str\]:" backend/app/services/invoice_renderer.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c "def _to_addr(snap: dict | None) -> Optional\[AddressSnapshot\]:" backend/app/services/invoice_renderer.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c "address_line_3" migrations/030_create_company_contact_subtables.sql
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c 'assert "ZZT" in ctx.currencies and ctx.currencies\[0\] == "JPY"' backend/tests/test_invoice_totals_pg.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && ls backend/tests/test_invoice_pdf_address.py 2>&1 | tail -1
  期待（命令の順）: 1、2、1、1、2、1 以上、1、`No such file`。

手順3 §2 の変更をする（2-1 から順に。2-7 は Write ツール、それ以外は Edit ツール）

手順4 道具を入れる（作業場所の外 ~/venv312。素の pip は見張りが止めるので使わない）
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
  python3.12 が無いときだけ 1行目の代わりに `cd ~ && uv venv --python 3.12 ~/venv312` と `cd ~ && ~/venv312/bin/python -m ensurepip` を流す（それも失敗したら `BLOCKED: python3.12 なし` で停止）。

手順5 形と試験
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && ~/venv312/bin/ruff check backend/app/routers/invoices.py backend/app/schemas/invoice.py backend/app/services/invoice_renderer.py backend/tests/test_invoice_totals_pg.py backend/tests/test_invoice_pdf_address.py 2>&1 | tail -10
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoice_pdf_address.py tests/test_invoice_pdf_payment.py tests/test_invoice_totals_pg.py 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoices.py tests/test_invoices_create_flow.py tests/test_issuer.py tests/test_error_detail_guard.py 2>&1 | tail -15
  期待: ruff `All checks passed!`。2行目は `7 passed`（新しい3・今の4）と `1 skipped`（PG の1本は CI だけで動く）。3行目は failed 0・error 0（本数はそのまま書く）。

手順6 API の形を書き出す
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git diff --numstat frontend/api-contract/openapi.json | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && grep -c '"country_name"' frontend/api-contract/openapi.json
  期待: 1行目は何も出ない。2行目は足した行が 0 より大きい。3行目 1 以上。

手順7 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git status --short | tail -20
  期待: §1 の 6 ファイルだけ（新規の試験は `??`）。ほかが出たら `BLOCKED: 範囲外のファイル` で停止。

手順8 記録と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git add backend/app/routers/invoices.py backend/app/schemas/invoice.py backend/app/services/invoice_renderer.py backend/tests/test_invoice_totals_pg.py backend/tests/test_invoice_pdf_address.py frontend/api-contract/openapi.json && git status --short | tail -20
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): return ship-to recipient, email, tax id and three address lines, and print them on new invoice PDFs (invoice-portfolio R1)" && git log --oneline -1 | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git push -u origin release/invoice-portfolio-r1-shipto 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r1-shipto && git rev-parse HEAD
  push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push` で停止する。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P8 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・注記より多く当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順5 で failed か error が出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - test_k4_quote_pdf_is_unchanged が落ちた → 直さず `BLOCKED: 見積の PDF が変わる`（設計の前提が崩れたので Opus が見る）。
  - 手順6 の期待が外れた → `BLOCKED: 手順6`。
- 記録して続ける: ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して結果を書く。I 以外なら `BLOCKED: ruff`。skipped・警告はそのまま書く。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R1 発送先の6項目をサーバーで返し請求書の PDF の宛名に出す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 1500 字を超えるときは、手順5 と手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール（新規の試験だけ Write ツール）。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。見積の `_to_addr`（render_quote_pdf の中）。請求書の詳細画面（frontend/src/pages/invoice-detail/）。migrations/・deploy.yml・scripts/。既存の試験の期待値。

END OF CARD
