# ADR-109 Status SSOT化 — 実装前 Recon

**調査日**: 2026-06-12  
**対象 ADR**: ADR-109-leads-status-ssot-immutable-codes.md (Accepted / 2026-06-04)  
**実装コミット**: `0f1924cf` feat(adr-109): status SSOT化 (PR #1726, 2026-06-07)

---

## 結論サマリ

| 項目 | 状態 |
|------|------|
| LeadStatus enum（英語コード化） | ✅ 完了（PR #1726） |
| バックエンド SQL リテラル置換 | ✅ 完了（PR #1726） |
| フロントエンド旧値マップ撤去 | ✅ 完了（PR #1726） |
| i18n キー（leads.statusCode.*） | ✅ 完了（PR #1726） |
| ADR-120 statusPresentation.ts 整合 | ✅ 完了（PR #1726 以前に ADR-120 で実装済み） |
| **DB migration（既存行 日本語→英語コード変換）** | ❌ **未完了（deploy.yml 未登録）** |
| **DB DEFAULT '新規' → 'lead' の既存テナント ALTER** | ❌ **未完了（新テナント側のみ修正済み）** |

**Generator が実装すべき残作業**: DB migration の SQL ファイル作成 ＋ deploy.yml 登録のみ。

---

## Q1. ADR-109 Scope 表の全対象の現在状態

### ファイルパス変更（3件）

| ADR-109 記載パス | 現在の実際パス |
|-----------------|----------------|
| `backend/app/services/discord_gateway/dm_writer.py` | `backend/app/discord_gateway/dm_writer.py` |
| `frontend/src/pages/LeadsPage.tsx` | `frontend/src/pages/leads/LeadsPage.tsx` |
| `frontend/src/features/inbox/inbox.types.ts` | `frontend/src/pages/inbox/inbox.types.ts` |
| `frontend/src/features/inbox/useInboxState.ts` | `frontend/src/pages/inbox/useInboxState.ts` |

### 各 Scope アイテムの現在状態

#### backend/app/schemas/lead.py:25-33 — LeadStatus enum
```python
class LeadStatus(str, Enum):
    lead = "lead"                                # アサイン前の新規リード
    negotiating = "negotiating"                  # アサイン済み・商談進行中
    existing_customer = "existing_customer"       # 成約済み・会社情報登録済み
    follow_up_short = "follow_up_short"           # 3 ヶ月以内に再アプローチ予定
    follow_up_long = "follow_up_long"             # 3 ヶ月以上先に再アプローチ予定
    lost = "lost"                                # 失注
    out_of_scope = "out_of_scope"                # スパム / 無関係
```
→ **✅ 完了**。ADR-109 指定の不変コード 7 値で実装済み。

#### backend/app/routers/leads.py — 日本語リテラル
- ADR-109 記載の行番号 (257, 326-328, 515, 534) はすべて行番号ズレ済み。
- **現在**:
  - `backend/app/routers/leads.py:295`: `"status": _enum_to_str(data.status)` — Pydantic enum 経由（日本語リテラルなし） ✅
  - `backend/app/routers/leads.py:553`: `SET status = 'negotiating'` — 英語コード ✅
- **全文検索で日本語ステータスリテラルなし** ✅

#### backend/app/routers/analytics.py:254, 450 — 日本語リテラル
- `backend/app/routers/analytics.py:254`: `AND status NOT IN ('lost', 'out_of_scope', 'existing_customer')` — 英語コード ✅
- `backend/app/routers/analytics.py:450`: `COUNT(*) FILTER (WHERE status = 'out_of_scope') AS excluded` — 英語コード ✅

#### backend/app/routers/dashboard.py:109 — 日本語リテラル
- `backend/app/routers/dashboard.py:109`:
  ```sql
  COUNT(*) FILTER (WHERE status NOT IN (
    'negotiating', 'existing_customer', 'lost',
    'follow_up_short', 'follow_up_long', 'out_of_scope'
  )) AS open_count,
  ```
  → **✅ 完了**。英語コードに変換済み。

#### backend/app/discord_gateway/dm_writer.py (旧: services/discord_gateway) — 初期値
- `backend/app/discord_gateway/dm_writer.py:161`:
  ```python
  VALUES (:tenant_id, :name, :source, 'Inbound', 'lead', ...)
  ```
  → **✅ 完了**。`'lead'`（英語コード）を使用。ファイルパスが変わっているため注意。

#### backend/tests/conftest.py:314 — テスト DB DEFAULT
- `backend/tests/conftest.py:314`: `status VARCHAR(50) DEFAULT 'lead'` → **✅ 完了**

#### frontend/src/pages/leads/LeadsPage.tsx (旧: pages/LeadsPage.tsx) — 旧値マップ
- **旧 107-114 行の日本語マップ**: 完全に撤去済み
- **現在の状態** (`frontend/src/pages/leads/LeadsPage.tsx:104`):
  ```tsx
  // ADR-109: status codes with i18n labels
  const LEAD_STATUSES: LeadStatusCode[] = [...LEAD_STATUS_CODES];
  const translateLeadStatus = (status: string) =>
    t(`leads.statusCode.${status}`, { defaultValue: status });
  ```
  → **✅ 完了**。LEAD_STATUS_CODES は `frontend/src/constants/leadStatus.ts` で定義（ADR-109 Scope 外の新規 SSOT ファイル）。

- **LeadsPage.tsx:77**: `status: "lead"` （emptyForm の初期値）→ ✅
- **LeadsPage.tsx:367**: `translateLeadStatus(l.status)` でステータス表示 → ✅

#### frontend/src/pages/inbox/inbox.types.ts (旧: features/inbox) — STATUS_TABS, FOLLOWUP_EXCLUDED
- `frontend/src/pages/inbox/inbox.types.ts:20`: STATUS_TABS — 英語コード使用 ✅
  ```tsx
  export const STATUS_TABS = [
    { key: "lead",     statuses: ["lead"] },
    { key: "deal",     statuses: ["negotiating"] },
    { key: "existing", statuses: ["existing_customer"] },
    { key: "followup", statuses: ["follow_up_short", "follow_up_long"] },
    { key: "archive",  statuses: ["lost", "out_of_scope"] },
  ] as const;
  ```
- `frontend/src/pages/inbox/inbox.types.ts:37`: `FOLLOWUP_EXCLUDED = new Set(["lost", "out_of_scope"])` → ✅

#### frontend/src/pages/inbox/useInboxState.ts (旧: features/inbox)
- ADR-109 記載の行番号 (664, 719) はズレ済み。
- **現在の行** `frontend/src/pages/inbox/useInboxState.ts:690`: `await api.patch<void>('/leads/${selectedLeadId}', { status: "out_of_scope" })` → ✅

#### i18n（frontend/src/locales/ja.json + en.json）
- `ja.json:470-478`:
  ```json
  "statusCode": {
    "lead": "リード", "negotiating": "商談中", "existing_customer": "既存顧客",
    "follow_up_short": "追客（短期）", "follow_up_long": "追客（長期）",
    "lost": "失注", "out_of_scope": "対象外"
  }
  ```
- `en.json:470-478`: 同一キー ✅
- **注意**: `ja.json:466-468` に旧キー (`leads.status_follow_up_short` 等) が残存。ADR-109 受入条件外だが cleanup 候補。

---

## Q2. ADR-120 statusPresentation.ts との整合

### 現在の lead ドメインキー

`frontend/src/utils/statusPresentation.ts:61-68`:
```typescript
lead: {
  lead:              { bucket: "neutral", badgeVariant: "neutral",     labelKey: "leads.statusCode.lead" },
  negotiating:       { bucket: "info",    badgeVariant: "negotiating", labelKey: "leads.statusCode.negotiating" },
  existing_customer: { bucket: "success", badgeVariant: "won",         labelKey: "leads.statusCode.existing_customer" },
  follow_up_short:   { bucket: "warning", badgeVariant: "pending",     labelKey: "leads.statusCode.follow_up_short" },
  follow_up_long:    { bucket: "warning", badgeVariant: "pending",     labelKey: "leads.statusCode.follow_up_long" },
  lost:              { bucket: "danger",  badgeVariant: "lost",        labelKey: "leads.statusCode.lost" },
  out_of_scope:      { bucket: "danger",  badgeVariant: "lost",        labelKey: "leads.statusCode.out_of_scope" },
},
```

→ **ADR-109 の 7 コード完全一致、二重定義なし。**

### 接続点（2 ADR の結節点）

```
DB: leads.status = 'negotiating'
  ↓
API: LeadResponse.status: str = 'negotiating'
  ↓ (ADR-120)
statusPresentation.ts:getStatusPresentation("lead", "negotiating")
  → { bucket: "info", badgeVariant: "negotiating", labelKey: "leads.statusCode.negotiating" }
  ↓ (ADR-109)
t("leads.statusCode.negotiating") → "商談中"  (ja.json:472)
```

**役割分担**:
- statusPresentation.ts → badge 色・バリアント（見た目）
- i18n `leads.statusCode.*` → 表示テキスト（ラベル）

### 実装パターン（各コンポーネント）

| コンポーネント | パターン | defaultValue 有無 |
|--------------|---------|-----------------|
| `frontend/src/pages/leads/LeadsPage.tsx:367` | `translateLeadStatus(l.status)` → `t('leads.statusCode.${status}', { defaultValue: status })` | ✅ あり |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:153` | `t(stagePresentation.labelKey ?? leadDetail.status)` | ✅ あり（statusCode キーが見つからない場合は status 直接） |
| `frontend/src/components/MergeLeadModal.tsx:221` | `t('leads.statusCode.${c.status}', { defaultValue: c.status })` | ✅ あり |
| `frontend/src/pages/inbox/InboxConversationList.tsx:228` | `` t(`leads.statusCode.${conv.lead_status}`) `` | **⚠️ defaultValue なし** |

---

## Q3. ダッシュボードに段階が英語のまま表示されるバグ

### ADR-109 記載の既存バグ（解消済み）

元の問題: `LeadsPage.tsx` 旧 107-114 行の JavaScript 値マップが旧ステータス値（コンタクト中・提案中・案件化・保留）にしか対応せず、当時の現行値（商談中・既存顧客・追客（短期）・追客（長期）・対象外）が日本語 raw 値で表示されていた。  
→ **PR #1726 で旧値マップを撤去・解消済み。**

### dashboard.py:109 との関係

`backend/app/routers/dashboard.py:109` は COUNT 集計クエリであり、ステータスラベルを画面に表示しない。「段階が英語のまま表示」の直接原因ではない。  
ただし DB が日本語値のままの状態で英語コードでフィルタすると、全件が `open_count` に誤カウントされる副作用がある。

### 現在の懸念箇所（DB 未移行時）

`frontend/src/pages/inbox/InboxConversationList.tsx:228`:
```tsx
<span className="conv-status-badge">{t(`leads.statusCode.${conv.lead_status}`)}</span>
```
- `defaultValue` が指定されていない。
- DB が日本語値のまま（例: `lead_status = '商談中'`）の場合、i18n キー `leads.statusCode.商談中` は存在しないため、react-i18next はキー文字列 `leads.statusCode.商談中` をそのまま表示する（壊れた表示）。
- 英語コードの場合（例: `lead_status = 'negotiating'`）は正常に '商談中' と表示される。

→ **根本原因は DB migration 未適用。** InboxConversationList のフォールバック不足も副次的問題。

---

## Q4. status 日本語リテラルの全文検索（ADR-109 Scope 外の漏れ確認）

### バックエンド（.py ファイル全体）

```
grep -r "'新規'\|'商談中'\|'既存顧客'\|'追客（短期）'\|'追客（長期）'\|'失注'\|'対象外'" backend/
```
→ **0 件**（コメント・ドキュメント文字列のみ）。ADR-109 Scope 外の漏れなし。 ✅

### フロントエンド（production コード）

```
grep -r "既存顧客\|商談中\|追客\|失注\|対象外" frontend/src/
```
主な結果:
- `frontend/src/pages/design-preview/sections/TabsSection.tsx:20`: `label: "既存顧客"` — **Storybook / デザインプレビュー専用ファイル。本番コードではない。**
- `frontend/src/components/Tabs.stories.tsx:31`: 同様
- `frontend/src/utils/statusPresentation.ts:50,53`: コメント内のみ

→ **production コードに漏れなし。** ✅

---

## Q5. Migration の現状

### DB DEFAULT の現状

| 場所 | 値 | 状態 |
|------|----|------|
| `migrations/003_add_phase1_tenant_tables.sql:85` | `DEFAULT '新規'` | ❌ 旧値（既存テナントの初期化 SQL） |
| `backend/app/services/tenant.py:312` | `DEFAULT 'lead'` | ✅ 新テナント作成時は英語コード |
| `scripts/qa/seed-tenant.sql:139-143` | `'lead'`, `'negotiating'` 等 | ✅ QA シードは英語コード |

### DB migration の状況

**`scripts/migrate_adr109_status_codes.py`** — PR #1726 で追加済み。  
変換マッピング:
```
'新規'        → 'lead'
'商談中'      → 'negotiating'
'既存顧客'    → 'existing_customer'
'追客（短期）' → 'follow_up_short'
'追客（長期）' → 'follow_up_long'
'失注'        → 'lost'
'対象外'      → 'out_of_scope'
'new'         → 'lead'          （旧英語非標準値）
'in_progress' → 'negotiating'   （旧英語非標準値）
'converted'   → 'existing_customer' （旧英語非標準値）
```

**問題**: `.github/workflows/deploy.yml` に登録なし → **本番 DB に未適用の可能性**。  
ADR-109 受入条件「migration が deploy.yml 経由で自動適用される（手動VPS作業なし）」: **未達**。

### 値分布確認 SQL（Generator が本番確認に使うこと）

```sql
-- docker compose exec -T backend psql "$DATABASE_URL" で実行
-- 本番テナント: tenant_004
SELECT status, COUNT(*) AS cnt
FROM tenant_004.leads
GROUP BY status
ORDER BY cnt DESC;
-- 期待値: 'lead' / 'negotiating' / 'existing_customer' / 'follow_up_short' / 'follow_up_long' / 'lost' / 'out_of_scope' のみ
-- 想定外の値（日本語や旧英語コード）が0件であれば migration 適用済み

-- 全テナント一括確認（shell: jq 不要版）
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT table_schema AS s FROM information_schema.tables
    WHERE table_name = 'leads' AND table_schema LIKE 'tenant_%'
  LOOP
    RAISE NOTICE 'schema=%', r.s;
  END LOOP;
END $$;
-- 各スキーマ個別に SELECT status, COUNT(*) FROM {schema}.leads GROUP BY status; を実行
```

### migration 番号体系（CLAUDE.md 準拠）

101 番以降は `YYYYMMDD_HHMMSS_description.sql` 形式。  
次に作成する migration ファイル例:
```
migrations/20260612_XXXXXX_leads_status_ja_to_en.sql
```
deploy.yml への psql ステップ追記も必須（migration-guard.yml が未登録 PR をブロック）。

---

## Q6. status 値に依存するテスト（migration で壊れる候補）

全テストは PR #1726 で英語コードに更新済み。追加の migration 実行で壊れる候補はない。

| テスト | 行 | status 値 | 状態 |
|--------|-----|-----------|------|
| `backend/tests/conftest.py` | 314 | `DEFAULT 'lead'` | ✅ |
| `backend/tests/test_webhook_instagram.py` | 61 | `DEFAULT 'lead'` | ✅ |
| `backend/tests/test_webhook_instagram.py` | 822 | `'lead'` リテラル | ✅ |
| `backend/tests/test_messages.py` | 238 | `'lead'` リテラル | ✅ |
| `backend/tests/test_discord_inbox.py` | 233 | `'lead'` リテラル | ✅ |
| `backend/tests/test_deals.py` | 156 | `body["status"] == "negotiating"` | ✅ |

---

## Generator への引継ぎ事項

### 残作業（これだけ）

1. **SQL migration ファイル作成**  
   `migrations/20260612_XXXXXX_leads_status_ja_to_en.sql`  
   内容: 全テナントの leads.status を日本語・旧英語コード → 英語コードに 1対1 変換 ＋ DEFAULT 'lead' に ALTER。  
   `scripts/migrate_adr109_status_codes.py` のマッピングをそのまま SQL 化すればよい。  
   `backend/CLAUDE.md` の additive-only 原則確認（UPDATE + ALTER DEFAULT は OK）。

2. **deploy.yml 登録**  
   `.github/workflows/deploy.yml` の「新しいマイグレーションはここに追加」コメント前に psql 実行ステップを追加。  
   未登録だと migration-guard.yml が PR をブロックする。

3. **migration-test.yml 最小定義確認**  
   `status` カラムが操作対象なので `.github/workflows/migration-test.yml` に `leads.status` の setup が存在することを確認すること（存在すれば追加不要）。

### ADR-109 受入条件の残確認項目

- [ ] 全テナントの `leads.status` に日本語値（新規・商談中等）が残っていないこと
- [ ] DB DEFAULT が `'lead'` になっていること
- [ ] migration が deploy.yml 経由で適用されること（手動 VPS 作業なし）
