# recon-2-2 raw（便2 の 2-2 が触る今のコード）

- 取得元: origin/main = 0f68e88c3676326bb3d4fd9be104d4ce18f83e78（git fetch origin の後）。行は origin/main の行番号。要約なし・そのまま写し。
- 設計: origin/main:docs/handoff/viewer-contract-stage/design.md の §3-4・§3-4a・§3-4b・§3-4d・§4 を読んだ。


## (a) tenant.py

### origin/main:backend/app/services/tenant.py :1140-1160
```
1140: -- Sprint 8 / migration 069: テナント発行者情報 (PO PDF / メール差出人)
1141: -- ADR-034: 新規テナント作成時に最初から保持される。
1142: -- 1 テナント 1 行運用、admin UI で内容編集。
1143: CREATE TABLE IF NOT EXISTS {schema}.tenant_profile (
1144:     id                  SERIAL PRIMARY KEY,
1145:     company_name        VARCHAR(255),
1146:     company_name_en     VARCHAR(255),
1147:     address             TEXT,
1148:     phone               VARCHAR(50),
1149:     email               VARCHAR(255),
1150:     website             VARCHAR(255),
1151:     seal_image_url      TEXT,
1152:     default_language    CHAR(2) NOT NULL DEFAULT 'ja',
1153:     created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
1154:     updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
1155:     CONSTRAINT tenant_profile_default_language_check
1156:         CHECK (default_language IN ('ja', 'en', 'ko', 'zh'))
1157: );
1158: -- 既定行を 1 行投入 (admin が UI で後から埋める)
1159: INSERT INTO {schema}.tenant_profile (default_language)
1160: SELECT 'ja' WHERE NOT EXISTS (SELECT 1 FROM {schema}.tenant_profile);
```

### origin/main:backend/app/services/tenant.py :861-895
```
861: -- 請求書ヘッダー
862: CREATE TABLE IF NOT EXISTS {schema}.invoices (
863:     id SERIAL PRIMARY KEY,
864:     tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
865:     invoice_number VARCHAR(30),
866:     quote_id INTEGER REFERENCES {schema}.quotes(id),
867:     -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
868:     company_id INTEGER CONSTRAINT fk_invoices_company REFERENCES {schema}.companies(id),
869:     contact_id INTEGER CONSTRAINT fk_invoices_contact REFERENCES {schema}.contacts(id),
870:     currency VARCHAR(10) DEFAULT 'JPY',
871:     subtotal NUMERIC(15, 2) DEFAULT 0,
872:     shipping_fee NUMERIC(15, 2) DEFAULT 0,
873:     tax_amount NUMERIC(15, 2) DEFAULT 0,
874:     total_amount NUMERIC(15, 2) DEFAULT 0,
875:     exchange_rate_jpy NUMERIC(12, 4),
876:     exchange_rate_usd NUMERIC(12, 4),
877:     amount_jpy NUMERIC(15, 2),
878:     amount_usd NUMERIC(15, 2),
879:     payment_method VARCHAR(50),
880:     status VARCHAR(20) DEFAULT 'draft',
881:     branch_number INTEGER DEFAULT 1,
882:     pdf_url VARCHAR(500),
883:     erp_key VARCHAR(100),
884:     issued_at TIMESTAMPTZ,
885:     due_date DATE,
886:     paid_at TIMESTAMPTZ,
887:     voided_at TIMESTAMPTZ,
888:     void_reason VARCHAR(500),
889:     notes TEXT,
890:     created_by INTEGER,
891:     created_at TIMESTAMPTZ DEFAULT NOW(),
892:     updated_at TIMESTAMPTZ DEFAULT NOW()
893: );
894: CREATE INDEX IF NOT EXISTS idx_invoices_company_id ON {schema}.invoices (company_id);
895: CREATE INDEX IF NOT EXISTS idx_invoices_contact_id ON {schema}.invoices (contact_id);
```

### origin/main:backend/app/services/tenant.py :1193-1211
```
1193: -- D-2: A在庫（自社保有在庫）— ADR SA-04/05（B在庫 public.inventory とは完全分離）
1194: CREATE TABLE IF NOT EXISTS {schema}.own_inventory (
1195:     id                SERIAL PRIMARY KEY,
1196:     tenant_id         INTEGER      NOT NULL,
1197:     product_id        INTEGER      NOT NULL REFERENCES public.products(id),
1198:     physical_qty      INTEGER      NOT NULL DEFAULT 0 CHECK (physical_qty >= 0),
1199:     reserved_qty      INTEGER      NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
1200:     available_qty     INTEGER GENERATED ALWAYS AS (physical_qty - reserved_qty) STORED,
1201:     unit_price        NUMERIC(15,2),
1202:     condition         VARCHAR(50),
1203:     status            VARCHAR(20)  NOT NULL DEFAULT 'active'
1204:                       CHECK (status IN ('active','inactive','sold_out')),
1205:     note_ja           TEXT,
1206:     note_en           TEXT,
1207:     antique_ledger_id INTEGER,
1208:     created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
1209:     updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
1210:     CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
1211: );
```

### origin/main:backend/app/services/tenant.py :1217-1218
```
1217: _RLS_ENABLE_SQL = """
1218: -- ADR-089 Sprint 5: customers は廃止済。RLS は companies 体系のみ。
```

### origin/main:backend/app/services/tenant.py :1234-1234
```
1234: ALTER TABLE {schema}.invoices ENABLE ROW LEVEL SECURITY;
```

### origin/main:backend/app/services/tenant.py :1258-1265
```
1258: -- ADR-015 §7: テナント別 AI 対応プレイブック
1259: ALTER TABLE {schema}.lead_playbook ENABLE ROW LEVEL SECURITY;
1260: -- D-2: A在庫（ADR SA-04/05）
1261: ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
1262: -- Phase 1-B-2 Step 5d / PR γ: _customer_migration_map は migration 036 で DROP 済。
1263: -- D-2: A在庫（ADR SA-04/05）
1264: ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
1265: """
```

### origin/main:backend/app/services/tenant.py :1267-1270
```
1267: # テナント分離ポリシー（DO $$ ... END $$ ブロックは1ステートメントとして実行する。
1268: # 内部の;でsplitすると$$ドル引用が分断されPostgresSyntaxErrorになるため）
1269: _RLS_POLICY_SQL = """
1270: DO $$
```

### origin/main:backend/app/services/tenant.py :1328-1332
```
1328:     -- D-2: A在庫（ADR SA-04/05）— ポリシー名は既存テナント（migration 20260604_140000）と統一
1329:     IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'own_inventory_tenant_isolation' AND schemaname = '{schema_raw}') THEN
1330:         CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
1331:             USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
1332:     END IF;
```

### origin/main:backend/app/services/tenant.py :1344-1348
```
1344:     END IF;
1345:     IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_invoices' AND schemaname = '{schema_raw}') THEN
1346:         CREATE POLICY tenant_isolation_invoices ON {schema}.invoices
1347:             USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
1348:     END IF;
```

### origin/main:backend/app/services/tenant.py :1486-1492
```
1486:     -- D-2: A在庫（ADR SA-04/05）— ポリシー名は既存テナント（migration 20260604_140000）と統一
1487:     IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'own_inventory_tenant_isolation' AND schemaname = '{schema_raw}') THEN
1488:         CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
1489:             USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
1490:     END IF;
1491: END $$
1492: """
```

