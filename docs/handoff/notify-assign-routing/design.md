# design: 通知の送信先振り分け ＋ 商談アサインの Discord 通知

**日付**: 2026-10-15
**ベース**: `origin/main` = `e1cdbc468`（PR #4310）
**recon**: `docs/handoff/notify-assign-routing/recon.md`
**対象 ADR**: ADR-144（UI 金型ガバナンス）／ADR-027（i18n）／ADR-067（デザイントークン）／ADR-072（テナント文脈）／ADR-109・ADR-120（区分値 SSOT の作法）／ADR-025（手動 DB 操作の原則禁止）／ADR-1015（PR 区分。本件は「新機能・新しい API を足す」ため **A 区分**＝ PO の GO 待ち）／ADR-1016（書き込みルートは realtime の表に必ず載せる）／ADR-147（共通6ロール。担当者の役割判定は名前で分岐しない）
**PO 決定**: 案 A 採用 ／ Q1=レポート通知は対象外 ／ Q2=案 1（未実装 3 種類を選択肢から外す）／ Q3=Checkbox 金型の新設を許可

---

## ① KGI（PO が画面で ○× を一義に判定できる粒度）

| # | KGI | 判定方法（PO が自分で見て決められる） |
|---|---|---|
| **K1** | オーナーが**通知設定画面だけで**「どの通知をどの Discord サーバーに送るか」を決められる | 設定画面で送信先を 2 つ登録し、片方に「商談の担当アサイン」だけ、もう片方に「Meta の新着メッセージ」だけチェックを入れて保存 → 再読み込みしてもその通りに表示される |
| **K2** | 登録済みの送信先の設定を**後から変更できる** | 既存の送信先の鉛筆ボタンからチェックを変えて保存 → 再読み込みで反映されている |
| **K3** | 商談化で担当を決めると、**担当者本人の Discord に通知が鳴る** | 受信箱で商談化 →「確定」→ 自社サーバーの該当チャンネルに投稿が出る。かつ**担当者のスマホに通知が来る**（メンションが鳴る） |
| **K4** | 顧客対応用の Discord には**何も起きない** | 商談化しても顧客対応サーバーには投稿されない |
| **K5** | 鳴らない選択肢が画面から消えている | 設定画面の選択肢が「商談の担当アサイン／Meta の新着メッセージ／TCG在庫配信エラー」の 3 つだけになっている |

### KPI（機械で測る）

| # | KPI | 測定 |
|---|---|---|
| P1 | `notification_channels` 以外に振り分け設定を保存する場所を増やさない | `git diff main...HEAD -- migrations/` が**空**であること |
| P2 | 通知の種類の一覧がバックエンド 1 箇所に集約されている | `NotificationEventType` Enum 以外に種類の文字列リストを持つ箇所が無い（`git grep` で確認） |
| P3 | 新規デザイントークンを作らない | `git diff main...HEAD -- frontend/src/index.css` が**空**であること（`check:new-tokens` / `check:dark-parity` の追加負荷ゼロ） |
| P4 | 既存の生 checkbox を本 PR では置き換えない | `git diff main...HEAD -- frontend/src/pages/inbox/SalesFormMultiSelect.tsx` が**空**（ADR-144:66-69 遵守） |

---

## ② 現在地（recon の要約・該当箇所のみ）

| 事実 | 根拠 |
|---|---|
| 送信先の表は複数行可・UNIQUE 制約なし | `migrations/009_add_phase4_tenant_tables.sql:8-18` |
| 該当する全送信先に送る | `backend/app/routers/notifications.py:117` |
| 絞り込みは `event_types LIKE '%種類%'`（部分一致） | 同 `:112` |
| **画面が種類を送っていない** | `frontend/src/pages/notifications/NotificationsPage.tsx:35` |
| **変更 API が無い**（GET/POST/DELETE のみ） | `backend/app/routers/notifications.py:62,71,94` |
| 変更用の部品はデッドコードとして既に存在 | 同 `:41-45`（`ChannelUpdate`）／`:59`（`_UPDATABLE`） |
| 実装済みの種類は 2 つだけ。既定 3 種類は送信元ゼロ | `backend/app/routers/webhook.py:938-947` ／ `backend/app/services/tcg_distribution_svc.py:857-866` |
| **埋め込みカード内のメンションは通知されない** | Discord 公式 `https://docs.discord.com/developers/resources/message` |
| 後追い処理の作法＝commit 後 `asyncio.create_task` | `backend/app/routers/leads.py:699-726` |
| 背景セッションは自前で開く | `backend/app/services/discord_role_sync.py:59-60` |
| テナント文脈は `set_tenant_context` 経由のみ（生 SET は CI がブロック） | `backend/app/auth/dependencies.py:309-318` |
| オーナーは `notifications.manage` を保持 | `migrations/025_resync_owner_admin_all_permissions.sql:48-70` |
| 複数選択の金型は存在しない／手本はある | `components/` 全数確認 ／ `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:126-143` |

