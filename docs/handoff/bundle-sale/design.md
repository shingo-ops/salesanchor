---
mode: handoff
adr: ADR-1027
status: Proposed（設計案・設計審査済み・KGI は PO 合意 2026-10-17・実装未着手）
---

# design — まとめ売り（N単位セット）の読み取り

この文書は何か: 「40パックセット/¥24,000 残り15」のようなまとめ売りの行を、全商品で同じ形で保存し、在庫表・在庫一覧(GAS)・閲覧ページの商品名の欄に「商品名 40パックセット」と出すための作り方。
親（あるべき姿＋KGI）: [../../specs/bundle-sale/README.md](../../specs/bundle-sale/README.md)／[ideal-state.md](../../specs/bundle-sale/ideal-state.md)／[kgi.md](../../specs/bundle-sale/kgi.md)
現状把握: [recon.md](./recon.md)（docs/handoff/bundle-sale/recon.md）（origin/main d6b956826 の file:line と本番の試し）
決定の記録: [ADR-1027 案](../../adr/ADR-1027-bundle-sale-reading.md)（ADR-1021 の便2「1枚単価にそろえる」を置き換える）

状態: 設計案作成済み・設計審査済み（Architect/Fable。1回目 REVISE → 指摘を反映 → 2回目 APPROVE。/tmp/CC報告ファイル/bundle-sale/review/fable-review.md・fable-review-2.md。2回目の「低」6件も反映）・KGI K1〜K6 は PO 合意（2026-10-17、PO の答え「y」）・便1 の実装カード [card-bin1.md](./card-bin1.md)・便1 #4479 本番反映済・便2 本番投入済（2026-10-17、[bin2-record.md](./bin2-record.md)）・便3 再解析 93 job 済（2026-10-17、[bin3-record.md](./bin3-record.md)、K1 PO 目視 ○（2026-10-18、PO チャット「y」）・K2 の値段は本文と未照合）・現行キーは現状維持（PO 2026-10-18 y、ADR-1027 追記）・バルク系だけの追加の形 P1・P2（§12）は設計審査済み（Opus reviewer 3回目 APPROVE・Fable 成功見込み「高」）・PO 承認済み（2026-10-21、PO の答え「1」）・便1 実装済み（この PR）・便2 未着手。

---

## 1. あるべき姿（PO 自筆）

[ideal-state.md](../../specs/bundle-sale/ideal-state.md) のとおり。要点: 商品名＋「40パックセット」（マスタ登録なし・仕組みで作る）／単位は中身の単位／状態は中身の状態／値段はまとめ1つの値段（割らない）／数量はまとめの数。全てのまとめ売りに効くこと。

## 2. KGI

[kgi.md](../../specs/bundle-sale/kgi.md) の K1〜K6（PO 合意 2026-10-17）。30th の 2 行は付随の確認（合否に入れない）。

## 3. KPI

達成 KGI 数 ◯/6。

## 4. recon（要点。詳細は recon.md）

- 保存先 public.analysis_results に「まとめの数」の列は無い（migrations/20260921_110000_pipeline_tables_public.sql:214-243、後の追加は price_basis・ship_ja・ship_en）。
- 今のバルク換算は区分「バルク系」だけで動き、set のとき値段÷N・数量×N・単位 Piece・備考「N枚セット単位（1セットX円）」（backend/app/services/v102_bulk_price_svc.py:161-189、入口 backend/app/services/line_analysis_v102_svc.py:956-973）。PO の指定と逆。
- 単位マスタ public.line_units は 10 行（本番 ai_ro.public__line_units。/tmp/CC報告ファイル/bundle-sale/prod-units/q3.txt）。列は id, code, canonical, kubun, is_active, created_at, updated_at, tenant_id, line_id で、日本語の呼び名の列は無い（同 q2.txt）。別名 public.line_unit_aliases は 46 行で全て lang=ja（同 q4.txt）。
- 配信の商品名の欄は `COALESCE(p.name, '') AS japanese_title`（backend/app/services/tcg_distribution_svc.py:304）。アプリ在庫表（backend/app/routers/inventory_offers.py:161）・閲覧ページ（backend/app/tasks/viewer_inventory_cache.py:38-45 → frontend/src/pages/viewer/viewerColumns.tsx:43）・GAS（_write_to_target_sync L665-672）は、全てこの 1 列を読む。
- 同じ行をまとめる鍵 gkey に「まとめの数」は無い（tcg_distribution_svc.py:326-328）。
- 単価の確かめの相場は (product_id, unit_canonical) で区切る（backend/app/services/v102_unit_price_check_svc.py:54-68）。
- 再解析 reanalyze_v102_job は Gemini を呼ばない（backend/app/tasks/tcg_extraction.py:734-735）。同じ入力から同じ結果が出る。
- 本番の試し（v102・現行 4,804 行／1,064 job。本文〔source_messages.raw_text〕の違う投稿は 1,007。この文書の「投稿」は job を指す）: 規則 R の当たり 152 行／95 投稿・本文 90 種。目視で正しい 84・誤り 3（#9・#81 括弧の中、#42 B2 だけ）・決まらない 3（#21・#44・#69）。当たった単位語は「パック・個・枚」だけで、全て単位の別名マスタにある（集計: /tmp/CC報告ファイル/bundle-sale/sim/hits-distinct.tsv の matched 列）。
- 例の行（job b8f6e15a item104 = 8d9eea15）は今 product 440525・Pack・24,000・15・状態 Searched pack（prod-units/q6.txt）。数・値段・単位はもう PO の指定どおりで、足りないのは商品名の「40パックセット」だけ。
- 30th の 2 行（b4ebf4e9・b6299b96）は今 440301・Set（prod-units/q6.txt）。
- 配信に出るのは `cr.needs_review IS FALSE` の行だけ（backend/app/services/tcg_distribution_svc.py:346-354）。例の行 item104 は今 needs_review=True で、理由は unit_price_mismatch の 1 つだけ（/tmp/CC報告ファイル/bundle-sale/sim/all-rows.tsv の 8d9eea15 行）。まとめの値段 24,000 を 1 パックの相場と比べて「単位と値段が合わない」になっているため、今は配信に出ていない。
- 規則 R の当たり 152 行の要確認の理由（重複あり）: condition_unknown 128・product_not_in_master 81・gemini_gap_suspect 78・product_multiple 44・bulk_price_basis_unknown 6・unit_price_mismatch 4・category_unknown 2・ほか 2。理由なしは 13 行（同 sim/hits.tsv を Opus が数えた）。

