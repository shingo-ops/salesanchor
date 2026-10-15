<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-edit-all-fields（要確認の比較表で9項目を直す）

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`
**recon**: `docs/handoff/review-edit-all-fields/recon.md`
**前提の設計**: `docs/handoff/review-fix-column/design.md`（比較表の「修正」列）、`docs/handoff/review-ack-revoke/design.md`（判断の追記と読み方）
**日付**: 2026-10-15
**担当**: Planner は Opus。設計審査とコード審査は Opus の別担当。実装は Sonnet。

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-15）:「商品名、数量単価、単位、状態、メモ、作品、商品ID、販売状況→商品IDはIDだと人間は分からないので商品名を選択したら自動反映されるようにしてくれ」
- 旧版（v6）の扱い（同日の質問「v6 は商品と状態だけのままでよいか」への回答）:「n」＝ v6 にも仕組みを足す。便が1回増える。
- 一任（同日）: マージ・デプロイまで任せる。SSOT と金型を守り、ハードコードはしない。推測では進めない。

## 1. 目的（KGI）

- K1: 要確認のドロワーの比較表で、次の9行を押すと「直す」欄が出る: 商品名・数量・単価・単位・状態・メモ・作品・商品ID・販売状況。
- K2: 商品名・作品・商品IDの行は、どれを押しても「商品名で検索して選ぶ」欄が出る。選ぶと、商品IDと作品は自動で入る（ID を手で打つ欄は出さない）。
- K3: 数量・単価は数字、単位と販売状況は一覧から選ぶ、メモは文章で直せる。保存すると、比較表の「システム」列と「修正」列にその値が出る。
- K4: 直した値は、解析をやり直しても残る。在庫表と GAS の在庫一覧に同じ値が出る。販売状況を Sold out にした件は、在庫表と GAS から消える（既存の除外の規則）。
- K5: 直した記録は消さない。item_corrections に1行を足すだけで、DB の列・表・migrations は変えない。
- K6（便2）: v6 の件でも K1〜K5 が成り立つ。

## 2. 変更前 → 変更後

### 変更前（recon §2・§3・§6）
- 押せる行は商品ID・作品と、空箱関連の件の状態だけ。数量・単価・単位・メモ・販売状況を直す仕組みは無い。
- 数量・単価の「システム」列は gemini の書き写しを出している（実際に配信される ar の値ではない）。

### 変更後
- 新しい field_name を5つ足す: override_quantity / override_price / override_unit / override_note / override_status。
  - human_value は `{"v":1,"value":<文字列>}`。メモを空にするときは value に空文字。
  - 定義・検証・読み方・重ね方は `backend/app/services/v102_human_decisions_svc.py` の1か所に置く。
- 保存の API を1本足す。保存と同じトランザクションで ar の該当列を即時に直す。再解析でも同じ関数で重ね直す。
- 画面は、9行すべてを押せるようにし、数量・単価・単位・メモ・販売状況には新しい入力欄を出す。

## 3. backend（便1。DB の列と migrations は変えない）

### 3-1. 定義と読み方（`backend/app/services/v102_human_decisions_svc.py`）
- 定数: `FIELD_OVERRIDE_QUANTITY = "override_quantity"` ほか4つ。`OVERRIDE_FIELDS`（5つのタプル）、`OVERRIDE_PREFIX = "override_"`、`OVERRIDE_VERSION = 1`。
- `ValueOverrides`（frozen dataclass）: quantity: Decimal|None、price: Decimal|None、unit: str|None、note: str|None（空文字は「空にした」）、status: str|None。is_empty を持つ。
- `Decisions` に `values: ValueOverrides = ValueOverrides()` を足す。is_empty は values も見る（効くのは _apply_decisions の早期 return だけ。審査 R11 で他の呼び出し元に影響が無いことを確認済み）。
- `load_v102_decisions`: OVERRIDE_FIELDS を2か所に足す。146 行の SQL に渡す fields と、158 行の _latest_valid に渡すフィルタ（R11）。書き写しの直しより前の行は無効（既存の規則）。形が違う行（JSON が読めない・v≠1・数字に読めない・is_finite でない）は warning を出して無視（_ack_codes と同じ扱い）。
  - 結果に含める件は「product・condition・ack・values のどれかがある件」。

### 3-2. マスタの軽い読み込みと検証（同ファイル）
- 単位: `backend/app/services/tcg_analyzer_svc.py` の load_lookup_maps（89-103 行）の単位の SQL を `load_unit_canonical_ids(session) -> dict[str, str]` に切り出し、load_lookup_maps もそれを呼ぶ（SQL は1か所のまま）。保存と選択肢はこの関数だけを呼び、全商品は読まない（R10）。別名の無い単位は選択肢に出ないが、これは v102 本体と同じ表で一貫している。
- 販売状況: `load_status_master`。例外時に rollback するので、必ず INSERT の前に読む（R10）。
- `override_rejection(field, value, unit_ids, status_entries) -> DecisionRejected | None`（422）:
  - quantity・price: Decimal に読めて is_finite、0 以上、小数は2桁まで（3桁以上は 422。列は NUMERIC(14,2)）、`_bounded_number` に入る（R9）。
  - unit: unit_ids のキーに含まれる。
  - status: status_entries の canonical のうち effect が OUTPUT か EXCLUDE のもの。
  - note: 2000 文字以内。
- 選択肢 `override_options(session) -> {"units":[...], "statuses":[...]}` は検証と同じ2つの関数から作る（選択肢と検証の正本を1つにする）。

### 3-3. 重ね方（同ファイル。v102 と v6 で共用）
- `apply_value_overrides(values: dict, overrides: ValueOverrides, unit_ids: dict, status_entries: list) -> dict`（元の values は変えない）:
  - quantity → quantity_normalized、price → price_normalized。
  - unit → unit_canonical=値、unit_id=int(unit_ids[値])、unit_resolved=True。
  - note → note_ja（空文字なら None）。
  - status → status=値、exclusion='excluded'（その canonical に effect=EXCLUDE の行があるとき）か None。EXCLUDE が優先（resolve_status_v2 と同じ）。
  - 単位・状態がマスタから消えていたら、その項目だけ warning を出して重ねない（例外にしない。R4）。
  - review_reasons と needs_review は変えない。
- `status_available_by_human(decision, status_entries) -> bool`: 人が販売状況を EXCLUDE 以外に直した件か。
- v102 の順序（`backend/app/services/line_analysis_v102_svc.py` 921-959 行 _write_results。R5）:
  1. base_values（_analysis_values）を作った直後に、件ごとに apply_value_overrides を重ねる。
  2. _buyback_units: 単位か価格の上書きがある件は、状態の判断がある件と同じく対象外にする（885-887 行の human_condition の集合に足す）。
  3. _unit_price_mismatches: 1. の値（人の値）で判定する（変更なし。入力が人の値になるだけ）。
  4. _apply_decisions は今のまま（値の上書きは 1. で済んでいるので、ここでは重ねない）。
  5. _extra_targets（841 行）だけを、`_has_human_judgement(decision) or status_available_by_human(...)` の件で止める（R2）。人が在庫ありに直した件が、ほかの商品の is_current を落とさないため。止める単位は件ごと（同じ投稿の他の件の〆はそのまま）。
     - _apply_soldout_targets（817 行。状態の差し替え）は止めない。止めると condition_unknown 系の理由が戻り、「このままで良い」では外せなくなるため（2回目審査 S3）。
  - _write_results の中では masters["status_entries"] を使い、load_status_master を呼び直さない（例外時に rollback するため）。
- 即時の保存（§3-4）も同じ apply_value_overrides を使う。

### 3-4. 保存（同ファイル）
- `save_value_override(db, extraction_item_id, source_message_id, field, value, corrected_by) -> int`
  1. 件の job_id を find_job_of_item で引き、`pg_advisory_xact_lock(hashtextextended('v102_analysis:'||job_id, 0))` を取る（run_v102_analysis 1180 行と同じ鍵。走行中の再解析と順番にする。R7）。
  2. 単位と販売状況のマスタを読む（INSERT の前。R10）。override_rejection で検査し、断るなら rollback して何も書かない。
  3. ar の行を FOR UPDATE で読み、今の値を system_value にして、`_INSERT_ACK_SQL` と同じ INSERT（field_name だけ違う）で1行足す。
  4. その件の判断を load_v102_decisions で読み直し、apply_value_overrides の結果のうち5項目の列（quantity_normalized、price_normalized、unit_id、unit_canonical、unit_resolved、note_ja、status、exclusion）を UPDATE。updated_at も更新。
  5. 販売状況を EXCLUDE の状態（Sold out）に直したときは、同じトランザクションで review_ack に "excluded" を足す（前の有効な codes との和集合）。save_review_ack は中で commit する（264 行）ので、commit しない内部関数 `_insert_review_ack_union(db, …)` に切り出し、save_review_ack とこの保存の両方が使う（S1）。excluded は外せる理由（review_reason_codes_svc.py:17 で外せないのは condition_unknown だけ）。人が自分で売り切れにした件を、除外の理由で要確認に戻さないため（R6）。EXCLUDE 以外に戻したときは ack を書かない（exclusion が None になり、除外の理由そのものが消える）。
  6. commit して 1 を返す。

### 3-5. API（`backend/app/routers/item_corrections.py`）
- `POST /tcg/items/{extraction_item_id}/value-override`、require_super_admin。入力 `{source_message_id, field: "quantity"|"price"|"unit"|"note"|"status", value: str}`（field は Literal、value は最大 2000 文字）。応答 `{ok, saved}`。
- 順序: find_job_of_item → item_rejection（便1は v102 以外 409）→ save_value_override（中で 422）→ enqueue_v102_reanalyze。
- `GET /tcg/review/value-options`（require_super_admin）→ override_options。
- 予約語: SaveCorrectionsRequest.validate_route（85-86 行）に「field_name が `override_` で始まるなら ValueError」を足す。/corrections から検証を通らずに書く道を塞ぐ（R3）。
- 通知: `backend/app/realtime/topics.py` の表に POST を (TOPIC_TCG_REVIEW, SCOPE_GLOBAL) で足す（19-20 行と同じ形）。GET は載せない（`backend/tests/test_realtime_topics.py` が判定）。

### 3-6. 一覧 API（`backend/app/services/tcg_analysis_review_svc.py`）
- SELECT に ar.quantity_normalized、ar.price_normalized を足し、system に "quantity"・"price" を足す。文字列は `format(d.normalize(), "f")`（1000 が 1E+3 にならない。R9）、None は ""。
- 応答の各件に "manual_values": `{quantity?, price?, unit?, note?, status?}`（直した項目だけ。数字は同じ書式）を足す。ページの件の id で load_v102_decisions を run_sync で1回呼んで作る（読み方の正本を使う）。
- この関数は要確認シート（tcg_review_sheet_svc.py:108）と CSV（tcg_review_csv_svc.py:75）からも呼ばれる。足すのはキーだけなので、両者の出力列は変えない（試験で確かめる）。

### 3-7. 対象外（触らない）
- POST /corrections の挙動（予約語の1行を除く）、save_corrections、書き写しの直し（PUT items）、cr_review_ack と review_version の SQL、配信の SQL。
- 直した値の取り消し（「直す前に戻す」）。必要なら、元の値をもう一度選んで保存する。
- 古い note_ja・status・exclusion・manual_partial_update の行（読み手を作らない。override_ で始まらないので読まれない）。

## 4. frontend（便1）

### 4-1. 型と API
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx` の AnalysisReviewItem に `is_v102?: boolean` と `manual_values?: Partial<Record<"quantity"|"price"|"unit"|"note"|"status", string>>` を足す。
- API 呼び出しは既存の `api.post` / `api.get` を使う。

