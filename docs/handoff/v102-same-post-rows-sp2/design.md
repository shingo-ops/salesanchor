# design: 在庫表を LINE 解析の行に切り替え・同じ投稿のまとめ ON/OFF（便SP2）

設計者: Opus（2026-10-13）。状態: 設計審査済み（Fable 2回目 APPROVE。§12）・PO 承認済み（2026-10-13）。
- 現状: [recon.md](/docs/handoff/v102-same-post-rows-sp2/recon.md)
- PO の決まり: [card-PO.md](/docs/handoff/v102-same-post-rows/card-PO.md)（SP1 の設計は docs/handoff/v102-same-post-rows/design.md）
- ADR: ADR-093 の一部を置き換える新しい ADR（§9）。関係する ADR は ADR-158、ADR-027、ADR-144。

## 0. PO の決定（原文）
- 2026-10-12（card-PO.md）: 「行をまとめる件を、在庫一覧で ON／OFF できるようにする→する、カスタム設定ページを作り、在庫表ページのヘッダーアクションにアイコンボタンを設定してそこからカスタムで在庫表の見え方を整えられるようにする」
- 2026-10-13: アプリの在庫表を LINE 解析の在庫（GAS と同じ行）に切り替え、まとめの ON/OFF を付ける → y
- 2026-10-13: 「在庫表はテナントに提供するための解析結果を見せるページなのでテナントが見れて良い、ただしsaas管理者メニューのLINE解析システムは引き続き見えないようにする」
- 2026-10-13: 設計者の問い「状態と形態を GAS と同じ英語のまま出す設計で、作るところから本番反映まで進めてよいか（y/n）」→ PO「y」
- GAS 在庫一覧はまとめない（切り替えも付けない）。まとめはアプリの在庫表だけで、利用者ごとに ON/OFF を持つ（card-PO.md の SP 分割）。

## 1. 目的と利用者に見える変化
- アプリの在庫表（/inventory）に、GAS 在庫一覧と同じ行（LINE 解析の配信行）が出る。今は5月に一括投入した88行のまま止まっている。
- 在庫表のヘッダー右に歯車のボタンが付く。押すと横から設定パネルが開き、「同じ投稿のランク違いを1行にまとめる」を ON／OFF できる。設定は利用者ごとに保存される。
- ON のとき、同じ投稿の「状態A-」と「状態B」のような行が1行になる。数量は合計、単価は高い方になる。OFF なら GAS と同じ行がそのまま出る。
- LINE 解析システムの管理メニュー（super admin 専用）は今のまま見えない。

## 2. 対象と対象外
- 対象
  - backend/app/services/tcg_distribution_svc.py（配信行の定義を1か所にまとめる。まとめ方もここに置く）
  - backend/app/routers/inventory_offers.py の list_inventory_view（出どころの切り替え）と、その schema（backend/app/schemas/inventory_offers.py の InventoryRow と InventoryListResponse）
  - backend/app/routers/me_inventory_filters.py（merge_same_post キーの追加）
  - frontend/src/pages/inventory/InventoryPage.tsx と InventoryFilterPanel.tsx、ja.json と en.json、型定義
  - 上のテストと新しいテスト、ADR の追加、ADR-093 への注記、ADR 目次の再生成
- 対象外
  - GAS 在庫一覧の行・列・並び（fetch_output_rows の結果は1文字も変えない）
  - public.inventory の表と /super-admin/inventory-offers（残す。消すかどうかは別の便で PO が決める）
  - DB の列、migration、解析の値、is_current
  - LINE 解析の管理画面とその権限（require_super_admin のまま）
  - 状態・形態の日本語訳の表（§5 の R-L。作らない）
  - 詳細フィルタを設定パネルへ移すこと（今の詳細フィルタは今の場所のまま）

