# recon: 受信箱の「新規」バッジ（担当になったが、まだ開いていない）

**日付**: 2026-10-15
**ベース**: `origin/main` = `62f341957`（PR-A 作業先 worktree で再確認）
**原則**: 全主張は一次情報（コード実体）で裏取り。サブエージェント報告は一次情報として扱わない。
本ファイルの引用はすべて作業先 worktree の実ファイルで再確認済み（審査 D5 対応）。
`backend/app/routers/leads.py`・`backend/app/routers/meta_inbox.py`・`frontend/` 配下の各ファイルは
PR-B（`release/inbox-new-assignment-badge`）側で行番号が動くため、識別子名で引用する
（本ファイルの対象は PR-A＝列だけなので、これらのファイルは触らない）。

> サブエージェントの報告には**行番号のずれ**と**バッジ表示条件の誤り**があったため、
> 決定的な箇所はすべて自分で読み直した（下記はその結果）。

---

## 0. 着手前 ADR 検索

| 検索 | 結果 |
|------|------|
| 受信箱・未読・バッジ | ADR-143（相手言語）・spec §5-3/§5-6 の記述あり。**バッジに関する ADR は無い** |
| 担当者・ID 体系 | **ADR-1008**（人の列の参照先を `public.users(id)` に統一） |
| UI 金型 | **ADR-144** |
| i18n | **ADR-027** |
| テナント文脈 | **ADR-072** |
| 危険パスの GO 手順 | **ADR-135 / ADR-136**（`migrations/` を触るため該当） |
| PR 区分 | **ADR-1015**（新機能・「.sql」を含む → **A 区分**） |
| 書き込みルート台帳 | **ADR-1016**（新しい書き込み API を足す場合のみ関係。本件は**足さない**） |

---

## 1. PO 要望と決定

- 要望（2026-10-15）: 「担当の受信箱に新規バッジをつける」
- 意味の確定（PO 回答）: **案 B「担当になったが、まだ開いていない」。開くと消える。**
- 便の分離: 本件は便2。便1（通知の振り分け＋アサイン通知）は PR #4318 でマージ済み。

---

## 2. leads テーブルに「担当になった時刻」は存在しない（確定）

### 2-1. 本体の列（21列）
`migrations/003_add_phase1_tenant_tables.sql:75-98`
```
id, tenant_id, lead_code, customer_name, company_name, email, phone, source,
type, status, temperature, estimated_scale, customer_type, response_speed,
monthly_forecast, prospect_rank, assigned_to, converted_deal_id, notes,
created_at, updated_at
```

### 2-2. 後から ALTER で追加された列（全数確認・25列）
`git grep -n "ALTER TABLE.*\.leads.*ADD COLUMN" origin/main -- migrations/` の全件より:
```
ai_collection_state, amount, challenge, competitor_check, country, cs_memo,
currency, discord_guild_channel_id, discord_role_sync_at, discord_role_sync_status,
english_name(→nickname に改名), escalation_flag, expected_close_date,
first_inquiry_at, first_response_at, first_response_seconds, meeting_impression,
meeting_memo, monthly_forecast_source, monthly_frequency, next_action,
next_action_date, per_order_amount, sales_form, target_titles
```
さらに `instagram_link` / `whatsapp_link` / `messenger_link` / `discord_id` /
`discord_user_id` / `discord_dm_channel_id` / `initiative` / `channel_type` も追加されている。

### 2-3. 新テナント作成時の定義
`backend/app/services/tenant.py:355-407` にも `leads` の CREATE TABLE があり、
**マイグレーションとは別に同じ列を持たせる必要がある**（2 箇所の同期が必須）。

### 2-4. 紛らわしい既存列（取り違え注意）
`assigned_at` は存在するが **`user_roles` の列**（ユーザーへの役割割当時刻）であり leads とは無関係。
`migrations/003_add_phase1_tenant_tables.sql:63-70`
```sql
CREATE TABLE IF NOT EXISTS {schema}.user_roles (
    ...
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by INTEGER,
    UNIQUE(user_id, role_id)
);
```

**結論: 列の追加は避けられない。既存列で代替する方法は無い。**

---

## 3. 「開いた」合図は既に存在する（新しい API は不要）

### 3-1. 会話を開いたときにフロントが呼ぶもの
`frontend/src/pages/inbox/useInboxState.ts` の、`selectedLeadId` が変わったときの `useEffect`
（PR-B で行番号が動くため識別子で引用。本ファイルは PR-A では触らない）
```ts
  useEffect(() => {
    if (selectedLeadId === null) {
      setMessagesData(null);
      setLeadDetail(null);
      return;
    }
    loadMessages(selectedLeadId);
    markRead(selectedLeadId);          // ← これが「開いた」合図になる
    loadLeadDetail(selectedLeadId);
```
依存配列は同 `useEffect` の `[selectedLeadId, loadMessages, markRead, loadLeadDetail]`。

