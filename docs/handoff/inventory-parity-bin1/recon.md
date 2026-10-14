便1 recon（読み取りのみ・基準 origin/main=758d84e8d）
略: RT=backend/app/routers/inventory_offers.py SVC=backend/app/services/tcg_distribution_svc.py PG=frontend/src/pages/inventory/InventoryPage.tsx GI=/tmp/CC報告ファイル/gas_pull_prod/index.html

## 1 Sold out
【事実】
- dist_base SVC:272-327、WHERE SVC:319-326。`ar.exclusion IS DISTINCT FROM 'excluded'` が SVC:322。
- dist_base を使う: RT:330(GET /inventory), SVC:369(distribution_rows_sql), SVC:917(run_distribution=GAS配信), backend/app/line_import_admin.py:117(inspect)。fetch_preview_data(SVC:404-491)は別COUNTクエリで dist_base 非使用。
- 要確認タブは dist_base 非依存(tcg_review_sheet_svc.py:106-109)。dist_base から除いても影響なし。
- status: tcg_analyzer_svc.py:1269-1305 resolve_status_v2。Sold out は migrations/20260903_150000_tcg_status_master_t004.sql ST0010-ST0014(EXCLUDE)。EXCLUDE なら exclusion='excluded'(line_analysis_v102_svc.py:687)→ SVC:322 で既に除外。
- 表記: コードは 'Sold out' 完全一致(SVC:284 COALESCE(ar.status,''))。GAS isSoldOut は trim+小文字の 'sold out'/'soldout'(GI:962-965)。アプリ側に正規化なし。
- 単一正本にするなら SVC dist_base WHERE(配信と/inventoryが同時に変わる)。/inventory のみなら RT _build_view_filters(RT:170-228)だが RT:308 は「配信のWHEREは書かない」と明記。
- テスト影響: backend/tests/test_inventory_distribution_rows.py:138-154(distribution_rows_sql を変更前と1文字も違わないと固定)、test_inventory_distribution_rows_pg.py:90-117,244、test_tcg_distribution.py:339,355,365。dist_base 変更はこれらを更新要。
【未確認】exclusion が 'excluded' でない Sold out 行が本番に実在するか(件数)／GAS画面側除外(GI:1165-1167)を残すか。

## 2 まとめ既定OFF
【事実】
- 既定 True の箇所: RT:295 / backend/app/routers/me_inventory_filters.py:51, :119(キー無し・非boolはTrue) / PG:163, PG:297, PG:311。ADR-1014 本文 docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:15「既定ON」。ja/en `inventory.settings.mergeSamePost*`(1518-1519)。
- 保存先 public.user_inventory_filters.filters(JSONB, migrations/20260602_190000_create_user_inventory_filters.sql)。専用列・migration なし(キー追加のみ)。
- PATCH は全キーを毎回書く(me_inventory_filters.py:132-146)。フィルタ変更時のみ250ms後PATCH(PG:323-348)。→ 既定を false にすると、キー無しの保存行はOFF、true を保存済みの行はONのまま残る。
- 影響テスト: backend/tests/test_me_inventory_filters.py:91-94,107-121、frontend/src/pages/inventory/InventoryPage.noechopatch.test.tsx:40-73、settings.test.tsx、singlefetch.test.tsx。
【未確認】merge_same_post を保存しているユーザー数(true/false/キー無しの内訳)。既存trueの人もOFFにするか(PO判断)。

