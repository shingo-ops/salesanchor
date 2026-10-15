# recon: 通知の送信先振り分け ＋ 商談アサインの Discord 通知

**日付**: 2026-10-15
**ベース**: `origin/main` = `e1cdbc468`（PR #4310 マージ時点）
**原則**: 全主張は一次情報（コード実体／公式ドキュメント）で裏取り。サブエージェント報告は一次情報として扱わず、本ファイルの引用はすべてコーディネータ（Opus）が `git show origin/main:<path>` で再確認済み。

> **注意（事故記録）**: 調査初期、ローカル作業ツリー `/root/projects/salesanchor` が `origin/main` から **4309 コミット遅れ**（HEAD = PR #3427）だったため、古い行番号を一度 PO に提示した。以降は必ず `git show origin/main:<path>` で読む運用に切替。

---

## 0. 着手前 ADR 検索（STANDARD-WORKFLOW 必須）

| 検索 | 結果 |
|------|------|
| `git grep -il "notification_channel\|discord" -- docs/adr/` | ADR-009（Discord Gateway）他。通知チャンネル振り分けに関する ADR は**存在しない** |
| `docs/adr/FEATURE-INDEX.md` | 「通知の送信先振り分け」に該当行なし |
| UI 金型 | **ADR-144**（UI ガバナンス）が正典 |
| 区分値 SSOT | **ADR-109**（LeadStatus 不変コード）／**ADR-120**（ステータス表示 SSoT） |
| デザイントークン | **ADR-067** |
| i18n | **ADR-027** |
| テナント文脈 | **ADR-072 Phase 1 / Phase 2.5** |

→ 本件に直接該当する ADR は無く、既存 ADR（144 / 109 / 027 / 067 / 072）の制約下で実装する。新規 ADR 起案は不要と判断。

---

## 1. Discord は 3 系統が併存する（混同禁止）