---

## ③ 設計（How）

### 3-1. 通知の種類の SSOT

**バックエンドの Enum を唯一の正とする。** フロントは一覧を持たず API から取得する。

**新規** `backend/app/schemas/notification.py`
```python
from enum import Enum


class NotificationEventType(str, Enum):
    """通知の種類の SSOT。

    ここに無い値は API が拒否する。送信元が存在しない種類を増やしてはいけない
    （recon §6: customer_created / deal_won / invoice_issued は送信元ゼロのため除外）。
    値は notification_channels.event_types に JSON 配列として保存され、
    送信時は LIKE '%値%' の部分一致で照合される（notifications.py:112）ため、
    **ある値が他の値の部分文字列になってはいけない**。
    """

    lead_assigned = "lead_assigned"                      # 商談の担当アサイン（本 PR 新設）
    meta_message_received = "meta_message_received"      # 既存: webhook.py:938-947
    tcg_distribution_error = "tcg_distribution_error"    # 既存: tcg_distribution_svc.py:857-866
```

**部分一致の安全性チェック（実装時に必ず確認）**: 3 値は互いに部分文字列関係に無い（`lead_assigned` / `meta_message_received` / `tcg_distribution_error`）。将来値を増やす際は同じ確認を行う。

**フロントが持つのは表示名の対応表のみ**（ADR-027 が i18n キーを要求し、`frontend/scripts/check-i18n-missing-keys.js` は literal キーしか検査できないため、キーはリテラルで書く）。

**新規** `frontend/src/constants/notificationEventTypes.ts`
```ts
/**
 * 通知の種類の「表示名キー」対応表。
 * 種類の一覧そのものは SSOT ではない（正は backend の NotificationEventType）。
 * 画面は GET /notification-event-types が返すコードを並べ、本表で表示名を引く。
 * 表に無いコードが来たらコードをそのまま表示する（黙って消さない）。
 */
export const NOTIFICATION_EVENT_LABEL_KEYS: Record<string, string> = {
  lead_assigned: "notifications.eventType.leadAssigned",
  meta_message_received: "notifications.eventType.metaMessageReceived",
  tcg_distribution_error: "notifications.eventType.tcgDistributionError",
};
```

**設計判断の理由**: ADR-109（LeadStatus）は backend Enum ＋ frontend 定数の二重持ちを採っているが、本件は「画面に並べる一覧」を API から取るため**一覧の二重持ちは発生しない**。表示名だけがフロントに残り、未知コードはコードをそのまま出すため**不一致が画面に見える形で露出する**（黙って欠落しない）。

---

### 3-2. バックエンド API（3 箇所）

#### (a) 選択肢を返す新規エンドポイント
先例: `backend/app/routers/leads.py:307-327`（`GET /leads/sales-form-options`）

**追加先** `backend/app/routers/notifications.py`（`list_channels` の直前）
```python
class EventTypeResponse(BaseModel):
    code: str


@router.get("/notification-event-types", response_model=list[EventTypeResponse],
            dependencies=[Depends(require_permission("notifications.view"))])
async def list_event_types() -> list[EventTypeResponse]:
    """通知の種類の一覧（SSOT: NotificationEventType）"""
    return [EventTypeResponse(code=e.value) for e in NotificationEventType]
```
DB に触らないため tenant / db 依存は取らない。

#### (b) 作成時の既定値を是正し、値を検証する
**変更前** `backend/app/routers/notifications.py:38`
```python
    event_types: list[str] = Field(default_factory=lambda: ["customer_created", "deal_won", "invoice_issued"])
```
**変更後**
```python
    event_types: list[NotificationEventType] = Field(default_factory=list)
```
- 既定値を `[]` にする（送信元ゼロの 3 種類を既定にしない＝PO 決定 Q2 案 1）
- 型を Enum にすることで **FastAPI が未知の値を 422 で拒否**する（手書きの検証コードは不要）
- `:83` の `json.dumps(data.event_types)` は Enum だと直列化できないため **`[e.value for e in data.event_types]` に変更**（実装時の必須注意点）