## 5. design（技術の作り方）

### 5-1. 保存（SSOT）

- analysis_results に `bundle_size integer NULL` を足す（migration。構造だけ・冪等。例は migrations/20261011_150000_add_analysis_results_price_basis.sql）。NULL＝まとめ売りでない。値は 2 以上。
- 「40パックセット」の文字は保存しない。表示のたびに bundle_size と単位から作る（同じ事実を 2 か所に持たない）。
- 単位の呼び名を単位マスタ public.line_units に足す: `name_ja text NULL`・`name_en text NULL`（migration は構造だけ）。値は記録した SQL で入れる（ADR-1007。docs/handoff/bundle-sale/data/units_display_{dry_run,commit,verify,rollback}.sql）。

| id | canonical | name_ja | name_en |
|---|---|---|---|
| 9 | Case | カートン | Case |
| 10 | Box | BOX | Box |
| 11 | Pack | パック | Pack |
| 12 | Piece | 枚 | Piece |
| 13 | Set | セット | Set |
| 16 | 個 | 個 | Item |
| 14・15・17・18 | 本・点・Booklet・MasterCarton | NULL（今は当たりなし。NULL のときは canonical を使う） | NULL |

### 5-2. 読み取り（新しい純関数 backend/app/services/v102_bundle_svc.py）

`detect_bundle(block: str, alias_to_canonical: Mapping[str, str], price, quantity) -> Bundle | None`

1. block を NFKC・小文字化し、数字に挟まれたカンマを除く。
2. 単位の語は単位の別名マスタ（line_unit_aliases の alias_text と canonical。今も解析が読み込んでいる表 backend/app/services/tcg_analyzer_svc.py:125-129）から作る。コードに単位の語を書かない。ただし canonical が Set（line_units id 13。別名「セット」「set」）の語は単位の語に使わない（「16セット」は 16 単位のまとめではないため）。Set の別名は 7 の「数量の直後に『セット』」の判定にだけ使う。
3. まとめの語はコードの定数 1 か所: セット・set・まとめ売り・まとめ・束・組・バルク・bulk・被りなし・被り無し・かぶりなし・ランダム。
4. 形は「数 N（1〜5 桁）＋単位の語＋まとめの語」だけ（B1）。「バルクN枚」型（B2）は使わない（B2 だけの当たりは誤りの #42 の 1 種で、ほかは全て B1 にも当たる）。
5. 括弧（）() の中の当たりは使わない（#9・#81。閉じていない括弧は行末〔原文ブロックの改行。_source_block line_analysis_v102_svc.py:945 は行を改行でつなぐ〕まで中とみなす。bundle_replay.py は TSV の本文の区切り " / " を改行に戻して当てる）。直後が「入」の当たりは使わない。N=1 は使わない。
6. 違う (N, 単位) が 2 つ以上 → 決まらない（印 bundle_unverified）。
7. 決まらない印 `bundle_unverified` を付ける条件（値は Gemini の読みのまま・bundle_size は NULL）:
   - 値段が無い（#51・#69）
   - 数量があり、数量が N で割り切れ（N 自身を含む）、本文で数量の直後に「セット」が無い（#21 数量 27＝N、#44「販売数量3,000」、#50「在庫数 400」）。#90「200セット」はセットが付くので決まる。
   - 単位の語が別名マスタで単位に引けない（防御的。B1 の単位の語は別名マスタからしか作らないので、今の作りでは起きない）
