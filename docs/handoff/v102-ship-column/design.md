# design: 発送日の専用列（v102）— 発送日が違えば別の件として配信する

状態：KGI K1〜K8 PO 承認済み（2026-10-12「y」）。設計審査 1回目 REVISE → §3b で修正 → 2回目 APPROVE（条件 A・B を card/design に反映済み）。参照：docs/handoff/v102-ship-column/recon.md、docs/handoff/v102-ship-note/design.md（#4161）、docs/adr/ADR-158-product-level-supersession.md、docs/handoff/condition-level-supersession/design.md、docs/adr/ADR-1007-migration-structure-only-run-once.md、docs/adr/ADR-135（main＝本番投入可）／ADR-136（危険PRの GO）。

## 1. 目的（PO の言葉、2026-10-12）
- 「新しい列として発送日情報を入力する欄を作成して、検索ワードでフォーマットを入力する仕組みにする、この発送日情報が異なる場合は別商品として判断する」
- 作り方 ①発送日の列を足す ②発送日の書き方をマスタに登録して決まった形にそろえる ③「同じもの」の決め手に発送日を加える →「合意」。配信シートに発送日の列 →「足す」。
- 「発送時期系→発送日に関する列を新規追加するのでそちらに移管する→まずここを実現してほしい」

## 2. KGI（PO 承認 2026-10-12「y」・○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 配信シートの14列目に「Ship_JA」の見出しがあり、既存13列の名前と並びは変わらない | 本番の配信シートを開いて目視＋ backend/tests/test_tcg_distribution.py（列数14・先頭13列が従来と一致） |
| K2 | 同じ投稿・同じ商品・同じ状態で、発送日が違う件は全部配信される（例：発送日要相談／発売日発送／10/19発送 の3価格 → 3行） | 本番：反映後に再解析した例の投稿で配信行数を数える＋ PG テスト |
| K3 | 発送日が同じなら従来どおり1件（同じ投稿の中の重複は増えない） | PG テスト |
| K4 | 新しい投稿が来たら、古い投稿の同じ商品・同じ状態の件は、発送日が違っても配信から外れる（従来の「最新の投稿だけ」を保つ） | PG テスト（古い投稿 10/16発送・新しい投稿 10/19発送 → 新しい方だけ） |
| K5 | 発送日の文字は「発送時期系」マスタで決まった形にそろう（例：「【10/16発送】」→「10/16発送」、「届き次第発送」→「入荷次第発送」）。マスタに当たらない文字は、拾った文字をそのまま入れる | 単体テスト＋本番の再解析後に Ship_JA の値の種類を数える |
| K6 | v102 の備考（Note_JA）には発送の文字を入れない（発送日の列へ移管） | 単体テスト＋本番：反映後に解析した v102 の行で note_ja に発送の文字が 0 |
| K7 | 同じ順位の件の選び方が毎回同じになる（同じ発送日の重複は投稿の上の行を採る） | PG テスト（同じ入力で2回 → 同じ行が current） |
| K8 | 発送日の英語表記を別の列（ship_en）に持つ。マスタに当たった件は英語になる（例：10/16発送 → Ships 10/16、入荷次第発送 → Ships upon arrival）。当たらない件は空。配信シートには出さない（PO「スプレッドシートへの配信には使用しないが英語圏の顧客用に必要」） | 単体テスト＋本番の再解析後に ship_ja ありで ship_en 空の件数を数える |

