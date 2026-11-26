from __future__ import annotations

"""
テナント別スキーマ自動生成サービス。

新しいテナントが登録されるたびに:
  1. public.tenants に企業情報を保存
  2. tenant_{id:03d} スキーマを自動作成
  3. スキーマ内に業務テーブル（companies, contacts, deals, orders, audit_logs,
     roles, role_permissions, user_roles, leads, teams, team_members）を作成
  4. Row Level Security（RLS）ポリシーを自動適用
  5. システムロール（オーナー/メンバー）をシード

たとえ話:
  新しい入居者（テナント企業）が契約したら、
  専用の鍵付き個室が自動的に用意される仕組み。

変更履歴:
  2026-04-16: Phase 1対応（roles/leads/teams追加、system_rolesシード）
  2026-05-07: ADR-015 段階分割 Phase 1 — leads にカルテ・AI 収集・返信速度・
    次回アクション列を追加、lead_playbook 新設、customer_contact_channels に
    external_id 追加（migration 046 と同じ列を新テナント作成時から備える）
  ADR-089 Sprint 5: customers/customer_*テーブル定義を削除（新テナントは最初から
    companies モデルのみ）。company_discord を追加。
"""

import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.system_roles import ROLE_KEY_ADMIN, ROLE_KEY_MANAGER, ROLE_KEY_OWNER, SYSTEM_MANAGE_KEY

logger = logging.getLogger(__name__)

# GAS版互換の既定ロール定義。テナント作成時に自動シードされる。
#
# 「permissions」キーの値:
#   - "ALL": 全権限付与
#   - "ALL_EXCEPT_SYSTEM_MANAGE": system.manage 以外の全権限
#   - list[str]: 指定された権限キーのみ付与
#
# is_system=True の役割は編集/削除不可（オーナーのみ）。
# その他の5役割は default として作成されるがテナント管理者が自由に編集可能。
#
# 変更履歴:
#   2026-06-26: 共通6ロール化 段階A — リーダー→マネージャー改名、仕入れ・発送を追加
DEFAULT_ROLES = [
    {
        "name": "オーナー",
        "color": "#6366f1",  # インディゴ（最高権限レベル）
        "priority": 1000,
        "is_system": True,
        "system_key": ROLE_KEY_OWNER,
        "permissions": "ALL",
        "description": "テナントの全権限を持つシステムロール",
    },
    {
        "name": "システム管理者",
        "color": "#a855f7",  # 紫
        "priority": 900,
        "is_system": True,
        "system_key": ROLE_KEY_ADMIN,
        "permissions": "ALL_EXCEPT_SYSTEM_MANAGE",
        "description": "システム設定以外の全機能を管理する管理者",
    },
    {
        "name": "マネージャー",
        "color": "#3b82f6",  # 青
        "priority": 500,
        "is_system": False,
        "system_key": ROLE_KEY_MANAGER,
        "permissions": [
            "dashboard.view", "reports.view", "reports.export",
            "customers.view", "customers.update",
            "leads.view", "leads.create", "leads.update", "leads.delete", "leads.convert",
            "leads.discord_invite", "leads.discord_resync", "leads.discord_remove_channel", "leads.discord_kick", "leads.discord_ban",
            "deals.view", "deals.update",
            "orders.view",
            "teams.view", "teams.manage_members",
            # Phase 2
            "products.view",
            "quotes.view", "quotes.update", "quotes.approve",
            "invoices.view", "invoices.update",
            "shipping.view", "shipping.calculate",
            # Phase 3
            "suppliers.view",
            "purchase_orders.view", "purchase_orders.create", "purchase_orders.update", "purchase_orders.receive",
            # Phase 4
            "notifications.view",
            "staff_reports.view_own", "staff_reports.view_team", "staff_reports.create", "staff_reports.review",
            "archive.view",
            # 目標管理（migration 075 と同じ状態）
            "goals.view", "goals.edit",
        ],
        "description": "チーム単位でリードや案件を統括するマネージャー",
    },
    {
        "name": "営業",
        "color": "#22c55e",  # 緑
        "priority": 300,
        "is_system": False,
        "permissions": [
            "dashboard.view", "reports.view",
            "customers.view", "customers.create", "customers.update",
            "leads.view", "leads.create", "leads.update", "leads.convert",
            "leads.discord_invite", "leads.discord_resync",
            "deals.view", "deals.create", "deals.update",
            "orders.view", "orders.create", "orders.update",
            # Phase 2
            "products.view",
            "quotes.view", "quotes.create", "quotes.update",
            "invoices.view", "invoices.create",
            "shipping.view", "shipping.calculate",
            # Phase 3
            "suppliers.view",
            "purchase_orders.view", "purchase_orders.create",
            # Phase 4
            "staff_reports.view_own", "staff_reports.create",
            "goals.view",
        ],
        "description": "顧客獲得から受注までを担当する営業担当者",
    },
    {
        "name": "CS",
        "color": "#f97316",  # オレンジ
        "priority": 300,
        "is_system": False,
        "permissions": [
            "dashboard.view", "reports.view",
            "customers.view", "customers.update",
            "leads.view",
            "deals.view",
            "orders.view",
            "teams.view",
            # Phase 2
            "products.view",
            "quotes.view",
            "invoices.view",
            "shipping.view",
            # Phase 4
            "staff_reports.view_own", "staff_reports.create",
            "goals.view",
        ],
        "description": "顧客からの問い合わせ対応を担当するカスタマーサポート",
    },
    {
        "name": "仕入れ",
        "color": "#06b6d4",  # シアン
        "priority": 450,
        "is_system": False,
        "permissions": [
            "dashboard.view", "reports.view",
            # 商品・仕入先
            "products.view",
            "suppliers.view", "suppliers.create", "suppliers.update",
            # 発注管理（フル）
            "purchase_orders.view", "purchase_orders.create",
            "purchase_orders.update", "purchase_orders.receive",
            # Phase 4
            "staff_reports.view_own", "staff_reports.create",
            "goals.view",
        ],
        "description": "仕入先管理と発注業務を担当する仕入れ担当者",
    },
    {
        "name": "発送",
        "color": "#84cc16",  # ライム
        "priority": 350,
        "is_system": False,
        "permissions": [
            "dashboard.view", "reports.view",
            # 商品確認
            "products.view",
            # 注文確認・更新
            "orders.view", "orders.update",
            # 配送管理（フル）
            "shipping.view", "shipping.calculate", "shipping.manage",
            # Phase 4
            "staff_reports.view_own", "staff_reports.create",
            "goals.view",
        ],
        "description": "受注後の梱包・出荷・配送を担当する発送担当者",
    },
]


# 新規ユーザー登録時に自動付与するデフォルトロール名（auth.py から参照）
DEFAULT_NEW_USER_ROLE = "CS"