### 4-2. 比較表の値
- systemCell（33-40 行）: quantity・price は system.quantity / system.price があればそれを出す（採用元は systemConfirmed）。無ければ今どおり gemini。saleStatus は buildComparisonRows で system.status のまま。

### 4-3. 押せる行（`frontend/src/features/tcg-analysis-review/reviewFixRows.ts`）
- RowScope に "value" を足す。
- v102 の件（item.is_v102 === true）:
  - name・productId・work → scope "product"。name の「修正」列は人が決めた商品名（productId と同じ値）。
  - state → scope "condition"（判定は 4-5 の isConditionFixable）。
  - quantity・price・unit・memo・saleStatus → scope "value"。「修正」列は manual_values の値（memo は note、saleStatus は status）。
- v6 の件は便1では今のまま（productId・work と、空箱関連の state）。name も scope "product" にする（商品を選ぶ欄は v6 でも既に動く）。

### 4-4. 直す欄（`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx`）
- FixChoice と FixScope に "value" を足す。CHOICES_OF_SCOPE.value = ["value"]。availableFixChoices は v102 の件で "value" を足す。
- ReviewFixWizard に `rowKey` を渡す（ReviewItemDrawer で押した行のキー）。choice が "value" なら新しい `ReviewValueFixForm` を出す。
- ReviewItemDrawer の Wizard の key（204 行 `${id}:${scope}`）に rowKey を足す。行を切り替えたら入力欄を作り直し、前の行の値を残さない（R8）。
- 新しい `frontend/src/features/tcg-analysis-review/ReviewValueFixForm.tsx`:
  - props: item, rowKey（quantity|price|unit|memo|saleStatus）, onRefresh。
  - quantity・price: TextField（type="number"、min 0、step any）。unit・saleStatus: Select（選択肢は GET /tcg/review/value-options）。memo: Textarea（maxLength 2000）。
  - 初期値は今の「システム」列の値。保存ボタン（Button）で POST value-override。成功なら onRefresh、失敗は 422/409 とそれ以外で文言を分ける。
  - 生の input・select、色の直値、新しい CSS は使わない。
