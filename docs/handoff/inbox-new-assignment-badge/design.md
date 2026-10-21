# design: 受信箱の「新規」バッジ（担当になったが、まだ開いていない）

**日付**: 2026-10-15
**ベース**: `origin/main` = `62f341957`（PR-A 作業先 worktree で再確認）
**recon**: `docs/handoff/inbox-new-assignment-badge/recon.md`
**本便の区分**: 本 PR（PR-A・`release/inbox-badge-column`）は「出し方（2段階・expand/contract）」
（本書この後の節）のうち**列だけ**を担当する。読み書きのコードと画面は PR-B
（`release/inbox-new-assignment-badge`）の担当。`backend/app/routers/leads.py`・
`backend/app/routers/meta_inbox.py`・`frontend/` 配下の各ファイルは PR-B で行番号が動くため、
本書では識別子名で引用する（審査 D5 対応）。
**対象 ADR**: ADR-1008（人の列は `public.users(id)` を参照）／ADR-144（UI 金型ガバナンス）／ADR-027（i18n）／ADR-067（デザイントークン）／ADR-072（テナント文脈）／ADR-025（手動 DB 操作の原則禁止）／ADR-135・ADR-136（危険パスの GO 手順）／ADR-1015（PR 区分＝**A 区分**：新機能かつ 「.sql」を含む）／ADR-1016（書き込みルート台帳。**本件は新しい書き込み API を足さないため登録不要**）
**PO 決定**: 案 B「**担当になったが、まだ開いていない**」。**開くと消える。**

---

## ① KGI（PO が画面で ○× を一義に判定できる粒度）

| # | KGI | 判定方法 |
|---|---|---|
| **K1** | 自分が担当になった会話に、受信箱の一覧で**「新規」バッジが出る** | 別の人の端末（またはオーナー）で商談化し担当を自分に設定 → 自分の受信箱を再読込 → その会話に「新規」が付く |
| **K2** | **その会話を開くとバッジが消える** | バッジ付きの会話をタップ → 一覧に戻る → バッジが消えている（再読込しても消えたまま） |
| **K3** | **他人が担当の会話にはバッジが出ない** | 自分が担当でない会話には付かない |
| **K4** | 担当が別の人に変わると、**新しい担当者側に出る**（前の担当者には出ない） | 担当を付け替えて双方で確認 |
| **K5** | **「すべて既読」では消えない**（開いたときだけ消える） | バッジ付きの会話を開かずに「すべて既読」を押す → バッジは残る |
| **K6** | **導入直後にバッジが大量発生しない** | 本番反映直後の受信箱で、既存の会話に「新規」が付いていない |

### KPI（機械で測る）

| # | KPI | 測定 |
|---|---|---|
| P1 | 追加する列は **1 本だけ** | `git diff main...HEAD -- migrations/` に `ADD COLUMN` が 1 種類だけ |
| P2 | **新しい表を作らない** | 同 diff に `CREATE TABLE` が 0 件 |
| P3 | **新しい API を作らない** | `git diff main...HEAD` に `@router.` の追加が 0 件（既存 API の拡張のみ） |
| P4 | **新しい UI 金型を作らない** | `frontend/src/components/` への新規ファイルが 0 件 |
| P5 | 新しいデザイントークンを作らない | `git diff main...HEAD -- frontend/src/index.css` が空 |
| P6 | 既存の未読バッジを触らない | `frontend/src/pages/inbox/InboxConversationRows.tsx` の `conv.unread_count > 0 && (...)` の既存3行が diff に現れない（PR-B で行番号が動くため識別子で引用） |

---

## ② 現在地（recon の要点）