## 3. 変更前と変更後
### 3-1. 配信行の定義を1か所にする（SSOT）
- 変更前: 配信の FROM と WHERE が、fetch_output_rows（:277-300）と fetch_preview_data の件数（:358-372）の2か所に書かれている。
- 変更後: tcg_distribution_svc.py に、配信行を作る SQL を返す関数を1つだけ置く（名前は `distribution_rows_sql(*, include_flag_single: bool, age_condition: str, merge_same_post: bool) -> str`）。
  - 出す列は、GAS の14列に、在庫表が使う列を足したもの。足す列は次のとおり。
    - row_key（行の識別。ar.id の文字列。まとめた行は組の中で並びが最初の行の ar.id）
    - product_id、tcg_type、category（p.category）、supplier_id（sc.supplier_id）
    - unit_canonical
    - 数値のままの単価（price_num）と数量（qty_num）
    - merged_count（まとめた行数。まとめない行は1）
    - sort_ord（result_order_sql() の通し番号。まとめた行は組の最小）
  - fetch_output_rows は、この関数を merge_same_post=False で呼び、14列を今と同じ順・同じ書式で取り出して、sort_ord の順に並べる。
  - fetch_preview_data の件数は、変更前の問い合わせをそのまま残す（products を結合しない）。状態の条件だけ _condition_filter を共有する。
    - 実装時の変更（2026-10-14、CI の PG テスト失敗による）: 当初は件数も distribution_rows_sql で数える設計だったが、products の結合が入り test_tcg_distribution_pg で `integer = uuid` になったため戻した。件数と出力のずれは test_tcg_condition_review.py の output_count と len(fetch_output_rows) の比較で CI が止める。
  - 除外の内訳（:377-409）は、解析の行単位の数え方のまま変えない。
  - cond_filter（FLAG と EXCLUDE の条件。:243-251 と :344-352 に重複している）も、同じ関数の中の1か所で作る。
- まとめ方（merge_same_post=True のときだけ働く）
  - 状態の列は、すべて review_joins の後の値（cr）を使う。GAS の Condition 列が cr.canonical（tcg_distribution_svc.py:263）なので、表示と鍵を同じ値にそろえる。ar.condition_id と ar.condition_basis は使わない（手動の確認や空箱の判定で cr と違う値になる。tcg_condition_review_svc.py:191-199）。
  - 組の鍵は次の7つ。
    - 投稿（ej.id）
    - product_id（ar.product_id）
    - cr.condition_id
    - unit_canonical
    - note_ja（空は空として扱う）
    - ship_ja（空は空として扱う）
    - status
  - SP1 の下書きは ship_ja を鍵に入れていなかった。PO の決まり「発送条件の違う行はまとめない」に合わせて足す。
  - まとめるのは、次のすべてを満たす組だけ。それ以外の行は1行ずつそのまま出す。
    - 2行以上ある。
    - cr.basis が組の中ですべて違う。
    - cr.basis が NULL の行が無い。
    - quantity_normalized が NULL の行が無い。
  - まとめた行の値は、数量が合計（SUM）、単価が最大（MAX）。ほかの列は組の中で同じ値になる。
  - 並びは、まとめた行を組の中で最も前の位置に置く。まとめない行は GAS と同じ並びのまま。
  - ランクを表す語はコードに書かない。マスタが出す根拠（cr.basis）だけで判断する。

### 3-2. GET /inventory の出どころを切り替える
- パス、権限 require_permission("products.view")、ページ送りは変えない。
- 中身は次のとおり。
  1. 設定を読む。load_distribution_settings と _max_age_hours を使う（GAS と同じ読み口）。
     - max_age_hours が未設定または不正（_max_age_hours が None）なら、GAS は配信しない。在庫表も items を空、total を 0 で返し、window_hours を null にする（例外にはしない）。
     - max_age_hours=0 は「絞らない」（tcg_distribution_svc.py:200,:217）。在庫表も絞らず、window_hours に 0 を返す。
  2. distribution_rows_sql(merge_same_post=<問い合わせ値>) を副問い合わせにして、外側で絞り込み・並べ替え・件数・ページ送りをする。
     - 絞り込みは、まとめた後の行にかける。組の中では仕入元・カテゴリー・状態・形態・区分・商品が同じなので、結果は変わらない。数量と単価の範囲は、画面に見える値（まとめた後の値）で判定する。
