# 要確認一覧の読み込みを速くする（作業2）設計 — 2026-10-13 Opus

状態: 設計案（Opus 作成）→ Fable 審査待ち。PO の依頼「データテーブルの読み込みが遅い → 理由と改善」（2026-10-13）。

## 1. KGI（PO が○×で判定できる形）
- KGI-1: 要確認タブの最初の20件の取得（GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW&limit=20 の中の SQL 合計）が **本番で 3.0 秒以下**（変更前 7.7〜7.9 秒・3周）
- KGI-2: 一覧に出る中身が **1文字も変わらない**（同じ条件で変更前後の戻り値の sha256 が一致）

## 2. 現在地（recon の要約。全文は docs/handoff/review-speed/recon.md）
- 遅い場所: backend/app/services/tcg_condition_review_svc.py:129 `CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data` を PostgreSQL が展開（subquery pull-up）し、:130 の `cr_product.id::text = cr_data.ar->>'product_id'` などの比較のたびに to_jsonb(ar) を作り直している。EXPLAIN（measure-out-explain-raw.txt:372-378）で当該ノード actual time 約3,750ms。変更後も除去行数は同程度（candidateA:491 Rows Removed 240,081）で、減るのは1比較あたりの費用（to_jsonb を行ごとに1回だけ作る）。同ノードは約140ms（candidateA:486-494）。
- 本番の列型: products.id integer・analysis_results.product_id integer（speed-measure-candidateA.txt:25-28、pg_attribute）。
- この部品 review_joins を使う経路（全走査 speed-recon-2.md §4、Fable 審査で `git grep` 再確認）: 要確認一覧 API（tcg_analysis_review_svc.py:47 _BASE_FROM → :180/:186/:197/:244）・CSV 出力（tcg_review_csv_svc.py:75）・シート出力（tcg_review_sheet_svc.py:108）・配信（tcg_distribution_svc.py:292/364/407）・取り込み進捗（tcg_import_progress.py:129）・状態保存と再解析（context_sql 経由 tcg_condition_review_svc.py:205-225、:283-325）。
- 関連 ADR（`git grep -il "analysis_results\|要確認" origin/main -- docs/adr`）: ADR-1002（:70 analysis_results.product_id を INTEGER 化。列型の根拠）・ADR-1001（:93 tcg_condition_review_svc.py をスキーマ参照変更の対象に列挙）・ADR-158（:58 source_cte の is_current。今回は触らない範囲の根拠）。docs/adr/FEATURE-INDEX.md に該当項目なし。本変更は SQL の意味を変えないため、どの ADR とも食い違わない。

## 3. 直し方（1か所・1語）
tcg_condition_review_svc.py:129 を次に変える:
```
変更前: CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data
変更後: CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar OFFSET 0) cr_data
```
直前にコメント1行: 「OFFSET 0 は PostgreSQL の展開（pull-up）を止め、to_jsonb(ar) を行ごとに1回だけ作るため。外すと要確認一覧が約3倍遅くなる（docs/handoff/review-speed/design.md）」
- 根拠（公式）: PostgreSQL REL_16_STABLE src/backend/optimizer/prep/prepjointree.c is_simple_subquery「Can't pull up a subquery involving grouping, aggregation, SRFs, sorting, limiting, or WITH」と `subquery->limitOffset ||` の条件。Context7 は月間上限で使えなかったため、起動指示の代替として公式ソースを直接確認。
- 1行のサブクエリに OFFSET 0 を付けても返る行は変わらない（SQL の意味は同じ。実行の順番だけが変わる）。

触らない範囲: review_joins の他の行、_BASE_FROM、source_cte、件数・提供者の SQL の共有化（「変更は一度に1つ」。この変更の効果を測ってから次を決める）、フロント。

### 代替案と選ばなかった理由
- B: 結合を `cr_product.id = (cr_data.ar->>'product_id')::integer` にする → 再解析の候補（candidate の JSON）で product_id が整数でない文字のとき型変換エラーで落ちる恐れ。意味が変わり得るので不採用。
- C: 件数・提供者・本体を1本の SQL にまとめる → 変更が大きく、CSV・シートにも波及。A の効果測定後に必要なら別便。