#### (c) 変更エンドポイントを新設（デッドコードを生かす）
`ChannelUpdate`（`:41-45`）と `_UPDATABLE`（`:59`）を初めて使う。

**追加先** `backend/app/routers/notifications.py`（`delete_channel` の直前）
```python
@router.patch("/notification-channels/{channel_id}", response_model=ChannelResponse,
              dependencies=[Depends(require_permission("notifications.manage"))])
async def update_channel(channel_id: int, data: ChannelUpdate, db=Depends(get_db),
                         tenant_id: int = Depends(get_current_tenant),
                         current_user: User = Depends(get_current_user)):
    """通知チャンネルを部分更新する（event_types の振り分けを含む）"""
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items()
                   if k in _UPDATABLE}
    if not update_data:
        raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")
    if "event_types" in update_data:
        update_data["event_types"] = json.dumps(
            [e.value if hasattr(e, "value") else e for e in update_data["event_types"]])
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = channel_id
    result = await db.execute(
        text(f"UPDATE notification_channels SET {set_clauses}, updated_at = NOW() "
             f"WHERE id = :id RETURNING {_COLS}"),
        update_data,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="チャンネルが見つかりません")
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="update", table_name="notification_channels",
                           record_id=channel_id, new_data=update_data)
    await db.commit()
    await reset_tenant_context(db, tenant_id)   # ADR-072 Phase 2.5
    return ChannelResponse(**dict(row))
```
- `ChannelUpdate.event_types` の型も `list[NotificationEventType] | None` に変更して検証を効かせる
- `_UPDATABLE` による allow-list で SQL のカラム名を固定（任意文字列を SET 句に入れない）
- 既存の `create_channel`（`:71-91`）と**同じ順序**で audit → commit → reset を行う

**既存データの扱い**: 保存済みの `customer_created` 等は**消さない**（送信元が無いため無害）。オーナーがこの画面で保存し直した時点で、チェックした内容に**置き換わる**＝自然に片付く。**手動の DB 操作は行わない**（ADR-025）。

---

### 3-3. メンションで実際に鳴らす（Discord 公式の制約に対応）

**根拠**: `https://docs.discord.com/developers/resources/message`
> mentions placed in embed titles or descriptions **do not trigger notifications**. Mentions only notify users when they appear in the message's `content` field.

**変更前** `backend/app/routers/notifications.py:108,119`
```python
async def send_discord_notification(db, tenant_id, event_type, title, message) -> None:
...
                    payload = {"embeds": [{"title": title, "description": message, "color": 3447003}]}
```
**変更後**
```python
async def send_discord_notification(db, tenant_id, event_type, title, message,
                                    mention_user_ids: list[str] | None = None) -> None:
...
                    payload: dict = {"embeds": [{"title": title, "description": message,
                                                 "color": 3447003}]}
                    if mention_user_ids:
                        # Discord 公式: embeds 内のメンションは通知されない。content に置く。
                        # https://docs.discord.com/developers/resources/message
                        payload["content"] = " ".join(f"<@{uid}>" for uid in mention_user_ids)
                        # 指定した相手だけを鳴らす（@everyone / @here / role の暴発を防ぐ）
                        payload["allowed_mentions"] = {"parse": [], "users": list(mention_user_ids)}
```
- **引数は末尾に既定値付きで追加** → 既存の 2 箇所の呼び出し（`backend/app/routers/webhook.py:938-947` / `backend/app/services/tcg_distribution_svc.py:857-866`）は**無変更で動く**
- `allowed_mentions.parse: []` により、文面に `@everyone` 等が混ざっても鳴らない（フェイルクローズ）
- `mention_user_ids` は数字のみの Discord Snowflake を想定。呼び出し側で `str.isdigit()` を確認してから渡す（文字列埋め込みによる細工を防ぐ）

---

### 3-4. 商談アサイン通知サービス（新規）

