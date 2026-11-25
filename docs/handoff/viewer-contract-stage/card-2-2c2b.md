# card: 便2-2c2b 会社情報の画面に国内用・海外用のタブを作る（ADR-1061）

- 状態: 設計と実装は PO 承認済み（2026-11-12「1」。design.md §3-4・§3-4a・§3-4b）。この便に進むのは PO 2026-11-25「1」（会社情報の画面を国内用・海外用のタブで作る）。
- 設計: docs/handoff/viewer-contract-stage/design.md §3-4（表・発行元を読む1つの道・画面の並び）・§3-4a（金型）・§3-4b（API の約束）。受入: A20（一部）・A21（tenant_id の絞り込みだけ）・A24・A27・A28・A29（登録の欄）・A30・A32・A40・A42（タブの部分）。
- 担当: クラウドの Sonnet。§1 のファイルだけを直す。本番・secrets・DB には触らない。PR は作らない（Opus が作る）。
- 基準: origin/main `5a72c083f`。行番号がずれていたら「変更前」の文字列で場所を探す。件数が §0-3 と合わなければ BLOCKED。
- 危険便か: いいえ（migrations/・deploy.yml・本番 scripts/ に触らない）。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと

- D1 発行元を読む2つの処理（get_issuer_country_code・get_issuer）は、地域に加えて会社の番号（tenant_id）でも絞る（A21 の tenant_id の部分）。返す値・引数は変えない（invoices.py の呼び出し :380・:481・:1203・:1251・:1384 はそのまま）。
- D2 旧来の会社情報の表を読む処理は issuer.py の新しい関数 read_legacy_issuer_values の1か所にまとめ、get_issuer と新しい口の両方がそれを使う（A40。issuer.py の当たりは1のまま）。
- D3 入力の決まりは backend/app/services/issuer_rules.py に置く。表の CHECK（migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql:39〜:67）と同じ決まりを、保存の前に欄ごとの理由の番号で返す（422・`detail.fields`）。DB の CHECK は最後の守りとして残す。理由の番号は required・postal_jp・postal_foreign・phone_jp・phone_foreign・registration_number・unknown_code・must_be_empty の8つ。画面が t() で文にする（ADR-027。detail に日本語の文を入れない）。
- D4 国の欄に既定の国を入れない（ADR-125 D5「暗黙に JP を使わない」）。国内用のタブも空から選ぶ。
- D5 画面は、国が日本のときは都道府県を出して州・地域を出さない。日本以外では逆。見えない欄は null で送る。登録が無のときは番号を null で送る。backend も同じ形に直す（登録が無なら番号を捨てる）。
- D6 今の会社情報の口（/admin/tenant-profile）は印影と既定の言語だけを返し・受け取る。古い6欄（会社名の日本語と英語・住所・電話・メール・サイト）は項目から外す。送られてきても無視する（Pydantic の既定）。表の列は消さない（発注書と FedEx がまだ読むため。design.md §3-4「対象外」）。
- D7 会社情報の区切り（IssuerProfileSection）は、今のページのフォームの下に置き、今の行が読めたときだけ出す（batch3f の Q2「読めなかったらフォームを出さない」を守る）。区切りは自分の読み込み中の表示を持つ。
- D8 行の無いタブでは、前の会社情報（古い6欄）を読むだけの欄で見せ、入れ直しを案内する（A42 のタブの部分。§3-4a の Callout と Textarea readOnly）。
- D9 都道府県の名前は API（/api/v1/prefectures）から読み、言語が日本語なら name_ja、それ以外は name_en を出す。画面のコードに都道府県名を書かない（試験で 0 件を確かめる）。
- D10 保存のたびに監査の記録を1行残す（新しく作ったときは create、直したときは update。前と後の値）。A32。
- D11 試験の都道府県は正本の seed ファイル（docs/handoff/viewer-contract-stage/data/prefectures.sql）から読んで入れる（test_issuer.py と同じ形）。試験に都道府県名を書かない。

## 0. カード発行前チェック

| # | 確かめたこと | 結果 |
|---|---|---|
| 1 | 設計の節（§3-4・§3-4a・§3-4b）と受入の行を指している | ○ |
| 2 | 触るファイルを §1 に全部並べた（22） | ○ |
| 3 | 直すファイルの「変更前」の文字列を 5a72c083f で数えた（§0-3） | ○ |
| 4 | 危険パス（migrations/・deploy.yml・本番 scripts/）を含まない | ○ |
| 5 | 対象外（振込先・発注書・FedEx・409・閲覧者の請求書・RLS）を書いた | ○ |
| 6 | get_issuer・get_issuer_country_code の引数と返す値を変えない | ○ |
| 7 | 画面の文字はすべて t()。ja.json と en.json に同じキー | ○ |
| 8 | 画面の部品は金型（§3-4a）だけ。生の input・select・自作タブ・色の直書きなし | ○ |
| 9 | 都道府県・国の一覧は DB の1か所から読む（SSOT） | ○ |
| 10 | commit のあと reset_tenant_context（lint Rule B・C） | ○ |
| 11 | 試験のコマンドは今のリポジトリにある（pytest・vitest・tsc・check:all・export_openapi） | ○ |
| 12 | 止まる条件を §4 に書いた | ○ |
| 13 | 報告の形を §5 に書いた | ○ |

## 0-2. 読んだ節

- docs/ai-agents/executor-checklist.md の 00-common・03-file・10-executor。

## 受領確認

最初の返事の1行目と2行目に次を書く。

```
RECEIVED viewer-contract-bin2-2c2b HEAD=<git rev-parse HEAD の40文字>
本報告はカード 便2-2c2b 会社情報の画面に国内用・海外用のタブを作る の実行結果である
```

## 0-3. 実装前点検

手順2で数える。1つでも違えば止める（BLOCKED）。

| # | ファイル | 数える文字列 | 期待 |
|---|---|---|---|
| P1 | backend/app/services/issuer_rules.py ほか新規7つ（§1 の「新規」） | ファイルがある | 無い |
| P2 | docs/handoff/viewer-contract-stage/data/prefectures.sql | `^  ('` で始まる行 | 47 |
| P3 | backend/app/services/issuer.py | `{"region": region},` | 2 |
| P4 | backend/app/services/issuer.py | `WHERE p.region = :region` | 1 |
| P4b | backend/app/services/issuer.py | `WHERE region = :region ORDER BY id LIMIT 1` | 1 |
| P5 | backend/app/services/issuer.py | `tenant_profile` | 1 |
| P6 | backend/app/routers/tenant_profile.py | `SELECT id, company_name, company_name_en, address, phone, email,` | 3 |
| P7 | backend/app/schemas/tenant_profile.py | `company_name` | 4 |
| P8 | backend/app/main.py | `    invoices,` | 1 |
| P8b | backend/app/main.py | `    payment_fee_settings,  # 決済手数料設定 テナント用` | 1 |
| P8c | backend/app/main.py | `countries.router, prefix=` | 1 |
| P8d | backend/app/main.py | `tenant_profile.router, prefix=` | 1 |
| P8e | backend/app/main.py | `issuer_profiles` と `prefectures` | 0 と 0 |
| P9 | backend/app/realtime/topics.py | `("PUT", "/api/v1/admin/tenant-profile"): _PENDING,` | 1 |
| P10 | backend/tests/conftest.py | `"app.routers.tenant_profile",` | 1 |
| P11 | frontend/src/pages/admin/TenantProfilePage.tsx | 行数（wc -l） | 263 |
| P12 | frontend/src/locales/ja.json と en.json | `  "addressRule": {` | 1 と 1 |
| P13 | frontend/src/locales/ja.json と en.json | `"issuerProfile"` | 0 と 0 |
| P14 | frontend/src（全体） | `北海道` を含むファイル | 0 |

手順2のコマンド（そのまま流す）:

```
cd ~/sa && for f in backend/app/services/issuer_rules.py backend/app/routers/issuer_profiles.py backend/app/routers/prefectures.py backend/app/schemas/issuer_profiles.py backend/app/schemas/prefectures.py backend/tests/test_issuer_profiles.py frontend/src/pages/admin/IssuerProfileSection.tsx frontend/src/pages/admin/InvoiceRegistrationField.tsx frontend/src/pages/admin/issuerProfileForm.ts frontend/src/pages/admin/issuerProfileForm.test.ts; do test -e "$f" && echo "EXISTS $f" || echo "absent $f"; done
cd ~/sa && grep -c "^  ('" docs/handoff/viewer-contract-stage/data/prefectures.sql
cd ~/sa && grep -cF '{"region": region},' backend/app/services/issuer.py; grep -cF 'WHERE p.region = :region' backend/app/services/issuer.py; grep -cF 'WHERE region = :region ORDER BY id LIMIT 1' backend/app/services/issuer.py; grep -cF 'tenant_profile' backend/app/services/issuer.py
cd ~/sa && grep -cF 'SELECT id, company_name, company_name_en, address, phone, email,' backend/app/routers/tenant_profile.py; grep -cF 'company_name' backend/app/schemas/tenant_profile.py
cd ~/sa && grep -cxF '    invoices,' backend/app/main.py; grep -cxF '    payment_fee_settings,  # 決済手数料設定 テナント用' backend/app/main.py; grep -cF 'countries.router, prefix=' backend/app/main.py; grep -cF 'tenant_profile.router, prefix=' backend/app/main.py; grep -c 'issuer_profiles' backend/app/main.py; grep -c 'prefectures' backend/app/main.py
cd ~/sa && grep -cF '("PUT", "/api/v1/admin/tenant-profile"): _PENDING,' backend/app/realtime/topics.py; grep -cF '"app.routers.tenant_profile",' backend/tests/conftest.py
cd ~/sa && wc -l frontend/src/pages/admin/TenantProfilePage.tsx; grep -cxF '  "addressRule": {' frontend/src/locales/ja.json frontend/src/locales/en.json; grep -c '"issuerProfile"' frontend/src/locales/ja.json frontend/src/locales/en.json; grep -rl '北海道' frontend/src | wc -l
```