## 4. 実測（本番・読み取りのみ・2026-10-13 10:03 UTC・別コンテナ・READ ONLY）生出力 speed-measure-candidateA.txt
| 条件 | 変更前 合計ms（3周） | 変更後 合計ms（3周） | sha256 |
|---|---|---|---|
| NEEDS_REVIEW 20件 | 7915 / 7734 / 7770 | 2388 / 2451 / 2419 | 一致 |
| NEEDS_REVIEW 500件 | 40398 / 40254 / 41373 | 5465 / 5414 / 5397 | 一致 |
| ALL 500件 0〜 | 15965 / 15835 / 15591 | 3437 / 3465 / 3428 | 一致 |
| ALL 500件 500〜 | 5351 / 5351 / 5350 | 4294 / 4186 / 4170 | 一致 |
| NORMAL_COMPLETED 500件 | 10881 / 10837 / 10867 | 6286 / 6244 / 6305 | 一致 |
| 配信 fetch_output_rows | 24873 | 23144 | 一致 |
| 配信 fetch_preview_data | 10743 | 8758 | 一致 |
| 取り込み進捗 2job×2関数 | — | — | 一致（as_of の時刻欄を除く） |

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| KGI-1 本番で NEEDS_REVIEW 20件の SQL 合計 ≤3.0秒 | デプロイ後、同じ測定スクリプト（x.py）を別コンテナ・READ ONLY で3周 |
| KGI-2 戻り値が変わらない | デプロイ前に取った sha256（変更前コード）と、デプロイ後の sha256 を比べる。データ更新があり得るため、デプロイ後は「旧コードの文字列を再現した版」と同時に測って一致を見る（今回と同じ方式） |
| 既存試験が通る | CI の pytest（test_tcg_condition_review.py:323-343 の実 PG 試験・test_tcg_result_order.py・CSV/シート試験） |
| 展開止めが外されない | 新しい単体試験（backend/tests/test_tcg_condition_review.py 末尾・pg fixture なし＝DB 不要で常時走る）: (a) review_joins() に `AS ar OFFSET 0) cr_data` を含み `AS ar) cr_data` を含まない (b) context_sql(analysis_expression="to_jsonb(ar) \|\| CAST(:candidate AS jsonb)") でも同様 (c) tcg_analysis_review_svc._BASE_FROM に `AS ar OFFSET 0) cr_data` がちょうど1回 |

## 6. 弊害とリスク
- PostgreSQL の版上げで最適化の方法が変わる可能性 → 単体試験で文字列を固定し、効果は本設計の測定スクリプトで再測できる。
- ALL 500件 500〜 は短縮が小さい（5.35→4.2秒）。主因は別の場所（並び替え）であり今回の対象外。

## 7. 維持の仕組み
- 守り手: CI の pytest（backend/tests/test_tcg_condition_review.py::test_review_joins_keeps_offset_zero_pullup_barrier。DB 不要で毎回走る）。速さの測り直しは設計担当（Opus）が本書 §5 の方法で行う。
- 単体試験（文字列の固定）＋ コードコメントで理由と本設計へのリンク。
- 測定スクリプト: repo 外の ~/CC報告ファイル-keep/review-page-20261013/x.py（再測用・本番データの中身を出さず件数と sha256 だけ出す）。repo には測り方（別コンテナ・READ ONLY・OLD/NEW 文字列を差し替えて同時に測る）を本書に記すに留める。

## 審査
- 2026-10-13 Fable（設計審査）: APPROVE。指摘（行番号・文言・ADR 参照・試験の置き場所・recon の未確認解消）は本版で反映済み。

## 8. 外部・過去事例の参照と我々への応用
- PostgreSQL 公式ソース（上記 §3）。OFFSET 0 で展開を止めるのは PostgreSQL 開発者の文書に基づく方法で、本件の効果は本番の実測（§4）で確認した。他社事例の数値は使わない（本件の判断は自社本番の実測だけで足りるため）。

## 9. 戻し方
- `OFFSET 0` を外す1行の revert。DB 変更なし。

## 10. 第2便: 画面を開いてから一覧が出るまで2秒以内（2026-10-21 Opus・設計案）

状態: 設計案（Opus 作成・2回目の実測を反映）。審査前。PO 承認済みの事項と未承認を分けて書く。

### 10-1. PO の決定（原文の要旨。PO の言葉は創作しない）
- 2026-10-21 PO「1」: KGI「画面を開いてから一覧が出るまで2秒以内」で設計を進める（作り始める前に再確認する約束）。
- 2026-10-21 PO 提案（採用の意思表示）: ①既定は投稿から24時間以内だけ・投稿日の新しい順。ボタン等で24時間の絞りを外すと古いものも見られる。②応答を圧縮して送る。③1ページの件数は既定25件、プルダウンで50件・100件。
- 2026-10-21 PO「1」: 見え方の4つ（新しい順・25/50/100・圧縮・24時間ボタン）は設計に入れ、同時に遅さの原因を EXPLAIN ANALYZE で確定する（PO が読み取り専用の台本を ! で1回流す）。

