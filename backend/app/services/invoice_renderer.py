"""
見積・請求書専用 PDF レンダラー（C-8）。

po_renderer.py とは独立した新規レンダラー（PO レンダラーとは別物）。

機能:
- A4 PDF 生成（ReportLab）
- テナント変数（ロゴ・発行者情報）を tenant_profile から自動流し込み
- Bill To + Ship To 両方表示
- 輸出必須項目（HS コード）固定表示
- duty_amount が None でない場合のみ Duty 行を表示
- 外貨の場合は為替レートと換算額を脚注に表示
- 明細ヘッダーは "Description"（NOT "Production"）

呼出元:
  backend/app/routers/invoices.py (GET /invoices/{id}/pdf, GET /quotes/{id}/pdf)

依存:
  reportlab (PDF 生成、純 Python)
  日本語フォント: 環境変数 PO_PDF_FONT_PATH があればそれを使う。
                  なければ Helvetica にフォールバック。
"""
from __future__ import annotations

import glob
import io
import logging
import os
from dataclasses import dataclass
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# フォント登録（モジュールロード時に 1 回だけ）
# ─────────────────────────────────────────────────────────────────────

_FONT_NAME_JA = "InvJapaneseFont"
_FONT_NAME_FALLBACK = "Helvetica"
_FONT_REGISTERED: Optional[str] = None


def _register_font() -> str:
    """TrueType の日本語フォントを登録し、登録名を返す。未登録時は Helvetica。

    重要: reportlab の TTFont は TrueType(glyf) のみ対応。Noto CJK は CFF
    (PostScript outlines) のため失敗する → 候補に含めず IPA ゴシック等を使う。
    """
    global _FONT_REGISTERED
    if _FONT_REGISTERED is not None:
        return _FONT_REGISTERED

    candidates: list[str] = []
    if env_path := os.getenv("PO_PDF_FONT_PATH"):
        candidates.append(env_path)
    candidates += [
        # IPA ゴシック (Debian fonts-ipafont-gothic, TrueType)
        "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        # VL / Takao ゴシック (TrueType)
        "/usr/share/fonts/truetype/vlgothic/VL-Gothic-Regular.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        # macOS 開発機
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for pat in (
        "/usr/share/fonts/**/ipag*.ttf",
        "/usr/share/fonts/**/*[Gg]othic*.ttf",
        "/usr/share/fonts/**/VL-*.ttf",
    ):
        candidates += sorted(glob.glob(pat, recursive=True))

    seen: set[str] = set()
    for path in candidates:
        if not path or path in seen or not os.path.exists(path):
            continue
        seen.add(path)
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_JA, path))
            _FONT_REGISTERED = _FONT_NAME_JA
            logger.info("[invoice_renderer] registered font: %s", path)
            return _FONT_NAME_JA
        except Exception as e:  # noqa: BLE001
            logger.warning("[invoice_renderer] failed to register font %s: %s", path, e)

    _FONT_REGISTERED = _FONT_NAME_FALLBACK
    logger.warning(
        "[invoice_renderer] no usable TrueType Japanese font found; using Helvetica "
        "(日本語は ■ になります)。fonts-ipafont-gothic を導入してください。"
    )
    return _FONT_NAME_FALLBACK


# ─────────────────────────────────────────────────────────────────────
# データ型
# ─────────────────────────────────────────────────────────────────────

@dataclass
class InvoiceItemForRender:
    name_en: str
    qty: int
    unit_price: float
    subtotal: float
    hs_code: Optional[str] = None


@dataclass
class AddressSnapshot:
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class FxRateSnapshot:
    currency: str
    rate: float  # 1 外貨 = rate JPY
    fetched_at: Optional[str] = None


@dataclass
class InvoiceRenderData:
    doc_type: str  # "invoice" or "quote"
    doc_code: str
    issued_at: Optional[str]
    ship_to: Optional[AddressSnapshot]
    bill_to: Optional[AddressSnapshot]
    items: list[InvoiceItemForRender]
    subtotal: float
    shipping_fee: float
    tax_amount: float
    total: float
    currency: str
    duty_amount: Optional[float] = None
    fx_rate: Optional[FxRateSnapshot] = None
    notes: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_address: Optional[str] = None
    tenant_phone: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_website: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────────────────────────────

def _fmt_money(amount: float, currency: str) -> str:
    if currency == "JPY":
        return f"¥{amount:,.0f}"
    return f"{currency} {amount:,.2f}"