# テナントスキーマ内に作成する業務テーブルのSQL定義
_TENANT_TABLES_SQL = """
-- ADR-089 Sprint 5: customers/customer_* テーブル定義を削除。
-- 新テナントは最初から companies モデルのみ。
-- 既存テナントの customers/* テーブルは Sprint 7 の DROP migration で削除する。

-- Phase 1-B-2: companies + contacts 階層（新テナントは最初から新構造）
CREATE TABLE IF NOT EXISTS {schema}.companies (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    company_code VARCHAR(20) NOT NULL,
    lead_id INTEGER NOT NULL,                          -- FK は leads 作成後に付与（便1a）
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    normalized_name VARCHAR(255),
    -- is_individual は Phase 1-B-2 Step 5a で削除（個人/法人の区別を撤廃、migration 033）
    industry VARCHAR(100),
    website VARCHAR(255),
    trust_level SMALLINT CHECK (trust_level IS NULL OR trust_level BETWEEN 1 AND 5),
    priority_focus VARCHAR(50),
    per_order_amount NUMERIC(15,2),
    monthly_frequency SMALLINT,
    monthly_forecast NUMERIC(15,2),
    monthly_forecast_source VARCHAR(20)
        CHECK (monthly_forecast_source IS NULL OR monthly_forecast_source IN ('manual','ai_analysis')),
    monthly_forecast_updated_at TIMESTAMPTZ,
    billing_display_name VARCHAR(255),
    payment_recipient_name VARCHAR(255),
    fedex_account VARCHAR(100),
    shipping_note TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        REFERENCES public.customer_statuses(code),
    sales_rep_id INTEGER,                             -- FK は public.users(id) へ付与（ADR-1008）
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, company_code)
);
CREATE INDEX IF NOT EXISTS idx_companies_tenant_id ON {schema}.companies (tenant_id);
CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON {schema}.companies (normalized_name);
CREATE INDEX IF NOT EXISTS idx_companies_lead_id ON {schema}.companies (lead_id);
CREATE INDEX IF NOT EXISTS idx_companies_sales_rep_id ON {schema}.companies (sales_rep_id);
CREATE INDEX IF NOT EXISTS idx_companies_status ON {schema}.companies (status);

CREATE TABLE IF NOT EXISTS {schema}.contacts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    company_id INTEGER NOT NULL REFERENCES {schema}.companies(id) ON DELETE CASCADE,
    contact_code VARCHAR(20) NOT NULL,
    lead_id INTEGER,                                   -- FK は leads 作成後に付与
    surname VARCHAR(100),
    given_name VARCHAR(100),
    display_name VARCHAR(255),
    job_title VARCHAR(100),
    department VARCHAR(100),
    is_primary_contact BOOLEAN NOT NULL DEFAULT FALSE,
    primary_email VARCHAR(255),
    primary_phone VARCHAR(50),
    -- 状態の記号は public.customer_statuses の4行が正本（ADR-1076・便2）。
    -- companies.status と同じく外部キーで結ぶ（値の一覧をここに書かない）。
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        REFERENCES public.customer_statuses(code),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, contact_code)
);
CREATE INDEX IF NOT EXISTS idx_contacts_tenant_id ON {schema}.contacts (tenant_id);
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON {schema}.contacts (company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_lead_id ON {schema}.contacts (lead_id);
CREATE INDEX IF NOT EXISTS idx_contacts_primary_email ON {schema}.contacts (primary_email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_one_primary_per_company
    ON {schema}.contacts (company_id) WHERE is_primary_contact = TRUE;

-- companies/contacts 副テーブル 5本
CREATE TABLE IF NOT EXISTS {schema}.company_addresses (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES {schema}.companies(id) ON DELETE CASCADE,
    address_type VARCHAR(20) NOT NULL CHECK (address_type IN ('billing','delivery')),
    branch_name VARCHAR(100),
    name VARCHAR(255),
    email VARCHAR(255),
    telephone VARCHAR(50),
    tax_id VARCHAR(100),
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    address_line_3 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    zip VARCHAR(50),
    country_code CHAR(2),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_company_addresses_company_id ON {schema}.company_addresses (company_id);
CREATE INDEX IF NOT EXISTS idx_company_addresses_type ON {schema}.company_addresses (company_id, address_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_addresses_one_default
    ON {schema}.company_addresses (company_id, address_type) WHERE is_default = TRUE;

CREATE TABLE IF NOT EXISTS {schema}.company_sales_channels (
    company_id INTEGER NOT NULL REFERENCES {schema}.companies(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (company_id, channel)
);

-- ADR-089 Sprint 1 / migration 097 と同等: 新テナントも最初から company_discord を保持
CREATE TABLE IF NOT EXISTS {schema}.company_discord (
    company_id INTEGER PRIMARY KEY REFERENCES {schema}.companies(id) ON DELETE CASCADE,
    is_joined BOOLEAN NOT NULL DEFAULT FALSE,
    channel_id VARCHAR(50),
    user_id VARCHAR(50),
    invoice_webhook TEXT,
    shipment_webhook TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS {schema}.contact_emails (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES {schema}.contacts(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    purpose VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (contact_id, email)
);
CREATE INDEX IF NOT EXISTS idx_contact_emails_contact_id ON {schema}.contact_emails (contact_id);

CREATE TABLE IF NOT EXISTS {schema}.contact_discord (
    contact_id INTEGER PRIMARY KEY REFERENCES {schema}.contacts(id) ON DELETE CASCADE,
    is_joined BOOLEAN NOT NULL DEFAULT FALSE,
    channel_id VARCHAR(50),
    user_id VARCHAR(50),
    invoice_webhook TEXT,
    shipment_webhook TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS {schema}.contact_contact_channels (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES {schema}.contacts(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL,
    purpose VARCHAR(50),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ccc_new_contact_id ON {schema}.contact_contact_channels (contact_id);
CREATE INDEX IF NOT EXISTS idx_ccc_new_channel ON {schema}.contact_contact_channels (channel);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ccc_new_one_primary_per_contact
    ON {schema}.contact_contact_channels (contact_id) WHERE is_primary = TRUE;

-- Phase 1-B-2 Step 5d / PR γ:
--   _customer_migration_map は migration 036 で DROP 済。
--   新テナント作成時は本テーブル不要のため CREATE TABLE ブロックを撤去した。
--   過去履歴: migration 031 で追加 → migration 034 で UNIQUE 付与 → migration 036 で DROP。

-- リード管理
-- ADR-015 §1〜§5 のカルテ・AI 収集・返信速度・次回アクション列を含める
-- （migration 046 と同じ列を新テナント作成時から備える）
CREATE TABLE IF NOT EXISTS {schema}.leads (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    lead_code VARCHAR(20),
    customer_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    channel_type VARCHAR(30),
    initiative VARCHAR(10) CONSTRAINT leads_initiative_check CHECK (initiative IS NULL OR initiative IN ('outbound', 'inbound')),
    type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'lead',
    temperature VARCHAR(20),
    estimated_scale VARCHAR(20),
    customer_type VARCHAR(50),
    response_speed VARCHAR(20),
    monthly_forecast NUMERIC(15, 2),
    amount NUMERIC(15, 2),
    currency VARCHAR(10) DEFAULT 'JPY',
    expected_close_date DATE,
    prospect_rank VARCHAR(10),
    assigned_to INTEGER,
    assignment_opened_at TIMESTAMPTZ,
    notes TEXT,
    -- ADR-015 §1/§2: AI 自動収集データ
    country VARCHAR(100),
    target_titles VARCHAR(500),
    -- ADR-015 §3: 返信速度トラッキング
    first_inquiry_at TIMESTAMPTZ,
    first_response_at TIMESTAMPTZ,
    first_response_seconds INTEGER,
    -- ADR-015 §4: カルテ AI 補助対象
    sales_form VARCHAR(50),
    competitor_check BOOLEAN NOT NULL DEFAULT FALSE,
    cs_memo TEXT,
    per_order_amount NUMERIC(15, 2),
    monthly_frequency NUMERIC(10, 2),
    monthly_forecast_source VARCHAR(50),
    -- ADR-015 §4: 営業担当が記入する列
    challenge TEXT,
    nickname VARCHAR(255),
    meeting_impression VARCHAR(50),
    meeting_memo TEXT,
    -- ADR-015 §5: ダッシュボードの次回アクション
    next_action VARCHAR(500),
    next_action_date DATE,
    -- ADR-015 §1/§2/§3: AI 収集ステート
    ai_collection_state VARCHAR(20),
    escalation_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_leads_next_action_date
    ON {schema}.leads (next_action_date) WHERE next_action_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_ai_collection_state
    ON {schema}.leads (ai_collection_state) WHERE ai_collection_state IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_escalation_flag
    ON {schema}.leads (escalation_flag) WHERE escalation_flag = TRUE;

-- ADR-015 §7: テナント別 AI 対応プレイブック
CREATE TABLE IF NOT EXISTS {schema}.lead_playbook (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    name VARCHAR(100) NOT NULL DEFAULT 'default',
    greeting_message TEXT,
    questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    assignment_condition VARCHAR(50) NOT NULL DEFAULT 'all_required',
    assignment_after_n_turns INTEGER,
    assignment_message TEXT,
    assignment_method VARCHAR(50) NOT NULL DEFAULT 'manual',
    country_assignment_map JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);
CREATE INDEX IF NOT EXISTS idx_lead_playbook_active
    ON {schema}.lead_playbook (tenant_id) WHERE is_active = TRUE;

-- 便D-1: deals テーブルDDL・インデックス・FK は新規テナント作成定義から除去済み（2026-07-28）
-- deals テーブル本体の DROP は便E で実施。既存テナントの deals は便D-1 では触らない。

-- Phase 1-B-2: companies.lead_id / contacts.lead_id → leads.id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_companies_lead'
          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
    ) THEN
        ALTER TABLE {schema}.companies
            ADD CONSTRAINT fk_companies_lead
            FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_contacts_lead'
          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
    ) THEN
        ALTER TABLE {schema}.contacts
            ADD CONSTRAINT fk_contacts_lead
            FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
    END IF;
END $$;

-- 注文データ
CREATE TABLE IF NOT EXISTS {schema}.orders (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
    company_id INTEGER NOT NULL CONSTRAINT fk_orders_company REFERENCES {schema}.companies(id),
    contact_id INTEGER CONSTRAINT fk_orders_contact REFERENCES {schema}.contacts(id),
    order_number VARCHAR(100) NOT NULL,
    total_amount NUMERIC(15, 2),
    status VARCHAR(50) DEFAULT 'pending',
    -- 支払済日時（NULL=未払い）。受注ステータスフロー判定の「支払済フラグ」。
    -- migration 20260604_050000 と同期。
    paid_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_company_id ON {schema}.orders (company_id);
CREATE INDEX IF NOT EXISTS idx_orders_contact_id ON {schema}.orders (contact_id);

-- 操作履歴（監査ログ）
CREATE TABLE IF NOT EXISTS {schema}.audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    user_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER,
    old_data JSONB,
    new_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ロール（Discord方式のカスタムロール）
CREATE TABLE IF NOT EXISTS {schema}.roles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#6c757d',
    priority INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    description VARCHAR(500),
    system_key TEXT,
    discord_role_id TEXT,                   -- つながる Discord のロールの番号（discord-server-management 第2段）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key ON {schema}.roles (system_key) WHERE system_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON {schema}.roles (discord_role_id) WHERE discord_role_id IS NOT NULL;

-- ロール×権限のリンク
CREATE TABLE IF NOT EXISTS {schema}.role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES {schema}.roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- ユーザー×ロールのリンク（多対多）
CREATE TABLE IF NOT EXISTS {schema}.user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL REFERENCES {schema}.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by INTEGER,
    UNIQUE(user_id, role_id)
);

-- チーム
CREATE TABLE IF NOT EXISTS {schema}.teams (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    name VARCHAR(100) NOT NULL,
    leader_id INTEGER,
    description VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE TABLE IF NOT EXISTS {schema}.team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES {schema}.teams(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- === Phase 1 再設計: updated_at 自動更新トリガ ===

CREATE OR REPLACE FUNCTION {schema}.trg_set_updated_at()
RETURNS TRIGGER AS $fn$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $fn$ LANGUAGE plpgsql;

DO $$
BEGIN
    -- Phase 1-B-2: companies + contacts 階層（migration 028-030 と同じトリガ名で idempotent）
    -- ADR-089 Sprint 5: customers/customer_* トリガ削除済（新テナントは company_discord のみ）
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_companies_updated_at' AND tgrelid = '{schema}.companies'::regclass) THEN
        CREATE TRIGGER trg_companies_updated_at BEFORE UPDATE ON {schema}.companies
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_contacts_updated_at' AND tgrelid = '{schema}.contacts'::regclass) THEN
        CREATE TRIGGER trg_contacts_updated_at BEFORE UPDATE ON {schema}.contacts
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_company_addresses_updated_at' AND tgrelid = '{schema}.company_addresses'::regclass) THEN
        CREATE TRIGGER trg_company_addresses_updated_at BEFORE UPDATE ON {schema}.company_addresses
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_contact_discord_updated_at' AND tgrelid = '{schema}.contact_discord'::regclass) THEN
        CREATE TRIGGER trg_contact_discord_updated_at BEFORE UPDATE ON {schema}.contact_discord
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    -- ADR-089 Sprint 1/Sprint 5: company_discord の updated_at 自動更新
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_company_discord_updated_at' AND tgrelid = '{schema}.company_discord'::regclass) THEN
        CREATE TRIGGER trg_company_discord_updated_at BEFORE UPDATE ON {schema}.company_discord
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_ccc_new_updated_at' AND tgrelid = '{schema}.contact_contact_channels'::regclass) THEN
        CREATE TRIGGER trg_ccc_new_updated_at BEFORE UPDATE ON {schema}.contact_contact_channels
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    -- ADR-015 §7: lead_playbook の updated_at 自動更新
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_lead_playbook_updated_at' AND tgrelid = '{schema}.lead_playbook'::regclass) THEN
        CREATE TRIGGER trg_lead_playbook_updated_at BEFORE UPDATE ON {schema}.lead_playbook
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
END $$;

-- === Phase 1 再設計: スタッフ・bot ===

-- 人間スタッフ（public.users との1対1紐付け）
CREATE TABLE IF NOT EXISTS {schema}.staff (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id),
    staff_code VARCHAR(20) NOT NULL,
    surname_jp VARCHAR(50) NOT NULL,
    given_name_jp VARCHAR(50) NOT NULL,
    surname_kana VARCHAR(100),
    given_name_kana VARCHAR(100),
    surname_en VARCHAR(100),
    given_name_en VARCHAR(100),
    primary_email VARCHAR(255),
    discord_user_id VARCHAR(50),
    role_id INTEGER REFERENCES {schema}.roles(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','pending')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, staff_code),
    UNIQUE (tenant_id, discord_user_id)
);

CREATE INDEX IF NOT EXISTS idx_staff_tenant_id ON {schema}.staff (tenant_id);
CREATE INDEX IF NOT EXISTS idx_staff_role_id ON {schema}.staff (role_id);
CREATE INDEX IF NOT EXISTS idx_staff_primary_email ON {schema}.staff (primary_email);
CREATE INDEX IF NOT EXISTS idx_staff_user_id ON {schema}.staff (user_id);
CREATE INDEX IF NOT EXISTS idx_staff_status ON {schema}.staff (status);

-- スタッフの副メール（EMP-00005 のような1人複数メール対応）
CREATE TABLE IF NOT EXISTS {schema}.staff_emails (
    id SERIAL PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES {schema}.staff(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    purpose VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (staff_id, email)
);

CREATE INDEX IF NOT EXISTS idx_staff_emails_staff_id ON {schema}.staff_emails (staff_id);

-- スタッフのUI設定
CREATE TABLE IF NOT EXISTS {schema}.staff_ui_preferences (
    staff_id INTEGER PRIMARY KEY REFERENCES {schema}.staff(id) ON DELETE CASCADE,
    dark_mode BOOLEAN NOT NULL DEFAULT FALSE,
    show_chat_menu BOOLEAN NOT NULL DEFAULT TRUE,
    show_sales_menu BOOLEAN NOT NULL DEFAULT TRUE,
    show_settings_menu BOOLEAN NOT NULL DEFAULT TRUE,
    show_admin_menu BOOLEAN NOT NULL DEFAULT FALSE,
    show_sidebar BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Phase 1-B-2 / ADR-1008: companies.sales_rep_id → public.users(id)
DO $$
BEGIN
    -- ADR-089 Sprint 5: fk_customers_sales_rep 削除済（customers テーブル不要）
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_companies_sales_rep_user'
          AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
    ) THEN
        ALTER TABLE {schema}.companies
            ADD CONSTRAINT fk_companies_sales_rep_user
            FOREIGN KEY (sales_rep_id) REFERENCES public.users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 自動化bot（請求書送付bot / 発送通知bot 等）
CREATE TABLE IF NOT EXISTS {schema}.bots (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    bot_code VARCHAR(20) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    purpose VARCHAR(50) NOT NULL
        CHECK (purpose IN ('invoice','shipment','notification','custom')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','maintenance')),
    api_key_hash VARCHAR(128) NOT NULL,
    discord_user_id VARCHAR(50),
    sender_email VARCHAR(255),
    -- owner_staff_id の外部キー fk_bots_owner_staff_id_user は下の「既存の表に足す外部キー」で付ける
    owner_staff_id INTEGER NOT NULL,
    last_executed_at TIMESTAMPTZ,
    execution_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, bot_code),
    UNIQUE (tenant_id, discord_user_id)
);

CREATE INDEX IF NOT EXISTS idx_bots_tenant_id ON {schema}.bots (tenant_id);
CREATE INDEX IF NOT EXISTS idx_bots_owner_staff_id ON {schema}.bots (owner_staff_id);
CREATE INDEX IF NOT EXISTS idx_bots_purpose ON {schema}.bots (purpose);
CREATE INDEX IF NOT EXISTS idx_bots_status ON {schema}.bots (status);

-- staff / staff_ui_preferences / bots の updated_at 自動更新トリガ
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_staff_updated_at' AND tgrelid = '{schema}.staff'::regclass) THEN
        CREATE TRIGGER trg_staff_updated_at BEFORE UPDATE ON {schema}.staff
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_staff_ui_preferences_updated_at' AND tgrelid = '{schema}.staff_ui_preferences'::regclass) THEN
        CREATE TRIGGER trg_staff_ui_preferences_updated_at BEFORE UPDATE ON {schema}.staff_ui_preferences
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bots_updated_at' AND tgrelid = '{schema}.bots'::regclass) THEN
        CREATE TRIGGER trg_bots_updated_at BEFORE UPDATE ON {schema}.bots
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
END $$;

-- 送信元統一ビュー（staff と bots を UNION）
CREATE OR REPLACE VIEW {schema}.v_senders AS
SELECT
    s.id, s.tenant_id, 'staff'::VARCHAR(10) AS sender_type,
    CONCAT(s.surname_jp, ' ', s.given_name_jp) AS display_name,
    u.email::VARCHAR(255) AS contact_email
FROM {schema}.staff s
JOIN public.users u ON u.id = s.user_id
UNION ALL
SELECT
    id, tenant_id, 'bot'::VARCHAR(10) AS sender_type,
    display_name, sender_email AS contact_email
FROM {schema}.bots;

-- === Phase 2: 販売・財務プロセス ===

-- 商品マスタ（テナント固有テーブル）
-- DEPRECATED (ADR-090 PR4): 商品マスタは public.products に統一済み。
--   このテーブルは将来の Phase B で DROP 予定。アプリは一切参照しない。
-- 2026-04-28 (Phase 1-C M-MVP / migration 038): TCG 輸出向け 11 列追加
CREATE TABLE IF NOT EXISTS {schema}.products (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    product_code VARCHAR(20),
    category VARCHAR(100),
    mark VARCHAR(100),
    name_en VARCHAR(255),
    name_ja VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    condition VARCHAR(50),
    unit_price NUMERIC(15, 2),
    quantity INTEGER DEFAULT 0,
    weight NUMERIC(10, 3),
    notes TEXT,
    release_date DATE,
    -- Phase 1-C M-MVP（2026-04-28、migration 038 同等）
    jan_code VARCHAR(20),
    card_number VARCHAR(50),
    expansion_code VARCHAR(20),
    rarity VARCHAR(20),
    language VARCHAR(10),
    unit_price_usd NUMERIC(15, 2),
    unit_price_eur NUMERIC(15, 2),
    image_url VARCHAR(500),
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    supplier_default_id INTEGER,  -- FK は新テナント作成順序の都合で後付け
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- products 索引（migration 038 同等）
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_tenant_code ON {schema}.products (tenant_id, product_code) WHERE product_code IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_tenant_jan ON {schema}.products (tenant_id, jan_code) WHERE jan_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_archived ON {schema}.products (is_archived);
CREATE INDEX IF NOT EXISTS idx_products_card_number ON {schema}.products (card_number) WHERE card_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_products_expansion ON {schema}.products (expansion_code) WHERE expansion_code IS NOT NULL;

-- 配送ゾーン
CREATE TABLE IF NOT EXISTS {schema}.shipping_zones (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    country_code VARCHAR(3) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    carrier VARCHAR(50) NOT NULL,
    zone VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, country_code, carrier)
);

-- 配送料金
CREATE TABLE IF NOT EXISTS {schema}.shipping_rates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    carrier VARCHAR(50) NOT NULL,
    zone VARCHAR(20) NOT NULL,
    weight_min NUMERIC(10, 3) NOT NULL,
    weight_max NUMERIC(10, 3) NOT NULL,
    price NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'JPY',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 見積ヘッダー
CREATE TABLE IF NOT EXISTS {schema}.quotes (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    quote_code VARCHAR(20),
    -- lead_id の外部キー fk_quotes_lead は下の「既存の表に足す外部キー」で付ける
    lead_id INTEGER NOT NULL,
    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
    company_id INTEGER NOT NULL CONSTRAINT fk_quotes_company REFERENCES {schema}.companies(id),
    contact_id INTEGER CONSTRAINT fk_quotes_contact REFERENCES {schema}.contacts(id),
    currency VARCHAR(10) DEFAULT 'JPY',
    subtotal NUMERIC(15, 2) DEFAULT 0,
    shipping_fee NUMERIC(15, 2) DEFAULT 0,
    tax_amount NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    validity_date DATE,
    shipping_country VARCHAR(100),
    shipping_carrier VARCHAR(50),
    delivery_info TEXT,
    pdf_url VARCHAR(500),
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quotes_company_id ON {schema}.quotes (company_id);
CREATE INDEX IF NOT EXISTS idx_quotes_contact_id ON {schema}.quotes (contact_id);
CREATE INDEX IF NOT EXISTS idx_quotes_lead_id ON {schema}.quotes (lead_id);

-- 成約・失注理由マスタ
CREATE TABLE IF NOT EXISTS {schema}.close_reasons (
    id SERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL CONSTRAINT close_reasons_type_check CHECK (type IN ('won', 'lost')),
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (type, label)
);

CREATE TABLE IF NOT EXISTS {schema}.deal_close_reasons (
    id SERIAL PRIMARY KEY,
    -- lead_id の外部キー fk_deal_close_reasons_lead は下の「既存の表に足す外部キー」で付ける
    lead_id INTEGER NOT NULL,
    reason_id INTEGER NOT NULL REFERENCES {schema}.close_reasons(id),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (lead_id, reason_id)
);
CREATE INDEX IF NOT EXISTS idx_deal_close_reasons_lead_id ON {schema}.deal_close_reasons (lead_id);

-- 見積明細
CREATE TABLE IF NOT EXISTS {schema}.quote_items (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER NOT NULL REFERENCES {schema}.quotes(id) ON DELETE CASCADE,
    product_id INTEGER CONSTRAINT quote_items_product_id_public_fkey REFERENCES public.products(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
    name_en VARCHAR(255),
    condition VARCHAR(50),
    unit VARCHAR(20),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(15, 2) NOT NULL,
    weight NUMERIC(10, 3),
    subtotal NUMERIC(15, 2) NOT NULL,
    hs_code VARCHAR(20),
    sort_order INTEGER DEFAULT 0
);

-- 請求書ヘッダー
CREATE TABLE IF NOT EXISTS {schema}.invoices (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    invoice_number VARCHAR(30),
    quote_id INTEGER REFERENCES {schema}.quotes(id),
    -- Phase 1-B-2 Step 5d / PR γ: 旧 customer_id 列は migration 035 で DROP 済。
    company_id INTEGER NOT NULL CONSTRAINT fk_invoices_company REFERENCES {schema}.companies(id),
    contact_id INTEGER CONSTRAINT fk_invoices_contact REFERENCES {schema}.contacts(id),
    currency VARCHAR(10) DEFAULT 'JPY',
    subtotal NUMERIC(15, 2) DEFAULT 0,
    shipping_fee NUMERIC(15, 2) DEFAULT 0,
    tax_amount NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2) DEFAULT 0,
    exchange_rate_jpy NUMERIC(12, 4),
    exchange_rate_usd NUMERIC(12, 4),
    amount_jpy NUMERIC(15, 2),
    amount_usd NUMERIC(15, 2),
    payment_method VARCHAR(50),
    status VARCHAR(20) DEFAULT 'draft',
    branch_number INTEGER DEFAULT 1,
    pdf_url VARCHAR(500),
    erp_key VARCHAR(100),
    issued_at TIMESTAMPTZ,
    due_date DATE,
    paid_at TIMESTAMPTZ,
    voided_at TIMESTAMPTZ,
    void_reason VARCHAR(500),
    issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN ('domestic', 'overseas')),
    -- 移行で全テナントに入っている列（20260604_160000・20260611_020000・20260612_131520）を新しいテナントにも作る
    ship_to_snapshot JSONB,
    bill_to_snapshot JSONB,
    issue_mode VARCHAR(20),
    duty_amount NUMERIC(15, 2),
    duty_policy_snapshot JSONB,
    fx_rate_snapshot JSONB,
    paypal_order_id TEXT,
    paypal_approval_url TEXT,
    payment_fee NUMERIC(15, 2),
    paypal_invoicer_view_url TEXT,
    paypal_copy_pdf BYTEA,
    paypal_copy_pdf_at TIMESTAMPTZ,
    -- invoice-create-portfolio 便A: 案内した支払い先・使った税率・選んだ送料（移行 20261113_120000 と同じ形）
    payment_method_id INTEGER,
    tax_rate_percent NUMERIC(5, 2),
    shipping_carrier VARCHAR(50),
    shipping_service VARCHAR(100),
    shipping_snapshot JSONB,
    -- invoice-create-portfolio 便E: お客様への合計に足した支払い手数料と計算の写し（移行 20261121_100000 と同じ形）
    payment_fee_charged NUMERIC(15, 2),
    payment_fee_snapshot JSONB,
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_invoices_company_id ON {schema}.invoices (company_id);
CREATE INDEX IF NOT EXISTS idx_invoices_contact_id ON {schema}.invoices (contact_id);

-- 請求書明細
CREATE TABLE IF NOT EXISTS {schema}.invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES {schema}.invoices(id) ON DELETE CASCADE,
    product_id INTEGER CONSTRAINT invoice_items_product_id_public_fkey REFERENCES public.products(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    -- 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
    name_en VARCHAR(255),
    condition VARCHAR(50),
    unit VARCHAR(20),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(15, 2) NOT NULL,
    weight NUMERIC(10, 3),
    subtotal NUMERIC(15, 2) NOT NULL,
    hs_code VARCHAR(20),
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS {schema}.order_items (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    order_id INTEGER NOT NULL,
    product_id INTEGER REFERENCES public.products(id),
    product_name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    condition VARCHAR(50),
    unit VARCHAR(20),
    sku VARCHAR(100),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(15, 2) NOT NULL,
    subtotal NUMERIC(15, 2) NOT NULL,
    weight NUMERIC(10, 3),
    hs_code VARCHAR(20),
    usd_unit_value NUMERIC(15, 2),
    exchange_rate_usd NUMERIC(12, 4),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON {schema}.order_items (order_id);

DO $order_items_fk$
BEGIN
    IF to_regclass('{schema}.orders') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_order_items_order'
              AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_raw}')
        ) THEN
            ALTER TABLE {schema}.order_items
                ADD CONSTRAINT fk_order_items_order
                FOREIGN KEY (order_id) REFERENCES {schema}.orders(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $order_items_fk$;

DO $order_items_trigger$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_order_items_updated_at'
          AND tgrelid = '{schema}.order_items'::regclass
    ) THEN
        CREATE TRIGGER trg_order_items_updated_at BEFORE UPDATE ON {schema}.order_items
            FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
END $order_items_trigger$;

-- === Phase 3: 仕入れ・調達管理 ===

-- 仕入先は public.suppliers 1 つにまとめる（docs/handoff/supplier-ssot-phase2/design.md）。
-- 会社ごとの suppliers 表は作らない（段5 5-2 B1。本番 5 社にも無い）。

-- products.supplier_default_id の FK は共用の public.suppliers を指す
-- （Phase 1-C M-MVP / 2026-04-28）
DO $supplier_fk$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = '{schema}.products'::regclass
          AND conname = 'fk_products_supplier_default'
    ) THEN
        ALTER TABLE {schema}.products
        ADD CONSTRAINT fk_products_supplier_default
        FOREIGN KEY (supplier_default_id) REFERENCES public.suppliers(id);
    END IF;
END $supplier_fk$;

CREATE TABLE IF NOT EXISTS {schema}.purchase_orders (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    po_number VARCHAR(20),
    supplier_id INTEGER NOT NULL REFERENCES public.suppliers(id),
    status VARCHAR(20) DEFAULT 'draft',
    total_amount NUMERIC(15, 2) DEFAULT 0,
    ordered_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    shipping_fee NUMERIC(15, 2) DEFAULT 0,
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS {schema}.purchase_order_items (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL REFERENCES {schema}.purchase_orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL CONSTRAINT purchase_order_items_product_id_public_fkey REFERENCES public.products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_cost NUMERIC(15, 2) NOT NULL,
    subtotal NUMERIC(15, 2) NOT NULL,
    -- order_item_id の外部キー fk_poi_order_item は下の「既存の表に足す外部キー」で付ける
    order_item_id INTEGER,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS {schema}.meta_messages (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL DEFAULT {tenant_id},
    lead_id     INTEGER REFERENCES {schema}.leads(id) ON DELETE SET NULL,
    platform    VARCHAR(20) NOT NULL DEFAULT 'messenger',
    sender_id   VARCHAR(100) NOT NULL,
    sender_name VARCHAR(200),
    -- ADR-026 / migration 052: Instagram の mid は 157 文字に達するため TEXT を使う。
    -- 既存テナントは migration 052 で TEXT 化済 → 新規テナント provisioning も整合させる。
    message_id  TEXT,
    message_text TEXT,
    direction   VARCHAR(10) NOT NULL DEFAULT 'inbound',
    raw_payload JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meta_messages_sender ON {schema}.meta_messages (sender_id);
CREATE INDEX IF NOT EXISTS idx_meta_messages_lead   ON {schema}.meta_messages (lead_id);
CREATE INDEX IF NOT EXISTS idx_meta_messages_ts     ON {schema}.meta_messages (created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_meta_messages_message_id_unique
    ON {schema}.meta_messages (message_id)
    WHERE message_id IS NOT NULL;
-- 会話の一本化 便1: 手の記録の列（migrations/20260622_010000 と同じ名前・型・既定値）。新しい会社でも読む側の条件が動くようにする
ALTER TABLE {schema}.meta_messages
    ADD COLUMN IF NOT EXISTS contact_id          INTEGER,
    ADD COLUMN IF NOT EXISTS company_id          INTEGER,
    ADD COLUMN IF NOT EXISTS deal_id             INTEGER,
    ADD COLUMN IF NOT EXISTS channel_identity    VARCHAR(255),
    ADD COLUMN IF NOT EXISTS original_language   VARCHAR(10),
    ADD COLUMN IF NOT EXISTS status              VARCHAR(20) DEFAULT 'sent',
    ADD COLUMN IF NOT EXISTS analysis            JSONB,
    ADD COLUMN IF NOT EXISTS occurred_at         TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_at          TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS is_manual           BOOLEAN DEFAULT NULL;
-- ADR-119: lead_channels — 1 lead : N platforms（クロスプラットフォーム名寄せ）
-- webhook が source 文字列比較ではなくこのテーブルを lookup 権威として使う
CREATE TABLE IF NOT EXISTS {schema}.lead_channels (
    id           SERIAL PRIMARY KEY,
    lead_id      INTEGER NOT NULL REFERENCES {schema}.leads(id) ON DELETE CASCADE,
    platform     VARCHAR(30)  NOT NULL,     -- 'messenger' / 'instagram' / 'discord'
    external_id  VARCHAR(255) NOT NULL,     -- PSID / IGSID / Discord UID
    display_name VARCHAR(255),              -- プラットフォーム側の表示名（任意）
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, external_id)          -- 1 channel → 1 lead（テナントスコープ内）
);
CREATE INDEX IF NOT EXISTS idx_lead_channels_lead_id
    ON {schema}.lead_channels (lead_id);
-- NOTE: UNIQUE (platform, external_id) が B-tree インデックスを暗黙作成するため
--       (platform, external_id) への追加インデックスは不要。

-- アプリ内の鈴: 人ごとの知らせ（未読つき）。本文・Discord の id の列は持たない
CREATE TABLE IF NOT EXISTS {schema}.user_notices (
    id           BIGSERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL,          -- 宛先の public.users.id
    kind         TEXT NOT NULL,             -- 'discord_outside_ticket_post'
    actor_name   TEXT,                      -- 書いた人の Discord の表示名
    channel_name TEXT,                      -- 書き込まれたチャンネル名
    link_url     TEXT,                      -- 書き込みへのリンク
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at      TIMESTAMPTZ                -- NULL は未読
);
CREATE INDEX IF NOT EXISTS idx_user_notices_user_created
    ON {schema}.user_notices (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_notices_user_unread
    ON {schema}.user_notices (user_id) WHERE read_at IS NULL;

-- アプリ内の鈴: 担当者がいないときに知らせを受け取る人（0 行 = 未設定 = オーナー全員）
CREATE TABLE IF NOT EXISTS {schema}.notice_fallback_recipients (
    user_id    INTEGER PRIMARY KEY,         -- 受け取る人の public.users.id
    updated_by INTEGER,                     -- 設定した人の public.users.id
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- discord-server-management 第2段: 消したアプリの役割の Discord のロールの番号（点検が登録した人から外す）
CREATE TABLE IF NOT EXISTS {schema}.discord_retired_roles (
    discord_role_id TEXT PRIMARY KEY,
    retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- discord-server-management 第2段: 消した・番号を変えたスタッフの元の Discord の番号（kick=true は自社サーバーから外す）
CREATE TABLE IF NOT EXISTS {schema}.discord_retired_members (
    discord_user_id TEXT PRIMARY KEY,
    kick            BOOLEAN NOT NULL,
    retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Phase 1-D Sprint 1 / migration 040: Meta OAuth 接続情報（Page / IG Business Account）
-- 同じ DDL は migrations/040_create_tenant_meta_config.sql にも置いてあり、
-- 既存テナントへの後付けはそちらの SQL を使う。新規テナントはこの本ブロックで自動作成される。
CREATE TABLE IF NOT EXISTS {schema}.tenant_meta_config (
    id                              SERIAL PRIMARY KEY,
    tenant_id                       INTEGER NOT NULL DEFAULT {tenant_id},
    page_id                         VARCHAR(50) NOT NULL,
    page_name                       VARCHAR(200) NOT NULL,
    page_access_token_encrypted     BYTEA NOT NULL,
    page_token_expires_at           TIMESTAMPTZ,
    instagram_business_account_id   VARCHAR(50),
    instagram_username              VARCHAR(100),
    subscribed_fields               JSONB,
    -- connected_by_staff_id の外部キー fk_tenant_meta_config_connected_by_staff_id_user は下の「既存の表に足す外部キー」で付ける
    connected_by_staff_id           INTEGER,
    connected_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_token_refreshed_at         TIMESTAMPTZ,
    is_active                       BOOLEAN NOT NULL DEFAULT TRUE,
    deactivated_at                  TIMESTAMPTZ,
    notes                           TEXT,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_meta_config_active_page
    ON {schema}.tenant_meta_config (tenant_id, page_id)
    WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_tenant_meta_config_ig_id
    ON {schema}.tenant_meta_config (instagram_business_account_id)
    WHERE instagram_business_account_id IS NOT NULL;

-- Sprint 8 / migration 069: テナント発行者情報 (PO PDF / メール差出人)
-- ADR-034: 新規テナント作成時に最初から保持される。
-- 1 テナント 1 行運用、admin UI で内容編集。
CREATE TABLE IF NOT EXISTS {schema}.tenant_profile (
    id                  SERIAL PRIMARY KEY,
    company_name        VARCHAR(255),
    company_name_en     VARCHAR(255),
    address             TEXT,
    phone               VARCHAR(50),
    email               VARCHAR(255),
    website             VARCHAR(255),
    seal_image_url      TEXT,
    default_language    CHAR(2) NOT NULL DEFAULT 'ja',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tenant_profile_default_language_check
        CHECK (default_language IN ('ja', 'en', 'ko', 'zh'))
);
-- 既定行を 1 行投入 (admin が UI で後から埋める)
INSERT INTO {schema}.tenant_profile (default_language)
SELECT 'ja' WHERE NOT EXISTS (SELECT 1 FROM {schema}.tenant_profile);

-- migration 075: 目標管理テーブル (ダッシュボード強化)
CREATE TABLE IF NOT EXISTS {schema}.goals (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
    team_id      INTEGER,
    period_type  VARCHAR(10)    NOT NULL
                     CHECK (period_type IN ('monthly', 'weekly')),
    period_year  SMALLINT       NOT NULL CHECK (period_year >= 2020),
    period_num   SMALLINT       NOT NULL CHECK (period_num BETWEEN 1 AND 53),
    kpi_type     VARCHAR(30)    NOT NULL
                     CHECK (kpi_type IN (
                         'revenue', 'deal_count', 'close_rate',
                         'lead_count', 'conversion_rate',
                         'won_count', 'gross_profit'
                     )),
    target_value NUMERIC(15, 2) NOT NULL CHECK (target_value >= 0),
    created_by   INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT goals_owner_check
        CHECK (
            (user_id IS NOT NULL AND team_id IS NULL) OR
            (user_id IS NULL AND team_id IS NOT NULL)
        ),
    CONSTRAINT goals_unique_target
        UNIQUE (user_id, team_id, period_type, period_year, period_num, kpi_type)
);
CREATE INDEX IF NOT EXISTS idx_goals_user_period
    ON {schema}.goals (user_id, period_year, period_num);
CREATE INDEX IF NOT EXISTS idx_goals_team_period
    ON {schema}.goals (team_id, period_year, period_num);

-- D-2: A在庫（自社保有在庫）— ADR SA-04/05（B在庫 public.inventory とは完全分離）
CREATE TABLE IF NOT EXISTS {schema}.own_inventory (
    id                SERIAL PRIMARY KEY,
    tenant_id         INTEGER      NOT NULL,
    product_id        INTEGER      NOT NULL REFERENCES public.products(id),
    physical_qty      INTEGER      NOT NULL DEFAULT 0 CHECK (physical_qty >= 0),
    reserved_qty      INTEGER      NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    available_qty     INTEGER GENERATED ALWAYS AS (physical_qty - reserved_qty) STORED,
    unit_price        NUMERIC(15,2),
    condition         VARCHAR(50),
    status            VARCHAR(20)  NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','inactive','sold_out')),
    note_ja           TEXT,
    note_en           TEXT,
    antique_ledger_id INTEGER,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
);

-- ADR-1061 2-2c1: 発行元の会社情報（国内用・海外用の 2 行まで）
CREATE TABLE IF NOT EXISTS {schema}.tenant_issuer_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    region VARCHAR(20) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    website VARCHAR(255),
    country_code CHAR(2) NOT NULL REFERENCES public.countries(code),
    postal_code VARCHAR(10),
    prefecture_code CHAR(2) REFERENCES public.prefectures(code),
    state_region TEXT,
    city TEXT NOT NULL,
    address1 TEXT NOT NULL,
    address2 TEXT,
    phone VARCHAR(16),
    is_invoice_registered BOOLEAN NOT NULL DEFAULT FALSE,
    registration_number VARCHAR(14),
    updated_by_user_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region),
    CONSTRAINT chk_tenant_issuer_profiles_region CHECK (region IN ('domestic', 'overseas')),
    CONSTRAINT chk_tenant_issuer_profiles_company_name CHECK (btrim(company_name) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_city CHECK (btrim(city) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_address1 CHECK (btrim(address1) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_jp_address CHECK (country_code <> 'JP' OR (postal_code IS NOT NULL AND postal_code ~ '^[0-9]{{7}}$' AND prefecture_code IS NOT NULL AND state_region IS NULL)),
    CONSTRAINT chk_tenant_issuer_profiles_foreign_address CHECK (country_code = 'JP' OR (prefecture_code IS NULL AND (postal_code IS NULL OR postal_code ~ '^[0-9A-Za-z -]{{1,10}}$'))),
    CONSTRAINT chk_tenant_issuer_profiles_phone CHECK (phone IS NULL OR (country_code = 'JP' AND phone ~ '^[0-9]{{10,11}}$') OR (country_code <> 'JP' AND phone ~ '^\\+[0-9]{{6,15}}$')),
    CONSTRAINT chk_tenant_issuer_profiles_registration CHECK ((is_invoice_registered AND registration_number IS NOT NULL AND registration_number ~ '^T[0-9]{{13}}$') OR (NOT is_invoice_registered AND registration_number IS NULL))
);

-- ADR-1061 2-2c1: 請求書に載せる振込先の一覧（銀行・Wise）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    region VARCHAR(20) NOT NULL,
    method_type VARCHAR(10) NOT NULL,
    display_name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by_user_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    superseded_by_id INTEGER,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
    CONSTRAINT chk_tenant_invoice_payment_methods_region CHECK (region IN ('domestic', 'overseas')),
    CONSTRAINT chk_tenant_invoice_payment_methods_method_type CHECK (method_type IN ('bank', 'wise')),
    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> ''),
    CONSTRAINT chk_tenant_invoice_payment_methods_superseded_not_self CHECK (superseded_by_id <> id),
    CONSTRAINT fk_tenant_invoice_payment_methods_superseded_by FOREIGN KEY (superseded_by_id) REFERENCES {schema}.tenant_invoice_payment_methods (id)
);

-- invoice-create-portfolio 便V: 次の版を指せるのは前の版1つだけ（ADR-1079）
CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by ON {schema}.tenant_invoice_payment_methods (superseded_by_id) WHERE superseded_by_id IS NOT NULL;

-- ADR-1061 2-2c1: 銀行振込先の詳細（振込先の一覧 1 行に 1 行）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_bank (
    payment_method_id INTEGER PRIMARY KEY,
    method_type VARCHAR(10) NOT NULL DEFAULT 'bank',
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    account_holder TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    bank_branch TEXT NOT NULL,
    bank_account_type TEXT NOT NULL,
    bank_account_number TEXT NOT NULL,
    swift_code TEXT,
    bank_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_invoice_payment_bank_method_type CHECK (method_type = 'bank'),
    CONSTRAINT chk_tenant_invoice_payment_bank_required CHECK (btrim(account_holder) <> '' AND btrim(bank_name) <> '' AND btrim(bank_branch) <> '' AND btrim(bank_account_type) <> '' AND btrim(bank_account_number) <> ''),
    CONSTRAINT fk_tenant_invoice_payment_bank_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);

-- ADR-1061 2-2c1: Wise 振込先の詳細（振込先の一覧 1 行に 1 行）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_wise (
    payment_method_id INTEGER PRIMARY KEY,
    method_type VARCHAR(10) NOT NULL DEFAULT 'wise',
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    account_holder TEXT NOT NULL,
    wise_currency CHAR(3) NOT NULL,
    wise_email VARCHAR(255) NOT NULL,
    iban TEXT,
    swift_bic TEXT,
    bank_name TEXT,
    bank_address TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_invoice_payment_wise_method_type CHECK (method_type = 'wise'),
    CONSTRAINT chk_tenant_invoice_payment_wise_currency CHECK (wise_currency ~ '^[A-Z]{{3}}$'),
    CONSTRAINT chk_tenant_invoice_payment_wise_required CHECK (btrim(account_holder) <> '' AND btrim(wise_email) <> ''),
    CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);

-- invoice-create-portfolio 便V: 振込先は版で持つ。詳細は書き足すだけ・振込先の行は消さない・表を空にしない（ADR-1079）
CREATE OR REPLACE FUNCTION {schema}.trg_payment_detail_immutable()
RETURNS TRIGGER AS $pv_detail$
DECLARE
    v_id INTEGER;
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'payment detail rows are immutable (versioned). Add a new version instead.';
    END IF;
    IF NEW.payment_method_id IS NOT NULL THEN
        EXECUTE 'SELECT id, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.payment_method_id || ' FOR SHARE'
            INTO v_id, v_superseded, v_deleted;
        IF v_id IS NULL OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'payment detail can be added only to the current version of a payment method';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_detail$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION {schema}.trg_payment_method_version_guard()
RETURNS TRIGGER AS $pv_method$
DECLARE
    v_id INTEGER;
    v_region VARCHAR(20);
    v_type VARCHAR(10);
    v_superseded INTEGER;
    v_deleted TIMESTAMPTZ;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'payment methods cannot be deleted. Set deleted_at instead.';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.superseded_by_id IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a new payment method must start as the current version';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.region IS DISTINCT FROM OLD.region
        OR NEW.method_type IS DISTINCT FROM OLD.method_type
        OR NEW.display_name IS DISTINCT FROM OLD.display_name
        OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'payment method versions are immutable. Add a new version instead.';
    END IF;
    IF OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id THEN
        RAISE EXCEPTION 'superseded_by_id can be set only once';
    END IF;
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
        RAISE EXCEPTION 'deleted_at can be set only once';
    END IF;
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL
        AND (OLD.superseded_by_id IS NOT NULL OR NEW.superseded_by_id IS NOT NULL) THEN
        RAISE EXCEPTION 'only the current version can be deleted';
    END IF;
    IF OLD.superseded_by_id IS NULL AND NEW.superseded_by_id IS NOT NULL THEN
        IF OLD.deleted_at IS NOT NULL OR NEW.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'a deleted payment method cannot be superseded';
        END IF;
        IF NEW.superseded_by_id <= OLD.id THEN
            RAISE EXCEPTION 'the next version must be newer than the current version';
        END IF;
        EXECUTE 'SELECT id, region, method_type, superseded_by_id, deleted_at FROM ' || quote_ident(TG_TABLE_SCHEMA)
            || '.tenant_invoice_payment_methods WHERE id = ' || NEW.superseded_by_id || ' FOR SHARE'
            INTO v_id, v_region, v_type, v_superseded, v_deleted;
        IF v_id IS NULL OR v_region IS DISTINCT FROM OLD.region OR v_type IS DISTINCT FROM OLD.method_type
            OR v_superseded IS NOT NULL OR v_deleted IS NOT NULL THEN
            RAISE EXCEPTION 'the next version must be a current version of the same region and type';
        END IF;
    END IF;
    RETURN NEW;
END;
$pv_method$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION {schema}.trg_payment_version_no_wipe()
RETURNS TRIGGER AS $pv_wipe$
BEGIN
    RAISE EXCEPTION 'payment version tables cannot be truncated';
    RETURN NULL;
END;
$pv_wipe$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_version_guard' AND tgrelid = '{schema}.tenant_invoice_payment_methods'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_methods_version_guard BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_methods FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_method_version_guard();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_immutable' AND tgrelid = '{schema}.tenant_invoice_payment_bank'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_bank_immutable BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_bank FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_detail_immutable();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_immutable' AND tgrelid = '{schema}.tenant_invoice_payment_wise'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_wise_immutable BEFORE INSERT OR UPDATE OR DELETE ON {schema}.tenant_invoice_payment_wise FOR EACH ROW EXECUTE FUNCTION {schema}.trg_payment_detail_immutable();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_methods_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_methods'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_methods_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_methods FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_bank_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_bank'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_bank_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_bank FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tenant_invoice_payment_wise_no_wipe' AND tgrelid = '{schema}.tenant_invoice_payment_wise'::regclass) THEN
        CREATE TRIGGER trg_tenant_invoice_payment_wise_no_wipe BEFORE TRUNCATE ON {schema}.tenant_invoice_payment_wise FOR EACH STATEMENT EXECUTE FUNCTION {schema}.trg_payment_version_no_wipe();
    END IF;
END $$;

-- invoice-create-portfolio 便A: 関税の決まり（行き先の国・送料の会社ごと。DDP のときに使う）
CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    destination_country_code CHAR(2) NOT NULL,
    carrier VARCHAR(50),
    label TEXT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    source_url TEXT NOT NULL,
    note TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_duty_rules_country CHECK (destination_country_code ~ '^[A-Z]{{2}}$'),
    CONSTRAINT chk_tenant_duty_rules_carrier CHECK (carrier IS NULL OR (carrier = lower(btrim(carrier)) AND carrier <> '')),
    CONSTRAINT chk_tenant_duty_rules_label CHECK (btrim(label) <> ''),
    CONSTRAINT chk_tenant_duty_rules_source_url CHECK (btrim(source_url) <> ''),
    CONSTRAINT chk_tenant_duty_rules_period CHECK (effective_to IS NULL OR effective_to >= effective_from)
);
CREATE INDEX IF NOT EXISTS idx_tenant_duty_rules_country_carrier ON {schema}.tenant_duty_rules (destination_country_code, carrier);

-- invoice-create-portfolio 便A: 関税の決まりの中身（関税・消費税・手数料など。率と下限・上限）
CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rule_components (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES {schema}.tenant_duty_rules(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    sort_order INTEGER NOT NULL DEFAULT 0,
    label TEXT NOT NULL,
    base VARCHAR(30) NOT NULL,
    rate_pct NUMERIC(8, 4) NOT NULL,
    min_amount NUMERIC(14, 2),
    max_amount NUMERIC(14, 2),
    amount_currency CHAR(3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_duty_rule_components_label CHECK (btrim(label) <> ''),
    CONSTRAINT chk_tenant_duty_rule_components_base CHECK (base IN ('subtotal', 'subtotal_shipping', 'subtotal_shipping_prior')),
    CONSTRAINT chk_tenant_duty_rule_components_rate CHECK (rate_pct >= 0),
    CONSTRAINT chk_tenant_duty_rule_components_amounts CHECK ((min_amount IS NULL OR min_amount >= 0) AND (max_amount IS NULL OR max_amount >= 0) AND (min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount)),
    CONSTRAINT chk_tenant_duty_rule_components_currency CHECK (amount_currency IS NULL OR amount_currency ~ '^[A-Z]{{3}}$'),
    CONSTRAINT chk_tenant_duty_rule_components_currency_required CHECK ((min_amount IS NULL AND max_amount IS NULL) OR amount_currency IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_tenant_duty_rule_components_rule_id ON {schema}.tenant_duty_rule_components (rule_id);
-- ============================================================================
-- 段5 5-2: 登録の移行（scripts/run_all_migrations.sh）が会社に作る物を、ひな形にも持たせる。
-- 新しい会社を作った直後と、登録を全件流した後で形が変わらないようにする（CI: scripts/check_tenant_template_shape.py）。
-- 書き写す元は、登録を全件流した後の会社の形。冪等（IF NOT EXISTS・名前の有無の確認）で、既にある会社に流しても壊さない。
-- ============================================================================

-- 既存の表に足す列
-- 分け表 A1: 注文の 8 列（本番 5 社全部にある。backend/app/routers/orders.py と backend/app/tasks/reports.py が読む。
-- 作る SQL migrations/005_add_phase2_tenant_tables.sql は登録に無い）。型・既定値は本番 003 と同じ
ALTER TABLE {schema}.orders
    ADD COLUMN IF NOT EXISTS invoice_id INTEGER,
    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'JPY',
    ADD COLUMN IF NOT EXISTS shipping_carrier VARCHAR(50),
    ADD COLUMN IF NOT EXISTS shipping_fee NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(200),
    ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS shipping_country VARCHAR(100);
ALTER TABLE {schema}.company_discord
    ADD COLUMN IF NOT EXISTS guild_id character varying(50);
ALTER TABLE {schema}.contact_contact_channels
    ADD COLUMN IF NOT EXISTS guild_id character varying(50);
ALTER TABLE {schema}.leads
    ADD COLUMN IF NOT EXISTS discord_dm_channel_id character varying(50),
    ADD COLUMN IF NOT EXISTS discord_guild_channel_id character varying(50),
    ADD COLUMN IF NOT EXISTS discord_id character varying(255),
    ADD COLUMN IF NOT EXISTS discord_role_sync_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS discord_role_sync_status character varying(20),
    ADD COLUMN IF NOT EXISTS discord_user_id character varying(50),
    ADD COLUMN IF NOT EXISTS english_name character varying(255),
    ADD COLUMN IF NOT EXISTS instagram_link character varying(1000),
    ADD COLUMN IF NOT EXISTS messenger_link character varying(1000),
    ADD COLUMN IF NOT EXISTS whatsapp_link character varying(1000);
ALTER TABLE {schema}.meta_messages
    ADD COLUMN IF NOT EXISTS attachment_type character varying(20),
    ADD COLUMN IF NOT EXISTS attachment_url text,
    ADD COLUMN IF NOT EXISTS error_code character varying(50),
    ADD COLUMN IF NOT EXISTS error_message text,
    ADD COLUMN IF NOT EXISTS message_tag character varying(50),
    ADD COLUMN IF NOT EXISTS messaging_type character varying(20),
    ADD COLUMN IF NOT EXISTS page_id character varying(50),
    ADD COLUMN IF NOT EXISTS recipient_id character varying(100),
    ADD COLUMN IF NOT EXISTS seen_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS seen_by_staff_id integer,
    ADD COLUMN IF NOT EXISTS sent_by_staff_id integer;
ALTER TABLE {schema}.purchase_orders
    ADD COLUMN IF NOT EXISTS company_name_snapshot character varying(255),
    ADD COLUMN IF NOT EXISTS contact_info_snapshot text;
ALTER TABLE {schema}.staff
    ADD COLUMN IF NOT EXISTS avatar_token text,
    ADD COLUMN IF NOT EXISTS is_employee boolean DEFAULT false NOT NULL,
    ADD COLUMN IF NOT EXISTS phone character varying(20);
ALTER TABLE {schema}.tenant_meta_config
    ADD COLUMN IF NOT EXISTS granted_scopes jsonb;

-- 新しい表（依存の順）
-- 登録の移行: scripts/migrate_009_phase4_tenant_tables.py（作る SQL: migrations/009_add_phase4_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.archives (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    source_table character varying(100) NOT NULL,
    source_id integer NOT NULL,
    archived_data jsonb NOT NULL,
    archived_by integer,
    archived_at timestamp with time zone DEFAULT now(),
    restored_at timestamp with time zone,
    restored_by integer,
    CONSTRAINT archives_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_archives_source ON {schema}.archives USING btree (source_table, source_id);

-- 登録の移行: migrations/20261126_100000_create_calendar_categories.sql（予定の種類の表。calendar_events より前に作る）
CREATE TABLE IF NOT EXISTS {schema}.calendar_categories (
    key character varying(50) NOT NULL,
    name character varying(50),
    color_key text,
    default_share character varying(10) DEFAULT 'all' NOT NULL,
    sort_order integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT calendar_categories_pkey PRIMARY KEY (key),
    CONSTRAINT calendar_categories_key_format_check CHECK (key ~ '^[a-z][a-z0-9_]{{0,49}}$'),
    CONSTRAINT calendar_categories_default_share_check CHECK (default_share IN ('self', 'all', 'team')),
    CONSTRAINT calendar_categories_color_key_check CHECK (color_key IN ('radicchio', 'cherry_blossom', 'flamingo', 'tomato', 'tangerine', 'pumpkin', 'mango', 'banana', 'citron', 'avocado', 'pistachio', 'basil', 'sage', 'eucalyptus', 'peacock', 'cobalt', 'lavender', 'blueberry', 'wisteria', 'amethyst', 'grape', 'cocoa', 'graphite', 'birch')),
    CONSTRAINT calendar_categories_name_check CHECK (name IS NOT NULL OR key IN ('meeting', 'personal', 'procurement', 'shipping', 'billing', 'release', 'holiday'))
);
INSERT INTO {schema}.calendar_categories (key, default_share, sort_order) VALUES
    ('meeting', 'all', 1),
    ('personal', 'self', 2),
    ('procurement', 'all', 3),
    ('shipping', 'all', 4),
    ('billing', 'all', 5),
    ('release', 'all', 6),
    ('holiday', 'all', 7)
ON CONFLICT (key) DO NOTHING;

-- 登録の移行: migrations/078_create_calendar_events_tenant.sql
CREATE TABLE IF NOT EXISTS {schema}.calendar_events (
    id SERIAL,
    user_id integer,
    calendar_type character varying(10) DEFAULT 'shared'::character varying NOT NULL,
    title character varying(500) NOT NULL,
    description text,
    location text,
    start_datetime timestamp with time zone NOT NULL,
    end_datetime timestamp with time zone NOT NULL,
    is_all_day boolean DEFAULT false NOT NULL,
    google_event_id character varying(255),
    google_calendar_id character varying(255),
    source character varying(10) DEFAULT 'app'::character varying NOT NULL,
    sync_status character varying(10) DEFAULT 'synced'::character varying,
    sync_origin_id character varying(500),
    last_synced_at timestamp with time zone,
    created_by_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    meet_url text,
    recurrence_rule text,
    color_key text,
    recurring_event_id integer,
    original_start_datetime timestamp with time zone,
    is_cancelled boolean DEFAULT false NOT NULL,
    -- 分け表 A3: 予定の分類（本番 5 社全部にある）。登録の移行 20261126_100000 で外部キー calendar_events_category_fkey が付く
    category character varying(50) DEFAULT 'meeting'::character varying NOT NULL,
    CONSTRAINT calendar_events_category_fkey FOREIGN KEY (category) REFERENCES {schema}.calendar_categories(key) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT calendar_events_pkey PRIMARY KEY (id),
    CONSTRAINT calendar_events_color_key_check CHECK (color_key IN ('radicchio', 'cherry_blossom', 'flamingo', 'tomato', 'tangerine', 'pumpkin', 'mango', 'banana', 'citron', 'avocado', 'pistachio', 'basil', 'sage', 'eucalyptus', 'peacock', 'cobalt', 'lavender', 'blueberry', 'wisteria', 'amethyst', 'grape', 'cocoa', 'graphite', 'birch')),
    CONSTRAINT calendar_events_calendar_type_check CHECK (calendar_type IN ('shared', 'personal', 'team')),
    CONSTRAINT calendar_events_cancelled_exception_check CHECK (((NOT is_cancelled) OR (recurring_event_id IS NOT NULL))),
    CONSTRAINT calendar_events_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL,
    CONSTRAINT calendar_events_exception_pair_check CHECK (((recurring_event_id IS NULL) = (original_start_datetime IS NULL))),
    CONSTRAINT calendar_events_recurrence_role_check CHECK ((NOT ((recurrence_rule IS NOT NULL) AND (recurring_event_id IS NOT NULL)))),
    CONSTRAINT calendar_events_recurring_event_id_fkey FOREIGN KEY (recurring_event_id) REFERENCES {schema}.calendar_events(id) ON DELETE CASCADE,
    CONSTRAINT calendar_events_source_check CHECK (source IN ('app', 'google')),
    CONSTRAINT calendar_events_sync_status_check CHECK (sync_status IN ('synced', 'pending', 'failed')),
    CONSTRAINT calendar_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL
);
-- 繰り返しの書式の制約は文字列の中にセミコロンを含み、ひな形の分割に壊されるので DO ブロックで付ける
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'calendar_events_recurrence_rule_format_check' AND conrelid = '{schema}.calendar_events'::regclass) THEN
        ALTER TABLE {schema}.calendar_events ADD CONSTRAINT calendar_events_recurrence_rule_format_check CHECK ((recurrence_rule ~ '^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$'::text));
    END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS calendar_events_exception_unique_idx ON {schema}.calendar_events USING btree (recurring_event_id, original_start_datetime) WHERE (recurring_event_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_calendar_events_google_id ON {schema}.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_calendar_events_range ON {schema}.calendar_events USING btree (start_datetime, end_datetime);
CREATE INDEX IF NOT EXISTS idx_calendar_events_sync_origin ON {schema}.calendar_events USING btree (sync_origin_id) WHERE (sync_origin_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_type ON {schema}.calendar_events USING btree (user_id, calendar_type);
CREATE UNIQUE INDEX IF NOT EXISTS uq_calendar_events_google_event_id ON {schema}.calendar_events USING btree (google_event_id) WHERE (google_event_id IS NOT NULL);

-- 登録の移行: migrations/20261127_100000_add_calendar_team_share.sql（予定とチームの対応・種類の初期のチーム）。
-- 親の calendar_events・calendar_categories に RLS が無いので、この 2 表にも付けない（design-bin2b.md §3-1）。
CREATE TABLE IF NOT EXISTS {schema}.calendar_event_teams (
    event_id integer NOT NULL REFERENCES {schema}.calendar_events(id) ON DELETE CASCADE,
    team_id integer NOT NULL REFERENCES {schema}.teams(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, team_id)
);
CREATE INDEX IF NOT EXISTS idx_calendar_event_teams_team ON {schema}.calendar_event_teams (team_id);
CREATE TABLE IF NOT EXISTS {schema}.calendar_category_teams (
    category_key character varying(50) NOT NULL REFERENCES {schema}.calendar_categories(key) ON UPDATE RESTRICT ON DELETE CASCADE,
    team_id integer NOT NULL REFERENCES {schema}.teams(id) ON DELETE CASCADE,
    PRIMARY KEY (category_key, team_id)
);

-- 分け表 A2: 予定の表示設定（本番 5 社全部にある。backend/app/routers/calendar.py が使う）。
-- 作る SQL migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql は登録に無い。
-- 登録の移行: migrations/20261128_100000_owner_color_key_drop_dead_columns.sql（人の色を color_key へ・使っていない 3 列を外す）。
-- RLS は本番 003 と同じく切ったまま・方針は足さない（recon-5-0b/prod003/table_flags.tsv。RLS を付けるかは別のテーマ）
CREATE TABLE IF NOT EXISTS {schema}.calendar_owner_settings (
    staff_id integer NOT NULL,
    color_key text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT calendar_owner_settings_pkey PRIMARY KEY (staff_id),
    CONSTRAINT calendar_owner_settings_color_key_check CHECK (color_key IN ('radicchio', 'cherry_blossom', 'flamingo', 'tomato', 'tangerine', 'pumpkin', 'mango', 'banana', 'citron', 'avocado', 'pistachio', 'basil', 'sage', 'eucalyptus', 'peacock', 'cobalt', 'lavender', 'blueberry', 'wisteria', 'amethyst', 'grape', 'cocoa', 'graphite', 'birch')),
    CONSTRAINT fk_calendar_owner_settings_staff_id_user FOREIGN KEY (staff_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_calendar_owner_settings_staff_id ON {schema}.calendar_owner_settings USING btree (staff_id);

-- 登録の移行: migrations/20260604_090000_create_conversation_logs.sql
CREATE TABLE IF NOT EXISTS {schema}.conversation_logs (
    id SERIAL,
    tenant_id integer NOT NULL,
    lead_id integer NOT NULL,
    contact_id integer,
    company_id integer,
    deal_id integer,
    channel_type character varying(30) NOT NULL,
    channel_identity character varying(255),
    direction character varying(10) NOT NULL,
    sender character varying(100),
    content_text text,
    original_language character varying(10),
    external_message_id character varying(255),
    raw_payload jsonb,
    status character varying(20) DEFAULT 'sent'::character varying,
    translated_text text,
    analysis jsonb,
    occurred_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    recorded_by_user_id integer,
    is_manual boolean,
    CONSTRAINT conversation_logs_pkey PRIMARY KEY (id),
    CONSTRAINT conversation_logs_external_message_id_key UNIQUE (external_message_id),
    CONSTRAINT conversation_logs_direction_check CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT fk_conversation_logs_lead FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id) ON UPDATE RESTRICT ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_conv_logs_company_id ON {schema}.conversation_logs USING btree (company_id);
CREATE INDEX IF NOT EXISTS idx_conv_logs_contact_id ON {schema}.conversation_logs USING btree (contact_id);
CREATE INDEX IF NOT EXISTS idx_conv_logs_deleted_at ON {schema}.conversation_logs USING btree (deleted_at) WHERE (deleted_at IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_conv_logs_occurred_at ON {schema}.conversation_logs USING btree (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_logs_tenant_id ON {schema}.conversation_logs USING btree (tenant_id);

-- 登録の移行: migrations/20260604_180000_analytics_agent_a_tables.sql
CREATE TABLE IF NOT EXISTS {schema}.customer_scores (
    id SERIAL,
    tenant_id integer NOT NULL,
    lead_id integer NOT NULL,
    score numeric(5,3) NOT NULL,
    confidence numeric(4,3) NOT NULL,
    tier character varying(10) NOT NULL,
    signal_summary jsonb DEFAULT '{{}}'::jsonb NOT NULL,
    sample_size integer DEFAULT 0 NOT NULL,
    is_cold_start boolean DEFAULT true NOT NULL,
    override_score numeric(5,3),
    override_note text,
    override_by integer,
    override_at timestamp with time zone,
    calibration_id integer,
    scored_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT customer_scores_pkey PRIMARY KEY (id),
    CONSTRAINT customer_scores_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT customer_scores_override_score_check CHECK (((override_score IS NULL) OR ((override_score >= (0)::numeric) AND (override_score <= (1)::numeric)))),
    CONSTRAINT customer_scores_score_check CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric))),
    CONSTRAINT customer_scores_tier_check CHECK (tier IN ('要観察', '有望', '最有望'))
);
CREATE INDEX IF NOT EXISTS idx_customer_scores_tier ON {schema}.customer_scores USING btree (tier);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_scores_lead_id ON {schema}.customer_scores USING btree (lead_id);

-- 登録の移行: migrations/20261001_150000_create_discord_channel_webhooks.sql
CREATE TABLE IF NOT EXISTS {schema}.discord_channel_webhooks (
    id SERIAL,
    tenant_id integer DEFAULT (current_setting('app.tenant_id'::text, true))::integer NOT NULL,
    channel_id text NOT NULL,
    webhook_id text NOT NULL,
    webhook_token_encrypted text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT discord_channel_webhooks_pkey PRIMARY KEY (id),
    CONSTRAINT uq_discord_channel_webhooks_channel UNIQUE (channel_id)
);
CREATE INDEX IF NOT EXISTS idx_dcw_tenant ON {schema}.discord_channel_webhooks USING btree (tenant_id);

-- 登録の移行: scripts/migrate_011_phase5_tenant_tables.py（作る SQL: migrations/011_add_phase5_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.erp_sync_logs (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    sync_type character varying(50) NOT NULL,
    direction character varying(10) DEFAULT 'export'::character varying NOT NULL,
    record_count integer DEFAULT 0,
    status character varying(20) DEFAULT 'pending'::character varying,
    error_message text,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    created_by integer,
    CONSTRAINT erp_sync_logs_pkey PRIMARY KEY (id)
);

-- 登録の移行: migrations/20260902_100000_create_lead_attachments.sql
CREATE TABLE IF NOT EXISTS {schema}.lead_attachments (
    id SERIAL,
    tenant_id integer NOT NULL,
    lead_id integer NOT NULL,
    message_id character varying(64) NOT NULL,
    platform character varying(32) NOT NULL,
    file_path text NOT NULL,
    file_size bigint NOT NULL,
    content_type character varying(128),
    original_filename text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lead_attachments_pkey PRIMARY KEY (id),
    CONSTRAINT lead_attachments_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_la_lead_id ON {schema}.lead_attachments USING btree (lead_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_la_message_id ON {schema}.lead_attachments USING btree (message_id);
CREATE INDEX IF NOT EXISTS idx_la_tenant_created ON {schema}.lead_attachments USING btree (tenant_id, created_at);

-- 登録の移行: migrations/20260614_100000_create_sales_form_tables.sql
CREATE TABLE IF NOT EXISTS {schema}.tenant_sales_form_options (
    id SERIAL,
    tenant_id integer NOT NULL,
    label character varying(100) NOT NULL,
    value character varying(100) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tenant_sales_form_options_pkey PRIMARY KEY (id),
    CONSTRAINT tenant_sales_form_options_tenant_id_value_key UNIQUE (tenant_id, value)
);
CREATE INDEX IF NOT EXISTS idx_tenant_sales_form_options_tenant_active ON {schema}.tenant_sales_form_options USING btree (tenant_id, is_active);

-- 登録の移行: migrations/20260614_100000_create_sales_form_tables.sql
CREATE TABLE IF NOT EXISTS {schema}.lead_sales_form_selections (
    id SERIAL,
    lead_id integer NOT NULL,
    option_id integer NOT NULL,
    other_text text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT lead_sales_form_selections_pkey PRIMARY KEY (id),
    CONSTRAINT lead_sales_form_selections_lead_id_option_id_key UNIQUE (lead_id, option_id),
    CONSTRAINT lead_sales_form_selections_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id) ON DELETE CASCADE,
    CONSTRAINT lead_sales_form_selections_option_id_fkey FOREIGN KEY (option_id) REFERENCES {schema}.tenant_sales_form_options(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_lead_sales_form_selections_lead_id ON {schema}.lead_sales_form_selections USING btree (lead_id);

-- 登録の移行: migrations/20260604_180000_analytics_agent_a_tables.sql
CREATE TABLE IF NOT EXISTS {schema}.message_labels (
    id SERIAL,
    tenant_id integer NOT NULL,
    message_id integer NOT NULL,
    lead_id integer,
    label character varying(30) NOT NULL,
    confidence numeric(4,3) NOT NULL,
    direction character varying(10) NOT NULL,
    source character varying(20) DEFAULT 'rule'::character varying NOT NULL,
    override_by integer,
    override_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT message_labels_pkey PRIMARY KEY (id),
    CONSTRAINT message_labels_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT message_labels_direction_check CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT message_labels_label_check CHECK (label IN ('price_focus', 'substance_talk', 'self_disclosure', 'early_purchase_signal', 'other')),
    CONSTRAINT message_labels_source_check CHECK (source IN ('rule', 'llm', 'human'))
);
CREATE INDEX IF NOT EXISTS idx_message_labels_lead_id ON {schema}.message_labels USING btree (lead_id);
CREATE INDEX IF NOT EXISTS idx_message_labels_message_id ON {schema}.message_labels USING btree (message_id);

-- 登録の移行: migrations/094_create_message_translations.sql
CREATE TABLE IF NOT EXISTS {schema}.message_translations (
    id SERIAL,
    message_id text NOT NULL,
    target_language character varying(10) NOT NULL,
    translated_text text NOT NULL,
    engine character varying(50) DEFAULT 'gemini-2.5-flash'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id integer,
    confidence real,
    original_language character varying(10),
    CONSTRAINT message_translations_pkey PRIMARY KEY (id),
    CONSTRAINT uq_message_translations UNIQUE (message_id, target_language)
);
CREATE INDEX IF NOT EXISTS idx_message_translations_message_id ON {schema}.message_translations USING btree (message_id);

-- 登録の移行: migrations/20260927_100000_create_meta_message_reactions.sql
CREATE TABLE IF NOT EXISTS {schema}.meta_message_reactions (
    id SERIAL,
    tenant_id integer DEFAULT (current_setting('app.tenant_id'::text, true))::integer NOT NULL,
    meta_message_id integer NOT NULL,
    emoji_name text NOT NULL,
    emoji_id text,
    emoji_animated boolean DEFAULT false,
    reactor_discord_user_id text NOT NULL,
    reactor_display_name text,
    is_bot_reaction boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT meta_message_reactions_pkey PRIMARY KEY (id),
    CONSTRAINT uq_reaction_per_user_emoji UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id),
    CONSTRAINT meta_message_reactions_meta_message_id_fkey FOREIGN KEY (meta_message_id) REFERENCES {schema}.meta_messages(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_mmr_meta_message_id ON {schema}.meta_message_reactions USING btree (meta_message_id);
CREATE INDEX IF NOT EXISTS idx_mmr_tenant ON {schema}.meta_message_reactions USING btree (tenant_id);

-- 登録の移行: scripts/migrate_009_phase4_tenant_tables.py（作る SQL: migrations/009_add_phase4_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.notification_channels (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    channel_type character varying(20) DEFAULT 'discord'::character varying NOT NULL,
    channel_name character varying(100) NOT NULL,
    webhook_url character varying(500) NOT NULL,
    event_types text DEFAULT '[]'::text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    blueprint_key text,
    CONSTRAINT notification_channels_pkey PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key ON {schema}.notification_channels USING btree (blueprint_key) WHERE (blueprint_key IS NOT NULL);

-- 登録の移行: scripts/migrate_009_phase4_tenant_tables.py（作る SQL: migrations/009_add_phase4_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.notification_logs (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    channel_id integer,
    event_type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    message text,
    status character varying(20) DEFAULT 'pending'::character varying,
    sent_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT notification_logs_pkey PRIMARY KEY (id),
    CONSTRAINT notification_logs_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES {schema}.notification_channels(id)
);

-- 登録の移行: scripts/migrate_adr021_sprint5_commissions.py（作る SQL: migrations/050_add_commissions.sql）
CREATE TABLE IF NOT EXISTS {schema}.order_commissions (
    id SERIAL,
    order_id integer NOT NULL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    role text NOT NULL,
    staff_id integer,
    calculated_amount numeric(14,2) DEFAULT 0 NOT NULL,
    calculated_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT order_commissions_pkey PRIMARY KEY (id),
    CONSTRAINT order_commissions_order_id_role_key UNIQUE (order_id, role),
    CONSTRAINT fk_order_commissions_staff_id_user FOREIGN KEY (staff_id) REFERENCES public.users(id) ON DELETE SET NULL,
    CONSTRAINT order_commissions_order_id_fkey FOREIGN KEY (order_id) REFERENCES {schema}.orders(id) ON DELETE CASCADE,
    CONSTRAINT order_commissions_role_check CHECK ((role = ANY (ARRAY['sales'::text, 'order'::text, 'ship'::text, 'purchase'::text, 'trouble'::text])))
);
CREATE INDEX IF NOT EXISTS idx_order_commissions_order ON {schema}.order_commissions USING btree (order_id);
CREATE INDEX IF NOT EXISTS idx_order_commissions_staff ON {schema}.order_commissions USING btree (staff_id);
CREATE INDEX IF NOT EXISTS idx_order_commissions_tenant ON {schema}.order_commissions USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_order_commissions_tenant_calc ON {schema}.order_commissions USING btree (tenant_id, calculated_at);

-- 登録の移行: scripts/migrate_adr021_sprint2_financials.py（作る SQL: migrations/047_create_order_financials.sql）
CREATE TABLE IF NOT EXISTS {schema}.order_financials (
    id SERIAL,
    order_id integer NOT NULL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    revenue_amount numeric(14,2) DEFAULT 0,
    purchase_cost numeric(14,2),
    purchase_shipping numeric(14,2) DEFAULT 0,
    paypal_fee numeric(14,2) DEFAULT 0,
    wise_fee numeric(14,2) DEFAULT 0,
    exchange_fee numeric(14,2) DEFAULT 0,
    outsource_fee numeric(14,2) DEFAULT 0,
    packing_fee numeric(14,2) DEFAULT 0,
    ad_cost numeric(14,2) DEFAULT 0,
    return_fee numeric(14,2) DEFAULT 0,
    refund_amount numeric(14,2) DEFAULT 0,
    commission_base_amount numeric(14,2) DEFAULT 0,
    tax_refund numeric(14,2) DEFAULT 0,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT order_financials_pkey PRIMARY KEY (id),
    CONSTRAINT order_financials_order_id_key UNIQUE (order_id),
    CONSTRAINT order_financials_order_id_fkey FOREIGN KEY (order_id) REFERENCES {schema}.orders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_order_financials_created_at ON {schema}.order_financials USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_order_financials_order ON {schema}.order_financials USING btree (order_id);
CREATE INDEX IF NOT EXISTS idx_order_financials_tenant ON {schema}.order_financials USING btree (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_order_financials_tenant_order ON {schema}.order_financials USING btree (tenant_id, order_id);

-- 登録の移行: scripts/migrate_adr021_sprint4_purchase.py（作る SQL: migrations/049_create_order_purchase_details.sql）
CREATE TABLE IF NOT EXISTS {schema}.order_purchase_details (
    id SERIAL,
    order_id integer NOT NULL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    purchase_staff text,
    purchase_date date,
    transaction_no text,
    supplier_name text,
    supplier_url text,
    purchase_amount numeric(14,2) DEFAULT 0,
    purchase_quantity integer DEFAULT 0,
    purchase_total numeric(14,2) DEFAULT 0,
    purchase_shipping numeric(14,2) DEFAULT 0,
    carrier_name text,
    waybill_no text,
    purchase_note text,
    purchase_status text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT order_purchase_details_pkey PRIMARY KEY (id),
    CONSTRAINT order_purchase_details_order_id_key UNIQUE (order_id),
    CONSTRAINT order_purchase_details_order_id_fkey FOREIGN KEY (order_id) REFERENCES {schema}.orders(id) ON DELETE CASCADE,
    CONSTRAINT order_purchase_details_purchase_status_check CHECK ((purchase_status = ANY (ARRAY[''::text, 'confirmed'::text])))
);
CREATE INDEX IF NOT EXISTS idx_order_purchase_details_order ON {schema}.order_purchase_details USING btree (order_id);
CREATE INDEX IF NOT EXISTS idx_order_purchase_details_status ON {schema}.order_purchase_details USING btree (purchase_status);
CREATE INDEX IF NOT EXISTS idx_order_purchase_details_tenant ON {schema}.order_purchase_details USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_order_purchase_details_tenant_supplier ON {schema}.order_purchase_details USING btree (tenant_id, supplier_name);
CREATE UNIQUE INDEX IF NOT EXISTS uq_order_purchase_details_tenant_order ON {schema}.order_purchase_details USING btree (tenant_id, order_id);

-- 登録の移行: scripts/migrate_adr021_sprint3_shipping.py（作る SQL: migrations/048_create_order_shipping_details.sql）
CREATE TABLE IF NOT EXISTS {schema}.order_shipping_details (
    id SERIAL,
    order_id integer NOT NULL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    recipient_name character varying(255),
    phone character varying(50),
    email character varying(255),
    tax_number character varying(100),
    address1 character varying(255),
    address2 character varying(255),
    address3 character varying(255),
    city character varying(100),
    state_code character varying(20),
    zip_code character varying(50),
    country_code character varying(10),
    length_cm numeric(8,2),
    width_cm numeric(8,2),
    height_cm numeric(8,2),
    weight_kg numeric(8,3),
    volume_g numeric(10,2),
    box_count integer,
    packing_memo text,
    packing_type character varying(50),
    inspection_status character varying(50),
    item_description character varying(500),
    item_price_usd numeric(12,2),
    exchange_rate numeric(12,6),
    hs_code character varying(50),
    tax_id character varying(100),
    fedex_id character varying(100),
    carrier character varying(20),
    ship_method character varying(50),
    ship_date date,
    tracking_number character varying(200),
    est_shipping_fee numeric(12,2),
    label_issued_at timestamp with time zone,
    pickup_requested_at timestamp with time zone,
    shipped_at timestamp with time zone,
    notified_at timestamp with time zone,
    ship_memo text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    address_type character varying(20),
    confirmed_shipping_fee numeric(12,2),
    confirmed_currency character varying(10),
    label_drive_url text,
    pickup_confirmation_code character varying(100),
    surcharges jsonb,
    CONSTRAINT order_shipping_details_pkey PRIMARY KEY (id),
    CONSTRAINT order_shipping_details_order_id_key UNIQUE (order_id),
    CONSTRAINT order_shipping_details_address_type_check CHECK (((address_type IS NULL) OR address_type IN ('RESIDENTIAL', 'BUSINESS'))),
    CONSTRAINT order_shipping_details_carrier_check CHECK (((carrier IS NULL) OR carrier IN ('elogi', 'fedex', 'dhl', 'yamato', 'other'))),
    CONSTRAINT order_shipping_details_order_id_fkey FOREIGN KEY (order_id) REFERENCES {schema}.orders(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_order_shipping_details_carrier ON {schema}.order_shipping_details USING btree (carrier);
CREATE INDEX IF NOT EXISTS idx_order_shipping_details_order ON {schema}.order_shipping_details USING btree (order_id);
CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tenant ON {schema}.order_shipping_details USING btree (tenant_id);
CREATE INDEX IF NOT EXISTS idx_order_shipping_details_tracking ON {schema}.order_shipping_details USING btree (tracking_number);
CREATE UNIQUE INDEX IF NOT EXISTS uq_order_shipping_details_tenant_order ON {schema}.order_shipping_details USING btree (tenant_id, order_id);

-- 登録の移行: migrations/20260604_220000_create_translation_glossary.sql
CREATE TABLE IF NOT EXISTS {schema}.outbound_translation_drafts (
    id SERIAL,
    tenant_id integer NOT NULL,
    lead_id integer,
    original_text text NOT NULL,
    draft_text text NOT NULL,
    confidence real,
    flagged_terms jsonb,
    model character varying(50) NOT NULL,
    confirmed_at timestamp with time zone,
    final_text text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    meta_message_id integer,
    is_edited boolean,
    CONSTRAINT outbound_translation_drafts_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_outbound_drafts_tenant_lead ON {schema}.outbound_translation_drafts USING btree (tenant_id, lead_id);
CREATE INDEX IF NOT EXISTS idx_outbound_drafts_unconfirmed ON {schema}.outbound_translation_drafts USING btree (tenant_id, confirmed_at) WHERE (confirmed_at IS NULL);

-- 登録の移行: migrations/20260612_154322_create_paypal_disputes.sql
CREATE TABLE IF NOT EXISTS {schema}.paypal_disputes (
    id SERIAL,
    dispute_id text NOT NULL,
    invoice_id integer,
    pp_status text,
    reason text,
    amount numeric(15,2),
    currency text,
    raw jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT paypal_disputes_pkey PRIMARY KEY (id),
    CONSTRAINT paypal_disputes_dispute_id_key UNIQUE (dispute_id),
    CONSTRAINT paypal_disputes_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES {schema}.invoices(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_paypal_disputes_invoice ON {schema}.paypal_disputes USING btree (invoice_id);

-- 登録の移行: scripts/migrate_011_phase5_tenant_tables.py（作る SQL: migrations/011_add_phase5_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.shifts (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    user_id integer NOT NULL,
    shift_date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    shift_type character varying(20) DEFAULT 'normal'::character varying,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT shifts_pkey PRIMARY KEY (id),
    CONSTRAINT shifts_tenant_id_user_id_shift_date_key UNIQUE (tenant_id, user_id, shift_date)
);
CREATE INDEX IF NOT EXISTS idx_shifts_date ON {schema}.shifts USING btree (shift_date);
CREATE INDEX IF NOT EXISTS idx_shifts_user ON {schema}.shifts USING btree (user_id);

-- 登録の移行: scripts/migrate_009_phase4_tenant_tables.py（作る SQL: migrations/009_add_phase4_tenant_tables.sql）
CREATE TABLE IF NOT EXISTS {schema}.staff_reports (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    report_code character varying(20),
    report_type character varying(20) NOT NULL,
    user_id integer NOT NULL,
    period character varying(20) NOT NULL,
    review text,
    goals text,
    challenges text,
    self_evaluation text,
    ai_feedback text,
    reviewer_id integer,
    reviewer_comment text,
    reviewed_at timestamp with time zone,
    submitted_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT staff_reports_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_staff_reports_type ON {schema}.staff_reports USING btree (report_type);
CREATE INDEX IF NOT EXISTS idx_staff_reports_user ON {schema}.staff_reports USING btree (user_id);

-- 登録の移行: migrations/20260604_180000_analytics_agent_a_tables.sql
CREATE TABLE IF NOT EXISTS {schema}.tenant_calibrations (
    id SERIAL,
    tenant_id integer NOT NULL,
    label_weights jsonb DEFAULT '{{}}'::jsonb NOT NULL,
    win_sample_size integer DEFAULT 0 NOT NULL,
    loss_sample_size integer DEFAULT 0 NOT NULL,
    is_cold_start boolean DEFAULT true NOT NULL,
    calibrated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tenant_calibrations_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_tenant_calibrations_latest ON {schema}.tenant_calibrations USING btree (tenant_id, calibrated_at DESC);

-- 登録の移行: scripts/migrate_adr021_sprint5_commissions.py（作る SQL: migrations/050_add_commissions.sql）
CREATE TABLE IF NOT EXISTS {schema}.tenant_commission_settings (
    id SERIAL,
    tenant_id integer DEFAULT {tenant_id} NOT NULL,
    commission_rates jsonb DEFAULT '{{"ship": {{"type": "fixed", "value": 200}}, "order": {{"type": "rate", "value": 0.10}}, "sales": {{"type": "rate", "value": 0.10}}, "trouble": {{"type": "fixed", "value": 500}}, "purchase": {{"type": "fixed", "value": 100}}}}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tenant_commission_settings_pkey PRIMARY KEY (id),
    CONSTRAINT tenant_commission_settings_tenant_id_key UNIQUE (tenant_id)
);
CREATE INDEX IF NOT EXISTS idx_tenant_commission_settings_tenant ON {schema}.tenant_commission_settings USING btree (tenant_id);

-- 既存の表に足す索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_ccc_unique_channel_purpose ON {schema}.contact_contact_channels USING btree (contact_id, channel, COALESCE(purpose, ''::character varying));
CREATE INDEX IF NOT EXISTS idx_leads_channel_type ON {schema}.leads USING btree (channel_type);
CREATE INDEX IF NOT EXISTS idx_leads_discord_guild_channel_id ON {schema}.leads USING btree (tenant_id, discord_guild_channel_id) WHERE (discord_guild_channel_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_leads_discord_user_id ON {schema}.leads USING btree (tenant_id, discord_user_id) WHERE (discord_user_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_leads_initiative ON {schema}.leads USING btree (initiative) WHERE (initiative IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_meta_messages_discord ON {schema}.meta_messages USING btree (tenant_id, platform, lead_id) WHERE ((platform)::text = 'discord'::text);
CREATE INDEX IF NOT EXISTS idx_meta_messages_lead_created ON {schema}.meta_messages USING btree (lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_meta_messages_lead_unread ON {schema}.meta_messages USING btree (lead_id) WHERE (((direction)::text = 'inbound'::text) AND (seen_at IS NULL));
CREATE INDEX IF NOT EXISTS idx_meta_messages_tenant_page ON {schema}.meta_messages USING btree (tenant_id, page_id) WHERE (page_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_poi_order_item_id ON {schema}.purchase_order_items USING btree (order_item_id);
CREATE INDEX IF NOT EXISTS idx_staff_phone ON {schema}.staff USING btree (phone) WHERE (phone IS NOT NULL);

-- 既存の表に足す外部キー（別名。名前があれば何もしない）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_bots_owner_staff_id_user' AND conrelid = '{schema}.bots'::regclass) THEN
        ALTER TABLE {schema}.bots ADD CONSTRAINT fk_bots_owner_staff_id_user FOREIGN KEY (owner_staff_id) REFERENCES public.users(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_deal_close_reasons_lead' AND conrelid = '{schema}.deal_close_reasons'::regclass) THEN
        ALTER TABLE {schema}.deal_close_reasons ADD CONSTRAINT fk_deal_close_reasons_lead FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_meta_messages_seen_by_staff_id_user' AND conrelid = '{schema}.meta_messages'::regclass) THEN
        ALTER TABLE {schema}.meta_messages ADD CONSTRAINT fk_meta_messages_seen_by_staff_id_user FOREIGN KEY (seen_by_staff_id) REFERENCES public.users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_meta_messages_sent_by_staff_id_user' AND conrelid = '{schema}.meta_messages'::regclass) THEN
        ALTER TABLE {schema}.meta_messages ADD CONSTRAINT fk_meta_messages_sent_by_staff_id_user FOREIGN KEY (sent_by_staff_id) REFERENCES public.users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_poi_order_item' AND conrelid = '{schema}.purchase_order_items'::regclass) THEN
        ALTER TABLE {schema}.purchase_order_items ADD CONSTRAINT fk_poi_order_item FOREIGN KEY (order_item_id) REFERENCES {schema}.order_items(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_quotes_lead' AND conrelid = '{schema}.quotes'::regclass) THEN
        ALTER TABLE {schema}.quotes ADD CONSTRAINT fk_quotes_lead FOREIGN KEY (lead_id) REFERENCES {schema}.leads(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_tenant_meta_config_connected_by_staff_id_user' AND conrelid = '{schema}.tenant_meta_config'::regclass) THEN
        ALTER TABLE {schema}.tenant_meta_config ADD CONSTRAINT fk_tenant_meta_config_connected_by_staff_id_user FOREIGN KEY (connected_by_staff_id) REFERENCES public.users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- updated_at を更新する関数とトリガ
CREATE OR REPLACE FUNCTION {schema}.set_updated_at_calendar_categories()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_calendar_events()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_goals()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_lead_playbook()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_commissions()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_financials()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_purchase_details()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_order_shipping_details()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_tenant_commission_settings()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_tenant_meta_config()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION {schema}.set_updated_at_tenant_profile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $function$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_calendar_categories_updated_at' AND tgrelid = '{schema}.calendar_categories'::regclass) THEN
        CREATE TRIGGER trg_calendar_categories_updated_at BEFORE UPDATE ON {schema}.calendar_categories FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_calendar_categories();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_calendar_events_updated_at' AND tgrelid = '{schema}.calendar_events'::regclass) THEN
        CREATE TRIGGER trg_calendar_events_updated_at BEFORE UPDATE ON {schema}.calendar_events FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_calendar_events();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_goals' AND tgrelid = '{schema}.goals'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_goals BEFORE UPDATE ON {schema}.goals FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_goals();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_la_updated_at' AND tgrelid = '{schema}.lead_attachments'::regclass) THEN
        CREATE TRIGGER trg_la_updated_at BEFORE UPDATE ON {schema}.lead_attachments FOR EACH ROW EXECUTE FUNCTION {schema}.trg_set_updated_at();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_lead_playbook' AND tgrelid = '{schema}.lead_playbook'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_lead_playbook BEFORE UPDATE ON {schema}.lead_playbook FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_lead_playbook();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_order_commissions' AND tgrelid = '{schema}.order_commissions'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_order_commissions BEFORE UPDATE ON {schema}.order_commissions FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_order_commissions();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_order_financials' AND tgrelid = '{schema}.order_financials'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_order_financials BEFORE UPDATE ON {schema}.order_financials FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_order_financials();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_order_purchase_details' AND tgrelid = '{schema}.order_purchase_details'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_order_purchase_details BEFORE UPDATE ON {schema}.order_purchase_details FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_order_purchase_details();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_order_shipping_details' AND tgrelid = '{schema}.order_shipping_details'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_order_shipping_details BEFORE UPDATE ON {schema}.order_shipping_details FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_order_shipping_details();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_tenant_commission_settings' AND tgrelid = '{schema}.tenant_commission_settings'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_tenant_commission_settings BEFORE UPDATE ON {schema}.tenant_commission_settings FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_tenant_commission_settings();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_tenant_meta_config' AND tgrelid = '{schema}.tenant_meta_config'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_tenant_meta_config BEFORE UPDATE ON {schema}.tenant_meta_config FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_tenant_meta_config();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_tenant_profile' AND tgrelid = '{schema}.tenant_profile'::regclass) THEN
        CREATE TRIGGER trigger_set_updated_at_tenant_profile BEFORE UPDATE ON {schema}.tenant_profile FOR EACH ROW EXECUTE FUNCTION {schema}.set_updated_at_tenant_profile();
    END IF;
END $$;

-- 会社の集計ビュー
-- 元: migrations/20261108_100000_rebuild_company_stats_on_meta_messages.sql（同じ書き方にして、流した後と形を揃える）
CREATE OR REPLACE VIEW {schema}.v_company_stats AS
SELECT
    c.id AS company_id,
    COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,
    COUNT(DISTINCT i.id) AS paid_invoice_count,
    MAX(i.paid_at) AS last_paid_at,
    COUNT(CASE WHEN l.status IN ('negotiating', 'existing_customer', 'lost') THEN 1 END) AS deal_count,
    COUNT(DISTINCT m.id) AS conversation_count,
    MAX(COALESCE(m.occurred_at, m.created_at)) AS last_conversation_at
FROM {schema}.companies c
LEFT JOIN {schema}.invoices i
    ON i.company_id = c.id
    AND i.paid_at IS NOT NULL
    AND i.voided_at IS NULL
LEFT JOIN {schema}.leads l
    ON l.id = c.lead_id
LEFT JOIN {schema}.meta_messages m
    ON m.company_id = c.id
    AND m.deleted_at IS NULL
GROUP BY c.id;
"""

