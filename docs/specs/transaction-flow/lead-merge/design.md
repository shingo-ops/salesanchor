# リードをまとめる 設計（design）

> この文書は何か（専門用語なしの1行）:
> リードをまとめるときに記録が1つも消えず止まらないように直し、受信箱のカルテからも開けるようにする作り方。

親（あるべき姿＋KGI）へのリンク: [README.md](./README.md)、[ideal-state.md](./ideal-state.md)、[kgi.md](./kgi.md)
決定記録: [ADR-1049](../../../adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md)（Amends ADR-119）
recon: [docs/handoff/inbox-brushup/lead-merge-recon.md](../../../handoff/inbox-brushup/lead-merge-recon.md)
日付: 2026-10-28 ／ 設計担当: Claude Opus

## 1. あるべき姿

[ideal-state.md](./ideal-state.md) の原文 1〜9（PO 2026-10-28）。

## 2. KGI

[kgi.md](./kgi.md) の K1〜K9。

## 3. KPI

達成 KGI 数 ◯/9。K1〜K7 は PR の CI で、K8 は PO の目視で、K9 は本番で最初の統合のあとに測る。

## 4. recon

[lead-merge-recon.md](../../../handoff/inbox-brushup/lead-merge-recon.md)。要点:
- 付け替えは4表だけ（`backend/app/routers/leads.py:3073-3119`）。conversation_logs は RESTRICT（`migrations/20260715_100000_add_conversation_logs_lead_fk.sql:19-22`）で、会話の記録を持つリードを消す方にすると 500。
- 統合のあと `publish_leads_update` を呼ばない（`backend/app/routers/leads.py:3157-3158`）。作成・更新・削除は呼ぶ（`backend/app/routers/leads.py:482-483`、`backend/app/routers/leads.py:711-712`、`backend/app/routers/leads.py:790-791`）。
- 受信箱は、開いている相手が消えても選択を外さない（`frontend/src/pages/inbox/useInboxState.ts:240`、外すのは自分で除外・削除したときだけ `frontend/src/pages/inbox/useInboxState.ts:983-1002`）。
- カルテ下の帯は相手が lead か existing_customer のときだけ出る（`frontend/src/pages/inbox/InboxKartePanel.tsx` ActionBar の `if (!primaryLabel) return null`）。
- 権限の判定は `frontend/src/hooks/usePermissions.ts:16`（`usePermissions()`、`hasPermission` は `:39-`）。受信箱でも `frontend/src/pages/inbox/InboxMessageThread.tsx:103` で使っている。リードの一覧は `frontend/src/pages/leads/LeadsPage.tsx:506` で `hasPermission("leads.delete") && l.status === "lead"` のときだけ統合を出す。
- 統合の窓 `frontend/src/components/MergeLeadModal.tsx` は loser を受け取り（`frontend/src/components/MergeLeadModal.tsx:36-43`）、成功で `onMerged(masterId)` を呼ぶ（`frontend/src/components/MergeLeadModal.tsx:122`）。素の `<button>` が2つ（`frontend/src/components/MergeLeadModal.tsx:247`、`frontend/src/components/MergeLeadModal.tsx:306-310`）。
- 画面の試験: `frontend/playwright.config.ts` に幅 390・768・1280 の組があり、PR のたびに frontend/tests-e2e/visual-language/*.spec.ts を全部動かす（e2e.yml の「画面検査（受信箱 3幅 Playwright）」）。押す場所 44px の値は `frontend/tests-e2e/visual-language/inbox-helpers.ts:27` `MIN_TOUCH_TARGET_PX = 44`。

## 5. design（作り方）

### 5-1 サーバー: 統合の処理（`backend/app/routers/leads.py`）

1. 統合の中身を「計画を作る関数」と「計画を実行する関数」に分ける。計画 = 各表の付け替え件数、一意の決まりで消す loser 側の件数、埋まる項目（項目名・残す方の今の値・入る値）。
2. 下見の入口 `POST /leads/{master_id}/merge/preview`（体は統合と同じ `LeadMergeRequest`、権限も同じ `leads.delete`）。計画だけを返し、書き込まない。返す形は新しい型 `LeadMergePreview`。
3. 統合 `POST /leads/{master_id}/merge` は、同じ計画を作ってから実行する。入出力の形は今のまま（`LeadResponse`）。
4. 付け替える表は recon §2 の13表。順番は「一意の決まりがある表の重複を消す → 13表の `lead_id` を付け替える → 空欄を埋める → loser を消す」。public.registration_tokens は `tenant_id` も条件に入れる。
5. 一意の決まりがある表: lead_channels（今の手順 `backend/app/routers/leads.py:3093-3119` のまま）、lead_sales_form_selections・deal_close_reasons（master に同じ組み合わせがあれば loser の行を消す）、customer_scores（master に行があれば loser の行を消す）。
6. 空欄を埋める: `_UPDATABLE_COLUMNS` から status・prospect_rank を除いた項目で、master が NULL・空文字・空の配列のとき、loser の値が空でなければ入れる。master に値があれば変えない。
7. 監査ログ merge_absorb の `new_data` に、全13表の付け替え件数と、埋めた項目名の一覧を足す（今の形 `backend/app/routers/leads.py:3136-3144` に項目を足すだけ）。
8. commit のあと、作成・更新・削除と同じ形で `publish_leads_update(tenant_id)` を呼ぶ（失敗しても統合は成功のまま。warning を残す）。
9. 13表の一覧は1か所の定数に置き、計画と実行と試験が同じ定数を読む。
10. 即時反映の登録表 `backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES` に、下見 `("POST", "/api/v1/leads/{master_id}/merge/preview")` を足す。理由の値は、ほかの下見（例 `/api/v1/conditions/import/preview`）と同じ `_PENDING`。足さないと `backend/tests/test_realtime_topics.py` の `test_every_write_route_is_in_exactly_one_table` が落ちる。統合の行（`("POST", "/api/v1/leads/{master_id}/merge")`）は `_PENDING` のまま変えない。リードの知らせは、作成・更新・削除と同じく登録表の外の `publish_leads_update` で出すため（作成・更新・削除の行も `_PENDING`）。

### 5-2 画面: 統合の窓（`frontend/src/components/MergeLeadModal.tsx`）

1. 確認の段（stage "confirm"）で下見を呼び、「残す方へ移るもの」（付け替え件数が1以上の表を、日本語の名前で）と「空いている欄に入る内容」（項目名・入る値）を出す。下見の失敗はその場で文言を出し、統合のボタンを押せないようにする。
2. 素の `<button>` 2つ（やめる・戻る）を金型 `Button` にする。
3. 文言から「audit_logs」をなくし、PO の見本（[画面見本](https://claude.ai/artifact/WLba4Mv3Ktfepb5g546pyC)）の言葉にそろえる。ja.json と en.json の `mergeLead` のキーを §5-6 の表のとおりに直し・足す。
4. 色・大きさは var(--…) だけ。新しい直書きを足さない。

### 5-3 画面: 受信箱のカルテ（`frontend/src/pages/inbox/InboxKartePanel.tsx`、`frontend/src/pages/inbox/useInboxState.ts`）

1. ActionBar の「⋯」メニューの一番下に「ほかのリードとまとめる」を足す。出す条件は `hasPermission("leads.delete") && status === "lead"`（一覧と同じ条件）。今のメニューの作り（`karte-overflow-menu`・`karte-overflow-item`）に足す。
2. 押すと MergeLeadModal を開き、開いている相手を loser として渡す。
3. 成功したら（`onMerged(masterId)`）: 窓を閉じる → 受信箱の一覧から loser を外す → 残す方を選び直す（`selectLead(masterId)`）→ 一覧を取り直す。この処理は useInboxState に1つ置き、カルテには関数として渡す。
4. メニュー項目の高さが 44px 未満なら、InboxPage.css の `.karte-overflow-menu button` に金型 ContextMenu と同じ値（`var(--size-icon-btn-lg)`）を最小の高さとして入れる。
5. ContextMenu への作り替えはしない。理由は §6。

### 5-4 大きさの基準（PO の懸念「本番で大きさがずれる」への答え）

- 見本の HTML の数字は使わない。大きさはすべて今の決まった値（デザイントークン）と金型から取る。
- 見本の比較（[evidence/size-compare.md](../../../handoff/inbox-brushup/evidence/size-compare.md)）では、SA の押す場所（44〜48px）と文字は、見本より押しやすく大きい側にある。今回の画面はこの値をそのまま使う。
- 守る数: 幅 390 で、メニュー項目と窓のボタンの高さ 44px 以上、横のはみ出し 0px。変更したファイルの直書きの色・大きさ 0件。

### 5-5 試験

1. サーバー backend/tests/test_lead_merge_pg.py（新規。既存の PostgreSQL を使う試験と同じ形）:
   - 13表それぞれに loser の行を1件置いて統合 → 200、13表で `lead_id = loser` が 0件（13件）
   - 会話の記録を持つ loser（K1）、添付と販売形態の選択の行数が変わらない（K3）
   - 空欄埋め2件（K4）、残す方の番号が変わらず loser は 404（K5）
   - 一意の決まりの重複4件（lead_channels・lead_sales_form_selections・deal_close_reasons・customer_scores）
   - 下見が書き込まないこと1件、下見と実行の件数が一致すること1件
   - 異常系3件（自分自身・loser が lead でない・無い番号）
   - 漏れの見張り1件（静的な検査。DB を使わない）: `backend/app/services/tenant.py` と migrations/ 配下の SQL の本文から、`lead_id` 列を作る表（CREATE TABLE の中の `lead_id` 列と、`ALTER TABLE … ADD COLUMN … lead_id`）の表名を集める。その集合から「後で消された表」の除外の一覧（表名と DROP の migration のファイル名を対で持つ）を引いたものが、13表の定数と一致する。集めた表名と除外の一覧は実装の担当が報告に全部出し、設計担当が確かめる。
   - 試験の DB の作り方: `scripts/check_test_schema_dup.py` が試験の中の CREATE TABLE を止めるので、表は手で書かない。手本は `backend/tests/test_permission_resolution_pg.py`（`backend/tests/rls_bootstrap.py` の `bootstrap_tenant_schema` で `backend/app/services/tenant.py` の本物の定義からテナントを作り、`_apply_migration_on_conn` で migration を流す）。API の呼び方の手本は `backend/tests/test_priority_prospects_pg_rls.py:103,137-139`。13表のうち作られない表があれば、その表を作る migration を `_apply_migration_on_conn` で流す。統合は API（`POST /api/v1/leads/{master_id}/merge`）を呼んで確かめる。
2. 画面 frontend/tests-e2e/visual-language/inbox-lead-merge.spec.ts（新規。`frontend/tests-e2e/visual-language/inbox-helpers.ts` の作り物のデータを使う。幅 390・768・1280 で動く）:
   - 権限ありで「ほかのリードとまとめる」が出る／権限なしで出ない（K6）
   - 幅 390 でメニュー項目・窓のボタンの高さ 44px 以上、`scrollWidth <= clientWidth`（K7）
   - 手順1〜3の写真を `testInfo.attach` で残す（3幅×3枚＝9枚が出る。K8 で PO に見せるのは幅 390 と 1280 の6枚。幅 768 の3枚は記録だけ。PR の「visual-language-report」から取り出す）

### 5-6 文言（ja.json / en.json の `mergeLead`）

直すキー:

| キー | ja | en |
|---|---|---|
| title | リードをまとめる | Merge leads |
| reasonLabel | まとめる理由（任意・記録に残ります） | Reason (optional, kept in the record) |
| confirmWarning | 元に戻せません | This cannot be undone |
| confirmDesc1 | 「{{sourceName}}」の記録は、すべて「{{masterName}}」へ移ります。 | All records of "{{sourceName}}" will move to "{{masterName}}". |
| confirmDesc3 | この操作は記録に残ります。 | This action is kept in the record. |
| executeLabel | 「{{masterName}}」へまとめる | Merge into "{{masterName}}" |

足すキー:

| キー | ja | en |
|---|---|---|
| menuLabel | ほかのリードとまとめる | Merge with another lead |
| movedTitle | 残す方へ移るもの | Moving to the kept lead |
| filledTitle | 空いている欄に入る内容 | Blank fields to be filled |
| nothingToFill | 埋まる欄はありません | No blank fields will be filled |
| previewError | 中身を確かめられませんでした。もう一度お試しください。 | Could not load the preview. Please try again. |
| tables.companies | 会社 | Companies |
| tables.contacts | 担当者 | Contacts |
| tables.meta_messages | メッセージ | Messages |
| tables.lead_channels | 窓口 | Channels |
| tables.conversation_logs | 会話の記録 | Conversation logs |
| tables.quotes | 見積 | Quotes |
| tables.deal_close_reasons | 成約・失注の理由 | Close reasons |
| tables.lead_attachments | 添付ファイル | Attachments |
| tables.lead_sales_form_selections | 販売形態の選択 | Sales form selections |
| tables.message_labels | メッセージの分類 | Message labels |
| tables.customer_scores | 顧客スコア | Customer scores |
| tables.outbound_translation_drafts | 翻訳の下書き | Translation drafts |
| tables.registration_tokens | 登録リンク | Registration links |

- 「空いている欄に入る内容」の項目名は、今ある文言のキー（リードの一覧・カルテの見出し）を使う。無い項目だけ `mergeLead.fields.<列名>` を足し、日本語はカルテの見出しと同じ語にする。足したキーは報告に全部出す。
- ja と en のキー数は一致させる（PR のチェック欄）。

## 6. 弊害・トレードオフ

- 消す方式のままにする: 消した番号を開くと 404 になる。消さずに印を付ける方式は、leads を読むすべての経路に条件が要るので採らない（ADR-1049 Why）。
- 下見の入口を1つ増やす: 入口は増えるが、空欄の規則を画面に二重に持たずに済む。
- ContextMenu に作り替えない: 今のメニューは、発行した登録リンクをメニューの中に出す（ContextMenu には項目以外を出す型が無い）。作り替えると登録リンクの出し方が変わり、今回の目的から外れる。金型から外れた作りは残るので、別の回で扱う（議事録 §3 に足す）。
- 確認画面に loser の値を出す: 権限のある人だけが見る画面なので、今の一覧で見られる値と同じ範囲。
- 統合は戻せない: 監査ログの控えから手で戻すだけ。確認画面で「元に戻せません」を出す。

## 7. 外部・過去事例

- HubSpot の統合（https://knowledge.hubspot.com/records/merge-records 、2026-10-28 取得）: 残す方の値を優先し、空なら消える方の値を使う。両方の記録と関連は残す方に出る。→ 空欄だけ埋める決定と、13表を全部付け替える方針の根拠。
- 過去の SA: リードの一覧の統合（ADR-119、#1752）は会話の記録の結び付き（2026-07-15）より前に作られ、その後直されなかった。→ 表を足したときに付け替えの漏れを見つける見張り（§5-5 の漏れの見張り）を入れる。

## 8. 受入基準

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | K1〜K5 | backend/tests/test_lead_merge_pg.py が全件合格（PR の CI） |
| A2 | K6・K7 | inbox-lead-merge.spec.ts が幅 390・768・1280 で合格（PR の「画面検査（受信箱 3幅 Playwright）」） |
| A3 | 直書き 0件 | 「Lint & Dark Mode Check (ADR-067)」が合格 |
| A4 | K8 | PR の写真9枚のうち、幅 390 と 1280 の手順1〜3の6枚を PO が見て合格 |
| A5 | K9 | 本番反映の後、設計担当（Claude Opus）が受信箱の見直しの各回の始めに、reader 鍵の道で監査ログの merge_absorb の件数を見る。1件以上になった最初の回に、4表の迷子を数えて 0件 |

## 9. 維持の仕組み

守り手: .github/workflows/e2e.yml と CI（バックエンドの試験・「画面検査（受信箱 3幅 Playwright）」・「Lint & Dark Mode Check (ADR-067)」）。中身は下の3つ。

- 守り手（機械）: backend/tests/test_lead_merge_pg.py の漏れの見張り（静的な検査）。`backend/app/services/tenant.py` か `migrations/` に `lead_id` を持つ表が足されると、13表の定数と合わず CI が落ちる。
- 守り手（機械）: `backend/tests/test_realtime_topics.py` が、下見の入口が登録表に載っていることを確かめる。
- 守り手（機械）: frontend/tests-e2e/visual-language/inbox-lead-merge.spec.ts が PR ごとに 44px とはみ出しを測る。
- 守り手（機械）: 「Lint & Dark Mode Check (ADR-067)」が直書きを止める。

## 10. 接触面分析

- ① 人: 受信箱を使う担当者のうち、リードを消す権限がある人だけに新しい項目が出る。リードの一覧の統合も、確認画面の中身が増える。
- ② エージェント: 本書・ADR-1049・議事録を読む。並行の作業: 受信箱・カルテ・統合を触る作業は登録簿に無い（2026-10-28 確認）。
- ③ 機械: 新しい試験2本が既存の CI（バックエンドの試験・「画面検査（受信箱 3幅 Playwright）」）で動く。CI の設定は変えない。
- ④ データ: 表の作りは変えない（migration なし）。書き込みは統合を押したときだけ。tenant_004 の統合は 0 回で、既存の行は変わらない。
- ⑤ 本番: 通常のデプロイで出る。止める設定は無い。戻すときは PR を戻す。
- ⑥ 外部: 外部の API は使わない。登録リンク（public.registration_tokens）は付け替わるので、loser 宛てに出したリンクは残す方の会社名で開く。

## 設計審査（Architect・同一 AI による自己審査。独立した第二者の審査ではない）

判定: **APPROVE（設計合格）**
- 既存の仕様・ADR との整合: ADR-098（手で寄せる）・ADR-095（写さず1か所。空欄埋めは残す方の行への1回の書き込みで、二重持ちではない）・ADR-119（本 ADR で改める）と食い違わない。
- 根拠: サーバーと画面の要所はすべて ファイル:行（lead-merge-recon.md）。本番の数は reader 鍵の道。
- 受入基準: すべて試験か PO の目視で ○× が付く。
- 実装範囲: §5 の6ファイル＋即時反映の登録表 `backend/app/realtime/topics.py`＋文言2ファイル＋試験2本。DB の形は変えない。
- 再審査（2026-10-29）: 審査役（reviewer・opus）の REQUEST_CHANGES 11件を反映（下見の登録表・削除するファイルの欄・漏れの見張りを静的な検査に統一・文言 §5-6・行番号・K6/K8/K9）。
- 未解決: migration の中の結び付きの行番号（recon §2 の未確認）は実装の担当が着手時に確かめる。結果が評価記録と違えば止まって報告させる。