8. 決まったとき: bundle_size=N、単位＝中身の単位（unit_canonical・unit_id・unit_resolved をそろえる）、値段・数量は Gemini の読みのまま（割らない・掛けない）。

この規則を本番の 4,804 行に、本番の単位の別名マスタ（prod-units/q3.txt・q4.txt、46 語。Set を除く単位の語 22 語）で当てた結果（台本 /tmp/CC報告ファイル/bundle-sale/replay2/replay.py、生出力 replay2/out2/summary.txt・rows.tsv）:
- 決まる 82 種 144 行（単位 Piece 133・個 8・Pack 3）・決まらない 5 種 5 行（#21・#44・#50 割り切れ、#51・#69 値段なし）・当たらない 4,655 行（旧 R の当たりから外れたのは誤りの #9・#42・#81 の 3 行だけ。新しく当たった行は 0）。当たりのある job は 92（b8f6e15a を含む）。
- 割り切れの判定は Gemini の読みの数量で行う。今の保存が ADR-1021 便2 の換算済み（price_basis `V102:bulk:set:N`、数量×N）の 13 行は ÷N して換算前に戻して判定した（例 #90 は 20,000→200、本文「200セット」で決まる）。
- 参考: 「N＋別名に無い語＋まとめの語」の当たり 135 行の語は「種」106・「種カートン」9・「人の最強」6・「thカード」3・「セット」（16セット 被り無し）2 ほか（replay2/gen_words.txt）。全て商品の中身や品名の説明（例「9種セット」は商品の検索語として登録済みの品名）で、単位のまとめ売りは 0。
- evidence.md の目視「正しい 84」との差: #50（在庫数 400 がセット数か枚数か本文で決まらない）と #51（値段なし）を決まらない側にした。

### 5-3. 解析の流れへのつなぎ（backend/app/services/line_analysis_v102_svc.py `_write_results` L995-1044）

- `_analysis_values` の直後に `_apply_bundle` を全ての行（区分を問わない）に当てる。原文ブロックは今の `_source_block`（L938-945）を全ての行で作る。
- `_apply_bulk_price` から set の換算（÷N・×N・備考・`V102:bulk:set:N`）を消す。まとめ売りと決まった行はバルク系でも `_apply_bulk_price` を通さない。まとめ売りでないバルク系の行は今のまま（piece は単位 Piece、決まらないは `bulk_price_basis_unknown`）。ただし convert が set を返したときは理由 bulk_price_basis_unknown で review にする（R' で決まらなかったセットの印を割って保存しない。本番の現行行で当たるのは 0 行、§11）。
- 単価の確かめ: `_MARKET_SQL` に `AND ar.bundle_size IS NULL` を足し、`_unit_price_mismatches` の候補から bundle_size のある行を外す（まとめの値段と 1 個の値段を混ぜない）。
- 価格の引き継ぎ: `_inherit_price` は bundle_size のある行を対象外にし、`_INHERIT_PRICE_SQL` の引き継ぎ元に `AND ar.bundle_size IS NULL` を足す。
- 買取単位（便BB）: `is_buyback_candidate`（backend/app/services/v102_buyback_unit_svc.py:134-143）に `values.get("bundle_size") is None` を足す。
- 人の直し（apply_value_overrides）は今のまま後から当たる（人が直した値が勝つ）。bundle_size の人による直しは便4。
- `_UPSERT_SQL`（L709-732）の INSERT 列・VALUES・ON CONFLICT に bundle_size を足す。`_analysis_values` は bundle_size=None を返す。

### 5-4. 表示（1 か所で作る）

- 配信 SQL（tcg_distribution_svc.py の dist_base）に `LEFT JOIN public.line_units lu ON lu.id = ar.unit_id` を足し（VIEW public.units は `AS TABLE public.line_units` で後から足す列が出ないため使わない。migrations/20260922_080000:32）、商品名の欄を作る:
  - japanese_title = `p.name || ' ' || ar.bundle_size || COALESCE(lu.name_ja, lu.canonical, ar.unit_canonical) || 'セット'`（bundle_size が NULL なら今と同じ `COALESCE(p.name,'')`）
  - english_title = `COALESCE(p.name_en, '') || ' ' || ar.bundle_size || ' ' || COALESCE(lu.name_en, lu.canonical, ar.unit_canonical) || ' Set'`（bundle_size が NULL なら今と同じ `COALESCE(p.name_en,'')`、tcg_distribution_svc.py:305）
  - 作り方は Python の関数 1 つ（`bundle_title_sql()`）に置き、SQL はそれを使う。