# RLS有効化のALTER TABLE群（;で安全に分割可能）
# 連携テーブル（role_permissions, user_roles, team_members）は tenant_id カラムを持たないが、
# 親テーブルのRLSを経由した保護を追加することで防御の二重化を実現する。
_RLS_ENABLE_SQL = """
-- ADR-089 Sprint 5: customers は廃止済。RLS は companies 体系のみ。
-- 便D-1: deals RLS は除去済み（deals テーブルは便E で DROP 予定）
ALTER TABLE {schema}.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.shipping_zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.shipping_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.purchase_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.meta_messages ENABLE ROW LEVEL SECURITY;
-- Phase 1-D Sprint 1: Meta OAuth 接続情報
ALTER TABLE {schema}.tenant_meta_config ENABLE ROW LEVEL SECURITY;
-- Phase 1 再設計の新テーブル（ADR-089 Sprint 5: customer_* 削除済）
ALTER TABLE {schema}.staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.staff_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.staff_ui_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.bots ENABLE ROW LEVEL SECURITY;
-- Phase 1-B-2: companies + contacts 階層
ALTER TABLE {schema}.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.company_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.company_sales_channels ENABLE ROW LEVEL SECURITY;
-- ADR-089 Sprint 1/Sprint 5: company_discord の RLS
ALTER TABLE {schema}.company_discord ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.contact_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.contact_discord ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.contact_contact_channels ENABLE ROW LEVEL SECURITY;
-- ADR-015 §7: テナント別 AI 対応プレイブック
ALTER TABLE {schema}.lead_playbook ENABLE ROW LEVEL SECURITY;
-- D-2: A在庫（ADR SA-04/05）
ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
-- Phase 1-B-2 Step 5d / PR γ: _customer_migration_map は migration 036 で DROP 済。
-- D-2: A在庫（ADR SA-04/05）
ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
-- ADR-1061 2-2c1: 発行元の会社情報と振込先
ALTER TABLE {schema}.tenant_issuer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;
-- invoice-create-portfolio 便A: 関税の決まりの表2つ
ALTER TABLE {schema}.tenant_duty_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_duty_rule_components ENABLE ROW LEVEL SECURITY;-- 段5 5-2: 登録の移行が作る表の RLS
ALTER TABLE {schema}.archives ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.conversation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.customer_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.discord_channel_webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.erp_sync_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.lead_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.message_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.message_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.message_translations FORCE ROW LEVEL SECURITY;
ALTER TABLE {schema}.meta_message_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.notification_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.notification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.order_commissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.order_financials ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.order_purchase_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.order_shipping_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.staff_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_calibrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_commission_settings ENABLE ROW LEVEL SECURITY;
"""