def _addr_lines(addr: AddressSnapshot) -> list[str]:
    """AddressSnapshot を表示行リストに変換する。"""
    lines: list[str] = []
    if addr.company_name:
        lines.append(addr.company_name)
    if addr.contact_name:
        lines.append(addr.contact_name)
    if addr.address:
        lines.append(addr.address)
    if addr.country:
        lines.append(addr.country)
    if addr.tax_id:
        lines.append(f"Tax ID: {addr.tax_id}")
    if addr.phone:
        lines.append(f"TEL: {addr.phone}")
    if addr.email:
        lines.append(f"Email: {addr.email}")
    return lines


def _draw_address_block(
    c: canvas.Canvas,
    font: str,
    label: str,
    addr: Optional[AddressSnapshot],
    x: float,
    y: float,
    col_width: float,
) -> float:
    """宛先ブロックを描画し、消費した高さ後の y を返す。"""
    c.setFont(font, 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(x, y, label)
    y -= 4 * mm
    c.setFillColorRGB(0, 0, 0)

    if addr is None:
        c.setFont(font, 9)
        c.drawString(x, y, "-")
        return y - 4 * mm

    for line in _addr_lines(addr):
        truncated = line[:55] if len(line) > 55 else line
        c.setFont(font, 9)
        c.drawString(x, y, truncated)
        y -= 4 * mm

    return y


# ─────────────────────────────────────────────────────────────────────
# 純粋関数: PDF レンダリング
# ─────────────────────────────────────────────────────────────────────

def _render_doc_pdf(data: InvoiceRenderData) -> bytes:
    """
    請求書または見積書の PDF を生成する（共通内部実装）。

    レイアウト (A4 縦):
      - 上部: 発行者（テナント）情報
      - タイトル + ドキュメント番号 + 発行日
      - Bill To / Ship To 2カラム
      - 明細表（Description / Qty / Unit Price / Amount）
      - 合計行 / Duty 行（NULL 時は非表示）
      - 為替レート脚注（外貨時のみ）
      - Notes
    """
    font = _register_font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 18 * mm

    # ── 1. 発行者（テナント）───────────────────────────────────────────
    if data.tenant_name:
        c.setFont(font, 11)
        c.drawString(20 * mm, y, data.tenant_name)
        y -= 5 * mm
    if data.tenant_address:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, data.tenant_address[:80])
        y -= 4 * mm
    contact_parts: list[str] = []
    if data.tenant_phone:
        contact_parts.append(f"TEL: {data.tenant_phone}")
    if data.tenant_email:
        contact_parts.append(f"Email: {data.tenant_email}")
    if contact_parts:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, "  ".join(contact_parts))
        y -= 4 * mm
    if data.tenant_website:
        c.setFont(font, 8)
        c.drawString(20 * mm, y, f"Web: {data.tenant_website}")
        y -= 4 * mm

    # ── 2. タイトル + 番号 + 発行日 ────────────────────────────────────
    y -= 6 * mm
    doc_label = "INVOICE" if data.doc_type == "invoice" else "QUOTATION"
    c.setFont(font, 18)
    c.drawCentredString(width / 2, y, doc_label)
    y -= 8 * mm
    c.setFont(font, 11)
    c.drawCentredString(width / 2, y, f"No. {data.doc_code}")
    y -= 5 * mm
    if data.issued_at:
        c.setFont(font, 9)
        date_str = data.issued_at[:10]
        c.drawCentredString(width / 2, y, f"Date: {date_str}")
        y -= 4 * mm

    # 区切り線
    y -= 3 * mm
    c.setLineWidth(0.5)
    c.line(20 * mm, y, 190 * mm, y)
    y -= 5 * mm

    # ── 3. Bill To / Ship To 2カラム ───────────────────────────────────
    mid_x = width / 2
    left_x = 20 * mm
    right_x = mid_x + 5 * mm

    y_left = _draw_address_block(c, font, "BILL TO:", data.bill_to, left_x, y, mid_x - left_x - 5 * mm)
    y_right = _draw_address_block(c, font, "SHIP TO:", data.ship_to, right_x, y, 190 * mm - right_x)
    y = min(y_left, y_right)

    y -= 5 * mm
    c.line(20 * mm, y, 190 * mm, y)
    y -= 6 * mm

    # ── 4. 明細表ヘッダー ───────────────────────────────────────────────
    c.setFont(font, 10)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(20 * mm, y, "Description")
    c.drawString(110 * mm, y, "HS Code")
    c.drawRightString(143 * mm, y, "Qty")
    c.drawRightString(165 * mm, y, "Unit Price")
    c.drawRightString(190 * mm, y, "Amount")
    y -= 2 * mm
    c.setLineWidth(0.7)
    c.line(20 * mm, y, 190 * mm, y)
    y -= 5 * mm
    c.setFillColorRGB(0, 0, 0)

    # ── 5. 明細行 ───────────────────────────────────────────────────────
    c.setFont(font, 9)
    for item in data.items:
        if y < 50 * mm:
            c.showPage()
            c.setFont(font, 9)
            y = height - 20 * mm

        name = item.name_en[:55] if len(item.name_en) > 55 else item.name_en
        hs = item.hs_code or "-"
        c.drawString(20 * mm, y, name)
        c.drawString(110 * mm, y, hs)
        c.drawRightString(143 * mm, y, str(item.qty))
        c.drawRightString(165 * mm, y, _fmt_money(item.unit_price, data.currency))
        c.drawRightString(190 * mm, y, _fmt_money(item.subtotal, data.currency))
        y -= 5 * mm

    # ── 6. 合計行 ───────────────────────────────────────────────────────
    y -= 3 * mm
    c.setLineWidth(0.5)
    c.line(20 * mm, y, 190 * mm, y)
    y -= 5 * mm

    c.setFont(font, 9)
    c.drawRightString(165 * mm, y, "Subtotal:")
    c.drawRightString(190 * mm, y, _fmt_money(data.subtotal, data.currency))
    y -= 5 * mm

    if data.shipping_fee:
        c.drawRightString(165 * mm, y, "Shipping:")
        c.drawRightString(190 * mm, y, _fmt_money(data.shipping_fee, data.currency))
        y -= 5 * mm

    if data.tax_amount:
        c.drawRightString(165 * mm, y, "Tax:")
        c.drawRightString(190 * mm, y, _fmt_money(data.tax_amount, data.currency))
        y -= 5 * mm

    # Duty 行（None の場合は非表示）
    if data.duty_amount is not None:
        c.drawRightString(165 * mm, y, "Duty:")
        c.drawRightString(190 * mm, y, _fmt_money(data.duty_amount, data.currency))
        y -= 5 * mm

    # 合計（太字）
    y -= 1 * mm
    c.setFont(font, 12)
    c.drawRightString(165 * mm, y, "TOTAL:")
    c.drawRightString(190 * mm, y, _fmt_money(data.total, data.currency))
    y -= 8 * mm

    # ── 7. 為替レート脚注（外貨時のみ）────────────────────────────────
    if data.fx_rate is not None and data.currency != "JPY":
        c.setFont(font, 8)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        rate_line = (
            f"Exchange rate: 1 {data.fx_rate.currency} = JPY {data.fx_rate.rate:,.4f}"
        )
        if data.fx_rate.fetched_at:
            rate_line += f"  (as of {data.fx_rate.fetched_at[:19]}Z)"
        c.drawString(20 * mm, y, rate_line)
        jpy_total = data.total * data.fx_rate.rate
        c.drawString(20 * mm, y - 4 * mm, f"JPY equivalent: ¥{jpy_total:,.0f}")
        y -= 10 * mm
        c.setFillColorRGB(0, 0, 0)

    # ── 8. Notes ─────────────────────────────────────────────────────
    if data.notes:
        c.setFont(font, 9)
        c.drawString(20 * mm, y, "Notes:")
        y -= 4 * mm
        c.setFont(font, 8)
        for line in data.notes.split("\n"):
            if y < 25 * mm:
                c.showPage()
                c.setFont(font, 8)
                y = height - 20 * mm
            c.drawString(22 * mm, y, line[:90])
            y -= 4 * mm

    c.save()
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────
# 公開インタフェース
# ─────────────────────────────────────────────────────────────────────