（grep -c が 0 件で終わると終了コードが 1 になる。数だけを見る。）

## 1. 触るファイル

1. backend/app/services/issuer.py（直す）
2. backend/app/services/issuer_rules.py（新規）
3. backend/app/routers/issuer_profiles.py（新規）
4. backend/app/routers/prefectures.py（新規）
5. backend/app/routers/tenant_profile.py（直す）
6. backend/app/schemas/issuer_profiles.py（新規）
7. backend/app/schemas/prefectures.py（新規）
8. backend/app/schemas/tenant_profile.py（全部書き直す）
9. backend/app/main.py（直す）
10. backend/app/realtime/topics.py（直す）
11. backend/tests/conftest.py（直す）
12. backend/tests/test_tenant_profile.py（全部書き直す）
13. backend/tests/test_issuer_profiles.py（新規）
14. frontend/src/pages/admin/TenantProfilePage.tsx（全部書き直す）
15. frontend/src/pages/admin/IssuerProfileSection.tsx（新規）
16. frontend/src/pages/admin/InvoiceRegistrationField.tsx（新規）
17. frontend/src/pages/admin/issuerProfileForm.ts（新規）
18. frontend/src/pages/admin/issuerProfileForm.test.ts（新規）
19. frontend/src/lib/query/batch3fPages.test.tsx（直す）
20. frontend/src/locales/ja.json（直す）
21. frontend/src/locales/en.json（直す）
22. frontend/api-contract/openapi.json（手順7の道具で作り直す。手で直さない）

触らない: migrations/・invoices.py・invoice_renderer.py・po_renderer.py・label_validation.py・services/tenant.py・frontend/src/types/schema.d.ts（手順8で作られるが git add しない）。

## 2. 変更

### 2-1 backend/app/services/issuer.py（4 か所）

(1) Edit。変更前:

```
        text(f"SELECT country_code FROM {profiles} WHERE region = :region ORDER BY id LIMIT 1"),
        {"region": region},
```

変更後:

```
        text(f"SELECT country_code FROM {profiles} WHERE tenant_id = :tenant_id AND region = :region ORDER BY id LIMIT 1"),
        {"tenant_id": tenant_id, "region": region},
```

(2) Edit。変更前:

```
            WHERE p.region = :region
            ORDER BY p.id
            LIMIT 1
        """),
        {"region": region},
```

変更後:

```
            WHERE p.tenant_id = :tenant_id AND p.region = :region
            ORDER BY p.id
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "region": region},
```

(3) Edit。変更前:

```
    legacy = tenant_table_ref(db, tenant_id, "tenant_profile")
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {legacy}
            ORDER BY id LIMIT 1
        """),
    )
    old = result.mappings().first()
```

変更後:

```
    old = await read_legacy_issuer_values(db, tenant_id)
```

(4) Edit。変更前:

```
async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:
```

変更後:

```
async def read_legacy_issuer_values(db: AsyncSession, tenant_id: int) -> dict | None:
    """旧来の会社情報の表の6欄（会社名・英語名・住所・電話・メール・サイト）を読む。この表を読むのはここ1か所だけ（A40）。"""
    legacy = tenant_table_ref(db, tenant_id, "tenant_profile")
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {legacy}
            ORDER BY id LIMIT 1
        """),
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:
```

（get_issuer の残り `if not old:` 以下はそのまま。`old["company_name"]` などは dict でも同じに動く。）

### 2-2 backend/app/services/issuer_rules.py（新規。Write ツールでこの全文）

```python
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
```

### 2-3 backend/app/schemas/issuer_profiles.py（新規。Write ツールでこの全文）

```python
"""書類に載せる会社情報（国内用・海外用）の型（ADR-1061 便2-2c2b。design.md §3-4b）。名前は DB の列名と同じ。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IssuerRegion = Literal["domestic", "overseas"]


class IssuerProfileUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, max_length=2)
    postal_code: str | None = Field(default=None, max_length=10)
    prefecture_code: str | None = Field(default=None, max_length=2)
    state_region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    address1: str | None = Field(default=None, max_length=255)
    address2: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=16)
    is_invoice_registered: bool = False
    registration_number: str | None = Field(default=None, max_length=14)


class IssuerProfileResponse(BaseModel):
    region: IssuerRegion
    company_name: str
    email: str | None = None
    website: str | None = None
    country_code: str
    postal_code: str | None = None
    prefecture_code: str | None = None
    state_region: str | None = None
    city: str
    address1: str
    address2: str | None = None
    phone: str | None = None
    is_invoice_registered: bool
    registration_number: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class LegacyIssuerValues(BaseModel):
    """旧来の会社情報の表の6欄（読むだけ）。"""

    company_name: str | None = None
    company_name_en: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class IssuerProfilesResponse(BaseModel):
    domestic: IssuerProfileResponse | None = None
    overseas: IssuerProfileResponse | None = None
    legacy: LegacyIssuerValues | None = None
```

### 2-4 backend/app/routers/issuer_profiles.py（新規。Write ツールでこの全文）

```python
"""書類に載せる会社情報（国内用・海外用）の口（ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。

- GET /admin/issuer-profiles: 国内用・海外用の行（無い方は null）と、旧来の会社情報の6欄（読むだけ）。
- PUT /admin/issuer-profiles/{region}: 片方の行を丸ごと保存する。決まり違いは 422 と欄ごとの理由（detail.fields）。
- 旧来の会社情報を読むのは app.services.issuer.read_legacy_issuer_values の1か所だけ（A40）。
- 権限は今の会社情報の口と同じ（tenant.profile.view で読む・tenant.profile.edit で書く）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User
from app.schemas.issuer_profiles import (
    IssuerProfileResponse,
    IssuerProfilesResponse,
    IssuerProfileUpdate,
    IssuerRegion,
    LegacyIssuerValues,
)
from app.services.audit import record_audit_log
from app.services.issuer import read_legacy_issuer_values
from app.services.issuer_rules import check_issuer_codes, check_issuer_fields, normalize_issuer_payload

router = APIRouter()

_COLUMNS = (
    "company_name", "email", "website", "country_code", "postal_code", "prefecture_code",
    "state_region", "city", "address1", "address2", "phone", "is_invoice_registered",
    "registration_number",
)
_SELECT = "SELECT id, region, " + ", ".join(_COLUMNS) + ", updated_at"


async def _read_region(db: AsyncSession, tenant_id: int, region: str) -> dict[str, Any] | None:
    table = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    row = (await db.execute(
        text(f"{_SELECT} FROM {table} WHERE tenant_id = :tenant_id AND region = :region"),
        {"tenant_id": tenant_id, "region": region},
    )).mappings().first()
    return dict(row) if row else None


def _audit_values(row: dict[str, Any] | None) -> dict[str, Any] | None:
    return {key: row[key] for key in _COLUMNS} if row else None


@router.get(
    "/admin/issuer-profiles",
    response_model=IssuerProfilesResponse,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_issuer_profiles(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """国内用・海外用の行と、旧来の会社情報の6欄を返す。"""
    domestic = await _read_region(db, tenant_id, "domestic")
    overseas = await _read_region(db, tenant_id, "overseas")
    legacy = await read_legacy_issuer_values(db, tenant_id)
    return IssuerProfilesResponse(
        domestic=IssuerProfileResponse(**domestic) if domestic else None,
        overseas=IssuerProfileResponse(**overseas) if overseas else None,
        legacy=LegacyIssuerValues(**legacy) if legacy else None,
    )


@router.put(
    "/admin/issuer-profiles/{region}",
    response_model=IssuerProfileResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def put_issuer_profile(
    region: IssuerRegion,
    data: IssuerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """片方の地域の行を丸ごと保存する（無ければ作る）。"""
    values = normalize_issuer_payload(data.model_dump())
    errors = check_issuer_fields(values)
    for key, code in (await check_issuer_codes(db, values)).items():
        errors.setdefault(key, code)
    if errors:
        raise HTTPException(status_code=422, detail={"fields": errors})

    table = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    before = await _read_region(db, tenant_id, region)
    params = {key: values[key] for key in _COLUMNS}
    params.update({"tenant_id": tenant_id, "region": region, "user_id": current_user.id})
    if before:
        set_sql = ", ".join(f"{key} = :{key}" for key in _COLUMNS)
        result = await db.execute(
            text(
                f"UPDATE {table} SET {set_sql}, updated_by_user_id = :user_id, "
                "updated_at = CURRENT_TIMESTAMP WHERE tenant_id = :tenant_id AND region = :region"
            ),
            params,
        )
        action = "update"
    else:
        columns = ", ".join(_COLUMNS)
        placeholders = ", ".join(f":{key}" for key in _COLUMNS)
        result = await db.execute(
            text(
                f"INSERT INTO {table} (tenant_id, region, {columns}, updated_by_user_id) "
                f"VALUES (:tenant_id, :region, {placeholders}, :user_id)"
            ),
            params,
        )
        action = "create"
    if result.rowcount != 1:
        raise HTTPException(status_code=500, detail="issuer_profile_not_saved")

    after = await _read_region(db, tenant_id, region)
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action=action, table_name="tenant_issuer_profiles",
        record_id=after["id"], old_data=_audit_values(before), new_data=_audit_values(after),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    saved = await _read_region(db, tenant_id, region)
    return IssuerProfileResponse(**saved)
```