### 10-2. KGI・KPI
| 基準 | 検証方法 |
|---|---|
| KGI-3 要確認画面を開いてから一覧の1行目が出るまで 2.0 秒以内（本番・既定表示） | 本番で Playwright の計時（画面遷移〜一覧1行目の描画）を3回。中央値で判定 |
| KPI-3a 一覧 API（既定: 24時間・25件）のサーバー側 SQL 合計 | 本番 nginx の request_time と、別コンテナ READ ONLY の再測 |
| KPI-3b 一覧 API の送信量（gzip 後） | 本番 nginx の body_bytes_sent（変更前 20行 約132KB） |
| KGI-4 24時間の絞りを外したときの中身が、絞りなしの従来と件数・中身・順番以外で一致（順番は新しい順に変わる） | 本番 reader で旧形と新形を同条件で比べる |
| KGI-5 CSV・シート出力の中身が変わらない | 変更前後の sha256 比較（§5 と同じ方式） |

### 10-3. 現在地（2026-10-21 調査・読み取りのみ）
生出力: /tmp/CC報告ファイル/review-slow-20261021/、/tmp/CC報告ファイル/review-speed-design-20261021/、/tmp/CC報告ファイル/review-window-recon-20261021/（社外秘を含むため repo に入れない）。
- 本番の画面全体: 反映後 4.03秒（nginx request_time、2026-10-20 15:30:48Z の1件）。応答 132,644 byte（非圧縮）。
- 画面の待ち順: /me/permissions（ページ）→ /me/permissions（パネル）→ 一覧、の直列（AnalysisRulesPage.tsx:100,:116、NeedsReviewTabsPanel.tsx:66-67,:89）。
- 一覧 API はサーバーで件数・仕入元・一覧の3本を直列に流す（tcg_analysis_review_svc.py:231,:240,:311）。reader 実測 約1.5+1.5+1.0 = 約4.1秒。3本とも review_joins を全 active 投稿について評価する。
- 1本化（V2）は NEEDS_REVIEW で約2.8秒・結果一致。他タブでは大幅悪化（ALL 1.0→33秒）。
- 投稿日は source_messages.line_posted_at。応答の posted_at に既に入っているが、画面型 NeedsReviewItem（NeedsReviewTabsPanel.tsx:35-53）に無い。画面の日付欄（:165-178）は gemini.span を整形したもので投稿日ではない（既存の食い違い）。
- 件数分布（2026-10-20 18:47:53Z）: 137行中 24時間以内 80 / 24〜48時間 10 / 48時間〜7日 26 / 7日超 21。
- 24時間の絞りを where に足すと 6〜14秒に悪化（line_posted_at の index で推定1〜7行・実80行の Nested Loop。EXPLAIN 推定のみ）。一番速い形（F3）でも約3.8秒。
- gzip は frontend/nginx.conf:8-13 だけ。API が通る外側 nginx（nginx/nginx.conf:217-230,:498-502）と backend に無い。20行で 110,236→31,757 byte。SSE 用 location は別（nginx.conf:158-208,:420-470・proxy_buffering off）。
- 並び: result_order_sql の呼び出し元は要確認一覧・配信（在庫表・閲覧）・取り込み進捗（tcg_analysis_review_svc.py:19,249,308／tcg_distribution_svc.py:38,348／tcg_import_progress.py:11,122）。正本 ADR-1023:70、ADR-1014:121。
- 画面: PAGE_SIZE=20（NeedsReviewTabsPanel.tsx:25）。API の limit は 1〜500（routers/tcg_analysis_review.py:126-127）。件数切替 25/50/100 の既存実装は無し。金型は Select（components/Select.tsx:64,126）、絞り切替は Button + aria-pressed の既存型（InventoryToolbar.tsx:68-80）。
- 未確認: 3本・窓付きの遅さの確定原因（§10-4 で確定する）、JIT の影響、/me/permissions 2回の所要時間、25/50/100件の gzip 後サイズ。