## (b) schemas/tenant_profile.py

### origin/main:backend/app/schemas/tenant_profile.py :1-49
```
1: """TenantProfile Pydantic schemas (Sprint 8 / F8)
2: 
3: PO PDF / メール送信時の差出人情報 (各テナント名義) を管理する。
4: """
5: from __future__ import annotations
6: 
7: from datetime import datetime
8: 
9: from pydantic import BaseModel, Field, field_validator
10: 
11: _VALID_LANGUAGES = {"ja", "en", "ko", "zh"}
12: 
13: 
14: class TenantProfileResponse(BaseModel):
15:     id: int
16:     company_name: str | None = None
17:     company_name_en: str | None = None
18:     address: str | None = None
19:     phone: str | None = None
20:     email: str | None = None
21:     website: str | None = None
22:     seal_image_url: str | None = None
23:     default_language: str = "ja"
24:     created_at: datetime
25:     updated_at: datetime
26: 
27:     model_config = {"from_attributes": True}
28: 
29: 
30: class TenantProfileUpdate(BaseModel):
31:     company_name: str | None = Field(default=None, max_length=255)
32:     company_name_en: str | None = Field(default=None, max_length=255)
33:     address: str | None = Field(default=None, max_length=5000)
34:     phone: str | None = Field(default=None, max_length=50)
35:     email: str | None = Field(default=None, max_length=255)
36:     website: str | None = Field(default=None, max_length=255)
37:     seal_image_url: str | None = Field(default=None, max_length=5000)
38:     default_language: str | None = Field(default=None, min_length=2, max_length=2)
39: 
40:     @field_validator("default_language")
41:     @classmethod
42:     def _validate_language(cls, v: str | None) -> str | None:
43:         if v is None:
44:             return v
45:         if v not in _VALID_LANGUAGES:
46:             raise ValueError(
47:                 f"default_language must be one of {sorted(_VALID_LANGUAGES)}"
48:             )
49:         return v
```

## (c) routers/tenant_profile.py

### origin/main:backend/app/routers/tenant_profile.py :1-154
```
1: """TenantProfile router (Sprint 8 / F8)
2: 
3: 各テナント admin が PO PDF / メールの差出人情報 (会社名・住所・印鑑 URL 等) を
4: CRUD するエンドポイント。
5: 
6: 設計:
7:   - 1 テナント 1 行運用 (migration 069 で既定行を 1 行 seed)
8:   - `GET /api/v1/admin/tenant-profile` → 取得 (見るだけなら view 権限)
9:   - `PUT /api/v1/admin/tenant-profile` → 全フィールド更新 (edit 権限)
10:   - require_permission("tenant.profile.view" / "tenant.profile.edit")
11:     permissions は migration 069 で seed 済
12: 
13: raw SQL は dialect-aware な schema prefix を付ける (search_path に依存しない)。
14:   - 背景: Issue #563 で PUT 側の commit 直後再 SELECT が
15:     "relation \"tenant_profile\" does not exist" で失敗する事象が観測された。
16:     SQLAlchemy AsyncSession の commit 後は新コネクションが払い出されて
17:     session-level の search_path が失われる可能性があるため、
18:     raw text() を使う router は schema prefix を明示するのが安全。
19:   - PostgreSQL では `tenant_{id:03d}.tenant_profile`、
20:     SQLite (pytest) では schema 概念がないので prefix なしに倒す
21:     (`_dialect_supports_search_path` と同じ dialect 判定で分岐)。
22: 
23: 関連:
24:   .claude-pipeline/spec.md F8 / AC8.7
25:   migrations/069_create_tenant_profile.sql
26:   backend/app/services/po_renderer.py
27: """
28: from __future__ import annotations
29: 
30: from fastapi import APIRouter, Depends, HTTPException, status
31: from sqlalchemy import text
32: from sqlalchemy.ext.asyncio import AsyncSession
33: 
34: from app.auth.dependencies import (
35:     get_current_tenant,
36:     get_current_user,
37:     require_permission,
38:     reset_tenant_context,
39:     tenant_table_ref,
40: )
41: from app.database import get_db
42: from app.models import User
43: from app.schemas.tenant_profile import TenantProfileResponse, TenantProfileUpdate
44: from app.services.audit import record_audit_log
45: 
46: router = APIRouter()
47: 
48: # ADR-072 Phase 1: ローカル helper を削除し、`app.auth.dependencies.tenant_table_ref`
49: # を import して使う。旧 `_tenant_profile_table(db, tenant_id)` 呼び出しは
50: # `tenant_table_ref(db, tenant_id, "tenant_profile")` に置換済。
51: 
52: 
53: @router.get(
54:     "/admin/tenant-profile",
55:     response_model=TenantProfileResponse,
56:     dependencies=[Depends(require_permission("tenant.profile.view"))],
57: )
58: async def get_tenant_profile(
59:     db: AsyncSession = Depends(get_db),
60:     tenant_id: int = Depends(get_current_tenant),
61:     current_user: User = Depends(get_current_user),  # noqa: ARG001
62: ):
63:     """テナント発行者情報を取得 (1 行)。
64: 
65:     migration 069 で既定の空行を seed しているため通常 404 にはならない。
66:     """
67:     table = tenant_table_ref(db, tenant_id, "tenant_profile")
68:     row = (await db.execute(
69:         text(f"""
70:             SELECT id, company_name, company_name_en, address, phone, email,
71:                    website, seal_image_url, default_language,
72:                    created_at, updated_at
73:             FROM {table}
74:             ORDER BY id LIMIT 1
75:         """),
76:     )).mappings().first()
77: 
78:     if not row:
79:         raise HTTPException(
80:             status_code=status.HTTP_404_NOT_FOUND,
81:             detail="tenant_profile が初期化されていません",
82:         )
83:     return TenantProfileResponse(**dict(row))
84: 
85: 
86: @router.put(
87:     "/admin/tenant-profile",
88:     response_model=TenantProfileResponse,
89:     dependencies=[Depends(require_permission("tenant.profile.edit"))],
90: )
91: async def update_tenant_profile(
92:     data: TenantProfileUpdate,
93:     db: AsyncSession = Depends(get_db),
94:     tenant_id: int = Depends(get_current_tenant),
95:     current_user: User = Depends(get_current_user),
96: ):
97:     """テナント発行者情報を更新 (PATCH 相当だが PUT で全フィールド指定可)。"""
98:     table = tenant_table_ref(db, tenant_id, "tenant_profile")
99: 
100:     # 既存行を確認
101:     existing = (await db.execute(
102:         text(f"SELECT id FROM {table} ORDER BY id LIMIT 1"),
103:     )).mappings().first()
104:     if not existing:
105:         raise HTTPException(
106:             status_code=status.HTTP_404_NOT_FOUND,
107:             detail="tenant_profile が初期化されていません (migration 069 適用要)",
108:         )
109: 
110:     # 更新フィールドを動的に組み立て
111:     payload = data.model_dump(exclude_unset=True)
112:     if not payload:
113:         # 何も指定なし → 現状返却
114:         row = (await db.execute(
115:             text(f"""
116:                 SELECT id, company_name, company_name_en, address, phone, email,
117:                        website, seal_image_url, default_language,
118:                        created_at, updated_at
119:                 FROM {table} WHERE id = :id
120:             """),
121:             {"id": existing["id"]},
122:         )).mappings().first()
123:         return TenantProfileResponse(**dict(row))
124: 
125:     set_clauses = []
126:     params: dict = {"id": existing["id"]}
127:     for k, v in payload.items():
128:         set_clauses.append(f"{k} = :{k}")
129:         params[k] = v
130:     set_sql = ", ".join(set_clauses)
131: 
132:     await db.execute(
133:         text(f"UPDATE {table} SET {set_sql} WHERE id = :id"),
134:         params,
135:     )
136: 
137:     await record_audit_log(
138:         db=db, tenant_id=tenant_id, user_id=current_user.id,
139:         action="update", table_name="tenant_profile",
140:         record_id=existing["id"], new_data=payload,
141:     )
142:     await db.commit()
143:     await reset_tenant_context(db, tenant_id)
144: 
145:     row = (await db.execute(
146:         text(f"""
147:             SELECT id, company_name, company_name_en, address, phone, email,
148:                    website, seal_image_url, default_language,
149:                    created_at, updated_at
150:             FROM {table} WHERE id = :id
151:         """),
152:         {"id": existing["id"]},
153:     )).mappings().first()
154:     return TenantProfileResponse(**dict(row))
```