def render_invoice_pdf(invoice_data: dict, tenant_profile: dict) -> bytes:
    """
    請求書 PDF を生成して bytes で返す。

    invoice_data キー:
        invoice_code: str
        issued_at: str | None
        ship_to_snapshot: dict | None  — {"company_name":..., "address":..., ...}
        bill_to_snapshot: dict | None
        items: list[{"name_en": str, "qty": int, "unit_price": float,
                      "hs_code": str | None, "subtotal": float}]
        subtotal: float
        shipping_fee: float
        tax_amount: float
        total: float
        currency: str
        duty_amount: float | None
        fx_rate_snapshot: dict | None  — {"currency":"USD","rate":150.25,"fetched_at":"..."}
        notes: str | None

    tenant_profile キー:
        name: str, address: str, phone: str, email: str, website: str
    """

    def _to_addr(snap: dict | None) -> Optional[AddressSnapshot]:
        if not snap:
            return None
        return AddressSnapshot(
            company_name=snap.get("company_name"),
            contact_name=snap.get("contact_name"),
            address=snap.get("address"),
            country=snap.get("country"),
            tax_id=snap.get("tax_id"),
            phone=snap.get("phone"),
            email=snap.get("email"),
        )

    def _to_fx(snap: dict | None) -> Optional[FxRateSnapshot]:
        if not snap:
            return None
        return FxRateSnapshot(
            currency=snap.get("currency", ""),
            rate=float(snap.get("rate", 0)),
            fetched_at=snap.get("fetched_at"),
        )

    data = InvoiceRenderData(
        doc_type="invoice",
        doc_code=invoice_data.get("invoice_code", "-"),
        issued_at=invoice_data.get("issued_at"),
        ship_to=_to_addr(invoice_data.get("ship_to_snapshot")),
        bill_to=_to_addr(invoice_data.get("bill_to_snapshot")),
        items=[
            InvoiceItemForRender(
                name_en=item.get("name_en") or item.get("product_name") or "-",
                qty=int(item.get("qty") or item.get("quantity") or 0),
                unit_price=float(item.get("unit_price") or 0),
                subtotal=float(item.get("subtotal") or 0),
                hs_code=item.get("hs_code"),
            )
            for item in invoice_data.get("items", [])
        ],
        subtotal=float(invoice_data.get("subtotal") or 0),
        shipping_fee=float(invoice_data.get("shipping_fee") or 0),
        tax_amount=float(invoice_data.get("tax_amount") or 0),
        total=float(invoice_data.get("total") or invoice_data.get("total_amount") or 0),
        currency=invoice_data.get("currency", "JPY"),
        duty_amount=invoice_data.get("duty_amount"),
        fx_rate=_to_fx(invoice_data.get("fx_rate_snapshot")),
        notes=invoice_data.get("notes"),
        tenant_name=tenant_profile.get("name"),
        tenant_address=tenant_profile.get("address"),
        tenant_phone=tenant_profile.get("phone"),
        tenant_email=tenant_profile.get("email"),
        tenant_website=tenant_profile.get("website"),
    )

    return _render_doc_pdf(data)