## 3 24時間以内
【事実】
- posted_ts = sm.line_posted_at(TIMESTAMPTZ, migrations/20260921_110000_pipeline_tables_public.sql:29, SVC:276)。スキーマは datetime(backend/app/schemas/inventory_offers.py:153-154)。
- 既存窓 `_age_window` SVC:212-222(NOW()-max_age_hours、全員共通、SVC:326)。
- RT絞り込みは _build_view_filters(RT:170-228)→rows_f(RT:249)→total/ページ(LIMIT/OFFSET RT:337)に反映。サーバ側で絞れば件数・ページが連動。ブラウザ側は50件/ページ(PG:67)と total がずれる。
- マージ群は同一投稿(gkey に ej.id、SVC:299-301)なので d.posted_ts での判定で結果は同じ。
- GAS: 閲覧端末時刻で判定(GI:1354, FRESH_WINDOW_HOURS=24 GI:937)、日時が空/不正は隠す(GI:1357-1362)。サーバは DB の NOW()。
- 金型: frontend/src/components/ に Switch/Checkbox/Toggle は無い(IconToggleButton のみ)。同ページ前例=PG:472-481 `<Button variant aria-pressed>`、InventoryFilterPanel.tsx に生 checkbox(行120,140,164,195,232,254,273)。scripts/check-ui-governance.js に checkbox 規則なし。ADR-144/docs/CC_UI_GOVERNANCE.md は新部品が要るとき「止めて報告→PO許可で金型登録」。
- i18n: frontend/src/locales/ja.json・en.json 同一キー必須(ADR-027)。
- 保存するなら user_inventory_filters.filters にキー追加(migration不要)。
【未確認】既定ONの24時間窓と max_age_hours(全員共通窓)の関係(本番の実値)／生checkboxの ui-allow 有無／PO許可。

## 4 GASの最初のタブ=ポケモン
【事実】
- アプリ: PG:135 useState("pokemon_booster_box")、固定ボタン PG:576、絞り込み d.tcg_type=:tcg_type(RT:177-179)、tcg_type は products.tcg_type(RT:245)。ラベル=/products/tcg-types(backend/app/routers/products.py:258-285)が type_master(code,name_ja) を sort_order,code 順で返す。
- GAS: Series=type_master.name_ja を p.work_id で結合(SVC:316-317,286)、タブは値から動的生成・件数順・既定「全て」(GI:934,1197-1228)。
- 2つの結び方が別: アプリ=products.tcg_type(文字コード, FK→type_master.code: migrations/20260623_060000_add_products_tcg_type_fk.sql)、GAS=products.work_id(INTEGER→type_master.id: migrations/20260919_030000_master_ssot_fk_work_id.sql)。
- type_master は seed なし(migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql 冒頭「ADR-155 準拠: seed なし」、085/086 も seed 撤去)。中身は画面(ADR-156)/CSV経由。repo に対応表は無い。
【未確認】type_master の実データ(code='pokemon_booster_box' の id と name_ja)／tcg_type と work_id が全商品で同じ種別を指すか／ポケモンに当たる Series 値。

## 5 GASの鮮度
【事実】
- 配信はイベント駆動、定期cronなし(celery_app.py:60-178 に配信エントリなし)。起動: (1)抽出後 tcg_extraction.py:605-608→_enqueue_auto_distribute(628-638)→auto_distribute_after_analysis_task(807-829,time_limit=600) (2)人の修正後 schedule_distribution(670-693): Redisキー tcg:distribution:scheduled(NX,TTL600s)・60秒後(DISTRIBUTION_DELAY_SECONDS)に scheduled_distribution_task(831-852) (3)手動 backend/app/routers/tcg_distribution.py:166-184(super_admin)。TCG_AUTO_DISTRIBUTE 既定 0(docker-compose.yml:104,224)。
- 中止条件: SVC:844-871 再解析未完了、SVC:873-899 extraction_jobs が pending/running/extracted、SVC:904-913 max_age_hours 未設定/不正、SVC:608-612 行数>5000、配信先ごと最大4回リトライ(SVC:969-1005,待ち1→2→4→8秒)。
- 配信はシート全置換 clear()+append_rows(SVC:615-617)。GAS はシートを読むだけ(GC:55-97)。GAS appsscript.json は webapp ANYONE_ANONYMOUS(GA:5-8)。
- UrlFetchApp は repo 内で docs/feedback_form_to_github.gs:127,219,254 のみ(在庫一覧GASでは未使用)。doGet 等の匿名向けAPI・トークン認証の前例: backend/app に該当なし(grep 0件)。
- /inventory 所要: memory project_same_post_rows_sp1_sp2.md の記録 #4249 本番再測定 ON 0.53〜0.64秒・OFF 0.51〜0.53秒(根拠 /tmp/CC報告ファイル/same-post-rows/sp2/perf2/RESULT-20261014-4249.md)。#4241 時点は約1.5秒、変更前約11秒。
- 本番DB読取の前例: docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58 制限付き鍵 salesanchor-claude の ForceCommand は `docker stats --no-stream; free -h; df -h; uptime`(監視のみ)で SQL は不可。無制限鍵 ~/.ssh/manual-only/id_ed25519 は人間の明示許可(都度)のみ(CLAUDE.md・design-b:107)。memory project_cc_db_path_backlog.md「当面は人間仲介(C方式)」。
【未確認】本番の TCG_AUTO_DISTRIBUTE 実値と実際の配信頻度／配信1回の所要時間の記録(repo・memory に数値なし)／GASから外部APIを呼ぶ場合の認証方式(前例なし)／GAS読込時間(別エージェント a841fe954aa0ee813 が測定中)。