- 問い合わせ値の対応（新しい名前は増やさず、意味を LINE 解析の列に付け替える）
  | 問い合わせ値 | 変更前 | 変更後 |
  |---|---|---|
  | q | 仕入元名・商品名・英名・商品ID・カテゴリー・型番 | 同じ項目（仕入元名は public.suppliers.name） |
  | tcg_type | p.tcg_type | 同じ（タブはそのまま動く） |
  | category / hide_categories | p.category | 同じ |
  | hide_supplier_ids | i.supplier_id | sc.supplier_id（同じ public.suppliers の id なので、保存済みの設定がそのまま効く） |
  | condition / condition_in | アプリ在庫の状態語 | condition canonical（例 Sealed box）。値は bind で渡す |
  | unit_in | i.unit | unit_canonical |
  | offer_type / offer_type_in | i.offer_type | status。対応は in_stock→'In Stock'、pre_order→'Pre-order' の1つの定数で持つ。対応に無い status の行は、区分の絞り込みが指定されたときは出さない |
  | qty_min / qty_max | i.quantity | 数量（まとめた後）。数量が空の行は、範囲を指定したときは出さない |
  | price_min / price_max | i.unit_price | 単価（まとめた後） |
  | sort | ホワイトリスト | 同じキーを新しい列に付け替える（name→日本語名、condition→canonical、unit→unit_canonical、offer_type→status、quantity→数量、unit_price→単価、supplier→仕入元名、offered_at→投稿日時、release_date→発売日、category、mark）。同順位は sort_ord（GAS の並び）で決める |
  | merge_same_post（新規） | — | true / false。既定は true |
- 応答（InventoryRow）の変更
  - id を int から str（row_key）にする。
  - quantity を任意（null 可）にする。
  - 足す列は次のとおり。
    - note_ja
    - ship_ja
    - status（値のまま）
    - posted_at（offered_at に投稿日時を入れる）
    - merged_count
  - offer_type は status から1つの定数で写す（'In Stock'→in_stock、'Pre-order'→pre_order）。対応に無い status は null。絞り込み（offer_type_in）も同じ定数を逆に使う。型は `str | None` に変える。
  - 消す列は無い。ship_timing は null を返す。is_best 系は今も {} の写像なので false のまま。
- 応答（InventoryListResponse）に window_hours（int か null）を足す。
- 候補一覧（suppliers、categories、conditions、units）は、同じ distribution_rows_sql（まとめなし）から DISTINCT で作る。public.inventory は読まない。

### 3-3. 利用者ごとの設定に merge_same_post を足す
- InventoryFilterPayload に `merge_same_post: bool = True` を足す。直す所は、GET の組み立て、PATCH の JSON、フロントの送信の3か所で、どれも同時に直す（PATCH は全体を置き換えるので、1か所でも漏れると消える）。
- 保存済みの3行には、このキーが無い。読むときは既定の true になる。migration は使わない（ADR-155）。
- 本番の保存済み3行は、show_conditions と show_units がどれも空（/tmp/CC報告ファイル/same-post-rows/sp2/ten2.out）。古い語の値を外す処理は作らない。もし古い語（shrink など）が残っていても、IN の絞り込みで0件になるだけで壊れない（利用者が詳細フィルタで選び直せる）。

### 3-4. 画面
- ヘッダー
  - PageLayout の headerAction に HeaderButton を置く。指定は variant="icon"、icon は PAGE_ICONS.settingsSolid、aria-label は t("inventory.settings.open")。