### 2-5 backend/app/routers/prefectures.py（新規。Write ツールでこの全文）

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant
from app.database import get_db
from app.schemas.prefectures import PrefectureResponse

router = APIRouter()


@router.get(
    "/prefectures",
    response_model=list[PrefectureResponse],
    summary="都道府県一覧",
)
async def list_prefectures(
    _tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[PrefectureResponse]:
    result = await db.execute(
        text(
            "SELECT code, name_ja, name_en, sort_order "
            "FROM public.prefectures "
            "ORDER BY sort_order, code"
        )
    )
    return [PrefectureResponse(**dict(row)) for row in result.mappings().all()]
```

### 2-6 backend/app/schemas/prefectures.py（新規。Write ツールでこの全文）

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PrefectureResponse(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name_ja: str
    name_en: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
```

### 2-7 backend/app/routers/tenant_profile.py（4 か所）

(1) Edit。変更前:

```
各テナント admin が PO PDF / メールの差出人情報 (会社名・住所・印鑑 URL 等) を
CRUD するエンドポイント。
```

変更後:

```
各テナント admin が印鑑画像 URL と既定の言語を読み書きするエンドポイント。
会社名・住所・電話・メール・サイトは issuer_profiles へ移した (ADR-1061 便2-2c2b)。
```

(2)(3)(4) 同じ形の3か所。`replace_all` を使わず1か所ずつ Edit する。

GET（12 スペースの字下げ。:70〜:71）と PUT の最後（12 スペース。:147〜:148）の2か所。変更前:

```
            SELECT id, company_name, company_name_en, address, phone, email,
                   website, seal_image_url, default_language,
```

変更後:

```
            SELECT id, seal_image_url, default_language,
```

PUT の空のとき（16 スペースの字下げ。:116〜:117）の1か所。変更前:

```
                SELECT id, company_name, company_name_en, address, phone, email,
                       website, seal_image_url, default_language,
```

変更後:

```
                SELECT id, seal_image_url, default_language,
```

ほかは変えない（404・空の送信で今の行を返す・監査の記録）。

### 2-8 backend/app/schemas/tenant_profile.py（全部書き直す。Write ツールでこの全文）

```python
"""TenantProfile Pydantic schemas (Sprint 8 / F8)

印鑑画像 URL と既定の言語を管理する。会社名・住所・電話・メール・サイトは
issuer_profiles へ移した (ADR-1061 便2-2c2b)。古い欄が送られてきても無視する。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_VALID_LANGUAGES = {"ja", "en", "ko", "zh"}


class TenantProfileResponse(BaseModel):
    id: int
    seal_image_url: str | None = None
    default_language: str = "ja"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantProfileUpdate(BaseModel):
    seal_image_url: str | None = Field(default=None, max_length=5000)
    default_language: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("default_language")
    @classmethod
    def _validate_language(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _VALID_LANGUAGES:
            raise ValueError(
                f"default_language must be one of {sorted(_VALID_LANGUAGES)}"
            )
        return v
```

### 2-9 backend/app/main.py（4 か所）

(1) Edit。変更前:

```
    invoices,
    item_corrections,  # PARITY-03 Phase 3 Stage 3: 修正履歴保存
```

変更後:

```
    invoices,
    issuer_profiles,  # ADR-1061 便2-2c2b: 書類に載せる会社情報
    item_corrections,  # PARITY-03 Phase 3 Stage 3: 修正履歴保存
```

(2) Edit。変更前:

```
    payment_fee_settings,  # 決済手数料設定 テナント用
```

変更後:

```
    payment_fee_settings,  # 決済手数料設定 テナント用
    prefectures,  # ADR-1061 便2-2c2b: 都道府県 (public.prefectures)
```

(3) Edit。変更前:

```
    countries.router, prefix="/api/v1", tags=["countries"],
    dependencies=[Depends(get_current_tenant)],
)
app.include_router(customer_statuses.router, prefix="/api/v1", tags=["customer-statuses"])
```

変更後:

```
    countries.router, prefix="/api/v1", tags=["countries"],
    dependencies=[Depends(get_current_tenant)],
)
app.include_router(
    prefectures.router, prefix="/api/v1", tags=["prefectures"],
    dependencies=[Depends(get_current_tenant)],
)
app.include_router(customer_statuses.router, prefix="/api/v1", tags=["customer-statuses"])
```

(4) Edit。変更前:

```
    tenant_profile.router, prefix="/api/v1", tags=["tenant_profile"],
    dependencies=[Depends(get_current_tenant)],
)
```

変更後:

```
    tenant_profile.router, prefix="/api/v1", tags=["tenant_profile"],
    dependencies=[Depends(get_current_tenant)],
)
# ADR-1061 便2-2c2b: 書類に載せる会社情報（国内用・海外用）
app.include_router(
    issuer_profiles.router, prefix="/api/v1", tags=["issuer_profiles"],
    dependencies=[Depends(get_current_tenant)],
)
```

（(4) の変更前が2か所以上に当たったら止める。）

### 2-10 backend/app/realtime/topics.py（1 か所）

Edit。変更前:

```
    ("PUT", "/api/v1/admin/tenant-profile"): _PENDING,
```

変更後:

```
    ("PUT", "/api/v1/admin/tenant-profile"): _PENDING,
    ("PUT", "/api/v1/admin/issuer-profiles/{region}"): _PENDING,
```

### 2-11 backend/tests/conftest.py（1 か所）

Edit。変更前:

```
        "app.routers.tenant_profile",
```

変更後:

```
        "app.routers.tenant_profile",
        "app.routers.issuer_profiles",
```

### 2-12 backend/tests/test_tenant_profile.py（全部書き直す。Write ツールでこの全文）

```python
"""tenant_profile router のテスト (Sprint 8 / F8 → ADR-1061 便2-2c2b)

SQLite ベースで読み書き + 認可を検証する。
会社名・住所・電話・メール・サイトは issuer_profiles へ移したので、この口は返さず受け取らない。

カバー範囲:
  - GET /admin/tenant-profile: 既定の行が返る（古い6欄は返さない）
  - PUT /admin/tenant-profile: 既定の言語が反映され、古い欄は無視される
  - PUT validation: default_language の不正値で 422
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_get_tenant_profile_returns_seeded_row(client, db_session):
    """既定行 (空) が seed されている前提で 200 を返す。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    resp = await client.get("/api/v1/admin/tenant-profile")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["default_language"] == "ja"
    assert "company_name" not in body


@pytest.mark.asyncio
async def test_get_tenant_profile_404_when_not_seeded(client, db_session):
    """seed 未投入なら 404 (migration 069 適用要)。"""
    await db_session.execute(text("DELETE FROM tenant_profile"))
    await db_session.commit()

    resp = await client.get("/api/v1/admin/tenant-profile")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tenant_profile_persists_fields(client, db_session):
    """既定の言語は保存され、古い欄は保存されない。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    payload = {
        "company_name": "QA テナント株式会社",
        "company_name_en": "QA Tenant Inc.",
        "address": "東京都渋谷区 1-2-3",
        "phone": "03-1234-5678",
        "email": "po@qa-tenant.example.com",
        "website": "https://qa-tenant.example.com",
        "default_language": "en",
    }
    resp = await client.put("/api/v1/admin/tenant-profile", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "company_name" not in body
    assert body["default_language"] == "en"

    row = (await db_session.execute(text(
        "SELECT company_name, default_language FROM tenant_profile ORDER BY id LIMIT 1"
    ))).first()
    assert row[0] is None
    assert row[1] == "en"


@pytest.mark.asyncio
async def test_update_tenant_profile_partial_update(client, db_session):
    """古い欄だけを送っても何も変わらない。"""
    await db_session.execute(text(
        "INSERT INTO tenant_profile (company_name, default_language) VALUES ('既存', 'ja')"
    ))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"phone": "06-9999-0000"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "phone" not in body
    assert body["default_language"] == "ja"

    row = (await db_session.execute(text(
        "SELECT company_name, phone FROM tenant_profile ORDER BY id LIMIT 1"
    ))).first()
    assert (row[0], row[1]) == ("既存", None)


@pytest.mark.asyncio
async def test_update_tenant_profile_rejects_invalid_language(client, db_session):
    """default_language のホワイトリスト外は 422。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"default_language": "fr"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_tenant_profile_404_when_not_seeded(client, db_session):
    """既定行が無い (migration 069 未適用) → 404。"""
    await db_session.execute(text("DELETE FROM tenant_profile"))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"default_language": "en"},
    )
    assert resp.status_code == 404
```

### 2-13 backend/tests/test_issuer_profiles.py（新規。Write ツールでこの全文）

```python
"""書類に載せる会社情報（国内用・海外用）の口の試験（ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。

- 国内用・海外用の行を片方ずつ丸ごと保存し、もう片方は変わらない。
- 決まり違いは 422 と欄ごとの理由（detail.fields）。保存しない。
- 登録が無のときは番号を送っても NULL で保存する。
- 保存のたびに監査の記録が1行残る（作った・直した）。
- ほかの会社の行は読まない。
- 都道府県名は試験に書かず、正本の seed ファイルから読む。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy import text

_ROOT = Path(__file__).resolve().parents[2]
_PREF_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_PREF_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_URL = "/api/v1/admin/issuer-profiles"
_REG_NO = "T1234567890123"


async def _seed_prefectures(db_session) -> list[tuple[str, str, str, str]]:
    rows = _PREF_ROW_RE.findall(_PREF_SEED.read_text("utf-8"))
    for code, name_ja, name_en, sort_order in rows:
        await db_session.execute(
            text("INSERT OR IGNORE INTO prefectures (code, name_ja, name_en, sort_order) VALUES (:c, :j, :e, :s)"),
            {"c": code, "j": name_ja, "e": name_en, "s": int(sort_order)},
        )
    await db_session.commit()
    return rows


async def _seed_legacy(db_session) -> None:
    await db_session.execute(text(
        "INSERT INTO tenant_profile (company_name, company_name_en, address, phone, email, website, default_language) "
        "VALUES ('Legacy Co', 'Legacy Co EN', 'Legacy Street 1', '03-0000-0000', 'legacy@example.com', "
        "'https://legacy.example.com', 'ja')"
    ))
    await db_session.commit()


def _domestic(**over):
    body = {
        "company_name": "Domestic Co", "email": "info@example.com", "website": None,
        "country_code": "JP", "postal_code": "1000001", "prefecture_code": "13", "state_region": None,
        "city": "Chiyoda", "address1": "1-1", "address2": None, "phone": "0312345678",
        "is_invoice_registered": False, "registration_number": None,
    }
    body.update(over)
    return body


def _overseas(**over):
    body = {
        "company_name": "Overseas Co", "email": None, "website": None,
        "country_code": "US", "postal_code": "94105", "prefecture_code": None, "state_region": "CA",
        "city": "San Francisco", "address1": "1 Market St", "address2": None, "phone": "+14155550100",
        "is_invoice_registered": False, "registration_number": None,
    }
    body.update(over)
    return body


async def _count_rows(db_session) -> int:
    return (await db_session.execute(text("SELECT COUNT(*) FROM tenant_issuer_profiles"))).scalar_one()


async def test_get_returns_nulls_without_rows(client):
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"domestic": None, "overseas": None, "legacy": None}


async def test_get_returns_legacy_values_when_region_row_missing(client, db_session):
    await _seed_legacy(db_session)
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["domestic"] is None
    assert body["overseas"] is None
    assert body["legacy"]["company_name"] == "Legacy Co"
    assert body["legacy"]["email"] == "legacy@example.com"


async def test_put_creates_then_updates_with_audit(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["region"] == "domestic"
    assert body["company_name"] == "Domestic Co"
    assert body["prefecture_code"] == "13"

    resp = await client.put(f"{_URL}/domestic", json=_domestic(company_name="Domestic Co 2"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["company_name"] == "Domestic Co 2"
    assert await _count_rows(db_session) == 1

    rows = (await db_session.execute(text(
        "SELECT action, old_data, new_data FROM audit_logs "
        "WHERE table_name = 'tenant_issuer_profiles' ORDER BY id"
    ))).all()
    assert [r[0] for r in rows] == ["create", "update"]
    assert rows[0][1] is None
    assert json.loads(rows[0][2])["company_name"] == "Domestic Co"
    assert json.loads(rows[1][1])["company_name"] == "Domestic Co"
    assert json.loads(rows[1][2])["company_name"] == "Domestic Co 2"


async def test_put_normalizes_spaces_case_and_empty(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/domestic",
        json=_domestic(company_name="  Domestic Co  ", country_code="jp", email=""),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["company_name"] == "Domestic Co"
    assert body["country_code"] == "JP"
    assert body["email"] is None


async def test_put_rejects_japan_rules_by_field(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/domestic",
        json=_domestic(postal_code="100-0001", phone="+81312345678", prefecture_code=None, state_region="Tokyo"),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "postal_code": "postal_jp",
        "phone": "phone_jp",
        "prefecture_code": "required",
        "state_region": "must_be_empty",
    }
    assert await _count_rows(db_session) == 0


async def test_put_rejects_foreign_rules_by_field(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(
        f"{_URL}/overseas",
        json=_overseas(postal_code="9410#", phone="0312345678", prefecture_code="13"),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "postal_code": "postal_foreign",
        "phone": "phone_foreign",
        "prefecture_code": "must_be_empty",
    }


async def test_put_rejects_missing_required_fields(client):
    resp = await client.put(
        f"{_URL}/overseas",
        json=_overseas(company_name="  ", country_code=None, city="", address1=None, phone=None),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {
        "company_name": "required",
        "country_code": "required",
        "city": "required",
        "address1": "required",
    }


async def test_put_rejects_unknown_codes(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic(prefecture_code="99"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"prefecture_code": "unknown_code"}
    resp = await client.put(f"{_URL}/overseas", json=_overseas(country_code="ZZ"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"country_code": "unknown_code"}


async def test_put_registration_number_rules(client, db_session):
    await _seed_prefectures(db_session)
    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number="T123"))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"registration_number": "registration_number"}
    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number=None))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["fields"] == {"registration_number": "required"}

    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=True, registration_number=_REG_NO))
    assert resp.status_code == 200, resp.text
    assert resp.json()["registration_number"] == _REG_NO

    resp = await client.put(f"{_URL}/domestic", json=_domestic(is_invoice_registered=False, registration_number=_REG_NO))
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_invoice_registered"] is False
    assert resp.json()["registration_number"] is None
    row = (await db_session.execute(text(
        "SELECT registration_number FROM tenant_issuer_profiles WHERE region = 'domestic'"
    ))).first()
    assert row[0] is None


async def test_saving_one_region_keeps_the_other(client, db_session):
    await _seed_prefectures(db_session)
    assert (await client.put(f"{_URL}/domestic", json=_domestic())).status_code == 200
    assert (await client.put(f"{_URL}/overseas", json=_overseas())).status_code == 200
    assert (await client.put(f"{_URL}/domestic", json=_domestic(company_name="Domestic Co 3"))).status_code == 200

    body = (await client.get(_URL)).json()
    assert body["domestic"]["company_name"] == "Domestic Co 3"
    assert body["overseas"]["company_name"] == "Overseas Co"
    assert body["overseas"]["state_region"] == "CA"


async def test_other_tenant_rows_are_not_read(client, db_session):
    await _seed_prefectures(db_session)
    await db_session.execute(text(
        "INSERT INTO tenant_issuer_profiles (tenant_id, region, company_name, country_code, city, address1) "
        "VALUES (1000, 'domestic', 'Other Tenant Co', 'US', 'X', 'Y')"
    ))
    await db_session.commit()

    assert (await client.get(_URL)).json()["domestic"] is None
    assert (await client.put(f"{_URL}/domestic", json=_domestic())).status_code == 200
    rows = (await db_session.execute(text(
        "SELECT tenant_id, company_name FROM tenant_issuer_profiles WHERE region = 'domestic' ORDER BY tenant_id"
    ))).all()
    assert [tuple(r) for r in rows] == [(999, "Domestic Co"), (1000, "Other Tenant Co")]


async def test_unknown_region_is_422(client):
    resp = await client.put(f"{_URL}/x", json=_overseas())
    assert resp.status_code == 422


async def test_prefectures_list_comes_from_the_seed_in_order(client, db_session):
    rows = await _seed_prefectures(db_session)
    assert len(rows) == 47
    resp = await client.get("/api/v1/prefectures")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected = sorted(rows, key=lambda r: (int(r[3]), r[0]))
    assert [(p["code"], p["name_ja"], p["name_en"], p["sort_order"]) for p in body] == [
        (c, j, e, int(s)) for c, j, e, s in expected
    ]
```

### 2-14 frontend/src/pages/admin/issuerProfileForm.ts（新規。Write ツールでこの全文）

```ts
/**
 * 書類に載せる会社情報（国内用・海外用）の型と、画面の欄 ⇔ API の値の変換
 * （ADR-1061 便2-2c2b。design.md §3-4・§3-4b）。
 * 決まりの正本は backend（app/services/issuer_rules.py と表の CHECK）。
 * 画面は返ってきた欄ごとの理由の番号を文言キーに直し、t() で文にする（ADR-027）。
 */
export type IssuerRegion = "domestic" | "overseas";

export const ISSUER_PROFILES_PATH = "/admin/issuer-profiles";
export const PREFECTURES_PATH = "/prefectures";
/** 日本の国の番号。backend の issuer_rules.py と表の CHECK が日本の決まりを当てる国 */
export const JAPAN_COUNTRY_CODE = "JP";

export interface IssuerProfile {
  region: IssuerRegion;
  company_name: string;
  email: string | null;
  website: string | null;
  country_code: string;
  postal_code: string | null;
  prefecture_code: string | null;
  state_region: string | null;
  city: string;
  address1: string;
  address2: string | null;
  phone: string | null;
  is_invoice_registered: boolean;
  registration_number: string | null;
  updated_at: string;
}

export interface LegacyIssuerValues {
  company_name: string | null;
  company_name_en: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
}

export interface IssuerProfiles {
  domestic: IssuerProfile | null;
  overseas: IssuerProfile | null;
  legacy: LegacyIssuerValues | null;
}

export interface Prefecture {
  code: string;
  name_ja: string;
  name_en: string;
  sort_order: number;
}

export interface RegionForm {
  company_name: string;
  email: string;
  website: string;
  country_code: string;
  postal_code: string;
  prefecture_code: string;
  state_region: string;
  city: string;
  address1: string;
  address2: string;
  phone: string;
  is_invoice_registered: boolean;
  registration_number: string;
}

export type IssuerForm = Record<IssuerRegion, RegionForm>;
export type FieldErrors = Partial<Record<keyof RegionForm, string>>;

export const emptyRegionForm: RegionForm = {
  company_name: "",
  email: "",
  website: "",
  country_code: "",
  postal_code: "",
  prefecture_code: "",
  state_region: "",
  city: "",
  address1: "",
  address2: "",
  phone: "",
  is_invoice_registered: false,
  registration_number: "",
};

export const emptyIssuerForm: IssuerForm = { domestic: emptyRegionForm, overseas: emptyRegionForm };

export function toRegionForm(p: IssuerProfile | null): RegionForm {
  if (!p) return emptyRegionForm;
  return {
    company_name: p.company_name ?? "",
    email: p.email ?? "",
    website: p.website ?? "",
    country_code: p.country_code ?? "",
    postal_code: p.postal_code ?? "",
    prefecture_code: p.prefecture_code ?? "",
    state_region: p.state_region ?? "",
    city: p.city ?? "",
    address1: p.address1 ?? "",
    address2: p.address2 ?? "",
    phone: p.phone ?? "",
    is_invoice_registered: Boolean(p.is_invoice_registered),
    registration_number: p.registration_number ?? "",
  };
}

export function toIssuerForm(d: IssuerProfiles): IssuerForm {
  return { domestic: toRegionForm(d.domestic), overseas: toRegionForm(d.overseas) };
}

export function isJapan(form: RegionForm): boolean {
  return form.country_code === JAPAN_COUNTRY_CODE;
}

const textOrNull = (v: string): string | null => (v.trim() === "" ? null : v.trim());

/** 保存で送る値。見えない欄（日本なら州・地域、日本以外なら都道府県、登録が無なら番号）は null */
export function toIssuerPayload(form: RegionForm): Record<string, string | boolean | null> {
  const jp = isJapan(form);
  return {
    company_name: textOrNull(form.company_name),
    email: textOrNull(form.email),
    website: textOrNull(form.website),
    country_code: textOrNull(form.country_code),
    postal_code: textOrNull(form.postal_code),
    prefecture_code: jp ? textOrNull(form.prefecture_code) : null,
    state_region: jp ? null : textOrNull(form.state_region),
    city: textOrNull(form.city),
    address1: textOrNull(form.address1),
    address2: textOrNull(form.address2),
    phone: textOrNull(form.phone),
    is_invoice_registered: form.is_invoice_registered,
    registration_number: form.is_invoice_registered ? textOrNull(form.registration_number) : null,
  };
}

const ERROR_KEYS: Record<string, string> = {
  required: "issuerProfile.errors.required",
  postal_jp: "issuerProfile.errors.postalJp",
  postal_foreign: "issuerProfile.errors.postalForeign",
  phone_jp: "issuerProfile.errors.phoneJp",
  phone_foreign: "issuerProfile.errors.phoneForeign",
  registration_number: "issuerProfile.errors.registrationNumber",
  unknown_code: "issuerProfile.errors.unknownCode",
  must_be_empty: "issuerProfile.errors.mustBeEmpty",
};

/** 422 の detail（{ fields: { 欄: 理由の番号 } }）を、欄 → 文言キーに直す。形が違えば null */
export function fieldErrorKeys(detail: unknown): FieldErrors | null {
  if (detail === null || typeof detail !== "object" || !("fields" in detail)) return null;
  const fields = (detail as { fields: unknown }).fields;
  if (fields === null || typeof fields !== "object") return null;
  const out: FieldErrors = {};
  for (const [field, code] of Object.entries(fields as Record<string, unknown>)) {
    if (typeof code === "string" && code in ERROR_KEYS) {
      out[field as keyof RegionForm] = ERROR_KEYS[code];
    }
  }
  return out;
}

/** 都道府県の選択肢。言語が日本語なら name_ja、それ以外は name_en（design.md §3-4「都道府県の一覧」） */
export function prefectureOptions(rows: Prefecture[], language: string): { value: string; label: string }[] {
  const ja = language.startsWith("ja");
  return rows.map((r) => ({ value: r.code, label: ja ? r.name_ja : r.name_en }));
}

/** 前の会社情報（古い6欄）を読むだけの欄に出す文。空の欄は飛ばす */
export function legacyText(v: LegacyIssuerValues): string {
  return [v.company_name, v.company_name_en, v.address, v.phone, v.email, v.website]
    .filter((x): x is string => typeof x === "string" && x.trim() !== "")
    .join("\n");
}
```

### 2-15 frontend/src/pages/admin/issuerProfileForm.test.ts（新規。Write ツールでこの全文）

```ts
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  emptyRegionForm,
  fieldErrorKeys,
  legacyText,
  prefectureOptions,
  toIssuerForm,
  toIssuerPayload,
  type RegionForm,
} from "./issuerProfileForm";

const SRC_ROOT = join(__dirname, "..", "..");

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (/\.(ts|tsx|json)$/.test(name)) out.push(path);
  }
  return out;
}

const form = (over: Partial<RegionForm>): RegionForm => ({ ...emptyRegionForm, ...over });

describe("toIssuerPayload", () => {
  it("sends prefecture and drops state for Japan, trimming and nulling empties", () => {
    const p = toIssuerPayload(form({
      company_name: "  A Co  ", country_code: "JP", prefecture_code: "13", state_region: "X",
      postal_code: "1000001", city: "C", address1: "1-1", email: "",
    }));
    expect(p.company_name).toBe("A Co");
    expect(p.prefecture_code).toBe("13");
    expect(p.state_region).toBeNull();
    expect(p.email).toBeNull();
  });

  it("sends state and drops prefecture outside Japan", () => {
    const p = toIssuerPayload(form({ country_code: "US", prefecture_code: "13", state_region: "CA" }));
    expect(p.prefecture_code).toBeNull();
    expect(p.state_region).toBe("CA");
  });

  it("drops the registration number when not registered", () => {
    expect(toIssuerPayload(form({ is_invoice_registered: false, registration_number: "T1234567890123" })).registration_number).toBeNull();
    expect(toIssuerPayload(form({ is_invoice_registered: true, registration_number: "T1234567890123" })).registration_number).toBe("T1234567890123");
  });
});

describe("fieldErrorKeys", () => {
  it("maps reason codes to message keys", () => {
    expect(fieldErrorKeys({ fields: { postal_code: "postal_jp", phone: "phone_foreign", city: "required" } })).toEqual({
      postal_code: "issuerProfile.errors.postalJp",
      phone: "issuerProfile.errors.phoneForeign",
      city: "issuerProfile.errors.required",
    });
  });

  it("returns null for other shapes", () => {
    expect(fieldErrorKeys("bad")).toBeNull();
    expect(fieldErrorKeys([{ loc: ["body"], msg: "x" }])).toBeNull();
    expect(fieldErrorKeys(null)).toBeNull();
  });
});

describe("prefectureOptions and forms", () => {
  const rows = [{ code: "13", name_ja: "JA-13", name_en: "EN-13", sort_order: 13 }];
  it("uses name_ja for Japanese and name_en otherwise", () => {
    expect(prefectureOptions(rows, "ja")).toEqual([{ value: "13", label: "JA-13" }]);
    expect(prefectureOptions(rows, "en")).toEqual([{ value: "13", label: "EN-13" }]);
  });

  it("starts empty when a region has no row and has no default country", () => {
    const f = toIssuerForm({ domestic: null, overseas: null, legacy: null });
    expect(f.domestic).toEqual(emptyRegionForm);
    expect(f.overseas.country_code).toBe("");
  });

  it("joins legacy values skipping empties", () => {
    expect(legacyText({ company_name: "Old", company_name_en: null, address: " ", phone: "1", email: null, website: null })).toBe("Old\n1");
  });
});

describe("prefecture names live only in the DB seed", () => {
  it("no source file under src contains a prefecture name", () => {
    // この試験ファイル自身も src の下にある。名前を直接書くと自分に当たるので、文字の番号から組み立てる（北海道）
    const name = String.fromCodePoint(0x5317, 0x6d77, 0x9053);
    const hits = walk(SRC_ROOT).filter((path) => readFileSync(path, "utf-8").includes(name));
    expect(hits).toEqual([]);
  });
});
```

### 2-16 frontend/src/pages/admin/InvoiceRegistrationField.tsx（新規。Write ツールでこの全文）

```tsx
/**
 * インボイス登録の有無と番号の欄（ADR-1061 便2-2c2b。design.md §3-4a。Toggle と TextField の金型）。
 * 番号の決まり（T と13桁）の正本は backend の issuer_rules.py と表の CHECK。
 */
import { useTranslation } from "react-i18next";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";

interface InvoiceRegistrationFieldProps {
  idPrefix: string;
  registered: boolean;
  number: string;
  disabled: boolean;
  error?: string;
  onRegisteredChange: (next: boolean) => void;
  onNumberChange: (next: string) => void;
}

export function InvoiceRegistrationField({
  idPrefix,
  registered,
  number,
  disabled,
  error,
  onRegisteredChange,
  onNumberChange,
}: InvoiceRegistrationFieldProps) {
  const { t } = useTranslation();
  const toggleId = `${idPrefix}-invoice-registered`;
  return (
    <Stack gap="2">
      <div className="form-group">
        <label htmlFor={toggleId}>{t("issuerProfile.invoiceRegistered")}</label>
        <Toggle
          id={toggleId}
          checked={registered}
          onCheckedChange={onRegisteredChange}
          disabled={disabled}
        />
      </div>
      {registered && (
        <TextField
          id={`${idPrefix}-registration-number`}
          data-testid={`${idPrefix}-registration-number`}
          label={t("issuerProfile.registrationNumber")}
          helperText={t("issuerProfile.registrationHint")}
          error={error}
          value={number}
          onChange={(e) => onNumberChange(e.target.value)}
          disabled={disabled}
          maxLength={14}
          required
          fullWidth
        />
      )}
    </Stack>
  );
}
```

### 2-17 frontend/src/pages/admin/IssuerProfileSection.tsx（新規。Write ツールでこの全文）

```tsx
/**
 * 書類に載せる会社情報（国内用・海外用のタブ）（ADR-1061 便2-2c2b。design.md §3-4・§3-4a・§3-4b）。
 *
 * 正本は会社ごとの tenant_issuer_profiles（国内用・海外用の2行まで）。
 * 行が無いタブは、前の会社情報（古い6欄）を読むだけの欄で見せ、入れ直しを案内する。
 * 都道府県と国の一覧は API から読む（画面のコードに名前を書かない）。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "../../lib/api";
import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { CountryCombobox } from "../../components/CountryCombobox";
import { SectionCard } from "../../components/SectionCard";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { Tabs } from "../../components/Tabs";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { LoadingBlock } from "../../components/loading";
import { InvoiceRegistrationField } from "./InvoiceRegistrationField";
import {
  ISSUER_PROFILES_PATH,
  PREFECTURES_PATH,
  emptyIssuerForm,
  fieldErrorKeys,
  isJapan,
  legacyText,
  prefectureOptions,
  toIssuerForm,
  toIssuerPayload,
  toRegionForm,
  type FieldErrors,
  type IssuerProfile,
  type IssuerProfiles,
  type IssuerRegion,
  type Prefecture,
  type RegionForm,
} from "./issuerProfileForm";

interface IssuerProfileSectionProps {
  canEdit: boolean;
}

export function IssuerProfileSection({ canEdit }: IssuerProfileSectionProps) {
  const { t, i18n } = useTranslation();
  const [region, setRegion] = useState<IssuerRegion>("domestic");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const profilesQ = useApiQuery<IssuerProfiles>(ISSUER_PROFILES_PATH);
  const prefecturesQ = useApiQuery<Prefecture[]>(PREFECTURES_PATH);
  const { form, setForm, ready } = useSeededForm(ISSUER_PROFILES_PATH, profilesQ.data, toIssuerForm, emptyIssuerForm);
  const cache = useApiCache();
  const readError = profilesQ.error ? (profilesQ.error instanceof Error ? profilesQ.error.message : t("common.fetchError")) : "";

  const current = form[region];
  const row = profilesQ.data?.[region] ?? null;
  const legacy = profilesQ.data?.legacy ?? null;
  const jp = isJapan(current);
  const locked = !canEdit;
  const idp = `issuer-${region}`;
  const fieldError = (key: keyof RegionForm): string | undefined => {
    const messageKey = fieldErrors[key];
    return messageKey ? t(messageKey) : undefined;
  };

  const update = <K extends keyof RegionForm>(key: K, value: RegionForm[K]) => {
    setForm((prev) => ({ ...prev, [region]: { ...prev[region], [key]: value } }));
  };

  const changeRegion = (next: IssuerRegion) => {
    setRegion(next);
    setFieldErrors({});
    setError("");
    setInfo("");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setFieldErrors({});
    setSaving(true);
    try {
      const saved = await api.put<IssuerProfile>(`${ISSUER_PROFILES_PATH}/${region}`, toIssuerPayload(current));
      const base: IssuerProfiles = profilesQ.data ?? { domestic: null, overseas: null, legacy: null };
      cache.write(ISSUER_PROFILES_PATH, { ...base, [region]: saved });
      setForm((prev) => ({ ...prev, [region]: toRegionForm(saved) }));
      setInfo(region === "domestic" ? t("issuerProfile.savedDomestic") : t("issuerProfile.savedOverseas"));
    } catch (err) {
      const keys = err instanceof ApiError && err.status === 422 ? fieldErrorKeys(err.responseDetail) : null;
      if (keys) {
        setFieldErrors(keys);
        setError(t("issuerProfile.fixFields"));
      } else {
        setError(err instanceof Error ? err.message : t("common.operationError"));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard title={t("issuerProfile.sectionTitle")}>
      {profilesQ.isPending ? (
        <LoadingBlock />
      ) : !ready ? (
        <div className="error-message">{readError}</div>
      ) : (
        <form className="form" onSubmit={handleSave} data-testid="issuer-profile-form">
          <Stack gap="4">
            <Tabs<IssuerRegion>
              items={[
                { key: "domestic", label: t("issuerProfile.tabDomestic") },
                { key: "overseas", label: t("issuerProfile.tabOverseas") },
              ]}
              activeKey={region}
              onChange={changeRegion}
              variant="underline"
            />
            {error && <div className="error-message">{error}</div>}
            {info && <div className="info-message" data-testid="issuer-profile-info">{info}</div>}
            {row === null && (
              <Callout variant="info" title={t("issuerProfile.legacyTitle")}>
                <Stack gap="2">
                  <p>{t("issuerProfile.legacyBody")}</p>
                  {legacy && legacyText(legacy) !== "" && (
                    <Textarea
                      id={`${idp}-legacy`}
                      label={t("issuerProfile.legacyValues")}
                      value={legacyText(legacy)}
                      readOnly
                      rows={6}
                    />
                  )}
                </Stack>
              </Callout>
            )}
            <TextField
              id={`${idp}-company-name`}
              data-testid={`${idp}-company-name`}
              label={t("issuerProfile.companyName")}
              value={current.company_name}
              onChange={(e) => update("company_name", e.target.value)}
              error={fieldError("company_name")}
              disabled={locked}
              maxLength={255}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-email`}
              label={t("issuerProfile.email")}
              type="email"
              value={current.email}
              onChange={(e) => update("email", e.target.value)}
              error={fieldError("email")}
              disabled={locked}
              maxLength={255}
              fullWidth
            />
            <TextField
              id={`${idp}-website`}
              label={t("issuerProfile.website")}
              value={current.website}
              onChange={(e) => update("website", e.target.value)}
              error={fieldError("website")}
              disabled={locked}
              maxLength={255}
              fullWidth
            />
            <div className="form-group">
              <label htmlFor={`${idp}-country`}>{t("issuerProfile.country")}</label>
              <CountryCombobox
                id={`${idp}-country`}
                value={current.country_code}
                onChange={(value) => update("country_code", value)}
                disabled={locked}
                required
              />
              {fieldError("country_code") && <div className="error-message">{fieldError("country_code")}</div>}
            </div>
            <TextField
              id={`${idp}-postal-code`}
              label={t("issuerProfile.postalCode")}
              helperText={jp ? t("issuerProfile.postalHintJp") : t("issuerProfile.postalHintForeign")}
              value={current.postal_code}
              onChange={(e) => update("postal_code", e.target.value)}
              error={fieldError("postal_code")}
              disabled={locked}
              maxLength={10}
              required={jp}
              fullWidth
            />
            {jp ? (
              <Select
                id={`${idp}-prefecture`}
                label={t("issuerProfile.prefecture")}
                placeholder={t("issuerProfile.prefecturePlaceholder")}
                options={prefectureOptions(prefecturesQ.data ?? [], i18n.language)}
                value={current.prefecture_code}
                onChange={(e) => update("prefecture_code", e.target.value)}
                error={fieldError("prefecture_code")}
                disabled={locked}
                required
                fullWidth
              />
            ) : (
              <TextField
                id={`${idp}-state-region`}
                label={t("issuerProfile.stateRegion")}
                value={current.state_region}
                onChange={(e) => update("state_region", e.target.value)}
                error={fieldError("state_region")}
                disabled={locked}
                maxLength={100}
                fullWidth
              />
            )}
            <TextField
              id={`${idp}-city`}
              label={t("issuerProfile.city")}
              value={current.city}
              onChange={(e) => update("city", e.target.value)}
              error={fieldError("city")}
              disabled={locked}
              maxLength={100}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-address1`}
              label={t("issuerProfile.address1")}
              value={current.address1}
              onChange={(e) => update("address1", e.target.value)}
              error={fieldError("address1")}
              disabled={locked}
              maxLength={255}
              required
              fullWidth
            />
            <TextField
              id={`${idp}-address2`}
              label={t("issuerProfile.address2")}
              value={current.address2}
              onChange={(e) => update("address2", e.target.value)}
              error={fieldError("address2")}
              disabled={locked}
              fullWidth
            />
            <TextField
              id={`${idp}-phone`}
              label={t("issuerProfile.phone")}
              helperText={jp ? t("issuerProfile.phoneHintJp") : t("issuerProfile.phoneHintForeign")}
              value={current.phone}
              onChange={(e) => update("phone", e.target.value)}
              error={fieldError("phone")}
              disabled={locked}
              maxLength={16}
              fullWidth
            />
            <InvoiceRegistrationField
              idPrefix={idp}
              registered={current.is_invoice_registered}
              number={current.registration_number}
              disabled={locked}
              error={fieldError("registration_number")}
              onRegisteredChange={(next) => update("is_invoice_registered", next)}
              onNumberChange={(next) => update("registration_number", next)}
            />
            {canEdit && (
              <div className="form-actions">
                <Button loading={saving} variant="primary" size="md"
                  type="submit"
                  disabled={saving}
                  data-testid="issuer-profile-save"
                >
                  {t("common.save")}
                </Button>
              </div>
            )}
          </Stack>
        </form>
      )}
    </SectionCard>
  );
}
```