## 6 並び替え(GAS方式)
【事実】
- _SORT_COLUMNS RT:117-129、`ORDER BY {sort_col} {dir} NULLS LAST, d.sort_ord ASC` RT:240、ROW_NUMBER() OVER 同order_by→__ord RT:252-255、最終整列 RT:355、LIMIT/OFFSET RT:337。変更は RT:240 と RT:253 の2箇所を同時に。sort 既定 release_date(RT:296-300)、order 既定 asc(RT:301)。
- 英語タイトル d.english_title=COALESCE(p.name_en,'')(SVC:279)なので空は''で昇順なら先頭=GASと同じ(NULLS LAST の影響を受けない)。GAS: 英語タイトル昇順を第1キー、選択列はその中、空欄は昇降とも末尾(GI:1387-1420、1405-1408)、文字列は localeCompare('ja-JP', numeric)。
- PG: 見出しクリック PG:360-367、既定 release_date desc PG:133-134、リセット name asc PG:370-377。
- テスト: backend/tests/test_inventory_distribution_rows_pg.py:224-231 が ORDER BY を再現して検証。backend/tests/test_inventory_list_view.py は sort の 422 検証(行4,21-23。「sort は name のみ許可」)で ORDER BY 内容は見ていない。
【未確認】DB照合順序(collation)による英語タイトル順とGAS localeCompare(ja-JP, numeric)の差／選択列が英語タイトルのときの扱い(GAS B33: 順が変わらない)をアプリでどうするか。

## 本番DBを読み取りで調べる経路(実行はしていない)
【事実】
- エージェントの制限付き鍵では SQL 不可(design-b-ssh-isolation.md:58)。無制限鍵は人間の明示許可・都度(CLAUDE.md「VPS 直作業禁止」)。memory: project_cc_db_path_backlog.md(人間仲介)、feedback_prod_measure_isolated_container.md(重い測定は docker compose run の別コンテナ)、feedback_po_bang_command_script_file.md(PO ! 実行はスクリプト化)、feedback_no_encoded_sql.md(SQL符号化禁止)。
- 調べたい4点を満たす読み取りSQL案(未実行): (a) max_age_hours の実値=設定保存先の読み取り(保存場所は SVC:197-209 _max_age_hours の呼び出し元を要確認)、(b) Sold out かつ dist_base 条件を満たす件数、(c) SELECT t.id,t.code,t.name_ja,count(*) FROM products p LEFT JOIN type_master t ON t.id=p.work_id GROUP BY 1,2,3 と p.tcg_type 別の突き合わせ、(d) SELECT filters->'merge_same_post', count(*) FROM user_inventory_filters GROUP BY 1。
【未確認】(a) の設定保存先(テーブル/列)。

## 関連 ADR
【事実】
- docs/adr/FEATURE-INDEX.md:18 在庫/inventory は ADR-099／ADR-093／ADR-014。配信・merge・sold の項目は FEATURE-INDEX に無し。
- ADR-1014(docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md): 在庫表=配信行。ADR-144(UI金型)、ADR-027(i18n)、ADR-093(/inventory=public.inventory)、ADR-155/156(type_master は seed なし・画面管理)。
【未確認】ADR-1014 の変更(既定OFF・Sold out・並び)が ADR 改訂を要するか(PO判断。ADR優先原則あり)。
