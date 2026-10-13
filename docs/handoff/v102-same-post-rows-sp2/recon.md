# recon: 在庫表を LINE 解析の行に切り替え・同じ投稿のまとめ ON/OFF（便SP2）

調査: Sonnet（2026-10-13）、確認と整理: Opus。基準は origin/main 392ae28bf。
生の調査記録（コード全文つき）は社外の作業フォルダ /tmp/CC報告ファイル/same-post-rows/sp2/recon-raw*.md にある。この文書には結論と行番号だけを書く。

## 0. 既存 ADR の検索
- `git grep -il inventory docs/adr/` と docs/adr/FEATURE-INDEX.md で確認した。
- docs/adr/ADR-093-inventory-table-product-master-redesign.md
  - /inventory は public.inventory（仕入元オファー）を読み取り専用で表示すると決めている。取り込み元は Discord 受信通知。
  - この便で決定が変わるので、新しい ADR で置き換える部分を明記する。
- docs/adr/ADR-014（整形済み在庫一覧はスプレッドシートで共有）。GAS 在庫一覧の根拠。この便では変えない。
- docs/adr/ADR-158-product-level-supersession.md（is_current）。この便では is_current を変えない。
- docs/adr/ADR-155（migration で値を決め直さない）。この便に migration は無い。
- docs/adr/ADR-027（i18n）、docs/adr/ADR-144（UI 金型）。新しい文言と部品に適用する。
- 「LINE 解析の在庫を /inventory に出す」という決定は docs に無かった（grep 0件）。今回、PO が 2026-10-13 に決めた（card-PO.md への追記を参照）。

## 1. アプリの在庫表の現状
- frontend/src/pages/inventory/InventoryPage.tsx（615行）が GET /inventory を呼ぶ。
- backend/app/routers/inventory_offers.py:171-367 list_inventory_view
  - 権限は require_permission("products.view")（:174）。
  - FROM は public.inventory i に、public.suppliers と public.products を LEFT JOIN（:109-111）。
  - 常に付く条件は i.status='in_stock' と、期限切れでないこと（:212-215）。
  - 絞り込みは q（:226-231）、tcg_type（:217-219。タブの値）、category、仕入元を隠す（:233-242）、カテゴリーを隠す（:244-249）。
  - ほかに状態（:251-256）、形態の unit_in（:257-262）、区分の offer_type_in（:263-268）、数量・単価の範囲（:270-281）がある。
  - 並べ替えはホワイトリスト（:122-134）、ページ送りあり。
  - 候補一覧は、仕入元（:305-314）、カテゴリー（:317-327）、状態（:331-346）、形態（:347-357）。
- 本番の public.inventory は88行。すべて 2026-05-26 08:41 の一括投入（recon-raw2 の本番実測）。
- LINE 解析から public.inventory へ書く経路は無い（grep 0件）。

## 2. GAS 在庫一覧（LINE 解析の配信）の現状
- backend/app/services/tcg_distribution_svc.py:225-324 の fetch_output_rows が、配信の14列（DIST_HEADERS :47-62）を作る。
  - Condition は cr.canonical の英語のまま（:263）。Status は ar.status の値のまま（:267）。単位の列は無い。
- 対象行の条件は :293-300 にある。
  - pid_resolved
  - is_current
  - needs_review が偽
  - 除外されていない
  - unit_resolved
  - 価格がある
  - 投稿日時がある
  - FLAG_ の状態でない
  - effect が EXCLUDE でない
  - 投稿からの時間（max_age_hours）
- 並び順は backend/app/services/tcg_result_order.py:20-32 の result_order_sql()。
- 同じ FROM と WHERE が fetch_preview_data の件数（:357-373）にもう1つ書かれている（2か所に重複している）。
- 設定は public.tcg_distribution_settings。本番は include_flag_single=false、max_age_hours=48。
  - 読み口は _max_age_hours（:197-209）と _age_window（:212-222）。
- 解析系のテーブルには tenant 列も RLS も無い（本番で確認）。GAS もテナントで分けずに全員へ同じ行を出している。