### 2-18 frontend/src/pages/admin/TenantProfilePage.tsx（全部書き直す。Write ツールでこの全文）

```tsx
/**
 * TenantProfilePage（会社情報。Sprint 8 / F8 → ADR-1061 便2-2c2b）
 *
 * 上から: 印鑑画像 URL・既定の言語（この画面のフォーム）、書類に載せる会社情報（国内用・海外用。IssuerProfileSection）。
 * 会社名・住所・電話・メール・サイトの欄は IssuerProfileSection へ移した（design.md §3-4）。
 *
 * 権限:
 *   tenant.profile.view → 閲覧
 *   tenant.profile.edit → 保存
 *
 * 関連:
 *   backend/app/routers/tenant_profile.py
 *   backend/app/routers/issuer_profiles.py
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";
import { IssuerProfileSection } from "./IssuerProfileSection";

interface TenantProfile {
  id: number;
  seal_image_url: string | null;
  default_language: string;
  created_at: string;
  updated_at: string;
}

interface FormState {
  seal_image_url: string;
  default_language: string;
}

const emptyForm: FormState = {
  seal_image_url: "",
  default_language: "ja",
};

const PROFILE_PATH = "/admin/tenant-profile";
const toForm = (data: TenantProfile): FormState => ({
  seal_image_url: data.seal_image_url ?? "",
  default_language: data.default_language ?? "ja",
});

export default function TenantProfilePage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const canView = hasPermission("tenant.profile.view");
  const canEdit = hasPermission("tenant.profile.edit");
  const profileQ = useApiQuery<TenantProfile>(PROFILE_PATH, { enabled: canView });
  const { form, setForm, ready } = useSeededForm(PROFILE_PATH, profileQ.data, toForm, emptyForm);
  const cache = useApiCache();
  const readError = profileQ.error ? (profileQ.error instanceof Error ? profileQ.error.message : t("common.fetchError")) : "";
  const shownError = error || readError;

  const handleChange = (key: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setSaving(true);
    try {
      // 空文字は null に変換 (バックエンド側で null と空文字を等価扱い)
      const payload: Record<string, string | null> = {};
      (Object.keys(form) as Array<keyof FormState>).forEach((k) => {
        const v = form[k];
        payload[k] = v === "" ? null : v;
      });
      const saved = await api.put<TenantProfile>("/admin/tenant-profile", payload);
      cache.write(PROFILE_PATH, saved);
      setInfo(t("tenantProfile.saved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.operationError"));
    } finally {
      setSaving(false);
    }
  };

  if (!canView) {
    return (
      <PageLayout navKey="nav.tenantProfile">
        <div className="error-message">{t("tenantProfile.permissionRequired")}</div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.tenantProfile" subtitleKey="tenantProfile.subtitle">
      {profileQ.isPending ? (
        <LoadingBlock />
      ) : !ready ? (
        <div className="error-message">{shownError}</div>
      ) : (
        <Stack gap="6">
          <form className="form" onSubmit={handleSave} data-testid="tenant-profile-form">
            {shownError && <div className="error-message">{shownError}</div>}
            {info && <div className="info-message" data-testid="tenant-profile-info">{info}</div>}

            <div className="form-group">
              <label htmlFor="tp-seal-url">{t("tenantProfile.sealImageUrl")}</label>
              <TextFieldControl
                id="tp-seal-url"
                data-testid="tp-seal-image-url"
                type="text"
                value={form.seal_image_url}
                onChange={handleChange("seal_image_url")}
                disabled={!canEdit}
                placeholder="https://..."
              />
              <small className="form-hint">{t("tenantProfile.sealHint")}</small>
            </div>

            <div className="form-group">
              <label htmlFor="tp-default-language">{t("tenantProfile.defaultLanguage")}</label>
              <SelectControl
                fullWidth
                id="tp-default-language"
                data-testid="tp-default-language"
                value={form.default_language}
                onChange={handleChange("default_language")}
                disabled={!canEdit}
              >
                <option value="ja">{t("language.ja")} (ja)</option>
                <option value="en">English (en)</option>
                <option value="ko">한국어 (ko)</option>
                <option value="zh">{t("language.zh")} (zh)</option>
              </SelectControl>
            </div>

            {canEdit && (
              <div className="form-actions">
                <Button loading={saving} variant="primary" size="md"
                  type="submit"

                  disabled={saving}
                  data-testid="tenant-profile-save"
                >
                  {t("common.save")}
                </Button>
              </div>
            )}
          </form>
          <IssuerProfileSection canEdit={canEdit} />
        </Stack>
      )}
    </PageLayout>
  );
}
```