### 10-4. 原因の確定（PO 台本・読み取り専用）
- 台本: ~/CC報告ファイル-keep/review-speed-explain-20261021/run-explain.sh（BEGIN READ ONLY … ROLLBACK、各文 60秒上限、postgres コンテナの psql 1本、直列）。
- 測る形: 現状3本 / V2（25件）/ 24時間の絞りを直接 / F3 / 絞りなし新しい順。
- 結果と、それに基づく速さの直し方は、本節に追記してから審査に出す。
- 1回目の結果（2026-10-20 19:18:23Z〜19:19:28Z、RESULT は台本の照合で確認、生出力 ~/CC報告ファイル-keep/review-speed-explain-20261021/out_20261020-191823.txt、読み解き /tmp/CC報告ファイル/review-speed-explain-analysis-20261021/SUMMARY.md）:
  | 形 | Execution Time ms | うち JIT Total ms |
  |---|---|---|
  | 現状 件数 | 1270 | 336 |
  | 現状 仕入元 | 1216 | 321 |
  | 現状 一覧20件 | 1044 | なし |
  | 1本化 V2 25件 | 2360 | 996 |
  | 24時間の絞りを直接 25件 | 55293 | なし |
  | F3（絞りの比較で索引を外す形）25件 | 1004 | なし |
  | 絞りなし新しい順 25件 | 1068 | なし |
- 読み解き（事実）: 24時間の絞りを直接足すと source_messages の索引走査が推定1行・実59行と過小見積りになり、products の Seq Scan（1439行）が loops=1037 で約52.8秒。F3 は推定79行で loops=1（72ms）。JIT は計画コストが jit_above_cost 既定 100000 を超える3本（件数・仕入元・V2）だけに掛かる。件数の JIT 以外の内訳は、空箱判定の Values 集計 3つ計約250ms（loops=1223）、cr_prev の直前投稿探索 約117ms ほか。
- （2回目で確定）jit=off で実際に何ms 減るか（上の JIT Total は上限）、アプリのロール（ADR-1018 は salesanchor_app・RLS 有効、今回は jarvis superuser で測定）での計画、バインド変数での計画。→ 2回目の測定（jit 既定/off・アプリのロール・新しい形 W25/50/100）で確定する。

- 2回目の結果（2026-10-20 19:51:52Z〜19:52:27Z、アプリと同じロール salesanchor_app・superuser でない・RLS 迂回なし、RESULT OK、24文すべて1回ずつ・ERROR 0・ROLLBACK 1、生出力 ~/CC報告ファイル-keep/review-speed-explain-20261021/out2_20261020-195152.txt、読み解き /tmp/CC報告ファイル/review-speed-explain2-20261021/analysis/SUMMARY.md・table.md・top_nodes.md）。Execution Time ms（r1 / r2）:
  | 形 | JIT あり（今の設定） | JIT なし |
  |---|---|---|
  | 現状 件数 | 1445 / 1453 | 1094 / 1072 |
  | 現状 仕入元 | 1367 / 1576 | 995 / 1018 |
  | 現状 一覧20件 | 1033 / 1021（JIT 掛からず） | 989 / 1009 |
  | 現状3本の合計 | 3844 / 4049 | 3078 / 3099 |
  | 1本化（絞りなし・今の並び）25件 | — | 1521 / 1456 |
  | W: 1本化＋24時間（F3）＋新しい順 25件 | 2135 / 2151 | 1142 / 1121 |
  | W 50件 | — | 1104 / 1819（r2 だけ外れ。原因は出力から読めない） |
  | W 100件（返り80行＝24時間内の全件） | — | 1096 / 1119 |
  | 1本化（絞りなし）＋新しい順 25件 | — | 1441 / 1499 |
- 読み解き（事実）: JIT あり/なしの差は JIT Total とほぼ一致（W25 差 993/1029 に対し JIT 992/1017）。JIT は計画コストが 100000 を超える件数・仕入元・W だけに掛かる（一覧20件はコスト 44241 で掛からない）。W の計画コストは 25/50/100 件で同一（165790）で、件数を増やしても時間はほぼ増えない。salesanchor_app のまま `SET LOCAL jit = off` が ERROR なく効いた（同ブロック）。1回目の「24時間を直接」で起きた products の全件走査×1037回は W では出ない。
- 結論（設計判断）: 要確認タブの既定表示は、W 形（件数・仕入元・ページを1本の SQL で返す＋24時間の絞りは F3 形＋投稿日の新しい順）を JIT なしで流す。DB 側は 約4.0秒 → 約1.1秒（実測）。絞りを外したときも 約1.5秒（実測）で今より速い。
- 未確認（この設計の合格を妨げない理由つき）: W50 r2 の 700ms の外れ（r1 と W25/W100 は約1.1秒で、計画は同一）。バインド変数とリテラルでの計画差（実装後に本番 nginx の request_time で KPI-3a を測る）。絞りを外して100件のとき（W100 から伸びない見込みだが推定は事実扱いしない→実装後に測る）。/me/permissions 2回・転送・描画の時間（KGI-3 の Playwright 計時で測る）。