### 3-2. markRead の中身
`frontend/src/lib/messages.ts` の `markRead` 関数
（PR-B で行番号が動くため識別子で引用）
```ts
 * POST /api/v1/leads/{lead_id}/messages/mark-read
  return api.post<MarkReadResponse>(`/leads/${leadId}/messages/mark-read`, {});
```
→ **既に空オブジェクトの body を送っている**ため、任意フィールドの追加は後方互換。

### 3-3. バックエンド実体
`backend/app/routers/leads.py` の `mark_lead_messages_read`
（PR-B で行番号が動くため識別子で引用）
```python
@router.post(
    "/leads/{lead_id}/messages/mark-read",
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def mark_lead_messages_read(lead_id, db, tenant_id, current_user):
    leads_t = tenant_table_ref(db, tenant_id, "leads")
    meta_messages_t = tenant_table_ref(db, tenant_id, "meta_messages")
    lead_q = await db.execute(
        text(f"SELECT id FROM {leads_t} WHERE id = :id AND tenant_id = :tenant_id"), ...)
    if lead_q.first() is None:
        raise HTTPException(404, detail="リードが見つかりません")

    # 既読者はログイン中の users.id（ADR-1008: seen_by_staff_id には users.id を入れる）
    staff_id: int = current_user.id

    upd = await db.execute(text(f"""
        UPDATE {meta_messages_t}
        SET seen_at = NOW(), seen_by_staff_id = :staff_id
        WHERE lead_id = :lead_id AND tenant_id = :tenant_id
          AND direction = 'inbound' AND seen_at IS NULL
    """), {...})
    marked = int(upd.rowcount or 0)
    if marked > 0:
        await record_audit_log(..., action="mark_messages_read", ...)
```
確定事項:
- **`leads` の存在確認を既に行っている**（同じトランザクションで leads を触れる）
- **`current_user.id` は `users.id`**（`mark_lead_messages_read` 内の
  「既読者はログイン中の users.id（ADR-1008: seen_by_staff_id には users.id を入れる）」
  というコメントが ADR-1008 を明示。PR-B で行番号が動くため識別子で引用）。
  `leads.assigned_to` も users.id（`backend/app/routers/analytics.py:104-114` の
  `LEFT JOIN public.users u ON u.id = l.assigned_to` で確認済み）→ **同じ体系で比較可能**
- 既存の未読（`meta_messages.seen_at`）は「**お客さまのメッセージを読んだか**」であり、
  「担当になった通知を開いたか」とは**別の概念**

### 3-4. mark-read は一括操作からも呼ばれる（重要）
`frontend/src/pages/inbox/useInboxState.ts` の `handleMarkAllRead`
（PR-B で行番号が動くため識別子で引用）
```ts
    await Promise.all(unreadConvs.map((c) => markRead(c.lead_id)));   // 「すべて既読」
```
同ファイルの `handleBulkMarkRead`
```ts
    await Promise.all([...selectedLeadIds].map((id) => markRead(id)));  // 複数選択の既読化
```
→ **これらは「開いた」ではない**。区別しないとバッジが開かずに消える。

---

## 4. 会話一覧 API は担当者を返していない

`backend/app/routers/meta_inbox.py` の `list_conversations`
（PR-B で行番号が動くため識別子で引用）
```python
@router.get("/conversations", dependencies=[Depends(require_permission("messaging.view"))])
async def list_conversations(
    platform: str = Query("all", pattern="^(all|messenger|instagram|discord)$"),
    unread_only: bool = Query(False),
    page_id: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),     # ← 既に居る
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
```
→ **`current_user` は既に依存に入っている**ため、サーバー側で「自分が担当か」を判定できる。

SELECT 句（`LEFT JOIN leads l` を含む箇所。PR-B で行番号が動くため識別子で引用）
```sql
        SELECT
            l.id                    AS lead_id,
            l.lead_code             AS lead_code,
            l.customer_name         AS customer_name,
            l.status                AS lead_status,
            lat.platform            AS platform,
            lat.page_id             AS page_id,
            lat.sender_id           AS sender_id,
            lat.message_text        AS last_message_text,
            lat.direction           AS last_message_direction,
            lat.created_at          AS last_message_at,
            COALESCE(agg.unread_count, 0) AS unread_count,
            agg.last_inbound_at     AS last_inbound_at
        FROM latest lat
        LEFT JOIN leads l ON l.id = lat.lead_id AND l.tenant_id = :tenant_id
        LEFT JOIN agg ON agg.lead_id = lat.lead_id
        WHERE lat.rn = 1
        ORDER BY lat.created_at DESC, lat.lead_id DESC
        LIMIT :limit OFFSET :offset
```
→ **`assigned_to` は SELECT にも WHERE にも無い**。

応答生成（`conversations.append({...})` の箇所。PR-B で行番号が動くため識別子で引用）
```python
        conversations.append({
            "lead_id": row["lead_id"],
            "lead_code": row["lead_code"],
            "customer_name": row["customer_name"],
            "lead_status": row.get("lead_status"),
            "platform": row["platform"],
            "page_id": row.get("page_id"),
            "last_message_text": row["last_message_text"],
            "last_message_at": _format_dt(row["last_message_at"]),
            "last_message_direction": row["last_message_direction"],
            "unread_count": unread_count,
            "messaging_window_expires_at": _compute_window_expires(last_inbound_at),
            "profile_picture_url": profile_picture_url,
        })
```