## (d) routers/invoices.py

### origin/main:backend/app/routers/invoices.py :60-130
```
60: 
61: async def _get_tenant_schema(tenant_id: int) -> str:
62:     """tenant_id からスキーマ名 (tenant_NNN) を生成する。"""
63:     return f"tenant_{tenant_id:03d}"
64: 
65: 
66: async def _fetch_address_snapshot(
67:     db: AsyncSession,
68:     company_id: int | None,
69:     address_type: str,
70: ) -> dict | None:
71:     """
72:     company_addresses から指定タイプ (delivery / billing) のデフォルト住所を取得し
73:     JSONB スナップショット形式で返す。company_id が None の場合は None を返す。
74:     """
75:     if company_id is None:
76:         return None
77:     result = await db.execute(
78:         text("""
79:             SELECT a.branch_name, a.zip, a.address_line_1, a.address_line_2,
80:                    a.city, a.state, a.country_code, a.telephone,
81:                    c.name AS company_name, c.billing_display_name
82:             FROM company_addresses a
83:             JOIN companies c ON c.id = a.company_id
84:             WHERE a.company_id = :cid
85:               AND a.address_type = :atype
86:               AND a.is_default = TRUE
87:             LIMIT 1
88:         """),
89:         {"cid": company_id, "atype": address_type},
90:     )
91:     row = result.mappings().first()
92:     if not row:
93:         return None
94:     return {
95:         "company_name": row["company_name"],
96:         "billing_display_name": row["billing_display_name"],
97:         "label": row["branch_name"],
98:         "postal_code": row["zip"],
99:         "address": " ".join(
100:             filter(None, [row["address_line_1"], row["address_line_2"]])
101:         ),
102:         "city": row["city"],
103:         "state": row["state"],
104:         "country": row["country_code"],
105:         "phone": row["telephone"],
106:     }
107: 
108: 
109: async def _fetch_tenant_profile(db: AsyncSession, tenant_schema: str) -> dict:
110:     """tenant_profile からテナント情報を取得する。"""
111:     result = await db.execute(
112:         text(f"""
113:             SELECT company_name, company_name_en, address, phone, email, website
114:             FROM {tenant_schema}.tenant_profile
115:             ORDER BY id LIMIT 1
116:         """),
117:     )
118:     row = result.mappings().first()
119:     if not row:
120:         return {}
121:     return {
122:         "name": row["company_name"] or row["company_name_en"] or "",
123:         "address": row["address"] or "",
124:         "phone": row["phone"] or "",
125:         "email": row["email"] or "",
126:         "website": row["website"] or "",
127:     }
128: 
129: 
130: _INVOICE_COLUMNS = """
```

### origin/main:backend/app/routers/invoices.py :230-380
```
230:         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
231:     items = await _get_invoice_items(db, invoice_id)
232:     return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])
233: 
234: 
235: @router.post(
236:     "/invoices/from-quote/{quote_id}",
237:     response_model=InvoiceDetailResponse,
238:     status_code=201,
239:     dependencies=[Depends(require_permission("invoices.create"))],
240: )
241: async def create_invoice_from_quote(
242:     quote_id: int,
243:     db: AsyncSession = Depends(get_db),
244:     tenant_id: int = Depends(get_current_tenant),
245:     current_user: User = Depends(get_current_user),
246: ):
247:     """承認済み見積もりから請求書を作成する（atomic変換）"""
248:     # アトミック性: 見積もりステータスをSELECT FOR UPDATEで排他ロックし、
249:     # 並行変換を防止。全操作が同一トランザクション内で完結する。
250:     quote = await db.execute(
251:         text("SELECT * FROM quotes WHERE id = :id FOR UPDATE"),
252:         {"id": quote_id},
253:     )
254:     q = quote.mappings().first()
255:     if not q:
256:         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:quote")
257:     if q["status"] != "approved":
258:         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="承認済みの見積もりのみ請求書に変換できます")
259: 
260:     # 請求番号生成
261:     max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
262:     next_id = max_result.scalar()
263:     invoice_number = f"IN-{next_id:04d}-01"
264:     erp_key = str(uuid.uuid4())[:8].upper()
265: 
266:     # スナップショット取得
267:     company_id = q.get("company_id")
268:     ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
269:     bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")
270: 
271:     # 為替レート取得（JPY 以外の場合）
272:     currency = q["currency"]
273:     fx_snap = get_fx_rate(currency) if currency and currency.upper() != "JPY" else None
274: 
275:     # 請求書ヘッダー作成（Step 5d: quote から company_id/contact_id を継承）
276:     inv_result = await db.execute(
277:         text("""
278:             INSERT INTO invoices (
279:                 tenant_id, invoice_number, quote_id, company_id, contact_id, currency,
280:                 subtotal, shipping_fee, tax_amount, total_amount,
281:                 payment_method, status, branch_number, erp_key, notes, created_by,
282:                 ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot
283:             ) VALUES (
284:                 :tid, :inv_num, :qid, :company_id, :contact_id, :currency,
285:                 :subtotal, :shipping, :tax, :total,
286:                 NULL, 'draft', 1, :erp_key, :notes, :created_by,
287:                 :ship_to, :bill_to, :fx_rate
288:             ) RETURNING id
289:         """),
290:         {
291:             "tid": tenant_id, "inv_num": invoice_number, "qid": quote_id,
292:             "company_id": company_id, "contact_id": q.get("contact_id"),
293:             "currency": currency,
294:             "subtotal": q["subtotal"], "shipping": q["shipping_fee"],
295:             "tax": q["tax_amount"], "total": q["total_amount"],
296:             "erp_key": erp_key, "notes": q["notes"], "created_by": current_user.id,
297:             "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
298:             "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
299:             "fx_rate": json.dumps(fx_snap) if fx_snap else None,
300:         },
301:     )
302:     invoice_id = inv_result.scalar_one()
303: 
304:     # 見積明細をコピー（hs_code を含む）
305:     quote_items = await db.execute(
306:         text("SELECT product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order, hs_code FROM quote_items WHERE quote_id = :qid ORDER BY sort_order"),
307:         {"qid": quote_id},
308:     )
309:     for item in quote_items.mappings().all():
310:         await db.execute(
311:             text("""
312:                 INSERT INTO invoice_items (invoice_id, product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order, hs_code)
313:                 VALUES (:iid, :product_id, :product_name, :name_en, :condition, :unit, :quantity, :unit_price, :weight, :subtotal, :sort_order, :hs_code)
314:             """),
315:             {"iid": invoice_id, **dict(item)},
316:         )
317: 
318:     await record_audit_log(
319:         db=db, tenant_id=tenant_id, user_id=current_user.id,
320:         action="create_from_quote", table_name="invoices", record_id=invoice_id,
321:         new_data={"quote_id": quote_id, "invoice_number": invoice_number},
322:     )
323:     await db.commit()
324:     await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
325:     await invalidate_dashboard_cache(tenant_id)
326: 
327:     fetched = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
328:     row = fetched.mappings().first()
329:     items = await _get_invoice_items(db, invoice_id)
330:     return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])
331: 
332: 
333: @router.post(
334:     "/invoices",
335:     response_model=InvoiceDetailResponse,
336:     status_code=201,
337:     dependencies=[Depends(require_permission("invoices.create"))],
338: )
339: async def create_invoice(
340:     data: InvoiceCreate,
341:     db: AsyncSession = Depends(get_db),
342:     tenant_id: int = Depends(get_current_tenant),
343:     current_user: User = Depends(get_current_user),
344: ):
345:     """請求書を直接作成する（見積もりを経由しない場合）"""
346:     # Step 5d: contact / company の存在 + 所属一致確認のみ
347:     contact_check = await db.execute(
348:         text("SELECT company_id FROM contacts WHERE id = :id"),
349:         {"id": data.contact_id},
350:     )
351:     contact_row = contact_check.first()
352:     if not contact_row:
353:         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:contact")
354:     if contact_row[0] != data.company_id:
355:         raise HTTPException(
356:             status_code=status.HTTP_400_BAD_REQUEST,
357:             detail="指定された担当者は指定会社に所属していません",
358:         )
359: 
360:     subtotal = sum(item.quantity * item.unit_price for item in data.items)
361:     shipping = data.shipping_fee or Decimal(0)
362:     tax = data.tax_amount or Decimal(0)
363:     total = subtotal + shipping + tax
364:     amount_jpy, amount_usd = _calc_currency_amounts(total, data.currency, data.exchange_rate_jpy, data.exchange_rate_usd)
365: 
366:     # スナップショット取得
367:     ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
368:     bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")
369: 
370:     # 為替レート取得（JPY 以外の場合）
371:     fx_snap = get_fx_rate(data.currency) if data.currency and data.currency.upper() != "JPY" else None
372: 
373:     max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
374:     next_id = max_result.scalar()
375:     invoice_number = f"IN-{next_id:04d}-01"
376:     erp_key = str(uuid.uuid4())[:8].upper()
377: 
378:     inv_result = await db.execute(
379:         text("""
380:             INSERT INTO invoices (
```