- 「比較表は表示だけ」のコメント（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx` 4 行）は「押した行に合わせて直す欄が出る」に直す。未使用の ManualInput は消さない（範囲外）。

### 4-5. 状態の行（R1）
- isConditionReviewRelevant（`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx` 16-21 行）は変えない。SupplierDetailView.tsx:117 の常設パネルは今のまま空箱関連の件だけに出る。
- 新しい `isConditionFixable(item) = isConditionReviewRelevant(item) || (item.is_v102 === true && Boolean(item.condition_review))` を同じファイルに置き、fixRowsOf と availableFixChoices はこれを使う。
- ConditionReviewPanel に `fromWizard?: boolean` を足す。表示の条件は `relevant || fromWizard`、選択肢の取得（40-47 行）も同じ条件。ReviewFixWizard（119 行）だけが fromWizard を渡す。
- 「空箱であることを確認」ボタンと空箱向けの文言は、isConditionReviewRelevant が真の件だけに出す。それ以外の件では「状態を選ぶ」欄と「この状態に直す」（既存の correct）だけを出す。
- 保存は既存の condition_review（decision=correct）。backend の save_condition_review は classification=none の件でも correct を受け付ける（recon、92）。

### 4-6. 文言（ja/en 同一キー、ADR-027）
- reviewItem.wizard.choice.value / valueDesc、reviewItem.valueFix.{title, quantity, price, unit, memo, saleStatus, save, saving, saved, invalid, changed, saveFailed, loadFailed}。

## 5. 便2（v6。便1 #4333 マージ後の main 759cee4d5 を基準。PO の回答「n」＝v6 にも同じ仕組みを足す）

略称: A=`backend/app/services/tcg_analyzer_svc.py`、H=`backend/app/services/v102_human_decisions_svc.py`、R=`backend/app/routers/item_corrections.py`、T=`backend/app/tasks/tcg_extraction.py`。

### 5-0. 便2の recon（事実）
- v6 の値の出どころ: 数量 A:1669、単価 A:1670、単位 A:1523-1524（`unit_uuid` は `str`、A:107 で `str(uid)`）、メモ A:1674、販売状況と除外 A:1678（`resolve_status_v2`）。UPSERT は A:1709 付近〜1812（`"unit_id": unit_uuid` A:1794、`"exclusion": exclusion_val` A:1804）。最初の commit は A:1814。
- 商品の直しがある件は A:1493-1507 で UPSERT に来ない（状態だけ更新して continue）。即時 UPDATE した人の値はそのまま残る。
- 状態の確定の束縛ハッシュ（`backend/app/services/tcg_condition_review_svc.py:93-96`）に単位・数量・単価が入る。直すと確定が外れる（v102 と同じ。既存の挙動）。
- v6 の exclusion を書くのは A:1804 だけで、値は `resolve_status_v2`（A:1273-1312）の「販売状況マスタの effect=EXCLUDE 行に一致」だけから来る。状態以外の理由で除外が付く経路はコードに無い（全走査）。
- 本番（読み取り）: v6 の status×exclusion は In Stock/空 35672、Sold out/excluded 1033、In Stock/excluded 90、Pre-order/空 8。'active' は 0 件。In Stock/excluded の 90 件は engine_version name-first-v9-product-all-terms（9/16〜10/09）で、review_reasons の大半が 'manual_review_pending'。この文字はコードにも git の全履歴にも無い。
- `resolve_status_v2` が 'active' を返すのは、マスタが空・読めない・どの行にも当たらないとき（A:1283、1309。A:1243-1244 はマスタが読めないとき空の一覧を返す）。apply_value_overrides は今の値を見ないので、'active' の件も上書きできる。
- `analyze_extraction_job`（A:1317）の呼び出し元は2つだけ: T:599（新規抽出。直前に commit T:588、行ロック・advisory lock なし）と `backend/app/services/tcg_product_master_svc.py:753`（再解析 API。analysis_runs の INSERT だけ先にある）。どちらも 1 取引 1 job。753 の前は analysis_runs と snapshots を INSERT してそれぞれ commit 済み（`tcg_product_master_svc.py:654-667,724` 付近）で、開いた取引は無い。
- 同じ鍵: `backend/app/services/v102_transcription_svc.py:166` `v102_analysis_lock_key(job_id)`。v102 の解析は `backend/app/services/line_analysis_v102_svc.py:1269` で取引の最初に取る。H:581 は同じ文字列を直書きしている。
- `load_v102_decisions`（H:231-279）は prompt_version を見ない。v6 でも読める。要確認一覧の manual_values（`backend/app/services/tcg_analysis_review_svc.py:277,319`）も v6 で返る。
- `item_rejection`（H:446）は 404 → v6 なら 409 → 422 の順。呼ぶのは H:443（review_ack_rejection）、R:231（取り消し）、R:273（value-override）。H:576 の save_value_override は 404 だけを自前で作る。
- 配信: `backend/app/services/tcg_distribution_svc.py:247` が status の 'sold out' を外し、:336・:448 が `exclusion IS DISTINCT FROM 'excluded'` を見る。配信の予約 `schedule_distribution`（T:670）を呼ぶのは v102 の再解析（T:723）だけ。v6 の人の直しは、今は配信の予約も画面通知もしない。
- 本番の `TCG_AUTO_DISTRIBUTE` は API（astro-webapp-backend-1）と worker（astro-webapp-celery-worker-1）の両方で `1`（読み取り 2026-10-16 01:02 JST、`/tmp/CC報告ファイル/review-edit-fields/291_api_env.txt`）。schedule_distribution は本番で働く。
- 解析の途中 commit A:1814 のあと、単位の補完 E3a/E4（`backend/app/services/tcg_unit_recovery_svc.py:873-880,1175-1182`）が `WHERE id = :ar_id` だけで ar の単位を書き換える。
- 鍵の後でマスタを読む関数は例外時に `session.rollback()` する（A:682、969、1037、1242）。rollback で xact lock は外れる。
- 循環 import: H や A の先頭で `v102_transcription_svc` を import すると ImportError（審査 `review-opus-bin2.md` §2-3 の実験）。transcription が先頭で H を import しているため（`v102_transcription_svc.py:18-20`）。
- 画面通知は便1で R の POST value-override を `backend/app/realtime/topics.py` の表に載せ済み（v6 でも同じ API なので通知は出る）。

### 5-1. 決めたこと（Opus の設計判断）
- D1 除外の規則は v102 と同じにする。人が販売状況を直したら、exclusion はその状態に合わせる（EXCLUDE なら 'excluded'、ほかは None）。根拠: v6 の exclusion は status 由来しかなく（5-0）、v6 を解析し直せば exclusion はもともと無条件に上書きされる。90 件の 'manual_review_pending' はコードに根拠が無い文字なので、それで分ける処理は作らない。
- D2 v6 の解析も同じ鍵を取る。人の値を読んだあとに保存が割り込んで、その値を古い値で上書きしないため。保存（H:581）は鍵 → FOR UPDATE の順、解析は鍵を最初に取るので、取る順が同じでデッドロックしない。呼び出し元は行ロックを先に持っていない（5-0）。
- D3 v6 で値を直したら、配信の予約を1回積む（v102 の再解析が積むのと同じ `schedule_distribution`）。Sold out に直した件を、次の配信で外すため。v6 の再解析は積まない（即時 UPDATE で ar は直っていて、v6 の再解析は重いため）。
- D4 状態（コンディション）の行は v6 では今のまま（空箱関連だけ）。PO の依頼の「状態」は v102 で満たし、v6 の状態の直しは便1から既存の空箱の流れだけ。
- D5 鍵の名前を作る関数の正本を H に移す（依存の一番下。循環しない）。`v102_transcription_svc.v102_analysis_lock_key` は H の関数をそのまま使う（import して名前を残す）。H:581 と `line_analysis_v102_svc.py:1269` の直書きもこの関数に揃える。中身の文字列は変えない。
- D6 単位の補完 E3a/E4 は、人が単位を直した行（unit_resolved = TRUE）を書き換えない。UPDATE の WHERE に `AND unit_resolved = FALSE` を足す。途中 commit 後に保存が割り込んでも、人の単位が消えないため。

### 5-2. backend
1. H:
   - 鍵の関数 `v102_analysis_lock_key(job_id) -> str` を H に置く（中身は今の `v102_transcription_svc.py:166-168` と同じ文字列）。H:581 の直書きをこの関数に替える（D5）。
   - 新しい `item_basic_rejection(found, source_message_id)`: 件なし 404 → source 不一致 422。
   - `item_rejection` は今の順（404 → v6 なら 409 → 422）を保つ: `found is None → 404`、`v102 でない → 409`、`return item_basic_rejection(found, source_message_id)`。docstring（H:432-433）も合わせる。review-ack の確定・取り消し・CSV（`tcg_review_csv_svc.py:177`）の応答は変わらない。
   - `save_value_override`（H:576 付近）は item_rejection の代わりに item_basic_rejection を使う。
2. `backend/app/services/v102_transcription_svc.py:166-168`: 定義を消し、`from app.services.v102_human_decisions_svc import v102_analysis_lock_key` を使う（既存の H の import 行に足す。今の呼び出し元はそのまま動く）。
3. `backend/app/services/line_analysis_v102_svc.py:1269`: 直書きの文字列を `v102_analysis_lock_key(job_id)` に替える（H から import 済みの行に足す）。
4. R の value-override（R:261-284）: R:273 を item_basic_rejection にする。保存後、v102 なら今どおり `enqueue_v102_reanalyze`、v6 なら `await run_in_threadpool(schedule_distribution)`（`starlette.concurrency`。同期の Redis 待ちで event loop を止めないため。import は R:45 の tasks の import 行に足す）。
5. A（v6 の解析）:
   - 鍵は、全マスタを読み終えたあと、extraction_items を読む SELECT（A:1440 付近、FOR SHARE）の直前で1回取る: `session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": v102_analysis_lock_key(str(extraction_job_id))})`。H は A の先頭で import してよい（審査の実験で循環しないことを確認済み）。job_id の型は v102 の呼び方と同じ文字列にする。
   - 鍵から A:1814 の commit までの間に rollback・commit が無いことを実装担当が確かめて報告する（審査時点で無い）。
   - SELECT の直後、ループの前に `decisions = load_v102_decisions(session, [件の id の文字列])` を1回。
   - A:1690（empty_box の理由を足す所）の後、A:1691-1692（`reanalysis_condition` の呼び出し）の前に、その件の判断があって values が空でないときだけ重ねる:
     ```python
     merged = apply_value_overrides(
         {"quantity_normalized": quantity_normalized, "price_normalized": price_normalized,
          "unit_id": unit_uuid, "unit_canonical": unit_canonical, "unit_resolved": unit_resolved,
          "note_ja": note_ja, "status": status_val, "exclusion": exclusion_val},
         d.values, unit_canonical_to_uuid, status_entries)
     ```
     のあと各変数へ戻す。unit_id は `str(v) if v is not None else None` で今の型（str）に揃える。
     - review_reasons・needs_review・`stats["unit_resolved"]`（A:1526-1527）は重ねる前の値のまま（便1の約束と同じ）。
     - 人の単位は商品照合の kubun の絞り込み（A:1530-1533）には効かない（v102 と同じ）。
     - candidate（A:1692）はこの後で作られるので、人の値が束縛ハッシュに入る。
   - 商品の直しがある件の分岐（A:1493-1507）には手を入れない。
