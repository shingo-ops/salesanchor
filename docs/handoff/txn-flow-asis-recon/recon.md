# recon.md：取引フロー As-Is（KGI K1〜K10 基準）

> この文書は何か：今のシステムとデータの実態を読むだけで数えた調査記録（生出力）。
> 親: ../../specs/transaction-flow/README.md ／ 指示書: ./recon-brief.md ／ FRESH-RUN: 2026-07-02 08:26-08:27 UTC ／ origin/main: 23316cfa

## Part A（リポジトリ・生出力）
```
>>> cd /Users/tanizawashingo/salesanchor && git fetch origin && date -u && git rev-parse origin/main
From https://github.com/shingo-ops/salesanchor
   6238c455..23316cfa  main       -> origin/main
   fa956ddc..8b8b8826  release/batch1-5-worktree-guard -> origin/release/batch1-5-worktree-guard
Thu Jul  2 08:26:50 UTC 2026
23316cfac359eec64948ce85328c8ff7ca908c37

>>> grep -n "CREATE TABLE" backend/app/services/tenant.py | grep -E "companies|contacts|leads|deals|orders|quotes|invoices|purchase_orders|purchase_order_items|conversation_logs"
190:CREATE TABLE IF NOT EXISTS {schema}.companies (
227:CREATE TABLE IF NOT EXISTS {schema}.contacts (
346:CREATE TABLE IF NOT EXISTS {schema}.leads (
423:CREATE TABLE IF NOT EXISTS {schema}.deals (
486:CREATE TABLE IF NOT EXISTS {schema}.orders (
816:CREATE TABLE IF NOT EXISTS {schema}.quotes (
861:CREATE TABLE IF NOT EXISTS {schema}.invoices (
945:CREATE TABLE IF NOT EXISTS {schema}.purchase_orders (
960:CREATE TABLE IF NOT EXISTS {schema}.purchase_order_items (

>>> nl -ba backend/app/services/tenant.py | sed -n "190,257p"
   190	CREATE TABLE IF NOT EXISTS {schema}.companies (
   191	    id SERIAL PRIMARY KEY,
   192	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   193	    company_code VARCHAR(20) NOT NULL,
   194	    lead_id INTEGER,                                   -- FK は leads 作成後に付与
   195	    name VARCHAR(255) NOT NULL,
   196	    name_en VARCHAR(255),
   197	    normalized_name VARCHAR(255),
   198	    -- is_individual は Phase 1-B-2 Step 5a で削除（個人/法人の区別を撤廃、migration 033）
   199	    industry VARCHAR(100),
   200	    website VARCHAR(255),
   201	    trust_level SMALLINT CHECK (trust_level IS NULL OR trust_level BETWEEN 1 AND 5),
   202	    priority_focus VARCHAR(50),
   203	    per_order_amount NUMERIC(15,2),
   204	    monthly_frequency SMALLINT,
   205	    monthly_forecast NUMERIC(15,2),
   206	    monthly_forecast_source VARCHAR(20)
   207	        CHECK (monthly_forecast_source IS NULL OR monthly_forecast_source IN ('manual','ai_analysis')),
   208	    monthly_forecast_updated_at TIMESTAMPTZ,
   209	    billing_display_name VARCHAR(255),
   210	    payment_recipient_name VARCHAR(255),
   211	    fedex_account VARCHAR(100),
   212	    shipping_note TEXT,
   213	    status VARCHAR(20) NOT NULL DEFAULT 'active'
   214	        CHECK (status IN ('active','inactive','archived','pending_dedup_review')),
   215	    sales_rep_id INTEGER,                              -- FK は staff 作成後に付与
   216	    notes TEXT,
   217	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   218	    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   219	    UNIQUE (tenant_id, company_code)
   220	);
   221	CREATE INDEX IF NOT EXISTS idx_companies_tenant_id ON {schema}.companies (tenant_id);
   222	CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON {schema}.companies (normalized_name);
   223	CREATE INDEX IF NOT EXISTS idx_companies_lead_id ON {schema}.companies (lead_id);
   224	CREATE INDEX IF NOT EXISTS idx_companies_sales_rep_id ON {schema}.companies (sales_rep_id);
   225	CREATE INDEX IF NOT EXISTS idx_companies_status ON {schema}.companies (status);
   226	
   227	CREATE TABLE IF NOT EXISTS {schema}.contacts (
   228	    id SERIAL PRIMARY KEY,
   229	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   230	    company_id INTEGER NOT NULL REFERENCES {schema}.companies(id) ON DELETE CASCADE,
   231	    contact_code VARCHAR(20) NOT NULL,
   232	    lead_id INTEGER,                                   -- FK は leads 作成後に付与
   233	    surname VARCHAR(100),
   234	    given_name VARCHAR(100),
   235	    display_name VARCHAR(255),
   236	    job_title VARCHAR(100),
   237	    department VARCHAR(100),
   238	    is_primary_contact BOOLEAN NOT NULL DEFAULT FALSE,
   239	    primary_email VARCHAR(255),
   240	    primary_phone VARCHAR(50),
   241	    -- PR #163 (PR #145 残課題 Q2): pending_dedup_review 解消フローのため
   242	    -- companies.status と CHECK 制約を揃える（migration 037 で既存テナントには
   243	    -- backport 済）。新テナント作成時は最初からこの 4 値を許容する。
   244	    status VARCHAR(20) NOT NULL DEFAULT 'active'
   245	        CHECK (status IN ('active','inactive','archived','pending_dedup_review')),
   246	    notes TEXT,
   247	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   248	    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   249	    UNIQUE (tenant_id, contact_code)
   250	);
   251	CREATE INDEX IF NOT EXISTS idx_contacts_tenant_id ON {schema}.contacts (tenant_id);
   252	CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON {schema}.contacts (company_id);
   253	CREATE INDEX IF NOT EXISTS idx_contacts_lead_id ON {schema}.contacts (lead_id);
   254	CREATE INDEX IF NOT EXISTS idx_contacts_primary_email ON {schema}.contacts (primary_email);
   255	CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_one_primary_per_company
   256	    ON {schema}.contacts (company_id) WHERE is_primary_contact = TRUE;
   257	

>>> nl -ba backend/app/services/tenant.py | sed -n "346,506p"
   346	CREATE TABLE IF NOT EXISTS {schema}.leads (
   347	    id SERIAL PRIMARY KEY,
   348	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   349	    lead_code VARCHAR(20),
   350	    customer_name VARCHAR(255) NOT NULL,
   351	    company_name VARCHAR(255),
   352	    email VARCHAR(255),
   353	    phone VARCHAR(50),
   354	    channel_type VARCHAR(30),
   355	    initiative VARCHAR(10),
   356	    type VARCHAR(50),
   357	    status VARCHAR(50) DEFAULT 'lead',
   358	    temperature VARCHAR(20),
   359	    estimated_scale VARCHAR(20),
   360	    customer_type VARCHAR(50),
   361	    response_speed VARCHAR(20),
   362	    monthly_forecast NUMERIC(15, 2),
   363	    prospect_rank VARCHAR(10),
   364	    assigned_to INTEGER,
   365	    converted_deal_id INTEGER,
   366	    notes TEXT,
   367	    -- ADR-015 §1/§2: AI 自動収集データ
   368	    country VARCHAR(100),
   369	    target_titles VARCHAR(500),
   370	    -- ADR-015 §3: 返信速度トラッキング
   371	    first_inquiry_at TIMESTAMPTZ,
   372	    first_response_at TIMESTAMPTZ,
   373	    first_response_seconds INTEGER,
   374	    -- ADR-015 §4: カルテ AI 補助対象
   375	    sales_form VARCHAR(50),
   376	    competitor_check BOOLEAN NOT NULL DEFAULT FALSE,
   377	    cs_memo TEXT,
   378	    per_order_amount NUMERIC(15, 2),
   379	    monthly_frequency NUMERIC(10, 2),
   380	    monthly_forecast_source VARCHAR(50),
   381	    -- ADR-015 §4: 営業担当が記入する列
   382	    challenge TEXT,
   383	    nickname VARCHAR(255),
   384	    meeting_impression VARCHAR(50),
   385	    meeting_memo TEXT,
   386	    -- ADR-015 §5: ダッシュボードの次回アクション
   387	    next_action VARCHAR(500),
   388	    next_action_date DATE,
   389	    -- ADR-015 §1/§2/§3: AI 収集ステート
   390	    ai_collection_state VARCHAR(20),
   391	    escalation_flag BOOLEAN NOT NULL DEFAULT FALSE,
   392	    created_at TIMESTAMPTZ DEFAULT NOW(),
   393	    updated_at TIMESTAMPTZ DEFAULT NOW()
   394	);
   395	CREATE INDEX IF NOT EXISTS idx_leads_next_action_date
   396	    ON {schema}.leads (next_action_date) WHERE next_action_date IS NOT NULL;
   397	CREATE INDEX IF NOT EXISTS idx_leads_ai_collection_state
   398	    ON {schema}.leads (ai_collection_state) WHERE ai_collection_state IS NOT NULL;
   399	CREATE INDEX IF NOT EXISTS idx_leads_escalation_flag
   400	    ON {schema}.leads (escalation_flag) WHERE escalation_flag = TRUE;
   401	
   402	-- ADR-015 §7: テナント別 AI 対応プレイブック
   403	CREATE TABLE IF NOT EXISTS {schema}.lead_playbook (
   404	    id SERIAL PRIMARY KEY,
   405	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   406	    name VARCHAR(100) NOT NULL DEFAULT 'default',
   407	    greeting_message TEXT,
   408	    questions JSONB NOT NULL DEFAULT '[]'::jsonb,
   409	    assignment_condition VARCHAR(50) NOT NULL DEFAULT 'all_required',
   410	    assignment_after_n_turns INTEGER,
   411	    assignment_message TEXT,
   412	    assignment_method VARCHAR(50) NOT NULL DEFAULT 'manual',
   413	    country_assignment_map JSONB,
   414	    is_active BOOLEAN NOT NULL DEFAULT TRUE,
   415	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   416	    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   417	    UNIQUE (tenant_id, name)
   418	);
   419	CREATE INDEX IF NOT EXISTS idx_lead_playbook_active
   420	    ON {schema}.lead_playbook (tenant_id) WHERE is_active = TRUE;
   421	
   422	-- 商談データ
   423	CREATE TABLE IF NOT EXISTS {schema}.deals (
   424	    id SERIAL PRIMARY KEY,
   425	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   426	    deal_code VARCHAR(20),
   427	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   428	    --   新テナント作成時も customer_id 列を作らない（新 B2B モデル唯一の正）。
   429	    -- CONSTRAINT 名は migration 032 と合わせる（verify の FK 存在 check が新旧テナントで揃うように）
   430	    company_id INTEGER CONSTRAINT fk_deals_company REFERENCES {schema}.companies(id),
   431	    contact_id INTEGER CONSTRAINT fk_deals_contact REFERENCES {schema}.contacts(id),
   432	    lead_id INTEGER REFERENCES {schema}.leads(id),
   433	    title VARCHAR(255) NOT NULL,
   434	    amount NUMERIC(15, 2),
   435	    currency VARCHAR(10) DEFAULT 'JPY',
   436	    status VARCHAR(50) DEFAULT 'open',
   437	    stage VARCHAR(50) DEFAULT 'open',
   438	    probability INTEGER DEFAULT 10,
   439	    assigned_to INTEGER,
   440	    expected_close_date DATE,
   441	    notes TEXT,
   442	    created_at TIMESTAMPTZ DEFAULT NOW(),
   443	    updated_at TIMESTAMPTZ DEFAULT NOW()
   444	);
   445	CREATE INDEX IF NOT EXISTS idx_deals_company_id ON {schema}.deals (company_id);
   446	CREATE INDEX IF NOT EXISTS idx_deals_contact_id ON {schema}.deals (contact_id);
   447	
   448	-- リード→案件への逆参照FK（leads作成時点ではdealsが未存在のため後から追加）
   449	DO $$
   450	BEGIN
   451	    IF NOT EXISTS (
   452	        SELECT 1 FROM pg_constraint
   453	        WHERE conname = 'fk_leads_converted_deal'
   454	          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
   455	    ) THEN
   456	        ALTER TABLE {schema}.leads
   457	            ADD CONSTRAINT fk_leads_converted_deal
   458	            FOREIGN KEY (converted_deal_id) REFERENCES {schema}.deals(id);
   459	    END IF;
   460	END $$;
   461	
   462	-- Phase 1-B-2: companies.lead_id / contacts.lead_id → leads.id
   463	DO $$
   464	BEGIN
   465	    IF NOT EXISTS (
   466	        SELECT 1 FROM pg_constraint
   467	        WHERE conname = 'fk_companies_lead'
   468	          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
   469	    ) THEN
   470	        ALTER TABLE {schema}.companies
   471	            ADD CONSTRAINT fk_companies_lead
   472	            FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
   473	    END IF;
   474	    IF NOT EXISTS (
   475	        SELECT 1 FROM pg_constraint
   476	        WHERE conname = 'fk_contacts_lead'
   477	          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
   478	    ) THEN
   479	        ALTER TABLE {schema}.contacts
   480	            ADD CONSTRAINT fk_contacts_lead
   481	            FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
   482	    END IF;
   483	END $$;
   484	
   485	-- 注文データ
   486	CREATE TABLE IF NOT EXISTS {schema}.orders (
   487	    id SERIAL PRIMARY KEY,
   488	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   489	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   490	    company_id INTEGER CONSTRAINT fk_orders_company REFERENCES {schema}.companies(id),
   491	    contact_id INTEGER CONSTRAINT fk_orders_contact REFERENCES {schema}.contacts(id),
   492	    deal_id INTEGER REFERENCES {schema}.deals(id),
   493	    order_number VARCHAR(100) NOT NULL,
   494	    total_amount NUMERIC(15, 2),
   495	    status VARCHAR(50) DEFAULT 'pending',
   496	    -- 支払済日時（NULL=未払い）。受注ステータスフロー判定の「支払済フラグ」。
   497	    -- migration 20260604_050000 と同期。
   498	    paid_at TIMESTAMPTZ,
   499	    notes TEXT,
   500	    created_at TIMESTAMPTZ DEFAULT NOW(),
   501	    updated_at TIMESTAMPTZ DEFAULT NOW()
   502	);
   503	CREATE INDEX IF NOT EXISTS idx_orders_company_id ON {schema}.orders (company_id);
   504	CREATE INDEX IF NOT EXISTS idx_orders_contact_id ON {schema}.orders (contact_id);
   505	
   506	-- 操作履歴（監査ログ）

>>> nl -ba backend/app/services/tenant.py | sed -n "816,968p"
   816	CREATE TABLE IF NOT EXISTS {schema}.quotes (
   817	    id SERIAL PRIMARY KEY,
   818	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   819	    quote_code VARCHAR(20),
   820	    deal_id INTEGER REFERENCES {schema}.deals(id),
   821	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   822	    company_id INTEGER CONSTRAINT fk_quotes_company REFERENCES {schema}.companies(id),
   823	    contact_id INTEGER CONSTRAINT fk_quotes_contact REFERENCES {schema}.contacts(id),
   824	    currency VARCHAR(10) DEFAULT 'JPY',
   825	    subtotal NUMERIC(15, 2) DEFAULT 0,
   826	    shipping_fee NUMERIC(15, 2) DEFAULT 0,
   827	    tax_amount NUMERIC(15, 2) DEFAULT 0,
   828	    total_amount NUMERIC(15, 2) DEFAULT 0,
   829	    status VARCHAR(20) DEFAULT 'draft',
   830	    validity_date DATE,
   831	    shipping_country VARCHAR(100),
   832	    shipping_carrier VARCHAR(50),
   833	    delivery_info TEXT,
   834	    pdf_url VARCHAR(500),
   835	    notes TEXT,
   836	    created_by INTEGER,
   837	    created_at TIMESTAMPTZ DEFAULT NOW(),
   838	    updated_at TIMESTAMPTZ DEFAULT NOW()
   839	);
   840	CREATE INDEX IF NOT EXISTS idx_quotes_company_id ON {schema}.quotes (company_id);
   841	CREATE INDEX IF NOT EXISTS idx_quotes_contact_id ON {schema}.quotes (contact_id);
   842	
   843	-- 見積明細
   844	CREATE TABLE IF NOT EXISTS {schema}.quote_items (
   845	    id SERIAL PRIMARY KEY,
   846	    quote_id INTEGER NOT NULL REFERENCES {schema}.quotes(id) ON DELETE CASCADE,
   847	    product_id INTEGER REFERENCES public.products(id),
   848	    product_name VARCHAR(255) NOT NULL,
   849	    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
   850	    name_en VARCHAR(255),
   851	    condition VARCHAR(50),
   852	    unit VARCHAR(20),
   853	    quantity INTEGER NOT NULL DEFAULT 1,
   854	    unit_price NUMERIC(15, 2) NOT NULL,
   855	    weight NUMERIC(10, 3),
   856	    subtotal NUMERIC(15, 2) NOT NULL,
   857	    sort_order INTEGER DEFAULT 0
   858	);
   859	
   860	-- 請求書ヘッダー
   861	CREATE TABLE IF NOT EXISTS {schema}.invoices (
   862	    id SERIAL PRIMARY KEY,
   863	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   864	    invoice_number VARCHAR(30),
   865	    quote_id INTEGER REFERENCES {schema}.quotes(id),
   866	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   867	    company_id INTEGER CONSTRAINT fk_invoices_company REFERENCES {schema}.companies(id),
   868	    contact_id INTEGER CONSTRAINT fk_invoices_contact REFERENCES {schema}.contacts(id),
   869	    currency VARCHAR(10) DEFAULT 'JPY',
   870	    subtotal NUMERIC(15, 2) DEFAULT 0,
   871	    shipping_fee NUMERIC(15, 2) DEFAULT 0,
   872	    tax_amount NUMERIC(15, 2) DEFAULT 0,
   873	    total_amount NUMERIC(15, 2) DEFAULT 0,
   874	    exchange_rate_jpy NUMERIC(12, 4),
   875	    exchange_rate_usd NUMERIC(12, 4),
   876	    amount_jpy NUMERIC(15, 2),
   877	    amount_usd NUMERIC(15, 2),
   878	    payment_method VARCHAR(50),
   879	    status VARCHAR(20) DEFAULT 'draft',
   880	    branch_number INTEGER DEFAULT 1,
   881	    pdf_url VARCHAR(500),
   882	    erp_key VARCHAR(100),
   883	    issued_at TIMESTAMPTZ,
   884	    due_date DATE,
   885	    paid_at TIMESTAMPTZ,
   886	    voided_at TIMESTAMPTZ,
   887	    void_reason VARCHAR(500),
   888	    notes TEXT,
   889	    created_by INTEGER,
   890	    created_at TIMESTAMPTZ DEFAULT NOW(),
   891	    updated_at TIMESTAMPTZ DEFAULT NOW()
   892	);
   893	CREATE INDEX IF NOT EXISTS idx_invoices_company_id ON {schema}.invoices (company_id);
   894	CREATE INDEX IF NOT EXISTS idx_invoices_contact_id ON {schema}.invoices (contact_id);
   895	
   896	-- 請求書明細
   897	CREATE TABLE IF NOT EXISTS {schema}.invoice_items (
   898	    id SERIAL PRIMARY KEY,
   899	    invoice_id INTEGER NOT NULL REFERENCES {schema}.invoices(id) ON DELETE CASCADE,
   900	    product_id INTEGER REFERENCES public.products(id),
   901	    product_name VARCHAR(255) NOT NULL,
   902	    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
   903	    name_en VARCHAR(255),
   904	    condition VARCHAR(50),
   905	    unit VARCHAR(20),
   906	    quantity INTEGER NOT NULL DEFAULT 1,
   907	    unit_price NUMERIC(15, 2) NOT NULL,
   908	    weight NUMERIC(10, 3),
   909	    subtotal NUMERIC(15, 2) NOT NULL,
   910	    sort_order INTEGER DEFAULT 0
   911	);
   912	
   913	-- === Phase 3: 仕入れ・調達管理 ===
   914	
   915	CREATE TABLE IF NOT EXISTS {schema}.suppliers (
   916	    id SERIAL PRIMARY KEY,
   917	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   918	    supplier_code VARCHAR(20),
   919	    name VARCHAR(255) NOT NULL,
   920	    contact_name VARCHAR(255),
   921	    email VARCHAR(255),
   922	    phone VARCHAR(50),
   923	    address TEXT,
   924	    notes TEXT,
   925	    is_active BOOLEAN DEFAULT TRUE,
   926	    created_at TIMESTAMPTZ DEFAULT NOW(),
   927	    updated_at TIMESTAMPTZ DEFAULT NOW()
   928	);
   929	
   930	-- products.supplier_default_id の FK を suppliers 作成後に付与
   931	-- （Phase 1-C M-MVP / 2026-04-28）
   932	DO $supplier_fk$
   933	BEGIN
   934	    IF NOT EXISTS (
   935	        SELECT 1 FROM pg_constraint
   936	        WHERE conrelid = '{schema}.products'::regclass
   937	          AND conname = 'fk_products_supplier_default'
   938	    ) THEN
   939	        ALTER TABLE {schema}.products
   940	        ADD CONSTRAINT fk_products_supplier_default
   941	        FOREIGN KEY (supplier_default_id) REFERENCES {schema}.suppliers(id);
   942	    END IF;
   943	END $supplier_fk$;
   944	
   945	CREATE TABLE IF NOT EXISTS {schema}.purchase_orders (
   946	    id SERIAL PRIMARY KEY,
   947	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   948	    po_number VARCHAR(20),
   949	    supplier_id INTEGER NOT NULL REFERENCES {schema}.suppliers(id),
   950	    status VARCHAR(20) DEFAULT 'draft',
   951	    total_amount NUMERIC(15, 2) DEFAULT 0,
   952	    ordered_at TIMESTAMPTZ,
   953	    received_at TIMESTAMPTZ,
   954	    notes TEXT,
   955	    created_by INTEGER,
   956	    created_at TIMESTAMPTZ DEFAULT NOW(),
   957	    updated_at TIMESTAMPTZ DEFAULT NOW()
   958	);
   959	
   960	CREATE TABLE IF NOT EXISTS {schema}.purchase_order_items (
   961	    id SERIAL PRIMARY KEY,
   962	    purchase_order_id INTEGER NOT NULL REFERENCES {schema}.purchase_orders(id) ON DELETE CASCADE,
   963	    product_id INTEGER NOT NULL REFERENCES public.products(id),
   964	    quantity INTEGER NOT NULL DEFAULT 1,
   965	    unit_cost NUMERIC(15, 2) NOT NULL,
   966	    subtotal NUMERIC(15, 2) NOT NULL,
   967	    sort_order INTEGER DEFAULT 0
   968	);

>>> grep -n "def create" backend/app/routers/deals.py backend/app/routers/companies.py backend/app/routers/orders.py
backend/app/routers/deals.py:142:async def create_deal(
backend/app/routers/companies.py:363:async def create_company(
backend/app/routers/orders.py:339:async def create_order(

>>> nl -ba backend/app/routers/deals.py | sed -n "136,230p"
   136	@router.post(
   137	    "/deals",
   138	    response_model=DealResponse,
   139	    status_code=201,
   140	    dependencies=[Depends(require_permission("deals.create"))],
   141	)
   142	async def create_deal(
   143	    data: DealCreate,
   144	    db: AsyncSession = Depends(get_db),
   145	    tenant_id: int = Depends(get_current_tenant),
   146	    current_user: User = Depends(get_current_user),
   147	):
   148	    """商談を登録する（deal_codeは自動採番）"""
   149	    deals_t = tenant_table_ref(db, tenant_id, "deals")
   150	    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
   151	    leads_t = tenant_table_ref(db, tenant_id, "leads")
   152	    # Step 5d: contact / company の存在 + 所属一致確認のみ
   153	    contact_check = await db.execute(
   154	        text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"),
   155	        {"id": data.contact_id},
   156	    )
   157	    contact_row = contact_check.first()
   158	    if not contact_row:
   159	        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された担当者が見つかりません")
   160	    if contact_row[0] != data.company_id:
   161	        raise HTTPException(
   162	            status_code=status.HTTP_400_BAD_REQUEST,
   163	            detail="指定された担当者は指定会社に所属していません",
   164	        )
   165	
   166	    # リード存在確認（指定時のみ）
   167	    if data.lead_id is not None:
   168	        lead_check = await db.execute(text(f"SELECT id FROM {leads_t} WHERE id = :id"), {"id": data.lead_id})
   169	        if not lead_check.first():
   170	            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたリードが見つかりません")
   171	
   172	    result = await db.execute(
   173	        text(f"""
   174	            INSERT INTO {deals_t} (
   175	                tenant_id, company_id, contact_id, lead_id,
   176	                title, amount, currency,
   177	                status, stage, probability,
   178	                assigned_to, expected_close_date, notes, lead_source
   179	            )
   180	            VALUES (
   181	                :tenant_id, :company_id, :contact_id, :lead_id,
   182	                :title, :amount, :currency,
   183	                :status, :stage, :probability,
   184	                :assigned_to, :expected_close_date, :notes, :lead_source
   185	            )
   186	            RETURNING id
   187	        """),
   188	        {
   189	            "tenant_id": tenant_id,
   190	            "company_id": data.company_id,
   191	            "contact_id": data.contact_id,
   192	            "lead_id": data.lead_id,
   193	            "title": data.title,
   194	            "amount": data.amount,
   195	            "currency": data.currency.value,
   196	            "status": data.status.value,
   197	            "stage": data.stage.value,
   198	            "probability": data.probability,
   199	            "assigned_to": data.assigned_to,
   200	            "expected_close_date": data.expected_close_date,
   201	            "notes": data.notes,
   202	            "lead_source": data.lead_source,
   203	        },
   204	    )
   205	    new_id = result.scalar_one()
   206	
   207	    # deal_code = DL-00001 形式で自動採番（Python側で生成してDB非依存）
   208	    await db.execute(
   209	        text(f"UPDATE {deals_t} SET deal_code = :code WHERE id = :id"),
   210	        {"code": f"DL-{new_id:05d}", "id": new_id},
   211	    )
   212	
   213	    fetched = await db.execute(
   214	        text(f"SELECT {_DEAL_COLUMNS} FROM {deals_t} WHERE id = :id"),
   215	        {"id": new_id},
   216	    )
   217	    row = fetched.mappings().first()
   218	
   219	    await record_audit_log(
   220	        db=db, tenant_id=tenant_id, user_id=current_user.id,
   221	        action="create", table_name="deals", record_id=new_id,
   222	        new_data=data.model_dump(exclude_none=True, mode="json"),
   223	    )
   224	    await db.commit()
   225	    await reset_tenant_context(db, tenant_id)
   226	    await invalidate_dashboard_cache(tenant_id)
   227	
   228	    return DealResponse(**row)
   229	
   230	

>>> nl -ba backend/app/schemas/deal.py | sed -n "55,95p"
    55	class DealCreate(BaseModel):
    56	    """商談登録リクエスト（Step 5d 以降は company_id + contact_id 必須）"""
    57	    company_id: int = Field(ge=1, description="会社ID")
    58	    contact_id: int = Field(ge=1, description="担当者ID")
    59	    lead_id: int | None = Field(default=None, ge=1, description="変換元リードID")
    60	    title: str = Field(min_length=1, max_length=255, description="商談タイトル")
    61	    amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2, description="金額")
    62	    currency: Currency = Field(default=Currency.JPY, description="通貨")
    63	    status: DealStatus = Field(default=DealStatus.open, description="ステータス")
    64	    stage: DealStage = Field(default=DealStage.open, description="ステージ")
    65	    probability: int | None = Field(default=None, ge=0, le=100, description="成約確率(%)")
    66	    assigned_to: int | None = Field(default=None, ge=1, description="担当者ユーザーID")
    67	    expected_close_date: date | None = Field(default=None, description="成約予定日")
    68	    notes: str | None = Field(default=None, max_length=5000, description="備考")
    69	    lead_source: str | None = Field(default=None, max_length=50, description="流入元")
    70	
    71	
    72	class CloseReasonRef(BaseModel):
    73	    """成約/失注理由の参照（商談更新時に渡す）"""
    74	    reason_id: int = Field(ge=1, description="close_reasons.id")
    75	    is_primary: bool = Field(default=False, description="主因フラグ（必ず1件だけ True）")
    76	
    77	
    78	class DealUpdate(BaseModel):
    79	    """商談更新リクエスト（部分更新）"""
    80	    company_id: int | None = Field(default=None, ge=1)
    81	    contact_id: int | None = Field(default=None, ge=1)
    82	    lead_id: int | None = Field(default=None, ge=1)
    83	    title: str | None = Field(default=None, min_length=1, max_length=255)
    84	    amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    85	    currency: Currency | None = None
    86	    status: DealStatus | None = None
    87	    stage: DealStage | None = None
    88	    probability: int | None = Field(default=None, ge=0, le=100)
    89	    assigned_to: int | None = Field(default=None, ge=1)
    90	    expected_close_date: date | None = None
    91	    notes: str | None = Field(default=None, max_length=5000)
    92	    lead_source: str | None = Field(default=None, max_length=50)
    93	    close_reason_memo: str | None = Field(default=None, max_length=1000, description="成約/失注メモ")
    94	    close_reasons: list[CloseReasonRef] | None = Field(default=None, description="成約/失注理由（主因1件必須）")
    95	

>>> nl -ba backend/app/routers/companies.py | sed -n "357,440p"
   357	@router.post(
   358	    "/companies",
   359	    response_model=CompanyResponse,
   360	    status_code=201,
   361	    dependencies=[Depends(require_permission("customers.create"))],
   362	)
   363	async def create_company(
   364	    data: CompanyCreate,
   365	    db: AsyncSession = Depends(get_db),
   366	    tenant_id: int = Depends(get_current_tenant),
   367	    current_user: User = Depends(get_current_user),
   368	):
   369	    """会社を登録する（本体 + 副テーブル）。company_code 未指定なら CO-{id:05d}。"""
   370	    try:
   371	        explicit_code = data.company_code and data.company_code.strip()
   372	        # CO-PEND-<8hex> = 最大 16 文字 (VARCHAR(20) に収まる)。
   373	        # 元は hex 32 文字で VARCHAR(20) 超過の StringDataRightTruncationError 500 が出ていた（Step 5c-1 検証で発覚）。
   374	        company_code = explicit_code if explicit_code else f"CO-PEND-{uuid.uuid4().hex[:8]}"
   375	
   376	        forecast_source_value = (
   377	            data.monthly_forecast_source.value if data.monthly_forecast_source else "manual"
   378	        ) if data.monthly_forecast is not None else None
   379	
   380	        result = await db.execute(
   381	            text("""
   382	                INSERT INTO companies (
   383	                    tenant_id, company_code, lead_id, sales_rep_id,
   384	                    name, name_en, normalized_name, industry, website,
   385	                    trust_level, priority_focus,
   386	                    per_order_amount, monthly_frequency,
   387	                    monthly_forecast, monthly_forecast_source, monthly_forecast_updated_at,
   388	                    billing_display_name, payment_recipient_name,
   389	                    fedex_account, shipping_note,
   390	                    status, notes
   391	                ) VALUES (
   392	                    :tenant_id, :company_code, :lead_id, :sales_rep_id,
   393	                    :name, :name_en, :normalized_name, :industry, :website,
   394	                    :trust_level, :priority_focus,
   395	                    :per_order_amount, :monthly_frequency,
   396	                    :monthly_forecast, :monthly_forecast_source, NULL,
   397	                    :billing_display_name, :payment_recipient_name,
   398	                    :fedex_account, :shipping_note,
   399	                    :status, :notes
   400	                )
   401	                RETURNING id
   402	            """),
   403	            {
   404	                "tenant_id": tenant_id,
   405	                "company_code": company_code,
   406	                "lead_id": data.lead_id,
   407	                "sales_rep_id": data.sales_rep_id,
   408	                "name": data.name,
   409	                "name_en": data.name_en,
   410	                "normalized_name": data.normalized_name,
   411	                "industry": data.industry,
   412	                "website": data.website,
   413	                "trust_level": data.trust_level,
   414	                "priority_focus": data.priority_focus,
   415	                "per_order_amount": data.per_order_amount,
   416	                "monthly_frequency": data.monthly_frequency,
   417	                "monthly_forecast": data.monthly_forecast,
   418	                "monthly_forecast_source": forecast_source_value,
   419	                "billing_display_name": data.billing_display_name,
   420	                "payment_recipient_name": data.payment_recipient_name,
   421	                "fedex_account": data.fedex_account,
   422	                "shipping_note": data.shipping_note,
   423	                "status": data.status.value,
   424	                "notes": data.notes,
   425	            },
   426	        )
   427	        new_id = result.scalar_one()
   428	
   429	        if not explicit_code:
   430	            await db.execute(
   431	                text("UPDATE companies SET company_code = :code WHERE id = :id"),
   432	                {"code": f"CO-{new_id:05d}", "id": new_id},
   433	            )
   434	        if data.monthly_forecast is not None:
   435	            await db.execute(
   436	                text("UPDATE companies SET monthly_forecast_updated_at = NOW() WHERE id = :id"),
   437	                {"id": new_id},
   438	            )
   439	
   440	        await _replace_addresses(db, new_id, data.addresses)

>>> nl -ba backend/app/schemas/company.py | sed -n "111,140p"
   111	class CompanyCreate(BaseModel):
   112	    company_code: str | None = Field(
   113	        default=None, max_length=20,
   114	        description="CO-00001 形式。未指定ならサーバー側で自動採番",
   115	    )
   116	    lead_id: int | None = Field(default=None, description="出自リード（任意）")
   117	    sales_rep_id: int | None = Field(default=None, description="担当スタッフ id")
   118	    name: str = Field(min_length=1, max_length=255)
   119	    name_en: str | None = Field(default=None, max_length=255)
   120	    normalized_name: str | None = Field(default=None, max_length=255)
   121	    industry: str | None = Field(default=None, max_length=100)
   122	    website: str | None = Field(default=None, max_length=255)
   123	    trust_level: int | None = Field(default=None, ge=1, le=5)
   124	    priority_focus: str | None = Field(default=None, max_length=50)
   125	    per_order_amount: Decimal | None = None
   126	    monthly_frequency: int | None = Field(default=None, ge=0)
   127	    monthly_forecast: Decimal | None = None
   128	    monthly_forecast_source: MonthlyForecastSource | None = None
   129	    billing_display_name: str | None = Field(default=None, max_length=255)
   130	    payment_recipient_name: str | None = Field(default=None, max_length=255)
   131	    fedex_account: str | None = Field(default=None, max_length=100)
   132	    shipping_note: str | None = None
   133	    status: CompanyStatus = CompanyStatus.active
   134	    notes: str | None = None
   135	    # 副テーブル（ネスト、任意）
   136	    addresses: list[CompanyAddressInput] = Field(default_factory=list)
   137	    sales_channels: list[str] = Field(default_factory=list)
   138	
   139	
   140	class CompanyUpdate(BaseModel):

>>> nl -ba backend/app/routers/orders.py | sed -n "337,468p"
   337	@router.post("/orders", response_model=OrderResponse, status_code=201,
   338	             dependencies=[Depends(require_permission("orders.create"))])
   339	async def create_order(
   340	    data: OrderCreate,
   341	    db: AsyncSession = Depends(get_db),
   342	    tenant_id: int = Depends(get_current_tenant),
   343	    current_user: User = Depends(get_current_user),
   344	):
   345	    """注文を登録する"""
   346	    orders_t = tenant_table_ref(db, tenant_id, "orders")
   347	    contacts_t = tenant_table_ref(db, tenant_id, "contacts")
   348	    deals_t = tenant_table_ref(db, tenant_id, "deals")
   349	    # Step 5d: contact / company の存在 + 所属一致確認のみ
   350	    contact_check = await db.execute(
   351	        text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"),
   352	        {"id": data.contact_id},
   353	    )
   354	    contact_row = contact_check.first()
   355	    if not contact_row:
   356	        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者が存在しません")
   357	    if contact_row[0] != data.company_id:
   358	        raise HTTPException(
   359	            status_code=status.HTTP_400_BAD_REQUEST,
   360	            detail="指定された担当者は指定会社に所属していません",
   361	        )
   362	
   363	    # 商談の存在確認（指定された場合）
   364	    if data.deal_id:
   365	        deal = await db.execute(text(f"SELECT id FROM {deals_t} WHERE id = :id"), {"id": data.deal_id})
   366	        if not deal.first():
   367	            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された商談が存在しません")
   368	
   369	    # 注文番号の重複チェック
   370	    dup = await db.execute(
   371	        text(f"SELECT id FROM {orders_t} WHERE order_number = :order_number"),
   372	        {"order_number": data.order_number},
   373	    )
   374	    if dup.first():
   375	        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="この注文番号は既に使用されています")
   376	
   377	    result = await db.execute(
   378	        text(f"""
   379	            INSERT INTO {orders_t} (
   380	                tenant_id, company_id, contact_id, deal_id, invoice_id, order_number,
   381	                total_amount, currency, status,
   382	                shipping_carrier, shipping_fee, shipping_country, notes
   383	            )
   384	            VALUES (
   385	                :tenant_id, :company_id, :contact_id, :deal_id, :invoice_id, :order_number,
   386	                :total_amount, :currency, :status,
   387	                :shipping_carrier, :shipping_fee, :shipping_country, :notes
   388	            )
   389	            RETURNING {_SELECT_COLS}
   390	        """),
   391	        {
   392	            "tenant_id": tenant_id,
   393	            "company_id": data.company_id,
   394	            "contact_id": data.contact_id,
   395	            "deal_id": data.deal_id,
   396	            "invoice_id": data.invoice_id,
   397	            "order_number": data.order_number,
   398	            "total_amount": data.total_amount,
   399	            "currency": data.currency,
   400	            "status": data.status.value,
   401	            "shipping_carrier": data.shipping_carrier,
   402	            "shipping_fee": data.shipping_fee,
   403	            "shipping_country": data.shipping_country,
   404	            "notes": data.notes,
   405	        },
   406	    )
   407	    row = result.mappings().first()
   408	
   409	    await record_audit_log(
   410	        db=db, tenant_id=tenant_id, user_id=current_user.id,
   411	        action="create", table_name="orders", record_id=row["id"],
   412	        new_data=data.model_dump(exclude_none=True, mode="json"),
   413	    )
   414	    await db.commit()
   415	    await invalidate_dashboard_cache(tenant_id)
   416	
   417	    return OrderResponse(**row)
   418	
   419	
   420	@router.patch("/orders/{order_id}", response_model=OrderResponse,
   421	              dependencies=[Depends(require_permission("orders.update"))])
   422	async def update_order(
   423	    order_id: int,
   424	    data: OrderUpdate,
   425	    db: AsyncSession = Depends(get_db),
   426	    tenant_id: int = Depends(get_current_tenant),
   427	    current_user: User = Depends(get_current_user),
   428	):
   429	    """注文情報を更新する（部分更新）"""
   430	    orders_t = tenant_table_ref(db, tenant_id, "orders")
   431	    old_result = await db.execute(
   432	        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
   433	        {"id": order_id},
   434	    )
   435	    old_row = old_result.mappings().first()
   436	    if not old_row:
   437	        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")
   438	
   439	    update_data = data.model_dump(exclude_unset=True)
   440	    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
   441	    if not update_data:
   442	        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")
   443	
   444	    if "status" in update_data and update_data["status"] is not None:
   445	        update_data["status"] = update_data["status"].value
   446	
   447	    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
   448	    update_data["id"] = order_id
   449	
   450	    result = await db.execute(
   451	        text(f"""
   452	            UPDATE {orders_t} SET {set_clauses}, updated_at = NOW()
   453	            WHERE id = :id
   454	            RETURNING {_SELECT_COLS}
   455	        """),
   456	        update_data,
   457	    )
   458	    row = result.mappings().first()
   459	
   460	    await record_audit_log(
   461	        db=db, tenant_id=tenant_id, user_id=current_user.id,
   462	        action="update", table_name="orders", record_id=order_id,
   463	        old_data=dict(old_row), new_data=update_data,
   464	    )
   465	    await db.commit()
   466	    await invalidate_dashboard_cache(tenant_id)
   467	
   468	    return OrderResponse(**row)

>>> nl -ba backend/app/schemas/order.py | sed -n "49,80p"
    49	class OrderCreate(BaseModel):
    50	    """注文登録リクエスト（Step 5d 以降は company_id + contact_id 必須）"""
    51	    company_id: int = Field(ge=1, description="会社ID")
    52	    contact_id: int = Field(ge=1, description="担当者ID")
    53	    deal_id: int | None = Field(default=None, ge=1)
    54	    invoice_id: int | None = Field(default=None, ge=1)
    55	    order_number: str = Field(min_length=1, max_length=100)
    56	    total_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    57	    currency: str = Field(default="JPY", max_length=10)
    58	    status: OrderStatus = Field(default=OrderStatus.awaiting_payment)
    59	    shipping_carrier: str | None = Field(default=None, max_length=50)
    60	    shipping_fee: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    61	    shipping_country: str | None = Field(default=None, max_length=100)
    62	    notes: str | None = Field(default=None, max_length=5000)
    63	
    64	
    65	class OrderUpdate(BaseModel):
    66	    # 注意: company_id / contact_id / deal_id / invoice_id は
    67	    # 作成後の変更を禁止（FK 整合性保護ポリシー）。router の _UPDATABLE_COLUMNS にも含まない。
    68	    # schema にも出さないことで API コントラクトと router 挙動を一致させる。
    69	    deal_id: int | None = Field(default=None, ge=1)
    70	    invoice_id: int | None = Field(default=None, ge=1)
    71	    order_number: str | None = Field(default=None, min_length=1, max_length=100)
    72	    total_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    73	    currency: str | None = Field(default=None, max_length=10)
    74	    status: OrderStatus | None = None
    75	    shipping_carrier: str | None = Field(default=None, max_length=50)
    76	    shipping_fee: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    77	    tracking_number: str | None = Field(default=None, max_length=200)
    78	    shipping_country: str | None = Field(default=None, max_length=100)
    79	    notes: str | None = Field(default=None, max_length=5000)
    80	

>>> grep -n "lead_id" backend/app/services/conv_log_writer.py backend/app/routers/conv_logs.py
backend/app/services/conv_log_writer.py:35:    lead_id: int | None,
backend/app/services/conv_log_writer.py:51:        lead_id: リード ID。案件未紐づけの場合も受け付ける（company_id は deals から補完）。
backend/app/services/conv_log_writer.py:65:    company_id = await _get_company_id_for_lead(db, lead_id) if lead_id else None
backend/app/services/conv_log_writer.py:66:    if contact_id is None and lead_id:
backend/app/services/conv_log_writer.py:67:        contact_id = await _get_contact_id_for_lead(db, lead_id)
backend/app/services/conv_log_writer.py:73:                tenant_id, lead_id, contact_id, company_id,
backend/app/services/conv_log_writer.py:77:                :tenant_id, :lead_id, :contact_id, :company_id,
backend/app/services/conv_log_writer.py:87:            "lead_id": lead_id,
backend/app/services/conv_log_writer.py:114:async def _get_company_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
backend/app/services/conv_log_writer.py:115:    """lead_id に紐づく最新案件の company_id を返す。案件がなければ None。"""
backend/app/services/conv_log_writer.py:120:            WHERE lead_id = :lead_id
backend/app/services/conv_log_writer.py:125:        {"lead_id": lead_id},
backend/app/services/conv_log_writer.py:131:async def _get_contact_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
backend/app/services/conv_log_writer.py:132:    """lead_id に紐づく primary contact の id を返す。なければ None。
backend/app/services/conv_log_writer.py:141:            WHERE lead_id = :lead_id
backend/app/services/conv_log_writer.py:145:        {"lead_id": lead_id},
backend/app/routers/conv_logs.py:4:  POST   /api/v1/leads/{lead_id}/conv-logs        — 手動記録の作成
backend/app/routers/conv_logs.py:5:  GET    /api/v1/leads/{lead_id}/conv-logs        — lead別 会話ログ一覧
backend/app/routers/conv_logs.py:6:  PATCH  /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録の編集
backend/app/routers/conv_logs.py:7:  DELETE /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録の論理削除
backend/app/routers/conv_logs.py:107:            f"SELECT id, lead_id, channel_type, direction, content_text, "
backend/app/routers/conv_logs.py:119:        "lead_id": row[1],
backend/app/routers/conv_logs.py:221:# POST /api/v1/leads/{lead_id}/conv-logs — 手動記録作成
backend/app/routers/conv_logs.py:226:    "/leads/{lead_id}/conv-logs",
backend/app/routers/conv_logs.py:232:    lead_id: int,
backend/app/routers/conv_logs.py:255:    # 重複チェック: 同一 lead_id + channel_type + content_text + occurred_at ±1h + deleted_at IS NULL
backend/app/routers/conv_logs.py:260:                f"WHERE lead_id = :lead_id "
backend/app/routers/conv_logs.py:268:                "lead_id": lead_id,
backend/app/routers/conv_logs.py:287:    company_id = await _get_company_id_for_lead(db, lead_id)
backend/app/routers/conv_logs.py:292:            f"(tenant_id, lead_id, company_id, channel_type, direction, content_text, "
backend/app/routers/conv_logs.py:294:            f"VALUES (:tenant_id, :lead_id, :company_id, :channel_type, :direction, :content_text, "
backend/app/routers/conv_logs.py:300:            "lead_id": lead_id,
backend/app/routers/conv_logs.py:314:            "lead_id": lead_id,
backend/app/routers/conv_logs.py:333:# GET /api/v1/leads/{lead_id}/conv-logs — 一覧取得
backend/app/routers/conv_logs.py:338:    "/leads/{lead_id}/conv-logs",
backend/app/routers/conv_logs.py:343:    lead_id: int,
backend/app/routers/conv_logs.py:355:            f"WHERE lead_id = :lead_id AND deleted_at IS NULL "
backend/app/routers/conv_logs.py:358:        {"lead_id": lead_id},
backend/app/routers/conv_logs.py:377:# PATCH /api/v1/leads/{lead_id}/conv-logs/{log_id} — 手動記録編集
backend/app/routers/conv_logs.py:382:    "/leads/{lead_id}/conv-logs/{log_id}",
backend/app/routers/conv_logs.py:387:    lead_id: int,
backend/app/routers/conv_logs.py:397:    if existing is None or existing.get("lead_id") != lead_id:
backend/app/routers/conv_logs.py:440:# DELETE /api/v1/leads/{lead_id}/conv-logs/{log_id} — 論理削除
backend/app/routers/conv_logs.py:445:    "/leads/{lead_id}/conv-logs/{log_id}",
backend/app/routers/conv_logs.py:451:    lead_id: int,
backend/app/routers/conv_logs.py:460:    if existing is None or existing.get("lead_id") != lead_id:

>>> nl -ba backend/app/services/conv_log_writer.py | sed -n "31,148p"
    31	async def write_conversation_log(
    32	    db: AsyncSession,
    33	    *,
    34	    tenant_id: int,
    35	    lead_id: int | None,
    36	    contact_id: int | None = None,
    37	    channel_type: str,
    38	    channel_identity: str | None = None,
    39	    direction: str,
    40	    sender: str | None = None,
    41	    content_text: str | None = None,
    42	    external_message_id: str | None = None,
    43	    raw_payload: dict[str, Any] | None = None,
    44	    occurred_at: datetime,
    45	) -> int | None:
    46	    """conversation_logs に 1 件挿入する。
    47	
    48	    Args:
    49	        db: テナントコンテキスト設定済みの AsyncSession。
    50	        tenant_id: テナント ID（RLS カラム用）。
    51	        lead_id: リード ID。案件未紐づけの場合も受け付ける（company_id は deals から補完）。
    52	        contact_id: コンタクト ID。省略時は contacts から lead の primary contact を自動補完。
    53	        channel_type: チャネル種別（'messenger' / 'instagram' / 'discord' / 'phone' 等）。
    54	        channel_identity: 送受信相手のチャネル固有 ID（PSID / Discord UID 等）。
    55	        direction: 'inbound'（受信）または 'outbound'（エコー含む送信）。
    56	        sender: 送信者識別子（PSID / 'staff' 等）。
    57	        content_text: メッセージ本文。
    58	        external_message_id: チャネル固有のメッセージ ID（重複排除キー）。
    59	        raw_payload: 生の webhook ペイロード（JSONB）。
    60	        occurred_at: メッセージの発生日時（タイムゾーン付き）。
    61	
    62	    Returns:
    63	        挿入された id。external_message_id 重複でスキップした場合は None。
    64	    """
    65	    company_id = await _get_company_id_for_lead(db, lead_id) if lead_id else None
    66	    if contact_id is None and lead_id:
    67	        contact_id = await _get_contact_id_for_lead(db, lead_id)
    68	    raw_json = json.dumps(raw_payload) if raw_payload else None
    69	
    70	    result = await db.execute(
    71	        text("""
    72	            INSERT INTO conversation_logs (
    73	                tenant_id, lead_id, contact_id, company_id,
    74	                channel_type, channel_identity, direction, sender,
    75	                content_text, external_message_id, raw_payload, occurred_at
    76	            ) VALUES (
    77	                :tenant_id, :lead_id, :contact_id, :company_id,
    78	                :channel_type, :channel_identity, :direction, :sender,
    79	                :content_text, :external_message_id, :raw_payload::jsonb, :occurred_at
    80	            )
    81	            ON CONFLICT (external_message_id) WHERE external_message_id IS NOT NULL
    82	            DO NOTHING
    83	            RETURNING id
    84	        """),
    85	        {
    86	            "tenant_id": tenant_id,
    87	            "lead_id": lead_id,
    88	            "contact_id": contact_id,
    89	            "company_id": company_id,
    90	            "channel_type": channel_type,
    91	            "channel_identity": channel_identity,
    92	            "direction": direction,
    93	            "sender": sender,
    94	            "content_text": content_text,
    95	            "external_message_id": external_message_id,
    96	            "raw_payload": raw_json,
    97	            "occurred_at": occurred_at,
    98	        },
    99	    )
   100	    new_id = result.scalar_one_or_none()
   101	    if new_id is None:
   102	        logger.debug(
   103	            "[conv_log_writer] duplicate skipped: channel=%s ext_id=%s",
   104	            channel_type, external_message_id,
   105	        )
   106	    else:
   107	        logger.info(
   108	            "[conv_log_writer] wrote id=%d channel=%s direction=%s",
   109	            new_id, channel_type, direction,
   110	        )
   111	    return new_id
   112	
   113	
   114	async def _get_company_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
   115	    """lead_id に紐づく最新案件の company_id を返す。案件がなければ None。"""
   116	    result = await db.execute(
   117	        text("""
   118	            SELECT company_id
   119	            FROM deals
   120	            WHERE lead_id = :lead_id
   121	              AND company_id IS NOT NULL
   122	            ORDER BY created_at DESC
   123	            LIMIT 1
   124	        """),
   125	        {"lead_id": lead_id},
   126	    )
   127	    row = result.first()
   128	    return int(row[0]) if row else None
   129	
   130	
   131	async def _get_contact_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
   132	    """lead_id に紐づく primary contact の id を返す。なければ None。
   133	
   134	    is_primary_contact=true を優先し、同 lead に複数 contact があるときは
   135	    最初に登録された（id が小さい）ものを採用する。
   136	    """
   137	    result = await db.execute(
   138	        text("""
   139	            SELECT id
   140	            FROM contacts
   141	            WHERE lead_id = :lead_id
   142	            ORDER BY is_primary_contact DESC, id ASC
   143	            LIMIT 1
   144	        """),
   145	        {"lead_id": lead_id},
   146	    )
   147	    row = result.first()
   148	    return int(row[0]) if row else None

>>> nl -ba backend/app/routers/conv_logs.py | sed -n "225,320p"
   225	@router.post(
   226	    "/leads/{lead_id}/conv-logs",
   227	    status_code=status.HTTP_201_CREATED,
   228	    summary="手動会話ログの作成",
   229	    tags=["conv-logs"],
   230	)
   231	async def create_conv_log(
   232	    lead_id: int,
   233	    body: ConvLogCreate,
   234	    current_user: User = Depends(get_current_user),
   235	    tenant_id: int = Depends(get_current_tenant),
   236	    db: AsyncSession = Depends(get_db),
   237	) -> dict[str, Any]:
   238	    await set_tenant_context(db, tenant_id)
   239	
   240	    # 入口排他: auto チャネルには手動入力不可
   241	    channel = await _get_channel_master(db, tenant_id, body.channel_type)
   242	    if channel is None:
   243	        raise HTTPException(
   244	            status_code=status.HTTP_400_BAD_REQUEST,
   245	            detail=f"チャネル '{body.channel_type}' はこのテナントで有効ではありません",
   246	        )
   247	    if channel["connection_type"] == "auto":
   248	        raise HTTPException(
   249	            status_code=status.HTTP_400_BAD_REQUEST,
   250	            detail=f"チャネル '{body.channel_type}' は自動連携チャネルのため手動入力は禁止です（SA-02-design §4）",
   251	        )
   252	
   253	    schema = f"tenant_{tenant_id:03d}"
   254	
   255	    # 重複チェック: 同一 lead_id + channel_type + content_text + occurred_at ±1h + deleted_at IS NULL
   256	    if not body.allow_duplicate:
   257	        dup_result = await db.execute(
   258	            text(
   259	                f"SELECT id, occurred_at FROM {schema}.conversation_logs "
   260	                f"WHERE lead_id = :lead_id "
   261	                f"  AND channel_type = :channel_type "
   262	                f"  AND content_text = :content_text "
   263	                f"  AND deleted_at IS NULL "
   264	                f"  AND occurred_at BETWEEN :oc_min AND :oc_max "
   265	                f"LIMIT 1"
   266	            ),
   267	            {
   268	                "lead_id": lead_id,
   269	                "channel_type": body.channel_type,
   270	                "content_text": body.content_text.strip(),
   271	                "oc_min": body.occurred_at - timedelta(hours=1),
   272	                "oc_max": body.occurred_at + timedelta(hours=1),
   273	            },
   274	        )
   275	        dup_row = dup_result.first()
   276	        if dup_row is not None:
   277	            raise HTTPException(
   278	                status_code=status.HTTP_409_CONFLICT,
   279	                detail={
   280	                    "code": "DUPLICATE_CONV_LOG",
   281	                    "existing_id": dup_row[0],
   282	                    "existing_occurred_at": dup_row[1].isoformat() if dup_row[1] else None,
   283	                    "message": "同一内容の会話ログが近接日時に既に存在します（重複登録防止）",
   284	                },
   285	            )
   286	
   287	    company_id = await _get_company_id_for_lead(db, lead_id)
   288	
   289	    result = await db.execute(
   290	        text(
   291	            f"INSERT INTO {schema}.conversation_logs "
   292	            f"(tenant_id, lead_id, company_id, channel_type, direction, content_text, "
   293	            f" occurred_at, recorded_by_user_id) "
   294	            f"VALUES (:tenant_id, :lead_id, :company_id, :channel_type, :direction, :content_text, "
   295	            f"        :occurred_at, :user_id) "
   296	            f"RETURNING id"
   297	        ),
   298	        {
   299	            "tenant_id": tenant_id,
   300	            "lead_id": lead_id,
   301	            "company_id": company_id,
   302	            "channel_type": body.channel_type,
   303	            "direction": body.direction,
   304	            "content_text": body.content_text,
   305	            "occurred_at": body.occurred_at,
   306	            "user_id": current_user.id,
   307	        },
   308	    )
   309	    log_id = result.scalar_one()
   310	    await record_audit_log(
   311	        db, tenant_id, current_user.id, "create", "conversation_logs",
   312	        record_id=log_id,
   313	        new_data={
   314	            "lead_id": lead_id,
   315	            "company_id": company_id,
   316	            "channel_type": body.channel_type,
   317	            "direction": body.direction,
   318	            "content_text": body.content_text,
   319	            "occurred_at": body.occurred_at.isoformat(),
   320	        },

>>> rg -n "initiative|channel_type|country|company_size|store_type|scale|business_type" backend/app/services/tenant.py migrations/*.sql | head -60
migrations/003_add_phase1_tenant_tables.sql:87:    estimated_scale VARCHAR(20),
migrations/003_add_phase1_tenant_tables.sql:139:ALTER TABLE {schema}.customers ADD COLUMN IF NOT EXISTS delivery_country VARCHAR(100);
backend/app/services/tenant.py:274:    country_code CHAR(2),
backend/app/services/tenant.py:354:    channel_type VARCHAR(30),
backend/app/services/tenant.py:355:    initiative VARCHAR(10),
backend/app/services/tenant.py:359:    estimated_scale VARCHAR(20),
backend/app/services/tenant.py:368:    country VARCHAR(100),
backend/app/services/tenant.py:413:    country_assignment_map JSONB,
backend/app/services/tenant.py:793:    country_code VARCHAR(3) NOT NULL,
backend/app/services/tenant.py:794:    country_name VARCHAR(100) NOT NULL,
backend/app/services/tenant.py:798:    UNIQUE(tenant_id, country_code, carrier)
backend/app/services/tenant.py:831:    shipping_country VARCHAR(100),
migrations/005_add_phase2_tenant_tables.sql:47:    country_code VARCHAR(3) NOT NULL,
migrations/005_add_phase2_tenant_tables.sql:48:    country_name VARCHAR(100) NOT NULL,
migrations/005_add_phase2_tenant_tables.sql:52:    UNIQUE(tenant_id, country_code, carrier)
migrations/005_add_phase2_tenant_tables.sql:84:    shipping_country VARCHAR(100),
migrations/005_add_phase2_tenant_tables.sql:164:ALTER TABLE {schema}.orders ADD COLUMN IF NOT EXISTS shipping_country VARCHAR(100);
migrations/015_replace_customers_schema.sql:149:    country_code CHAR(2),                              -- ISO 3166-1 alpha-2
migrations/015_replace_customers_schema.sql:157:COMMENT ON COLUMN {schema}.customer_addresses.country_code IS
migrations/009_add_phase4_tenant_tables.sql:11:    channel_type VARCHAR(20) NOT NULL DEFAULT 'discord',
migrations/030_create_company_contact_subtables.sql:55:                country_code CHAR(2),
migrations/046_adr015_lead_foundation.sql:12:--   §1/§2 AI 自動収集（Q1=国 / Q2=タイトル）   → leads.country / target_titles / ai_collection_state
migrations/046_adr015_lead_foundation.sql:52:ALTER TABLE {schema}.leads ADD COLUMN IF NOT EXISTS country VARCHAR(100);
migrations/046_adr015_lead_foundation.sql:103:COMMENT ON COLUMN {schema}.leads.country IS 'ADR-015 §2 Q1: 配送先の国（AI が会話から抽出）';
migrations/046_adr015_lead_foundation.sql:120:    -- 質問定義: [{"key":"country","prompt":"Which country are you shipping to?","required":true,"order":1}, ...]
migrations/046_adr015_lead_foundation.sql:127:    -- 担当者割り当て方法: 'manual' / 'round_robin' / 'country'
migrations/046_adr015_lead_foundation.sql:129:    -- 'country' の場合のマッピング: {"JP": 12, "US": 7, "default": 1}
migrations/046_adr015_lead_foundation.sql:130:    country_assignment_map      JSONB,
migrations/048_create_order_shipping_details.sql:52:    country_code VARCHAR(10),
migrations/20260602_150000_add_discord_scale_channels.sql:7:-- 用途: estimated_scale (Small/Large) に対応するチャンネルへの招待メッセージ送信先
migrations/20260604_090000_create_conversation_logs.sql:10:--   - channel_type: 'meta_messenger' / 'instagram' / 'discord' / 'email' 等
migrations/20260604_090000_create_conversation_logs.sql:41:                channel_type        VARCHAR(30) NOT NULL,
migrations/20260613_030000_funnel_leads_initiative_channel.sql:1:-- Migration 103: leads.initiative + leads.channel_type 追加、leads.source 廃止
migrations/20260613_030000_funnel_leads_initiative_channel.sql:5:--   リードの流入軸を「きっかけ（initiative）」と「チャネル（channel_type）」の2軸に整理する。
migrations/20260613_030000_funnel_leads_initiative_channel.sql:10:--   - 既存行はすべて channel_type='unknown', initiative=NULL に初期化（移行対応表の個別変換なし）
migrations/20260613_030000_funnel_leads_initiative_channel.sql:77:        -- ── 3. initiative カラム追加 ──────────────────────────────────────
migrations/20260613_030000_funnel_leads_initiative_channel.sql:80:             ADD COLUMN IF NOT EXISTS initiative VARCHAR(10)
migrations/20260613_030000_funnel_leads_initiative_channel.sql:81:                 CHECK (initiative IS NULL OR initiative IN (''outbound'', ''inbound''))',
migrations/20260613_030000_funnel_leads_initiative_channel.sql:85:        -- ── 4. channel_type カラム追加 ────────────────────────────────────
migrations/20260613_030000_funnel_leads_initiative_channel.sql:88:             ADD COLUMN IF NOT EXISTS channel_type VARCHAR(30)',
migrations/20260613_030000_funnel_leads_initiative_channel.sql:95:             SET channel_type = ''unknown''
migrations/20260613_030000_funnel_leads_initiative_channel.sql:96:             WHERE channel_type IS NULL',
migrations/20260613_030000_funnel_leads_initiative_channel.sql:99:        -- initiative はすべて NULL のまま（きっかけ不明）
migrations/20260613_030000_funnel_leads_initiative_channel.sql:110:            'CREATE INDEX IF NOT EXISTS idx_leads_initiative
migrations/20260613_030000_funnel_leads_initiative_channel.sql:111:             ON %I.leads (initiative)
migrations/20260613_030000_funnel_leads_initiative_channel.sql:112:             WHERE initiative IS NOT NULL',
migrations/20260613_030000_funnel_leads_initiative_channel.sql:117:            'CREATE INDEX IF NOT EXISTS idx_leads_channel_type
migrations/20260613_030000_funnel_leads_initiative_channel.sql:118:             ON %I.leads (channel_type)',
migrations/20260621_010000_create_countries_master.sql:4:--       lead.country / company.country_code の統制・backfill に繋ぐ。
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:64:                    WHEN cl.channel_type = 'meta_messenger' THEN 'messenger'
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:65:                    WHEN cl.channel_type = 'instagram' THEN 'instagram'
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:66:                    WHEN cl.channel_type = 'discord' THEN 'discord'
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:67:                    WHEN cl.channel_type = 'phone' THEN 'phone'
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:68:                    ELSE cl.channel_type

>>> rg -n "company_size|store_type|business_type" backend/app/services/tenant.py migrations/*.sql || echo "なし"
なし

>>> rg -n "close_reason|deal_close_reasons|lost_reason|won|lost" backend/app/services/tenant.py backend/app/routers/deals.py backend/app/schemas/deal.py
backend/app/schemas/deal.py:10:  closed_at, close_reason_memo, created_at, updated_at
backend/app/schemas/deal.py:18:  2026-06-12: PR1 — lost_reason / lost_reason_code 廃止（migration 102）
backend/app/schemas/deal.py:19:  2026-06-13: PR3 — closed_at, close_reason_memo, close_reasons 追加
backend/app/schemas/deal.py:32:    won = "won"
backend/app/schemas/deal.py:33:    lost = "lost"
backend/app/schemas/deal.py:43:    won = "won"
backend/app/schemas/deal.py:44:    lost = "lost"
backend/app/schemas/deal.py:74:    reason_id: int = Field(ge=1, description="close_reasons.id")
backend/app/schemas/deal.py:93:    close_reason_memo: str | None = Field(default=None, max_length=1000, description="成約/失注メモ")
backend/app/schemas/deal.py:94:    close_reasons: list[CloseReasonRef] | None = Field(default=None, description="成約/失注理由（主因1件必須）")
backend/app/schemas/deal.py:122:    close_reason_memo: str | None = None
backend/app/routers/deals.py:10:    currency, assigned_to, lost_reason 追加、require_permission統合）
backend/app/routers/deals.py:13:  2026-06-04: C-1 — lost_reason_code（選択式失注理由）追加
backend/app/routers/deals.py:44:    closed_at, close_reason_memo, created_at, updated_at
backend/app/routers/deals.py:52:    "close_reason_memo",
backend/app/routers/deals.py:55:_WON_LOST_STATUSES = {"won", "lost"}
backend/app/routers/deals.py:257:    close_reasons_input = raw_update.pop("close_reasons", None)
backend/app/routers/deals.py:259:    if not update_data and close_reasons_input is None:
backend/app/routers/deals.py:262:    # won/lost 遷移の検出と closed_at 自動セット
backend/app/routers/deals.py:271:        # close_reasons 必須チェック
backend/app/routers/deals.py:272:        if not close_reasons_input:
backend/app/routers/deals.py:275:                detail="成約/失注遷移時は close_reasons（主因1件必須）が必要です",
backend/app/routers/deals.py:277:        primary_count = sum(1 for r in close_reasons_input if r.get("is_primary"))
backend/app/routers/deals.py:283:        # close_reason_memo 必須チェック
backend/app/routers/deals.py:284:        if not update_data.get("close_reason_memo"):
backend/app/routers/deals.py:287:                detail="成約/失注遷移時は close_reason_memo が必要です",
backend/app/routers/deals.py:365:    # close_reasons 登録（won/lost 遷移時）
backend/app/routers/deals.py:366:    if close_reasons_input and is_closing:
backend/app/routers/deals.py:367:        close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")
backend/app/routers/deals.py:368:        deal_close_reasons_t = tenant_table_ref(db, tenant_id, "deal_close_reasons")
backend/app/routers/deals.py:371:            text(f"DELETE FROM {deal_close_reasons_t} WHERE deal_id = :did"),
backend/app/routers/deals.py:374:        for reason in close_reasons_input:
backend/app/routers/deals.py:377:                text(f"SELECT id FROM {close_reasons_t} WHERE id = :rid AND is_active = true"),
backend/app/routers/deals.py:383:                    detail=f"close_reason id={reason['reason_id']} が見つかりません",
backend/app/routers/deals.py:387:                    INSERT INTO {deal_close_reasons_t} (deal_id, reason_id, is_primary)

>>> nl -ba backend/app/services/tenant.py | sed -n "423,444p"
   423	CREATE TABLE IF NOT EXISTS {schema}.deals (
   424	    id SERIAL PRIMARY KEY,
   425	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   426	    deal_code VARCHAR(20),
   427	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   428	    --   新テナント作成時も customer_id 列を作らない（新 B2B モデル唯一の正）。
   429	    -- CONSTRAINT 名は migration 032 と合わせる（verify の FK 存在 check が新旧テナントで揃うように）
   430	    company_id INTEGER CONSTRAINT fk_deals_company REFERENCES {schema}.companies(id),
   431	    contact_id INTEGER CONSTRAINT fk_deals_contact REFERENCES {schema}.contacts(id),
   432	    lead_id INTEGER REFERENCES {schema}.leads(id),
   433	    title VARCHAR(255) NOT NULL,
   434	    amount NUMERIC(15, 2),
   435	    currency VARCHAR(10) DEFAULT 'JPY',
   436	    status VARCHAR(50) DEFAULT 'open',
   437	    stage VARCHAR(50) DEFAULT 'open',
   438	    probability INTEGER DEFAULT 10,
   439	    assigned_to INTEGER,
   440	    expected_close_date DATE,
   441	    notes TEXT,
   442	    created_at TIMESTAMPTZ DEFAULT NOW(),
   443	    updated_at TIMESTAMPTZ DEFAULT NOW()
   444	);

>>> nl -ba migrations/20260613_020000_funnel_close_reasons.sql | sed -n "1,122p"
     1	-- Migration 102: 成約・失注理由マスタ（ファネルダッシュボード PR1）
     2	--
     3	-- 目的:
     4	--   テナント別の成約/失注理由マスタ（close_reasons）と
     5	--   商談との中間表（deal_close_reasons）を作成する。
     6	--   deals.close_reason_memo を追加し、deals.lost_reason_code / deals.lost_reason を廃止する。
     7	--
     8	-- 設計判断:
     9	--   - ADR-138 §D1-2: クリーンスレート方針（PO宣言 2026-06-12）
    10	--   - lost_reason_code (enum 7値): 全テナント実データ 0件確認済み → 移行なし・カラムごと廃止
    11	--   - lost_reason (VARCHAR 255): 全テナント実データ 0件確認済み → close_reason_memo に置換
    12	--   - デフォルト理由は全テナントに自動投入
    13	--
    14	-- 冪等性:
    15	--   CREATE TABLE IF NOT EXISTS / DROP COLUMN IF EXISTS / INSERT ... ON CONFLICT DO NOTHING
    16	-- 適用対象: 全テナント
    17	-- 作成日: 2026-06-12
    18	-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2.2
    19	--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1-2
    20	
    21	DO $$
    22	DECLARE
    23	    schema_rec RECORD;
    24	    constraint_rec RECORD;
    25	BEGIN
    26	    FOR schema_rec IN
    27	        SELECT nspname AS schema_name
    28	        FROM pg_namespace
    29	        WHERE nspname ~ '^tenant_\d+$'
    30	        ORDER BY nspname
    31	    LOOP
    32	        RAISE NOTICE 'Migration 102: processing schema %', schema_rec.schema_name;
    33	
    34	        -- ── 1. close_reasons マスタテーブル ──────────────────────────────────
    35	        EXECUTE format($sql$
    36	            CREATE TABLE IF NOT EXISTS %I.close_reasons (
    37	                id         SERIAL PRIMARY KEY,
    38	                type       VARCHAR(10) NOT NULL CHECK (type IN ('won', 'lost')),
    39	                label      TEXT        NOT NULL,
    40	                sort_order INTEGER     NOT NULL DEFAULT 0,
    41	                is_active  BOOLEAN     NOT NULL DEFAULT true,
    42	                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    43	                UNIQUE (type, label)
    44	            )
    45	        $sql$, schema_rec.schema_name);
    46	
    47	        -- ── 2. deal_close_reasons 中間表（主因1 + 副因複数）────────────────
    48	        EXECUTE format($sql$
    49	            CREATE TABLE IF NOT EXISTS %I.deal_close_reasons (
    50	                id         SERIAL PRIMARY KEY,
    51	                deal_id    INTEGER NOT NULL
    52	                               REFERENCES %I.deals(id) ON DELETE CASCADE,
    53	                reason_id  INTEGER NOT NULL
    54	                               REFERENCES %I.close_reasons(id),
    55	                is_primary BOOLEAN NOT NULL DEFAULT false,
    56	                UNIQUE (deal_id, reason_id)
    57	            )
    58	        $sql$,
    59	            schema_rec.schema_name,
    60	            schema_rec.schema_name,
    61	            schema_rec.schema_name
    62	        );
    63	
    64	        EXECUTE format(
    65	            'CREATE INDEX IF NOT EXISTS idx_deal_close_reasons_deal
    66	             ON %I.deal_close_reasons (deal_id)',
    67	            schema_rec.schema_name
    68	        );
    69	
    70	        -- ── 3. deals.close_reason_memo 追加 ──────────────────────────────────
    71	        EXECUTE format(
    72	            'ALTER TABLE %I.deals
    73	             ADD COLUMN IF NOT EXISTS close_reason_memo TEXT',
    74	            schema_rec.schema_name
    75	        );
    76	
    77	        -- ── 4. deals.lost_reason_code 廃止（実データ 0件確認済み） ───────────
    78	        EXECUTE format(
    79	            'ALTER TABLE %I.deals
    80	             DROP COLUMN IF EXISTS lost_reason_code',
    81	            schema_rec.schema_name
    82	        );
    83	
    84	        -- ── 5. deals.lost_reason 廃止（実データ 0件確認済み・close_reason_memo に置換） ──
    85	        EXECUTE format(
    86	            'ALTER TABLE %I.deals
    87	             DROP COLUMN IF EXISTS lost_reason',
    88	            schema_rec.schema_name
    89	        );
    90	
    91	        -- ── 6. デフォルト理由を投入 ──────────────────────────────────────────
    92	        -- 成約理由
    93	        EXECUTE format($sql$
    94	            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
    95	                ('won', '在庫・品揃え',  1),
    96	                ('won', '価格',          2),
    97	                ('won', '安心感',        3),
    98	                ('won', 'スピード',      4),
    99	                ('won', '取引条件',      5),
   100	                ('won', '人・関係',      6),
   101	                ('won', 'その他',       99)
   102	            ON CONFLICT (type, label) DO NOTHING
   103	        $sql$, schema_rec.schema_name);
   104	
   105	        -- 失注理由
   106	        EXECUTE format($sql$
   107	            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
   108	                ('lost', '価格が合わなかった',             1),
   109	                ('lost', '在庫・品揃えで応えられなかった', 2),
   110	                ('lost', '不安を解消できなかった',         3),
   111	                ('lost', '対応が遅れた',                   4),
   112	                ('lost', '取引条件が合わなかった',         5),
   113	                ('lost', '連絡が途絶えた',                 6),
   114	                ('lost', 'お客様側の事情',                 7),
   115	                ('lost', 'その他',                        99)
   116	            ON CONFLICT (type, label) DO NOTHING
   117	        $sql$, schema_rec.schema_name);
   118	
   119	    END LOOP;
   120	    RAISE NOTICE 'Migration 102: complete';
   121	END
   122	$$;

>>> nl -ba backend/app/routers/deals.py | sed -n "250,403p"
   250	        {"id": deal_id},
   251	    )
   252	    old_row = old_result.mappings().first()
   253	    if not old_row:
   254	        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商談が見つかりません")
   255	
   256	    raw_update = data.model_dump(exclude_unset=True)
   257	    close_reasons_input = raw_update.pop("close_reasons", None)
   258	    update_data = {k: v for k, v in raw_update.items() if k in _UPDATABLE_COLUMNS}
   259	    if not update_data and close_reasons_input is None:
   260	        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")
   261	
   262	    # won/lost 遷移の検出と closed_at 自動セット
   263	    new_status_raw = update_data.get("status")
   264	    new_status = new_status_raw.value if new_status_raw is not None else None
   265	    old_status = old_row["status"]
   266	    is_closing = new_status in _WON_LOST_STATUSES and old_status not in _WON_LOST_STATUSES
   267	
   268	    if is_closing:
   269	        # closed_at を自動セット
   270	        update_data["closed_at_now"] = True  # UPDATE 句で NOW() を埋め込む（後で処理）
   271	        # close_reasons 必須チェック
   272	        if not close_reasons_input:
   273	            raise HTTPException(
   274	                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
   275	                detail="成約/失注遷移時は close_reasons（主因1件必須）が必要です",
   276	            )
   277	        primary_count = sum(1 for r in close_reasons_input if r.get("is_primary"))
   278	        if primary_count != 1:
   279	            raise HTTPException(
   280	                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
   281	                detail=f"主因（is_primary: true）はちょうど1件必要です（{primary_count}件指定）",
   282	            )
   283	        # close_reason_memo 必須チェック
   284	        if not update_data.get("close_reason_memo"):
   285	            raise HTTPException(
   286	                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
   287	                detail="成約/失注遷移時は close_reason_memo が必要です",
   288	            )
   289	
   290	    # company_id / contact_id の整合性検証（Step 5d 以降）
   291	    has_company_update = "company_id" in raw_update
   292	    has_contact_update = "contact_id" in raw_update
   293	
   294	    if has_company_update or has_contact_update:
   295	        target_company_id = raw_update["company_id"] if has_company_update else old_row["company_id"]
   296	        target_contact_id = raw_update["contact_id"] if has_contact_update else old_row["contact_id"]
   297	
   298	        if target_contact_id is not None:
   299	            contact_check = await db.execute(
   300	                text(f"SELECT company_id FROM {contacts_t} WHERE id = :id"),
   301	                {"id": target_contact_id},
   302	            )
   303	            contact_row = contact_check.first()
   304	            if not contact_row:
   305	                raise HTTPException(
   306	                    status_code=status.HTTP_404_NOT_FOUND,
   307	                    detail="指定された担当者が見つかりません",
   308	                )
   309	            if target_company_id is not None and contact_row[0] != target_company_id:
   310	                raise HTTPException(
   311	                    status_code=status.HTTP_400_BAD_REQUEST,
   312	                    detail="指定された担当者は指定会社に所属していません",
   313	                )
   314	            # company_id を明示更新せず contact のみ更新 → contact 側の company_id を採用
   315	            if target_company_id is None and contact_row[0] is not None:
   316	                update_data["company_id"] = contact_row[0]
   317	
   318	        elif target_company_id is not None and has_company_update:
   319	            company_check = await db.execute(
   320	                text(f"SELECT id FROM {companies_t} WHERE id = :id"),
   321	                {"id": target_company_id},
   322	            )
   323	            if not company_check.first():
   324	                raise HTTPException(
   325	                    status_code=status.HTTP_404_NOT_FOUND,
   326	                    detail="指定された会社が見つかりません",
   327	                )
   328	
   329	    # lead_id を更新する場合は存在確認（指定された場合のみ、NULL クリアは許容）
   330	    if "lead_id" in raw_update and raw_update["lead_id"] is not None:
   331	        lead_check = await db.execute(
   332	            text(f"SELECT id FROM {leads_t} WHERE id = :id"),
   333	            {"id": raw_update["lead_id"]},
   334	        )
   335	        if not lead_check.first():
   336	            raise HTTPException(
   337	                status_code=status.HTTP_404_NOT_FOUND,
   338	                detail="指定されたリードが見つかりません",
   339	            )
   340	
   341	    # Enum型の値を文字列に変換
   342	    for key in ("status", "stage", "currency"):
   343	        if key in update_data and update_data[key] is not None:
   344	            update_data[key] = update_data[key].value
   345	
   346	    # closed_at_now フラグを SET 句に変換
   347	    use_closed_at_now = update_data.pop("closed_at_now", False)
   348	    set_clauses_parts = [f"{k} = :{k}" for k in update_data]
   349	    if use_closed_at_now:
   350	        set_clauses_parts.append("closed_at = NOW()")
   351	    set_clauses_parts.append("updated_at = NOW()")
   352	    set_clauses = ", ".join(set_clauses_parts)
   353	    update_data["id"] = deal_id
   354	
   355	    result = await db.execute(
   356	        text(f"""
   357	            UPDATE {deals_t} SET {set_clauses}
   358	            WHERE id = :id
   359	            RETURNING {_DEAL_COLUMNS}
   360	        """),
   361	        update_data,
   362	    )
   363	    row = result.mappings().first()
   364	
   365	    # close_reasons 登録（won/lost 遷移時）
   366	    if close_reasons_input and is_closing:
   367	        close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")
   368	        deal_close_reasons_t = tenant_table_ref(db, tenant_id, "deal_close_reasons")
   369	        # 既存の理由をクリア（再遷移の場合でも冪等に）
   370	        await db.execute(
   371	            text(f"DELETE FROM {deal_close_reasons_t} WHERE deal_id = :did"),
   372	            {"did": deal_id},
   373	        )
   374	        for reason in close_reasons_input:
   375	            # reason_id の存在確認
   376	            reason_check = await db.execute(
   377	                text(f"SELECT id FROM {close_reasons_t} WHERE id = :rid AND is_active = true"),
   378	                {"rid": reason["reason_id"]},
   379	            )
   380	            if not reason_check.first():
   381	                raise HTTPException(
   382	                    status_code=status.HTTP_400_BAD_REQUEST,
   383	                    detail=f"close_reason id={reason['reason_id']} が見つかりません",
   384	                )
   385	            await db.execute(
   386	                text(f"""
   387	                    INSERT INTO {deal_close_reasons_t} (deal_id, reason_id, is_primary)
   388	                    VALUES (:did, :rid, :is_primary)
   389	                    ON CONFLICT (deal_id, reason_id) DO UPDATE SET is_primary = EXCLUDED.is_primary
   390	                """),
   391	                {"did": deal_id, "rid": reason["reason_id"], "is_primary": reason["is_primary"]},
   392	            )
   393	
   394	    await record_audit_log(
   395	        db=db, tenant_id=tenant_id, user_id=current_user.id,
   396	        action="update", table_name="deals", record_id=deal_id,
   397	        old_data=dict(old_row), new_data=update_data,
   398	    )
   399	    await db.commit()
   400	    await reset_tenant_context(db, tenant_id)
   401	    await invalidate_dashboard_cache(tenant_id)
   402	
   403	    return DealResponse(**row)

>>> rg -rln "累計\\|受注回数\\|最終取引\\|company detail\\|CompanyDetail" frontend/src | head

>>> nl -ba frontend/src/pages/company-detail/CompanyBasicTab.tsx | sed -n "1,170p"
     1	/**
     2	 * 会社詳細 — 基本情報タブ。
     3	 * 編集フォームと pending_dedup_review 解消セクションを含む。
     4	 */
     5	
     6	import { FormEvent } from "react";
     7	import { useTranslation } from "react-i18next";
     8	import type { BasicFormState, Company } from "./company-detail.types";
     9	
    10	interface Props {
    11	  basicForm: BasicFormState;
    12	  setBasicForm: (f: BasicFormState) => void;
    13	  basicDirty: boolean;
    14	  setBasicDirty: (v: boolean) => void;
    15	  basicSubmitting: boolean;
    16	  handleBasicSubmit: (e: FormEvent) => void;
    17	  canEdit: boolean;
    18	  canMerge: boolean;
    19	  company: Company;
    20	  dedupSubmitting: boolean;
    21	  setDedupConfirmOpen: (v: boolean) => void;
    22	  setMergeModalOpen: (v: boolean) => void;
    23	}
    24	
    25	export function CompanyBasicTab({
    26	  basicForm, setBasicForm, basicDirty, setBasicDirty, basicSubmitting,
    27	  handleBasicSubmit, canEdit, canMerge, company, dedupSubmitting,
    28	  setDedupConfirmOpen, setMergeModalOpen,
    29	}: Props) {
    30	  const { t } = useTranslation();
    31	
    32	  return (
    33	    <form onSubmit={handleBasicSubmit} className="form-grid">
    34	      <div className="form-row"><label>{t("common.name")} *</label>
    35	        <input required disabled={!canEdit} value={basicForm.name}
    36	          onChange={(e) => { setBasicForm({ ...basicForm, name: e.target.value }); setBasicDirty(true); }} />
    37	      </div>
    38	      <div className="form-row"><label>{t("companies.nameEn")}</label>
    39	        <input disabled={!canEdit} value={basicForm.name_en}
    40	          onChange={(e) => { setBasicForm({ ...basicForm, name_en: e.target.value }); setBasicDirty(true); }} />
    41	      </div>
    42	      <div className="form-row"><label>{t("companies.industry")}</label>
    43	        <input disabled={!canEdit} value={basicForm.industry}
    44	          onChange={(e) => { setBasicForm({ ...basicForm, industry: e.target.value }); setBasicDirty(true); }} />
    45	      </div>
    46	      <div className="form-row"><label>{t("companies.website")}</label>
    47	        <input disabled={!canEdit} value={basicForm.website}
    48	          onChange={(e) => { setBasicForm({ ...basicForm, website: e.target.value }); setBasicDirty(true); }} />
    49	      </div>
    50	      <div className="form-row"><label>{t("companies.priorityFocus")}</label>
    51	        <input disabled={!canEdit} value={basicForm.priority_focus}
    52	          onChange={(e) => { setBasicForm({ ...basicForm, priority_focus: e.target.value }); setBasicDirty(true); }} />
    53	      </div>
    54	      <div className="form-row"><label>{t("companies.perOrderAmount")}</label>
    55	        <input disabled={!canEdit} value={basicForm.per_order_amount}
    56	          onChange={(e) => { setBasicForm({ ...basicForm, per_order_amount: e.target.value }); setBasicDirty(true); }} />
    57	      </div>
    58	      <div className="form-row"><label>{t("companies.monthlyFrequency")}</label>
    59	        <input type="number" min="0" disabled={!canEdit} value={basicForm.monthly_frequency}
    60	          onChange={(e) => { setBasicForm({ ...basicForm, monthly_frequency: e.target.value }); setBasicDirty(true); }} />
    61	      </div>
    62	      <div className="form-row"><label>{t("companies.monthlyForecast")}</label>
    63	        <input disabled={!canEdit} value={basicForm.monthly_forecast}
    64	          onChange={(e) => { setBasicForm({ ...basicForm, monthly_forecast: e.target.value }); setBasicDirty(true); }} />
    65	      </div>
    66	      <div className="form-row"><label>{t("companies.billingDisplayName")}</label>
    67	        <input disabled={!canEdit} value={basicForm.billing_display_name}
    68	          onChange={(e) => { setBasicForm({ ...basicForm, billing_display_name: e.target.value }); setBasicDirty(true); }} />
    69	      </div>
    70	      <div className="form-row"><label>{t("companies.paymentRecipientName")}</label>
    71	        <input disabled={!canEdit} value={basicForm.payment_recipient_name}
    72	          onChange={(e) => { setBasicForm({ ...basicForm, payment_recipient_name: e.target.value }); setBasicDirty(true); }} />
    73	      </div>
    74	      <div className="form-row"><label>{t("companies.fedexAccount")}</label>
    75	        <input disabled={!canEdit} value={basicForm.fedex_account}
    76	          onChange={(e) => { setBasicForm({ ...basicForm, fedex_account: e.target.value }); setBasicDirty(true); }} />
    77	      </div>
    78	      <div className="form-row"><label>{t("companies.shippingNote")}</label>
    79	        <textarea disabled={!canEdit} value={basicForm.shipping_note}
    80	          onChange={(e) => { setBasicForm({ ...basicForm, shipping_note: e.target.value }); setBasicDirty(true); }} />
    81	      </div>
    82	      <div className="form-row"><label>{t("common.status")}</label>
    83	        <select disabled={!canEdit} value={basicForm.status}
    84	          onChange={(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}>
    85	          <option value="active">active</option>
    86	          <option value="inactive">inactive</option>
    87	          <option value="archived">archived</option>
    88	          <option value="pending_dedup_review">pending_dedup_review</option>
    89	        </select>
    90	      </div>
    91	      <div className="form-row"><label>{t("common.notes")}</label>
    92	        <textarea disabled={!canEdit} value={basicForm.notes}
    93	          onChange={(e) => { setBasicForm({ ...basicForm, notes: e.target.value }); setBasicDirty(true); }} />
    94	      </div>
    95	      {canEdit && (
    96	        <div className="form-actions">
    97	          <button type="submit" className="btn-primary" disabled={!basicDirty || basicSubmitting}>
    98	            {basicSubmitting ? t("common.saving") : t("companies.saveBasicInfo")}
    99	          </button>
   100	        </div>
   101	      )}
   102	
   103	      {/* v_company_stats: 読み取り専用集計エリア */}
   104	      <div className="form-section-divider" />
   105	      <div className="form-row">
   106	        <label>{t("company.stats.total_deal_amount")}</label>
   107	        <span className="read-only-value">
   108	          {company.total_deal_amount != null
   109	            ? Number(company.total_deal_amount).toLocaleString("ja-JP", { style: "currency", currency: "JPY" })
   110	            : "—"}
   111	        </span>
   112	      </div>
   113	      <div className="form-row">
   114	        <label>{t("company.stats.deal_count")}</label>
   115	        <span className="read-only-value">
   116	          {company.deal_count != null ? company.deal_count : "—"}
   117	        </span>
   118	      </div>
   119	      <div className="form-row">
   120	        <label>{t("company.stats.conversation_count")}</label>
   121	        <span className="read-only-value">
   122	          {company.conversation_count != null ? company.conversation_count : "—"}
   123	        </span>
   124	      </div>
   125	      <div className="form-row">
   126	        <label>{t("company.stats.last_conversation_at")}</label>
   127	        <span className="read-only-value">
   128	          {company.last_conversation_at
   129	            ? new Date(company.last_conversation_at).toLocaleString("ja-JP")
   130	            : "—"}
   131	        </span>
   132	      </div>
   133	
   134	      {/* PR #145 Q2: pending_dedup_review 解消セクション */}
   135	      {canEdit && company.status === "pending_dedup_review" && (
   136	        <div className="dedup-resolve-section">
   137	          <h3>{t("companies.dedupResolveTitle")}</h3>
   138	          <p>{t("companies.dedupResolveDesc")}</p>
   139	          <div className="dedup-resolve-actions">
   140	            <button
   141	              type="button"
   142	              className="btn-primary"
   143	              onClick={() => setDedupConfirmOpen(true)}
   144	              disabled={dedupSubmitting || basicDirty}
   145	              title={basicDirty ? t("companies.dedupUnsavedHint") : ""}
   146	            >
   147	              {t("companies.dedupConfirmAsDistinct")}
   148	            </button>
   149	            <button
   150	              type="button"
   151	              className="btn-danger"
   152	              onClick={() => setMergeModalOpen(true)}
   153	              disabled={!canMerge || dedupSubmitting || basicDirty}
   154	              title={
   155	                !canMerge
   156	                  ? t("companies.dedupMergeNoPermission")
   157	                  : basicDirty
   158	                    ? t("companies.dedupUnsavedHint")
   159	                    : t("companies.dedupMergeHint")
   160	              }
   161	            >
   162	              {t("companies.dedupMergeLabel")}
   163	            </button>
   164	          </div>
   165	        </div>
   166	      )}
   167	    </form>
   168	  );
   169	}

>>> nl -ba frontend/src/pages/company-detail/CompanyDetailPage.tsx | sed -n "1,260p"
     1	/**
     2	 * 会社詳細ページ（Phase 1-B-2 Step 5c-2）。
     3	 *
     4	 * URL: /companies/:id
     5	 * 5 タブ: 基本情報 / 住所（multi_branch）/ 担当者 / 販売チャネル / Discord
     6	 *
     7	 * このファイルはオーケストレーターのみ。ロジックは useCompanyDetail、
     8	 * UI は各タブコンポーネントに分割済み。
     9	 */
    10	
    11	import { useState } from "react";
    12	import { useParams, useNavigate } from "react-router-dom";
    13	import { useTranslation } from "react-i18next";
    14	import { usePermissions } from "../../hooks/usePermissions";
    15	import { api } from "../../lib/api";
    16	import { Button } from "../../components/Button";
    17	import ConfirmModal from "../../components/ConfirmModal";
    18	import MergeCompanyModal from "../../components/MergeCompanyModal";
    19	import { useCompanyDetail } from "./useCompanyDetail";
    20	import { CompanyBasicTab } from "./CompanyBasicTab";
    21	import { CompanyAddressesTab } from "./CompanyAddressesTab";
    22	import { CompanyContactsTab } from "./CompanyContactsTab";
    23	import { CompanyChannelsTab } from "./CompanyChannelsTab";
    24	import { CompanyDiscordTab } from "./CompanyDiscordTab";
    25	import { CompanyConvLogsTab } from "./CompanyConvLogsTab";
    26	import { CompanyAddressModal } from "./CompanyAddressModal";
    27	import { typeLabel } from "./company-detail.types";
    28	
    29	export default function CompanyDetailPage() {
    30	  const { t } = useTranslation();
    31	  const { id } = useParams<{ id: string }>();
    32	  const navigate = useNavigate();
    33	  const { hasPermission } = usePermissions();
    34	  const canEdit = hasPermission("customers.update");
    35	  // A-4: 会社マージは customers.delete 権限相当
    36	  const canMerge = hasPermission("customers.delete");
    37	  // ADR-SA-03 + ADR-127: 登録リンク発行（register / add_address / change_billing）
    38	  const [regLinkUrl, setRegLinkUrl] = useState<string | null>(null);
    39	  const [regLinkLoading, setRegLinkLoading] = useState(false);
    40	  const [addrLinkUrl, setAddrLinkUrl] = useState<string | null>(null);
    41	  const [addrLinkLoading, setAddrLinkLoading] = useState(false);
    42	  const [changeBillingLinkUrl, setChangeBillingLinkUrl] = useState<string | null>(null);
    43	  const [changeBillingLinkLoading, setChangeBillingLinkLoading] = useState(false);
    44	
    45	  const state = useCompanyDetail(id);
    46	  const {
    47	    company, contacts, loading, error,
    48	    activeTab, setActiveTab,
    49	    basicForm, setBasicForm, basicDirty, setBasicDirty, basicSubmitting,
    50	    channelsText, setChannelsText, channelsDirty, setChannelsDirty, channelsSubmitting,
    51	    addrModalOpen, setAddrModalOpen,
    52	    addrForm, setAddrForm,
    53	    addrDeleteTarget, setAddrDeleteTarget,
    54	    contactModalOpen, setContactModalOpen,
    55	    contactForm, setContactForm, contactSubmitting,
    56	    contactDeleteTarget, setContactDeleteTarget,
    57	    discordForm, setDiscordForm, discordDirty, setDiscordDirty, discordSubmitting,
    58	    dedupConfirmOpen, setDedupConfirmOpen, dedupSubmitting,
    59	    mergeModalOpen, setMergeModalOpen,
    60	    handleBasicSubmit, handleChannelsSubmit,
    61	    submitAddresses,
    62	    openAddressNew, openAddressEdit,
    63	    handleAddressTypeChange,
    64	    openContactNew, openContactEdit,
    65	    handleContactSubmit, handleContactDelete,
    66	    handleDiscordSubmit, handleDiscordDelete,
    67	    handleResolveAsDistinct, handleAddressDelete,
    68	    load,
    69	  } = state;
    70	
    71	  if (loading) return <div className="page-container"><p>{t("common.loading")}</p></div>;
    72	  if (!company) {
    73	    return (
    74	      <div className="page-container">
    75	        <p>{t("common.noData")}</p>
    76	        <Button variant="secondary" onClick={() => navigate("/companies")}>{t("common.back")}</Button>
    77	      </div>
    78	    );
    79	  }
    80	
    81	  const handleGenerateRegLink = async () => {
    82	    if (!company.lead_id) return;
    83	    setRegLinkLoading(true);
    84	    try {
    85	      const res = await api.post("/registration-tokens", {
    86	        lead_id: company.lead_id,
    87	        type: "register",
    88	      }) as { registration_url: string };
    89	      setRegLinkUrl(res.registration_url);
    90	    } catch {
    91	      // noop
    92	    } finally {
    93	      setRegLinkLoading(false);
    94	    }
    95	  };
    96	
    97	  const handleGenerateAddrLink = async () => {
    98	    if (!company.lead_id) return;
    99	    setAddrLinkLoading(true);
   100	    try {
   101	      const res = await api.post("/registration-tokens", {
   102	        lead_id: company.lead_id,
   103	        type: "add_address",
   104	      }) as { registration_url: string };
   105	      setAddrLinkUrl(res.registration_url);
   106	    } catch {
   107	      // noop
   108	    } finally {
   109	      setAddrLinkLoading(false);
   110	    }
   111	  };
   112	
   113	  const handleGenerateChangeBillingLink = async () => {
   114	    if (!company.lead_id) return;
   115	    setChangeBillingLinkLoading(true);
   116	    try {
   117	      const res = await api.post("/registration-tokens", {
   118	        lead_id: company.lead_id,
   119	        type: "change_billing",
   120	      }) as { registration_url: string };
   121	      setChangeBillingLinkUrl(res.registration_url);
   122	    } catch {
   123	      // noop
   124	    } finally {
   125	      setChangeBillingLinkLoading(false);
   126	    }
   127	  };
   128	
   129	  const billingAddresses = company.addresses.filter((a) => a.address_type === "billing");
   130	  const deliveryAddresses = company.addresses.filter((a) => a.address_type === "delivery");
   131	  // ADR-127 §4: 第1層ゲート — 登録済み（billing is_default=true が存在）なら register 発行を無効化
   132	  const isAlreadyRegistered = billingAddresses.some((a) => a.is_default);
   133	
   134	  const switchTab = (tab: typeof activeTab) => {
   135	    if ((basicDirty || channelsDirty) && tab !== activeTab) {
   136	      if (!window.confirm(t("companies.unsavedChangesConfirm"))) return;
   137	      setBasicForm(state.basicForm ? { ...state.basicForm } : null);
   138	      setChannelsText(company.sales_channels.join(", "));
   139	      setBasicDirty(false);
   140	      setChannelsDirty(false);
   141	    }
   142	    setActiveTab(tab);
   143	  };
   144	
   145	  return (
   146	    <div className="page-container">
   147	      <div className="page-header">
   148	        <div>
   149	          <Button size="sm" variant="secondary" onClick={() => navigate("/companies")}>&larr; {t("common.back")}</Button>
   150	          <h1>{company.name}</h1>
   151	        </div>
   152	        <div className="page-header-actions">
   153	          {canEdit && company.lead_id && (
   154	            <>
   155	              <Button
   156	                size="sm"
   157	                onClick={handleGenerateRegLink}
   158	                disabled={regLinkLoading || isAlreadyRegistered}
   159	                title={isAlreadyRegistered ? t("registration.alreadyRegisteredGate") : undefined}
   160	              >
   161	                {regLinkLoading ? t("common.loading") : isAlreadyRegistered ? t("registration.registeredLabel") : t("registration.generateLink")}
   162	              </Button>
   163	              {isAlreadyRegistered && (
   164	                <>
   165	                  <Button
   166	                    size="sm"
   167	                    variant="secondary"
   168	                    onClick={handleGenerateAddrLink}
   169	                    disabled={addrLinkLoading}
   170	                  >
   171	                    {addrLinkLoading ? t("common.loading") : t("registration.generateAddressLink")}
   172	                  </Button>
   173	                  <Button
   174	                    size="sm"
   175	                    variant="secondary"
   176	                    onClick={handleGenerateChangeBillingLink}
   177	                    disabled={changeBillingLinkLoading}
   178	                  >
   179	                    {changeBillingLinkLoading ? t("common.loading") : t("registration.generateChangeBillingLink")}
   180	                  </Button>
   181	                </>
   182	              )}
   183	            </>
   184	          )}
   185	          <span className={`status-badge status-${company.status}`}>{company.status}</span>
   186	        </div>
   187	      </div>
   188	
   189	      {regLinkUrl && (
   190	        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
   191	          {t("registration.linkGenerated")}: <a href={regLinkUrl} target="_blank" rel="noopener noreferrer">{regLinkUrl}</a>
   192	          <Button size="sm" variant="secondary" style={{ marginLeft: "var(--spacing-2)" }}
   193	            onClick={() => { navigator.clipboard.writeText(regLinkUrl); }}>
   194	            {t("registration.copyLink")}
   195	          </Button>
   196	        </div>
   197	      )}
   198	      {addrLinkUrl && (
   199	        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
   200	          {t("registration.addressLinkGenerated")}: <a href={addrLinkUrl} target="_blank" rel="noopener noreferrer">{addrLinkUrl}</a>
   201	          <Button size="sm" variant="secondary" style={{ marginLeft: "var(--spacing-2)" }}
   202	            onClick={() => { navigator.clipboard.writeText(addrLinkUrl); }}>
   203	            {t("registration.copyLink")}
   204	          </Button>
   205	        </div>
   206	      )}
   207	      {changeBillingLinkUrl && (
   208	        <div className="info-banner" style={{ marginBottom: "var(--spacing-4)", wordBreak: "break-all" }}>
   209	          {t("registration.changeBillingLinkGenerated")}: <a href={changeBillingLinkUrl} target="_blank" rel="noopener noreferrer">{changeBillingLinkUrl}</a>
   210	          <Button size="sm" variant="secondary" style={{ marginLeft: "var(--spacing-2)" }}
   211	            onClick={() => { navigator.clipboard.writeText(changeBillingLinkUrl); }}>
   212	            {t("registration.copyLink")}
   213	          </Button>
   214	        </div>
   215	      )}
   216	
   217	      {error && <div className="error-banner">{error}</div>}
   218	
   219	      <div className="tabs">
   220	        <Button variant="ghost" className={`tab ${activeTab === "basic" ? "active" : ""}`} onClick={() => switchTab("basic")}>
   221	          {t("companies.basicInfo")}
   222	        </Button>
   223	        <Button variant="ghost" className={`tab ${activeTab === "addresses" ? "active" : ""}`} onClick={() => switchTab("addresses")}>
   224	          {t("companies.address")} ({company.addresses.length})
   225	        </Button>
   226	        <Button variant="ghost" className={`tab ${activeTab === "contacts" ? "active" : ""}`} onClick={() => switchTab("contacts")}>
   227	          {t("contacts.title")} ({contacts.length})
   228	        </Button>
   229	        <Button variant="ghost" className={`tab ${activeTab === "channels" ? "active" : ""}`} onClick={() => switchTab("channels")}>
   230	          {t("nav.channels")} ({company.sales_channels.length})
   231	        </Button>
   232	        <Button variant="ghost" className={`tab ${activeTab === "discord" ? "active" : ""}`} onClick={() => switchTab("discord")}>
   233	          {t("discord.title")}
   234	        </Button>
   235	        <Button variant="ghost" className={`tab ${activeTab === "convHistory" ? "active" : ""}`} onClick={() => switchTab("convHistory")}>
   236	          {t("companies.convHistory.tabLabel")}
   237	        </Button>
   238	      </div>
   239	
   240	      {activeTab === "basic" && basicForm && (
   241	        <CompanyBasicTab
   242	          basicForm={basicForm}
   243	          setBasicForm={setBasicForm}
   244	          basicDirty={basicDirty}
   245	          setBasicDirty={setBasicDirty}
   246	          basicSubmitting={basicSubmitting}
   247	          handleBasicSubmit={handleBasicSubmit}
   248	          canEdit={canEdit}
   249	          canMerge={canMerge}
   250	          company={company}
   251	          dedupSubmitting={dedupSubmitting}
   252	          setDedupConfirmOpen={setDedupConfirmOpen}
   253	          setMergeModalOpen={setMergeModalOpen}
   254	        />
   255	      )}
   256	
   257	      {activeTab === "addresses" && (
   258	        <CompanyAddressesTab
   259	          billingAddresses={billingAddresses}
   260	          deliveryAddresses={deliveryAddresses}

>>> nl -ba frontend/src/pages/company-detail/company-detail.types.ts | sed -n "1,160p"
     1	/**
     2	 * 会社詳細ページの型定義・定数・ヘルパー関数。
     3	 */
     4	
     5	export const PHONE_RE = /^(\+?\d{10,15}|0\d{9,10})$/;
     6	
     7	export interface CompanyAddress {
     8	  id: number;
     9	  address_type: "billing" | "delivery";
    10	  branch_name: string | null;
    11	  name: string | null;
    12	  email: string | null;
    13	  telephone: string | null;
    14	  tax_id: string | null;
    15	  address_line_1: string | null;
    16	  address_line_2: string | null;
    17	  address_line_3: string | null;
    18	  city: string | null;
    19	  state: string | null;
    20	  zip: string | null;
    21	  country_code: string | null;
    22	  is_default: boolean;
    23	}
    24	
    25	export interface CompanyDiscord {
    26	  company_id: number;
    27	  is_joined: boolean;
    28	  channel_id: string | null;
    29	  user_id: string | null;
    30	  invoice_webhook: string | null;
    31	  shipment_webhook: string | null;
    32	}
    33	
    34	export interface Company {
    35	  id: number;
    36	  tenant_id: number;
    37	  company_code: string;
    38	  lead_id: number | null;
    39	  sales_rep_id: number | null;
    40	  name: string;
    41	  name_en: string | null;
    42	  normalized_name: string | null;
    43	  industry: string | null;
    44	  website: string | null;
    45	  priority_focus: string | null;
    46	  per_order_amount: string | null;
    47	  monthly_frequency: number | null;
    48	  monthly_forecast: string | null;
    49	  monthly_forecast_source: string | null;
    50	  monthly_forecast_updated_at: string | null;
    51	  billing_display_name: string | null;
    52	  payment_recipient_name: string | null;
    53	  fedex_account: string | null;
    54	  shipping_note: string | null;
    55	  status: string;
    56	  notes: string | null;
    57	  addresses: CompanyAddress[];
    58	  sales_channels: string[];
    59	  discord: CompanyDiscord | null;
    60	  created_at: string;
    61	  updated_at: string;
    62	  // 読み取り専用集計（v_company_stats）
    63	  total_deal_amount: string | null;
    64	  deal_count: number | null;
    65	  conversation_count: number | null;
    66	  last_conversation_at: string | null;
    67	}
    68	
    69	export interface Contact {
    70	  id: number;
    71	  contact_code: string;
    72	  display_name: string | null;
    73	  surname: string | null;
    74	  given_name: string | null;
    75	  job_title: string | null;
    76	  department: string | null;
    77	  is_primary_contact: boolean;
    78	  primary_email: string | null;
    79	  primary_phone: string | null;
    80	  status: string;
    81	}
    82	
    83	export type Tab = "basic" | "addresses" | "contacts" | "channels" | "discord" | "convHistory";
    84	
    85	export type DiscordFormState = {
    86	  is_joined: boolean;
    87	  channel_id: string;
    88	  user_id: string;
    89	  invoice_webhook: string;
    90	  shipment_webhook: string;
    91	};
    92	
    93	export const emptyDiscordForm = (): DiscordFormState => ({
    94	  is_joined: false,
    95	  channel_id: "", user_id: "",
    96	  invoice_webhook: "", shipment_webhook: "",
    97	});
    98	
    99	export const discordFromApi = (d: CompanyDiscord): DiscordFormState => ({
   100	  is_joined: d.is_joined,
   101	  channel_id: d.channel_id || "",
   102	  user_id: d.user_id || "",
   103	  invoice_webhook: d.invoice_webhook || "",
   104	  shipment_webhook: d.shipment_webhook || "",
   105	});
   106	
   107	export type ContactFormState = {
   108	  /** null = 新規、数値 = 既存更新 */
   109	  id: number | null;
   110	  display_name: string;
   111	  surname: string;
   112	  given_name: string;
   113	  job_title: string;
   114	  department: string;
   115	  is_primary_contact: boolean;
   116	  primary_email: string;
   117	  primary_phone: string;
   118	  status: string;
   119	};
   120	
   121	export const emptyContact = (): ContactFormState => ({
   122	  id: null,
   123	  display_name: "", surname: "", given_name: "",
   124	  job_title: "", department: "",
   125	  is_primary_contact: false,
   126	  primary_email: "", primary_phone: "",
   127	  status: "active",
   128	});
   129	
   130	export const contactFromApi = (c: Contact): ContactFormState => ({
   131	  id: c.id,
   132	  display_name: c.display_name || "",
   133	  surname: c.surname || "",
   134	  given_name: c.given_name || "",
   135	  job_title: c.job_title || "",
   136	  department: c.department || "",
   137	  is_primary_contact: c.is_primary_contact,
   138	  primary_email: c.primary_email || "",
   139	  primary_phone: c.primary_phone || "",
   140	  status: c.status || "active",
   141	});
   142	
   143	export type AddressFormState = {
   144	  /** null = 新規、数値 = 既存更新 */
   145	  id: number | null;
   146	  address_type: "billing" | "delivery";
   147	  branch_name: string;
   148	  name: string;
   149	  email: string;
   150	  telephone: string;
   151	  tax_id: string;
   152	  address_line_1: string;
   153	  address_line_2: string;
   154	  address_line_3: string;
   155	  city: string;
   156	  state: string;
   157	  zip: string;
   158	  country_code: string;
   159	  is_default: boolean;
   160	};

>>> nl -ba frontend/src/pages/inbox/InboxKartePanel.tsx | sed -n "500,705p"
   500	      <div className="right-panel-memo-label">{t("leads.nextAction")}</div>
   501	      <textarea className="right-panel-field" rows={3} value={cardForm.next_action ?? ""}
   502	        onChange={(e) => handleCardFieldChange("next_action", e.target.value)}
   503	        onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />
   504	      <div className="right-panel-row">
   505	        <span className="right-panel-label">{t("leads.nextActionDate")}</span>
   506	        <input
   507	          className={`right-panel-field${!cardForm.next_action_date ? " karte-field-empty" : ""}`}
   508	          type="date" value={cardForm.next_action_date ?? ""}
   509	          onChange={(e) => handleCardFieldChange("next_action_date", e.target.value || null)} onBlur={handleCardFieldBlur} />
   510	      </div>
   511	      <div className="right-panel-row">
   512	        <span className="right-panel-label">{t("leads.responseSpeed")}</span>
   513	        <select className="right-panel-field" value={cardForm.response_speed ?? ""}
   514	          onChange={(e) => handleCardFieldChange("response_speed", e.target.value || null)} onBlur={handleCardFieldBlur}>
   515	          <option value="">—</option>
   516	          <option value="24h以内">{t("leads.responseSpeed_24h")}</option>
   517	          <option value="3日以内">{t("leads.responseSpeed_3days")}</option>
   518	          <option value="3日超">{t("leads.responseSpeed_over3days")}</option>
   519	        </select>
   520	      </div>
   521	
   522	      {/* 見極め */}
   523	      <div className="right-panel-group-heading">{t("inbox.sectionAnalysis")}</div>
   524	      <div className="right-panel-row">
   525	        <span className="right-panel-label">{t("leads.temperature")}</span>
   526	        <select className="right-panel-field" value={cardForm.temperature ?? ""}
   527	          onChange={(e) => handleCardFieldChange("temperature", e.target.value || null)} onBlur={handleCardFieldBlur}>
   528	          <option value="">—</option>
   529	          <option value="Hot">{t("leads.temperature_hot")}</option>
   530	          <option value="Warm">{t("leads.temperature_warm")}</option>
   531	          <option value="Cold">{t("leads.temperature_cold")}</option>
   532	        </select>
   533	      </div>
   534	      <div className="right-panel-memo-label">{t("leads.challenge")}</div>
   535	      <textarea className="right-panel-field" rows={3} value={cardForm.challenge ?? ""}
   536	        onChange={(e) => handleCardFieldChange("challenge", e.target.value)}
   537	        onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />
   538	      <div className="right-panel-row">
   539	        <span className="right-panel-label">{t("leads.competitorCheck")}</span>
   540	        <select className="right-panel-field" value={competitorValue}
   541	          onChange={(e) => {
   542	            const v = e.target.value;
   543	            handleCardFieldChange("competitor_check", v === "" ? null : v === "true");
   544	            setTimeout(handleCardFieldBlur, 0);
   545	          }}>
   546	          <option value="">—</option>
   547	          <option value="false">{t("leads.competitorUnconfirmed")}</option>
   548	          <option value="true">{t("leads.competitorFound")}</option>
   549	        </select>
   550	      </div>
   551	
   552	      {/* 商談規模 */}
   553	      <div className="right-panel-group-heading">{t("inbox.sectionScale")}</div>
   554	      <div className="right-panel-row">
   555	        <span className="right-panel-label">{t("leads.estimatedScale")}</span>
   556	        <select className="right-panel-field" value={cardForm.estimated_scale ?? ""}
   557	          onChange={(e) => handleCardFieldChange("estimated_scale", e.target.value || null)} onBlur={handleCardFieldBlur}>
   558	          <option value="">—</option>
   559	          <option value="Small">{t("leads.estimatedScale_small")}</option>
   560	          <option value="Medium">{t("leads.estimatedScale_medium")}</option>
   561	          <option value="Large">{t("leads.estimatedScale_large")}</option>
   562	        </select>
   563	      </div>
   564	      <div className="right-panel-row">
   565	        <span className="right-panel-label">{t("leads.monthlyForecast")}</span>
   566	        <input className="right-panel-field" type="number" min="0" value={cardForm.monthly_forecast ?? ""}
   567	          onChange={(e) => handleCardFieldChange("monthly_forecast", e.target.value || null)} onBlur={handleCardFieldBlur}
   568	          placeholder={t("inbox.emptyField")} />
   569	      </div>
   570	      <div className="right-panel-row">
   571	        <span className="right-panel-label">{t("leads.perOrderAmount")}</span>
   572	        <input className="right-panel-field" type="number" min="0" value={cardForm.per_order_amount ?? ""}
   573	          onChange={(e) => handleCardFieldChange("per_order_amount", e.target.value || null)} onBlur={handleCardFieldBlur}
   574	          placeholder={t("inbox.emptyField")} />
   575	      </div>
   576	      <div className="right-panel-row">
   577	        <span className="right-panel-label">{t("leads.monthlyFrequency")}</span>
   578	        <input className="right-panel-field" type="number" min="0" value={cardForm.monthly_frequency ?? ""}
   579	          onChange={(e) => handleCardFieldChange("monthly_frequency", e.target.value || null)} onBlur={handleCardFieldBlur}
   580	          placeholder={t("inbox.emptyField")} />
   581	      </div>
   582	
   583	      {/* メモ */}
   584	      <div className="right-panel-group-heading">{t("inbox.sectionMemo")}</div>
   585	      <div className="right-panel-memo-label">{t("leads.meetingMemo")}</div>
   586	      <textarea className="right-panel-field" rows={3} value={cardForm.meeting_memo ?? ""}
   587	        onChange={(e) => handleCardFieldChange("meeting_memo", e.target.value)}
   588	        onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />
   589	    </div>
   590	  );
   591	}
   592	
   593	// ---------------------------------------------------------------------------
   594	// ADR-110/136: Performance Summary — read-only, 3 rows with order + message data
   595	// 取引額は v_company_stats 経由（ADR-136）。クライアント側集計は撤去済み。
   596	// ---------------------------------------------------------------------------
   597	
   598	interface LeadStats {
   599	  total_deal_amount: number;
   600	  paid_invoice_count: number;
   601	  last_paid_at: string | null;
   602	  conversation_count: number;
   603	  last_conversation_at: string | null;
   604	}
   605	
   606	function PerformanceSummary({ leadId }: { leadId: number }) {
   607	  const { t } = useTranslation();
   608	  const [totalRevenue, setTotalRevenue] = useState<number | null>(null);
   609	  const [orderCount, setOrderCount] = useState<number | null>(null);
   610	  const [lastOrderDate, setLastOrderDate] = useState<string | null>(null);
   611	  const [messageCount, setMessageCount] = useState<number | null>(null);
   612	  const [lastMessageDate, setLastMessageDate] = useState<string | null>(null);
   613	  const [loading, setLoading] = useState(true);
   614	
   615	  useEffect(() => {
   616	    let cancelled = false;
   617	    setLoading(true);
   618	
   619	    const fetchData = async () => {
   620	      // Fetch messages count + last message date
   621	      try {
   622	        const msgData = await api.get<{ messages: Array<{ created_at: string }> }>(
   623	          `/leads/${leadId}/messages?limit=500`
   624	        );
   625	        if (!cancelled) {
   626	          const msgs = msgData.messages ?? [];
   627	          setMessageCount(msgs.length);
   628	          setLastMessageDate(msgs.length > 0 ? (msgs[msgs.length - 1].created_at ?? null) : null);
   629	        }
   630	      } catch {
   631	        if (!cancelled) { setMessageCount(0); setLastMessageDate(null); }
   632	      }
   633	
   634	      // Fetch v_company_stats 由来の取引実績（ADR-136）
   635	      try {
   636	        const stats = await api.get<LeadStats>(`/leads/${leadId}/stats`);
   637	        if (!cancelled) {
   638	          if (stats.paid_invoice_count > 0) {
   639	            setTotalRevenue(Number(stats.total_deal_amount));
   640	            setOrderCount(stats.paid_invoice_count);
   641	            setLastOrderDate(stats.last_paid_at);
   642	          } else {
   643	            setTotalRevenue(null);
   644	            setOrderCount(0);
   645	            setLastOrderDate(null);
   646	          }
   647	        }
   648	      } catch {
   649	        if (!cancelled) { setTotalRevenue(null); setOrderCount(0); setLastOrderDate(null); }
   650	      }
   651	
   652	      if (!cancelled) setLoading(false);
   653	    };
   654	
   655	    fetchData();
   656	    return () => { cancelled = true; };
   657	  }, [leadId]);
   658	
   659	  if (loading) {
   660	    return (
   661	      <div className="karte-performance-section" data-testid="karte-performance-section">
   662	        <div className="right-panel-row">
   663	          <span className="right-panel-value">...</span>
   664	        </div>
   665	      </div>
   666	    );
   667	  }
   668	
   669	  const lastOrderDisplay = (() => {
   670	    if (!orderCount) return "—";
   671	    const dateStr = lastOrderDate ? lastOrderDate.replace(" ", "T").split("T")[0] : "—";
   672	    return `${orderCount}${t("inbox.orderCountSuffix")}・${dateStr}`;
   673	  })();
   674	
   675	  const lastMsgDisplay = (() => {
   676	    if (!messageCount) return "—";
   677	    return `${messageCount}${t("inbox.conversationCountSuffix")}・${elapsedLabel(lastMessageDate, t)}`;
   678	  })();
   679	
   680	  return (
   681	    <div className="karte-performance-section" data-testid="karte-performance-section">
   682	      {/* 取引額累計 */}
   683	      <div className="karte-ro-row" data-testid="karte-ro-row">
   684	        <span className="right-panel-label">{t("inbox.performanceTotalRevenue")}</span>
   685	        <span className="right-panel-value karte-ro-value">
   686	          {totalRevenue != null ? `¥${totalRevenue.toLocaleString()}` : t("inbox.performanceNoHistory")}
   687	        </span>
   688	      </div>
   689	      {/* 取引回数・最終取引日 */}
   690	      <div className="karte-ro-row" data-testid="karte-ro-row">
   691	        <span className="right-panel-label">{t("inbox.performanceOrderCount")}</span>
   692	        <span className={`right-panel-value${!orderCount ? " karte-ro-muted" : " karte-ro-value"}`}>
   693	          {lastOrderDisplay}
   694	        </span>
   695	      </div>
   696	      {/* 会話数・最終会話 */}
   697	      <div className="karte-ro-row" data-testid="karte-ro-row">
   698	        <span className="right-panel-label">{t("inbox.performanceConversationCount")}</span>
   699	        <span className={`right-panel-value${!messageCount ? " karte-ro-muted" : " karte-ro-value"}`}>
   700	          {lastMsgDisplay}
   701	        </span>
   702	      </div>
   703	    </div>
   704	  );
   705	}

>>> nl -ba frontend/src/pages/inbox/InboxPage.tsx | sed -n "176,200p"
   176	          {/* モバイルドロワーバックドロップ */}
   177	          {showKartePanel && inboxSettings.showRightPanel && (
   178	            <div className="karte-overlay" onClick={closeKartePanel} aria-hidden="true" />
   179	          )}
   180	
   181	          <InboxKartePanel
   182	            selectedLeadId={selectedLeadId}
   183	            leadDetail={leadDetail}
   184	            cardForm={cardForm}
   185	            cardSaveStatus={cardSaveStatus}
   186	            cardSaveError={cardSaveError}
   187	            karteTab={karteTab}
   188	            setKarteTab={setKarteTab}
   189	            showKartePanel={showKartePanel}
   190	            closeKartePanel={closeKartePanel}
   191	            setShowProfileModal={setShowProfileModal}
   192	            inboxSettings={inboxSettings}
   193	            selectedConversation={selectedConversation}
   194	            avatarErrors={avatarErrors}
   195	            handleAvatarError={handleAvatarError}
   196	            handleCardFieldChange={handleCardFieldChange}
   197	            handleCardFieldBlur={handleCardFieldBlur}
   198	            handleConvertLead={handleConvertLead}
   199	            handleCreateInvoice={handleCreateInvoice}
   200	          />

>>> nl -ba backend/app/services/tenant.py | sed -n "486,506p"
   486	CREATE TABLE IF NOT EXISTS {schema}.orders (
   487	    id SERIAL PRIMARY KEY,
   488	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   489	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   490	    company_id INTEGER CONSTRAINT fk_orders_company REFERENCES {schema}.companies(id),
   491	    contact_id INTEGER CONSTRAINT fk_orders_contact REFERENCES {schema}.contacts(id),
   492	    deal_id INTEGER REFERENCES {schema}.deals(id),
   493	    order_number VARCHAR(100) NOT NULL,
   494	    total_amount NUMERIC(15, 2),
   495	    status VARCHAR(50) DEFAULT 'pending',
   496	    -- 支払済日時（NULL=未払い）。受注ステータスフロー判定の「支払済フラグ」。
   497	    -- migration 20260604_050000 と同期。
   498	    paid_at TIMESTAMPTZ,
   499	    notes TEXT,
   500	    created_at TIMESTAMPTZ DEFAULT NOW(),
   501	    updated_at TIMESTAMPTZ DEFAULT NOW()
   502	);
   503	CREATE INDEX IF NOT EXISTS idx_orders_company_id ON {schema}.orders (company_id);
   504	CREATE INDEX IF NOT EXISTS idx_orders_contact_id ON {schema}.orders (contact_id);
   505	
   506	-- 操作履歴（監査ログ）

>>> nl -ba backend/app/services/tenant.py | sed -n "816,968p"
   816	CREATE TABLE IF NOT EXISTS {schema}.quotes (
   817	    id SERIAL PRIMARY KEY,
   818	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   819	    quote_code VARCHAR(20),
   820	    deal_id INTEGER REFERENCES {schema}.deals(id),
   821	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   822	    company_id INTEGER CONSTRAINT fk_quotes_company REFERENCES {schema}.companies(id),
   823	    contact_id INTEGER CONSTRAINT fk_quotes_contact REFERENCES {schema}.contacts(id),
   824	    currency VARCHAR(10) DEFAULT 'JPY',
   825	    subtotal NUMERIC(15, 2) DEFAULT 0,
   826	    shipping_fee NUMERIC(15, 2) DEFAULT 0,
   827	    tax_amount NUMERIC(15, 2) DEFAULT 0,
   828	    total_amount NUMERIC(15, 2) DEFAULT 0,
   829	    status VARCHAR(20) DEFAULT 'draft',
   830	    validity_date DATE,
   831	    shipping_country VARCHAR(100),
   832	    shipping_carrier VARCHAR(50),
   833	    delivery_info TEXT,
   834	    pdf_url VARCHAR(500),
   835	    notes TEXT,
   836	    created_by INTEGER,
   837	    created_at TIMESTAMPTZ DEFAULT NOW(),
   838	    updated_at TIMESTAMPTZ DEFAULT NOW()
   839	);
   840	CREATE INDEX IF NOT EXISTS idx_quotes_company_id ON {schema}.quotes (company_id);
   841	CREATE INDEX IF NOT EXISTS idx_quotes_contact_id ON {schema}.quotes (contact_id);
   842	
   843	-- 見積明細
   844	CREATE TABLE IF NOT EXISTS {schema}.quote_items (
   845	    id SERIAL PRIMARY KEY,
   846	    quote_id INTEGER NOT NULL REFERENCES {schema}.quotes(id) ON DELETE CASCADE,
   847	    product_id INTEGER REFERENCES public.products(id),
   848	    product_name VARCHAR(255) NOT NULL,
   849	    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
   850	    name_en VARCHAR(255),
   851	    condition VARCHAR(50),
   852	    unit VARCHAR(20),
   853	    quantity INTEGER NOT NULL DEFAULT 1,
   854	    unit_price NUMERIC(15, 2) NOT NULL,
   855	    weight NUMERIC(10, 3),
   856	    subtotal NUMERIC(15, 2) NOT NULL,
   857	    sort_order INTEGER DEFAULT 0
   858	);
   859	
   860	-- 請求書ヘッダー
   861	CREATE TABLE IF NOT EXISTS {schema}.invoices (
   862	    id SERIAL PRIMARY KEY,
   863	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   864	    invoice_number VARCHAR(30),
   865	    quote_id INTEGER REFERENCES {schema}.quotes(id),
   866	    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
   867	    company_id INTEGER CONSTRAINT fk_invoices_company REFERENCES {schema}.companies(id),
   868	    contact_id INTEGER CONSTRAINT fk_invoices_contact REFERENCES {schema}.contacts(id),
   869	    currency VARCHAR(10) DEFAULT 'JPY',
   870	    subtotal NUMERIC(15, 2) DEFAULT 0,
   871	    shipping_fee NUMERIC(15, 2) DEFAULT 0,
   872	    tax_amount NUMERIC(15, 2) DEFAULT 0,
   873	    total_amount NUMERIC(15, 2) DEFAULT 0,
   874	    exchange_rate_jpy NUMERIC(12, 4),
   875	    exchange_rate_usd NUMERIC(12, 4),
   876	    amount_jpy NUMERIC(15, 2),
   877	    amount_usd NUMERIC(15, 2),
   878	    payment_method VARCHAR(50),
   879	    status VARCHAR(20) DEFAULT 'draft',
   880	    branch_number INTEGER DEFAULT 1,
   881	    pdf_url VARCHAR(500),
   882	    erp_key VARCHAR(100),
   883	    issued_at TIMESTAMPTZ,
   884	    due_date DATE,
   885	    paid_at TIMESTAMPTZ,
   886	    voided_at TIMESTAMPTZ,
   887	    void_reason VARCHAR(500),
   888	    notes TEXT,
   889	    created_by INTEGER,
   890	    created_at TIMESTAMPTZ DEFAULT NOW(),
   891	    updated_at TIMESTAMPTZ DEFAULT NOW()
   892	);
   893	CREATE INDEX IF NOT EXISTS idx_invoices_company_id ON {schema}.invoices (company_id);
   894	CREATE INDEX IF NOT EXISTS idx_invoices_contact_id ON {schema}.invoices (contact_id);
   895	
   896	-- 請求書明細
   897	CREATE TABLE IF NOT EXISTS {schema}.invoice_items (
   898	    id SERIAL PRIMARY KEY,
   899	    invoice_id INTEGER NOT NULL REFERENCES {schema}.invoices(id) ON DELETE CASCADE,
   900	    product_id INTEGER REFERENCES public.products(id),
   901	    product_name VARCHAR(255) NOT NULL,
   902	    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
   903	    name_en VARCHAR(255),
   904	    condition VARCHAR(50),
   905	    unit VARCHAR(20),
   906	    quantity INTEGER NOT NULL DEFAULT 1,
   907	    unit_price NUMERIC(15, 2) NOT NULL,
   908	    weight NUMERIC(10, 3),
   909	    subtotal NUMERIC(15, 2) NOT NULL,
   910	    sort_order INTEGER DEFAULT 0
   911	);
   912	
   913	-- === Phase 3: 仕入れ・調達管理 ===
   914	
   915	CREATE TABLE IF NOT EXISTS {schema}.suppliers (
   916	    id SERIAL PRIMARY KEY,
   917	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   918	    supplier_code VARCHAR(20),
   919	    name VARCHAR(255) NOT NULL,
   920	    contact_name VARCHAR(255),
   921	    email VARCHAR(255),
   922	    phone VARCHAR(50),
   923	    address TEXT,
   924	    notes TEXT,
   925	    is_active BOOLEAN DEFAULT TRUE,
   926	    created_at TIMESTAMPTZ DEFAULT NOW(),
   927	    updated_at TIMESTAMPTZ DEFAULT NOW()
   928	);
   929	
   930	-- products.supplier_default_id の FK を suppliers 作成後に付与
   931	-- （Phase 1-C M-MVP / 2026-04-28）
   932	DO $supplier_fk$
   933	BEGIN
   934	    IF NOT EXISTS (
   935	        SELECT 1 FROM pg_constraint
   936	        WHERE conrelid = '{schema}.products'::regclass
   937	          AND conname = 'fk_products_supplier_default'
   938	    ) THEN
   939	        ALTER TABLE {schema}.products
   940	        ADD CONSTRAINT fk_products_supplier_default
   941	        FOREIGN KEY (supplier_default_id) REFERENCES {schema}.suppliers(id);
   942	    END IF;
   943	END $supplier_fk$;
   944	
   945	CREATE TABLE IF NOT EXISTS {schema}.purchase_orders (
   946	    id SERIAL PRIMARY KEY,
   947	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
   948	    po_number VARCHAR(20),
   949	    supplier_id INTEGER NOT NULL REFERENCES {schema}.suppliers(id),
   950	    status VARCHAR(20) DEFAULT 'draft',
   951	    total_amount NUMERIC(15, 2) DEFAULT 0,
   952	    ordered_at TIMESTAMPTZ,
   953	    received_at TIMESTAMPTZ,
   954	    notes TEXT,
   955	    created_by INTEGER,
   956	    created_at TIMESTAMPTZ DEFAULT NOW(),
   957	    updated_at TIMESTAMPTZ DEFAULT NOW()
   958	);
   959	
   960	CREATE TABLE IF NOT EXISTS {schema}.purchase_order_items (
   961	    id SERIAL PRIMARY KEY,
   962	    purchase_order_id INTEGER NOT NULL REFERENCES {schema}.purchase_orders(id) ON DELETE CASCADE,
   963	    product_id INTEGER NOT NULL REFERENCES public.products(id),
   964	    quantity INTEGER NOT NULL DEFAULT 1,
   965	    unit_cost NUMERIC(15, 2) NOT NULL,
   966	    subtotal NUMERIC(15, 2) NOT NULL,
   967	    sort_order INTEGER DEFAULT 0
   968	);

>>> rg -n "order_financials|order_shipping_details" backend/app/services/tenant.py migrations/*.sql backend/app/schemas backend/app/routers
migrations/047_create_order_financials.sql:10:-- ADR-021 Phase 2 / Sprint 2 / Migration 047: order_financials テーブル新設
migrations/047_create_order_financials.sql:32:CREATE TABLE IF NOT EXISTS {schema}.order_financials (
migrations/047_create_order_financials.sql:61:CREATE UNIQUE INDEX IF NOT EXISTS uq_order_financials_tenant_order
migrations/047_create_order_financials.sql:62:    ON {schema}.order_financials (tenant_id, order_id);
migrations/047_create_order_financials.sql:63:CREATE INDEX IF NOT EXISTS idx_order_financials_tenant
migrations/047_create_order_financials.sql:64:    ON {schema}.order_financials (tenant_id);
migrations/047_create_order_financials.sql:65:CREATE INDEX IF NOT EXISTS idx_order_financials_order
migrations/047_create_order_financials.sql:66:    ON {schema}.order_financials (order_id);
migrations/047_create_order_financials.sql:70:CREATE INDEX IF NOT EXISTS idx_order_financials_created_at
migrations/047_create_order_financials.sql:71:    ON {schema}.order_financials (created_at);
migrations/047_create_order_financials.sql:74:CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_financials()
migrations/047_create_order_financials.sql:82:DROP TRIGGER IF EXISTS trigger_set_updated_at_order_financials
migrations/047_create_order_financials.sql:83:    ON {schema}.order_financials;
migrations/047_create_order_financials.sql:85:CREATE TRIGGER trigger_set_updated_at_order_financials
migrations/047_create_order_financials.sql:86:    BEFORE UPDATE ON {schema}.order_financials
migrations/047_create_order_financials.sql:88:    EXECUTE FUNCTION {schema}.set_updated_at_order_financials();
migrations/047_create_order_financials.sql:91:ALTER TABLE {schema}.order_financials ENABLE ROW LEVEL SECURITY;
migrations/047_create_order_financials.sql:98:          AND tablename = 'order_financials'
migrations/047_create_order_financials.sql:99:          AND policyname = 'tenant_isolation_order_financials'
migrations/047_create_order_financials.sql:102:            'CREATE POLICY tenant_isolation_order_financials ON %I.order_financials '
migrations/048_create_order_shipping_details.sql:10:-- ADR-021 Phase 3 / Sprint 3 / Migration 048: order_shipping_details テーブル新設
migrations/048_create_order_shipping_details.sql:33:CREATE TABLE IF NOT EXISTS {schema}.order_shipping_details (
migrations/048_create_order_shipping_details.sql:100:CREATE UNIQUE INDEX IF NOT EXISTS uq_order_shipping_details_tenant_order
migrations/048_create_order_shipping_details.sql:101:    ON {schema}.order_shipping_details (tenant_id, order_id);
migrations/048_create_order_shipping_details.sql:102:CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tenant
migrations/048_create_order_shipping_details.sql:103:    ON {schema}.order_shipping_details (tenant_id);
migrations/048_create_order_shipping_details.sql:104:CREATE INDEX IF NOT EXISTS idx_order_shipping_details_order
migrations/048_create_order_shipping_details.sql:105:    ON {schema}.order_shipping_details (order_id);
migrations/048_create_order_shipping_details.sql:106:CREATE INDEX IF NOT EXISTS idx_order_shipping_details_carrier
migrations/048_create_order_shipping_details.sql:107:    ON {schema}.order_shipping_details (carrier);
migrations/048_create_order_shipping_details.sql:108:CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tracking
migrations/048_create_order_shipping_details.sql:109:    ON {schema}.order_shipping_details (tracking_number);
migrations/048_create_order_shipping_details.sql:112:CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_shipping_details()
migrations/048_create_order_shipping_details.sql:120:DROP TRIGGER IF EXISTS trigger_set_updated_at_order_shipping_details
migrations/048_create_order_shipping_details.sql:121:    ON {schema}.order_shipping_details;
migrations/048_create_order_shipping_details.sql:123:CREATE TRIGGER trigger_set_updated_at_order_shipping_details
migrations/048_create_order_shipping_details.sql:124:    BEFORE UPDATE ON {schema}.order_shipping_details
migrations/048_create_order_shipping_details.sql:126:    EXECUTE FUNCTION {schema}.set_updated_at_order_shipping_details();
migrations/048_create_order_shipping_details.sql:129:ALTER TABLE {schema}.order_shipping_details ENABLE ROW LEVEL SECURITY;
migrations/048_create_order_shipping_details.sql:136:          AND tablename = 'order_shipping_details'
migrations/048_create_order_shipping_details.sql:137:          AND policyname = 'tenant_isolation_order_shipping_details'
migrations/048_create_order_shipping_details.sql:140:            'CREATE POLICY tenant_isolation_order_shipping_details ON %I.order_shipping_details '
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:1:-- Migration 105: order_financials.purchase_cost を NULL 許容・DEFAULT 削除
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:37:        -- order_financials テーブルの存在確認
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:41:              AND table_name   = 'order_financials'
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:43:            RAISE NOTICE '  order_financials テーブルが存在しません。スキップ。';
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:51:          AND table_name   = 'order_financials'
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:57:          AND table_name   = 'order_financials'
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:63:                'ALTER TABLE %I.order_financials
migrations/20260613_050000_funnel_purchase_cost_nullable.sql:75:                'ALTER TABLE %I.order_financials
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:1:-- Migration 20260611_110000: ADR-128 — order_shipping_details に Ship/Pickup 用カラム追加
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:4:-- order_shipping_details テーブルへ additive 追加する。
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:24:        -- order_shipping_details が存在しないテナント（CI 用最小 schema 等）は skip
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:25:        IF to_regclass(sch || '.order_shipping_details') IS NULL THEN
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:30:            'ALTER TABLE %I.order_shipping_details
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:37:            'ALTER TABLE %I.order_shipping_details
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:43:            'ALTER TABLE %I.order_shipping_details
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:49:            'ALTER TABLE %I.order_shipping_details
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:55:            'ALTER TABLE %I.order_shipping_details
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql:61:            'ALTER TABLE %I.order_shipping_details
migrations/20260604_050000_add_orders_paid_at.sql:11:--     完了         = order_shipping_details.label_issued_at + tracking_number 有
backend/app/routers/shipping.py:519:    # order_shipping_details に記録
backend/app/routers/shipping.py:524:    osd_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/shipping.py:613:    # order_shipping_details に集荷確認番号を記録
backend/app/routers/shipping.py:614:    osd_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/analytics.py:598:    # ── 粗利集計（order_financials JOIN）──
backend/app/routers/analytics.py:611:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/routers/analytics.py:1599:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/routers/analytics.py:1721:    # ── 粗利: lead → deal → order → order_financials（二重カウント回避のため別クエリ）──
backend/app/routers/analytics.py:1743:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/schemas/order_financial.py:4:受注ごとの売上情報（order_financials）テーブル用 Pydantic スキーマ。
backend/app/schemas/order_financial.py:199:    受注 1 件 = 売上情報 1 件（無い場合もある）。order_financials があれば
backend/app/schemas/order_shipping_detail.py:4:受注ごとの発送情報（order_shipping_details）テーブル用 Pydantic スキーマ。
backend/app/schemas/order.py:124:    order_shipping_details.city / country_code を JOIN で同梱する。
backend/app/routers/order_financials.py:4:受注ごとの売上情報 API（order_financials）。
backend/app/routers/order_financials.py:103:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:105:        text(f"SELECT {_SELECT_COLS} FROM {order_financials_t} WHERE order_id = :order_id"),
backend/app/routers/order_financials.py:150:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:152:        INSERT INTO {order_financials_t} (
backend/app/routers/order_financials.py:179:        table_name="order_financials",
backend/app/routers/order_financials.py:243:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:245:        UPDATE {order_financials_t}
backend/app/routers/order_financials.py:258:        table_name="order_financials",
backend/app/routers/order_financials.py:287:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:289:        text(f"DELETE FROM {order_financials_t} WHERE order_id = :order_id"),
backend/app/routers/order_financials.py:298:        table_name="order_financials",
backend/app/routers/order_financials.py:324:    ADR-021 第 4 節 AC-004 の最小実装。集計範囲は order_financials.created_at が
backend/app/routers/order_financials.py:336:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:347:        FROM {order_financials_t}
backend/app/routers/order_financials.py:397:    受注ごとに order_financials を LEFT JOIN し、売上 / 原価 / 粗利 / 粗利率を
backend/app/routers/order_financials.py:405:    financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_shipping_details.py:4:受注ごとの発送情報 API（order_shipping_details）。
backend/app/routers/order_shipping_details.py:89:    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/order_shipping_details.py:91:        text(f"SELECT {_SELECT_COLS} FROM {order_shipping_details_t} WHERE order_id = :order_id"),
backend/app/routers/order_shipping_details.py:166:    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/order_shipping_details.py:168:        INSERT INTO {order_shipping_details_t} ({', '.join(insert_cols)})
backend/app/routers/order_shipping_details.py:180:        table_name="order_shipping_details",
backend/app/routers/order_shipping_details.py:243:    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/order_shipping_details.py:245:        UPDATE {order_shipping_details_t}
backend/app/routers/order_shipping_details.py:258:        table_name="order_shipping_details",
backend/app/routers/order_shipping_details.py:287:    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
backend/app/routers/order_shipping_details.py:289:        text(f"DELETE FROM {order_shipping_details_t} WHERE order_id = :order_id"),
backend/app/routers/order_shipping_details.py:298:        table_name="order_shipping_details",
backend/app/routers/order_commissions.py:19:  recalc は order の status / order_financials.commission_base_amount /
backend/app/routers/order_commissions.py:112:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_commissions.py:115:            f"SELECT commission_base_amount FROM {order_financials_t} "
backend/app/routers/orders.py:225:    shipping_t = tenant_table_ref(db, tenant_id, "order_shipping_details")

>>> nl -ba migrations/047_create_order_financials.sql | sed -n "1,108p"
     1	-- ============================================================================
     2	-- !! 警告 !! このSQLファイルは **テンプレート** です。
     3	-- {schema}, {tenant_id} のプレースホルダを含むため、
     4	-- そのまま psql で実行するとシンタックスエラーになります。
     5	--
     6	-- 必ず scripts/migrate_adr021_sprint2_financials.py 経由で実行してください:
     7	--   docker compose exec backend python /app/scripts/migrate_adr021_sprint2_financials.py
     8	-- ============================================================================
     9	--
    10	-- ADR-021 Phase 2 / Sprint 2 / Migration 047: order_financials テーブル新設
    11	--
    12	-- 目的:
    13	--   ADR-021 第 4 節「売上計算とレポート」AC-004 を最小実装する。
    14	--   受注ごとに売上情報（売上高 / 仕入原価 / 各種手数料 / 利益率）を構造化テーブルに記録し、
    15	--   Phase 5（報酬計算）で必要となる commission_base_amount フィールドも本 Sprint で先取り。
    16	--   OrderFlow Manager の「売上情報」27 列を本テーブルへ分解する。
    17	--
    18	-- 設計:
    19	--   - 1 受注 = 1 売上情報（order_id UNIQUE / ON DELETE CASCADE）
    20	--   - 全金額カラムは NUMERIC(14,2) JPY 換算前提（多通貨は本 Sprint スコープ外）
    21	--   - 導出列（cost_total / gross_profit / gross_profit_rate /
    22	--     operating_profit_with_tax_refund）は DB ではなく Python 側で計算
    23	--   - tenant_id 列は RLS 用（既存の per-tenant スキーマ分離との二重防御）
    24	--
    25	-- 冪等性:
    26	--   - CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS で再実行 no-op
    27	--
    28	-- 変更履歴:
    29	--   2026-05-11: 初版（ADR-021 Phase 2 / Sprint 2）
    30	-- ============================================================================
    31	
    32	CREATE TABLE IF NOT EXISTS {schema}.order_financials (
    33	    id SERIAL PRIMARY KEY,
    34	    order_id INTEGER NOT NULL UNIQUE
    35	        REFERENCES {schema}.orders(id) ON DELETE CASCADE,
    36	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    37	
    38	    -- 売上 / 仕入 / 各種手数料（OrderFlow EP 列ベース、JPY 換算済前提）
    39	    revenue_amount         NUMERIC(14, 2) DEFAULT 0,  -- 売上高
    40	    purchase_cost          NUMERIC(14, 2) DEFAULT 0,  -- 仕入原価
    41	    purchase_shipping      NUMERIC(14, 2) DEFAULT 0,  -- 仕入送料
    42	    paypal_fee             NUMERIC(14, 2) DEFAULT 0,
    43	    wise_fee               NUMERIC(14, 2) DEFAULT 0,
    44	    exchange_fee           NUMERIC(14, 2) DEFAULT 0,  -- 為替手数料
    45	    outsource_fee          NUMERIC(14, 2) DEFAULT 0,  -- 外注費
    46	    packing_fee            NUMERIC(14, 2) DEFAULT 0,  -- 荷造運賃
    47	    ad_cost                NUMERIC(14, 2) DEFAULT 0,  -- 広告費
    48	    return_fee             NUMERIC(14, 2) DEFAULT 0,  -- 返送料
    49	    refund_amount          NUMERIC(14, 2) DEFAULT 0,  -- 返金額
    50	    commission_base_amount NUMERIC(14, 2) DEFAULT 0,  -- Phase 5 報酬計算ベース額（OrderFlow EP 列 = SALES_INCENTIVE 相当）
    51	    tax_refund             NUMERIC(14, 2) DEFAULT 0,  -- 消費税還付
    52	
    53	    notes TEXT,
    54	
    55	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    56	    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    57	);
    58	
    59	-- 索引
    60	-- order_id は UNIQUE 制約で自動 index されるが、明示的に貼って named index にする
    61	CREATE UNIQUE INDEX IF NOT EXISTS uq_order_financials_tenant_order
    62	    ON {schema}.order_financials (tenant_id, order_id);
    63	CREATE INDEX IF NOT EXISTS idx_order_financials_tenant
    64	    ON {schema}.order_financials (tenant_id);
    65	CREATE INDEX IF NOT EXISTS idx_order_financials_order
    66	    ON {schema}.order_financials (order_id);
    67	
    68	-- 月次集計用に created_at で範囲索引（将来 receipts テーブルが受注 → 月次の集計を担うが、
    69	-- 本 Sprint では financials.created_at で代替）
    70	CREATE INDEX IF NOT EXISTS idx_order_financials_created_at
    71	    ON {schema}.order_financials (created_at);
    72	
    73	-- updated_at 自動更新トリガー（既存パターンに倣う）
    74	CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_financials()
    75	RETURNS TRIGGER AS $$
    76	BEGIN
    77	    NEW.updated_at = NOW();
    78	    RETURN NEW;
    79	END;
    80	$$ LANGUAGE plpgsql;
    81	
    82	DROP TRIGGER IF EXISTS trigger_set_updated_at_order_financials
    83	    ON {schema}.order_financials;
    84	
    85	CREATE TRIGGER trigger_set_updated_at_order_financials
    86	    BEFORE UPDATE ON {schema}.order_financials
    87	    FOR EACH ROW
    88	    EXECUTE FUNCTION {schema}.set_updated_at_order_financials();
    89	
    90	-- RLS 有効化（既存テナントテーブル群と同じ tenant_id ベース ポリシー）
    91	ALTER TABLE {schema}.order_financials ENABLE ROW LEVEL SECURITY;
    92	
    93	DO $$
    94	BEGIN
    95	    IF NOT EXISTS (
    96	        SELECT 1 FROM pg_policies
    97	        WHERE schemaname = '{schema}'
    98	          AND tablename = 'order_financials'
    99	          AND policyname = 'tenant_isolation_order_financials'
   100	    ) THEN
   101	        EXECUTE format(
   102	            'CREATE POLICY tenant_isolation_order_financials ON %I.order_financials '
   103	            'USING (tenant_id = public.current_tenant_id())',
   104	            '{schema}'
   105	        );
   106	    END IF;
   107	END
   108	$$;

>>> nl -ba migrations/048_create_order_shipping_details.sql | sed -n "1,146p"
     1	-- ============================================================================
     2	-- !! 警告 !! このSQLファイルは **テンプレート** です。
     3	-- {schema}, {tenant_id} のプレースホルダを含むため、
     4	-- そのまま psql で実行するとシンタックスエラーになります。
     5	--
     6	-- 必ず scripts/migrate_adr021_sprint3_shipping.py 経由で実行してください:
     7	--   docker compose exec backend python /app/scripts/migrate_adr021_sprint3_shipping.py
     8	-- ============================================================================
     9	--
    10	-- ADR-021 Phase 3 / Sprint 3 / Migration 048: order_shipping_details テーブル新設
    11	--
    12	-- 目的:
    13	--   ADR-021 第 3 節「発送情報の登録と外部システム連携」AC-003 を最小実装する。
    14	--   OrderFlow Manager の「発送情報」27-85 列 + 「elogi連携」56-76 列を本テーブルへ
    15	--   分解し、eLogi CSV 出力を eLogi 既存フォーマット互換で実現する。
    16	--   後続キャリア追加（DHL / FedEx / ヤマト）に拡張できる adapter 層と組み合わせる。
    17	--
    18	-- 設計:
    19	--   - 1 受注 = 1 発送情報（order_id UNIQUE / ON DELETE CASCADE）
    20	--   - 全カラム NULL 可（最低限 order_id のみ必須）。発送ワークフローの段階入力に対応。
    21	--   - 寸法・重量・金額は NUMERIC（cm / kg / USD）。為替換算は本 Sprint 範囲外。
    22	--   - tenant_id 列は RLS 用（既存の per-tenant スキーマ分離との二重防御）
    23	--   - carrier は CHECK 制約付き enum（'elogi' / 'fedex' / 'dhl' / 'yamato' / 'other'）。
    24	--     adapter 層は subclass で簡単に拡張できる構造（実装は本 Sprint では eLogi のみ）
    25	--
    26	-- 冪等性:
    27	--   - CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS で再実行 no-op
    28	--
    29	-- 変更履歴:
    30	--   2026-05-11: 初版（ADR-021 Phase 3 / Sprint 3）
    31	-- ============================================================================
    32	
    33	CREATE TABLE IF NOT EXISTS {schema}.order_shipping_details (
    34	    id SERIAL PRIMARY KEY,
    35	    order_id INTEGER NOT NULL UNIQUE
    36	        REFERENCES {schema}.orders(id) ON DELETE CASCADE,
    37	    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    38	
    39	    -- 受取人
    40	    recipient_name VARCHAR(255),
    41	    phone          VARCHAR(50),
    42	    email          VARCHAR(255),
    43	    tax_number     VARCHAR(100),
    44	
    45	    -- 住所
    46	    address1     VARCHAR(255),
    47	    address2     VARCHAR(255),
    48	    address3     VARCHAR(255),
    49	    city         VARCHAR(100),
    50	    state_code   VARCHAR(20),
    51	    zip_code     VARCHAR(50),
    52	    country_code VARCHAR(10),
    53	
    54	    -- 寸法・重量
    55	    length_cm  NUMERIC(8, 2),
    56	    width_cm   NUMERIC(8, 2),
    57	    height_cm  NUMERIC(8, 2),
    58	    weight_kg  NUMERIC(8, 3),
    59	    volume_g   NUMERIC(10, 2),
    60	    box_count  INTEGER,
    61	
    62	    -- 梱包
    63	    packing_memo      TEXT,
    64	    packing_type      VARCHAR(50),
    65	    inspection_status VARCHAR(50),
    66	
    67	    -- 品目
    68	    item_description VARCHAR(500),
    69	    item_price_usd   NUMERIC(12, 2),
    70	    exchange_rate    NUMERIC(12, 6),
    71	    hs_code          VARCHAR(50),
    72	    tax_id           VARCHAR(100),
    73	    fedex_id         VARCHAR(100),
    74	
    75	    -- 配送
    76	    carrier           VARCHAR(20)
    77	        CHECK (carrier IS NULL OR carrier IN ('elogi', 'fedex', 'dhl', 'yamato', 'other')),
    78	    ship_method       VARCHAR(50),
    79	    ship_date         DATE,
    80	    tracking_number   VARCHAR(200),
    81	    est_shipping_fee  NUMERIC(12, 2),
    82	
    83	    -- ステータス
    84	    label_issued_at     TIMESTAMPTZ,
    85	    pickup_requested_at TIMESTAMPTZ,
    86	    shipped_at          TIMESTAMPTZ,
    87	    notified_at         TIMESTAMPTZ,
    88	
    89	    -- メモ
    90	    ship_memo TEXT,
    91	
    92	    -- 標準
    93	    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    94	    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    95	);
    96	
    97	-- 索引
    98	-- order_id は UNIQUE 制約で自動 index されるが、tenant_id との複合 UNIQUE で
    99	-- マルチテナント防御を二重化する（migration 047 と同じパターン）。
   100	CREATE UNIQUE INDEX IF NOT EXISTS uq_order_shipping_details_tenant_order
   101	    ON {schema}.order_shipping_details (tenant_id, order_id);
   102	CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tenant
   103	    ON {schema}.order_shipping_details (tenant_id);
   104	CREATE INDEX IF NOT EXISTS idx_order_shipping_details_order
   105	    ON {schema}.order_shipping_details (order_id);
   106	CREATE INDEX IF NOT EXISTS idx_order_shipping_details_carrier
   107	    ON {schema}.order_shipping_details (carrier);
   108	CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tracking
   109	    ON {schema}.order_shipping_details (tracking_number);
   110	
   111	-- updated_at 自動更新トリガー（既存パターンに倣う）
   112	CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_shipping_details()
   113	RETURNS TRIGGER AS $$
   114	BEGIN
   115	    NEW.updated_at = NOW();
   116	    RETURN NEW;
   117	END;
   118	$$ LANGUAGE plpgsql;
   119	
   120	DROP TRIGGER IF EXISTS trigger_set_updated_at_order_shipping_details
   121	    ON {schema}.order_shipping_details;
   122	
   123	CREATE TRIGGER trigger_set_updated_at_order_shipping_details
   124	    BEFORE UPDATE ON {schema}.order_shipping_details
   125	    FOR EACH ROW
   126	    EXECUTE FUNCTION {schema}.set_updated_at_order_shipping_details();
   127	
   128	-- RLS 有効化（既存テナントテーブル群と同じ tenant_id ベース ポリシー）
   129	ALTER TABLE {schema}.order_shipping_details ENABLE ROW LEVEL SECURITY;
   130	
   131	DO $$
   132	BEGIN
   133	    IF NOT EXISTS (
   134	        SELECT 1 FROM pg_policies
   135	        WHERE schemaname = '{schema}'
   136	          AND tablename = 'order_shipping_details'
   137	          AND policyname = 'tenant_isolation_order_shipping_details'
   138	    ) THEN
   139	        EXECUTE format(
   140	            'CREATE POLICY tenant_isolation_order_shipping_details ON %I.order_shipping_details '
   141	            'USING (tenant_id = public.current_tenant_id())',
   142	            '{schema}'
   143	        );
   144	    END IF;
   145	END
   146	$$;

>>> rg -n "payment_method|currency|status" backend/app/services/tenant.py | grep -iE "order|invoice|purchase"

>>> rg -n "status" backend/app/routers/orders.py | head -20
20:    `?status=` の whitelist 検証を追加（旧 `confirmed` 等の許可外値は 400）。
25:from fastapi import APIRouter, Depends, HTTPException, Query, status
57:_SORTABLE_COLUMNS = {"created_at", "updated_at", "total_amount", "status"}
59:# ADR-021 J1 fix (2026-05-13): `?status=` パラメータの許可値ホワイトリスト。
64:def _validate_status_filter(status_filter: str | None) -> None:
65:    """`?status=` の値を OrderStatus 6 値のホワイトリストで検証する。
71:    if status_filter is None or status_filter == "":
73:    if status_filter not in _ALLOWED_STATUS_VALUES:
75:            status_code=status.HTTP_400_BAD_REQUEST,
77:                "指定された status は許可されていません。"
111:    total_amount, currency, status,
119:    "order_number", "total_amount", "currency", "status",
126:    status_filter: str | None,
137:    if status_filter:
138:        conditions.append("o.status = :status")
139:        params["status"] = status_filter
164:    status_filter: str | None = Query(default=None, alias="status"),
174:        description="ソート対象カラム（updated_at / created_at / total_amount / status）",
194:            status_code=status.HTTP_400_BAD_REQUEST,
200:            status_code=status.HTTP_400_BAD_REQUEST,

>>> nl -ba backend/app/routers/orders.py | sed -n "420,446p"
   420	@router.patch("/orders/{order_id}", response_model=OrderResponse,
   421	              dependencies=[Depends(require_permission("orders.update"))])
   422	async def update_order(
   423	    order_id: int,
   424	    data: OrderUpdate,
   425	    db: AsyncSession = Depends(get_db),
   426	    tenant_id: int = Depends(get_current_tenant),
   427	    current_user: User = Depends(get_current_user),
   428	):
   429	    """注文情報を更新する（部分更新）"""
   430	    orders_t = tenant_table_ref(db, tenant_id, "orders")
   431	    old_result = await db.execute(
   432	        text(f"SELECT {_SELECT_COLS} FROM {orders_t} WHERE id = :id"),
   433	        {"id": order_id},
   434	    )
   435	    old_row = old_result.mappings().first()
   436	    if not old_row:
   437	        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")
   438	
   439	    update_data = data.model_dump(exclude_unset=True)
   440	    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
   441	    if not update_data:
   442	        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")
   443	
   444	    if "status" in update_data and update_data["status"] is not None:
   445	        update_data["status"] = update_data["status"].value
   446	

>>> rg -n "total_deal_amount|deal_count|conversation_count|last_conversation_at|cumulative|profit|order_financials" backend/app/services/tenant.py backend/app/routers backend/app/schemas | head -200
backend/app/services/tenant.py:1085:                         'revenue', 'deal_count', 'close_rate',
backend/app/schemas/goal.py:15:KpiType = Literal["revenue", "deal_count", "close_rate", "lead_count", "conversion_rate"]
backend/app/routers/companies.py:194:                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
backend/app/routers/companies.py:195:                       deal_count, conversation_count, last_conversation_at
backend/app/schemas/lead.py:268:    total_deal_amount: Decimal
backend/app/schemas/lead.py:271:    conversation_count: int
backend/app/schemas/lead.py:272:    last_conversation_at: datetime | None
backend/app/routers/analytics.py:291:    open_deal_count: int
backend/app/routers/analytics.py:324:                COUNT(*) AS open_deal_count
backend/app/routers/analytics.py:348:        open_deal_count=int(row.get("open_deal_count", 0) or 0),
backend/app/routers/analytics.py:386:    gross_profit: float = 0.0
backend/app/routers/analytics.py:387:    gross_profit_margin: float | None = None
backend/app/routers/analytics.py:598:    # ── 粗利集計（order_financials JOIN）──
backend/app/routers/analytics.py:611:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/routers/analytics.py:619:    gross_profit = gp_rev - gp_cost
backend/app/routers/analytics.py:620:    gross_profit_margin = round(gross_profit / gp_rev * 100, 1) if gp_rev > 0 else None
backend/app/routers/analytics.py:679:            gross_profit=gross_profit,
backend/app/routers/analytics.py:680:            gross_profit_margin=gross_profit_margin,
backend/app/routers/analytics.py:1211:    won_target = int(goals.get("won_count", goals.get("deal_count", 0)))
backend/app/routers/analytics.py:1599:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/routers/analytics.py:1721:    # ── 粗利: lead → deal → order → order_financials（二重カウント回避のため別クエリ）──
backend/app/routers/analytics.py:1743:            LEFT JOIN order_financials f ON f.order_id = o.id
backend/app/routers/analytics.py:2217:                SELECT company_id, MAX(occurred_at) AS last_conversation_at
backend/app/routers/analytics.py:2225:            if company_id in candidate_company_ids and row["last_conversation_at"] is not None:
backend/app/routers/analytics.py:2226:                contact_last_seen[company_id] = row["last_conversation_at"]
backend/app/schemas/order_financial.py:4:受注ごとの売上情報（order_financials）テーブル用 Pydantic スキーマ。
backend/app/schemas/order_financial.py:13:  - gross_profit = revenue_amount - cost_total
backend/app/schemas/order_financial.py:14:  - gross_profit_rate = gross_profit / revenue_amount（revenue_amount=0 のとき null）
backend/app/schemas/order_financial.py:15:  - operating_profit_with_tax_refund = gross_profit + tax_refund
backend/app/schemas/order_financial.py:76:    revenue_amount=0 の場合 gross_profit_rate は None を返す（ZeroDivisionError 回避）。
backend/app/schemas/order_financial.py:80:    gross_profit = revenue - cost_total
backend/app/schemas/order_financial.py:82:        gross_profit_rate: Decimal | None = None
backend/app/schemas/order_financial.py:85:        gross_profit_rate = (gross_profit / revenue).quantize(Decimal("0.000001"))
backend/app/schemas/order_financial.py:87:    operating_profit_with_tax_refund = gross_profit + tax_refund
backend/app/schemas/order_financial.py:90:        "gross_profit": gross_profit,
backend/app/schemas/order_financial.py:91:        "gross_profit_rate": gross_profit_rate,
backend/app/schemas/order_financial.py:92:        "operating_profit_with_tax_refund": operating_profit_with_tax_refund,
backend/app/schemas/order_financial.py:152:    gross_profit: Decimal
backend/app/schemas/order_financial.py:153:    gross_profit_rate: Decimal | None
backend/app/schemas/order_financial.py:154:    operating_profit_with_tax_refund: Decimal
backend/app/schemas/order_financial.py:174:            "gross_profit",
backend/app/schemas/order_financial.py:175:            "gross_profit_rate",
backend/app/schemas/order_financial.py:176:            "operating_profit_with_tax_refund",
backend/app/schemas/order_financial.py:178:        if any(k not in values or values.get(k) is None and k != "gross_profit_rate"
backend/app/schemas/order_financial.py:180:            # gross_profit_rate は revenue=0 のとき正常に None になり得るので
backend/app/schemas/order_financial.py:185:                # cost_total / gross_profit / operating_profit_with_tax_refund のいずれかが
backend/app/schemas/order_financial.py:188:                    k != "gross_profit_rate" and values.get(k) is None
backend/app/schemas/order_financial.py:199:    受注 1 件 = 売上情報 1 件（無い場合もある）。order_financials があれば
backend/app/schemas/order_financial.py:200:    導出値（gross_profit / gross_profit_rate）を同梱し、無ければ null。
backend/app/schemas/order_financial.py:211:    gross_profit: Decimal | None = None
backend/app/schemas/order_financial.py:212:    gross_profit_rate: Decimal | None = None
backend/app/schemas/order_financial.py:225:    gross_profit_total: Decimal
backend/app/schemas/order_financial.py:226:    gross_profit_rate: Decimal | None  # 合計売上=0 のとき None
backend/app/schemas/order_financial.py:240:    gross_profit_total: Decimal
backend/app/schemas/order_financial.py:241:    gross_profit_rate: Decimal | None  # 合計売上=0 のとき None
backend/app/schemas/company.py:197:    total_deal_amount: Optional[Decimal] = None
backend/app/schemas/company.py:200:    deal_count: Optional[int] = None
backend/app/schemas/company.py:201:    conversation_count: Optional[int] = None
backend/app/schemas/company.py:202:    last_conversation_at: Optional[datetime] = None
backend/app/routers/order_financials.py:4:受注ごとの売上情報 API（order_financials）。
backend/app/routers/order_financials.py:19:導出列 (cost_total / gross_profit / gross_profit_rate /
backend/app/routers/order_financials.py:20:operating_profit_with_tax_refund) は Python 側で計算し、レスポンスに同梱する。
backend/app/routers/order_financials.py:103:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:105:        text(f"SELECT {_SELECT_COLS} FROM {order_financials_t} WHERE order_id = :order_id"),
backend/app/routers/order_financials.py:150:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:152:        INSERT INTO {order_financials_t} (
backend/app/routers/order_financials.py:179:        table_name="order_financials",
backend/app/routers/order_financials.py:243:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:245:        UPDATE {order_financials_t}
backend/app/routers/order_financials.py:258:        table_name="order_financials",
backend/app/routers/order_financials.py:287:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:289:        text(f"DELETE FROM {order_financials_t} WHERE order_id = :order_id"),
backend/app/routers/order_financials.py:298:        table_name="order_financials",
backend/app/routers/order_financials.py:324:    ADR-021 第 4 節 AC-004 の最小実装。集計範囲は order_financials.created_at が
backend/app/routers/order_financials.py:336:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:347:        FROM {order_financials_t}
backend/app/routers/order_financials.py:356:    gross_profit_total = revenue_total - cost_total
backend/app/routers/order_financials.py:360:        rate = (gross_profit_total / revenue_total).quantize(Decimal("0.000001"))
backend/app/routers/order_financials.py:368:        gross_profit_total=gross_profit_total,
backend/app/routers/order_financials.py:369:        gross_profit_rate=rate,
backend/app/routers/order_financials.py:397:    受注ごとに order_financials を LEFT JOIN し、売上 / 原価 / 粗利 / 粗利率を
backend/app/routers/order_financials.py:399:    導出値（gross_profit / gross_profit_rate）は SQL 側で計算する。
backend/app/routers/order_financials.py:405:    financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_financials.py:453:                gross_profit=gross,
backend/app/routers/order_financials.py:454:                gross_profit_rate=rate,
backend/app/routers/order_financials.py:458:    gross_profit_total = revenue_total - cost_total_sum
backend/app/routers/order_financials.py:460:        (gross_profit_total / revenue_total).quantize(Decimal("0.000001"))
backend/app/routers/order_financials.py:470:        gross_profit_total=gross_profit_total,
backend/app/routers/order_financials.py:471:        gross_profit_rate=total_rate,
backend/app/routers/leads.py:2621:            total_deal_amount=Decimal("0"),
backend/app/routers/leads.py:2624:            conversation_count=0,
backend/app/routers/leads.py:2625:            last_conversation_at=None,
backend/app/routers/leads.py:2633:                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
backend/app/routers/leads.py:2634:                       conversation_count, last_conversation_at
backend/app/routers/leads.py:2646:            total_deal_amount=Decimal("0"),
backend/app/routers/leads.py:2649:            conversation_count=0,
backend/app/routers/leads.py:2650:            last_conversation_at=None,
backend/app/routers/leads.py:2654:        total_deal_amount=Decimal(str(stats_row["total_deal_amount"] or 0)),
backend/app/routers/leads.py:2657:        conversation_count=int(stats_row["conversation_count"] or 0),
backend/app/routers/leads.py:2658:        last_conversation_at=stats_row["last_conversation_at"],
backend/app/routers/goals.py:312:    kpi_types_team = ["revenue", "deal_count", "close_rate", "lead_count", "conversion_rate"]
backend/app/routers/goals.py:313:    kpi_types_individual = ["revenue", "deal_count", "close_rate"]
backend/app/routers/goals.py:390:    deal_count = float(r.scalar() or 0)
backend/app/routers/goals.py:440:        "deal_count": deal_count,
backend/app/routers/order_commissions.py:19:  recalc は order の status / order_financials.commission_base_amount /
backend/app/routers/order_commissions.py:112:    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
backend/app/routers/order_commissions.py:115:            f"SELECT commission_base_amount FROM {order_financials_t} "

>>> rg -n "total_deal_amount|deal_count|conversation_count|last_conversation_at" backend/app/routers | head -50
backend/app/routers/companies.py:194:                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
backend/app/routers/companies.py:195:                       deal_count, conversation_count, last_conversation_at
backend/app/routers/leads.py:2621:            total_deal_amount=Decimal("0"),
backend/app/routers/leads.py:2624:            conversation_count=0,
backend/app/routers/leads.py:2625:            last_conversation_at=None,
backend/app/routers/leads.py:2633:                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
backend/app/routers/leads.py:2634:                       conversation_count, last_conversation_at
backend/app/routers/leads.py:2646:            total_deal_amount=Decimal("0"),
backend/app/routers/leads.py:2649:            conversation_count=0,
backend/app/routers/leads.py:2650:            last_conversation_at=None,
backend/app/routers/leads.py:2654:        total_deal_amount=Decimal(str(stats_row["total_deal_amount"] or 0)),
backend/app/routers/leads.py:2657:        conversation_count=int(stats_row["conversation_count"] or 0),
backend/app/routers/leads.py:2658:        last_conversation_at=stats_row["last_conversation_at"],
backend/app/routers/analytics.py:291:    open_deal_count: int
backend/app/routers/analytics.py:324:                COUNT(*) AS open_deal_count
backend/app/routers/analytics.py:348:        open_deal_count=int(row.get("open_deal_count", 0) or 0),
backend/app/routers/analytics.py:1211:    won_target = int(goals.get("won_count", goals.get("deal_count", 0)))
backend/app/routers/analytics.py:2217:                SELECT company_id, MAX(occurred_at) AS last_conversation_at
backend/app/routers/analytics.py:2225:            if company_id in candidate_company_ids and row["last_conversation_at"] is not None:
backend/app/routers/analytics.py:2226:                contact_last_seen[company_id] = row["last_conversation_at"]
backend/app/routers/goals.py:312:    kpi_types_team = ["revenue", "deal_count", "close_rate", "lead_count", "conversion_rate"]
backend/app/routers/goals.py:313:    kpi_types_individual = ["revenue", "deal_count", "close_rate"]
backend/app/routers/goals.py:390:    deal_count = float(r.scalar() or 0)
backend/app/routers/goals.py:440:        "deal_count": deal_count,

>>> rg -n "UPDATE .*total_deal_amount|UPDATE .*deal_count|UPDATE .*conversation_count|UPDATE .*last_conversation_at|INSERT INTO .*order_financials|UPDATE .*commission_base_amount" backend/app/routers backend/app/services || echo "なし"
backend/app/routers/order_financials.py:152:        INSERT INTO {order_financials_t} (

>>> nl -ba backend/app/routers/companies.py | sed -n "189,205p"
   189	async def _fetch_company_stats(db: AsyncSession, company_id: int) -> dict:
   190	    """v_company_stats ビューから集計値を取得。ビューが存在しない場合は空 dict を返す。"""
   191	    try:
   192	        res = await db.execute(
   193	            text("""
   194	                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
   195	                       deal_count, conversation_count, last_conversation_at
   196	                FROM v_company_stats
   197	                WHERE company_id = :cid
   198	            """),
   199	            {"cid": company_id},
   200	        )
   201	        row = res.mappings().first()
   202	        if row is None:
   203	            return {}
   204	        return dict(row)
   205	    except Exception:

>>> nl -ba backend/app/routers/leads.py | sed -n "2620,2659p"
  2620	        return LeadStatsResponse(
  2621	            total_deal_amount=Decimal("0"),
  2622	            paid_invoice_count=0,
  2623	            last_paid_at=None,
  2624	            conversation_count=0,
  2625	            last_conversation_at=None,
  2626	        )
  2627	
  2628	    company_id = co_row["id"]
  2629	
  2630	    try:
  2631	        stats_res = await db.execute(
  2632	            text("""
  2633	                SELECT total_deal_amount, paid_invoice_count, last_paid_at,
  2634	                       conversation_count, last_conversation_at
  2635	                FROM v_company_stats
  2636	                WHERE company_id = :cid
  2637	            """),
  2638	            {"cid": company_id},
  2639	        )
  2640	        stats_row = stats_res.mappings().first()
  2641	    except Exception:
  2642	        stats_row = None
  2643	
  2644	    if stats_row is None:
  2645	        return LeadStatsResponse(
  2646	            total_deal_amount=Decimal("0"),
  2647	            paid_invoice_count=0,
  2648	            last_paid_at=None,
  2649	            conversation_count=0,
  2650	            last_conversation_at=None,
  2651	        )
  2652	
  2653	    return LeadStatsResponse(
  2654	        total_deal_amount=Decimal(str(stats_row["total_deal_amount"] or 0)),
  2655	        paid_invoice_count=int(stats_row["paid_invoice_count"] or 0),
  2656	        last_paid_at=stats_row["last_paid_at"],
  2657	        conversation_count=int(stats_row["conversation_count"] or 0),
  2658	        last_conversation_at=stats_row["last_conversation_at"],
  2659	    )

>>> nl -ba backend/app/routers/order_financials.py | sed -n "140,265p"
   140	        )
   141	
   142	    payload = data.model_dump()
   143	    params = {
   144	        "tenant_id": tenant_id,
   145	        "order_id": order_id,
   146	        **{k: payload[k] for k in _NUMERIC_INPUT_COLUMNS},
   147	        "notes": payload.get("notes"),
   148	    }
   149	
   150	    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
   151	    insert_sql = text(f"""
   152	        INSERT INTO {order_financials_t} (
   153	            tenant_id, order_id,
   154	            revenue_amount, purchase_cost, purchase_shipping,
   155	            paypal_fee, wise_fee, exchange_fee,
   156	            outsource_fee, packing_fee, ad_cost,
   157	            return_fee, refund_amount,
   158	            commission_base_amount, tax_refund,
   159	            notes
   160	        ) VALUES (
   161	            :tenant_id, :order_id,
   162	            :revenue_amount, :purchase_cost, :purchase_shipping,
   163	            :paypal_fee, :wise_fee, :exchange_fee,
   164	            :outsource_fee, :packing_fee, :ad_cost,
   165	            :return_fee, :refund_amount,
   166	            :commission_base_amount, :tax_refund,
   167	            :notes
   168	        )
   169	        RETURNING {_SELECT_COLS}
   170	    """)
   171	    result = await db.execute(insert_sql, params)
   172	    row = result.mappings().first()
   173	
   174	    await record_audit_log(
   175	        db=db,
   176	        tenant_id=tenant_id,
   177	        user_id=current_user.id,
   178	        action="create",
   179	        table_name="order_financials",
   180	        record_id=row["id"],
   181	        new_data=data.model_dump(mode="json"),
   182	    )
   183	    await db.commit()
   184	
   185	    return _build_response(dict(row))
   186	
   187	
   188	@router.get(
   189	    "/orders/{order_id}/financial",
   190	    response_model=OrderFinancialResponse,
   191	    dependencies=[Depends(require_permission("orders.view"))],
   192	)
   193	async def get_order_financial(
   194	    order_id: int,
   195	    db: AsyncSession = Depends(get_db),
   196	    tenant_id: int = Depends(get_current_tenant),
   197	    current_user: User = Depends(get_current_user),
   198	):
   199	    """受注の売上情報を取得する。"""
   200	    row = await _fetch_financial_row(db, order_id, tenant_id)
   201	    if not row:
   202	        # 受注の有無は問わず 404（情報量を最小化）。
   203	        raise HTTPException(
   204	            status_code=status.HTTP_404_NOT_FOUND,
   205	            detail="売上情報が見つかりません",
   206	        )
   207	    return _build_response(row)
   208	
   209	
   210	@router.patch(
   211	    "/orders/{order_id}/financial",
   212	    response_model=OrderFinancialResponse,
   213	    dependencies=[Depends(require_permission("orders.update"))],
   214	)
   215	async def update_order_financial(
   216	    order_id: int,
   217	    data: OrderFinancialUpdate,
   218	    db: AsyncSession = Depends(get_db),
   219	    tenant_id: int = Depends(get_current_tenant),
   220	    current_user: User = Depends(get_current_user),
   221	):
   222	    """受注の売上情報を部分更新する（自動 updated_at）。"""
   223	    old_row = await _fetch_financial_row(db, order_id, tenant_id)
   224	    if not old_row:
   225	        raise HTTPException(
   226	            status_code=status.HTTP_404_NOT_FOUND,
   227	            detail="売上情報が見つかりません",
   228	        )
   229	
   230	    update_data = data.model_dump(exclude_unset=True)
   231	    # ホワイトリスト経由でのみ列を許可（FK / id / tenant_id / *_at は変更不可）
   232	    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
   233	    if not update_data:
   234	        raise HTTPException(
   235	            status_code=status.HTTP_400_BAD_REQUEST,
   236	            detail="更新するフィールドを指定してください",
   237	        )
   238	
   239	    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
   240	    params = dict(update_data)
   241	    params["order_id"] = order_id
   242	
   243	    order_financials_t = tenant_table_ref(db, tenant_id, "order_financials")
   244	    update_sql = text(f"""
   245	        UPDATE {order_financials_t}
   246	        SET {set_clauses}, updated_at = NOW()
   247	        WHERE order_id = :order_id
   248	        RETURNING {_SELECT_COLS}
   249	    """)
   250	    result = await db.execute(update_sql, params)
   251	    new_row = result.mappings().first()
   252	
   253	    await record_audit_log(
   254	        db=db,
   255	        tenant_id=tenant_id,
   256	        user_id=current_user.id,
   257	        action="update",
   258	        table_name="order_financials",
   259	        record_id=old_row["id"],
   260	        old_data=old_row,
   261	        new_data=update_data,
   262	    )
   263	    await db.commit()
   264	
   265	    return _build_response(dict(new_row))

>>> nl -ba backend/app/routers/order_shipping_details.py | sed -n "154,265p"
   154	    payload = data.model_dump(mode="python")
   155	    # ホワイトリスト経由で列を制限。明示指定された列のみ INSERT し、
   156	    # それ以外は DB の DEFAULT NULL に任せる。
   157	    insert_cols = ["tenant_id", "order_id"]
   158	    insert_vals = [":tenant_id", ":order_id"]
   159	    params: dict = {"tenant_id": tenant_id, "order_id": order_id}
   160	    for col in INPUT_FIELDS:
   161	        if col in payload:
   162	            insert_cols.append(col)
   163	            insert_vals.append(f":{col}")
   164	            params[col] = payload[col]
   165	
   166	    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
   167	    insert_sql = text(f"""
   168	        INSERT INTO {order_shipping_details_t} ({', '.join(insert_cols)})
   169	        VALUES ({', '.join(insert_vals)})
   170	        RETURNING {_SELECT_COLS}
   171	    """)
   172	    result = await db.execute(insert_sql, params)
   173	    row = result.mappings().first()
   174	
   175	    await record_audit_log(
   176	        db=db,
   177	        tenant_id=tenant_id,
   178	        user_id=current_user.id,
   179	        action="create",
   180	        table_name="order_shipping_details",
   181	        record_id=row["id"],
   182	        new_data=data.model_dump(mode="json", exclude_none=True),
   183	    )
   184	    await db.commit()
   185	
   186	    return OrderShippingDetailResponse(**dict(row))
   187	
   188	
   189	@router.get(
   190	    "/orders/{order_id}/shipping",
   191	    response_model=OrderShippingDetailResponse,
   192	    dependencies=[Depends(require_permission("orders.view"))],
   193	)
   194	async def get_order_shipping(
   195	    order_id: int,
   196	    db: AsyncSession = Depends(get_db),
   197	    tenant_id: int = Depends(get_current_tenant),
   198	    current_user: User = Depends(get_current_user),
   199	):
   200	    """受注の発送情報を取得する。"""
   201	    row = await _fetch_shipping_row(db, order_id, tenant_id)
   202	    if not row:
   203	        raise HTTPException(
   204	            status_code=status.HTTP_404_NOT_FOUND,
   205	            detail="発送情報が見つかりません",
   206	        )
   207	    return OrderShippingDetailResponse(**row)
   208	
   209	
   210	@router.patch(
   211	    "/orders/{order_id}/shipping",
   212	    response_model=OrderShippingDetailResponse,
   213	    dependencies=[Depends(require_permission("orders.update"))],
   214	)
   215	async def update_order_shipping(
   216	    order_id: int,
   217	    data: OrderShippingDetailUpdate,
   218	    db: AsyncSession = Depends(get_db),
   219	    tenant_id: int = Depends(get_current_tenant),
   220	    current_user: User = Depends(get_current_user),
   221	):
   222	    """受注の発送情報を部分更新する（自動 updated_at）。"""
   223	    old_row = await _fetch_shipping_row(db, order_id, tenant_id)
   224	    if not old_row:
   225	        raise HTTPException(
   226	            status_code=status.HTTP_404_NOT_FOUND,
   227	            detail="発送情報が見つかりません",
   228	        )
   229	
   230	    update_data = data.model_dump(exclude_unset=True, mode="python")
   231	    # ホワイトリスト経由でのみ列を許可（FK / id / tenant_id / *_at は変更不可）
   232	    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
   233	    if not update_data:
   234	        raise HTTPException(
   235	            status_code=status.HTTP_400_BAD_REQUEST,
   236	            detail="更新するフィールドを指定してください",
   237	        )
   238	
   239	    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
   240	    params = dict(update_data)
   241	    params["order_id"] = order_id
   242	
   243	    order_shipping_details_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
   244	    update_sql = text(f"""
   245	        UPDATE {order_shipping_details_t}
   246	        SET {set_clauses}, updated_at = NOW()
   247	        WHERE order_id = :order_id
   248	        RETURNING {_SELECT_COLS}
   249	    """)
   250	    result = await db.execute(update_sql, params)
   251	    new_row = result.mappings().first()
   252	
   253	    await record_audit_log(
   254	        db=db,
   255	        tenant_id=tenant_id,
   256	        user_id=current_user.id,
   257	        action="update",
   258	        table_name="order_shipping_details",
   259	        record_id=old_row["id"],
   260	        old_data=old_row,
   261	        new_data=update_data,
   262	    )
   263	    await db.commit()
   264	
   265	    return OrderShippingDetailResponse(**dict(new_row))

>>> rg -n "CREATE TABLE IF NOT EXISTS \{schema\}\.close_reasons|CREATE TABLE IF NOT EXISTS \{schema\}\.deal_close_reasons|close_reasons" backend/app/services/tenant.py migrations/*.sql backend/app/routers/deals.py backend/app/schemas/deal.py
migrations/20260613_020000_funnel_close_reasons.sql:4:--   テナント別の成約/失注理由マスタ（close_reasons）と
migrations/20260613_020000_funnel_close_reasons.sql:5:--   商談との中間表（deal_close_reasons）を作成する。
migrations/20260613_020000_funnel_close_reasons.sql:34:        -- ── 1. close_reasons マスタテーブル ──────────────────────────────────
migrations/20260613_020000_funnel_close_reasons.sql:36:            CREATE TABLE IF NOT EXISTS %I.close_reasons (
migrations/20260613_020000_funnel_close_reasons.sql:47:        -- ── 2. deal_close_reasons 中間表（主因1 + 副因複数）────────────────
migrations/20260613_020000_funnel_close_reasons.sql:49:            CREATE TABLE IF NOT EXISTS %I.deal_close_reasons (
migrations/20260613_020000_funnel_close_reasons.sql:54:                               REFERENCES %I.close_reasons(id),
migrations/20260613_020000_funnel_close_reasons.sql:65:            'CREATE INDEX IF NOT EXISTS idx_deal_close_reasons_deal
migrations/20260613_020000_funnel_close_reasons.sql:66:             ON %I.deal_close_reasons (deal_id)',
migrations/20260613_020000_funnel_close_reasons.sql:94:            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
migrations/20260613_020000_funnel_close_reasons.sql:107:            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
backend/app/routers/deals.py:257:    close_reasons_input = raw_update.pop("close_reasons", None)
backend/app/routers/deals.py:259:    if not update_data and close_reasons_input is None:
backend/app/routers/deals.py:271:        # close_reasons 必須チェック
backend/app/routers/deals.py:272:        if not close_reasons_input:
backend/app/routers/deals.py:275:                detail="成約/失注遷移時は close_reasons（主因1件必須）が必要です",
backend/app/routers/deals.py:277:        primary_count = sum(1 for r in close_reasons_input if r.get("is_primary"))
backend/app/routers/deals.py:365:    # close_reasons 登録（won/lost 遷移時）
backend/app/routers/deals.py:366:    if close_reasons_input and is_closing:
backend/app/routers/deals.py:367:        close_reasons_t = tenant_table_ref(db, tenant_id, "close_reasons")
backend/app/routers/deals.py:368:        deal_close_reasons_t = tenant_table_ref(db, tenant_id, "deal_close_reasons")
backend/app/routers/deals.py:371:            text(f"DELETE FROM {deal_close_reasons_t} WHERE deal_id = :did"),
backend/app/routers/deals.py:374:        for reason in close_reasons_input:
backend/app/routers/deals.py:377:                text(f"SELECT id FROM {close_reasons_t} WHERE id = :rid AND is_active = true"),
backend/app/routers/deals.py:387:                    INSERT INTO {deal_close_reasons_t} (deal_id, reason_id, is_primary)
backend/app/schemas/deal.py:19:  2026-06-13: PR3 — closed_at, close_reason_memo, close_reasons 追加
backend/app/schemas/deal.py:74:    reason_id: int = Field(ge=1, description="close_reasons.id")
backend/app/schemas/deal.py:94:    close_reasons: list[CloseReasonRef] | None = Field(default=None, description="成約/失注理由（主因1件必須）")

```