### 2-19 frontend/src/lib/query/batch3fPages.test.tsx（4 か所）

(1) Edit。変更前:

```
  useTranslation: () => ({ t: (key: string) => key }),
```

変更後:

```
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "ja" } }),
```

(2) Edit。変更前:

```
// 中身は画面の型（TenantProfilePage.tsx:27-39・TenantPolicyPage.tsx:25-34・DiscordConfigPage.tsx:27-42・
```

変更後:

```
// 中身は画面の型（TenantProfilePage.tsx の TenantProfile・issuerProfileForm.ts の IssuerProfiles・TenantPolicyPage.tsx:25-34・DiscordConfigPage.tsx:27-42・
```

(3) Edit。変更前:

```
const profile = {
  id: 1, company_name: "Fixture Company", company_name_en: null, address: null, phone: null, email: null,
  website: null, seal_image_url: null, default_language: "ja", created_at: "", updated_at: "",
};
```

変更後:

```
const profile = { id: 1, seal_image_url: null, default_language: "ja", created_at: "", updated_at: "" };
// 会社名は国内用の会社情報の行に移った（ADR-1061 便2-2c2b）
const issuerProfiles = {
  domestic: {
    region: "domestic", company_name: "Fixture Company", email: null, website: null, country_code: "JP",
    postal_code: "1000001", prefecture_code: "13", state_region: null, city: "Fixture City", address1: "1-1",
    address2: null, phone: null, is_invoice_registered: false, registration_number: null, updated_at: "",
  },
  overseas: null,
  legacy: null,
};
```