**新規** `backend/app/services/lead_assign_notifier.py`
```python
"""商談の担当アサインを Discord に通知する（fire-and-forget）。

呼び出しは leads.update_lead の commit 後（ADR-072: 新しいセッションを開き、
notification_channels / staff はテナントスキーマのため set_tenant_context が必須）。
作法は services/discord_role_sync.py:59-60 に倣う。
"""
import logging

from sqlalchemy import text

from app.auth.dependencies import set_tenant_context, tenant_table_ref
from app.routers.notifications import send_discord_notification
from app.schemas.notification import NotificationEventType

logger = logging.getLogger(__name__)


async def notify_lead_assigned(tenant_id: int, lead_id: int, assigned_to_user_id: int) -> None:
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tenant_id)          # ADR-072（生 SET は CI がブロック）
            staff_t = tenant_table_ref(db, tenant_id, "staff")
            leads_t = tenant_table_ref(db, tenant_id, "leads")

            staff_row = (await db.execute(
                text(f"SELECT discord_user_id, last_name, first_name FROM {staff_t} "
                     f"WHERE user_id = :uid"),
                {"uid": assigned_to_user_id},
            )).mappings().first()
            lead_row = (await db.execute(
                text(f"SELECT lead_code, customer_name FROM {leads_t} WHERE id = :lid"),
                {"lid": lead_id},
            )).mappings().first()
            if not lead_row:
                return

            name = " ".join(filter(None, [
                (staff_row or {}).get("last_name"), (staff_row or {}).get("first_name")])) or ""
            did = str((staff_row or {}).get("discord_user_id") or "")
            mention = [did] if did.isdigit() else None       # 数字以外は渡さない

            await send_discord_notification(
                db=db, tenant_id=tenant_id,
                event_type=NotificationEventType.lead_assigned.value,
                title=TITLE, message=BODY,                   # 文面は §3-7 で確定
                mention_user_ids=mention,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[leads] アサイン通知失敗（商談化自体には影響なし）: lead=%s %s", lead_id, exc)
```
- 例外は**外に出さない**（商談化の成否に影響させない）。既存 `backend/app/services/tcg_distribution_svc.py:867-868` と同じ方針
- `send_discord_notification` が末尾で `db.commit()` と `reset_tenant_context` を行う（`backend/app/routers/notifications.py:132-133`）ため、本関数側では行わない
- `discord_user_id` が未登録のスタッフでも**投稿自体は行う**（メンションのみ付かない）。通知が無言で消えるより運用上安全

---

### 3-5. 商談化からの呼び出し（既存の作法に合わせる）

**追加先** `backend/app/routers/leads.py`（既存の Discord ロール同期ブロック `:707-726` の直後）
```python
    # 商談アサイン通知 (fire-and-forget)
    # 担当が「変わったとき」のみ。同じ担当への再保存では鳴らさない。
    new_assigned = update_data.get("assigned_to")
    if "assigned_to" in update_data and new_assigned and new_assigned != old_row["assigned_to"]:
        try:
            from app.services.lead_assign_notifier import notify_lead_assigned
            asyncio.create_task(
                notify_lead_assigned(
                    tenant_id=tenant_id,
                    lead_id=lead_id,
                    assigned_to_user_id=int(new_assigned),
                )
            )
        except Exception:
            logger.warning("[leads] assign notify task creation failed lead=%d", lead_id)
```
- 置き場所: `await db.commit()`（`:699`）より**後**。更新が確定してから通知する
- `old_row`（`:504-509`）と比較して**担当が実際に変わった時だけ**鳴らす（二重通知を防ぐ）
- 商談化（`status="negotiating"` ＋ `assigned_to`）でも、担当変更だけでも鳴る。PO 要望は「担当にメンション」なので**担当変更を起点**とする

---

### 3-6. フロントエンド

#### (a) Checkbox 金型を新設（ADR-144:59-64 手順・PO 許可済）

手本は `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:126-143` の DOM 形（`label > input[type=checkbox] + span`）。

**新規 3 点セット**
- `frontend/src/components/Checkbox.tsx`
  ```ts
  export type CheckboxSize = "sm" | "md" | "lg";

  export interface CheckboxOwnProps {
    label: string;          // 表示済みの文字列（呼び出し側で t() 済み）
    size?: CheckboxSize;    // 既定 "md"
    error?: string;
    description?: string;
  }
  export type CheckboxProps = CheckboxOwnProps &
    Omit<InputHTMLAttributes<HTMLInputElement>, keyof CheckboxOwnProps | "size" | "type">;
  ```
  - `frontend/src/components/TextField.tsx:16-27` と同じ `Omit<..., keyof OwnProps | "size">` 方式に揃える
  - `type` は固定（`Omit` で外から変えられないようにする）
