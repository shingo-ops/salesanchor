# 受信箱カルテ: 住所から開いたときの最初のタブ（ADR-1089 の直し）

- 状態: 設計案作成済み（2026-11-24）。PO 承認「1」（2026-11-24 チャット「直す」）
- 関係する決まり: `docs/adr/ADR-1089-inbox-karte-stage-layout.md`（表「最初に開くタブ」成約後＝顧客）
- 前の設計: `docs/handoff/inbox-karte-stage-tabs/design.md`（K4「最初に顧客が開く」）
- 現在地: `docs/handoff/inbox-karte-test-data/recon.md`（本番の観測・コードの行・今ある試験）

## 1. 目的（PO の言葉）

「直す」（2026-11-24）。お客さんの返信の知らせから成約後の会話を開くと、カルテが「商談」から開く。設計どおり「顧客」から開くようにする。

## 2. 本番で見たこと（2026-11-24 21:0x JST・テナント001・テストデータ TST-KARTE-1〜3）

| 開き方 | 段階 | 最初に開いたタブ | 設計 |
|---|---|---|---|
| 住所 `/lead-chat?lead_id=951` | リード | 商談 | 商談 ○ |
| 住所 `/lead-chat?lead_id=952` | 商談中 | 商談 | 商談 ○ |
| 住所 `/lead-chat?lead_id=953` | 追客（短期） | 商談 | 顧客 × |
| 一覧で押す（前の確認・Akane） | 既存顧客 | 顧客 | 顧客 ○ |

## 3. 原因（コードの事実）

- 最初のタブを段階で決めるのは、一覧で押したときの `selectLead` だけ（`frontend/src/pages/inbox/useInboxState.ts:656-658`）。
- 住所の `lead_id` から開くときは `selectLead` を通らず、`selectedLeadId` の初めの値になるだけ（`frontend/src/pages/inbox/useInboxState.ts:220-223`・`:253`）。タブは初めの値 `"deal"` のまま（`frontend/src/pages/inbox/useInboxState.ts:267`）。
- カルテは `resolveKarteTab` で、今のタブがその段階にあればそのまま使う（`frontend/src/pages/inbox/InboxKartePanel.tsx:126-127`・`frontend/src/pages/inbox/karteLayout.ts:125`）。成約後にも「商談」があるので、「商談」のまま開く。
- 住所つきで開く道: お客さんの返信の知らせ（`backend/app/services/customer_reply_notifier.py:58`）。

## 4. 成功条件

| # | 基準 | 検証方法 |
|---|---|---|
| U1 | 住所の lead_id で成約後（existing_customer・follow_up_short・follow_up_long）を開くと、最初のタブが「顧客」 | 新しい部品の試験（下の §6）。本番で `/lead-chat?lead_id=953` を開いて「顧客」が選ばれている写真 |
| U2 | 住所の lead_id でリード・商談中を開くと「商談」のまま | 同じ試験。本番で 951・952 |
| U3 | 住所で開いたあと、利用者がタブを押して変えたら、そのタブのまま（あとから戻されない） | 同じ試験（カルテが届いたあとに setKarteTab("contact") → 次の再描画でも contact） |
| U4 | 一覧で押したときの動きは変わらない | 今の試験がそのまま緑（`frontend/src/pages/inbox/karteLayout.test.ts`・`frontend/src/pages/inbox/useInboxState.autoSelectBadge.test.tsx`・CI「Karte Visual Gate」） |
| U5 | 触るのは `frontend/src/pages/inbox/useInboxState.ts` と新しい試験 1 本だけ。CSS・翻訳・backend は触らない | `git diff origin/main --name-only` |

## 5. 作り方

- 住所から開いた会話のカルテ（`leadDetail`）が初めて届いたとき 1 回だけ、`getKarteLayout(leadDetail.status).tabs[0]` を入れる。
- 段階はカルテの中身（`leadDetail.status`）から読む。一覧は最新 50 件しか読まないので、一覧に無い古い会話でも正しく決まるため（`backend/app/routers/meta_inbox.py:877`）。カルテのタブの並びも同じ `leadDetail.status` を読む（`frontend/src/pages/inbox/InboxKartePanel.tsx:126`）。
- 1 回だけにするため、印（`useRef`）を持つ。利用者が一覧で別の会話を押したら（`selectLead`）、印を下ろす。
- 段階の一覧は `frontend/src/pages/inbox/karteLayout.ts` の 1 か所のまま。新しく書かない（ADR-1089 What 4）。

## 6. 代わりの案

- 案B: `selectedLeadId` が変わるたびにカルテ到着でタブを決め直す → 一覧で押したときの `selectLead` と二重になる。選ばない。
- 案C: 一覧（conversations）から段階を読む → 一覧に無い古い会話で決まらない。選ばない。

## 7. 危ないことと対処

- カルテの再読み込み（保存のあと等）でタブが戻される → 印で 1 回だけにする（U3 で試験）。
- 戻し方: この PR を戻す（revert）。データには触らない。

## 外部・過去事例の参照と我々への応用

外部事例は使わない。1 つの画面の初めの値の直しで、根拠はコードと本番の観測で足りるため。

## 維持の仕組み

- 守り手: 新しい部品の試験 `frontend/src/pages/inbox/useInboxState.karteTabFromUrl.test.tsx` が CI で毎回流れる（U1〜U3）。
- 本番のテストデータ TST-KARTE-1〜3 で直したあとに確かめ、そのあと `docs/handoff/inbox-karte-test-data/rollback.sql` で消す（PO の同意のあと）。