6. `backend/app/services/tcg_unit_recovery_svc.py:873-880` と `:1175-1182`: UPDATE の WHERE に `AND unit_resolved = FALSE` を足す（D6）。v102 の解析がこの2つを呼ぶかを実装担当が grep で確かめて報告する。呼ぶなら v102 にも同じ守りが効く（悪化しない）。読む側の SELECT が既に unit_resolved = FALSE の行だけなら、競合時以外は結果が変わらないことも報告する。違う場合は止めて Opus に報告。
7. 対象外: v6 の再解析を積む仕組み、`resolve_status_v2`、配信の SQL、要確認一覧の SQL、`save_condition_review`。

### 5-3. frontend
- `frontend/src/features/tcg-analysis-review/reviewFixRows.ts:37` の `if (item.is_v102 === true)` を外し、数量・単価・単位・メモ・販売状況を v6 でも scope "value" にする。
- `ReviewFixWizard.tsx:39` の availableFixChoices の "value" の v102 条件を外す。`ReviewFixWizard.tsx:27`（ackableReasonCodes）と `ConditionReviewPanel.tsx:25`（状態の行、D4）は残す。
- 保存後の文言（`ReviewValueFixForm.tsx:87`）: v102 は今の `reviewItem.valueFix.saved`（「直しました。解析をやり直しています」）、v6 は新しいキー `reviewItem.valueFix.savedNoReanalyze`（ja「直しました」／en「Saved」）を `item.is_v102` で出し分ける。ja.json と en.json の両方に足す（ADR-027）。
- 既存の試験の期待値を直す: `ReviewFixWizard.test.tsx:49-53`（v6 にも "value"）、`ReviewItemDrawer.test.tsx:182-191`（v6 の数量を「押せない行」の例にしている所を、v6 で押せない状態の行などに替える）。

