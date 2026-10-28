# ADR-1049: リードの統合は13表すべてを付け替え、残す方の空欄だけを埋め、受信箱のカルテからも開ける

Amends ADR-119

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-28・実装前） |
| 備考 | PO 2026-10-28 の発言：「受信箱でも統合できるように出来ない？使用頻度は少ないからあまり使わないところにしまっておきたい」「1. 空いている欄だけ埋める。」「1,これで決定する」「決めた内容を記録に残してクローンの大きさを測り、作る」 |
| 起案日 | 2026-10-28 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-119（統合の元の決定。本 ADR で改める）、ADR-098（自動で同一人物と判定しない）、ADR-095（同じ事実は1か所）、ADR-096（顧客は永続）、ADR-067（デザイントークン） |
| 設計 | `docs/specs/transaction-flow/lead-merge/design.md`、現状 `docs/handoff/inbox-brushup/lead-merge-recon.md` |

---

## What（何を決めたか）

1. 統合（`POST /leads/{master_id}/merge`）は、`lead_id` を持つ13表すべてを、消える方（loser）から残す方（master）へ付け替えてから loser を消す。13表は companies・contacts・meta_messages・lead_channels・conversation_logs・quotes・deal_close_reasons・lead_attachments・lead_sales_form_selections・message_labels・customer_scores・outbound_translation_drafts・public.registration_tokens。
2. 一意の決まりがある表（lead_channels・lead_sales_form_selections・customer_scores・deal_close_reasons）は、master に同じ行があれば loser の行を消してから付け替える。
3. master の項目が空（NULL・空文字・複数選択の項目では空の配列）のときだけ、loser の値で埋める。対象は画面で直せる項目の一覧（`_UPDATABLE_COLUMNS`）から status と prospect_rank を除いたもの。master に値がある項目は変えない。
4. 同じ処理を「下見」として、書き込まずに結果（各表の付け替え件数・埋まる項目）だけ返せるようにする。統合の窓の確認画面はこの下見を表示する。画面側で同じ規則を持たない。
5. loser の条件は ADR-119 の `converted_deal_id IS NOT NULL` を改め、`status != 'lead'` なら 400 とする（deals の表は廃止済み）。
6. 統合のあと、他の画面へ「リードが変わった」を知らせる（`publish_leads_update`）。
7. 受信箱のカルテ下の「⋯」メニューに「ほかのリードとまとめる」を足す。開いている相手が loser になり、master を選ぶ。PC とスマホは同じメニュー。リードを消す権限があり、相手がまだリード（status が lead）のときだけ出す。今回は今のメニューに項目を1つ足す（メニューの中に作った登録リンクを出す欄があり、金型 ContextMenu にはその置き場が無いため。金型への作り替えは別の回）。
8. ADR-119 の「lead 新規作成時は同一トランザクション内で `lead_channels` にも INSERT する」は、「窓口の番号を持つ経路（Meta・Discord の受信）だけ」と読み替える。人が手で作るリードには窓口の番号が無い。

## Why（なぜ）

- 今の統合は4表しか付け替えない。conversation_logs の結び付きは ON DELETE RESTRICT なので、会話の記録を持つリードを loser にすると削除で止まり、「データベースエラーが発生しました。」になる。受信で生まれた新しいリードは受信のときに会話の記録を書くので、統合の本来の使い道（新しい窓口から来た人を前からのリードへ寄せる）で必ず止まる。CASCADE の2表は黙って消え、FK の無い4表は迷子になる。
- 本番の統合は 0 回（2026-10-28 本番を読むだけで確認）。今直せば被害は無い。
- 消す方式は変えない。消さずに印を付ける方式は、leads を読むすべての経路に条件を足す必要があり、今の規模（リード 56 件・統合 0 回）では作業と漏れの危険が大きい。13表を付け替えれば、消す方式でも記録は1つも失われない。
- 空欄だけ埋めるのは PO の選択。HubSpot の統合の既定動作と同じ考え方（primary の値を優先し、空なら secondary の値を使う）。
- 下見をサーバーで返すのは、埋める規則を1か所に置くため（ADR-095）。
- 置き場所は PO の決定。使う回数が少ないので、普段は目に入らない「⋯」の中に置く。

## 守り方

- 試験 `backend/tests/test_lead_merge_pg.py` が13表・空欄埋め・下見・異常系を毎回の CI で確かめる。13表に新しい表が足されたときに漏れを見つけるため、試験は「leads を参照する列を持つ表」を DB から数え、付け替えの一覧と数が合わなければ落ちる。
- 画面は金型とデザイントークンだけで作る（ADR-067）。

## 戻し方

- 表の作りは変えないので、PR を戻すだけで前の動きに戻る。統合済みのデータは監査ログ（merge_absorb・merge_delete。loser の全項目の控え）から手で戻す。

## 対象外（別の回で PO に聞く）

- リードの削除（`delete_lead`）に同じ付け替えを入れるか。
- FK の無い4表に FK を足すか。
- 窓口の記録が無い 49 件（2026-07-02 の移し替えで作られた）の結び付け方。