- gkey に `COALESCE(ar.bundle_size::text, '')` を足す（40 パックのまとめと 1 パックの行をまとめない）。
- アプリ在庫表・閲覧ページ・GAS は配信の商品名の欄を読むだけなので、画面のコードは変えない（recon.md の表示経路）。検索（inventory_offers.py:207）と並べ替え（L372）も同じ欄なので「40パックセット」で探せる。
- 「セット」「Set」はこの関数の中だけに書く。画面の文言ではなく配信データの値なので i18n（ADR-027）の対象外。理由ラベル bundle_unverified の文言は i18n（frontend/src/locales/ja.json・en.json の bulk_price_basis_unknown の隣）と backend/app/data/review_reason_labels_ja.json に足す。

### 5-5. 理由コード

- `bundle_unverified` を public.review_reason_codes に記録した SQL で足す（source=system, fix_stage=analysis。例 docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261016_bulk_price_basis_unknown.sql）。NON_ACKABLE_REASON_CODES（backend/app/services/review_reason_codes_svc.py:22。今は condition_unknown・bulk_price_basis_unknown）には入れない。unit_price_mismatch と同じ扱いで、人の「このままで良い」で外せる（ack は item_corrections に残り、再解析で review_reasons から外れて配信に戻る。line_analysis_v102_svc.py:814-823）。値は Gemini の読みのまま。
- 配信に出ない仕組みは今のまま: 配信が見る cr.needs_review は保存列ではなく、問い合わせのたびに ar から作る式で、review_reasons に理由が 1 つでもあれば真（backend/app/services/tcg_condition_review_svc.py:228-255、:242）。再解析は ar を UPSERT で上書きし（line_analysis_v102_svc.py:727）、cr は自動で追う。
- 理由コードを足すと既存の整合テストが 4 点をそろえることを求める（CI で毎回）: backend の定数、記録した SQL 1 行、frontend/src/locales/ja.json・en.json の reviewReason、backend/app/data/review_reason_labels_ja.json（同期ツールで作り直す）。テスト backend/tests/test_review_reason_codes_consistency.py・test_review_reason_labels_ja_sync.py。

### 5-6. 便の分け方（1 便 1 目的）

| 便 | 中身 | 危険なパス | 実装 |
|---|---|---|---|
| 便1 | migration 2 本（analysis_results.bundle_size、line_units.name_ja/name_en）＋scripts/run_all_migrations.sh 登録＋読み取り（5-2・5-3）＋配信（5-4）＋理由ラベル＋テスト＋scripts/dev/bundle_replay.py＋ADR-1021 と docs/handoff/g28-bulk-price/design.md の便2 に「ADR-1027 で置き換え」の注記（ADR 索引の作り直し） | migrations/ を含む → GO 記録 | Sonnet |
| 便2 | 記録した SQL（単位の呼び名・理由コード）を本番で DRY-RUN → COMMIT → verify | 本番データ（PO 委任の範囲） | Opus の指示で Sonnet |
| 便3 | 当たりのある 92 job（b8f6e15a を含む）の再解析、K1〜K6 の照合と付随の確認。始める前に、換算済み 13 行に人の直し（apply_value_overrides の元）があるかを読み取りの道で数え、あれば止めて一覧を出す | 本番の再解析 | Opus の指示で Sonnet |
| 便4（後日） | 比較・レビュー画面に bundle_size を出す・人が直せるようにする・単位マスタの管理画面に呼び名の欄 | フロント | 別設計 |

便1 は名前の欄が NULL でも canonical で出るので、便2 より先に本番に出ても壊れない（Pack なら「40Packセット」になる。便2 の後に「40パックセット」）。便3 は便2 の後。SystemFields・比較表の quantity/price の見え方（recon 未確認 #1）は便1〜3 では触らない（便4）。

## 6. 弊害・トレードオフ

- 本文が「100枚 / 50セット @24,000」型（まとめ語が無い・8 行）、「150枚入」「カートン(20BOX入り)」（28 行）、×N（565 行）は今のまま。全てのまとめ売りの形を拾うわけではない。拾えない形は今の保存のまま要確認で人が見る。
- バルク系の 13 行は 1 枚単価（380 円）から まとめの値段（38,000 円）に変わる。GAS・閲覧の利用者から見える値段の桁が変わる（PO 指定どおり）。
- まとめ売りの行は単価の確かめ（相場）から外れる。まとめの値段の誤りは機械で見つけない。
- 決まらない 5 種は配信から消える（人が「このままで良い」を押すか値を直すまで）。今は #44 などが配信に出ている。
- 単位の呼び名は管理画面で直せない（便4 まで SQL）。
- まとめ売りの行の多く（152 行中 139 行）は、状態や商品が決まらないなど本テーマと別の理由で要確認になっており、本テーマを入れても配信には出ない。出るのは、ほかに理由が無い行（例の行 item104 は、まとめの値段を相場と比べなくなることで理由が無くなる）と、人が要確認を片づけた行。

## 7. 外部・過去事例