- 設定パネル
  - frontend/src/components/Drawer.tsx を使う。title は t("inventory.settings.title")。
  - 中には1項目だけを置く。見出しは t("inventory.settings.mergeSamePost")、説明は t("inventory.settings.mergeSamePostNote")。
  - 切り替えは Button 金型で行う。variant は ON なら primary、OFF なら secondary にし、aria-pressed を付ける。文言は t("inventory.settings.on") / t("inventory.settings.off")。
  - この形は同じページの InventoryPage.tsx:402-411 と同じ。生の checkbox、色の直書き、新しい CSS の値は使わない。
  - 切り替えたら、今の詳細フィルタと同じ保存の流れ（:249-269、250ms 後に PATCH）で保存し、一覧を読み直す。
- 一覧
  - 状態は canonical の値をそのまま出す（GAS と同じ英語。§5 の R-L）。t("inventory.condition.*") は通さない。
  - 形態は unit_canonical の値をそのまま出す。
  - 区分は、offer_type があれば t(`inventory.offerType.${offer_type}`)、null なら status の値のまま出す。今の表示（:560-564）は offer_type を見ているので、null の分岐だけ足す。
  - 列を2つ足す。どちらも隠せる列（HIDEABLE_COLUMNS）に入れる。
    - 備考（note_ja）。見出しは t("inventory.col.note")。
    - 発送（ship_ja）。見出しは t("inventory.col.ship")。
  - 数量が空の行は、空欄にする（GAS と同じ）。
  - まとめた行（merged_count が2以上）には、数量の横に t("inventory.mergedCount", { count }) を出す。例「2行分」。キーは基底の inventory.mergedCount を ja と en の両方に置く（frontend/scripts/check-i18n-missing-keys.js:21,:61-64 が基底キーを求める）。複数形のキーを足すなら ja と en に同じキーで置く。
  - 注意書き expiryWarning は「LINE の投稿から {{hours}} 時間以内のオファーを表示しています。」に変える（en も同じ意味）。hours は応答の window_hours。0 のときは t("inventory.windowUnlimited")、null のときは t("inventory.distributionOff") を出す。
- 選択（selectedIds）は Set<string> にする。preselectedInventoryIds の型も string[] にする（渡してくる画面は0件。recon §4）。
- 新しい文言はすべて ja.json と en.json に同じキーで入れる（ADR-027）。

## 4. 代替案と選んだ理由
| 案 | 中身 | 判断 |
|---|---|---|
| A（採用） | 配信行の SQL を1つの関数にまとめ、GAS（まとめなし）と在庫表（ON/OFF）の両方がそれを使う | 行の定義が1か所になる（SSOT）。GAS の出力は変わらない。DB に新しい表も複製も作らない |
| B | LINE 解析の行を public.inventory へ書き写す | 同じデータが2か所にでき、ずれる。PO の「データを分散させない」に反する |
| C | 在庫表専用の SQL を inventory_offers.py に新しく書く | 配信の条件が3か所目になり、GAS と在庫表で行がずれる |
| D | まとめを画面（フロント）で行う | ページ送りと件数が合わなくなる。まとめの決まりがサーバーとフロントに分かれる |
| E | 設定を新しいページ（別の URL）にする | 設定は1項目だけなので、一覧を見ながら切り替えられるパネルにした。Drawer は onOpenFullPage を持つので、項目が増えたらページへ広げられる |

## 5. リスクと対処
- R-L（表示の語）: 状態と形態が英語のまま出る（例 Sealed box、MasterCarton）。
  - GAS 在庫一覧と同じ語なので、テナントが見比べてもずれない。
  - 日本語にするには訳語の表（マスタ）が要る。訳語を推測で作らないため、この便では作らない。PO の判断で別の便にする。