### 10-5. 見え方の変更（PO 提案どおり。金型・i18n・SSOT を守る）
- 既定: 投稿から24時間以内（line_posted_at >= 取得時点の now() - 24時間）だけ、投稿日の新しい順。
- 絞りを外すボタン: Button 金型の aria-pressed 切替（InventoryToolbar.tsx:68-80 と同じ型）。i18n キーは needsReview 名前空間に新設（ja.json・en.json 同一キー、ADR-027）。
- 件数: Select 金型で 25（既定）/ 50 / 100。生 select・直値の色は使わない（ADR-144、ADR-067）。
- 日付欄: 投稿日（posted_at）を表示する（既存の食い違いの是正）。
- API: 一覧 API に「投稿からの時間の上限」と「並び（投稿日の新しい順）」の引数を足し、既定は従来どおり（CSV・シート・SupplierDetailView・InventoryRowDrawer は呼び方を変えないので中身が変わらない）。並びは result_order_sql 本体を変えず、要確認一覧の ORDER BY の先頭に投稿日を前置する（在庫表・配信・取り込み進捗は無影響）。
- データ: 新しい表・列・置き場所は作らない（投稿日は既存の source_messages.line_posted_at を読むだけ）。
- 圧縮: 外側 nginx の API 経路に gzip（application/json）。SSE の location と text/event-stream は対象にしない。

### 10-6. 速さの直し方（§10-4 の実測に基づく）
- S1 要確認タブ（status_tab=NEEDS_REVIEW）だけ、件数・仕入元・一覧の3本を W 形の1本に置き換える。他タブ（ALL ほか）は今の3本のまま（1本化は ALL で 1.0→33秒に悪化した実測があるため、§10-3）。
- S2 その1本の直前に、同じトランザクション内で `SET LOCAL jit = off` を流す（このトランザクションだけに効き、他の画面・在庫表・配信には効かない）。
- S3 24時間の絞りは F3 形（`(sm.line_posted_at + interval '0 second') >= now() - interval '24 hours'`）で書き、なぜ +0秒 を足すか（索引の過小見積りで 55秒になった実測）をコードのコメントとテストで固定する。
- S4 圧縮（§10-5）は別便。外側 nginx の設定変更で、S1〜S3 と同時に入れると効果が分けて測れないため（変更は一度に1つ）。
- S5 /me/permissions の2回直列は、S1〜S4 の後に KGI-3 が 2.0秒を超えた場合だけ設計する。

### 10-7. 便の分け方と受入条件
| 便 | 中身 | 受入条件（○×） | 検証方法 |
|---|---|---|---|
| 便1 | S1〜S3 ＋ §10-5 の画面（24時間ボタン・新しい順・25/50/100・投稿日の表示）＋API の新しい引数（既定は従来） | ①既定表示の一覧 API の request_time が 2.0秒以下（3回の中央値）②W 形と旧3本の件数・仕入元・行の中身が一致（順番は新しい順）③絞りを外すと旧3本と件数・中身が一致 ④CSV・シートの sha256 が変更前と一致 ⑤他タブの SQL が変わらない（テストで固定）⑥生 select・直値色・ハードコード文字列が0（CI の UI ガバナンス・i18n 検査） | ①本番 nginx ログ ②③本番 reader で旧形と新形を比べる ④§5 と同じ方式 ⑤⑥ pytest・CI |
| 便2 | S4 圧縮 | 一覧 API の body_bytes_sent が変更前（約132KB/20行）より小さい・SSE の3本が切れない | 本番 nginx ログ・SSE の接続ログ |
| 判定 | KGI-3 | 画面遷移〜一覧1行目の描画が 2.0秒以内（3回の中央値） | 本番 Playwright 計時。超えたら S5 を設計 |

### 10-8. 弊害・戻し方・維持
- 弊害: 既定では24時間より古い要確認行が見えない（PO 提案どおり。ボタンで外せる）。JIT を切るのはこの1本だけで、他は今の設定のまま。
- 戻し方: 便1 は PR の revert（DB の変更なし・新しい表や列なし）。便2 は nginx 設定の revert。
- 維持: F3 形と JIT なしの理由はコードのコメントとテスト（SQL 文字列の固定）に残す。KGI-3 は便ごとに本番で測り、本節に追記する。

### 10-9. 未解決
- 実装は PO の実装承認後（§10-1 の約束どおり作り始める前に再確認する）。