該当なし。理由: 仕入元の LINE 投稿の書き方に依存する読み取りで、外部の数値事例は本テーマの成功の根拠にならない。根拠は本番の全 4,804 行の試しと全 90 種の目視（recon.md「本番の試し」）。過去の社内事例として ADR-1021 便2（区分だけで決める換算）は、区分がバルク系でない 133 行のまとめ売りに効かなかった（試しの 152 行中バルク系 19 行）。

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| A1 新関数を本番の 4,804 行（/tmp の all-rows.tsv。列 item_id・job_id・md5_8・product_id・kubun_type・unit_canonical・price_normalized・quantity_normalized・price_basis・needs_review・review_reasons・condition_canonical・note_ja・body のタブ区切り、取り方 /tmp/CC報告ファイル/bundle-sale/sim/fetch-all.sh。社外秘のためリポジトリに入れない）と本番の単位マスタ・別名マスタに当て、決まる 82 種 144 行・決まらない 5 種 5 行・当たらない 4,655 行（設計時の台本 replay2/replay.py と行ごとに一致） | 便1 の PR 前に Sonnet が scripts/dev/bundle_replay.py（リポジトリに置く・データは引数）で実行し、生出力を keep に保存 |
| A2 単体テスト: 5-2 の各条件（B1、括弧、入、N=1、複数、値段なし、割り切れ、セット付き、別名に無い語）と、バルク系で ÷N しないこと、相場・引き継ぎ・買取から外れること、gkey と商品名の作り方 | CI（backend の pytest） |
| A3 backend/tests/test_v102_bulk_price.py のうち set の換算（÷N・×N）を固定していた L22・L28・L44（全角）・L102・L152 を新しい決まり（割らない・掛けない・bundle_size=N）に書き換える。L163 `test_write_results_non_bulk_is_untouched`（箱系・単位 Set・本文「100枚セット / 5セット@26,000円」・期待 (26000, 5, "Set", None)）は、新しい決まりでは全区分に当たるので期待を (26000, 5, "Piece", bundle_size=100) に変える。piece と review のテストは変えずに緑 | CI と PR の差分 |
| A4 i18n の ja/en が同じキー | CI（既存の i18n 検査） |
| A5 K1〜K6 と付随の確認 | 便3 の照合 SQL（ADR-1024 の読み取りの道）と 3 画面の目視 |
| A6 K6 の差は 0。差が出たら止めて一覧を出す（マスタの更新で変わった行と区別するため、再解析前の値を先に保存する） | 便3 の前後比較 |

## 9. 維持の仕組み

守り手: backend/tests/test_review_reason_codes_consistency.py（既存・CI で毎回。理由コード bundle_unverified の 4 点のずれを赤にする）。便1 で backend/tests/test_v102_bundle.py と scripts/dev/bundle_replay.py が加わる（下の守り手1〜5）。

- 守り手1（CI・毎回）: backend の pytest に A2・A3 のテスト。規則を変えると赤になる。
- 守り手2（マスタが正本）: 単位の語は別名マスタから作るので、新しい単位・別名を登録すれば読み取りにも自動で効く。コードに単位の語の表を持たない（持つとテストで見つけるため、v102_bundle_svc に単位語の直書きが無いことを確かめるテストを置く）。
- 守り手3（人の目・毎日）: 決まらない行は理由 bundle_unverified で要確認の欄に出る（今の要確認の仕組み）。
- 守り手4（再現の台本）: scripts/dev/bundle_replay.py。規則を変える便は、PR 前にこれで本番の全行に当て直し、結果の数を PR 本文に書く（ADR-1027 の決まり）。
- 守り手5（理由コードの整合・毎回）: 既存の test_review_reason_codes_consistency.py と test_review_reason_labels_ja_sync.py が、bundle_unverified の定数・SQL・ja/en・ラベル JSON のずれを赤にする。
- 守り手6（手順書・2026-10-21 追記）: docs/runbooks/bundle-sale-new-wording.md。新しい書き方を見つけたら、数える→設計の追記→テスト→PR 本文に数、の順で直す。索引は docs/adr/FEATURE-INDEX.md の「まとめ売り」の行。
- 未確立（正直な明記）: 「新しい書き方のまとめ売りが増えた」ことを自動で知らせる仕組みは無い。bundle_replay.py は「N＋別名に無い語＋まとめの語」の当たりの語を数えて出す（設計時は 135 行・全て品名の説明）ので、規則を変える便と週次の点検ではこの欄の新しい語を人が見る。拾えない形（B3・入り・×N）は人が要確認で見る。bundle_replay.py は本番データが要るため CI では走らない。

## 10. 接触面分析（6 面）

逆参照: `git grep -n "V102:bulk\|_apply_bulk_price\|convert_bulk_price\|bulk_price_basis_unknown\|japanese_title\|gkey" origin/main`（recon.md に結果）。