## 3. 変更（前後）
※この表は初版。§3b と card.md が優先（migration は2本、関数は `_note_matches`＋`build_ship_labels`、② の並びは gemini_index を含む）。
| 場所 | 変更前 | 変更後 |
|---|---|---|
| migrations/2026101x_xxxxxx_add_analysis_results_ship_ja.sql（新規） | 無し | `ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS ship_ja TEXT;` と `ship_en TEXT`、`ALTER TABLE public.tcg_note_master ADD COLUMN IF NOT EXISTS label_template_en TEXT;` ＋ COMMENT。値の操作なし（ADR-1007）。scripts/run_all_migrations.sh に1行登録 |
| 備考マスタの管理画面（super_admin_note_master.py・note_master.py・NoteMasterPanel.tsx・NoteMasterPage.tsx・CSV 入出力） | label_template_en 無し | 一覧・編集・CSV に label_template_en を足す（既存の金型 TextField、i18n キーを ja/en 両方に追加） |
| backend/app/services/tcg_analyzer_svc.py 発送マスタの読み込み（新規 `load_ship_master`） | 無し | public.tcg_note_master から `enabled AND category = :category` を読み、build_note_ja と同じ形の辞書で返す。分類名は定数 `SHIP_NOTE_CATEGORY = "発送時期系"`（マスタの category 値を指す名前。0 行なら警告ログ） |
| backend/app/services/line_analysis_v102_svc.py `load_v102_masters` | 発送マスタ無し | `ship_entries` を足す |
| 同 `ship_label`（新規） | 無し | `text = ship_note(ship)`。None なら None。`build_note_ja(text, ship_entries)` が値を返せばそれ、無ければ text（拾った文字のまま） |
| 同 `ship_label_en`（新規） | 無し | 同じ当たり方で英語を作る：LITERAL は label_en、REGEX は label_template_en の $1 展開（無ければ label_en）。複数は ", " でつなぐ。当たらなければ None。build_note_ja と当たり判定を共有し、日本語と英語で当たる行がずれないようにする |
| 同 `_analysis_values` | `note_ja = ship_note(ship)` | `ship_ja = ship_label(...)`、`ship_en = ship_label_en(...)`、`note_ja = None`（#4161 以前に戻す） |
| 同 `_UPSERT_SQL` | 23列 | ship_ja・ship_en を INSERT 列・VALUES・DO UPDATE の3か所に足す |
| backend/app/services/tcg_analyzer_svc.py `_merge_supplier_products` | 順位は (商品, 状態) ごとに received_at → computed_at → 仮の行は後 → 先頭1件 | candidates に ship_ja と行番号（ei.line_start）を足す。①(商品, 状態) ごとに「最新の投稿」＝ RANK() OVER (PARTITION BY 商品, 状態 ORDER BY received_at DESC, computed_at DESC) = 1 ②その中で ROW_NUMBER() OVER (PARTITION BY 商品, 状態, COALESCE(ship_ja,'') ORDER BY received_at DESC, computed_at DESC, (id IS NULL), line_start NULLS LAST, id) = 1。①かつ②を current にする。touched_triples・extra_pairs・呼び出し元3つは変えない |
| backend/app/services/tcg_distribution_svc.py | 13列 | DIST_HEADERS の末尾に "Ship_JA"、SELECT に `COALESCE(ar.ship_ja, '') AS ship_ja`、返却の末尾に足す |
| backend/app/services/tcg_product_master_svc.py:668-725 analysis_run_snapshots の複写 | ship_ja 無し | 変えない（履歴表に列が無い。必要になったら別便） |
| v6 の判定・build_note_ja・備考マスタの他の分類 | — | 変えない（v6 の行は ship_ja が NULL のまま＝従来どおり1件） |
| 在庫一覧 GAS（repo 外） | — | この便では変えない（列が増えても壊れないことは recon §6）。表示は別便（GAS の push は PO） |

## 4. 段取り（1つずつ反映→測定）
1. コード PR（上の表）。migration を含むため危険PR（ADR-135/136）。CI 緑・審査後に GO 記録→マージ→デプロイ。
2. 反映の確認：①デプロイ成功 ②列がある ③反映後に解析された v102 の行で ship_ja が入り note_ja に発送の文字が無い ④配信シートの14列目。
3. 発送時期系マスタへの追加（データの変更・候補表を見せて PO の y/n）：試算で当たらない／月の違いが消える形（例「N月入荷分」「M/D〜D発送」「M/D入荷」）と、REGEX 8行の英語の書式（label_template_en、例 `Ships $1/$2`）。
4. 配信対象の期間の v102 の投稿を再解析（データの変更・DRY-RUN→COMMIT、PO の y/n）。前後で「同じ投稿・同じ商品・同じ状態で current が2件以上ある組」の数と配信行数を測る。

## 5. 代替案と選んだ理由
- 発送日を備考（note_ja）のまま決め手にする：備考は今後ほかの情報も入れる欄で、発送日以外の違いでも分かれてしまう → 専用列（PO 決定）。
- 発送日の書き方の新しいマスタ表を作る：同じ語が2か所に分かれる（SSOT 違反）→ 既存の備考マスタの「発送時期系」をそのまま発送日の列の書き方の正本にする。管理画面で追加・編集できる（recon §4）。
- 決め手を (商品, 状態, 発送日) に単純に広げる：古い投稿の「10/16発送」が、新しい投稿の「10/19発送」に上書きされず残る → 「最新の投稿の中だけ発送日で分ける」形にする（K4）。
- マスタに当たらない文字を空にする：違う発送日がまとまってしまう → 拾った文字のまま入れる（今の備考と同じ情報量、K5）。