### origin/main:backend/app/routers/invoices.py :820-880
```
820:         text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"),
821:         {"id": invoice_id},
822:     )
823:     row = result.mappings().first()
824:     if not row:
825:         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
826: 
827:     items = await _get_invoice_items(db, invoice_id)
828:     tenant_schema = await _get_tenant_schema(tenant_id)
829:     tenant_profile = await _fetch_tenant_profile(db, tenant_schema)
830: 
831:     invoice_data = {
832:         "invoice_code": row["invoice_number"] or f"IN-{invoice_id:04d}-01",
833:         "issued_at": row["issued_at"].isoformat() if row["issued_at"] else None,
834:         "ship_to_snapshot": row["ship_to_snapshot"],
835:         "bill_to_snapshot": row["bill_to_snapshot"],
836:         "items": [
837:             {
838:                 "name_en": it.get("name_en") or it.get("product_name") or "-",
839:                 "quantity": it["quantity"],
840:                 "unit_price": float(it["unit_price"] or 0),
841:                 "subtotal": float(it["subtotal"] or 0),
842:                 "hs_code": it.get("hs_code"),
843:             }
844:             for it in items
845:         ],
846:         "subtotal": float(row["subtotal"] or 0),
847:         "shipping_fee": float(row["shipping_fee"] or 0),
848:         "tax_amount": float(row["tax_amount"] or 0),
849:         "total_amount": float(row["total_amount"] or 0),
850:         "currency": row["currency"],
851:         "duty_amount": float(row["duty_amount"]) if row["duty_amount"] is not None else None,
852:         "fx_rate_snapshot": row["fx_rate_snapshot"],
853:         "notes": row["notes"],
854:     }
855: 
856:     pdf_bytes = await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile)
857:     filename = f"{invoice_data['invoice_code']}.pdf"
858: 
859:     return Response(
860:         content=pdf_bytes,
861:         media_type="application/pdf",
862:         headers={"Content-Disposition": f'attachment; filename="{filename}"'},
863:     )
864: 
865: 
866: # ──────────────────────────────────────────────────────────────────────
867: # ADR-101改訂(2) Inc1: PayPal 請求書の写しPDF（自動保存・取得）
868: # ──────────────────────────────────────────────────────────────────────
869: 
870: async def _render_paypal_copy_pdf(db: AsyncSession, tenant_id: int, row, invoice_id: int,
871:                                   pp_invoice_number: str, original_url: str | None) -> bytes:
872:     """請求書データ＋テナント情報から写しPDF（PayPal 請求書の写し注記＋原本リンク＋QR）を生成。"""
873:     items = await _get_invoice_items(db, invoice_id)
874:     tenant_schema = await _get_tenant_schema(tenant_id)
875:     tenant_profile = await _fetch_tenant_profile(db, tenant_schema)
876:     invoice_data = {
877:         "invoice_code": row["invoice_number"] or f"IN-{invoice_id:04d}-01",
878:         "issued_at": row["issued_at"].isoformat() if row["issued_at"] else None,
879:         "ship_to_snapshot": row["ship_to_snapshot"],
880:         "bill_to_snapshot": row["bill_to_snapshot"],
```

### origin/main:backend/app/routers/invoices.py :970-1010
```
970:     dependencies=[Depends(require_permission("invoices.view"))],
971: )
972: async def download_quote_pdf(
973:     quote_id: int,
974:     db: AsyncSession = Depends(get_db),
975:     tenant_id: int = Depends(get_current_tenant),
976:     current_user: User = Depends(get_current_user),  # noqa: ARG001
977: ):
978:     """見積書 PDF を生成して返す（C-8）。"""
979:     result = await db.execute(
980:         text("""
981:             SELECT id, quote_code, company_id, currency,
982:                    subtotal, shipping_fee, tax_amount, total_amount,
983:                    notes, created_at
984:             FROM quotes WHERE id = :id
985:         """),
986:         {"id": quote_id},
987:     )
988:     row = result.mappings().first()
989:     if not row:
990:         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")
991: 
992:     items_result = await db.execute(
993:         text("""
994:             SELECT product_id, product_name, name_en, condition, unit,
995:                    quantity, unit_price, weight, subtotal, sort_order, hs_code
996:             FROM quote_items WHERE quote_id = :qid ORDER BY sort_order, id
997:         """),
998:         {"qid": quote_id},
999:     )
1000:     items = [dict(r) for r in items_result.mappings().all()]
1001: 
1002:     company_id = row["company_id"]
1003:     ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
1004:     bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")
1005: 
1006:     tenant_schema = await _get_tenant_schema(tenant_id)
1007:     tenant_profile = await _fetch_tenant_profile(db, tenant_schema)
1008: 
1009:     quote_data = {
1010:         "quote_code": row["quote_code"] or f"QT-{quote_id:04d}",
```