# テナント分離ポリシー（DO $$ ... END $$ ブロックは1ステートメントとして実行する。
# 内部の;でsplitすると$$ドル引用が分断されPostgresSyntaxErrorになるため）
_RLS_POLICY_SQL = """
DO $$
BEGIN
    -- ADR-089 Sprint 5: tenant_isolation_customers 削除済（customers テーブル廃止）
    -- 便D-1: tenant_isolation_deals 削除済（deals テーブルは便E で DROP 予定）
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_orders' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_orders ON {schema}.orders
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_order_items' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_order_items ON {schema}.order_items
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_audit_logs' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_audit_logs ON {schema}.audit_logs
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_leads' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_leads ON {schema}.leads
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_roles' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_roles ON {schema}.roles
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_teams' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_teams ON {schema}.teams
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- 連携テーブルは tenant_id カラムを持たないため、親テーブルのRLSをEXISTS経由で参照
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_role_permissions' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_role_permissions ON {schema}.role_permissions
            USING (EXISTS (
                SELECT 1 FROM {schema}.roles r
                WHERE r.id = role_permissions.role_id
                  AND r.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_user_roles' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_user_roles ON {schema}.user_roles
            USING (EXISTS (
                SELECT 1 FROM {schema}.roles r
                WHERE r.id = user_roles.role_id
                  AND r.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_team_members' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_team_members ON {schema}.team_members
            USING (EXISTS (
                SELECT 1 FROM {schema}.teams t
                WHERE t.id = team_members.team_id
                  AND t.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- Phase 2: 販売・財務プロセスのテーブル
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_products' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_products ON {schema}.products
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- D-2: A在庫（ADR SA-04/05）— ポリシー名は既存テナント（migration 20260604_140000）と統一
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'own_inventory_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_shipping_zones' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_shipping_zones ON {schema}.shipping_zones
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_shipping_rates' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_shipping_rates ON {schema}.shipping_rates
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_quotes' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_quotes ON {schema}.quotes
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_invoices' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_invoices ON {schema}.invoices
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- 明細テーブル（tenant_id なし → 親テーブル経由）
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_quote_items' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_quote_items ON {schema}.quote_items
            USING (EXISTS (
                SELECT 1 FROM {schema}.quotes q
                WHERE q.id = quote_items.quote_id
                  AND q.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_invoice_items' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_invoice_items ON {schema}.invoice_items
            USING (EXISTS (
                SELECT 1 FROM {schema}.invoices inv
                WHERE inv.id = invoice_items.invoice_id
                  AND inv.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- Phase 3: 仕入れ・調達管理
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_purchase_orders' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_purchase_orders ON {schema}.purchase_orders
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_po_items' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_po_items ON {schema}.purchase_order_items
            USING (EXISTS (
                SELECT 1 FROM {schema}.purchase_orders po
                WHERE po.id = purchase_order_items.purchase_order_id
                  AND po.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- Meta Messaging
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_meta_messages' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_meta_messages ON {schema}.meta_messages
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- Phase 1-D Sprint 1: tenant_meta_config（Page / IG OAuth 接続情報）
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_tenant_meta_config' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_tenant_meta_config ON {schema}.tenant_meta_config
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- ADR-089 Sprint 5: customer_addresses/customer_sales_channels/customer_discord/
    -- customer_contact_channels ポリシー削除済（テーブル廃止）
    -- Phase 1 再設計: staff / bots
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_staff' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_staff ON {schema}.staff
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_bots' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_bots ON {schema}.bots
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_staff_emails' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_staff_emails ON {schema}.staff_emails
            USING (EXISTS (
                SELECT 1 FROM {schema}.staff s
                WHERE s.id = staff_emails.staff_id
                  AND s.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_staff_ui_preferences' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_staff_ui_preferences ON {schema}.staff_ui_preferences
            USING (EXISTS (
                SELECT 1 FROM {schema}.staff s
                WHERE s.id = staff_ui_preferences.staff_id
                  AND s.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- ADR-089 Sprint 5: tenant_isolation_customer_contact_channels 削除済（テーブル廃止）
    -- Phase 1-B-2: companies + contacts 階層
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_companies' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_companies ON {schema}.companies
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_contacts' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_contacts ON {schema}.contacts
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_company_addresses' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_company_addresses ON {schema}.company_addresses
            USING (EXISTS (
                SELECT 1 FROM {schema}.companies c
                WHERE c.id = company_addresses.company_id
                  AND c.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_company_sales_channels' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_company_sales_channels ON {schema}.company_sales_channels
            USING (EXISTS (
                SELECT 1 FROM {schema}.companies c
                WHERE c.id = company_sales_channels.company_id
                  AND c.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- ADR-089 Sprint 1/Sprint 5: company_discord の RLS ポリシー
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_company_discord' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_company_discord ON {schema}.company_discord
            USING (EXISTS (
                SELECT 1 FROM {schema}.companies c
                WHERE c.id = company_discord.company_id
                  AND c.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_contact_emails' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_contact_emails ON {schema}.contact_emails
            USING (EXISTS (
                SELECT 1 FROM {schema}.contacts ct
                WHERE ct.id = contact_emails.contact_id
                  AND ct.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_contact_discord' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_contact_discord ON {schema}.contact_discord
            USING (EXISTS (
                SELECT 1 FROM {schema}.contacts ct
                WHERE ct.id = contact_discord.contact_id
                  AND ct.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_contact_contact_channels' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_contact_contact_channels ON {schema}.contact_contact_channels
            USING (EXISTS (
                SELECT 1 FROM {schema}.contacts ct
                WHERE ct.id = contact_contact_channels.contact_id
                  AND ct.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    -- Phase 1-B-2 Step 5d / PR γ: tenant_isolation_customer_migration_map policy は
    -- migration 036 で _customer_migration_map テーブルごと削除されるため撤去済。
    -- ADR-015 §7: テナント別 AI 対応プレイブック
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_lead_playbook' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_lead_playbook ON {schema}.lead_playbook
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- D-2: A在庫（ADR SA-04/05）— ポリシー名は既存テナント（migration 20260604_140000）と統一
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'own_inventory_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- ADR-1061 2-2c1: 発行元の会社情報と振込先 — ポリシー名は migration 20261112_160000 と同じ
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_issuer_profiles_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_issuer_profiles_tenant_isolation ON {schema}.tenant_issuer_profiles
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_methods_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_methods_tenant_isolation ON {schema}.tenant_invoice_payment_methods
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_bank_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_bank_tenant_isolation ON {schema}.tenant_invoice_payment_bank
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_wise_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- invoice-create-portfolio 便A: 関税の決まりの表2つ — ポリシー名は migration 20261113_120000 と同じ
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rules_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_duty_rules_tenant_isolation ON {schema}.tenant_duty_rules
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rule_components_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_duty_rule_components_tenant_isolation ON {schema}.tenant_duty_rule_components
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- 段5 5-2: 登録の移行が作る表の方針
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_archives' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_archives ON {schema}.archives
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'conversation_logs_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY conversation_logs_tenant_isolation ON {schema}.conversation_logs
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'customer_scores_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY customer_scores_tenant_isolation ON {schema}.customer_scores
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_discord_channel_webhooks' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_discord_channel_webhooks ON {schema}.discord_channel_webhooks
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_erp_sync_logs' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_erp_sync_logs ON {schema}.erp_sync_logs
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_lead_attachments' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_lead_attachments ON {schema}.lead_attachments
            USING (EXISTS (
                SELECT 1 FROM {schema}.leads l
                WHERE l.id = lead_attachments.lead_id
                  AND l.tenant_id = current_setting('app.tenant_id', true)::INTEGER
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'message_labels_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY message_labels_tenant_isolation ON {schema}.message_labels
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'message_translations_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY message_translations_tenant_isolation ON {schema}.message_translations
            USING ((tenant_id = (NULLIF(current_setting('app.tenant_id'::text, true), ''::text))::integer));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_meta_message_reactions' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_meta_message_reactions ON {schema}.meta_message_reactions
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_notification_channels' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_notification_channels ON {schema}.notification_channels
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_notification_logs' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_notification_logs ON {schema}.notification_logs
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_order_commissions' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_order_commissions ON {schema}.order_commissions
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_order_financials' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_order_financials ON {schema}.order_financials
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_order_purchase_details' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_order_purchase_details ON {schema}.order_purchase_details
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_order_shipping_details' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_order_shipping_details ON {schema}.order_shipping_details
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_shifts' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_shifts ON {schema}.shifts
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_staff_reports' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_staff_reports ON {schema}.staff_reports
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_calibrations_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_calibrations_tenant_isolation ON {schema}.tenant_calibrations
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_tenant_commission_settings' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_isolation_tenant_commission_settings ON {schema}.tenant_commission_settings
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
END $$
"""