## 6. リスクと対処
- 分類名「発送時期系」が管理画面で変えられると、全部が拾った文字のままになる → 0 行なら警告ログ。テストで定数とマスタの seed の一致を確認。
- 同じ値にそろう形（「2月入荷分」と「4月入荷分」が両方「入荷次第発送」）は、マスタに行を足すまで1件にまとまる → 段取り3で解消し、再解析後に数で確認。
- 配信行が増える（最大で、同じ投稿の中で発送日だけが違う組の件数分）→ 段取り4で前後の行数を測る。上限 5,000 行（tcg_distribution_svc.py:44）に対し現在の行数を反映前に記録する。
- v102 の備考が空に戻る（#4161 の表示が消える）→ 発送の情報は Ship_JA 列へ移る。在庫一覧で見えるようにするのは GAS の別便。

## 7. 戻し方
- コード：PR を revert（ship_ja の列は残っても読まれない。列の削除は不要）。データ：再解析で従来の形に戻る。

## 外部・過去事例の参照と我々への応用
- 外部事例：使わない（社内の照合キーと配信列の変更で、比べられる公開の実測が無い）。
- 過去事例：#4161（備考への発送の文字）と #4158（予約の判定）の「全件の前後比較→再解析→数で確認」の作法をそのまま使う。照合キーの拡張は condition-level-supersession（product_id → product_id＋condition_id）と同じ段取り。

## 維持の仕組み
- テスト：ship_label（当たる・当たらない・None）、_analysis_values の ship_ja と note_ja、_merge_supplier_products（K2・K3・K4・K7）、配信の14列。CI で毎回走る。
- テスト：分類名の定数と seed migration の category 値の一致。
- 守り手：CI（backend/tests/test_line_analysis_v102_svc.py・test_v102_*_pg.py・test_tcg_distribution.py・test_tcg_result_order.py）。マスタの書き方の追加は管理画面（備考マスタ・分類「発送時期系」）。

## 3b. 設計審査（Fable、REVISE）を受けて確定した点
実装の手順と触るファイルの全列挙は docs/handoff/v102-ship-column/card.md。
1. 基準を origin/main 8a421f22c に更新（recon 冒頭）。
2. `_merge_supplier_products` ② の並び：`received_at DESC, computed_at DESC, (id IS NULL), ei.gemini_index NULLS LAST, ei.line_start NULLS LAST, id`。gemini_index は job 内で一意（人の編集で振り直し）なので、同じ入力なら毎回同じ行（K7）。仮の行（analysis_soldout_extra_targets）の ship_ja・gemini_index・line_start は親の行の値（:1833 の注記「順位の鍵は親の行と同じ」に合わせる）。
3. 当たり判定の共有：`build_note_ja` から `_note_matches(raw_memo, entries, *, raw_state="") -> list[tuple[dict, re.Match | None]]` を切り出す（除外・正規表現エラーの扱いは今のまま）。`build_note_ja` はその結果から今と同じ文字を作る（v6 の結果は不変）。発送用の `build_ship_labels(ship, entries) -> (ship_ja, ship_en)` も同じ結果から日本語と英語を作る。
4. 発送の文字が " / " で複数あるとき（ship_note の区切り）は、部分ごとに：マスタに当たれば日本語＝当たった label をつなぐ（","、build_note_ja と同じ）・英語＝label_en または label_template_en の展開をつなぐ（", "）。当たらなければ日本語＝その部分の文字のまま・英語＝なし。部分どうしは " / " でつなぐ（同じ値は1つ）。英語は全部の部分が当たったときだけ入れ、1つでも当たらなければ ship_en は NULL（K8「当たらない件は空」）。
5. `load_ship_master`：`label_en`・`label_template_en` も読む。例外を握りつぶさない（列が無ければ失敗させる）。0 行なら警告ログ。分類名の定数とマスタの seed（migrations/20260907_100000_tcg_note_master_expand_t004.sql・20260909_130000_tcg_note_b2_t004.sql の category 値）の一致を単体テストで固定。
6. 同じ18行は v6 の build_note_ja（全分類）にも今までどおり使われる（二重用途。v6 の備考は変えない）。
7. migration は1表1本の前例に合わせて2本（analysis_results の ship_ja・ship_en／tcg_note_master の label_template_en）。
8. スキーマ（backend/app/schemas/central_masters.py の TcgNoteMaster 系）に label_template_en を足すため frontend/api-contract/openapi.json を再生成する。
9. 変えない表示：tcg_analysis_review_svc.py:229,291・tcg_import_progress.py:32,133 の note_ja 表示、analysis_run_snapshots の複写、v6 の判定、GAS。