(4) Edit。変更前:

```
  "/admin/tenant-profile": profile,
```

変更後:

```
  "/admin/tenant-profile": profile,
  "/admin/issuer-profiles": issuerProfiles,
  "/prefectures": [],
  "/countries": [],
```

（cases の "tenant profile" の行は変えない。"Fixture Company" は国内用のタブの会社名の欄に出る。）

### 2-20 frontend/src/locales/ja.json（3 か所）

(1) Edit。変更前:

```
    "tenantProfile": "発行者情報",
```

変更後:

```
    "tenantProfile": "会社情報",
```

(2) Edit。変更前:

```
    "title": "発行者情報",
    "subtitle": "発注書 PDF / メールの差出人欄に表示される会社情報を設定します",
    "companyName": "会社名 (日本語)",
    "companyNameEn": "会社名 (英語)",
    "address": "住所",
    "phone": "電話番号",
    "email": "メールアドレス",
    "website": "ウェブサイト",
    "sealImageUrl": "印鑑画像 URL",
```

変更後:

```
    "title": "会社情報",
    "subtitle": "見積書と請求書の PDF に載せる会社情報と振込先を設定します",
    "sealImageUrl": "印鑑画像 URL",
```

(3) Edit。変更前:

```
    "saved": "発行者情報を保存しました",
```