- `frontend/src/components/Checkbox.css`
  - クラス名は BEM: `comp-checkbox` / `comp-checkbox--sm|md|lg` / `comp-checkbox__input` / `comp-checkbox__label` / `comp-checkbox__description` / `comp-checkbox--error`
  - **既存トークンのみを使用**（`frontend/src/index.css` に新規トークンを足さない＝KPI P3）
    `--border` / `--bg-surface` / `--text-primary` / `--text-secondary` / `--danger` / `--accent` /
    `--space-1` / `--space-2` / `--space-3` / `--comp-input-radius` /
    `--font-xs` / `--font-sm` / `--font-base` / `--font-weight-medium` / `--line-height-base` /
    `--transition-micro` / `--focus-ring-shadow` / `--bg-hover`
  - hex / rgba / 生数値・`var(--x, fallback)` は書かない（`check:css-colors` / `check:css-values` / `check:css-var-fallbacks`）
- `frontend/src/components/Checkbox.stories.tsx`
  - `frontend/scripts/check-stories-count.js` の必須要件。`Meta` ＋ `tags: ['autodocs']`、Story は `Default` / `Checked` / `WithDescription` / `WithError` / `Disabled` / `Sizes` / `Group`（縦並びの複数選択例）

#### (b) 通知設定画面を改修
`frontend/src/pages/notifications/NotificationsPage.tsx`

| 変更 | 内容 |
|---|---|
| 読み込み | `GET /notification-event-types` を追加で取得し、選択肢を描画 |
| 追加フォーム | 既存の名前・URL（`:62-63` の `TextFieldControl`）の下に **Checkbox 群**を追加。POST で `event_types` を送る（`:35` を修正） |
| 一覧 | 「通知の種類」列を追加（保存済み JSON を parse して表示名を並べる。表に無いコードは**コードをそのまま表示**） |
| 編集 | 行に鉛筆ボタン（`Button` 金型）を追加 → `Modal` で名前・URL・種類を編集 → `PATCH /notification-channels/{id}` |
| エラー | 既存の `.error-message` を流用 |

**変更前** `:35`
```ts
await api.post("/notification-channels", { channel_name: form.channel_name, webhook_url: form.webhook_url });
```
**変更後**
```ts
await api.post("/notification-channels", {
  channel_name: form.channel_name,
  webhook_url: form.webhook_url,
  event_types: form.event_types,     // 選択されたコードの配列
});
```