def render_quote_pdf(quote_data: dict, tenant_profile: dict) -> bytes:
    """
    見積書 PDF を生成して bytes で返す。

    quote_data キー:
        quote_code: str
        issued_at: str | None
        ship_to_snapshot: dict | None
        bill_to_snapshot: dict | None
        items: list[{"name_en": str, "qty": int, "unit_price": float,
                      "hs_code": str | None, "subtotal": float}]
        subtotal: float
        shipping_fee: float
        tax_amount: float
        total: float
        currency: str
        notes: str | None

    tenant_profile キー:
        name: str, address: str, phone: str, email: str, website: str
    """

    def _to_addr(snap: dict | None) -> Optional[AddressSnapshot]:
        if not snap:
            return None
        return AddressSnapshot(
            company_name=snap.get("company_name"),
            contact_name=snap.get("contact_name"),
            address=snap.get("address"),
            country=snap.get("country"),
            tax_id=snap.get("tax_id"),
            phone=snap.get("phone"),
            email=snap.get("email"),
        )

    data = InvoiceRenderData(
        doc_type="quote",
        doc_code=quote_data.get("quote_code", "-"),
        issued_at=quote_data.get("issued_at") or quote_data.get("created_at"),
        ship_to=_to_addr(quote_data.get("ship_to_snapshot")),
        bill_to=_to_addr(quote_data.get("bill_to_snapshot")),
        items=[
            InvoiceItemForRender(
                name_en=item.get("name_en") or item.get("product_name") or "-",
                qty=int(item.get("qty") or item.get("quantity") or 0),
                unit_price=float(item.get("unit_price") or 0),
                subtotal=float(item.get("subtotal") or 0),
                hs_code=item.get("hs_code"),
            )
            for item in quote_data.get("items", [])
        ],
        subtotal=float(quote_data.get("subtotal") or 0),
        shipping_fee=float(quote_data.get("shipping_fee") or 0),
        tax_amount=float(quote_data.get("tax_amount") or 0),
        total=float(quote_data.get("total") or quote_data.get("total_amount") or 0),
        currency=quote_data.get("currency", "JPY"),
        duty_amount=None,  # 見積書では Duty 行は表示しない
        fx_rate=None,
        notes=quote_data.get("notes"),
        tenant_name=tenant_profile.get("name"),
        tenant_address=tenant_profile.get("address"),
        tenant_phone=tenant_profile.get("phone"),
        tenant_email=tenant_profile.get("email"),
        tenant_website=tenant_profile.get("website"),
    )

    return _render_doc_pdf(data)