変更後:

```
    "saved": "会社情報を保存しました",
```

(4) Edit。変更前（ja.json の `  "addressRule": {` の行）:

```
  "addressRule": {
```

変更後:

```
  "issuerProfile": {
    "sectionTitle": "書類に載せる会社情報",
    "tabDomestic": "国内用",
    "tabOverseas": "海外用",
    "companyName": "会社名",
    "email": "メールアドレス",
    "website": "ウェブサイト",
    "country": "国",
    "postalCode": "郵便番号",
    "postalHintJp": "7桁の数字で入れてください（ハイフンなし）",
    "postalHintForeign": "英数字・空白・ハイフンで10文字まで",
    "prefecture": "都道府県",
    "prefecturePlaceholder": "都道府県を選んでください",
    "stateRegion": "州・地域",
    "city": "市区町村",
    "address1": "番地・通り",
    "address2": "建物名・部屋番号",
    "phone": "電話番号",
    "phoneHintJp": "10桁か11桁の数字で入れてください（ハイフンなし）",
    "phoneHintForeign": "+ と国番号から入れてください（例: +14155550100）",
    "invoiceRegistered": "インボイス登録をしている",
    "registrationNumber": "登録番号",
    "registrationHint": "T と13桁の数字",
    "legacyTitle": "前の会社情報（読むだけ）",
    "legacyBody": "このタブの会社情報はまだ保存されていません。今の書類は前の会社情報で出ています。下の欄に入れ直して保存してください。",
    "legacyValues": "前の会社情報",
    "savedDomestic": "国内用の会社情報を保存しました",
    "savedOverseas": "海外用の会社情報を保存しました",
    "fixFields": "赤い欄を直してから、もう一度保存してください",
    "errors": {
      "required": "入れてください",
      "postalJp": "7桁の数字で入れてください",
      "postalForeign": "英数字・空白・ハイフンで10文字までにしてください",
      "phoneJp": "10桁か11桁の数字で入れてください",
      "phoneForeign": "+ と6〜15桁の数字で入れてください",
      "registrationNumber": "T と13桁の数字で入れてください",
      "unknownCode": "一覧から選んでください",
      "mustBeEmpty": "この国では空にしてください"
    }
  },
  "addressRule": {
```