#### (c) i18n（ADR-027・ja.json と en.json の両方に同一キー）
`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `notifications` 配下に追加:

| キー | ja |
|---|---|
| `notifications.eventTypesLabel` | この送信先に送る通知 |
| `notifications.eventTypesEmpty` | （未選択） |
| `notifications.eventTypesColumn` | 通知の種類 |
| `notifications.editChannel` | 送信先を編集 |
| `notifications.eventType.leadAssigned` | 商談の担当アサイン |
| `notifications.eventType.metaMessageReceived` | Meta の新着メッセージ |
| `notifications.eventType.tcgDistributionError` | TCG在庫配信エラー |

既存 `settings.*`（`frontend/src/locales/ja.json:2000-2007`）はそのまま使う（`addChannel` / `channelName` / `noChannels` 等）。

---

### 3-7. 通知の文面（PO 判断 Q4 待ち・実装はどちらでも差し替え可能な形にする）

既存 Meta 通知は「個人情報を載せない」方針（`backend/app/routers/webhook.py:931` のコメント）。自社内サーバー向けに顧客名を出すかは PO 判断。

| 案 | content（鳴る部分） | embed title | embed description |
|---|---|---|---|
| **ア（顧客名あり）** | `<@123456789>` | `🤝 商談化：担当アサイン` | `顧客: 山田商事\nリード: L-00123\n担当: 谷澤 伸吾` |
| **イ（顧客名なし）** | `<@123456789>` | `🤝 商談化：担当アサイン` | `リード: L-00123\n担当: 谷澤 伸吾` |

→ 実装では文面生成を `backend/app/services/lead_assign_notifier.py` 内の 1 箇所に閉じ、案ア／イの切替が 1 行で済む形にする。**日本語文字列はバックエンドのため i18n 制約の対象外**（ADR-027 は UI 文字列が対象。既存 `backend/app/routers/webhook.py:934-936` / `backend/app/services/tcg_distribution_svc.py:860-865` も日本語直書き）。

---

## ④ 弊害・リスクと対策

| # | リスク | 対策 | 検証 |
|---|---|---|---|
| R1 | `event_types LIKE '%x%'` の部分一致で別の種類に誤ヒット | 3 値が互いに部分文字列でないことを実装時に確認。Enum の docstring に明記 | 単体テストで 3 値の相互部分文字列チェックを自動化 |
| R2 | 背景タスクでテナント文脈を張り忘れ、**別テナントの送信先に送る**（最悪の事故） | `notify_lead_assigned` 冒頭で `set_tenant_context` を必ず呼ぶ。`notification_channels` はスキーマ修飾なしの SQL（`backend/app/routers/notifications.py:112`）なので文脈が命 | テナント 2 つを用意した単体テストで、他テナントの送信先に送られないことを検証 |
| R3 | 既存 2 箇所の通知呼び出しを壊す | `mention_user_ids` は**末尾に既定値 None で追加**。既存呼び出しは無変更 | 既存テスト `backend/tests/test_webhook_instagram.py:317` / `backend/tests/test_conv_backbone_ben1b.py:179` が緑 |
| R4 | `@everyone` 等の暴発 | `allowed_mentions = {"parse": [], "users": [...]}` でフェイルクローズ | 単体テストで payload を検証 |
| R5 | 商談化の応答が Discord の遅延（timeout 10s）で遅くなる | commit 後の `asyncio.create_task`（`backend/app/routers/leads.py:707-726` と同じ作法） | 商談化の応答時間が変わらないことを実機で体感確認 |
| R6 | 通知失敗で商談化そのものが失敗する | サービス全体を try/except で包み warning ログのみ | 単体テストで webhook 送信失敗時も 200 を返すことを検証 |
| R7 | 新規トークン追加で `check:new-tokens` / `check:dark-parity` に引っかかる | 既存トークンのみで CSS を書く（KPI P3） | `git diff -- frontend/src/index.css` が空 |
| R8 | 保存済みの `customer_created` 等が画面に出ず「設定が消えた」と誤解される | 一覧では**未知コードもそのまま表示**する。黙って隠さない | 画面で確認 |
| R9 | PATCH の SET 句にユーザー入力のカラム名が入る | `_UPDATABLE`（`backend/app/routers/notifications.py:59`）の allow-list で固定 | コードレビュー |
| R10 | **メンションが実際に鳴らない**（公式制約の読み違い） | `content` に置く設計（公式ドキュメント根拠あり）。**実機の自社サーバーで鳴ることを確認するまで完了にしない** | 実機確認（U3） |

---

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | `GET /notification-event-types` が 3 件（`lead_assigned` / `meta_message_received` / `tcg_distribution_error`）を返す | 単体テスト（`notifications.view` 権限で 200・件数と値を assert） |
| A2 | `POST /notification-channels` が未知の種類を 422 で拒否する | 単体テスト（`event_types: ["bogus"]` → 422） |
| A3 | `POST` の既定が `[]`（送信元ゼロの 3 種類が入らない） | 単体テスト（`event_types` 省略 → 保存値が `[]`） |
| A4 | `PATCH /notification-channels/{id}` で `event_types` を変更でき、GET に反映される | 単体テスト（PATCH → GET で値一致） |
| A5 | `PATCH` が `notifications.manage` 権限を要求する | 単体テスト（権限なし → 403） |
| A6 | `PATCH` が存在しない id で 404 | 単体テスト |
| A7 | 担当が変わったとき `lead_assigned` の通知が 1 回だけ送られる | 単体テスト（`send_discord_notification` を mock し呼び出し回数と `event_type` を assert） |
| A8 | 担当が変わらない更新では通知が送られない | 単体テスト（同じ `assigned_to` で PATCH → 呼び出し 0 回） |
| A9 | 送信 payload の `content` にメンションが入り、`allowed_mentions.parse` が `[]` | 単体テスト（httpx を mock して payload を検証） |
| A10 | `discord_user_id` 未登録でも投稿は行われ、メンションは付かない | 単体テスト |
| A11 | 他テナントの送信先に送られない | 単体テスト（2 テナントの送信先を用意） |
| A12 | 通知が失敗しても `PATCH /leads/{id}` は 200 を返す | 単体テスト |
| A13 | 既存の Meta / TCG 通知の呼び出しが壊れていない | 既存テストが緑（`backend/tests/test_webhook_instagram.py` / `backend/tests/test_conv_backbone_ben1b.py`） |
| A14 | `Checkbox` 金型が 3 点セットで登録され CI が緑 | `npm run check:all`（`check:stories` 含む）が緑 |
| A15 | 新規デザイントークンがゼロ | `git diff main...HEAD -- frontend/src/index.css` が空 |
| A16 | i18n キーが ja/en 両方に存在 | `npm run check:i18n` が緑 |
| A17 | `migrations/` の変更がゼロ（危険パスを含まない PR） | `git diff main...HEAD --name-only -- migrations/` が空 |
| A18 | **実機**: 設定画面で 2 つの送信先に別々の種類を割り当てて保存・再読み込みで保持 | PO ＋ 実機（K1 / K2） |
| A19 | **実機**: 商談化の「確定」で自社サーバーに投稿され、担当者のスマホに通知が鳴る | PO ＋ 実機（K3・U3） |
| A20 | **実機**: 顧客対応サーバーには投稿されない | PO ＋ 実機（K4） |

---

## ⑥ 触るファイル

```
backend/app/schemas/notification.py, backend/app/routers/notifications.py, backend/app/routers/leads.py, backend/app/services/lead_assign_notifier.py, backend/tests/test_notification_event_routing.py, frontend/src/components/Checkbox.tsx, frontend/src/components/Checkbox.css, frontend/src/components/Checkbox.stories.tsx, frontend/src/constants/notificationEventTypes.ts, frontend/src/pages/notifications/NotificationsPage.tsx, frontend/src/locales/ja.json, frontend/src/locales/en.json, docs/handoff/notify-assign-routing/recon.md, docs/handoff/notify-assign-routing/design.md, .claude-pipeline/active-work.d/release-notify-assign-routing.md
```

## ⑦ 削除するファイル

なし

## ⑧ 触らない範囲（明示）

- `migrations/`（**新しい表・列は一切作らない**。危険パスを含まないため ADR-135/136 の危険 PR 手順に該当しない）
- `docs/adr/ADR-009-discord-gateway.md` 系統（顧客とのやり取り用 Discord Bot）— 一切変更しない
- `backend/app/services/discord_notifier.py`（env `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` の admin 通知系統）
- `frontend/src/pages/inbox/SalesFormMultiSelect.tsx` および既存の生 checkbox 30 箇所超（ADR-144:66-69 により移行は別 PR）
- `frontend/src/index.css`（新規トークンを作らない）
- 受信箱の「新規バッジ」（PO 要望の 3 つ目・**別便**。Q7 の回答が必要）
- レポート通知（PO 決定 Q1 により対象外）
- 受信箱の商談化ポップアップ（`frontend/src/pages/inbox/InboxKartePanel.tsx`）— 既に本番稼働中。本 PR では変更しない

---

## ⑨ 外部・過去事例の参照と我々への応用

| 出典 | 確認した内容 | 設計への反映 |
|---|---|---|
| Discord 公式 `https://docs.discord.com/developers/resources/message`（2026-10-15 取得） | 「mentions placed in embed titles or descriptions **do not trigger notifications**. Mentions only notify users when they appear in the message's `content` field」／`allowed_mentions` は **message content** のメンションで通知するかを制御する | §3-3 で `content` にメンションを置き、`allowed_mentions.parse: []` ＋ `users` 明示でフェイルクローズ |

