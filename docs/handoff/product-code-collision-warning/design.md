# Phase 3 設計 — product-code-collision-warning

**対象ADR**: ADR-155  
**recon**: docs/handoff/product-code-collision-warning/recon.md  
**日付**: 2026-10-09  
**担当**: 実装担当（Sonnet）。設計はカード（Opus 発行・PO 承認済み）

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本便は自社マスタの内部整合の警告で、根拠は PO の業務知識（型番の取り違い再発防止）と自社の実データの調査。出典と数値のそろった外部事例は確認していない。
- 社内の過去事例: 除外ワードで公式の重なりを見分けた規則（excl-official）。推奨語の規則に同じ内容を使う。

---

## 変更前 → 変更後

| 入口 | 変更前 | 変更後 |
|---|---|---|
| 新規（画面・登録スクリプト） | `create_product` は重なりを見ない | 返り値に `code_collisions` を足す（保存は止めない） |
| 更新（画面） | `update_product_detail` は重なりを見ない | 返り値に `code_collisions` を足す（保存後の値で判定、自分は除く） |
| CSV 新規 | mark の完全一致のみ・相手1件・`load_existing_marks` | 正規化一致・重なった相手ごとに `MARK_ALREADY_USED_BY_<id>`・行に `code_collisions` |
| CSV 更新 | warnings は常に空 | mark を変える行だけ同じ判定で warnings と `code_collisions` |

判定は `backend/app/services/tcg_product_code_collision_svc.py` の `find_code_collisions` が唯一の場所。

## 触らない範囲

- 照合（`backend/app/services/extraction_judgement_svc.py` の match_product ほか）、v6（tcg_analyzer_svc.py）、配信
- 画面と i18n（2/2 で行う）、マスタのデータ、migration（表は変えない）

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 正規化一致・作品をまたぐ・自分を除く・空値は無視・推奨語の規則が働く | `pytest backend/tests/test_tcg_product_code_collision_svc.py` |
| 新規・CSV 新規・CSV 更新が警告を返し、保存は止まらない | `pytest backend/tests/test_tcg_product_code_collision_wiring.py` |
| 無効商品を除く（SQL の is_active）と更新の実 DB 動作 | CI の PG 付きジョブで `backend/tests/test_tcg_product_code_collision_pg.py`（ローカルでは skip） |
| 既存の挙動が壊れていない | `pytest backend/tests/test_tcg_product_import.py backend/tests/test_tcg_product_roundtrip.py backend/tests/test_tcg_product_master.py` |
| API の形が契約ファイルと一致 | CI「API contract is up to date」（`frontend/api-contract/openapi.json` を再生成して同梱） |
| 新しい DB 書き込みが無い | 新モジュールの SQL が SELECT のみ（単体試験で全文を検査） |

## 技術 How・KPI

- 判定: 渡された product_code・mark（空は除く）を normalize_for_match し、有効商品（is_active=TRUE、全作品）の product_code・mark の正規化値と比べる。1商品1件。`matched_field` は相手側の項目（product_code を先に見る）
- 推奨語: 相手の名前全体＋型番でない検索ワードを候補に、3文字未満・受け手自身の名前や検索ワードに含まれる語・受け手の既存の除外ワードを除く（excl-official と同じ規則）。逆向き（`suggest_add_to_other`）は対称
- `already_excluded_by_this` / `already_excluded_by_other`: 除外ワードのうち、相手の名前・検索ワードに既に当たっているもの
- 応答の型: `backend/app/schemas/tcg_product_code_collision.py`。3つの API に `response_model` を付け、`response_model_exclude_unset=True` で既存の欄の形を変えない
- KPI: 型番が重なる組を作る操作で、4つの入口すべてが重なった相手の商品IDを返す（単体・配線試験で確認）

## 弊害・トレードオフ

