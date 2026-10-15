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

## 5. 便2（v6）
- item_rejection の代わりに、value-override 専用の検査で v6 も通す（件なし 404、source 不一致 422 は同じ）。
- v6 の再解析（`backend/app/services/tcg_analyzer_svc.py` 1489-1505 行と 1708-1790 行）:
  - product_id 行がある件は今も上書きしないので、即時 UPDATE の値が残る（追加の作業なし）。
  - product_id 行が無い件は、UPSERT の直後に `load_v102_decisions` → `apply_value_overrides` で該当列を UPDATE する。
- 画面: reviewFixRows の v102 の条件を外し、v6 も同じ9行にする。状態は v6 でも condition_review が動く（95 §5）。
- 便2の詳細は便1マージ後に本書へ追記して、同じ審査を通す。未決の点:
  - v6 では状態以外が理由の除外（本番で In Stock + excluded が 90 件）がある。status の上書きで exclusion を None にすると、その除外まで外れる。v6 では「status 由来の除外だけを動かす」別の規則が要る。
  - v6 の status 'active' の扱い。

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