# Phase 1-E F16-FU2 (2026-05-03): 新規テナント作成時に migration 044 と同等のトリガを
# 自動セットアップする。既存テナントへの適用は `scripts/migrate_meta_page_routing.py`
# 側が担当し、本関数は **新規テナント onboard 経路** からの呼び出しでのみ動く。
#
# migration 044 とのコード重複だが、ファイル読み込みベースより inline 定数の方が
# 既存パターン（_TENANT_TABLES_SQL / _RLS_*_SQL）と一貫性がある。
# F16-FU1 の `SET search_path = pg_catalog, public` も含めた版を保持する。
_META_PAGE_ROUTING_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION {schema}.sync_meta_page_routing()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $sync_mpr$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        DELETE FROM public.meta_page_routing
        WHERE tenant_id = OLD.tenant_id
          AND config_id = OLD.id;
        RETURN OLD;
    END IF;

    INSERT INTO public.meta_page_routing (
        tenant_id, config_id, schema_name,
        page_id, instagram_business_account_id, is_active, updated_at
    )
    VALUES (
        NEW.tenant_id,
        NEW.id,
        '{schema_raw}',
        NEW.page_id,
        NEW.instagram_business_account_id,
        NEW.is_active,
        NOW()
    )
    ON CONFLICT (tenant_id, config_id) DO UPDATE SET
        schema_name                     = EXCLUDED.schema_name,
        page_id                         = EXCLUDED.page_id,
        instagram_business_account_id   = EXCLUDED.instagram_business_account_id,
        is_active                       = EXCLUDED.is_active,
        updated_at                      = NOW();

    RETURN NEW;