**注**: 上記以外の外部事例は一次情報で確認できていないため記載しない（推測で事例を書かない）。

---

## 維持の仕組み

守り手: `backend/tests/test_notification_event_routing.py`

この仕組みが将来壊れたときに**自動で赤くなる**関所を並べる。人手の記憶に頼らない。

| 守るもの | 関所 | 壊れたときに出る症状 |
|---|---|---|
| 通知の種類の SSOT（3種類・相互に部分文字列でない） | `backend/tests/test_notification_event_routing.py`（A1・R1） | 種類を増やして部分一致が衝突すると赤 |
| 未知の種類を API が拒否する | 同上（A2） | Enum 外の値を受け付けるようになると赤 |
| 振り分けを後から変更できる | 同上（A4〜A6） | PATCH が壊れると赤 |
| **他テナントへ送らない** | 同上（A11：行レベル検証） | `tenant_id` 条件を外すと赤 |
| メンションが `content` に入り `allowed_mentions` が閉じている | 同上（A9） | `embeds` だけに戻すと赤（＝通知が鳴らない状態に戻る） |
| 担当が変わったときだけ1回送る | 同上（A7・A8） | 二重通知・誤通知になると赤 |
| 通知失敗が商談化を壊さない | 同上（A12） | 例外が外に漏れると赤 |
| 既存の Meta / TCG 通知を壊さない | `backend/tests/test_webhook_instagram.py` ／ `backend/tests/test_conv_backbone_ben1b.py` | 引数追加で既存呼び出しが壊れると赤 |
| 書き込み API を台帳に登録する（ADR-1016） | `backend/tests/test_realtime_topics.py` | 新しい書き込み API を足して登録を忘れると赤 |
| Checkbox 金型の3点セット | `frontend/scripts/check-stories-count.js` | 「.stories.tsx」を消すと赤 |
| CSS に直値を書かない | `frontend/scripts/check-css-hardcoded-colors.js` ／ `frontend/scripts/check-css-hardcoded-values.js` ／ `frontend/scripts/check-css-var-fallbacks.js` | hex・生数値・フォールバックを書くと赤 |
| i18n キーが ja/en 両方にある | `frontend/scripts/check-i18n-missing-keys.js` | 片方だけ足すと赤 |
| API の形と台帳が一致する | CI「API contract is up to date」 | `frontend/api-contract/openapi.json` の更新を忘れると赤 |