## (e) services/invoice_renderer.py

### origin/main:backend/app/services/invoice_renderer.py :140-160
```
140:     subtotal: float
141:     shipping_fee: float
142:     tax_amount: float
143:     total: float
144:     currency: str
145:     duty_amount: Optional[float] = None
146:     fx_rate: Optional[FxRateSnapshot] = None
147:     notes: Optional[str] = None
148:     tenant_name: Optional[str] = None
149:     tenant_address: Optional[str] = None
150:     tenant_phone: Optional[str] = None
151:     tenant_email: Optional[str] = None
152:     tenant_website: Optional[str] = None
153:     # ADR-101改訂(2): PayPal 請求書の写し注記（{"pp_invoice_number", "original_url"}）。
154:     # 指定時はフッターに「写し」帯＋原本リンク＋QR を描画する。
155:     paypal_copy: Optional[dict] = None
156: 
157: 
158: # ─────────────────────────────────────────────────────────────────────
159: # ヘルパー
160: # ─────────────────────────────────────────────────────────────────────
```

### origin/main:backend/app/services/invoice_renderer.py :250-270
```
250:         y -= 4 * mm
251:     contact_parts: list[str] = []
252:     if data.tenant_phone:
253:         contact_parts.append(f"TEL: {data.tenant_phone}")
254:     if data.tenant_email:
255:         contact_parts.append(f"Email: {data.tenant_email}")
256:     if contact_parts:
257:         c.setFont(font, 8)
258:         c.drawString(20 * mm, y, "  ".join(contact_parts))
259:         y -= 4 * mm
260:     if data.tenant_website:
261:         c.setFont(font, 8)
262:         c.drawString(20 * mm, y, f"Web: {data.tenant_website}")
263:         y -= 4 * mm
264: 
265:     # ── 2. タイトル + 番号 + 発行日 ────────────────────────────────────
266:     y -= 6 * mm
267:     doc_label = "INVOICE" if data.doc_type == "invoice" else "QUOTATION"
268:     c.setFont(font, 18)
269:     c.drawCentredString(width / 2, y, doc_label)
270:     y -= 8 * mm
```

### origin/main:backend/app/services/invoice_renderer.py :500-590
```
500:         ],
501:         subtotal=float(invoice_data.get("subtotal") or 0),
502:         shipping_fee=float(invoice_data.get("shipping_fee") or 0),
503:         tax_amount=float(invoice_data.get("tax_amount") or 0),
504:         total=float(invoice_data.get("total") or invoice_data.get("total_amount") or 0),
505:         currency=invoice_data.get("currency", "JPY"),
506:         duty_amount=invoice_data.get("duty_amount"),
507:         fx_rate=_to_fx(invoice_data.get("fx_rate_snapshot")),
508:         notes=invoice_data.get("notes"),
509:         tenant_name=tenant_profile.get("name"),
510:         tenant_address=tenant_profile.get("address"),
511:         tenant_phone=tenant_profile.get("phone"),
512:         tenant_email=tenant_profile.get("email"),
513:         tenant_website=tenant_profile.get("website"),
514:         paypal_copy=paypal_copy,
515:     )
516: 
517:     return _render_doc_pdf(data)
518: 
519: 
520: def render_quote_pdf(quote_data: dict, tenant_profile: dict) -> bytes:
521:     """
522:     見積書 PDF を生成して bytes で返す。
523: 
524:     quote_data キー:
525:         quote_code: str
526:         issued_at: str | None
527:         ship_to_snapshot: dict | None
528:         bill_to_snapshot: dict | None
529:         items: list[{"name_en": str, "qty": int, "unit_price": float,
530:                       "hs_code": str | None, "subtotal": float}]
531:         subtotal: float
532:         shipping_fee: float
533:         tax_amount: float
534:         total: float
535:         currency: str
536:         notes: str | None
537: 
538:     tenant_profile キー:
539:         name: str, address: str, phone: str, email: str, website: str
540:     """
541: 
542:     def _to_addr(snap: dict | None) -> Optional[AddressSnapshot]:
543:         if not snap:
544:             return None
545:         return AddressSnapshot(
546:             company_name=snap.get("billing_display_name") or snap.get("company_name"),
547:             contact_name=snap.get("contact_name"),
548:             address=snap.get("address"),
549:             country=snap.get("country"),
550:             tax_id=snap.get("tax_id"),
551:             phone=snap.get("phone"),
552:             email=snap.get("email"),
553:         )
554: 
555:     data = InvoiceRenderData(
556:         doc_type="quote",
557:         doc_code=quote_data.get("quote_code", "-"),
558:         issued_at=quote_data.get("issued_at") or quote_data.get("created_at"),
559:         ship_to=_to_addr(quote_data.get("ship_to_snapshot")),
560:         bill_to=_to_addr(quote_data.get("bill_to_snapshot")),
561:         items=[
562:             InvoiceItemForRender(
563:                 name_en=item.get("name_en") or item.get("product_name") or "-",
564:                 qty=int(item.get("qty") or item.get("quantity") or 0),
565:                 unit_price=float(item.get("unit_price") or 0),
566:                 subtotal=float(item.get("subtotal") or 0),
567:                 hs_code=item.get("hs_code"),
568:             )
569:             for item in quote_data.get("items", [])
570:         ],
571:         subtotal=float(quote_data.get("subtotal") or 0),
572:         shipping_fee=float(quote_data.get("shipping_fee") or 0),
573:         tax_amount=float(quote_data.get("tax_amount") or 0),
574:         total=float(quote_data.get("total") or quote_data.get("total_amount") or 0),
575:         currency=quote_data.get("currency", "JPY"),
576:         duty_amount=None,  # 見積書では Duty 行は表示しない
577:         fx_rate=None,
578:         notes=quote_data.get("notes"),
579:         tenant_name=tenant_profile.get("name"),
580:         tenant_address=tenant_profile.get("address"),
581:         tenant_phone=tenant_profile.get("phone"),
582:         tenant_email=tenant_profile.get("email"),
583:         tenant_website=tenant_profile.get("website"),
584:     )
585: 
586:     return _render_doc_pdf(data)
```

## (f) 会社情報の画面とメニュー