| 系統 | 用途 | 設定の置き場所 | 根拠 |
|------|------|----------------|------|
| **A. Discord Gateway** | 顧客とのやり取り（Bot 常時接続・受信） | 環境変数 `DISCORD_BOT_TOKEN_<TENANT_ID>` | `docs/adr/ADR-009-discord-gateway.md:1-30` |
| **B. notification_channels** | 通知の送信（Webhook 片方向） | テナントスキーマの `notification_channels` 表 | `backend/app/routers/notifications.py:108-135` |
| **C. admin 通知** | LLM 予算超過等の運用通知 | 環境変数 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` | `backend/app/services/discord_notifier.py:10-12,41` |

→ PO 要望「既存の Discord は顧客とのやり取り用なので自社用サーバーも連携したい」は **系統 B の送信先を増やす**話であり、系統 A には一切触れない。

---

## 2. notification_channels 表（送信先）

`migrations/009_add_phase4_tenant_tables.sql:8-18`
```sql
CREATE TABLE IF NOT EXISTS {schema}.notification_channels (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    channel_type VARCHAR(20) NOT NULL DEFAULT 'discord',
    channel_name VARCHAR(100) NOT NULL,
    webhook_url VARCHAR(500) NOT NULL,
    event_types TEXT DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

- **UNIQUE 制約は存在しない** → 1 テナントで送信先を複数登録可能（表の作りとして既に可能）
- `event_types` は **TEXT に JSON 配列文字列**を格納（`backend/app/routers/notifications.py:83` が `json.dumps`）
- RLS 有効化のみが後続変更（`migrations/009_...:72`）。ALTER による列追加は無い
- `migrations/009_...:24` の `notification_logs.channel_id` が本表を FK 参照

**結論: 新しい表・新しい列は不要。振り分け設定の SSOT はこの 1 表。**

---

## 3. 送信処理（既存）

`backend/app/routers/notifications.py:108-135`
```python
async def send_discord_notification(db, tenant_id, event_type, title, message) -> None:
    result = await db.execute(
        text("SELECT id, webhook_url FROM notification_channels "
             "WHERE is_active = TRUE AND event_types LIKE :pattern"),   # :112
        {"pattern": f"%{event_type}%"},
    )
    channels = result.mappings().all()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for ch in channels:                                              # :117
            payload = {"embeds": [{"title": title,
                                   "description": message,
                                   "color": 3447003}]}                   # :119
            resp = await client.post(ch["webhook_url"], json=payload)
            ... INSERT INTO notification_logs ...                        # :122-129
    await db.commit()
    await reset_tenant_context(db, tenant_id)
```

確定事項:
- **該当した全送信先に送る**（`:117` のループ。1 件で打ち切らない）
- 絞り込みは `event_types LIKE '%<種類>%'`（`:112`）＝**部分一致**。種類名を他の種類名の部分文字列にしてはいけない
- テーブル参照が**スキーマ修飾なし**（`:112`）→ **search_path に依存**。別セッションから呼ぶ場合はテナント文脈の設定が必須（§7）
- **payload は `embeds` のみ。`content` が無い**（`:119`）→ §8 の致命的制約に直結

---

## 4. API（既存）: 変更エンドポイントが無い

`backend/app/routers/notifications.py`

| メソッド | パス | 権限 | 行 |
|---|---|---|---|
| GET | `/notification-channels` | `notifications.view` | `:62-68` |
| POST | `/notification-channels` | `notifications.manage` | `:71-91` |
| DELETE | `/notification-channels/{channel_id}` | `notifications.manage` | `:94-105` |

- **PUT / PATCH は存在しない** → 登録後に `event_types` を変更する手段が無い
- 変更用の部品は**定義済みだが未使用（デッドコード）**
  - `class ChannelUpdate(BaseModel)` … `:41-45`（`channel_name` / `webhook_url` / `event_types` / `is_active` すべて Optional）
  - `_UPDATABLE = {"channel_name", "webhook_url", "event_types", "is_active"}` … `:59`
- 作成時の既定値 … `:38`
  ```python
  event_types: list[str] = Field(default_factory=lambda: ["customer_created", "deal_won", "invoice_issued"])
  ```

---

## 5. 画面（既存）: 通知の種類を送っていない

`frontend/src/pages/notifications/NotificationsPage.tsx`

- `:10-11` … **既に金型を使用**（`Button` / `TextFieldControl` を import）→ ADR-144 の金型化作業は**不要**
- `:35` … POST するのは `channel_name` と `webhook_url` **のみ**
  ```ts
  await api.post("/notification-channels", { channel_name: form.channel_name, webhook_url: form.webhook_url });
  ```
- 一覧は `DataTable` 表示（`channel_name` / `webhook_url` / `is_active` / 削除ボタン）。**`event_types` は表示も編集もしていない**

**結論: 画面が種類を送らない ＋ 変更 API が無い ＝ UI 由来の送信先は既定 3 種類に永久固定。**

---

## 6. 実際に飛んでいる通知の種類（全数）

`git grep -n "send_discord_notification" -- backend/app` の全件を確認:

| event_type | 送信元 | 行 |
|---|---|---|
| `meta_message_received` | Meta Messenger / Instagram DM 受信 | `backend/app/routers/webhook.py:938-947` |
| `tcg_distribution_error` | TCG 在庫配信エラー | `backend/app/services/tcg_distribution_svc.py:857-866` |

- 既定値の `customer_created` / `deal_won` / `invoice_issued` は**送信元が 1 つも存在しない**（＝鳴らない選択肢）
- **レポート通知は存在しない**。`staff_reports` 表はある（`migrations/009_...:34-48`）が、生成・送信処理は無い。Celery beat（`backend/app/celery_app.py:58-150`）にもレポート送信タスクの登録は無い
- 既定 3 種類と実装 2 種類が**噛み合っていない**ため、UI から登録した送信先には Meta 新着通知が届かない（本番の登録内容は未確認＝§11 の宿題）

---

## 7. テナント文脈とスキーマ修飾（ADR-072）

| 関数 | 役割 | 行 |
|---|---|---|
| `set_tenant_context(db, tenant_id)` | `search_path` ＋ `app.tenant_id` ＋ `app.is_operator` を一括設定 | `backend/app/auth/dependencies.py:309-332` |
| `reset_tenant_context(db, tenant_id)` | 返却前のクリア | `:371` |
| `tenant_table_ref(db, tenant_id, name)` | `tenant_{id:03d}.{name}` を返す | `:441-459` |

`:317-318`（docstring）
```
**この関数を経由せず生の `SET search_path` を書いてはいけない。**
CI grep チェック（.github/workflows/test.yml）が直接書きを検出してブロックする。
```

`:446-449`（docstring）
```
AsyncSession の commit 後に session-level の search_path が失われる可能性があるため、
raw text() を使う箇所では schema prefix を明示するのが安全
```

→ 背景タスクから `send_discord_notification` を呼ぶ場合、**新しいセッションで `set_tenant_context` を必ず呼ぶ**。生 `SET search_path` は CI がブロックする。

---

## 8. 【致命的】埋め込みカード内のメンションは通知されない

**公式一次情報**: `https://docs.discord.com/developers/resources/message`（2026-10-15 取得）

> mentions placed in embed titles or descriptions **do not trigger notifications**. Mentions only notify users when they appear in the message's `content` field or in component text.
> `allowed_mentions` … determines "whether users will receive notifications when you include mentions in the **message content**, or the content of components attached to that message."

現状の payload は `embeds` のみ（§3 `:119`）＝ **`<@ID>` を書いても担当者のスマホは鳴らない**。

→ `send_discord_notification` に **`content`（メンション）を渡せる口**を追加する必要がある。実機（自社サーバー）で実際に鳴ることを確認するまで完了としない。

---

## 9. 商談化の起点と担当者情報

### 9-1. 更新エンドポイント
`backend/app/routers/leads.py:490-494`
```python
@router.patch("/leads/{lead_id}", response_model=LeadResponse,
              dependencies=[Depends(require_permission("leads.update"))])
async def update_lead(lead_id, data: LeadUpdate, db, tenant_id, current_user):
```
- `old_row` を先に取得（`:504-509`）→ **変更前の `assigned_to` / `status` が取れる**
- `_UPDATABLE_COLUMNS` に `assigned_to` を含む（`:84`）
- 状態遷移を検出する既存の書き方あり: `is_lost_transition`（`:538`）

### 9-2. 後追い処理（fire-and-forget）の既存作法
`backend/app/routers/leads.py:699-726`
```python
await db.commit()                                   # :699
await invalidate_dashboard_cache(tenant_id)
... publish_leads_update(tenant_id) ...
# Discord ロール同期 (fire-and-forget, AC2.7)        # :707
if "estimated_scale" in update_data:
    ...
    asyncio.create_task(sync_lead_discord_role(...)) # :715
```
→ **commit 後に `asyncio.create_task` で投げる**のが本リポジトリの確立した作法。応答を待たせない。

### 9-3. 背景サービスのセッション取得
`backend/app/services/discord_role_sync.py:59-60`
```python
from app.database import AsyncSessionLocal
async with AsyncSessionLocal() as db:
```
→ 自前でセッションを開く。ただし同ファイルが参照するのは `public.*` 表のため `set_tenant_context` を呼んでいない。**本件はテナントスキーマの `notification_channels` / `staff` を読むため、§7 に従い `set_tenant_context` が必須。**

### 9-4. 担当者 → Discord ID
`migrations/019_create_staff_tables.sql`
```sql
:47    discord_user_id VARCHAR(50),
:55    UNIQUE (tenant_id, discord_user_id)   -- テナント内で重複なし
```
- `leads.assigned_to` は **`public.users.id`**（`backend/app/routers/analytics.py:106-113` の `LEFT JOIN public.users u ON u.id = l.assigned_to` で確認）
- `staff.user_id` が `users.id` を指す（`backend/app/schemas/staff.py` の `StaffResponse.user_id: int | None`）
- → `SELECT discord_user_id, last_name, first_name FROM {staff} WHERE user_id = :assigned_to`

---

## 10. 権限

| 権限キー | 定義 | 行 |
|---|---|---|
| `notifications.view` | 通知設定の閲覧 | `migrations/008_add_phase4_permissions.sql:8` |
| `notifications.manage` | 通知設定の管理 | `migrations/008_add_phase4_permissions.sql:9` |

`migrations/025_resync_owner_admin_all_permissions.sql:48-70`
```sql
--   オーナー: ALL（system.manage 含む）
--   システム管理者: ALL_EXCEPT_SYSTEM_MANAGE
FOR role_rec IN EXECUTE format(
    'SELECT id, name FROM %I.roles WHERE name IN (''オーナー'', ''システム管理者'')', ...)
...
'INSERT INTO %I.role_permissions (role_id, permission_id) SELECT %s, p.id FROM public.permissions p %s'
```
→ **オーナーは `notifications.manage` を保持**（全権限 INSERT の対象）。新規の権限付与は不要。

`require_permission` の実装: `backend/app/auth/dependencies.py:531-557`

---

## 11. UI 金型（ADR-144）

### 11-1. 金型が無い場合の手順（遵守済み）
`docs/adr/ADR-144-ui-component-governance.md:59-64`
```
### 4. 金型がない場合の手順
1. 実装を止め PO に報告する
2. PO 許可を得てから `components/` に金型を新設する
   (「Xxx.tsx」 + 「Xxx.css」（var() のみ）+ 「Xxx.stories.tsx」 の作法で）
3. 金型登録後にそれを使って実装する
```
→ 2026-10-15 に PO へ報告し「Q3 はよい」＝**新設許可を受領**。

### 11-2. 既存実装の扱い
`docs/adr/ADR-144-...:66-69`
```
### 5. 既存の独自実装
差分のみ検査のため既存実装（118+16+20 件）は赤化しない。
移行（金型への置き換え）は別トラック・別 PR で 1 ページ 1 部品ずつ順次行う。
```
→ 既存の生 checkbox 群は**本 PR では置き換えない**。

### 11-3. 複数選択の既存手本（これを金型に昇格させる）
`frontend/src/pages/inbox/SalesFormMultiSelect.tsx:126-143`
```tsx
{options.map((option) => {
  const checked = isSelected(option.id);
  return (
    <label
      key={option.id}
      className={`sales-form-option${checked ? " sales-form-option--checked" : ""}`}
      data-testid={`sales-form-option-${option.value}`}
    >
      <input type="checkbox" checked={checked}
             onChange={() => toggleOption(option)} aria-label={option.label} />
      <span className="sales-form-option-label">{option.label}</span>
    </label>
  );
})}
```
DOM の形＝`label > input[type=checkbox] + span`。CSS はページ側（`frontend/src/pages/inbox/InboxPage.css`）にあり、**金型化されていない**。

### 11-4. 既存金型には複数選択が無い
- `frontend/src/components/` 全数確認 → **`frontend/src/components/Checkbox.tsx` は存在しない**
- `frontend/src/components/Select.tsx:15-32` … `SelectOption { value; label; disabled? }`、`SelectSize = "sm"|"md"|"lg"`。**`multiple` 非対応＝単一選択のみ**

### 11-5. ガバナンス禁止リスト（checkbox は対象外）
`docs/CC_UI_GOVERNANCE.md:19-28`
```
| 生 <select> | <Select> 金型を使うこと |
| 生 <input type="text"|"search"|省略> | <TextField> / SearchBar 等を使うこと |
| 自作タブ（className に tab 語を含む div/nav 等） | <Tabs> / <OverflowTabs> を使うこと |
| 色直値（#xxx / rgba()）のインラインスタイル | CSS 変数 var(--color-*)（ADR-067）|
| 生 px 数値のインラインスタイル | デザイントークン var(--size-*)（ADR-067）|
```
→ `type="checkbox"` は CI の禁止対象では**ない**が、PO 指示「金型登録のないハードコードを禁止」に従い金型を新設する。

---

## 12. i18n（ADR-027）

既存キー `frontend/src/locales/ja.json:2000-2007`
```json
"settings": {
  "title": "設定",
  "notifications": "通知設定",
  "addChannel": "チャンネル追加",
  "addDiscordWebhook": "Discord Webhookチャンネル追加",
  "channelName": "チャンネル名",
  "noChannels": "通知チャンネルが設定されていません",
  "subtitle": "Webhook通知チャネルを設定・管理します."
}
```
- `frontend/scripts/check-i18n-missing-keys.js` … `t("key")` の literal キーが **ja.json と en.json の両方**に無いと exit 1
- `frontend/scripts/eslint-rules/no-japanese-literal.cjs` … JSXText / Literal / TemplateElement 内の日本語を検出。例外は `// eslint-disable-next-line local/no-japanese-literal -- <理由>` を**違反行の直前行**に置く

---

## 13. 新規金型に掛かる CI ゲート

| スクリプト | 要求 |
|---|---|
| `frontend/scripts/check-stories-count.js` | 全 「.tsx」 コンポーネントに対応する 「.stories.tsx」 が必須（EXEMPT 配列のみ除外） |
| `frontend/scripts/check-css-hardcoded-colors.js` | CSS に hex / rgba() 直書き禁止 |
| `frontend/scripts/check-css-hardcoded-values.js` | opacity / border-radius / z-index / spacing / sizing / font-size の数値直書き禁止 |
| `frontend/scripts/check-css-var-fallbacks.js` | `var(--x, #hex)` のフォールバック禁止 |
| `frontend/scripts/check-dark-parity.js` | `frontend/src/index.css` の `:root` と `:root.force-dark` で色系変数名が完全一致 |
| `frontend/scripts/check-new-tokens.js` | 新規トークン追加時は PR 本文のチェックリスト 4 項目が必須 |
| `frontend/scripts/check-i18n-missing-keys.js` | §12 |
| eslint `local/no-japanese-literal` | §12（lint-staged は `--max-warnings=0`） |

→ **新規デザイントークンを作らず既存トークンのみで組めば `check-new-tokens` / `check-dark-parity` を回避できる**（§13 の方針）。
`frontend/src/components/FormField.css` が使う既存トークン（流用候補）:
`--border` / `--bg-surface` / `--text-primary` / `--text-secondary` / `--text-muted` / `--danger` / `--accent` /
`--space-1` / `--space-2` / `--space-3` / `--space-4` / `--comp-input-radius` /
`--font-xs` / `--font-sm` / `--font-base` / `--font-weight-medium` / `--line-height-base` /
`--transition-micro` / `--focus-ring-shadow` / `--bg-hover`

---

## 14. 選択肢を API で配る先例（あり）

`backend/app/routers/leads.py:307-327`
```python
@router.get("/leads/sales-form-options", response_model=list[SalesFormOptionResponse],
            dependencies=[Depends(require_permission("leads.view"))])
async def list_sales_form_options(db, tenant_id) -> list[SalesFormOptionResponse]:
    """テナント別 sales_form 選択肢マスタ一覧を取得する（is_active=True のみ）"""
```
→ 「選択肢の一覧を API で返す」形には**先例がある**。フロントに一覧を複製せず API から取る設計が本リポジトリの作法から外れない。

---

## 15. 未確認（宿題）

| # | 内容 | 確認方法 |
|---|---|---|
| U1 | 本番 `notification_channels` に現在何が登録されているか（`event_types` の実値） | 実機で `https://app.salesanchor.jp/notifications` を開く。**ただし現画面は `event_types` を表示しないため、本 PR で表示されるようになってから確認する** |
| U2 | 自社用 Discord サーバーの Webhook URL の有無 | PO 回答待ち。URL は会話に貼らず設定画面から直接登録 |
| U3 | 埋め込み外 `content` のメンションで実際にスマホが鳴るか | 自社サーバー登録後に実送信して確認（§8 の設計はこれを前提に組む） |
| U4 | 通知文面に顧客名を載せてよいか | PO 回答待ち（Q4）。既存 Meta 通知は「個人情報を載せない」方針（`backend/app/routers/webhook.py:931` のコメント） |
| U5 | 受信箱の「新規バッジ」の意味（担当表示か未開封表示か） | PO 回答待ち（Q7）。**本 PR の対象外・別便** |

---

## 16. PO 決定事項（2026-10-15）

| # | 決定 |
|---|---|
| 案 A 採用 | 画面で「どの通知をどの送信先に流すか」を設定できるようにする（サーバー側固定の案 B は却下＝設定の分散になるため） |
| Q1 | **レポート通知は不要。アサイン連絡のみ** |
| Q2 | **案 1**＝未実装の 3 種類（`customer_created` / `deal_won` / `invoice_issued`）は選択肢から外す |
| Q3 | **Checkbox 金型の新設を許可** |