1. 人: PO・利用者（GAS・閲覧ページ）に、バルクの値段の桁と商品名の欄の変化が見える。GAS の列は増えない。
2. エージェント: ADR-1021 便2 を読んで ÷N を前提にする担当が出る → ADR-1021 に「便2 は ADR-1027 で置き換え」の注記を足す。docs/handoff/g28-bulk-price/design.md の便2 にも同じ注記。
3. 機械: CI（pytest・i18n・ADR 索引）。scripts/run_all_migrations.sh への登録。process-artifacts gate（migrations/ を含むため GO 記録）。
4. データ: analysis_results と line_units に列が足される（NULL 許可・既存行は NULL）。review_reason_codes に 1 行。テナント: public のみ。tenant_004 には触れない。
5. 本番: deploy で migration が走る（ADR-SA の手順のまま）。再解析は当たりのある 92 job（b8f6e15a を含む）。監視は変えない。
6. 外部: 仕入元・Gemini は変わらない（再解析は Gemini を呼ばない）。GAS のシートは同じ 14 列。

## 11. 未解決事項

- なし（設計の範囲）。参考: 例の行の状態は今「Searched pack」（prod-units/q6.txt）。PO の例は「Unsearched pack など」。状態の決め方は本テーマの対象外で、今の決め方のまま。
- 30th の 2 行は付随の確認（kgi.md）。便3 で b8f6e15a を再解析して 466088 になるかを見る。ならないときは別の便で原因を調べる。
- 影響範囲の決定（recon 未確認 #7・#8・#12）:
  - #7: 配信の cr.needs_review は ar から毎回作る式なので、bundle_unverified は配信に効く（5-5）。
  - #8: price_normalized の読み手 66 行（backend/app）のうち「1 個の値段」前提で影響が出るのは相場（v102_unit_price_check_svc.py:54-65、line_analysis_v102_svc.py:913-918）・引き継ぎ（:1161-1225）・買取（v102_buyback_unit_svc.py:140・215）の 3 つで、5-3 で bundle_size のある行を外す。配信の SUM/MAX（tcg_distribution_svc.py:377）は gkey に bundle_size を入れるので混ざらない。ほかは NULL かどうかと表示だけ（/tmp/CC報告ファイル/bundle-sale/replay2/facts.md）。
  - #12: 換算済み 13 行は便3 の再解析で置き換える（UPSERT は ON CONFLICT (extraction_item_id)、line_analysis_v102_svc.py:709-732。Gemini の読みから毎回作り直す）。bundle_size は ON CONFLICT の SET にも足す。人の直しがある行は便3 の始めに数えて止める。
- 現在の換算済みでない行で「バルク系・convert が set・規則 R' で決まらない」（新しく review になる行）は 0（換算済み 13 行は全て決まる。replay2 の照合）。

## 12. 追記 2026-10-21: バルク系だけ見る形 P1・P2

PO 承認: 2026-10-21、PO の答え「1」（既存の延長として進め、8 行を在庫表・シート版に「商品名 100枚セット」で出す）。ADR-1027「バルク系だけの追加の形（2026-10-21 追記）」が決定、この節が作り方。仕入元の名前・本文はこの節に載せない（調査の生データはリポジトリの外）。

### 12-1. 目的
区分がバルク系の行で、本文が「100枚のかたまり」と「在庫Nセット」を両方書いているのに「1枚かセットか分からない」（bulk_price_basis_unknown）で止まっている行を、まとめ売り（bundle_size=100）として読む。

### 12-2. 現在地（origin/main 7560d8007）
- 読み取りは backend/app/services/v102_bundle_svc.py の `detect_bundle`（:112-143）1 か所。形は :76 の「数＋単位の語＋まとめの語」だけ。括弧の中は :80-89 で使わない。
- 呼び出しは backend/app/services/line_analysis_v102_svc.py `_write_results` の :1140（`_apply_bundle` :1028 → :1034）。全ての区分に当てる。直後の :1141-1143 は既に `item.get("product_category") == PRODUCT_KUBUN_BULK` で分けている（PRODUCT_KUBUN_BULK は gemini_raw_copy_v102_product_first.py:49）。
- まとめ売りと決まった行は `_apply_bulk_price` を通らない（line_analysis_v102_svc.py:1049）ので、理由 bulk_price_basis_unknown は付かない（backend/tests/test_v102_bulk_price.py:162-165 が固定）。
- scripts/dev/bundle_replay.py:94 は区分を見ずに detect_bundle を呼ぶ。入力の TSV は既に列 kubun_type を持つ（:6-7）が読んでいない。
- 基準値（2026-10-21、ADR-1024 の読み取りの道）: 現行のバルク系 55 行のうち bulk_price_basis_unknown 21 行・bundle_unverified 0 行。
- 2026-10-22 便2 後の基準値（便3 の SQL で測定。2026-10-22 09:58 JST）: 現行のバルク系（全エンジン）288 行（うち v102-f_ct 57 行）・bulk_price_basis_unknown 14 行・bundle_unverified 0 行・全区分の bundle_unverified 5 行（product_id 未解決の行はバルク系か判定できないため参考値）。21 行の元の SQL は残っておらず、21→14 の差の内訳は確かめていない。