## 3. 本番の配信相当の行（48時間・2026-10-13 時点の概数。dist1.out / dist2.out）
- 956行（review_joins を入れずに数えた上限。Error 30行などの配信されない行を含む）。
  - 数量が空 22行、ship_ja あり 21行、note_ja あり 35行。
  - status は In Stock 898行、Pre-order 58行。
- unit_canonical は Box、Case、Set、Pack、Piece、Booklet、MasterCarton、個。
- condition canonical は Sealed box、Case、Damaged sealed box、No shrink box、Damaged case、Searched pack、Error、Unsearched pack、Opened box、Searched box。
- まとめの条件（design §3-1）に当たる組は、同じく上限で9組18行。すべて R2:状態A- と R2:状態B の組だった。

## 4. 見積との連携
- InventoryPage.tsx:79-83 は、location.state の preselectedInventoryIds: number[] を読む。:96-97 で選択の初期値にしている。
- preselectedInventoryIds を積んで /inventory へ来る画面は0件。在庫表から見積へ戻る navigate も0件。
- i18n の applyToQuote と createPO を使っている所は0件。
- 見積の backend（schemas/quote.py、routers/quotes.py:231）は inventory_id を持たず、保存もしない。
- → 選択した行の id は、どこにも渡されていない。id が int から文字列に変わっても、壊れる所は無い。

## 5. 表示の語
- ja.json と en.json の inventory.condition.* は16キー。値は shrink や sealed など、アプリ在庫の語。
- inventory.unit.* は5キー（piece、pack、box、case、set）。inventory.offerType.* は2キー（in_stock＝在庫、pre_order＝予約）。
- LINE 解析の canonical（Sealed box、Damaged case など）を日本語にする表は、どこにも無い（grep 0件）。
- backend/app/services/condition_vocab.py:54-71 の VER41_TO_CONDITION は5語しか写さない（Damaged case、Searched pack、Opened box、Searched box、Error は無い）。
- inventory.expiryWarning は「オファーは掲載から18時間で自動的に削除されます。」で、条件なしで常に出る（InventoryPage.tsx:492-497）。

## 6. 利用者ごとの在庫表設定
- backend/app/routers/me_inventory_filters.py（153行）。GET は :79、PATCH は :116。保存先は public.user_inventory_filters（user_id が主キー、enabled、filters の JSONB）。
- モデルは InventoryFilterPayload（:29-49）。キーは11個。
- PATCH は全体を置き換える（:125-148）。キーを足すときは、次の4か所を同時に直す。
  - モデル
  - GET の組み立て（:101-112）
  - PATCH の JSON（:125-137）
  - フロントの送信（InventoryPage.tsx:249-269）
- 本番の行は3つ。

## 7. 金型（共通部品）
- PageLayout の headerAction（frontend/src/components/PageLayout.tsx:8）。
- HeaderButton variant="icon"（aria-label が必須）。
- アイコンは frontend/src/constants/icons.tsx の PAGE_ICONS.settingsSolid。
- frontend/src/components/Drawer.tsx:22-30。
  - props は open、onClose、title、children、onOpenFullPage、footer。
  - フォーカストラップと Esc で閉じる動きがある。
  - 使用例は CompaniesPage.tsx:565-580。
- ON/OFF に使える部品。
  - IconToggleButton（アイコン専用）。
  - Button の variant を primary と secondary で切り替え、aria-pressed を付ける形。この形は同じ InventoryPage.tsx:402-411 で使われている。
  - Switch と Checkbox の金型は無い。生の checkbox を新しく使うことはしない。

## 8. テスト
- backend/tests/test_inventory_list_view.py は、GET /inventory の問い合わせ値の検証（422）だけを見ている。
- backend/tests/test_me_inventory_filters.py は、既定値、往復、型の誤りを見ている。
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:47-71 は、在庫表の GET の URL が完全に一致することを求める。
- frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx:36。
- frontend/tests-e2e/horizontal-overflow.spec.ts:76 は、/inventory が 375px で横にはみ出さないことを見る。
- list_inventory_view の SQL の中身を固めるテストは無い。
- 下書きの PG テスト /tmp/CC報告ファイル/same-post-rows/draft-merge/test_same_post_rows_pg.full.py は、GITHUB_ACTIONS のときだけ動く。
