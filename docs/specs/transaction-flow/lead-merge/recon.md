# リードをまとめる 現状把握（recon）

> この文書は何か（専門用語なしの1行）:
> リードをまとめる機能が今どう作られているかを、ファイルと行で記録したもの。

親（表紙）へのリンク: [README.md](./README.md)
基準: origin/main 5b3162403（2026-10-28）。本番の数は reader 鍵の道で読むだけ（2026-10-28 22:18〜22:54 JST、tenant_004）。
詳しい独立評価: [docs/handoff/inbox-brushup/evidence/lead-merge-review.md](../../../handoff/inbox-brushup/evidence/lead-merge-review.md)

ラベル: 【事実】= ファイル:行か本番の数で確かめた ／【未確認】= 確かめていない

## 1. サーバー側の統合の処理【事実】

- 入口: `backend/app/routers/leads.py:2991-2995` `POST /leads/{master_id}/merge`、権限 `require_permission("leads.delete")`
- 受け取る形: `backend/app/routers/leads.py:2986-2988` `LeadMergeRequest{loser_id, reason}`
- loser の条件: `backend/app/routers/leads.py:3063-3064` `if loser_row["status"] != "lead":` → 400
- 付け替え: companies（`leads.py:3073-3076`）、contacts（`leads.py:3078-3081`）、meta_messages（`leads.py:3084-3087`）、lead_channels（重複は先に削除 `leads.py:3093-3119`）の4表だけ
- 削除: `backend/app/routers/leads.py:3121-3125` `DELETE FROM {leads_t} WHERE id = :loser`
- 監査ログ: `backend/app/routers/leads.py:3135-3155` merge_absorb（master の旧値と付け替え件数）・merge_delete（loser の全項目）
- 後始末: `backend/app/routers/leads.py:3157-3158` commit とダッシュボードの控えの破棄。`publish_leads_update` は呼ばない
- 画面で直せる項目の一覧: `backend/app/routers/leads.py:80-93` `_UPDATABLE_COLUMNS`（status・prospect_rank・sales_form を含む）
- 失敗時の表示: 例外は共通の処理で 500「データベースエラーが発生しました。」（`backend/app/main.py:796-803`）

## 2. リード番号を持つ表（13表）と、今 loser を消したときの結果【事実】

| 表 | 結び付きの決まり（出典） | 今の統合 | loser を消すと |
|---|---|---|---|
| companies | FK・NOT NULL（`backend/app/services/tenant.py:203,448`） | 付け替える | 移る |
| contacts | FK（`backend/app/services/tenant.py:241,457`） | 付け替える | 移る |
| meta_messages | FK ON DELETE SET NULL（`backend/app/services/tenant.py:1025`） | 付け替える | 移る |
| lead_channels | FK ON DELETE CASCADE（`backend/app/services/tenant.py:1047`） | 付け替える | 移る |
| conversation_logs | FK ON DELETE RESTRICT（`migrations/20260715_100000_add_conversation_logs_lead_fk.sql:19-20`） | 付け替えない | **削除が止まり 500** |
| quotes | FK（`backend/app/services/tenant.py:798`） | 付け替えない | 行があれば止まる |
| deal_close_reasons | FK・UNIQUE(lead_id, reason_id)（`backend/app/services/tenant.py:835,838`） | 付け替えない | 行があれば止まる |
| lead_attachments | FK ON DELETE CASCADE（`migrations/20260902_100000_create_lead_attachments.sql`） | 付け替えない | 黙って消える |
| lead_sales_form_selections | FK ON DELETE CASCADE（`migrations/20260614_100000_create_sales_form_tables.sql`） | 付け替えない | 黙って消える |
| message_labels | FK なし（`migrations/20260604_180000_analytics_agent_a_tables.sql`） | 付け替えない | 迷子 |
| customer_scores | FK なし・UNIQUE(lead_id)（`migrations/20260604_180000_analytics_agent_a_tables.sql`） | 付け替えない | 迷子 |
| outbound_translation_drafts | FK なし（`migrations/20260604_220000_create_translation_glossary.sql`） | 付け替えない | 迷子 |
| public.registration_tokens | FK なし（`migrations/20260604_080000_create_registration_tokens.sql`） | 付け替えない | 迷子 |

- 【未確認】上の migration の中で結び付きを決めている行（行番号）は、本書では開いていない。決まりの中身は評価記録（evidence/lead-merge-review.md §1-2）が本番の `pg_constraint` で確かめた値。実装の担当が着手時に行を確かめる。
- 受信のとき会話の記録を書く: Meta `backend/app/routers/webhook.py:873-886`、Discord `dm_writer.py:231-243`（評価記録の記載）。受信で生まれた新しいリードは会話の記録を持つ → 統合の本来の使い道で止まる。

## 3. 本番の数（tenant_004）【事実】

- 統合の記録 0 件。リード 56 件（全部 status=lead）。窓口の記録があるリード 4 件。会話の記録を持つリード 4 件。
- FK の無い4表の迷子 0 件（統合が 0 回だから）。

## 4. 画面側【事実】

- 統合の窓: `frontend/src/components/MergeLeadModal.tsx`。loser を受け取る形（`MergeLeadModal.tsx:35-43`）。送信は `MergeLeadModal.tsx:118`。呼び出し元はリードの一覧の1か所。
- 受信箱のカルテ下の帯: `frontend/src/pages/inbox/InboxKartePanel.tsx:261`（ActionBar）、`InboxKartePanel.tsx:370-375`（相手が lead / existing_customer のときだけ出す）、「⋯」は手作りの並び（`InboxKartePanel.tsx:385-430`）
- スマホではカルテが画面いっぱいに開く: `frontend/src/pages/inbox/InboxPage.css:1332-1350`
- 金型のメニュー: `frontend/src/components/ContextMenu.tsx`（項目の型 `{key,label,icon?,onSelect,danger?}`、区切り線の型は無い）
- 文言に「audit_logs」が出る: `frontend/src/locales/ja.json:2339,2345`
- 画面側の詳しい調べ（権限の判定・選択中の会話の扱い・写真の試験）は §5。