### origin/main:frontend/src/pages/admin/TenantProfilePage.tsx :1-263
```
1: /**
2:  * TenantProfilePage (Sprint 8 / F8)
3:  *
4:  * 各テナント admin が PO PDF / メールの差出人情報 (会社名・住所・印鑑 URL 等) を
5:  * 編集する画面。
6:  *
7:  * 権限:
8:  *   tenant.profile.view → 閲覧
9:  *   tenant.profile.edit → 保存
10:  *
11:  * 関連:
12:  *   .claude-pipeline/spec.md F8 / AC8.7
13:  *   backend/app/routers/tenant_profile.py
14:  *   migrations/069_create_tenant_profile.sql
15:  */
16: import { useState } from "react";
17: import { useTranslation } from "react-i18next";
18: import { api } from "../../lib/api";
19: import { useApiCache, useApiQuery } from "../../lib/query/apiQuery";
20: import { useSeededForm } from "../../lib/query/useSeededForm";
21: import { usePermissions } from "../../hooks/usePermissions";
22: import { PageLayout } from "../../components/PageLayout";
23: import { Button } from "../../components/Button";
24: import { SelectControl } from "../../components/Select";
25: import { TextareaControl } from "../../components/Textarea";
26: import { TextFieldControl } from "../../components/TextField";
27: import { LoadingBlock } from "../../components/loading";
28: 
29: interface TenantProfile {
30:   id: number;
31:   company_name: string | null;
32:   company_name_en: string | null;
33:   address: string | null;
34:   phone: string | null;
35:   email: string | null;
36:   website: string | null;
37:   seal_image_url: string | null;
38:   default_language: string;
39:   created_at: string;
40:   updated_at: string;
41: }
42: 
43: interface FormState {
44:   company_name: string;
45:   company_name_en: string;
46:   address: string;
47:   phone: string;
48:   email: string;
49:   website: string;
50:   seal_image_url: string;
51:   default_language: string;
52: }
53: 
54: const emptyForm: FormState = {
55:   company_name: "",
56:   company_name_en: "",
57:   address: "",
58:   phone: "",
59:   email: "",
60:   website: "",
61:   seal_image_url: "",
62:   default_language: "ja",
63: };
64: 
65: const PROFILE_PATH = "/admin/tenant-profile";
66: const toForm = (data: TenantProfile): FormState => ({
67:   company_name: data.company_name ?? "",
68:   company_name_en: data.company_name_en ?? "",
69:   address: data.address ?? "",
70:   phone: data.phone ?? "",
71:   email: data.email ?? "",
72:   website: data.website ?? "",
73:   seal_image_url: data.seal_image_url ?? "",
74:   default_language: data.default_language ?? "ja",
75: });
76: 
77: export default function TenantProfilePage() {
78:   const { t } = useTranslation();
79:   const { hasPermission } = usePermissions();
80:   const [saving, setSaving] = useState(false);
81:   const [error, setError] = useState("");
82:   const [info, setInfo] = useState("");
83: 
84:   const canView = hasPermission("tenant.profile.view");
85:   const canEdit = hasPermission("tenant.profile.edit");
86:   const profileQ = useApiQuery<TenantProfile>(PROFILE_PATH, { enabled: canView });
87:   const { form, setForm, ready } = useSeededForm(PROFILE_PATH, profileQ.data, toForm, emptyForm);
88:   const cache = useApiCache();
89:   const readError = profileQ.error ? (profileQ.error instanceof Error ? profileQ.error.message : t("common.fetchError")) : "";
90:   const shownError = error || readError;
91: 
92:   const handleChange = (key: keyof FormState) => (
93:     e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
94:   ) => {
95:     setForm((prev) => ({ ...prev, [key]: e.target.value }));
96:   };
97: 
98:   const handleSave = async (e: React.FormEvent) => {
99:     e.preventDefault();
100:     setError("");
101:     setInfo("");
102:     setSaving(true);
103:     try {
104:       // 空文字は null に変換 (バックエンド側で null と空文字を等価扱い)
105:       const payload: Record<string, string | null> = {};
106:       (Object.keys(form) as Array<keyof FormState>).forEach((k) => {
107:         const v = form[k];
108:         payload[k] = v === "" ? null : v;
109:       });
110:       const saved = await api.put<TenantProfile>("/admin/tenant-profile", payload);
111:       cache.write(PROFILE_PATH, saved);
112:       setInfo(t("tenantProfile.saved"));
113:     } catch (err) {
114:       setError(err instanceof Error ? err.message : t("common.operationError"));
115:     } finally {
116:       setSaving(false);
117:     }
118:   };
119: 
120:   if (!canView) {
121:     return (
122:       <PageLayout navKey="nav.tenantProfile">
123:         <div className="error-message">{t("tenantProfile.permissionRequired")}</div>
124:       </PageLayout>
125:     );
126:   }
127: 
128:   return (
129:     <PageLayout navKey="nav.tenantProfile" subtitleKey="tenantProfile.subtitle">
130:       {profileQ.isPending ? (
131:         <LoadingBlock />
132:       ) : !ready ? (
133:         <div className="error-message">{shownError}</div>
134:       ) : (
135:         <form className="form" onSubmit={handleSave} data-testid="tenant-profile-form">
136:           {shownError && <div className="error-message">{shownError}</div>}
137:           {info && <div className="info-message" data-testid="tenant-profile-info">{info}</div>}
138: 
139:           <div className="form-group">
140:             <label htmlFor="tp-company-name">{t("tenantProfile.companyName")}</label>
141:             <TextFieldControl
142:               id="tp-company-name"
143:               data-testid="tp-company-name"
144:               type="text"
145:               value={form.company_name}
146:               onChange={handleChange("company_name")}
147:               disabled={!canEdit}
148:               maxLength={255}
149:             />
150:           </div>
151: 
152:           <div className="form-group">
153:             <label htmlFor="tp-company-name-en">{t("tenantProfile.companyNameEn")}</label>
154:             <TextFieldControl
155:               id="tp-company-name-en"
156:               data-testid="tp-company-name-en"
157:               type="text"
158:               value={form.company_name_en}
159:               onChange={handleChange("company_name_en")}
160:               disabled={!canEdit}
161:               maxLength={255}
162:             />
163:           </div>
164: 
165:           <div className="form-group">
166:             <label htmlFor="tp-address">{t("tenantProfile.address")}</label>
167:             <TextareaControl
168:               id="tp-address"
169:               data-testid="tp-address"
170:               value={form.address}
171:               onChange={handleChange("address")}
172:               disabled={!canEdit}
173:               rows={3}
174:             />
175:           </div>
176: 
177:           <div className="form-group">
178:             <label htmlFor="tp-phone">{t("tenantProfile.phone")}</label>
179:             <TextFieldControl
180:               id="tp-phone"
181:               data-testid="tp-phone"
182:               type="text"
183:               value={form.phone}
184:               onChange={handleChange("phone")}
185:               disabled={!canEdit}
186:               maxLength={50}
187:             />
188:           </div>
189: 
190:           <div className="form-group">
191:             <label htmlFor="tp-email">{t("tenantProfile.email")}</label>
192:             <TextFieldControl
193:               id="tp-email"
194:               data-testid="tp-email"
195:               type="email"
196:               value={form.email}
197:               onChange={handleChange("email")}
198:               disabled={!canEdit}
199:               maxLength={255}
200:             />
201:           </div>
202: 
203:           <div className="form-group">
204:             <label htmlFor="tp-website">{t("tenantProfile.website")}</label>
205:             <TextFieldControl
206:               id="tp-website"
207:               data-testid="tp-website"
208:               type="text"
209:               value={form.website}
210:               onChange={handleChange("website")}
211:               disabled={!canEdit}
212:               maxLength={255}
213:             />
214:           </div>
215: 
216:           <div className="form-group">
217:             <label htmlFor="tp-seal-url">{t("tenantProfile.sealImageUrl")}</label>
218:             <TextFieldControl
219:               id="tp-seal-url"
220:               data-testid="tp-seal-image-url"
221:               type="text"
222:               value={form.seal_image_url}
223:               onChange={handleChange("seal_image_url")}
224:               disabled={!canEdit}
225:               placeholder="https://..."
226:             />
227:             <small className="form-hint">{t("tenantProfile.sealHint")}</small>
228:           </div>
229: 
230:           <div className="form-group">
231:             <label htmlFor="tp-default-language">{t("tenantProfile.defaultLanguage")}</label>
232:             <SelectControl
233:               fullWidth
234:               id="tp-default-language"
235:               data-testid="tp-default-language"
236:               value={form.default_language}
237:               onChange={handleChange("default_language")}
238:               disabled={!canEdit}
239:             >
240:               <option value="ja">{t("language.ja")} (ja)</option>
241:               <option value="en">English (en)</option>
242:               <option value="ko">한국어 (ko)</option>
243:               <option value="zh">{t("language.zh")} (zh)</option>
244:             </SelectControl>
245:           </div>
246: 
247:           {canEdit && (
248:             <div className="form-actions">
249:               <Button loading={saving} variant="primary" size="md"
250:                 type="submit"
251: 
252:                 disabled={saving}
253:                 data-testid="tenant-profile-save"
254:               >
255:                 {t("common.save")}
256:               </Button>
257:             </div>
258:           )}
259:         </form>
260:       )}
261:     </PageLayout>
262:   );
263: }
```