### 5-4. 受け入れ基準（便2）

| 基準 | 検証方法 |
|---|---|
| V1 9行 | vitest: v6 の件で fixRowsOf が name・productId・work（product）、quantity・price・unit・memo・saleStatus（value）を返す。state は空箱関連のときだけ |
| V2 API | pytest: v6 の件の value-override が 200 で保存され、即時 UPDATE される。件なし 404、source 不一致 422 は同じ。v6 の review-ack の確定と取り消しは 409 のまま（v6 かつ source 不一致も 409）。`test_v102_value_overrides.py:266` の v6→409 の期待は 200 に直す |
| V3 配信の予約 | pytest: R の schedule_distribution を monkeypatch して数える。v6 で保存すると1回、enqueue_v102_reanalyze は0回。v102 は今どおり再解析が1回・配信0回 |
| V4 再解析で残る | pytest（PG）: v6 の件で数量と販売状況（Sold out）を直し、analyze_extraction_job をやり直しても ar が人の値で、exclusion='excluded'。In Stock に直すと None |
| V5 商品の直しがある件 | pytest（PG）: 商品の直しがある v6 の件は、やり直しても人の値が残る（V4 と同じ試験の中で確かめてよい） |
| V6 鍵 | pytest（PG、V4 と同じ試験の中）: 別の接続で `pg_advisory_xact_lock(hashtextextended('v102_analysis:<job>',0))` を持ったまま、解析側で `SET lock_timeout='200ms'` にして analyze_extraction_job を呼ぶと LockNotAvailable（55P03）になる |
| V6b 鍵の正本 | pytest: H の v102_analysis_lock_key と transcription の名前が同じ関数で、文字列が `v102_analysis:<job>` のまま。app の import が循環しない（`python -c 'import app.main'` 相当） |
| V6c 単位の補完 | pytest: E3a/E4 の UPDATE が unit_resolved=TRUE の行を書き換えない（SQL 文字列か PG で確かめる） |
| V6d 文言 | vitest: v6 で保存すると「直しました」、v102 は今の文言。ja/en のキーが揃う（既存の i18n の検査） |
| V7 既存 | test_tcg_work_matching_integration.py、test_line_analysis_v102_svc.py、test_v102_value_overrides*.py、test_item_corrections*.py、tcg_unit_recovery の試験、tcg-analysis-review の vitest が緑（5-3・V2 の期待値更新のうえで） |
| V8 PG 試験の数 | PG の試験の追加は2本まで（共有の pg fixture は試験ごとに DB を作るため） |