| 事実 | 根拠 |
|---|---|
| `leads` に「担当になった時刻」の列は**無い**（本体21列＋追加33列を全数確認） | `migrations/003_add_phase1_tenant_tables.sql:75-98` ／ recon §2 |
| 紛らわしい `assigned_at` は **`user_roles` の列**（無関係） | `migrations/003_add_phase1_tenant_tables.sql:63-70` |
| 新テナント用の定義が**別ファイルにもある** | `backend/app/services/tenant.py:355-407` |
| **会話を開くと既に `mark-read` が呼ばれる** | `frontend/src/pages/inbox/useInboxState.ts` の `selectedLeadId` 変更時の `useEffect`（PR-B で行番号が動くため識別子） |
| その API は**空 body を既に送っている**（任意項目の追加は後方互換） | `frontend/src/lib/messages.ts` の `markRead` 関数（同上） |
| その API は**同じ処理内で `leads` の存在確認をしている** | `backend/app/routers/leads.py` の `mark_lead_messages_read`（同上） |
| **`current_user.id` は `users.id`**（ADR-1008）。`leads.assigned_to` も users.id | `mark_lead_messages_read` 内の ADR-1008 コメント（同上） ／ `backend/app/routers/analytics.py:104-114` |
| **一括既読からも `mark-read` が呼ばれる**（＝「開いた」と区別が必要） | `frontend/src/pages/inbox/useInboxState.ts` の `handleMarkAllRead` ／ `handleBulkMarkRead`（同上） |
| 会話一覧 API に `current_user` は**既に居る** | `backend/app/routers/meta_inbox.py` の `list_conversations`（同上） |
| 会話一覧は `assigned_to` を返していない | 同関数内の SELECT 句 ／ `conversations.append({...})`（同上） |
| **`Badge` 金型は既にある**（新設不要） | `frontend/src/components/Badge.tsx:16-34` |
| 既存の未読バッジは金型未使用（本 PR では置き換えない） | `frontend/src/pages/inbox/InboxConversationRows.tsx` の既存の未読バッジ JSX（同上） ／ ADR-144:66-69 |

---

## ③ 設計（How）

### 3-0. 設計の核：**列は 1 本だけで足りる**

1 件のリードに**担当者は 1 人**（`leads.assigned_to` は単一値）。
したがって「担当者ごとの表」は不要で、**「現在の担当者が開いたか」を表す 1 列**で表現できる。

```
バッジを出す条件 ＝  assigned_to が自分 かつ assignment_opened_at が未設定
担当が変わったら    assignment_opened_at を未設定に戻す（＝新しい担当者に出る）
担当者が開いたら    assignment_opened_at に現在時刻を入れる（＝消える）
```

**「担当になった時刻」の列は作らない。** 担当変更の履歴は監査記録に既に残るため
（`backend/app/routers/leads.py` の `update_lead` 内 `record_audit_log(..., old_data=dict(old_row), new_data=audit_new_data, ...)` が `assigned_to` を含める。PR-B で行番号が動くため識別子で引用）、
時刻列を別に持つのは重複になる。

### 3-1. マイグレーション（列 1 本の追加 ＋ 既存行の埋め直し）

**新規** `migrations/20261015_090000_add_leads_assignment_opened_at.sql`

手本は `migrations/20260718_100000_leads_add_deal_columns.sql`（冪等な全テナントループ）、
既存行の埋め直しの先例は `migrations/032_add_company_contact_to_downstream.sql:124`。

```sql
-- 受信箱「新規」バッジ: leads に「現在の担当者が開いた時刻」を追加（全テナント・冪等）
-- 設計: docs/handoff/inbox-new-assignment-badge/design.md §3-1
-- NULL = 現在の担当者はまだ開いていない（バッジを出す）
-- 既存行は「既に開いた」扱いで埋める（導入直後にバッジが大量発生しないようにする。KGI K6）
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS assignment_opened_at TIMESTAMPTZ',
            s
        );
        -- 既に担当が付いている既存行だけを「開いた済み」にする（冪等: NULL の行のみ）
        EXECUTE format(
            'UPDATE %I.leads SET assignment_opened_at = NOW() '
            'WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL',
            s
        );
        RAISE NOTICE 'leads.assignment_opened_at ready on %', s;
    END LOOP;
END $$;
```

**設計判断（埋め直しの方針）**: 既存行を `NOW()` で埋める。
埋めない場合、本番反映の瞬間に**担当が付いている全会話に「新規」が付く**（意味のない大量通知）。
埋めることで「**本番反映より後に担当が決まったものだけ**」にバッジが出る。
→ **PO に異存があれば埋めない版に切り替える**（SQL の `UPDATE` を 1 文消すだけ）。