### origin/main:frontend/src/pages/management-center/ManagementCenterPage.tsx :76-90
```
76:       ],
77:     },
78:     {
79:       key: "business",
80:       titleKey: "managementCenter.sectionBusiness",
81:       items: [
82:         { to: "tenant-profile", labelKey: "nav.tenantProfile",
83:           visible: can("tenantProfile") },
84:         { to: "channels",       labelKey: "nav.channels",       visible: can("channels") },
85:         { to: "channel-masters", labelKey: "nav.channelMasters", visible: can("channelMasters") },
86:         { to: "bots",           labelKey: "nav.bots",           visible: can("bots") },
87:         { to: "notifications",  labelKey: "nav.notifications",  visible: can("notifications") },
88:         { to: "login-requests", labelKey: "nav.tenantLoginRequests", visible: isTenantOwner },
89:       ],
90:     },
```

### origin/main:frontend/src/pages/admin/AdminHubPage.tsx :20-32
```
20: import { useIsMobile } from "../../hooks/useIsMobile";
21: import "./admin-hub.css";
22: 
23: const TABS = [
24:   {
25:     to:       "tenant-profile",
26:     labelKey: "nav.tenantProfile",
27:     Icon:     ADMIN_HUB_ICONS.tenantProfile,
28:   },
29:   {
30:     to:       "tenant-policy",
31:     labelKey: "nav.tenantPolicy",
32:     Icon:     ADMIN_HUB_ICONS.tenantPolicy,
```

### origin/main:frontend/src/App.tsx :398-403
```
398:                     {/* SaaS 管理者ハブ（ボトムタブ統合） */}
399:                     <Route path="/admin" element={<AdminHubPage />}>
400:                       <Route index element={<Navigate to="tenant-profile" replace />} />
401:                       {/* Sprint 8 / F8: テナント admin (tenant.profile.edit / view) */}
402:                       <Route path="tenant-profile"      element={<TenantProfilePage />} />
403:                       {/* ADR-106: テナントポリシー設定 (tenant.profile.edit / view) */}
```

### origin/main:frontend/src/App.tsx :429-432
```
429:                       <Route path="inventory-visibility" element={<InventoryVisibilityPage />} />
430:                       <Route path="commission"          element={<CommissionSettingsPage />} />
431:                       <Route path="tenant-profile"      element={<TenantProfilePage />} />
432:                       {/* 管理センター左メニューを保ったまま開くため /admin/* と同じページを再掲 */}
```

### origin/main:frontend/src/pages/invoice-create/InvoiceCreatePage.tsx :212-226
```
212: 
213:   return (
214:     <PageLayout
215:       titleText={t("invoices.createTitle")}
216:       subtitleKey="invoices.createSubtitle"
217:       headerAction={
218:         <div style={{ display: "flex", gap: "var(--space-2)" }}>
219:           <Button variant="secondary" size="md" onClick={() => navigate("/management-center/tenant-profile")}>
220:             {t("nav.tenantProfile")}
221:           </Button>
222:         </div>
223:       }
224:     >
225: 
226:       {shownError && <div className="error-message">{shownError}</div>}
```

### origin/main:frontend/src/locales/ja.json :282-282
```
282:     "tenantProfile": "発行者情報",
```

### origin/main:frontend/src/locales/ja.json :2058-2072
```
2058:   "tenantProfile": {
2059:     "title": "発行者情報",
2060:     "subtitle": "発注書 PDF / メールの差出人欄に表示される会社情報を設定します",
2061:     "companyName": "会社名 (日本語)",
2062:     "companyNameEn": "会社名 (英語)",
2063:     "address": "住所",
2064:     "phone": "電話番号",
2065:     "email": "メールアドレス",
2066:     "website": "ウェブサイト",
2067:     "sealImageUrl": "印鑑画像 URL",
2068:     "sealHint": "印鑑画像の URL を入力すると PDF に表示されます (オプション)",
2069:     "defaultLanguage": "既定言語",
2070:     "saved": "発行者情報を保存しました",
2071:     "permissionRequired": "この画面の閲覧には tenant.profile.view 権限が必要です"
2072:   },
```

### origin/main:frontend/src/constants/menuPermissions.ts :69-69
```
69:   tenantProfile: { labelKey: "nav.tenantProfile", anyOf: ["tenant.profile.edit", "tenant.profile.view"] },
```

### origin/main:frontend/src/config/routeTitles.ts :46-46
```
46:   "/admin/tenant-profile":       "nav.tenantProfile",
```

## (g) 税率の画面の置き場