### 5-5. リスクと対処（便2）
- 待ちは2方向: 解析は同じ投稿の保存1回分を待つ。保存は同じ投稿の v6 ループ（鍵から A:1814 まで）を待つ。v6 ループ1投稿の所要時間は未測定。別の投稿とはぶつからない。
- 便1の保存側も、鍵の後の `load_status_master`（H:584）が例外で rollback すると鍵が外れる。本番には表があり実害は無い。同じ型の穴として記録だけ残す（今回は直さない）。
- 人が Sold out にした v6 の件にも excluded の確認済みが付く（便1と同じ H の処理）。v6 では確認済みの取り消しが 409 のため、取り消すには販売状況を別の値に直す（exclusion が None になり、除外の理由そのものが消える）。
- 90 件の In Stock/excluded の件で販売状況を直すと、除外が外れる（D1）。人が明示して直したときだけ起き、もともと v6 を解析し直しても同じことが起きる。
- 戻し方: PR を revert。override_* の行は残っても、古いコードの v6 解析は読まないので、次の解析で解析の値に戻る。
- 測り方（反映後）: ①デプロイ success ②本番 bundle に `savedNoReanalyze` がある ③PO が v6 の件を1件直したとき、item_corrections と ar を読み取りで確かめ、worker のログに `scheduled_distribution` が出る。TCG_AUTO_DISTRIBUTE=1 は確認済み（5-0）。