- R-T（テナントへの公開）: 解析の行がテナントの営業担当に見える。PO の決定どおり。
  - 見えるのは GAS 在庫一覧と同じ14列に、次の列を足したもの: row_key（analysis_results の id）、product_id、supplier_id、tcg_type、category、unit_canonical、offer_type、merged_count。
  - 解析の根拠（原文、condition_basis、要確認の理由）は応答に入れない。
- R-P（重さ）: 1回の表示で、配信行を作り、絞り込んでから50行を返す。配信行は多くても約956行（recon §3。確認の条件を入れずに数えた上限）。
  - 配信と同じ SQL で、配信は数秒以内に終わっている。
  - 受入の T7 で、本番の応答時間を測る。
- R-S（保存済みの絞り込み）: 本番の保存値は空なので、影響を受ける利用者は0人（§3-3）。
- R-E（空の窓）: max_age_hours が未設定なら、在庫表も空になる（GAS と同じ）。注意書きで分かるようにする。
- R-1（ダメージの程度違い）: まとめない（card-PO.md の R1 の既定どおり）。

## 6. 影響範囲（呼び出し元の全走査）
- fetch_output_rows: run_distribution（backend/app/services/tcg_distribution_svc.py:853）と backend/app/line_import_admin.py:117。関数の引数は変えない。どちらも出力が同じなので、影響は無い（T1 で固める）。
- fetch_preview_data: 配信プレビューの画面。件数の定義は今と同じ（まとめなし）なので、値は変わらない（T1）。
- GET /inventory を呼ぶのは InventoryPage.tsx だけ（frontend の grep で確認する。実装カードの最初の手順）。
- InventoryRow を使う所: inventory_offers.py の _project_inventory_rows（/inventory 専用）。super-admin 側は InventoryOfferResponse で別物。

## 7. 受入条件と検証方法
| # | 基準 | 検証方法 |
|---|---|---|
| T1 | GAS の出力（fetch_output_rows の14列と並び）と配信プレビューの件数が、変更前と1文字も変わらない | PG テスト。固定データで変更前の SQL と新しい関数の結果を比べる。本番では、デプロイ前後の配信件数（プレビューの output_count）を比べる |
| T2 | まとめ ON で、同じ投稿の R2:状態A- と R2:状態B の組が1行になる。数量は合計、単価は最大、merged_count=2（card-PO の K2） | PG テスト。本番では、デプロイ後に同じ関数で ON と OFF の行数を数え、差が「merged_count の合計 − まとめた行数」と一致する（recon の9組は上限の目安で、合格の基準にしない） |
| T3 | 備考が違う組、発送が違う組、status が違う組、数量が空の組、根拠が同じ組は、ON でもまとまらない（K1・K5） | PG テスト（組の種類ごとに1本） |
| T4 | まとめ OFF の在庫表の行数が、同じ時点の配信件数と同じ | PG テスト。本番では、OFF の total とプレビューの output_count を比べる |
| T5 | merge_same_post が保存され、読み直しても残る。キーの無い保存済みの行は true で読める | backend の test_me_inventory_filters に追加 |
| T6 | 歯車のボタンで設定パネルが開き、切り替えると PATCH が merge_same_post 付きで送られ、一覧の GET に merge_same_post=false が付く | frontend の単体テスト。CommerceNavigationButtonMigration.test.tsx の URL は merge_same_post=true を含む形に直す |
| T7 | 本番の GET /inventory（per_page=50）の応答が2秒以内 | デプロイ後に docker compose run の別コンテナで、同じ関数を ON と OFF で時間を測る（読み取りのみ。稼働中の backend コンテナでは測らない） |
| T8 | テナントの利用者（products.view を持つ）が在庫表を見られる。LINE 解析の管理メニューと /super-admin の API は 403 のまま | backend のテストを新しく書く: products.view あり→200、なし→403、super admin でない利用者が LINE 解析の API→403 |
| T9 | 375px で横にはみ出さない | 既存の horizontal-overflow.spec.ts が通る |
| T10 | i18n の ja と en のキーが一致し、ハードコードの日本語が無い | 既存の CI（i18n の検査） |
| PO 確認 | 在庫表に今日の LINE の行が出る。歯車 → OFF で件数が増え、ON で戻る | PO が画面で見る（数は報告に書く） |