END;
$sync_mpr$;

DROP TRIGGER IF EXISTS trg_sync_meta_page_routing ON {schema}.tenant_meta_config;
CREATE TRIGGER trg_sync_meta_page_routing
    AFTER INSERT OR UPDATE OR DELETE ON {schema}.tenant_meta_config
    FOR EACH ROW EXECUTE FUNCTION {schema}.sync_meta_page_routing();
"""


async def _assign_permissions_to_role(
    db: AsyncSession,
    schema_name: str,
    role_id: int,
    permissions_spec,
) -> None:
    """ロールに対して指定された権限を適用する（既存割当は全クリア後に再投入）。"""
    await db.execute(
        text(f"DELETE FROM {schema_name}.role_permissions WHERE role_id = :rid"),
        {"rid": role_id},
    )

    if permissions_spec == "ALL":
        await db.execute(
            text(f"""
                INSERT INTO {schema_name}.role_permissions (role_id, permission_id)
                SELECT :rid, id FROM public.permissions
            """),
            {"rid": role_id},
        )
    elif permissions_spec == "ALL_EXCEPT_SYSTEM_MANAGE":
        await db.execute(
            text(f"""
                INSERT INTO {schema_name}.role_permissions (role_id, permission_id)
                SELECT :rid, id FROM public.permissions WHERE key != :system_manage_key
            """),
            {"rid": role_id, "system_manage_key": SYSTEM_MANAGE_KEY},
        )
    elif isinstance(permissions_spec, list):
        for key in permissions_spec:
            await db.execute(
                text(f"""
                    INSERT INTO {schema_name}.role_permissions (role_id, permission_id)
                    SELECT :rid, id FROM public.permissions WHERE key = :key
                    ON CONFLICT DO NOTHING
                """),
                {"rid": role_id, "key": key},
            )


async def seed_system_roles(db: AsyncSession, tenant_id: int, schema_name: str) -> None:
    """
    共通6ロールをシードする（冪等）。

    - オーナー (system): 全権限、削除/編集不可
    - システム管理者: system.manage 以外の全権限、編集可
    - マネージャー: チーム単位のリード/案件管理、編集可
    - 営業: 顧客〜案件〜注文の販売サイクル、編集可
    - CS: 顧客フォローアップ、編集可
    - 仕入れ: 仕入先管理・発注業務、編集可
    - 発送: 梱包・出荷・配送管理、編集可

    非システムロールは「名前が既存でない場合のみ」権限を初期設定する。
    既に存在する場合は権限のカスタマイズを上書きしない（priority/descriptionのみ更新）。
    """
    for role_def in DEFAULT_ROLES:
        # 既存チェック（編集済みロールの権限を上書きしないため）
        existing = await db.execute(
            text(f"SELECT id FROM {schema_name}.roles WHERE tenant_id = :tid AND name = :name"),
            {"tid": tenant_id, "name": role_def["name"]},
        )
        existing_row = existing.first()
        is_new = existing_row is None

        # upsert（名前で識別、color/priority/description は常に最新化）
        # color も更新対象とすることで、パレット変更時に既定ロールの色を一括同期できる。
        # カスタムロール（名前が DEFAULT_ROLES にないもの）はこのループの対象外なので
        # ユーザーのカスタマイズは保持される。
        result = await db.execute(
            text(f"""
                INSERT INTO {schema_name}.roles (tenant_id, name, color, priority, is_system, description, system_key)
                VALUES (:tid, :name, :color, :priority, :is_system, :description, :system_key)
                ON CONFLICT (tenant_id, name) DO UPDATE
                SET color = EXCLUDED.color,
                    priority = EXCLUDED.priority,
                    description = EXCLUDED.description,
                    system_key = COALESCE({schema_name}.roles.system_key, EXCLUDED.system_key)
                RETURNING id
            """),
            {
                "tid": tenant_id,
                "name": role_def["name"],
                "color": role_def["color"],
                "priority": role_def["priority"],
                "is_system": role_def["is_system"],
                "description": role_def["description"],
                "system_key": role_def.get("system_key"),
            },
        )
        role_id = result.scalar_one()

        # 権限割当: システムロールは常に同期（オーナーは必ず全権限）
        # 非システムロールは「新規作成時のみ」デフォルト権限を入れる
        # （既存の場合はテナント管理者によるカスタマイズを保持）
        if role_def["is_system"] or is_new:
            await _assign_permissions_to_role(db, schema_name, role_id, role_def["permissions"])


async def create_tenant_schema(
    db: AsyncSession,
    tenant_id: int,
    admin_db: AsyncSession | None = None,
) -> str:
    """
    テナント専用スキーマを作成し、業務テーブルとRLSポリシー、
    システムロールを設定する。

    SA-18 Phase2: DDL（CREATE SCHEMA/TABLE/RLS/POLICY）は admin_db で実行し、
    シード DML（tenant_settings 等）は db で実行する。
    admin_db が None の場合は db にフォールバック（後方互換）。

    Args:
        db: データベースセッション（DML 用）
        tenant_id: テナントID（public.tenants.id）
        admin_db: 管理者セッション（DDL 用、省略時は db にフォールバック）

    Returns:
        作成したスキーマ名（例: "tenant_001"）
    """
    # admin_db が未提供なら db にフォールバック（後方互換: テスト・既存スクリプト対応）
    ddl_db = admin_db if admin_db is not None else db

    # スキーマ名はtenant_{数値ID}形式（int()で型を強制しSQLインジェクション防止）
    # セキュリティ不変条件: schema_nameは必ず ^tenant_\d{3,}$ にマッチすること
    safe_id = int(tenant_id)
    schema_name = f"tenant_{safe_id:03d}"
    if not re.match(r"^tenant_\d{3,}$", schema_name):
        raise ValueError(f"不正なスキーマ名: {schema_name}")

    # 1. スキーマ作成（DDL → admin_db）
    await ddl_db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

    # 2. 業務テーブル作成（DO $$ ブロックがあるため単純split不可、区切り工夫）
    tables_sql = _TENANT_TABLES_SQL.format(
        schema=schema_name,
        schema_raw=schema_name,
        tenant_id=safe_id,
    )
    # DO $$ ... END $$ ブロックを保ったまま分割するため、セミコロンでのsplitを避けて
    # ブロック単位で分割する（PostgreSQLは単一execute内で複数文を許容しないため
    # ステートメントを分ける必要がある）。
    await _execute_statements_preserving_do_blocks(ddl_db, tables_sql)

    # 3a. RLS有効化（ALTER TABLE群、;で分割可能）（DDL → admin_db）
    enable_sql = _RLS_ENABLE_SQL.format(schema=schema_name)
    for statement in enable_sql.strip().split(";"):
        statement = statement.strip()
        if statement:
            await ddl_db.execute(text(statement))

    # 3b. RLSポリシー（DOブロック、splitせず1ステートメントで実行）（DDL → admin_db）
    policy_sql = _RLS_POLICY_SQL.format(schema=schema_name, schema_raw=schema_name)
    await ddl_db.execute(text(policy_sql))

    # 3c. SA-18 Phase2: salesanchor_app に新スキーマの権限を GRANT（DDL → admin_db）
    # salesanchor_app ロールが存在しない環境（ローカル開発・テスト）では best-effort で実行。
    grant_sql = f"""
    DO $$
    BEGIN
      GRANT USAGE ON SCHEMA {schema_name} TO salesanchor_app;
      GRANT SELECT, INSERT, UPDATE, DELETE
        ON ALL TABLES IN SCHEMA {schema_name} TO salesanchor_app;
      GRANT USAGE, SELECT
        ON ALL SEQUENCES IN SCHEMA {schema_name} TO salesanchor_app;
      ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA {schema_name}
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
      ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA {schema_name}
        GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app;
      RAISE NOTICE 'Granted salesanchor_app on schema: {schema_name}';
    EXCEPTION WHEN others THEN
      RAISE WARNING 'GRANT failed for %: %', '{schema_name}', SQLERRM;
    END $$;
    """
    await ddl_db.execute(text(grant_sql))

    # 5. F16-FU2: meta_page_routing 同期トリガをセットアップ（DDL → admin_db）
    # ★壁0修正: DDL を step4(DML)より前に集約する。admin_db を commit する前に
    # db セッションから seed_* で tenant_X.* を参照すると 42P01 になるため、
    # 全 DDL をここで終わらせてから commit する。
    # 既存テナントへの適用は scripts/migrate_meta_page_routing.py が担当する。
    # 新規テナントは public.meta_page_routing 表 (migration 043) が既に存在する前提。
    trigger_sql = _META_PAGE_ROUTING_TRIGGER_SQL.format(
        schema=schema_name,
        schema_raw=schema_name,
    )
    await _execute_statements_preserving_do_blocks(ddl_db, trigger_sql)

    # ★壁0修正: 全 DDL をここで確定する。
    # admin_db が db と別オブジェクト（SA-18 Phase2 で注入される別 AsyncSession）の場合のみ
    # commit して、db セッションから tenant_X.* が可視化されるようにする。
    # admin_db が None（= db にフォールバック）または db と同一オブジェクト
    # （テスト用 bootstrap_tenant_schema が conn=db=admin_db で渡すケース）の場合は
    # 同一接続内なので commit 不要（context manager に任せる）。
    if admin_db is not None and ddl_db is not db:
        await ddl_db.commit()

    # DDL commit 後に DML が失敗した場合、DDL は不可逆なためスキーマが孤立する。
    # 以下の try/except で例外時に DROP SCHEMA CASCADE して孤立ゼロを維持する。
    try:
        # ★壁2修正: seed_* が salesanchor_app で tenant_X.* に INSERT できるよう
        # RLS 用セッション変数を設定する。SET文はバインド変数を受け付けないため
        # set_config() を使用（第3引数 true = トランザクション内のみ有効）。
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(safe_id)},
        )

        # 4. システムロール（オーナー/メンバー）をシード（DML → db）
        await seed_system_roles(db, safe_id, schema_name)

        # 6. Sprint 9 / F9 v1.2: public.tenant_settings に Phase='B' で初期行を seed（DML → db）。
        #    migration 070 未適用環境では tenant_settings テーブルが存在しないので
        #    best-effort で実行する。phase_gate.get_phase は 'A' fallback してくれる。
        #
        #    SAVEPOINT ガード: 単純な except Exception: pass はトランザクションを ABORTED 状態に
        #    しても Python 側に伝播させない（PG: "current transaction is aborted"）ため、
        #    外側トランザクションの COMMIT が実質 ROLLBACK になりスキーマが消える。
        #    begin_nested() で SAVEPOINT を切り、失敗時はそこだけロールバックして
        #    外側トランザクションを生かしたまま警告ログを出す。
        try:
            async with db.begin_nested():
                await db.execute(
                    text(
                        "INSERT INTO public.tenant_settings "
                        "(tenant_id, spreadsheet_phase, "
                        " inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, "
                        " quote_validity_days, default_currency, document_language, "
                        " duty_incoterms, issue_mode) "
                        "VALUES (:tid, 'B', "
                        " 'none', 0, 0, "
                        " 1, 'JPY', 'en', "
                        " 'DAP', 'pdf') "
                        "ON CONFLICT (tenant_id) DO NOTHING"
                    ),
                    {"tid": safe_id},
                )
        except Exception as exc:
            # migration 070 未適用環境（テスト・開発）では tenant_settings が存在しないため skip。
            # SAVEPOINT がロールバックされるだけで外側トランザクションは生き残る。
            logger.warning(
                "tenant_settings seed skipped for tenant %d (migration 070 not applied?): %s",
                safe_id,
                exc,
            )

    except Exception:
        # DML 失敗: DDL は既に commit 済みのためスキーマが孤立する前に DROP する。
        # admin_db が None または db と同一オブジェクトの場合は db.rollback() で巻き戻るので不要。
        if admin_db is not None and ddl_db is not db:
            try:
                await ddl_db.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                await ddl_db.commit()
                logger.warning("Dropped orphan schema %s after DML failure", schema_name)
            except Exception as drop_exc:
                logger.error(
                    "Failed to drop orphan schema %s: %s",
                    schema_name,
                    drop_exc,
                )
        raise

    # commitは呼び出し元で行う（監査ログ等と一括でcommitするため）
    return schema_name


def get_tenant_tables_sql(schema_name: str, tenant_id: int) -> str:
    """テナントテーブル作成SQL（フォーマット済み）を返す公開 API（ADR-034）。"""
    return _TENANT_TABLES_SQL.format(
        schema=schema_name, schema_raw=schema_name, tenant_id=tenant_id
    )


def get_rls_enable_sql(schema_name: str) -> str:
    """RLS 有効化SQL（フォーマット済み）を返す公開 API（ADR-034）。"""
    return _RLS_ENABLE_SQL.format(schema=schema_name)


def get_rls_policy_sql(schema_name: str) -> str:
    """テナント分離 RLS ポリシーSQL（フォーマット済み）を返す公開 API（ADR-034）。"""
    return _RLS_POLICY_SQL.format(schema=schema_name, schema_raw=schema_name)


async def _execute_statements_preserving_do_blocks(db: AsyncSession, sql: str) -> None:
    """
    DO $$ ... END $$ ブロックを壊さずに複数SQL文を順次実行する。
    $$ 区切り内部のセミコロンは文の終わりとみなさない。
    """
    statements = _split_sql_preserving_do_blocks(sql)
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            await db.execute(text(stmt))


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    """
    DO $$ ... END $$ や CREATE FUNCTION ... AS $tag$ ... $tag$ 等の
    dollar-quoted ブロック内の ; を保持したまま SQL をステートメント単位に分割する。

    単純に ";" で split すると、ブロック内部の ; が文末と誤認されて SQL が壊れる。
    PostgreSQL の dollar quoting は `$$` だけでなく `$tag$ ... $tag$` の named tag
    形式もサポートする（例: `AS $sync_mpr$ ... $sync_mpr$`）。

    PR #256 Reviewer F1 修正:
      旧版は `$$` ペアしか認識せず、F16-FU2 で導入した `$sync_mpr$` を含む
      `_META_PAGE_ROUTING_TRIGGER_SQL` を分割すると関数本体内の `;` が文末扱いされ
      `unterminated dollar-quoted string` エラーになっていた。
      `scripts/migrate_meta_page_routing.py` の同名関数で既に named tag 対応版が
      動作実績ありのため、その実装をこちらに移植する。
    """
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""

    while i < len(sql):
        if sql[i] == "$":
            # `$tag$` 形式（tag は英数字 + アンダースコア、`$$` は tag 空）の境界検出
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]  # `$...$`
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                elif tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
                # ブロック内で別 tag に出会った場合（ネスト）は通常 SQL では稀。
                # そのまま文字として buffer に積む。

        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1

    if buf:
        statements.append("".join(buf))
    return statements


# setup_tenant.py 等の外部スクリプト向け公開エイリアス（ADR-034）。
# 内部実装は _split_sql_preserving_do_blocks に集約し、こちらは名前だけ公開する。
split_sql_preserving_do_blocks = _split_sql_preserving_do_blocks