## 6. 影響範囲（呼び出し元）
- load_v102_decisions: run_v102_analysis（1202 行）、save_review_ack・save_review_ack_revoke（252・277 行）、_fixed_products。Decisions に項目が増えるだけで、既存の3つの意味は変えない。
- Decisions.is_empty: _apply_decisions の早期 return。values がある件でも重ねるようにするための変更。
- systemCell: 比較表と FinalSystemValue の両方。数量・単価の表示が ar の値になる（v6 も同じ）。
- 配信: ar の列を直すだけなので、配信の SQL は変えない。`_GOLDEN` は変わらない。

## 7. 代替案と選択理由
- 既存の POST /corrections に field_name を足すだけの案: 検証が無く、自由文字列のまま。v102 の判断の読み方と別の入口になる。不採用。
- 書き写しの直し（PUT items）で数量・単価を直す案: 投稿の全件が必須で、商品・状態の判断が無効になる。不採用。
- analysis_results に「人の値」の列を足す案: migration が要り、ar と人の判断の正本が2つになる。不採用。
- 新しい表を作る案: 正本が分散する。不採用。

## 8. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。社内の記録の読み方の拡張で、外部の数値事例が判断を変えない。
- 過去の自社事例: `docs/handoff/review-ack-revoke/design.md` の「判断は item_corrections に追記し、読み方の正本は1か所」をそのまま使う。

## 9. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 9行が押せる | vitest: v102 の件で fixRowsOf が name, quantity, price, unit, state, memo, work, productId, saleStatus の9キーに scope を返す。v6 の件は便1では name, productId, work（と空箱の state） |
| K2 商品名で選ぶ | vitest: name・productId・work のどれを押しても ReviewProductFixForm が出て、ID の入力欄は無い |
| K3 入力と表示 | vitest: ReviewValueFixForm で数量は数字、単位・販売状況は選択肢、メモは文章。保存で POST value-override が1回、body が {source_message_id, field, value}。成功で onRefresh。manual_values の値が「修正」列に出る |
| K3 選択肢 | pytest: value-options が units と statuses を返し、override_rejection が同じ集合で判定する |
| K4 再解析で残る | pytest（PG）: 5項目を直した件を run_v102_analysis でやり直しても、ar の列が人の値。書き写しの直しを足すと無効になる |
| K4 配信 | pytest（PG）: status を Sold out にすると exclusion='excluded' で、要確認に戻らない（review_ack に excluded が足される）。In Stock に戻すと None。配信に出るのは既存の条件（要確認でない・is_current・unit_resolved・価格あり）を満たす件 |
| R2 〆 | pytest（PG）: 〆の相手がある件を In Stock に直すと、extra targets が書かれない（状態の差し替えは残る）。同じ投稿の他の件の〆は変わらない |
| S2 確認済みタブ | pytest（PG）: Sold out に直した件は status_tab=ACKED に出て、NEEDS_REVIEW には出ない |
| R4 マスタから消えた値 | pytest: unit_ids に無い単位、status_entries に無い状態の上書きは無視され、例外にならない |
| R5 買取単位 | pytest: 単位か価格を直した件は apply_buyback_units の対象外。単位と価格の不一致の判定は人の値で行う |
| R7 競合 | pytest（PG）: save_value_override が v102_analysis の鍵を取る（同じ鍵を別の接続で持っている間は待つ） |
| R3 予約語 | pytest: POST /corrections に field_name="override_price" を送ると 422 |
| R9 数字 | pytest: NaN・Infinity・負の数・小数3桁・上限超えは 422。1000 は "1000" と表示される |
| K5 追記のみ | pytest（PG）: 保存の前後で item_corrections が +1、前の行は残る。git diff に migrations/ が無い |
| API の断り | pytest: 件なし 404、v6 409（便1）、source 不一致 422、範囲外の数字・未知の単位・未知の状態・長すぎるメモ 422（何も書かない）、成功で再解析を1回積む |
| 一覧 | pytest: system.quantity・system.price と manual_values が出る。要確認シートと CSV の出力列は変わらない |
| R1 状態パネル | vitest: 空箱関連でない v102 の件で、ドロワーの常設パネルは出ず、state 行を押すと Wizard の中にだけ状態の欄が出る。空箱の確認ボタンは出ない |
| R8 行の切り替え | vitest: 数量の行 → 単価の行に切り替えると、入力欄の初期値が単価の値になる |
| 通知 | `backend/tests/test_realtime_topics.py` が緑 |
| 既存 | backend: test_v102_human_decisions*.py、test_item_corrections.py、test_tcg_analysis_review*.py、test_tcg_condition_review*.py が緑。frontend: tcg-analysis-review 配下の試験が緑 |
| i18n・金型 | CI（ja/en 同一キー、ハードコード検査、CSS 直値検査）が緑。生 input/select を足さない |