### 12-3. 足す形
| 形 | 書き方 | 当てる本文 | 候補にする条件 |
|---|---|---|---|
| P1 | まとめの語 ＋ 空白 ＋ `(` N 単位の語 `)` | 括弧を除く前の本文 | 括弧の直前がまとめの語。括弧の内側の前後に空白を許さない |
| P2 | まとめの語 ＋ 空白 ＋ N 単位の語 | 括弧を除いた後の本文 | 数量が整数に読め、`_has_set_after_quantity(本文, 数量, Set の語)` が真 |

- 共通: 当たりの終わりの次の 1 字が「入」なら使わない・N<2 は使わない・単位は別名マスタの canonical（コードに単位名を書かない）・まとめの語は既存 BUNDLE_WORDS（v102_bundle_svc.py:23-25）。
- 足した候補は既存の候補に混ぜてから、既存の判定（:131-143）を 1 回通す。違う大きさが 2 つなら決まらない。
- 足さない形: 「N種＋まとめの語」（「種」を単位にしない・区分で絞らないと非バルクで動く）、「N単位M種」（P2 に含まれる）。

### 12-4. 便1 で触るファイル（ほかは触らない）
- backend/app/services/v102_bundle_svc.py: `detect_bundle(..., bulk_shapes: bool = False)`。:128 の後に `if bulk_shapes: found += _find_bulk_candidates(full, word_to_canonical, set_words, quantity)`。`_bulk_patterns`（lru_cache・`_patterns` と同じ語の作り方）と `_find_bulk_candidates` を足す。説明文 :4 に「バルク系だけ P1・P2 も見る」を足す。
- backend/app/services/line_analysis_v102_svc.py: `_apply_bundle` に `bulk_shapes` を足して渡す。:1140 を `pairs` と zip し、`bulk_shapes=item.get("product_category") == PRODUCT_KUBUN_BULK`。
- scripts/dev/bundle_replay.py: `_BULK_KUBUN = "バルク系"`（product_first を import しない。一致はテストで固定）。:94 に `bulk_shapes=(r.get("kubun_type") or "") == _BULK_KUBUN`。集計をバルク系／それ以外に分け、False と True で結果が違う行の数を出す。説明文 :1-13 に、バルク系は bulk_shapes=True で読むことを 1 行足す。
- backend/tests/test_v102_bundle.py: P1・P2（セットあり→決まる／セット無し→None）・bulk_shapes=False→None・既存の形と混ざる→決まらない・誤り #9・#81・#42 の形→None・`_BULK_KUBUN == PRODUCT_KUBUN_BULK`。単位名の直書き検査（:90-95）は今のまま通る。
- backend/tests/test_v102_bulk_price.py: `_write_results` 段で、バルク系の P1 の作り文→bundle_size=100・Piece・値段と数量は不変・review_reasons None。同じ本文で箱系→bundle_size None。
- 触らない: v102_bulk_price_svc.py・配信 SQL・マスタ・migrations・frontend。

### 12-5. 便の分け方（1 便 1 変更）
- 便0（この節・文書のみ）: ADR-1027 追記・この節・FEATURE-INDEX・手順書 docs/runbooks/bundle-sale-new-wording.md。
- 便1（コード）: 12-4。PR の前に bundle_replay.py を全行に当て直し、バルク系／それ以外の数と増えた行数を PR 本文に書く。固定一覧（下の 12-6）と 1 行でも違う、またはバルク系以外で 1 行でも変わるなら止める。
- 便2（本番データ）: 現行 8 行を含む 4 投稿だけを再解析する（過去 7 行の投稿は配信に出ないので通さない）。前の値を全列保存・必ず戻す試し・書き戻しの SQL を先に用意。実行の前に同意票で PO に確認（ADR-1033）。再解析の最後に配信の予約が走るので、8 行が次の配信で出ることを同意票に書く。
- 便3（見張り）: 本番の celery beat（毎週月曜 09:05）で、現行のバルク系の bulk_price_basis_unknown・bundle_unverified の件数と、参考に全区分の bundle_unverified の件数を管理者用 Discord に出す（backend/app/tasks/bundle_bulk_monitor.py）。PO 2026-10-22「1」で agent-console 週次から変更（Mac が止まっても届く・既存 ADR-1020 便4c と同じ型）。engine_version では絞らない（理由コードは v102 系だけが付けるため）。基準値は 12-2。
- 便4（表示）: 英語名（products.name_en）が NULL・空・空白だけのときは、まとめ売りでも英語タイトルを空にする（まとめ売りでない行と同じ）。PO『1』（2026-10-22）。変更は tcg_distribution_svc.py の bundle_title_sql の英語 CASE だけ。受け入れ: |基準|検証方法| ①英語名が空の行は英語タイトルが空になる → 単体テスト (b)(c)（backend/tests/test_bundle_title_empty_name_en_pg.py） ②英語名がある行は今と同じ → 単体テスト (a)(d)、本番の読み取りで、新旧の式の差がその条件の行の外では0件 ③配信対象で変わるのは3行 → 本番の読み取りの件数

