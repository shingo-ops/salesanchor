# 現在地: 受信箱カルテを住所から開いたときの最初のタブ

- 作成: 2026-11-24（Opus）。根拠は origin/main（650005f29 以降・fetch 後）の実物
- 既存 ADR の検索: `git grep -il karte origin/main -- docs/adr/` の当たりのうち、カルテのタブを決めるのは `docs/adr/ADR-1089-inbox-karte-stage-layout.md`（段階ごとのタブと最初に開くタブ）。ほか ADR-108・ADR-110・ADR-1086 は並びと幅・見た目で、最初のタブは決めていない。`docs/adr/FEATURE-INDEX.md:42` の受信箱の行が ADR-1089 を含む

## 1. 本番の観測（2026-11-24・テナント001・テストデータ）

- テストデータ: `docs/handoff/inbox-karte-test-data/insert.sql`（PO が `docs/handoff/inbox-karte-test-data/run-insert.sh` で投入。リード 951=lead・952=negotiating・953=follow_up_short、送信メッセージ tst-karte-1〜3）
- `/lead-chat?lead_id=951` → タブ「商談・連絡先」、商談が選ばれている（設計どおり）
- `/lead-chat?lead_id=952` → タブ「商談・連絡先」、商談が選ばれている（設計どおり）
- `/lead-chat?lead_id=953` → タブ「顧客・連絡先・商談」の順は正しいが、商談が選ばれている（設計は顧客）

## 2. コードの事実

- `frontend/src/pages/inbox/useInboxState.ts:220-223` 住所の `lead_id` を `initialLeadId` に読む
- `frontend/src/pages/inbox/useInboxState.ts:253` `selectedLeadId` の初めの値が `initialLeadId`
- `frontend/src/pages/inbox/useInboxState.ts:267` `karteTab` の初めの値が `"deal"`
- `frontend/src/pages/inbox/useInboxState.ts:379-380` カルテの中身 `leadDetail` を `/leads/<id>` から読む
- `frontend/src/pages/inbox/useInboxState.ts:656-658` 一覧で押したとき（`selectLead`）だけ `getKarteLayout(conv?.lead_status).tabs[0]` をタブに入れる
- `frontend/src/pages/inbox/useInboxState.ts:698-728` `selectedLeadId` が変わったときの効果。メッセージ・既読・カルテを読むが、タブは決めない
- `frontend/src/pages/inbox/InboxKartePanel.tsx:125-127` タブの並びは `getKarteLayout(leadDetail?.status)`、選ぶタブは `resolveKarteTab(karteLayout, karteTab)`
- `frontend/src/pages/inbox/karteLayout.ts:125` `resolveKarteTab` は今のタブがその段階にあればそのまま返す。成約後の並びにも `deal` があるので `"deal"` のまま残る
- `backend/app/routers/meta_inbox.py:877` 一覧は最後のメッセージが新しい順に 50 件だけ読む（一覧に無い会話もありうる）
- `backend/app/services/customer_reply_notifier.py:58` お客さんの返信の知らせの住所が `/lead-chat?lead_id={lead_id}`（利用者がこの不具合に当たる道）

## 3. 今ある試験

- `frontend/src/pages/inbox/karteLayout.test.ts`（段階ごとの並び）
- `frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx`・`frontend/src/pages/inbox/useInboxState.cache.test.tsx`（フックの試験の作法。vi.mock と renderHook）
- `frontend/tests-e2e/karte-visual-gate.spec.ts`（CI「Karte Visual Gate」・一覧から開く場合）
- 住所から開いたときの最初のタブを確かめる試験は無い

## 4. 未確認

- なし（原因は本番の観測とコードの行で一致）