## 10. リスクと対処
- 開いたままの状態の保存が 409 になる（recon §8）: 値を保存すると onRefresh で版を読み直すので、同じドロワーでは起きない。別のタブでは既存の「変わりました」文言が出る。
- 単価だけ直して「単位と単価の食い違い」の理由が残る: 理由は外さない（§3-3）。人が「このままで良い」で外す。
- v102 で再解析が失敗した件: 即時 UPDATE の値が ar に残るので、画面と配信は人の値のまま。
- 走行中の再解析との競合: 保存が同じ鍵を取るので、保存は再解析の終わりを待つ（R7）。待つのは1投稿の解析の時間だけ。
- 人が Sold out にした件に excluded の確認済みが自動で付く: 人が売り切れと決めた件なので、除外の理由で要確認に戻さないのが正しい（R6）。取り消しは既存の「確認済みを取り消す」でできる。
- 自動で付いた excluded の確認済みにより、その件は「確認済み」タブに出る。そこで取り消すと要確認に戻る（S2）。
- 数量・単価を人が直しても、理由 value_out_of_range（範囲外）は残る。「このままで良い」で外す（S4）。
- 商品名の行の「システム」列は今どおり書き写しの商品名を出し、「修正」列に人が選んだ商品名を出す（K3 の「システム列に出る」は数量・単価・単位・メモ・販売状況の5項目）。

## 11. 戻し方・測り方
- 戻し方: PR を revert。足した override_* の行は古いコードでは読まれない（読み手が無いだけ）。ar の値は次の再解析で解析の値に戻る。
- 測り方（反映後）: 本番で、route が 401 を返すこと（存在しないパスは 404）、bundle に value-override が入っていること。PO が1件直したら、item_corrections の override_* 行と ar の列を読み取りで確かめる。

## 12. 計画票
1. Sonnet: §3 の backend と試験（PG 試験を含む）。
2. Sonnet: §4 の frontend と試験。
3. Opus（別担当）: コード審査。
4. PR → CI → 委任 GO → マージ → デプロイ確認 → §11。
5. 便2: §5 を追記 → 審査 → 実装 → 同じ流れ。

## 維持の仕組み
- 読み方と重ね方の正本: 守り手: `backend/tests/test_v102_human_decisions_pg.py`
- 通知の載せ忘れ: 守り手: `backend/tests/test_realtime_topics.py`
- i18n と金型: 守り手: 人手で守る（既存 CI のハードコード検査と CSS 直値検査）

## 13. 設計審査（Opus 別担当）への対応
- 1回目は REVISE（2026-10-15、/tmp/CC報告ファイル/review-edit-fields/96_design_review.md）。反映した内容:
  - R1: isConditionReviewRelevant は変えず、isConditionFixable と fromWizard を足した（§4-5）。
  - R2: 人が在庫ありに直した件は〆の差し替えと extra targets を止める（§3-3）。
  - R3: /corrections で override_ を予約語にした（§3-5）。
  - R4: マスタから消えた値は無視（§3-3）。
  - R5: 上書きを base_values の直後に重ね、買取単位の対象外にした（§3-3）。
  - R6: Sold out に直したら excluded の確認済みを同時に書く（§3-4）。
  - R7: 保存で同じ advisory lock を取る（§3-4）。
  - R8: Wizard の key に rowKey（§4-4）。
  - R9: 数字の検査と表示の書式（§3-2・§3-6）。
  - R10: 単位の軽い読み込みを切り出し、状態は INSERT 前に読む（§3-2）。
  - R11: load_v102_decisions の2か所（§3-1）。
  - 未解決の v6 の除外は便2で決める（§5）。商品名の行の表示は §10 に書いた。
- 2回目は APPROVE（2026-10-15、/tmp/CC報告ファイル/review-edit-fields/97_design_review2.md）。小さい指摘 S1〜S4 と補足を反映した（§3-3・§3-4・§4-4・§9・§10）。S3 は「extra targets だけを止める」を選んだ。