### origin/main:frontend/src/pages/super-admin/settings/settingsNav.ts :1-38
```
1: // 全体設定（/super-admin/settings）の項目の正本。
2: // App.tsx の Route・SettingsHubPage の小さなメニュー・LINE解析の転送・転送表・取込画面の戻り先が、ここを読む。
3: // 項目を足すときは、ここに1行と SettingsMasterPage の Panel の表に1行。
4: 
5: export interface SettingsNavItem {
6:   key: string;
7:   labelKey: string;
8: }
9: 
10: /** 金額の設定の組。 */
11: export const SETTINGS_MONEY_ITEMS: readonly SettingsNavItem[] = [
12:   { key: "fx-rate", labelKey: "nav.superAdminFxRate" },
13:   { key: "tax-rates", labelKey: "nav.superAdminTaxRates" },
14:   { key: "sa-products", labelKey: "nav.superAdminSaProducts" },
15: ];
16: 
17: /** マスタ管理の組（LINE解析にあった11件。並びも同じ）。 */
18: export const SETTINGS_MASTER_ITEMS: readonly SettingsNavItem[] = [
19:   { key: "product-master", labelKey: "analysisRules.sidebar.productMaster" },
20:   { key: "product-categories-master", labelKey: "analysisRules.sidebar.productCategoriesMaster" },
21:   { key: "product-kinds-master", labelKey: "analysisRules.sidebar.productKindsMaster" },
22:   { key: "type-master", labelKey: "analysisRules.sidebar.typeMaster" },
23:   { key: "product-lines-master", labelKey: "analysisRules.sidebar.productLinesMaster" },
24:   { key: "product-formats-master", labelKey: "analysisRules.sidebar.productFormatsMaster" },
25:   { key: "supplier-master", labelKey: "analysisRules.sidebar.supplierMaster" },
26:   { key: "note-master", labelKey: "analysisRules.sidebar.noteMaster" },
27:   { key: "quantity-units-master", labelKey: "analysisRules.sidebar.quantityUnitsMaster" },
28:   { key: "condition-defs-master", labelKey: "analysisRules.sidebar.conditionDefsMaster" },
29:   { key: "weight-classes-master", labelKey: "analysisRules.sidebar.weightClassesMaster" },
30: ];
31: 
32: export function settingsMasterPath(key: string): string {
33:   return `/super-admin/settings/masters/${key}`;
34: }
35: 
36: export function isSettingsMasterKey(key: string | null | undefined): key is string {
37:   return !!key && SETTINGS_MASTER_ITEMS.some((i) => i.key === key);
38: }
```

### origin/main:frontend/src/App.tsx :322-348
```
322:                     {/* 全体設定ハブ (is_super_admin 限定、ハブ内で 403 ガード)。項目の正本は settingsNav.ts */}
323:                     <Route path="/super-admin/settings" element={<SettingsHubPage />}>
324:                       <Route index element={<Navigate to="fx-rate" replace />} />
325:                       {/* 為替レート SSOT */}
326:                       <Route path="fx-rate" element={<FxRatePage />} />
327:                       <Route
328:                         path="tax-rates"
329:                         element={
330:                           <ComingSoonPage
331:                             title={t("nav.superAdminTaxRates")}
332:                             description={t("superAdmin.settings.comingSoon")}
333:                           />
334:                         }
335:                       />
336:                       <Route
337:                         path="sa-products"
338:                         element={
339:                           <ComingSoonPage
340:                             title={t("nav.superAdminSaProducts")}
341:                             description={t("superAdmin.settings.comingSoon")}
342:                           />
343:                         }
344:                       />
345:                       <Route path="masters/:key" element={<SettingsMasterPage />} />
346:                     </Route>
347:                     {/* ADR-1055: ログインの許可待ち (is_super_admin 限定、Page 内で 403 の表示) */}
348:                     <Route
```

## (h) ADR-142 Decision 2・3

### origin/main:docs/adr/ADR-142-tenant-provisioning-completeness.md :18-22
```
18: ## Decision（決定）
19: 
20: 1. **新テナント作成時に、必須のテナント別テーブルは provisioning コードで漏れなく作られ、各々に RLS有効化＋テナント分離ポリシーが付与される**ことを正典とする。GRANT は `GRANT … ON ALL TABLES IN SCHEMA` の一括付与でカバーする。
21: 2. **「テナント別テーブルを migration で追加する変更」は、同時に provisioning コード（`create_tenant_schema` 経路）への反映を必須とする**。片方だけの変更は不完全とみなす。
22: 3. テナント別 RLS テーブルの**分離ポリシーは、既存テナントと同一の命名・定義に揃える**（同一テーブルは全テナントで同一ポリシー名）。D-2 では `own_inventory_tenant_isolation`（既存 migration と同名）を採用。
```

## (i) 全会社へ表を足す既存の移行

### origin/main:migrations/20260604_140000_create_own_inventory.sql :1-78
```
1: -- Migration: 全テナントに own_inventory テーブルを作成
2: --
3: -- 目的 (ADR SA-04/05):
4: --   A在庫（自社保有在庫）をテナント専用スキーマに分離して管理する。
5: --   B在庫（public.inventory, 仕入元フィード）とは完全に別テーブル。
6: --
7: --   物理在庫数(physical_qty) / 引当済み(reserved_qty) / 利用可能(available_qty) の
8: --   2段階引当モデルを実装する。
9: --
10: -- 影響テーブル: {tenant_NNN}.own_inventory（新規作成）
11: -- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
12: -- 冪等: CREATE TABLE IF NOT EXISTS + DO ブロックでポリシー重複チェック
13: 
14: DO $$
15: DECLARE
16:     schema_record RECORD;
17: BEGIN
18:     FOR schema_record IN
19:         SELECT nspname AS schema_name
20:         FROM pg_namespace
21:         WHERE nspname LIKE 'tenant_%'
22:         ORDER BY nspname
23:     LOOP
24:         RAISE NOTICE 'Processing schema: %', schema_record.schema_name;
25: 
26:         -- own_inventory テーブルを作成
27:         EXECUTE format(
28:             'CREATE TABLE IF NOT EXISTS %I.own_inventory (
29:                 id             SERIAL PRIMARY KEY,
30:                 tenant_id      INTEGER      NOT NULL,
31:                 product_id     INTEGER      NOT NULL REFERENCES public.products(id),
32:                 physical_qty   INTEGER      NOT NULL DEFAULT 0 CHECK (physical_qty >= 0),
33:                 reserved_qty   INTEGER      NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
34:                 available_qty  INTEGER GENERATED ALWAYS AS (physical_qty - reserved_qty) STORED,
35:                 unit_price     NUMERIC(15,2),
36:                 condition      VARCHAR(50),
37:                 status         VARCHAR(20)  NOT NULL DEFAULT ''active''
38:                                CHECK (status IN (''active'',''inactive'',''sold_out'')),
39:                 note_ja        TEXT,
40:                 note_en        TEXT,
41:                 antique_ledger_id INTEGER,
42:                 created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
43:                 updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
44:                 CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
45:             )',
46:             schema_record.schema_name
47:         );
48: 
49:         -- テーブルコメント
50:         EXECUTE format(
51:             'COMMENT ON TABLE %I.own_inventory IS
52:              ''ADR SA-04/05: A在庫（自社保有）。B在庫（public.inventory）とは完全分離。''',
53:             schema_record.schema_name
54:         );
55: 
56:         -- RLS 有効化（冪等: 既に有効でもエラーにならない）
57:         EXECUTE format(
58:             'ALTER TABLE %I.own_inventory ENABLE ROW LEVEL SECURITY',
59:             schema_record.schema_name
60:         );
61: 
62:         -- RLS ポリシー（冪等: pg_policies で存在確認）
63:         IF NOT EXISTS (
64:             SELECT 1 FROM pg_policies
65:             WHERE schemaname = schema_record.schema_name
66:               AND tablename  = 'own_inventory'
67:               AND policyname = 'own_inventory_tenant_isolation'
68:         ) THEN
69:             EXECUTE format(
70:                 'CREATE POLICY own_inventory_tenant_isolation ON %I.own_inventory
71:                  USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)',
72:                 schema_record.schema_name
73:             );
74:         END IF;
75: 
76:     END LOOP;
77: END
78: $$;
```