**訂正（レビュー 2026-10-15 指摘・PO が migration ファイル本体を書き直し済み）**: 上記サンプルの
`WHERE assigned_to IS NOT NULL AND assignment_opened_at IS NULL` は**本番で毎デプロイ再実行される**
（`scripts/run_all_migrations.sh` は冪等性のため全件を毎回流す運用）ため、2回目以降の実行で
「担当になったがまだ開いていない」行（＝バッジを出すべき行）まで埋めてしまう欠陥があった。
実際のファイルは `information_schema.columns` で列の有無を確認し、列が既にあれば `CONTINUE` で
**丸ごとスキップ**する方式に修正されている。列が無いときだけ `ADD COLUMN`（`IF NOT EXISTS` 無し）
＋ `WHERE assigned_to IS NOT NULL`（NULL ガード無し）の埋め直しを実行する。
現物は `migrations/20261015_090000_add_leads_assignment_opened_at.sql` を参照（このファイルは
PO が直接書き直すため、上記サンプルは更新していない）。検証:
`backend/tests/test_inbox_new_assignment_badge.py` の
`test_a1_a2_column_guard_backfill_is_idempotent_across_redeploys`。

**追記（CI で実発生・2026-10-17）**: 埋め直し UPDATE は `assigned_to` 列があるスキーマだけで行う。
`leads` 表があっても `assigned_to` が無いスキーマが CI の試験用 DB に実在する
（根拠: `.github/workflows/migration-test.yml` の試験用 `tenant_001.leads` 最小定義）。
検証: `backend/tests/test_leads_assignment_opened_at_pg.py` の T5。

**実行登録**: `scripts/run_all_migrations.sh` の**末尾に追記**
```bash
# 受信箱「新規」バッジの置き場（leads に 1 列。構造＋既存行の埋め直し・冪等）
run_sql migrations/20261015_090000_add_leads_assignment_opened_at.sql
```

**新テナント用の定義も同期**: `backend/app/services/tenant.py:355-407` の
`leads` CREATE TABLE に `assignment_opened_at TIMESTAMPTZ,` を追加（recon §2-3：2 箇所同期が必須）。

### 3-2. 担当が変わったら未設定に戻す

**追加先** `backend/app/routers/leads.py` の `update_lead`（PR-B で行番号が動くため識別子で引用）。
`update_data` に `assigned_to` が含まれ、かつ `old_row["assigned_to"]` と異なるときだけ、
同じ UPDATE 文で `assignment_opened_at = NULL` も設定する。

```python
    # 受信箱「新規」バッジ: 担当が変わったら「開いた」記録を白紙に戻す（design.md §3-2）
    # 同じ人への再保存では戻さない（バッジが無駄に再出現しないため）
    reset_assignment_badge = (
        "assigned_to" in update_data
        and update_data["assigned_to"] != old_row["assigned_to"]
    )
```
UPDATE 文の組み立て（`set_clauses` を構築する箇所。PR-B で行番号が動くため識別子で引用）で
`assignment_opened_at = NULL` を**文字列として足す**（バインド不要の固定値）。
`_UPDATABLE_COLUMNS` には**加えない**（利用者が直接書き換える列ではない）。

### 3-3. 「開いた」ときだけ消す（一括既読では消さない）

`mark-read` は**開いたとき**と**一括既読**の両方から呼ばれる（recon §3-4）。
区別のため、**既存 API に任意フィールドを 1 つ追加**する。新しい API は作らない。

**変更前** `backend/app/routers/leads.py` の `mark_lead_messages_read`（PR-B で行番号が動くため識別子で引用）
```python
@router.post(
    "/leads/{lead_id}/messages/mark-read",
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def mark_lead_messages_read(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    ...
```
**変更後**
```python
class MarkReadRequest(BaseModel):
    """mark-read の任意パラメータ。

    opened=True は「会話を実際に開いた」ことを表す。受信箱の「新規」バッジを消すのは
    この場合のみ（一括既読では消さない。design.md §3-3 / KGI K5）。
    既定 False なので、フィールドを送らない既存の呼び出しは挙動が変わらない。
    """
    opened: bool = False


@router.post(
    "/leads/{lead_id}/messages/mark-read",
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def mark_lead_messages_read(
    lead_id: int,
    data: MarkReadRequest = MarkReadRequest(),
    db: AsyncSession = Depends(get_db),
    ...
```
既存の `UPDATE {meta_messages_t} ...` の**後ろ**に追加:
```python
    # 受信箱「新規」バッジ: 自分が担当の会話を開いたときだけ消す（design.md §3-3）
    if data.opened:
        await db.execute(
            text(f"""
                UPDATE {leads_t}
                SET assignment_opened_at = NOW()
                WHERE id = :lead_id
                  AND tenant_id = :tenant_id
                  AND assigned_to = :me
                  AND assignment_opened_at IS NULL
            """),
            {"lead_id": lead_id, "tenant_id": tenant_id, "me": current_user.id},
        )
```
- `assigned_to = :me` 条件により、**他人が担当の会話を開いても何も起きない**
- `assignment_opened_at IS NULL` 条件により**何度開いても最初の時刻のまま**
- `tenant_id` 条件は多重防御（`tenant_table_ref` でスキーマ修飾済みだが条件も付ける）