フロントの型 `frontend/src/lib/messages.ts` の `Conversation` interface も同じ 12 項目
（`profile_picture_url` は任意。PR-B で行番号が動くため識別子で引用）。

---

## 5. 担当の変更箇所

`backend/app/routers/leads.py` の `update_lead`（`PATCH /leads/{lead_id}`・権限 `leads.update`。
PR-B で行番号が動くため識別子で引用）
- `old_row`（`old_result.mappings().first()`）を先に取得 → **変更前の `assigned_to` が取れる**
- `_UPDATABLE_COLUMNS` に `assigned_to` を含む
- 便1 で追加したアサイン通知が `asyncio.create_task(notify_lead_assigned(...))` で実行
  （担当が変わったときのみ）
- 監査記録 `record_audit_log(..., old_data=dict(old_row), new_data=audit_new_data, ...)` を残す
  → **担当変更の履歴は audit_logs に既にある**ので、時刻列を別に持つ必要はない

---

## 6. バッジの金型（新設不要）

### 6-1. `Badge` 金型は既に存在する
`frontend/src/components/Badge.tsx:16-34`
```ts
export type BadgeVariant    = 'neutral' | 'info' | 'success' | 'warning' | 'danger';
export type BadgeAppearance = 'soft' | 'solid';
export type BadgeSize       = 'sm' | 'md';

export interface BadgeProps {
  variant?:    BadgeVariant;
  appearance?: BadgeAppearance;
  size?:       BadgeSize;
  dot?:        boolean;
  icon?:       ReactNode;
  children:    ReactNode;
  className?:  string;
}
```
docstring（`:1-14`）に明記:
```
ラベルは children で渡す（業務ステータス名はこのコンポーネントに埋め込まない）。
ステータス値 → variant のマッピングは呼び出し側で定義すること。
```
→ **金型の新設は不要。この金型をそのまま使う。**

### 6-2. 既存の未読バッジは金型を使っていない（本 PR では置き換えない）
`frontend/src/pages/inbox/InboxConversationRows.tsx` の
`conv.unread_count > 0 && (<span className="badge conv-unread-badge">...)` の箇所
（PR-B で行番号が動くため識別子で引用）

**訂正（実装時に判明）**: 本行は当初 InboxConversationList.tsx の239-241行目として記載していたが、
別PR（会話一覧の行描画を共通部品に分離するリファクタ）で既に上記ファイルへ移動済みだった。
recon時点のサブエージェント報告を裏取りせず転記したことが原因。
```tsx
{conv.unread_count > 0 && (
  <span className="badge conv-unread-badge">{conv.unread_count}</span>
)}
```
ADR-144:66-69 により既存実装の金型移行は別 PR。**新しいバッジだけ金型で書く。**

---

## 7. マイグレーションの作法（本番 DB を触るため厳守）

### 7-1. 命名規則
「YYYYMMDD_HHMMSS_description.sql」（連番 `NNN_` は廃止）。
`.github/workflows/migration-guard.yml` が形式を検査する。

### 7-2. テナントスキーマへの列追加の手本（全文）
`migrations/20260718_100000_leads_add_deal_columns.sql`
```sql
-- deals廃止 段階①: leads に商談列を追加（全テナント・冪等）
-- 設計: docs/specs/db-ssot/deal-removal/design.md §4.5
-- 既存テナント/新テナントの両方で同じ列を持つため、IF NOT EXISTS を付与する。
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS amount NUMERIC(15,2)', s
        );
        ...
        RAISE NOTICE 'leads columns added or already present on %', s;
    END LOOP;
END $$;
```

### 7-3. 既存行の埋め直し（backfill）の先例
`migrations/032_add_company_contact_to_downstream.sql:124` に
`UPDATE %I.orders o ...` の形で既存行を埋める先例がある
（＝構造変更と同じマイグレーション内での UPDATE は本リポジトリの確立した作法）。

### 7-4. 実行登録
`scripts/run_all_migrations.sh` に追記する。recon 時点（2026-10-15）の最終行付近は次の形だった
（`:968-969`。**訂正**: PR-A 実装時点では `run_all_migrations.sh` の登録はタイムスタンプ順に
並んでいたため、末尾ではなくタイムスタンプ順の位置に挿入した。design.md §3-1「実行登録」参照）:
```bash
# 試運転（shadow）の表2件の削除（画面・API・書き込み経路は #4218 で削除済み・PO GO 待ち・冪等・不可逆）
run_sql migrations/20261013_180000_drop_extraction_shadow_tables.sql
```
`.github/workflows/deploy.yml` からの直接実行は廃止済み（`scripts/run_all_migrations.sh` に一元化）。

---

## 8. 未確認（宿題）

| # | 内容 | 確認方法 |
|---|---|---|
| U1 | 本番 `leads` のうち `assigned_to IS NOT NULL` の件数（backfill の影響範囲） | マージ後に読み取り専用で数える。設計は件数に依存しない形にする |
| U2 | 「開くと消える」の実機確認 | 本番反映後に実機で |