### 12-6. 受入基準
固定一覧: 判定の写し（origin/main 7560d8007 と同じ判定に 12-3 を足したもの）を全 v102 35,846 行に当てて変わる 15 行（現行 8・過去 7。全て「当たりなし→100・Piece」）。一覧はリポジトリの外（社外秘）。

| 基準 | 検証方法 |
|---|---|
| K1 固定一覧の現行 8 行が bundle_size=100・単位 Piece になる。一覧外のバルク系現行行の bundle_size は変わらない | 便2 の前後を ADR-1024 の読み取りの道で照合 |
| K2 対象行の値段・数量の変化 0 | 同上 |
| K3 既存の bundle_size 157 行の変化 0 | 同上＋bundle_replay.py 全行 |
| K4 バルク系以外の行の変化 0 | bundle_replay.py 全行（区分付き）＋便2 前後照合 |
| K5 誤り #9・#81・#42 の形は None のまま | 単体テスト（同じ形の作り文）＋bundle_replay.py |
| K6 新しく要確認になる行 0 | 便2 前後照合 |
| K7 変わってよい列は bundle_size・unit_canonical・unit_id・unit_resolved・needs_review・review_reasons の 6 列だけ | 便2 前後照合（ほかの列が 1 つでも違えば止める） |
| K8 在庫表・シート版の日本語の表示が「商品名 100枚セット」 | K10 と同じ目視 |
| K9 現行 8 行は needs_review=False・review_reasons NULL になり要確認の欄から出る | 便2 前後照合 |
| K10 8 行のうち配信の条件（tcg_distribution_svc.py:198-226 の max_age_hours 等。便2 の前に値を記録）に合う行だけが出る | 配信 SQL の読み取り＋PO 目視 |

### 12-7. 弊害・トレードオフ
- 正解の記録と照らせる行は 0。根拠は ①本文が「100枚のかたまり」と「在庫Nセット」を両方書く ②同じ仕入元・同じ商品・同じ値段で語の順番だけ違う行が既に 100 で読めている ③既存 157 行・バルク系以外は動かない ④過去の誤り 3 件は当たらない。
- 在庫が裸の数（「在庫 20」）の行は読まない。今のまま要確認に残る（悪化はしない）。
- 「数量の直後にセット」が本文の別の数と偶然並ぶ危険は、既存の割り切れ判定と同じ関数・同じ危険。
- まとめの語は v102_bundle_svc.py:23-25 のほか v102_bulk_price_svc.py:27・55・58・62 にもある。今回は増やさない。1 か所にまとめるのは別の ADR。
- 再解析は他の規則も当て直すので、コードを戻しても DB は戻らない（便2 で書き戻しの SQL を先に用意）。

### 12-8. 外部・過去事例
外部事例は使わない。理由: LINE の仕入れ文面の独自の書き方の読み分けで、同じ条件の数値つき公開事例が無い。社内の過去事例は ADR-1027 便1〜3（82 種 144 行を読み、誤り 3 種を括弧と形の除外で外した）。今回はその除外を「バルク系＋本文の裏付けあり」の狭い形でだけ戻す。Gemini に選ばせる案は 2026-10-21 の試験で根拠の無い行も言い切ったため、PO が採らないと判断した。

### 12-9. 維持の仕組み（この追記の分）
- 守り手: backend/tests/test_v102_bundle.py と backend/tests/test_v102_bulk_price.py（便1 で追加。CI 必須の pytest で毎回）。
- 守り手: scripts/dev/bundle_replay.py（便1 で区分付きに。規則を変える便は PR の前に全行へ当て直す。CI では走らない）。
- 守り手: docs/runbooks/bundle-sale-new-wording.md（便0）と docs/adr/FEATURE-INDEX.md の「まとめ売り」の行（便0）。
- 未確立（正直な明記）: 件数の自動の見張り（便3 まで無い）・英語名が空の表示のテスト（便4 で backend/tests/test_bundle_title_empty_name_en_pg.py に追加。CI の PostgreSQL 専用）・まとめの語の置き場の 1 本化（別の ADR）。

### 12-10. 未確認（便2 の前に確かめる）
- 本番で動いている版が origin/main と同じか。
- 本番に public.unit_aliases の互換ビューがあるか（結果の一致は傍証）。
- `_write_results` のほかの段が 8 行に新しい理由を足さないか（K9 は便2 の前後で判定。足されたら止めて理由を見る）。