**フロント**: `frontend/src/lib/messages.ts` の `markRead` に任意引数を追加
```ts
export function markRead(leadId: number, opened = false) {
  return api.post<MarkReadResponse>(`/leads/${leadId}/messages/mark-read`, { opened });
}
```
`frontend/src/pages/inbox/useInboxState.ts` の `selectedLeadId` 変更時の `useEffect` 内の
**開いたときの呼び出しだけ** `true` にする（PR-B で行番号が動くため識別子で引用）。
`handleMarkAllRead` と `handleBulkMarkRead` の一括既読は**無変更**（既定 `false`）。

**追記（レビュー 2026-10-15 指摘・修正2）**: PC（非モバイル）では「未選択なら先頭会話を
自動選択する」効果（`frontend/src/pages/inbox/useInboxState.ts` 内の `isMobile` 判定の効果）があり、これが
`selectedLeadId` を立てるため、素朴な実装では開いたときの効果が自動選択でも発火し、
**自分で開いていない先頭会話のバッジが消えてしまう**。PO 決定は**案ア「自動選択では
消さない」**。対策: `autoSelectRef`（`useRef`）を自動選択の直前に立て、開いたときの
効果はこのフラグが立っていれば `opened=false` を送り、フラグを消費する。
利用者の明示操作（行クリック・URL の `lead_id` 指定での初期表示）は影響を受けず
`opened=true` のまま。自動選択の判定条件・挙動自体（PR 4165 の退行対策）は変更しない。
検証: `frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx`。

**追記（レビュー 2026-10-15 指摘・修正3）**: `frontend/src/pages/inbox/useInboxState.ts` の `markRead` ローカル
ラッパーは、`opened=true` のときだけ一覧の楽観更新に `is_new_assignment: false` を含める
（一括既読 `opened=false` では落とさない。KGI K5 を再度満たすための対応）。
`loadConversations()` は mount・絞り込み変更・送信・SSE でしか走らないため、これが無いと
スマホで会話から一覧に戻った瞬間にはバッジが消えて見えない（再読込すれば消える＝サーバ側は
正しいが、KGI K2「その場で」を満たさない）。

### 3-4. 会話一覧がバッジの有無を返す

`backend/app/routers/meta_inbox.py` の `list_conversations` 内 SELECT 句（PR-B で行番号が動くため識別子で引用）に 2 列を足す。
```sql
            l.assigned_to           AS assigned_to,
            l.assignment_opened_at  AS assignment_opened_at,
```
応答生成（`conversations.append({...})` の箇所。同上）に**計算済みの真偽値 1 つ**を足す。
```python
            # 受信箱「新規」バッジ: 自分が担当で、まだ開いていない（design.md §3-4）
            "is_new_assignment": (
                row.get("assigned_to") == current_user.id
                and row.get("assignment_opened_at") is None
            ),
```
**判断の理由**: 生の `assigned_to` をフロントに返さず、**サーバーで判定した真偽値だけ**返す。
- フロントに「自分の users.id」を持ち回る配線が不要
- **他人の担当者 ID を画面に出さない**（便3 の可視範囲制限とも整合）

フロントの型 `frontend/src/lib/messages.ts` の `Conversation` interface に追加（PR-B で行番号が動くため識別子で引用）
```ts
  /** 自分が担当になったが、まだ開いていない（受信箱の「新規」バッジ用） */
  is_new_assignment?: boolean;
```