## 5. 画面側の詳しい調べ

基準は同じ origin/main 5b3162403。調べの生の記録は設計担当の作業メモ（作業場所の外）にある。ここには設計に使う事実だけを写す。

### 5-1 権限の判定【事実】
- `frontend/src/hooks/usePermissions.ts:15` `usePermissions()`。`/me/permissions` を取り（`:22`）、`hasPermission(key)` で判定する（`:41-44`）。
- リードの一覧での使い方: `frontend/src/pages/leads/LeadsPage.tsx:122`、統合を出す条件 `LeadsPage.tsx:506` `hasPermission("leads.delete") && l.status === "lead"`。
- 受信箱（`frontend/src/pages/inbox/` 配下）では使っていない（`hasPermission|usePermissions|leads.delete` で検索して該当なし）。
- サーバー: `backend/app/routers/leads.py:763`（削除）と `leads.py:2994`（統合）が `require_permission("leads.delete")`。

### 5-2 統合の窓【事実】
- props: `frontend/src/components/MergeLeadModal.tsx:36-43`（`open`・`source{id,lead_code,customer_name}`・`onMerged(masterId)`・`onCancel`）。2段（select・confirm）`MergeLeadModal.tsx:55`。
- 残す方の候補: `MergeLeadModal.tsx:76-80` で `GET /leads?per_page=100&search=`。自分自身は除く（`:84`）。
- 送信 `:118`、成功で `onMerged(selected.id)`（`:122`、窓は親が閉じる）。
- 素の `<button>`: `:247`（やめる）、`:306-310`（戻る）。ほかは金型 `Button`（`:250`、`:313`）。style の直書きはすべて `var(--…)`。
- 文言: `frontend/src/locales/ja.json:2332` `mergeLead`。
- 呼び出し元: `frontend/src/pages/leads/LeadsPage.tsx:551-558` の1か所。

### 5-3 カルテ下の帯【事実】
- 呼び出し `frontend/src/pages/inbox/InboxKartePanel.tsx:261-266`（`leadDetail.status`・`leadDetail.id` を渡す）。本体 `InboxKartePanel.tsx:331` `ActionBar`。
- 「⋯」の中身 `InboxKartePanel.tsx:392` `karte-overflow-menu`: 登録リンクを作る2項目、既存顧客だけの1項目、作ったリンクを出す欄（`karte-overflow-link`）。項目は素の `<button className="karte-overflow-item">`。
- CSS: `frontend/src/pages/inbox/InboxPage.css:1478`（帯）〜`:1533`（`.karte-overflow-menu button`）。
- 【未確認】「⋯」とメニュー項目の高さが 44px 以上か（既存の試験は帯が画面の中にあることだけを見る `inbox-single-column.spec.ts:1496-1520`）。

### 5-4 受信箱の選択と更新【事実】
- 選択は state が正で URL に写す: `frontend/src/pages/inbox/useInboxState.ts:240`（初期値 `:210` の `lead_id`）。`selectLead` が `:619-621` で URL を書く。
- 更新のきっかけは会話の知らせ（`useInboxState.ts:536` → `frontend/src/hooks/useInboxSSE.ts:14` `/api/v1/conversations/stream`）と定期の取り直し（`useInboxState.ts:547-575`）。リードの知らせ（`/api/v1/leads/stream`）は受けない（受けるのは `LeadsPage.tsx:185-187` だけ）。
- 選択中の相手が一覧から消えても選択は外れない。外すのは自分で除外・削除したとき（`useInboxState.ts:983-1002`）だけ。消えた相手を開いたままだと会話の取得が 404 で「Lead not found.」になる（`:648-660`）。

### 5-5 知らせの送り方【事実】
- `backend/app/services/sse_pubsub.py:108` `publish_leads_update(tenant_id)`。作成・更新・削除は commit の後に関数の中で import して呼び、失敗は warning（`leads.py:482-483`、`:711-712`、`:790-791`）。統合は呼ばない（`:3157-3158`）。

### 5-6 画面の試験と直書きの検査【事実】
- `frontend/playwright.config.ts`: `vl-mobile-390`（390x844）・`vl-tablet-768`・`vl-desktop-1280` が `visual-language/*.spec.ts` を動かす。
- `.github/workflows/e2e.yml`: PR で `npm run test:e2e:vl`（`frontend/package.json:14`）。まとめの名「画面検査（受信箱 3幅 Playwright）」。報告は artifact `visual-language-report`。
- 道具: `frontend/tests-e2e/visual-language/inbox-helpers.ts`（`MIN_TOUCH_TARGET_PX = 44` `:27`、`baseMocks` `:29`、`openInboxListWithLeadStatus` `:128`）。44px の前例 `inbox-single-column.spec.ts:454`。写真は `testInfo.attach`（`inbox-baseline.spec.ts:121-122`）。
- 直書きの検査: `npm run check:all`（`frontend/package.json:46`、まとめの名 `Lint & Dark Mode Check (ADR-067)`）。TSX の style は `frontend/eslint.config.js:40` が hex・opacity・zIndex の数を止める。
- 【未確認】素の `<button>` を止める lint の決まりの有無。