- 判定のたびに有効商品の型番を全件読む（件数上限なし）。CSV 新規は行ごとに1回 → 行数が多いと遅くなる。対策: 必要になった時点で読み込み結果の再利用を検討（今は足さない）
- 公式でも型番が重なる組は常に警告が出る。対策: 除外ワードで見分けた組は `already_excluded_by_*` で区別できる（画面での扱いは 2/2）
- CSV 新規の `MARK_ALREADY_USED_BY_<id>` は、以前は完全一致の1件だけだったが、正規化一致の全件に変わる（警告が増える）

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 単体試験（RED）→ 新モジュール（GREEN） | Generator |
| 2 | 4つの入口へ配線、`load_existing_marks` を削除 | Generator |
| 3 | 応答の型と openapi.json の再生成 | Generator |
| 4 | 配線試験・PG 試験の追加 | Generator |

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_product_code_collision_svc.py`（判定規則）
- 守り手: `backend/tests/test_tcg_product_code_collision_wiring.py`（入口ごとの配線。`load_existing_marks` が復活しないことも検査）
- 守り手: `.github/workflows/api-contract-check.yml`（応答の形のずれを赤にする）

## 戻し方

- この PR を revert する。表・データ・migration の変更は無いため、データの戻しは不要
- 入口の返り値に足した `code_collisions` を読む側（2/2 の画面）は、欄が無くても動く作りにする

## 継続

- 完了後の監視: 2/2 の画面で警告が表示されること
- 次フェーズへの引き継ぎ: 2/2（画面と部品集への登録、i18n 文言）

---

## 画面（2/2）

**recon**: docs/handoff/product-code-collision-warning/recon.md「画面（2/2）」
**対象ADR**: ADR-155・ADR-144・ADR-027・ADR-067

### 外部・過去事例の参照と我々への応用

- 該当なし：自社マスタの警告表示で、根拠は PO の指示（「どの商品と重複するかも表示すると親切」「画面に残る警告の枠を部品集に登録する」）。出典と数値のそろった外部事例は確認していない。

### 変更前 → 変更後

| 項目 | 変更前 | 変更後 |
|------|-------|-------|
| 部品集 | 残る警告の枠が無い | `frontend/src/components/Callout.tsx`・`frontend/src/components/Callout.css`・`frontend/src/components/Callout.stories.tsx`（variant warning/info、role は alert/status、閉じるボタン無し、色・余白は既存トークンのみ） |
| 商品詳細ドロワー（新規） | 保存後に必ず閉じる | 応答の code_collisions が1件以上なら閉じず、Callout（warning）で相手商品・推奨語を表示。0件なら今どおり閉じる。重なり表示中は二重登録を防ぐため保存ボタンを無効のままにする |
| 商品詳細ドロワー（編集） | 保存後に何も出さない | 応答の code_collisions があれば Callout を表示 |
| CSV 取り込み preview | 「商品{{value}}でも同じ型番が使われています。」 | 「型番が {{value}} と重なっています。除外ワードの追加をおすすめします」＋行の下に Callout（相手の商品名・作品・推奨語） |
| i18n | - | `codeCollision.*` を ja.json・en.json に同一キーで追加。`productCsv.messages.markUsed` の文言変更 |

### 触らない範囲

- バックエンド・ProductMasterDrawer（解析レビュー）・保存を止める動き・語の自動登録（案内だけ）

### 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Callout が variant ごとに warning=role alert・info=role status で出る。閉じるボタンが無い | `frontend/src/components/Callout.test.tsx` |
| 新規作成の応答に code_collisions があるとき、ドロワーが閉じず警告に相手商品名・作品・重なった値・推奨語が出る | `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx` |
| 推奨語が両方空のとき「除外ワードは登録済みです」が出る | 同上 |
| code_collisions が空または欄が無いとき、今までどおり閉じる | 同上 |
| CSV preview の行に新文言と Callout が出る | `frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx` |
| ja.json・en.json が同一キー・日本語直書きが無い・デザイントークン規約を満たす | `cd frontend && npm run check:all` |
| 型検査・build が通る | `cd frontend && npm run build` |

### 技術 How・KPI

- 表示は共通部品 `frontend/src/features/tcg-product-import/CodeCollisionNotice.tsx`1つに集約し、ドロワーと CSV preview の両方から使う。Callout は汎用部品として components/ に置く
- KPI: 上記7基準が全て通ること

### 弊害・トレードオフ

- CSV preview の「{{value}}」は API の警告コード末尾の相手商品IDのまま（カード指定の文言）。相手の名前は行の下の Callout で表示する
- 新規作成で重なりが出たあと、同じドロワーのまま続けて登録はできない（二重登録防止）。閉じて開き直す

### 維持の仕組み

- 守り手: Callout.test.tsx・TcgProductDetailDrawer.test.tsx・TcgProductImportPanel.test.tsx
- 守り手: `npm run check:stories`（Callout.stories.tsx の存在）・`check:i18n-missing-keys`・`check:css-colors`

### 戻し方

- この PR を revert する（バックエンドの応答は変わらず、画面が警告を出さない元の状態に戻る）

### 継続

- 完了後の監視: 本番で型番が重なる商品を保存したとき警告の枠が出ること（PO 確認）

## 除外ワードの追加（3）

### 方針

- 型番重なりの警告（CodeCollisionNotice）の推奨語ごとに [この商品に追加] [相手に追加] を出す。語の自動登録はしない（押したときだけ）
- 相手に追加: 確認（ConfirmModal）→ GET /tcg/products/detail/{相手のid} で最新の値と revision を取る → 除外ワードに足して PUT /tcg/products/detail/{相手のid}（audit_log に変更前後が残る）。既存語なら PUT せず「登録済み」。409（revision 不一致）は既存の productDetail.conflict を出し、ボタンは残るので押し直すと読み直して足し直せる
- この商品に追加: 編集中は入力欄に足すだけ（API なし・保存で一緒に登録）。新規作成直後は作成応答の product_id に対して上と同じ経路（確認つき）
- API を呼ぶのは productDetailModel.ts の addExcludeWord 1か所。PUT の body は buildUpdateBody をドロワーの保存と共用（二重に書かない）
- CSV preview: MARK_ALREADY_USED_BY_ の {{value}} を同じ行の code_collisions の「商品名（作品）」に置き換える（無ければ id のまま）。[相手に追加] のみ出す
- backend・新しい部品は無し。add_exclude_keyword は使わない

### 基準と検証方法

|基準|検証方法|
|---|---|
| 相手に追加: 確認後に GET→PUT が相手のidで呼ばれ、revision と足した語を含む body が送られ「追加しました」が出てボタンが消える | TcgProductDetailDrawer.test.tsx |
| 既存語は PUT せず「登録済み」 | 同上 |
| 失敗は追加失敗の表示でボタンが残る・409 は conflict 文言 | 同上 |
| 新規作成直後の [この商品に追加] が作成応答の product_id に PUT する | 同上 |
| 編集中の [この商品に追加] は API を呼ばず除外ワード欄に足す | 同上 |
| CSV の文言が相手の商品名（作品）になる・見つからなければ id | TcgProductImportPanel.test.tsx |
| CSV 行に [相手に追加] だけが出る | 同上 |
| ja.json・en.json 同一キー・日本語直書き無し | cd frontend && npm run check:all |
| 型検査・build | cd frontend && npm run build |

### 外部事例

該当なし（理由: 既存の保存経路を再利用する画面の追加で、新しい仕組みを導入しないため）。

### 弊害・トレードオフ

- 追加のたびに GET と PUT の2回呼ぶ。同時に別の人が変えると 409 になり、押し直しが必要
- english_title・mark が NULL の商品に追加すると、PUT でそれらが空文字になる（ドロワー保存と同じ既存挙動）

### 維持の仕組み

- 守り手: TcgProductDetailDrawer.test.tsx・TcgProductImportPanel.test.tsx

### 戻し方

- この PR を revert する（バックエンド変更なし）

### 継続

- 本番で [相手に追加] を1回実行し、相手商品の audit_log に変更前後が残ることを PO が確認
