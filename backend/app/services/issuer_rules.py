"""書類に載せる会社情報（国内用・海外用）の入力の決まり（ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。

表の CHECK（migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql:39〜:67）と同じ決まりを、
保存の前に欄ごとの理由の番号で返す。DB の CHECK は最後の守りとして残す。
理由の番号は画面が t() で文にする（ADR-027。ここに日本語の文を書かない）。
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

JAPAN = "JP"
POSTAL_JP_RE = re.compile(r"[0-9]{7}")
POSTAL_FOREIGN_RE = re.compile(r"[0-9A-Za-z -]{1,10}")
PHONE_JP_RE = re.compile(r"[0-9]{10,11}")
PHONE_FOREIGN_RE = re.compile(r"\+[0-9]{6,15}")
REGISTRATION_RE = re.compile(r"T[0-9]{13}")

_TEXT_FIELDS = (
    "company_name", "email", "website", "country_code", "postal_code", "prefecture_code",
    "state_region", "city", "address1", "address2", "phone", "registration_number",
)
_REQUIRED = ("company_name", "country_code", "city", "address1")


def normalize_issuer_payload(data: dict[str, Any]) -> dict[str, Any]:
    """前後の空白を取り、空は None にする。国の番号は大文字。登録が無なら番号を捨てる。"""
    out = dict(data)
    for key in _TEXT_FIELDS:
        value = out.get(key)
        if isinstance(value, str):
            out[key] = value.strip() or None
    if out.get("country_code"):
        out["country_code"] = out["country_code"].upper()
    if not out.get("is_invoice_registered"):
        out["is_invoice_registered"] = False
        out["registration_number"] = None
    return out


def check_issuer_fields(data: dict[str, Any]) -> dict[str, str]:
    """形の決まりを確かめ、欄 → 理由の番号を返す。空なら決まりどおり。"""
    errors: dict[str, str] = {}
    for key in _REQUIRED:
        if not data.get(key):
            errors[key] = "required"
    postal = data.get("postal_code")
    phone = data.get("phone")
    if data.get("country_code") == JAPAN:
        if not postal:
            errors["postal_code"] = "required"
        elif not POSTAL_JP_RE.fullmatch(postal):
            errors["postal_code"] = "postal_jp"
        if not data.get("prefecture_code"):
            errors["prefecture_code"] = "required"
        if data.get("state_region"):
            errors["state_region"] = "must_be_empty"
        if phone and not PHONE_JP_RE.fullmatch(phone):
            errors["phone"] = "phone_jp"
    else:
        if data.get("prefecture_code"):
            errors["prefecture_code"] = "must_be_empty"
        if postal and not POSTAL_FOREIGN_RE.fullmatch(postal):
            errors["postal_code"] = "postal_foreign"
        if phone and not PHONE_FOREIGN_RE.fullmatch(phone):
            errors["phone"] = "phone_foreign"
    if data.get("is_invoice_registered"):
        number = data.get("registration_number")
        if not number:
            errors["registration_number"] = "required"
        elif not REGISTRATION_RE.fullmatch(number):
            errors["registration_number"] = "registration_number"
    return errors


async def check_issuer_codes(db: AsyncSession, data: dict[str, Any]) -> dict[str, str]:
    """国と都道府県の番号が一覧（public.countries・public.prefectures）にあるかを確かめる。"""
    errors: dict[str, str] = {}
    country = data.get("country_code")
    if country:
        found = (await db.execute(
            text("SELECT 1 FROM public.countries WHERE code = :code AND is_active = TRUE"),
            {"code": country},
        )).first()
        if not found:
            errors["country_code"] = "unknown_code"
    prefecture = data.get("prefecture_code")
    if prefecture:
        found = (await db.execute(
            text("SELECT 1 FROM public.prefectures WHERE code = :code"),
            {"code": prefecture},
        )).first()
        if not found:
            errors["prefecture_code"] = "unknown_code"
    return errors
