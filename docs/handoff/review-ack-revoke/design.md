<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-ack-revoke（確認済みの取り消し）

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`
**recon**: `docs/handoff/review-ack-revoke/recon.md`
**前提の設計**: `docs/handoff/review-excluded-ack/design.md`（確認済みの和集合と cr_review_ack）、`docs/handoff/review-ack-confirm/design.md`（確認ダイアログ）、`docs/handoff/realtime-standard/design.md`（ADR-1016 即時反映）
**日付**: 2026-10-15
**担当**: Planner は Opus。設計審査とコード審査は Opus の別担当（2026-10-15 PO 決定）。実装は Sonnet。

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-15）:「誤って確認済みに写った商品を取り消すする機能は作れる？」
- 決定（同日「Y」）: 次の2か所に付ける。
  - (a) 確定した直後のお知らせに「元に戻す」ボタン。
  - (b) 確認済みの商品を開いたときに「確認済みを取り消す」ボタン。
- 一任（同日）: マージ・デプロイまで任せる。SSOT と金型を守り、ハードコードはしない。推測では進めない。
- きっかけ: 試しに確定した倉田さんの1件（item_corrections id=1610）を、手作業でしか戻せなかった（recon §3）。

## 1. 目的（KGI）

- K1: 要確認のドロワーで「このままで良い」を確定したあと、お知らせ「確認済みにしました…」の中に「元に戻す」ボタンが出る。押して確認ダイアログで「取り消す」を選ぶと、お知らせが「確認済みを取り消しました。解析をやり直しています」に変わる。
- K2: 要確認ページに「確認済み」タブが増える。確認済みの記録が今も有効な件だけがそこに並ぶ。行を押すとドロワーが開き、「この商品は確認済みです」と「確認済みを取り消す」ボタンが出る。
- K3: 取り消したあとは、解析のやり直しが終わって一覧が読み直されると、その件が「確認済み」タブから消える。確認が必要な理由が残っている件（例: 除外の対象）は「要確認」タブに戻る。
- K4: 取り消しても記録は消さない。item_corrections に1行を足すだけで、DB の列・表・migrations は変えない。確認済みかどうかの正本は item_corrections だけにする（SSOT）。
- K5: 取り消したあと、もう一度「このままで良い」を押せる。その確定は取り消し前の理由を引き継がない。

## 2. 変更前 → 変更後

### 変更前（recon §1・§4）
- 確定は item_corrections に review_ack 行を足すだけで、取り消す API も画面も無い。
- 確定した件は要確認タブから消える。消えた件をこのドロワーで開き直す場所が無い。

### 変更後
- 取り消しは、同じ件に `{"v":1,"codes":[]}` の review_ack 行を1行足して表す。
  - 読み手は2つあり、どちらも「最新の1行だけ」を見る。
    - Python の _ack_codes は、空の codes を warning なしで「確認済みなし」として扱う（recon §1、`backend/app/services/v102_human_decisions_svc.py` 108-116・170 行）。
    - SQL の cr_review_ack は、空の codes を偽として扱う（`backend/app/services/tcg_condition_review_svc.py` 190-206 行）。
  - このため、読む側の規則を変えずに「確認済みなし」に戻る。
- 取り消しの API を1本足す。保存したあとは、確定と同じように解析をやり直す。
- 一覧に「確認済み」タブを足す。判定は既存の cr_review_ack の中に1列足して行い、規則の置き場は1か所に保つ。

## 3. backend の変更（DB の列と migrations は変えない）

### 3-1. 取り消しの保存
ファイル: `backend/app/services/v102_human_decisions_svc.py`

- `save_review_ack` の隣に `save_review_ack_revoke(db, extraction_item_id, source_message_id, corrected_by) -> int` を足す。
- 手順は save_review_ack（245-265 行）と同じ形にする。
  1. `_CURRENT_REASONS_SQL`（FOR UPDATE）で analysis_results の行をロックし、今の review_reasons を読む。
  2. `load_v102_decisions` で、前の有効な ack_codes を読む。
  3. 前の ack_codes が空なら、何も書かずに 0 を返す（取り消すものが無い）。
     - 0 を返す前に、`await db.rollback()` を明示的に呼ぶ。FOR UPDATE のロックをすぐ外すため。
  4. 空でなければ `_INSERT_ACK_SQL` で、human_value=`{"v":1,"codes":[]}`（`json.dumps({"v": REVIEW_ACK_VERSION, "codes": []})`）、system_value=今の review_reasons を1行 INSERT する。そのあと commit して 1 を返す。
- 新しい field_name は作らない。理由は §7 案A。
- 定数（FIELD_REVIEW_ACK と REVIEW_ACK_VERSION）は既存のものを使い、直書きしない。

### 3-2. 取り消しの API
ファイル: `backend/app/routers/item_corrections.py`

- `POST /tcg/items/{extraction_item_id}/review-ack/revoke` を足す（/api/v1 配下）。
  - 権限は require_super_admin。
  - 入力は `ReviewAckRevokeRequest {source_message_id: UUID}`。
  - 応答は既存の `ReviewAckResponse {ok, saved}` を使う。
- 順序
  1. find_job_of_item。無ければ 404。
  2. v102 以外なら 409。
  3. source_message_id が合わなければ 422。
     - 2 と 3 の判定は、review_ack_rejection（`backend/app/services/v102_human_decisions_svc.py` 295-318 行）の中にある「件・v102・source」の検査部分を共通の関数に切り出し、確定と取り消しの両方から使う。同じ規則を二重に書かない。
     - 断る順序と状態コードは、確定のときと同じにする。
  4. save_review_ack_revoke を呼ぶ。0 なら 409（detail は「確認済みの記録がありません」の英語表記。API の detail は既存の英語の書き方に合わせる）。
  5. 1 なら enqueue_v102_reanalyze(job_id) を呼び、{ok: true, saved: 1} を返す。
- 通知: `backend/app/realtime/topics.py` の WRITE_ROUTE_TOPICS に `("POST", "/api/v1/tcg/items/{extraction_item_id}/review-ack/revoke")` を (tcg.review, global) で足す。確定の行（18-20 行）の隣に置く。
  - 合図は2回出る。1回目は、書き込みが成功した時点でミドルウェアが出す（`backend/app/middleware/realtime.py` 50-69 行）。2回目は、再解析のあとに出す（recon §2）。
    - 一覧の SQL は、1回目の時点で取り消し行を読む。そのため、取り消した件はすぐ「確認済み」タブから消える。
    - 自分の操作から出た合図は、画面側で無視する（`frontend/src/hooks/useRealtimeRefresh.ts` 3 行）。自分の画面は onRefresh で読み直す。
  - `backend/tests/test_realtime_topics.py` が載せ忘れを検知する。

### 3-3. 「確認済み」の判定を一覧に出す
ファイル: `backend/app/services/tcg_condition_review_svc.py`（review_joins の cr_review_ack）

- 既存の LATERAL cr_review_ack（190-206 行）が、`excluded_acked` に加えて `review_acked` を返すようにする。
- `review_acked` が真になる条件は、最新の1行が次をすべて満たすこと。
  - v=1。
  - codes が配列で、全要素が空でない文字列。
  - codes の要素数が 1 以上（`jsonb_array_length(...) > 0`）。
  - それより後（同じ時刻を含む）に書き写し直しの行が無い。
  - excluded_acked と同じ最新行・同じ検査を使い、条件を1つ足すだけにする。
- LATERAL の数、`OFFSET 0`、fence の正規表現（`backend/tests/test_tcg_condition_review_fenced.py`）は変えない。
- SQL の形（審査 R1 で決定）
  - `CROSS JOIN LATERAL (SELECT COALESCE(bool_or(<excluded の条件>), FALSE) AS excluded_acked, COALESCE(bool_or(<review_acked の条件>), FALSE) AS review_acked FROM (<最新1行の副問い合わせ>) a WHERE NOT EXISTS (<書き写し直しの検査>)) cr_review_ack` にする。
  - GROUP BY の無い集計なので、どの件でも必ず1行になる。2列とも NULL にならない。
  - `<最新1行の副問い合わせ>`、`<書き写し直しの検査>`、v と codes の検査は、今の 190-206 行の中身をそのまま使う。
  - 禁止すること
    - LEFT JOIN LATERAL にして NULL を出すこと。229 行の `NOT cr_review_ack.excluded_acked` が NULL になると、確認していない除外の件まで要確認から消える。
    - 最新行を引く副問い合わせを2本にすること。速さが落ち、規則も二重になる。
  - 229・236・248 行での excluded_acked の使い方は変えない。
- cr の出力に `cr_review_ack.review_acked AS review_acked` を足す。digest（version）には入れない。

### 3-4. 一覧 API のタブと応答
ファイル: `backend/app/routers/tcg_analysis_review.py` と `backend/app/services/tcg_analysis_review_svc.py`

- `_STATUS_TABS` に `ACKED` を足す。
- `_build_where` のタブ分岐（82-96 行）に `ACKED: cr.review_acked` を足す。
- review_only の分岐（99 行）は変えない。ACKED と同時に送られたら、両方の条件で絞る。review_only を送る frontend の呼び出し元は無い（審査の arch-frontend.txt）。
- 応答には review_acked を足さない。ドロワーは、どのタブから開かれたかを props で受け取る（§4-2）。応答の型（`backend/app/routers/tcg_analysis_review.py` 81-93 行 AnalysisResultItem）も変えない。

### 3-5. 対象外（触らない）
- CSV 取り込み（`backend/app/services/tcg_review_csv_svc.py`）。CSV からの取り消しは作らない。
- 一部の理由だけを取り消すこと。取り消しは、その件の確認済みを全部消す。
- POST /corrections で review_ack を直接書けてしまう件（recon §1）。既存の穴で、今回は直さない。§10 に記録する。
- migrations/、DB の列・制約、analysis_results の形。

## 4. frontend の変更

### 4-1. API 呼び出し
`frontend/src/features/tcg-analysis-review/reviewActions.ts` に `postReviewAckRevoke(item)` を足す。POST `/tcg/items/${id}/review-ack/revoke` に {source_message_id} を送る。postReviewAck（45-50 行）と同じ書き方にする。

### 4-2. ドロワー
`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`

- props: `ackedView?: boolean` を足す（既定は false）。「確認済み」タブから開いたときだけ true を渡す。item の型は変えない。
  - 理由（審査 R5）: 一部の理由だけ確認済みの件は、要確認タブにも残る。要確認タブで開いたときに「確認済みです」と出すと、残っている理由と食い違う。
- 状態: `revokedNotice`（boolean）、`revokeError`（boolean）、`revokeAsk`（boolean）を足す。
  - 次の3つのときに、revokedNotice と revokeError を false に戻す。
    - 「このままで良い」を押したとき（askKeep）。
    - 確定が成功したとき。
    - 行を選んだとき（scope を変えたとき）。
  - こうしておくと、取り消してから確定し直したときに、もう一度「元に戻す」が出る。2つのお知らせが並ぶこともない。
- (a) 確定の直後: 既存の Callout info（125 行、title=reviewItem.acked）の children に `<div><Button variant="secondary" size="sm">…</Button></div>` を置く。文言は reviewItem.revokeUndo（元に戻す）。
  - `<div>` で包むのは、既存の 118-122 行と同じ書き方。Callout の本文は縦並びの flex なので、Button が横幅いっぱいに伸びないようにするため。新しい CSS は書かない。
- (b) 確認済みタブから開いたとき: `ackedView && !ackedNotice && !revokedNotice` なら Callout info を出す。
  - title は reviewItem.ackedState（この商品は確認済みです）。
  - children は `<div><Button variant="secondary" size="sm">…</Button></div>`（reviewItem.revoke、確認済みを取り消す）。
  - ackedView のときは、「このままで良い」のボタン（canKeep）は今の規則のままにする。確認済みの理由は review_reasons から外れているので、外せる理由が無ければ出ない。
- (a) と (b) のボタンは、どちらも同じ ConfirmModal（既存 154-171 行の作りに並べる）を開く。
  - 文言は reviewItem.revokeConfirm.{title,message,confirm}。キャンセルは common.close。
- 確定（取り消す）を押したとき
  - postReviewAckRevoke を送る。
  - 成功: ackedNotice=false、ackedCodes をクリア、revokedNotice=true、onRefresh() の順に行う。
  - 失敗: Callout warning（reviewItem.revokeFailed）を出す。
- revokedNotice のあいだは Callout info（reviewItem.revoked）を出し、(a) と (b) のボタンは出さない。
- 新しい CSS は書かない。色・余白の直値は書かない。新しい金型も作らない。使うのは Callout・Button・ConfirmModal だけ。

### 4-3. 要確認ページのタブ
`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`

- TabKey（26 行）に "acked" を足す。Tabs の金型に「確認済み」タブを足す（並びは production、acked、posts の順）。
- タブと status_tab の対応: production は NEEDS_REVIEW、acked は ACKED。対応表は定数を1つだけ置いて使う。
- 取得の effect（82 行）の入口を `activeTab === "posts"` なら何もしない、に変える。data・offset・reloadKey は、production と acked で共通の1組をそのまま使う。同じ行の部品と同じドロワーを使い、別の一覧は書き起こさない。
- タブを切り替えたら、offset を 0 に戻し、ドロワーを閉じる（drawerItemId を null にする）。
- CSV のカード（191-194 行）は、production タブのときだけ出す。
- ドロワーに `ackedView={activeTab === "acked"}` を渡す。
- useRealtimeRefresh（79 行）は reloadKey を増やす。effect の依存に activeTab があるので、表示中のタブが読み直される。acked タブでも読み直されることを試験で確かめる。
- acked タブでは removedFromList を渡さない。その文言「この商品は要確認から外れました」（ja.json 3782 行）は、要確認を前提にしているため。

### 4-4. 文言（ja/en 同一キー、ADR-027）

| キー | ja | en |
|---|---|---|
| reviewItem.revokeUndo | 元に戻す | Undo |
| reviewItem.ackedState | この商品は確認済みです | This item is marked as checked |
| reviewItem.revoke | 確認済みを取り消す | Undo "checked" |
| reviewItem.revokeConfirm.title | 確認済みを取り消しますか？ | Undo "checked"? |
| reviewItem.revokeConfirm.message | この商品の確認済みをすべて取り消し、解析をやり直します。確認が必要な理由が残っていれば、要確認の一覧に戻ります。 | All "checked" marks on this item are removed and the analysis runs again. If a reason still needs checking, the item returns to the review list. |
| reviewItem.revokeConfirm.confirm | 取り消す | Undo |
| reviewItem.revoked | 確認済みを取り消しました。解析をやり直しています | Undone. Re-running the analysis |
| reviewItem.revokeFailed | 取り消せませんでした。もう一度お試しください | Could not undo. Please try again |
| needsReview.tabs.acked | 確認済み | Checked |

- タブのキーは、既存の needsReview.tabs.production と needsReview.tabs.posts に並べる。

## 5. 対象と対象外
- 対象: §3・§4 のファイルと、その試験。台帳、recon、design。
- 対象外: §3-5 のとおり。比較表の「押して直せる行」は、別件として PO の回答を待っている。

## 6. 影響範囲（呼び出し元）
- cr_review_ack と review_joins の利用元（`docs/handoff/review-excluded-ack/design.md` §3-4 の全走査）: 配信（`backend/app/services/tcg_distribution_svc.py`）、進捗、一覧。
  - 足すのは列1つで、WHERE は変えない。SQL の文字列は変わるが、既存の結果は変わらない。
  - 配信 SQL の文字列を固定した試験 `backend/tests/test_inventory_distribution_rows.py` 186-201 行（`_GOLDEN` の SHA-256）は、必ず赤になる。作り直しの手順は次のとおり（前の便 review-excluded-ack と同じ）。
    1. 変更前と変更後の SQL 文字列の差分を出し、/tmp/CC報告ファイル/review-ack-revoke/ に保存する。
    2. 差分が「cr_review_ack の形が変わり、列が1つ増えた」だけであることを示す。
    3. `_GOLDEN` を新しい値に替え、横のコメントを更新する。
  - context_sql の `SELECT cr.*`（`backend/app/services/tcg_condition_review_svc.py` 273 行）は、使う側が必要な鍵だけを読むので、列が増えても問題ない。
  - CSV（`backend/app/services/tcg_review_csv_svc.py` 75 行）とシート（`backend/app/services/tcg_review_sheet_svc.py` 108 行）は NEEDS_REVIEW だけを取るので、影響は無い。
  - 生の走査の結果は /tmp/CC報告ファイル/review-ack-revoke/arch-*.txt にある。
- 取り消しで再解析が走ると、同じ投稿の全件が計算し直される。人の判断の正本は変わらないので、結果は確定前の状態に戻る（recon §1）。

## 7. 代替案と選択理由
- 案A（新しい field_name 'review_ack_revoke' を作る）
  - Python と SQL の2つの読み手に「どちらが新しいか」の比較を足す必要がある。
  - 規則の置き場が増え、ずれが起きやすい。
  - 不採用。
- 案B（review_ack 行を DELETE する）
  - 追記だけで残すという決まり（recon §3）に反する。
  - 誰がいつ取り消したかが残らない。
  - 不採用。
- 案C（採用）: 空の codes の review_ack 行を足す。
  - 2つの読み手は今の規則のままで「確認済みなし」と読む。
  - 誰がいつ取り消したかが corrected_by と corrected_at に残る。
- 「元に戻す」をトーストに載せる案
  - Toast の金型は action に対応していない（recon §4）。金型を広げる必要がある。
  - ドロワーの中の Callout は children を受け取れるので、そこにボタンを置く。
  - 不採用。

## 8. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。
  - 社内の記録の読み方と、ボタン1つの追加で、外部の数値事例が判断を変えない。
- 過去の自社事例
  - `docs/handoff/review-excluded-ack/design.md` の「規則は Python が正本で、SQL は同じ意味にし、一致を試験で守る」をそのまま使う（§9 の一致試験）。
  - 一覧の速度は `docs/handoff/review-speed/design.md` の「行ごとの LATERAL は重い」に従う。LATERAL は増やさず、列だけを足す。

## 9. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 元に戻す | vitest: ReviewItemDrawer で確定に成功したあと「元に戻す」が出る。押す → ダイアログ → 「取り消す」で postReviewAckRevoke が1回呼ばれ、「確認済みを取り消しました」が出る。失敗したときは revokeFailed が出る |
| K2 確認済みタブとボタン | vitest: NeedsReviewTabsPanel に「確認済み」タブがあり、選ぶと status_tab=ACKED・offset=0 で取得する。CSV のカードは出ない。ドロワーに ackedView=true が渡る。ReviewItemDrawer で ackedView=true なら「この商品は確認済みです」と「確認済みを取り消す」が出て、false なら出ない |
| K1/K5 状態の戻り | vitest: 確定 → 取り消し → もう一度確定、の順で「元に戻す」が再び出る。お知らせは同時に1つだけ |
| K2 一覧の判定 | pytest（PG）: ack を保存した件は ACKED に出る。取り消すと出ない。ack が無い件は出ない |
| K3 取り消しで要確認に戻る | pytest（PG）: exclusion='excluded' の件 → ack(excluded) → NEEDS_REVIEW に出ない → 取り消し → NEEDS_REVIEW に出る（excluded_acked が偽） |
| K3 再解析の適用 | pytest（PG）: 取り消しのあと、load_v102_decisions の ack_codes が空 |
| K4 追記のみ | pytest（PG）: 取り消しの前後で item_corrections の行数が +1、前の行は残っている。git diff に migrations/ が無い |
| K5 再確定 | pytest（PG）: ack(A) → 取り消し → ack(B) で、最新行の codes が [B] だけ（A を引き継がない） |
| API の断り | pytest: 件なし 404、v102 以外 409、source 不一致 422、確認済みなし 409（保存しない・再解析を積まない）、成功で再解析を1回積む |
| SQL と Python の一致 | pytest（PG）: codes が空・["excluded"]・["note_unmatched"]・書き写しの後・同じ時刻の書き写し・v≠1・壊れた JSON の7件で、SQL の review_acked と「Python の ack_codes が空でない」が一致する |
| 通知の表 | `backend/tests/test_realtime_topics.py` が緑 |
| 配信 SQL の固定値 | test_inventory_distribution_rows.py の `_GOLDEN` を §6 の手順で作り直し、差分が列1つの追加だけであることを保存ファイルで示す |
| 既存の試験 | backend: test_v102_human_decisions*.py、test_tcg_condition_review*.py、test_tcg_analysis_review*.py、test_tcg_distribution*、test_inventory_distribution_rows* が緑。frontend: tcg-analysis-review 配下と NeedsReviewTabsPanel の試験が緑 |
| i18n・金型 | CI（ja/en 同一キー、ハードコード検査、CSS 直値検査）が緑。新しい CSS ファイルや CSS の行を足さない |
| 速度 | §11 の方法で、要確認タブの1ページ目の SQL の実行時間が、変更前の 1.2 倍以内 |

## 10. リスクと対処
- 一覧が重くなる: LATERAL は増やさず、同じ最新行から列を1つ出すだけにする。マージ前に §11 で測り、1.2 倍を超えたらマージしない。
- 規則がずれる（SQL と Python）: §9 の一致試験で守る。
- 取り消しを連打して行が増える: 確認済みでないときは 409 で、何も書かない。
- 一部の理由だけ取り消したい要望: 今回は対象外。全部取り消してから、もう一度確定し直す。
- 既存の穴（POST /corrections で review_ack を直接書ける）: 今回の変更で悪化はしない。記録だけに留める。

## 11. 戻し方・測り方
- 戻し方: この PR を revert する。足した取り消し行は、古いコードでも「確認済みなし」と読まれる（今の読み手の規則のため）。データの後始末は要らない。
- 測り方（マージ前）
  - Sonnet が、変更前後の「要確認タブ・1ページ目・既定の並び」の items と count の SQL 文字列を Python から出力する。ACKED タブの1ページ目（items と count）も出力する。
  - Opus が本番で読み取り専用の EXPLAIN ANALYZE を取って比べる。
- 測り方（反映後）
  - デプロイを確認したら、本番で読み取り専用に次を取る。
    - 要確認タブの total。
    - ACKED に当たる件数（item_corrections の最新 review_ack が空でない件）。
  - 倉田さんの1件（id=1610）が ACKED 側に数えられることを確かめる。
  - PO がその件をボタンで取り消したら、空の codes の行が1行増え、件が要確認に戻ったことを読み取りで確かめる。

## 12. 計画票
1. Sonnet: §3 の backend と試験（PG 試験を含む）。
2. Sonnet: §4 の frontend と試験。
3. Sonnet: §11 の SQL 文字列を出力し、Opus が本番で EXPLAIN ANALYZE を取る。
4. Opus（別担当）: コード審査。
5. PR → CI → 委任 GO → マージ → デプロイ確認 → §11 の反映後の測り。

## 維持の仕組み
- 規則の一致: §9 の PG 試験（`backend/tests/test_v102_human_decisions_pg.py` に足す）。守り手: `backend/tests/test_v102_human_decisions_pg.py`
- 通知の載せ忘れ: 守り手: `backend/tests/test_realtime_topics.py`
- i18n と金型: 守り手: 人手で守る（既存 CI のハードコード検査と CSS 直値検査）

## 13. 設計審査（Opus 別担当）への対応
- 1回目は REVISE（2026-10-15）。反映した内容:
  - R1: SQL の形を bool_or の集計にして、必ず1行・NULL なしにする（§3-3）。
  - R2: 応答には review_acked を足さない（§3-4）。R5 で props 方式にしたため不要になった。
  - R3: `_GOLDEN` の作り直しの手順を書いた（§6・§9）。
  - R4: 状態を戻すきっかけと、`<div>` で包むことを書いた（§4-2）。
  - R5: 案1を採用。(b) は確認済みタブから開いたときだけ出す。ダイアログに「すべて取り消す」と書く（§4-2・§4-4）。PO の原文「確認済みの商品を開いたとき」は、確認済みタブから開く場合で満たせる。
  - R6: タブの対応、effect の入口、offset、CSV のカードの扱いを書いた（§4-3）。
  - R7: review_only、removedFromList、タブのキー、型の置き場所を設計で決めた（§3-4・§4-2・§4-3・§4-4）。
  - R8: 合図が書き込みの時点でも出ることを書いた（§3-2）。
  - R9: 0 を返すときは rollback する（§3-1）。
  - 任意: ACKED タブも速度を測る（§11）。
- 対象外（前からある差）: v=true を、Python は 1 として通し、SQL は落とす。excluded_acked でも同じで、今回は直さない。
- 2回目は APPROVE（2026-10-15）。審査が bool_or の形を PostgreSQL 16 の一時表で確かめた（6件とも1行で、NULL なし。/tmp/CC報告ファイル/review-ack-revoke/arch-boolor-shape.*）。あわせて次の4点を実装の指示として足した。
  1. §4-3: タブを切り替えるときは、offset=0 とドロワーを閉じることに加えて、`setData(null)` も行う。
     - 今の effect は、posts で止まるときに lastReloadKeyRef を更新しない（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx` 82-85 行）。そのため、前のタブの行が一瞬残る。
     - 試験: 「posts を挟み、合図が来たあとで acked → production と切り替えても、acked の行が出ない」。
  2. §4-2: Drawer の onClose を止める条件に、revokeAsk を足す（今は confirmOpen だけ。`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx` 93 行）。
  3. §3-3: v と codes の検査は、2つの bool_or に同じ文で書いてよい。ただし、最新行の副問い合わせは1本にする。
  4. §6: `_GOLDEN` の差分のファイルを /tmp/CC報告ファイル/review-ack-revoke/ に保存し、報告に書く。
- 実装メモ: 共通の検査関数名は item_rejection にした。確認済みタブが空のときは needsReview.ackedEmpty を出す（Opus 判断 2026-10-15）