### 3-5. 画面（既存の金型を使う・新設なし）

`frontend/src/pages/inbox/InboxConversationRows.tsx` の既存の未読バッジ JSX
（`conv.unread_count > 0 && (...)`。PR-B で行番号が動くため識別子で引用）の**隣**に追加。
既存 3 行は**触らない**（ADR-144:66-69）。

**訂正（レビュー後）**: 当初 InboxConversationList.tsx の239-241行目と記載していたが、これは別PR
（会話一覧の行描画を共通部品に分離するリファクタ）により既に `frontend/src/pages/inbox/InboxConversationRows.tsx` へ
移動済みの実装を元に書かれた誤記だった（recon時点で未検知。実装時に判明・訂正）。

```tsx
{conv.is_new_assignment && (
  <Badge variant="info" size="sm">{t("inbox.newAssignmentBadge")}</Badge>
)}
```
- `Badge` 金型（`frontend/src/components/Badge.tsx`）をそのまま使う＝**ハードコードしない**
- `variant="info"` は「お知らせ」の意味。色は金型側のトークンで決まるため**直値を書かない**
- 配置は未読数バッジと同じ行。CSS の追加は**しない**（金型の既定で成立するため）

### 3-6. i18n（ADR-027・ja/en 同一キー）

| キー | ja | en |
|---|---|---|
| `inbox.newAssignmentBadge` | 新規 | New |