## 8. 実装の分け方（1つの PR）
- 順番: backend の関数 → GAS の出力が同じであることのテスト → /inventory → 設定キー → フロント → ADR。
- /tmp/CC報告ファイル/same-post-rows/draft-merge/tcg_distribution_svc.diff（SP1 の下書き。13列・GAS でもまとめる・鍵に ship_ja なし・ar の列を使う）は使わない。テストの書き方だけ test_same_post_rows_pg.full.py を参考にしてよい。
- T1 のテストデータは、ei.id が行ごとに違う形で作る（ei.id の同点は今の SQL でも並びが決まらない。本番で同点があるかは未確認なので、テストには入れない）。
- build_condition_filter_clause は super-admin の一覧（inventory_offers.py:397）で使い続けるので、import と関数は残す。
- 危険なパス（migrations/、deploy.yml、本番の scripts/）は含まない。ADR-136 の GO の対象外だが、GO 記録は委任の範囲で残す。

## 9. ADR
- 新しい ADR（次の空き番号 = ADR-1014）「在庫表は LINE 解析の配信行を出す」。様式は ADR-113 の形にする。
  - Why: 在庫表が5月の88行のまま止まっていて、テナントに渡す解析結果を見せる場所が GAS だけだった。行の定義を1か所にして、GAS と在庫表をずらさない。
  - 置き換える部分: ADR-093 の「/inventory は public.inventory を表示する」。
- docs/adr/ADR-093-inventory-table-product-master-redesign.md の冒頭に、置き換えた部分と新しい ADR への参照を書く。本文は消さない（同じ番号の docs/adr/ADR-093-sales-management-page.md は触らない）。
- `node scripts/generate-adr-index.js` で目次を作り直す。

## 10. 維持の仕組み
- 配信行（GAS 出力と在庫表）の定義は distribution_rows_sql の1か所だけ。プレビュー件数は変更前の問い合わせを残し、_condition_filter だけ共有する。T1 と T4、および test_tcg_condition_review.py の output_count と len(fetch_output_rows) の比較が、ずれを CI で止める。
- まとめの鍵と条件は同じ関数の中に置き、テスト T2・T3 で固める。
- 守り手: backend/tests/test_inventory_distribution_rows_pg.py

## 11. 外部・過去事例の参照と我々への応用
- 該当なし。理由: 社内の SQL を1か所にまとめる変更と、利用者ごとの表示設定の追加で、外部の事例で成否が変わる判断を含まない。

## 12. 設計審査（Fable）
- 1回目（2026-10-13）: REVISE。必須修正7件。全文は /tmp/CC報告ファイル/same-post-rows/sp2/review-fable-1.md。
  1. 鍵と判定を cr の列にする → §3-1 に反映。
  2. 956行と9組は上限 → R-P と T2 に反映。
  3. T8 の根拠のテストが別画面 → backend の権限テストに差し替え。
  4. offer_type の値 → status からの写像を1つの定数で持つ（§3-2、§3-4）。
  5. max_age_hours=0 → window_hours=0 と windowUnlimited（§3-2、§3-4）。
  6. 古い語を外す処理 → 作らない。本番の保存値は空（§3-3）。
  7. パスと ADR-093 のファイル名、下書きを使わないこと → §6、§8、§9。
  - 任意の指摘 A・B・C・D・F も反映した。E は今の型のままで足りる。
- 2回目（2026-10-13）: APPROVE。全文は /tmp/CC報告ファイル/same-post-rows/sp2/review-fable-2.md。実装への指示 G1（mergedCount は基底キー）を §3-4 に反映した。PO の承認が必要（状態・形態の語を英語のまま出す R-L）。