### 2-21 frontend/src/locales/en.json（4 か所）

(1) Edit。変更前:

```
    "tenantProfile": "Issuer Profile",
```

変更後:

```
    "tenantProfile": "Company information",
```

(2) Edit。変更前:

```
    "title": "Issuer Profile",
    "subtitle": "Configure the issuer information displayed on PO PDF and email",
    "companyName": "Company name (Japanese)",
    "companyNameEn": "Company name (English)",
    "address": "Address",
    "phone": "Phone",
    "email": "Email",
    "website": "Website",
    "sealImageUrl": "Seal image URL",
```

変更後:

```
    "title": "Company information",
    "subtitle": "Configure the company information and payee accounts printed on quote and invoice PDFs",
    "sealImageUrl": "Seal image URL",
```

(3) Edit。変更前:

```
    "saved": "Issuer profile saved",
```

変更後:

```
    "saved": "Company information saved",
```

(4) Edit。変更前（en.json の `  "addressRule": {` の行）:

```
  "addressRule": {
```

変更後:

```
  "issuerProfile": {
    "sectionTitle": "Company information on documents",
    "tabDomestic": "Domestic",
    "tabOverseas": "Overseas",
    "companyName": "Company name",
    "email": "Email",
    "website": "Website",
    "country": "Country",
    "postalCode": "Postal code",
    "postalHintJp": "Enter 7 digits without a hyphen.",
    "postalHintForeign": "Up to 10 letters, digits, spaces or hyphens.",
    "prefecture": "Prefecture",
    "prefecturePlaceholder": "Select a prefecture",
    "stateRegion": "State / region",
    "city": "City",
    "address1": "Street address",
    "address2": "Building / suite",
    "phone": "Phone",
    "phoneHintJp": "Enter 10 or 11 digits without hyphens.",
    "phoneHintForeign": "Start with + and the country code (e.g. +14155550100).",
    "invoiceRegistered": "Registered for qualified invoices",
    "registrationNumber": "Registration number",
    "registrationHint": "T followed by 13 digits",
    "legacyTitle": "Previous company information (read only)",
    "legacyBody": "This tab has not been saved yet. Documents currently use the previous company information. Please enter it again below and save.",
    "legacyValues": "Previous company information",
    "savedDomestic": "Domestic company information saved",
    "savedOverseas": "Overseas company information saved",
    "fixFields": "Please fix the fields in red and save again.",
    "errors": {
      "required": "Please fill this in.",
      "postalJp": "Please enter 7 digits.",
      "postalForeign": "Please use up to 10 letters, digits, spaces or hyphens.",
      "phoneJp": "Please enter 10 or 11 digits.",
      "phoneForeign": "Please enter + followed by 6 to 15 digits.",
      "registrationNumber": "Please enter T followed by 13 digits.",
      "unknownCode": "Please choose from the list.",
      "mustBeEmpty": "Please leave this empty for this country."
    }
  },
  "addressRule": {
```

（ja.json・en.json の (2) の変更前は tenantProfile の中の行。同じ並びが他に無いことを Edit の一意性で確かめる。当たらなければ止める。）

### 2-22 frontend/api-contract/openapi.json

手順7の道具で作り直す。手で直さない。

## 3. 手順

1. 場所を作る。

```
cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2c2b && git log --oneline -1 | tail -1
cd ~/sa && git merge-base --is-ancestor 5a72c083f HEAD; echo "is-ancestor exit=$?"
```

期待: `is-ancestor exit=0`。

2. 点検する。

```
cd ~/sa && git rev-parse HEAD
cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2c2b.md
```

続けて §0-3 のコマンドを流し、表の期待と比べる。

3. §2 を当てる。新規ファイルは Write、それ以外は Edit。1か所ずつ。

4. Python の場所を作る。

```
cd ~/sa/backend && python3.12 -m venv ~/venv312 && ~/venv312/bin/pip install -q -r requirements.txt -r requirements-dev.txt && ~/venv312/bin/ruff --version
```

python3.12 が無いときだけ: `cd ~/sa/backend && uv venv --python 3.12 ~/venv312 && ~/venv312/bin/python -m ensurepip && ~/venv312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt`。

5. 書き方と会社の絞り込みの検査。

```
cd ~/sa/backend && ~/venv312/bin/ruff check app/ 2>&1 | tail -15
cd ~/sa && python3 scripts/lint_tenant_schema.py --mode strict backend/app/ 2>&1 | tail -15
cd ~/sa && python3 -c "import re,pathlib;r=pathlib.Path('backend/app');p=re.compile(r'\{[A-Za-z_]+\}\.tenant_profile\b|\"tenant_profile\"\s*\)|\bFROM\s+tenant_profile\b|\bINTO\s+tenant_profile\b|\bUPDATE\s+tenant_profile\b',re.I);[print(f.relative_to(r),i) for f in sorted(r.rglob('*.py')) for i,l in enumerate(f.read_text('utf-8').splitlines(),1) if p.search(l)]" | tail -15
```

期待: ruff は `All checks passed!`。A40 の出力は12行で、ファイルと件数が次と同じ（routers/tenant_profile.py 3・services/issuer.py 1・services/label_validation.py 1・services/po_renderer.py 2・services/tenant.py 5）。新しいファイルは0件。

6. 試験（backend）。

```
cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_issuer.py tests/test_issuer_profiles.py tests/test_tenant_profile.py tests/test_prefectures_seed.py 2>&1 | tail -15
```

期待: failed 0・error 0。

7. API の約束の写しを作り直す。

```
cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
cd ~/sa && git diff --stat frontend/api-contract/openapi.json | tail -3
cd ~/sa && grep -c '"/api/v1/admin/issuer-profiles' frontend/api-contract/openapi.json; grep -c '"/api/v1/prefectures"' frontend/api-contract/openapi.json
```

期待: 2つの grep が 1 以上。

8. 画面の検査。

```
cd ~/sa/frontend && node --version && npm --version
cd ~/sa/frontend && npm ci 2>&1 | tail -3
cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -3
cd ~/sa/frontend && npx tsc --noEmit -p . 2>&1 | tail -15
cd ~/sa/frontend && npm run test:unit -- src/pages/admin/issuerProfileForm.test.ts src/lib/query/batch3fPages.test.tsx 2>&1 | tail -15
cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
cd ~/sa/frontend && wc -l src/pages/admin/TenantProfilePage.tsx src/pages/admin/IssuerProfileSection.tsx src/pages/admin/InvoiceRegistrationField.tsx src/pages/admin/issuerProfileForm.ts
```

期待: tsc の出力なし。vitest は failed 0。check:all は終了コード 0。

9. 確かめる。

```
cd ~/sa && git status --short | tail -30
cd ~/sa && git diff --stat | tail -25
```

frontend/src/types/schema.d.ts が出ても git add しない。

10. 記録して送る（shingo-cc 名義）。

```
cd ~/sa && git add backend/app/services/issuer.py backend/app/services/issuer_rules.py backend/app/routers/issuer_profiles.py backend/app/routers/prefectures.py backend/app/routers/tenant_profile.py backend/app/schemas/issuer_profiles.py backend/app/schemas/prefectures.py backend/app/schemas/tenant_profile.py backend/app/main.py backend/app/realtime/topics.py backend/tests/conftest.py backend/tests/test_tenant_profile.py backend/tests/test_issuer_profiles.py frontend/src/pages/admin/TenantProfilePage.tsx frontend/src/pages/admin/IssuerProfileSection.tsx frontend/src/pages/admin/InvoiceRegistrationField.tsx frontend/src/pages/admin/issuerProfileForm.ts frontend/src/pages/admin/issuerProfileForm.test.ts frontend/src/lib/query/batch3fPages.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json frontend/api-contract/openapi.json
cd ~/sa && git -c user.name=shingo-cc -c user.email=shingo-cc@users.noreply.github.com commit -m "feat(admin): company information page with domestic and overseas tabs (ADR-1061 bin2-2c2b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd ~/sa && git push origin release/viewer-contract-bin2-2c2b 2>&1 | tail -3
cd ~/sa && git log --oneline -2 | tail -2
```

## 4. 想定される分かれ道

次のときは、そこで止めて BLOCKED と報告する（直さない・言い換えない）。

- 手順1の is-ancestor が 0 でない。
- §0-3 の数が1つでも違う。
- §2 の「変更前」の文字列が見つからない、または2か所以上に当たる。
- A40 の出力が §手順5 の期待と違う。
- pytest に failed か error がある。
- vitest に failed がある。
- tsc が何か出す。
- check:all が 0 以外で終わる（どの検査が何を言ったかを生のまま報告する）。
- ruff・lint_tenant_schema が何か出す。
- openapi の grep が 0。
- push が失敗する。

直してよいのは、このカードの写し間違い（字下げ・閉じかっこ・カンマの抜け）だけ。直したら、どこをどう直したかを報告に書く。試験の skipped は止めずに数を書く。

## 5. 報告の形

最後の返事に、受領確認の2行、手順ごとの tail の生出力、止まったときは「どの手順で・何が出たか・何をしなかったか」の3点を書く。最後の行は `DONE` か `BLOCKED: 理由` のどちらか。

## 6. 委任の定型

- sleep・ヒアドキュメントは使わない。PR は作らない。
- 見張り（hook）に止められたら、言い換えずに止められた文をそのまま報告する。
- §1 にないファイルは直さない。

END OF CARD