## Part B（本番DB・生出力・transaction_read_only=on）
```
=== date ===
Thu Jul  2 08:27:19 UTC 2026
=== B0 readonly ===
 transaction_read_only 
-----------------------
 on
(1 row)

=== R1 背骨NULL率 (tenant_004) ===
        col        | total | nn 
-------------------+-------+----
 deals.lead_id     |     0 |  0
 companies.lead_id |    51 |  2
 orders.deal_id    |     0 |  0
 conv.lead_id      |     6 |  5
(4 rows)

=== R2 6軸の実データ充足 (tenant_004) ===
                                                 Table "tenant_004.leads"
          Column          |           Type           | Collation | Nullable |                   Default                    
--------------------------+--------------------------+-----------+----------+----------------------------------------------
 id                       | integer                  |           | not null | nextval('tenant_004.leads_id_seq'::regclass)
 tenant_id                | integer                  |           | not null | 4
 lead_code                | character varying(20)    |           |          | 
 customer_name            | character varying(255)   |           | not null | 
 company_name             | character varying(255)   |           |          | 
 email                    | character varying(255)   |           |          | 
 phone                    | character varying(50)    |           |          | 
 type                     | character varying(50)    |           |          | 
 status                   | character varying(50)    |           |          | 'lead'::character varying
 temperature              | character varying(20)    |           |          | 
 estimated_scale          | character varying(20)    |           |          | 
 customer_type            | character varying(50)    |           |          | 
 response_speed           | character varying(20)    |           |          | 
 monthly_forecast         | numeric(15,2)            |           |          | 
 prospect_rank            | character varying(10)    |           |          | 
 assigned_to              | integer                  |           |          | 
 converted_deal_id        | integer                  |           |          | 
 notes                    | text                     |           |          | 
 created_at               | timestamp with time zone |           |          | now()
 updated_at               | timestamp with time zone |           |          | now()
 country                  | character varying(100)   |           |          | 
 target_titles            | character varying(500)   |           |          | 
 first_inquiry_at         | timestamp with time zone |           |          | 
 first_response_at        | timestamp with time zone |           |          | 
 first_response_seconds   | integer                  |           |          | 
 sales_form               | character varying(50)    |           |          | 
 competitor_check         | boolean                  |           | not null | false
 cs_memo                  | text                     |           |          | 
 per_order_amount         | numeric(15,2)            |           |          | 
 monthly_frequency        | numeric(10,2)            |           |          | 
 monthly_forecast_source  | character varying(50)    |           |          | 
 challenge                | text                     |           |          | 
 nickname                 | character varying(255)   |           |          | 
 meeting_impression       | character varying(50)    |           |          | 
 meeting_memo             | text                     |           |          | 
 next_action              | character varying(500)   |           |          | 
 next_action_date         | date                     |           |          | 
 ai_collection_state      | character varying(20)    |           |          | 
 escalation_flag          | boolean                  |           | not null | false
 english_name             | character varying(255)   |           |          | 
 discord_user_id          | character varying(50)    |           |          | 
 discord_dm_channel_id    | character varying(50)    |           |          | 
 messenger_link           | character varying(1000)  |           |          | 
 discord_id               | character varying(255)   |           |          | 
 instagram_link           | character varying(1000)  |           |          | 
 whatsapp_link            | character varying(1000)  |           |          | 
 discord_role_sync_status | character varying(20)    |           |          | 
 discord_role_sync_at     | timestamp with time zone |           |          | 
 discord_guild_channel_id | character varying(50)    |           |          | 
 initiative               | character varying(10)    |           |          | 
 channel_type             | character varying(30)    |           |          | 
Indexes:
    "leads_pkey" PRIMARY KEY, btree (id)
    "idx_leads_ai_collection_state" btree (ai_collection_state) WHERE ai_collection_state IS NOT NULL
    "idx_leads_channel_type" btree (channel_type)
    "idx_leads_discord_guild_channel_id" btree (tenant_id, discord_guild_channel_id) WHERE discord_guild_channel_id IS NOT NULL
    "idx_leads_discord_user_id" btree (tenant_id, discord_user_id) WHERE discord_user_id IS NOT NULL
    "idx_leads_escalation_flag" btree (escalation_flag) WHERE escalation_flag = true
    "idx_leads_initiative" btree (initiative) WHERE initiative IS NOT NULL
    "idx_leads_next_action_date" btree (next_action_date) WHERE next_action_date IS NOT NULL
Check constraints:
    "leads_initiative_check" CHECK (initiative IS NULL OR (initiative::text = ANY (ARRAY['outbound'::character varying, 'inbound'::character varying]::text[])))
Foreign-key constraints:
    "fk_leads_converted_deal" FOREIGN KEY (converted_deal_id) REFERENCES tenant_004.deals(id)
Referenced by:
    TABLE "tenant_004.companies" CONSTRAINT "companies_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id)
    TABLE "tenant_004.contacts" CONSTRAINT "contacts_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id)
    TABLE "tenant_004.deals" CONSTRAINT "deals_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id)
    TABLE "tenant_004.lead_channels" CONSTRAINT "lead_channels_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id) ON DELETE CASCADE
    TABLE "tenant_004.lead_sales_form_selections" CONSTRAINT "lead_sales_form_selections_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id) ON DELETE CASCADE
    TABLE "tenant_004.meta_messages" CONSTRAINT "meta_messages_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id) ON DELETE SET NULL
Policies:
    POLICY "tenant_isolation_leads"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

=== R5 orders/invoices 実列 (tenant_004) ===
                                             Table "tenant_004.orders"
      Column      |           Type           | Collation | Nullable |                    Default                    
------------------+--------------------------+-----------+----------+-----------------------------------------------
 id               | integer                  |           | not null | nextval('tenant_004.orders_id_seq'::regclass)
 tenant_id        | integer                  |           | not null | 4
 deal_id          | integer                  |           |          | 
 order_number     | character varying(100)   |           | not null | 
 total_amount     | numeric(15,2)            |           |          | 
 status           | character varying(50)    |           |          | 'pending'::character varying
 notes            | text                     |           |          | 
 created_at       | timestamp with time zone |           |          | now()
 updated_at       | timestamp with time zone |           |          | now()
 company_id       | integer                  |           | not null | 
 contact_id       | integer                  |           |          | 
 invoice_id       | integer                  |           |          | 
 currency         | character varying(10)    |           |          | 'JPY'::character varying
 shipping_carrier | character varying(50)    |           |          | 
 shipping_fee     | numeric(15,2)            |           |          | 
 tracking_number  | character varying(200)   |           |          | 
 shipped_at       | timestamp with time zone |           |          | 
 delivered_at     | timestamp with time zone |           |          | 
 shipping_country | character varying(100)   |           |          | 
 paid_at          | timestamp with time zone |           |          | 
Indexes:
    "orders_pkey" PRIMARY KEY, btree (id)
    "idx_orders_company_id" btree (company_id)
    "idx_orders_contact_id" btree (contact_id)
Foreign-key constraints:
    "fk_orders_company" FOREIGN KEY (company_id) REFERENCES tenant_004.companies(id)
    "fk_orders_contact" FOREIGN KEY (contact_id) REFERENCES tenant_004.contacts(id)
    "orders_deal_id_fkey" FOREIGN KEY (deal_id) REFERENCES tenant_004.deals(id)
Referenced by:
    TABLE "tenant_004.order_commissions" CONSTRAINT "order_commissions_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_004.orders(id) ON DELETE CASCADE
    TABLE "tenant_004.order_financials" CONSTRAINT "order_financials_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_004.orders(id) ON DELETE CASCADE
    TABLE "tenant_004.order_purchase_details" CONSTRAINT "order_purchase_details_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_004.orders(id) ON DELETE CASCADE
    TABLE "tenant_004.order_shipping_details" CONSTRAINT "order_shipping_details_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_004.orders(id) ON DELETE CASCADE
Policies:
    POLICY "tenant_isolation_orders"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

                                                 Table "tenant_004.invoices"
          Column          |           Type           | Collation | Nullable |                     Default                     
--------------------------+--------------------------+-----------+----------+-------------------------------------------------
 id                       | integer                  |           | not null | nextval('tenant_004.invoices_id_seq'::regclass)
 tenant_id                | integer                  |           | not null | 4
 invoice_number           | character varying(30)    |           |          | 
 quote_id                 | integer                  |           |          | 
 currency                 | character varying(10)    |           |          | 'JPY'::character varying
 subtotal                 | numeric(15,2)            |           |          | 0
 shipping_fee             | numeric(15,2)            |           |          | 0
 tax_amount               | numeric(15,2)            |           |          | 0
 total_amount             | numeric(15,2)            |           |          | 0
 exchange_rate_jpy        | numeric(12,4)            |           |          | 
 exchange_rate_usd        | numeric(12,4)            |           |          | 
 amount_jpy               | numeric(15,2)            |           |          | 
 amount_usd               | numeric(15,2)            |           |          | 
 payment_method           | character varying(50)    |           |          | 
 status                   | character varying(20)    |           |          | 'draft'::character varying
 branch_number            | integer                  |           |          | 1
 pdf_url                  | character varying(500)   |           |          | 
 erp_key                  | character varying(100)   |           |          | 
 issued_at                | timestamp with time zone |           |          | 
 due_date                 | date                     |           |          | 
 paid_at                  | timestamp with time zone |           |          | 
 voided_at                | timestamp with time zone |           |          | 
 void_reason              | character varying(500)   |           |          | 
 notes                    | text                     |           |          | 
 created_by               | integer                  |           |          | 
 created_at               | timestamp with time zone |           |          | now()
 updated_at               | timestamp with time zone |           |          | now()
 company_id               | integer                  |           | not null | 
 contact_id               | integer                  |           |          | 
 ship_to_snapshot         | jsonb                    |           |          | 
 bill_to_snapshot         | jsonb                    |           |          | 
 issue_mode               | character varying(20)    |           |          | 
 duty_amount              | numeric(15,2)            |           |          | 
 duty_policy_snapshot     | jsonb                    |           |          | 
 fx_rate_snapshot         | jsonb                    |           |          | 
 paypal_order_id          | text                     |           |          | 
 paypal_approval_url      | text                     |           |          | 
 payment_fee              | numeric(15,2)            |           |          | 
 paypal_invoicer_view_url | text                     |           |          | 
 paypal_copy_pdf          | bytea                    |           |          | 
 paypal_copy_pdf_at       | timestamp with time zone |           |          | 
Indexes:
    "invoices_pkey" PRIMARY KEY, btree (id)
    "idx_invoices_company_id" btree (company_id)
    "idx_invoices_contact_id" btree (contact_id)
Foreign-key constraints:
    "fk_invoices_company" FOREIGN KEY (company_id) REFERENCES tenant_004.companies(id)
    "fk_invoices_contact" FOREIGN KEY (contact_id) REFERENCES tenant_004.contacts(id)
    "invoices_quote_id_fkey" FOREIGN KEY (quote_id) REFERENCES tenant_004.quotes(id)
Referenced by:
    TABLE "tenant_004.invoice_items" CONSTRAINT "invoice_items_invoice_id_fkey" FOREIGN KEY (invoice_id) REFERENCES tenant_004.invoices(id) ON DELETE CASCADE
    TABLE "tenant_004.paypal_disputes" CONSTRAINT "paypal_disputes_invoice_id_fkey" FOREIGN KEY (invoice_id) REFERENCES tenant_004.invoices(id) ON DELETE SET NULL
Policies:
    POLICY "tenant_isolation_invoices"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

=== R5 決済・通貨の充足 (tenant_004) ===
 total | pm | cur 
-------+----+-----
     0 |  0 |   0
(1 row)

=== R6 派生値保存列の行数 (tenant_004) ===
 count 
-------
     0
(1 row)

=== R1 背骨NULL率 (tenant_006) ===
        col        | total | nn 
-------------------+-------+----
 deals.lead_id     |    18 |  0
 companies.lead_id |    30 |  5
 orders.deal_id    |    26 |  0
 conv.lead_id      |    13 | 10
(4 rows)

=== R2 6軸の実データ充足 (tenant_006) ===
                                                 Table "tenant_006.leads"
          Column          |           Type           | Collation | Nullable |                   Default                    
--------------------------+--------------------------+-----------+----------+----------------------------------------------
 id                       | integer                  |           | not null | nextval('tenant_006.leads_id_seq'::regclass)
 tenant_id                | integer                  |           | not null | 6
 lead_code                | character varying(20)    |           |          | 
 customer_name            | character varying(255)   |           | not null | 
 company_name             | character varying(255)   |           |          | 
 email                    | character varying(255)   |           |          | 
 phone                    | character varying(50)    |           |          | 
 type                     | character varying(50)    |           |          | 
 status                   | character varying(50)    |           |          | 'lead'::character varying
 temperature              | character varying(20)    |           |          | 
 estimated_scale          | character varying(20)    |           |          | 
 customer_type            | character varying(50)    |           |          | 
 response_speed           | character varying(20)    |           |          | 
 monthly_forecast         | numeric(15,2)            |           |          | 
 prospect_rank            | character varying(10)    |           |          | 
 assigned_to              | integer                  |           |          | 
 converted_deal_id        | integer                  |           |          | 
 notes                    | text                     |           |          | 
 country                  | character varying(100)   |           |          | 
 target_titles            | character varying(500)   |           |          | 
 first_inquiry_at         | timestamp with time zone |           |          | 
 first_response_at        | timestamp with time zone |           |          | 
 first_response_seconds   | integer                  |           |          | 
 sales_form               | character varying(50)    |           |          | 
 competitor_check         | boolean                  |           | not null | false
 cs_memo                  | text                     |           |          | 
 per_order_amount         | numeric(15,2)            |           |          | 
 monthly_frequency        | numeric(10,2)            |           |          | 
 monthly_forecast_source  | character varying(50)    |           |          | 
 challenge                | text                     |           |          | 
 nickname                 | character varying(255)   |           |          | 
 meeting_impression       | character varying(50)    |           |          | 
 meeting_memo             | text                     |           |          | 
 next_action              | character varying(500)   |           |          | 
 next_action_date         | date                     |           |          | 
 ai_collection_state      | character varying(20)    |           |          | 
 escalation_flag          | boolean                  |           | not null | false
 created_at               | timestamp with time zone |           |          | now()
 updated_at               | timestamp with time zone |           |          | now()
 english_name             | character varying(255)   |           |          | 
 discord_user_id          | character varying(50)    |           |          | 
 discord_dm_channel_id    | character varying(50)    |           |          | 
 messenger_link           | character varying(1000)  |           |          | 
 discord_id               | character varying(255)   |           |          | 
 instagram_link           | character varying(1000)  |           |          | 
 whatsapp_link            | character varying(1000)  |           |          | 
 discord_role_sync_status | character varying(20)    |           |          | 
 discord_role_sync_at     | timestamp with time zone |           |          | 
 discord_guild_channel_id | character varying(50)    |           |          | 
 initiative               | character varying(10)    |           |          | 
 channel_type             | character varying(30)    |           |          | 
Indexes:
    "leads_pkey" PRIMARY KEY, btree (id)
    "idx_leads_ai_collection_state" btree (ai_collection_state) WHERE ai_collection_state IS NOT NULL
    "idx_leads_channel_type" btree (channel_type)
    "idx_leads_discord_guild_channel_id" btree (tenant_id, discord_guild_channel_id) WHERE discord_guild_channel_id IS NOT NULL
    "idx_leads_discord_user_id" btree (tenant_id, discord_user_id) WHERE discord_user_id IS NOT NULL
    "idx_leads_escalation_flag" btree (escalation_flag) WHERE escalation_flag = true
    "idx_leads_initiative" btree (initiative) WHERE initiative IS NOT NULL
    "idx_leads_next_action_date" btree (next_action_date) WHERE next_action_date IS NOT NULL
Check constraints:
    "leads_initiative_check" CHECK (initiative IS NULL OR (initiative::text = ANY (ARRAY['outbound'::character varying, 'inbound'::character varying]::text[])))
Foreign-key constraints:
    "fk_leads_converted_deal" FOREIGN KEY (converted_deal_id) REFERENCES tenant_006.deals(id)
Referenced by:
    TABLE "tenant_006.deals" CONSTRAINT "deals_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id)
    TABLE "tenant_006.companies" CONSTRAINT "fk_companies_lead" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id)
    TABLE "tenant_006.contacts" CONSTRAINT "fk_contacts_lead" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id)
    TABLE "tenant_006.lead_channels" CONSTRAINT "lead_channels_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id) ON DELETE CASCADE
    TABLE "tenant_006.lead_sales_form_selections" CONSTRAINT "lead_sales_form_selections_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id) ON DELETE CASCADE
    TABLE "tenant_006.meta_messages" CONSTRAINT "meta_messages_lead_id_fkey" FOREIGN KEY (lead_id) REFERENCES tenant_006.leads(id) ON DELETE SET NULL
Policies:
    POLICY "tenant_isolation_leads"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

=== R5 orders/invoices 実列 (tenant_006) ===
                                             Table "tenant_006.orders"
      Column      |           Type           | Collation | Nullable |                    Default                    
------------------+--------------------------+-----------+----------+-----------------------------------------------
 id               | integer                  |           | not null | nextval('tenant_006.orders_id_seq'::regclass)
 tenant_id        | integer                  |           | not null | 6
 company_id       | integer                  |           | not null | 
 contact_id       | integer                  |           |          | 
 deal_id          | integer                  |           |          | 
 order_number     | character varying(100)   |           | not null | 
 total_amount     | numeric(15,2)            |           |          | 
 status           | character varying(50)    |           |          | 'pending'::character varying
 notes            | text                     |           |          | 
 created_at       | timestamp with time zone |           |          | now()
 updated_at       | timestamp with time zone |           |          | now()
 invoice_id       | integer                  |           |          | 
 currency         | character varying(10)    |           |          | 'JPY'::character varying
 shipping_carrier | character varying(50)    |           |          | 
 shipping_fee     | numeric(15,2)            |           |          | 
 tracking_number  | character varying(200)   |           |          | 
 shipped_at       | timestamp with time zone |           |          | 
 delivered_at     | timestamp with time zone |           |          | 
 shipping_country | character varying(100)   |           |          | 
 paid_at          | timestamp with time zone |           |          | 
Indexes:
    "orders_pkey" PRIMARY KEY, btree (id)
    "idx_orders_company_id" btree (company_id)
    "idx_orders_contact_id" btree (contact_id)
Foreign-key constraints:
    "fk_orders_company" FOREIGN KEY (company_id) REFERENCES tenant_006.companies(id)
    "fk_orders_contact" FOREIGN KEY (contact_id) REFERENCES tenant_006.contacts(id)
    "orders_deal_id_fkey" FOREIGN KEY (deal_id) REFERENCES tenant_006.deals(id)
Referenced by:
    TABLE "tenant_006.order_commissions" CONSTRAINT "order_commissions_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_006.orders(id) ON DELETE CASCADE
    TABLE "tenant_006.order_financials" CONSTRAINT "order_financials_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_006.orders(id) ON DELETE CASCADE
    TABLE "tenant_006.order_purchase_details" CONSTRAINT "order_purchase_details_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_006.orders(id) ON DELETE CASCADE
    TABLE "tenant_006.order_shipping_details" CONSTRAINT "order_shipping_details_order_id_fkey" FOREIGN KEY (order_id) REFERENCES tenant_006.orders(id) ON DELETE CASCADE
Policies:
    POLICY "tenant_isolation_orders"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

                                                 Table "tenant_006.invoices"
          Column          |           Type           | Collation | Nullable |                     Default                     
--------------------------+--------------------------+-----------+----------+-------------------------------------------------
 id                       | integer                  |           | not null | nextval('tenant_006.invoices_id_seq'::regclass)
 tenant_id                | integer                  |           | not null | 6
 invoice_number           | character varying(30)    |           |          | 
 quote_id                 | integer                  |           |          | 
 company_id               | integer                  |           | not null | 
 contact_id               | integer                  |           |          | 
 currency                 | character varying(10)    |           |          | 'JPY'::character varying
 subtotal                 | numeric(15,2)            |           |          | 0
 shipping_fee             | numeric(15,2)            |           |          | 0
 tax_amount               | numeric(15,2)            |           |          | 0
 total_amount             | numeric(15,2)            |           |          | 0
 exchange_rate_jpy        | numeric(12,4)            |           |          | 
 exchange_rate_usd        | numeric(12,4)            |           |          | 
 amount_jpy               | numeric(15,2)            |           |          | 
 amount_usd               | numeric(15,2)            |           |          | 
 payment_method           | character varying(50)    |           |          | 
 status                   | character varying(20)    |           |          | 'draft'::character varying
 branch_number            | integer                  |           |          | 1
 pdf_url                  | character varying(500)   |           |          | 
 erp_key                  | character varying(100)   |           |          | 
 issued_at                | timestamp with time zone |           |          | 
 due_date                 | date                     |           |          | 
 paid_at                  | timestamp with time zone |           |          | 
 voided_at                | timestamp with time zone |           |          | 
 void_reason              | character varying(500)   |           |          | 
 notes                    | text                     |           |          | 
 created_by               | integer                  |           |          | 
 created_at               | timestamp with time zone |           |          | now()
 updated_at               | timestamp with time zone |           |          | now()
 ship_to_snapshot         | jsonb                    |           |          | 
 bill_to_snapshot         | jsonb                    |           |          | 
 issue_mode               | character varying(20)    |           |          | 
 duty_amount              | numeric(15,2)            |           |          | 
 duty_policy_snapshot     | jsonb                    |           |          | 
 fx_rate_snapshot         | jsonb                    |           |          | 
 paypal_order_id          | text                     |           |          | 
 paypal_approval_url      | text                     |           |          | 
 payment_fee              | numeric(15,2)            |           |          | 
 paypal_invoicer_view_url | text                     |           |          | 
 paypal_copy_pdf          | bytea                    |           |          | 
 paypal_copy_pdf_at       | timestamp with time zone |           |          | 
Indexes:
    "invoices_pkey" PRIMARY KEY, btree (id)
    "idx_invoices_company_id" btree (company_id)
    "idx_invoices_contact_id" btree (contact_id)
Foreign-key constraints:
    "fk_invoices_company" FOREIGN KEY (company_id) REFERENCES tenant_006.companies(id)
    "fk_invoices_contact" FOREIGN KEY (contact_id) REFERENCES tenant_006.contacts(id)
    "invoices_quote_id_fkey" FOREIGN KEY (quote_id) REFERENCES tenant_006.quotes(id)
Referenced by:
    TABLE "tenant_006.invoice_items" CONSTRAINT "invoice_items_invoice_id_fkey" FOREIGN KEY (invoice_id) REFERENCES tenant_006.invoices(id) ON DELETE CASCADE
    TABLE "tenant_006.paypal_disputes" CONSTRAINT "paypal_disputes_invoice_id_fkey" FOREIGN KEY (invoice_id) REFERENCES tenant_006.invoices(id) ON DELETE SET NULL
Policies:
    POLICY "tenant_isolation_invoices"
      USING ((tenant_id = (current_setting('app.tenant_id'::text, true))::integer))

=== R5 決済・通貨の充足 (tenant_006) ===
 total | pm | cur 
-------+----+-----
     0 |  0 |   0
(1 row)

=== R6 派生値保存列の行数 (tenant_006) ===
 count 
-------
     9
(1 row)

```