**人手に残る部分**: メンションで実際にスマホが鳴るかの確認（A19）。Discord 公式仕様の根拠はあるが、実機の自社サーバーでの実測は自動化していない。送信先の Webhook URL は秘密情報のため CI に置かない。

---

## ⑩ 継続（この PR の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | 受信箱の「新規バッジ」 | **別便**。PO 回答（2026-10-15）= **案 B「担当になったが、まだ開いていない」（開くと消える）**。担当者ごとの既読記録を新設する必要があるため `migrations/` を触る → **ADR-135/136 の危険 PR 手順（事前提示＋「GO #PR番号」）が必要**。会話一覧 API（`backend/app/routers/meta_inbox.py`）が `assigned_to` を返していないため、API の返却項目追加も必要 |
| C2 | 役割名の文字列依存の恒久対策（商談化の担当候補） | 別便。**2026-10-15 訂正**: 当初「`roles.system_key` は流用不可、`roles` への列追加が必要」と書いたが誤り。正しくは**権限キーを1つ新設する**のが恒久対策。`backend/app/auth/system_roles.py:1-5` の通り owner / admin は権限マスタ（`public.permissions`）から**check 時に計算**されるため、新しい権限キーは `role_permissions` の行追加なしで自動的に届く（`compute_permission_keys`:22-37）。名前での分岐は ADR-147 追補が禁じている（`backend/app/auth/system_roles.py:13`「見分けは roles.system_key で行い、名前では分岐しない」）。`roles` への列追加は不要。権限キーの seed のみ `migrations/` を触る＝A 区分 |
| C3 | 既存の生 checkbox 30 箇所超の金型移行 | ADR-144:66-69 に従い別トラック・1 ページ 1 部品 |
| C4 | レポート通知の実装 | PO が必要と判断した時点で着手（Celery beat の土台はある: `backend/app/celery_app.py:58-150`） |
| C5 | 本番 `notification_channels` の現状確認（U1） | 本 PR で `event_types` が画面に出るようになってから実機で確認 |

## PO の決定（2026-10-29）: 担当割当の通知はお客さんの名前で知らせる

- 担当割当の Discord 通知は、リードの番号ではなくお客さんの名前（leads.customer_name）で知らせる。名前が空のときは「名前の無いリード」と出し、番号には戻さない（PO 回答「1」）。
- 背景: PO は同日「リード番号はアプリ全体で画面に出さない。CSV の取り込み・書き出しのときだけ使う」と決めた（記録は docs/handoff/inbox-brushup/README.md、ADR-1049 の一連の作業）。