`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の**両方**に追加
（`frontend/scripts/check-i18n-missing-keys.js` が片方だけだと赤にする）。

---

## ④ リスクと対策

| # | リスク | 対策 | 検証 |
|---|---|---|---|
| R1 | **導入直後にバッジが大量発生**して業務の邪魔になる | マイグレーションで既存行を「開いた済み」に埋める（§3-1） | 単体テストで既存行が埋まることを確認＋実機（K6） |
| R2 | **一括既読でバッジが消えてしまう**（PO の「開くと消える」に反する） | `opened` フラグで区別（§3-3）。一括既読は既定 `false` | 単体テスト（K5 相当） |
| R3 | 他人が担当の会話を開いて相手のバッジを消してしまう | SQL に `assigned_to = :me` 条件 | 単体テスト |
| R4 | 他人の担当者 ID が画面に漏れる | 生の `assigned_to` を返さず**真偽値だけ**返す（§3-4） | 応答に `assigned_to` が無いことをテスト |
| R5 | 既存の `mark-read` 呼び出しが壊れる | **任意フィールド・既定 False**。既存の `{}` body はそのまま通る | 既存テストが緑 |
| R6 | **新テナントに列が無い**（マイグレーションは既存テナントのみループ） | `backend/app/services/tenant.py` の CREATE TABLE にも追加（§3-1） | 2 箇所に列名があることを grep で確認するテスト |
| R7 | **マイグレーションの二重実行で壊れる** | `information_schema.columns` で列の有無を見て、列が無いときだけ `ADD COLUMN` + `UPDATE`。あれば `CONTINUE` で完全スキップ（審査 D4。現物: `migrations/20261015_090000_add_leads_assignment_opened_at.sql`） | 同じ SQL を 2 回流すテスト（`backend/tests/test_leads_assignment_opened_at_pg.py` の T3） |
| R8 | 本番適用の失敗・巻き戻し | **戻し方を ⑦ に明記**（列は残しても無害＝前方互換） | ⑦ 参照 |
| R9 | 未読バッジ（お客さまのメッセージ）と**意味が混ざる** | 別概念として別列・別条件。`unread_count` は一切触らない | コードレビュー＋実機 |

---

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 | 担当PR |
|---|---|---|---|
| A1 | マイグレーションが列を足し、既存の担当付き行を埋める | 単体テスト（実行前後の値） | **PR-A** |
| A2 | マイグレーションを 2 回流しても同じ結果（冪等） | 単体テスト | **PR-A** |
| A3 | 担当が変わると `assignment_opened_at` が NULL に戻る | 単体テスト（`PATCH /leads/{id}` で担当変更） | PR-B |
| A4 | **同じ担当者への再保存では NULL に戻らない** | 単体テスト | PR-B |
| A5 | `mark-read` に `opened=true` を送ると、**自分が担当のときだけ**時刻が入る | 単体テスト（担当が自分／他人の 2 ケース） | PR-B |
| A6 | `mark-read` に `opened` を送らない（または false）と時刻は入らない | 単体テスト（＝一括既読で消えない） | PR-B |
| A7 | 2 回開いても時刻は最初のまま | 単体テスト | PR-B |
| A8 | 会話一覧が `is_new_assignment` を返し、**自分が担当＆未開封のときだけ true** | 単体テスト（自分担当・他人担当・担当なしの 3 ケース） | PR-B |
| A9 | 会話一覧の応答に **`assigned_to` が含まれない** | 単体テスト（キーの不在を assert） | PR-B |
| A10 | 既存の `mark-read` 呼び出し（body なし）が壊れていない | 既存テストが緑 | PR-B |
| A11 | `leads` の CREATE TABLE が**2 箇所**（migration と tenant.py）で列を持つ | 単体テスト（grep 相当の静的チェック） | **PR-A** |
| A12 | 新しい表・新しい API・新しい金型・新しいトークンがゼロ | KPI P2〜P5 の diff チェック | PR-A・PR-B 各々 |
| A13 | i18n キーが ja/en 両方にある | `npm run check:i18n-missing-keys` が緑 | PR-B |
| A14 | フロントの検査が全部緑 | `npm run check:all` ／ `npm run lint`。**`check:all` は型検査（tsc）を含まないため、`npx tsc --noEmit` を別に実行する**（審査 D10） | PR-B |
| A15 | **実機**: 担当になるとバッジが出る | PO ＋ 実機（K1） | PR-B |
| A16 | **実機**: 開くと消える・再読込しても消えたまま | PO ＋ 実機（K2） | PR-B |
| A17 | **実機**: 他人担当には出ない／担当変更で新担当側に出る | PO ＋ 実機（K3・K4） | PR-B |
| A18 | **実機**: 「すべて既読」では消えない | PO ＋ 実機（K5） | PR-B |
| A19 | **実機**: 本番反映直後に既存会話へバッジが付かない | PO ＋ 実機（K6） | PR-B |

---

## ⑥ 触るファイル

```
migrations/20261015_090000_add_leads_assignment_opened_at.sql, scripts/run_all_migrations.sh, backend/app/services/tenant.py, backend/app/routers/leads.py, backend/app/routers/meta_inbox.py, backend/tests/test_inbox_new_assignment_badge.py, backend/tests/test_conversations.py, frontend/src/lib/messages.ts, frontend/src/pages/inbox/useInboxState.ts, frontend/src/pages/inbox/InboxConversationRows.tsx, frontend/src/locales/ja.json, frontend/src/locales/en.json, frontend/api-contract/openapi.json, docs/handoff/inbox-new-assignment-badge/recon.md, docs/handoff/inbox-new-assignment-badge/design.md, .claude-pipeline/active-work.d/release-inbox-new-assignment-badge.md
```

## 出し方（2段階・expand/contract）

本設計は当初 `release/inbox-new-assignment-badge` 1本（列＋読み書きコード＋画面）で出す
予定だったが、`.github/workflows/deploy.yml` を精査した結果、以下のデプロイ順序上の危険が
判明したため、**PR-A（列だけ）→ PR-B（読み書きのコードと画面）** の2段階（expand/contract）
に分割する。

### デプロイ順序の事実（`.github/workflows/deploy.yml`、行番号は PR-A 作業先 worktree で確認した値）
- `- name: Deploy to VPS (code + env + docker compose)`（:230）のステップ内で
  `bash scripts/blue-green-cutover.sh`（:418）が走り、新コードが客を受け始める。
- `- name: Run database migrations`（:547、`bash scripts/run_all_migrations.sh` を実行、:561）は
  **その後**に実行される。

### 危険
列の追加と、その列を読み書きするコード（`/api/v1/conversations` の読み・`mark-read` の書き・
担当変更の書き）を同じ PR で出すと、切替からマイグレーション完了までの間、これらが
存在しない列に触って失敗する。

### 決定（expand/contract）
- **PR-A（本 PR、先行・列だけ）**: `migrations/20261015_090000_add_leads_assignment_opened_at.sql`
  と `backend/app/services/tenant.py` の列追加のみ。読み書きのアプリコード・画面は一切含まない。
  列が増えてもアプリはまだ読み書きしないので、コードが古いまま先にデプロイされても安全
  （expand）。
- **PR-B（`release/inbox-new-assignment-badge`、PR-A マージ・本番反映後に出す）**:
  `backend/app/routers/leads.py`・`backend/app/routers/meta_inbox.py`・`frontend/` 配下の
  読み書きと画面。PR-A が本番反映済みであることが前提。
- 先例: `docs/handoff/llm-usage-ledger/design.md §9`（:89）と同じ分割方式。

### PR-A が単独で安全な根拠
- 追加列 `assignment_opened_at` は NULL 許容。
- `leads` に VIEW も TRIGGER も無い（`git grep -n "CREATE VIEW\|CREATE TRIGGER" migrations/` で
  `leads` を対象にした VIEW/TRIGGER が無いことを確認済み。`leads` に言及する既存 TRIGGER は
  いずれも `customers`/`companies`/`contacts`/`lead_playbook`/`lead_attachments` 側に定義されて
  いるものであり、`leads` 自体には無い）。
- RLS は `migrations/003_add_phase1_tenant_tables.sql:191` のテナント分離ポリシー1本のみで、
  新しい列を参照する条件は無い。

## ⑦ 戻し方（本番適用後に問題が出た場合）

**列は残したまま戻せる（前方互換）。** 列を DROP する必要はない。

| 段階 | 戻し方 |
|---|---|
| 画面だけ止める | `frontend/src/pages/inbox/InboxConversationRows.tsx` の本便で追加した `conv.is_new_assignment && (...)` バッジ描画（PR-B で行番号が動くため識別子で引用）を外す（列もデータも無害に残る） |
| API も止める | `is_new_assignment` を常に `false` で返す（1 行） |
| 全部戻す | この PR を revert。**列は残る**が参照されないため無害。`DROP COLUMN` は**行わない**（不可逆・PO 確認必須のため） |

**列を消す必要が無い根拠**: `assignment_opened_at` は NULL 許容の追加列であり、
既存の SELECT（`_LEAD_COLUMNS` 等）は列名を明示しているため、列が増えても既存処理に影響しない。

## ⑧ 削除するファイル

なし（ファイル自体の削除は無い）

## ⑨ 触らない範囲（明示）

- **新しい表を作らない**（`CREATE TABLE` はゼロ）
- **新しい API を作らない**（既存 `mark-read` に任意フィールドを 1 つ足すのみ）→ ADR-1016 の台帳登録は**不要**
- **新しい UI 金型を作らない**（既存 `frontend/src/components/Badge.tsx` を使う）
- **`frontend/src/index.css` を触らない**（新しいデザイントークンを作らない）
- **既存の未読バッジを触らない**（`frontend/src/pages/inbox/InboxConversationRows.tsx` の既存の未読バッジ JSX。PR-B で行番号が動くため識別子で引用・ADR-144:66-69 により移行は別 PR）
- **`unread_count`（お客さまのメッセージの未読）に一切触らない**
- **`DROP COLUMN` / `DROP TABLE` を書かない**
- 便3（担当者別の可視範囲）は別便。本 PR では**誰に何が見えるかを変えない**

## ⑩ 外部・過去事例の参照と我々への応用

| 出典 | 確認した内容 | 本設計への反映 |
|---|---|---|
| 自リポジトリの先例 `migrations/20260718_100000_leads_add_deal_columns.sql` | 全テナントをループして `ADD COLUMN IF NOT EXISTS` する冪等な形 | §3-1 の DO $$ ループをこの形に揃えた（自分で発明しない） |
| 自リポジトリの先例 `migrations/032_add_company_contact_to_downstream.sql:124` | 構造変更と同じマイグレーション内で既存行を `UPDATE` して埋める | §3-1 の既存行の埋め直しをこの作法に揃えた |
| 自リポジトリの先例 `backend/app/routers/leads.py` の `mark_lead_messages_read` 内 ADR-1008 コメント（PR-B で行番号が動くため識別子で引用） | 「人」の列は `public.users(id)` を参照し、`current_user.id` をそのまま入れる | §3-3 の `assigned_to = :me` 比較に `current_user.id` をそのまま使える根拠 |
| 自リポジトリの金型 `frontend/src/components/Badge.tsx:1-12` | 「ラベルは children で渡す」「ステータス値 → variant のマッピングは呼び出し側で定義すること」 | §3-5 でラベルを i18n から渡し、`variant` を呼び出し側で指定する形にした |

**注**: 上記以外の外部事例は一次情報で確認できていないため記載しない（推測で事例を書かない）。

## 維持の仕組み

守り手: PR-A は `backend/tests/test_leads_assignment_opened_at_pg.py`（T1〜T5）、
PR-B は `backend/tests/test_inbox_new_assignment_badge.py`（A3〜A10 等。PR-A の時点では
未着手のため PR-A のツリーには存在しない。`git cat-file -e HEAD:backend/tests/test_inbox_new_assignment_badge.py`
は PR-A では `does not exist in 'HEAD'` になる＝想定どおり）。

| 守るもの | 関所 | 壊れたときの症状 | 担当PR |
|---|---|---|---|
| 担当変更でバッジが復活する | `backend/tests/test_inbox_new_assignment_badge.py`（A3・A4） | リセット処理を外すと赤 | PR-B |
| **開いたときだけ消える**（一括既読で消えない） | 同上（A5・A6） | `opened` の判定を外すと赤 | PR-B |
| 他人のバッジを消せない | 同上（A5） | `assigned_to = :me` 条件を外すと赤 | PR-B |
| **他人の担当者 ID を返さない** | 同上（A9） | 応答に `assigned_to` を足すと赤 | PR-B |
| マイグレーションが冪等 | `backend/tests/test_leads_assignment_opened_at_pg.py`（T3） | `information_schema.columns` での列有無チェックや `CONTINUE` を外すと赤（審査 D4） | **PR-A** |
| `leads` 表はあるが `assigned_to` が無いスキーマでも落ちない | 同上（T5） | 埋め直し UPDATE の前に `assigned_to` の有無を確認する分岐を外すと赤（CI で実発生・2026-10-17） | **PR-A** |
| **新テナントにも列がある**（2 箇所同期） | `backend/tests/test_leads_assignment_opened_at_pg.py`（T4）／CI「テナントスキーマ整合性チェック（実行）」（`.github/workflows/schema-check.yml:48` のジョブ。`scripts/db/sync_tenant_schema.py --dry-run`〔`.github/workflows/schema-check.yml:217`〕が `information_schema.columns`〔`scripts/db/sync_tenant_schema.py:98`〕を読んで列レベルで突き合わせる） | `backend/app/services/tenant.py` の `leads` CREATE TABLE への追加を忘れると赤 | **PR-A** |
| 既存の `mark-read` 呼び出しが壊れない | 既存の受信箱テスト | 必須フィールドにすると赤 | PR-B |
| i18n キーが ja/en 揃う | `frontend/scripts/check-i18n-missing-keys.js` | 片方だけ足すと赤 | PR-B |
| API の形と台帳が一致 | CI「API contract is up to date」 | `frontend/api-contract/openapi.json` の更新忘れで赤 | PR-B |
| マイグレーションのファイル名形式 | `.github/workflows/migration-guard.yml` | 命名規則を外すと赤 | **PR-A**（本便の `migrations/20261015_090000_...` にも適用） |

**人手に残る部分**: 実機での往復確認（A15〜A19）。特に「導入直後にバッジが大量発生しないこと」は
本番データの件数に依存するため自動化していない。

---

## ⑪ 継続（この PR の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | 便3（担当者別の可視範囲・4段階） | PO 決定済み（未アサインは見せない／CRM も絞る／注文・見積・請求も対象）。**残り1問**＝たどっても担当者が分からない行の扱い |
| C2 | 既存の未読バッジの金型移行 | ADR-144:66-69 に従い別 PR |
| C3 | 本番の `assigned_to IS NOT NULL` の件数確認 | マージ後に読み取りのみで数える（recon §8 U1） |
| C4 | バッジ消去（`assignment_opened_at` の更新）が監査記録に残らない | `mark_lead_messages_read`（`backend/app/routers/leads.py`）の監査記録は未読が1件以上のとき（`marked > 0`）だけ記録され、`table_name` は `meta_messages` 固定。バッジ消去自体の別記録は無い。本便の対象外と裁定（審査 D11） |
