# design: 本番の LINE解析を試作版 v102 へ切り替える

- 作成: 2026-10-09 Claude Opus（設計担当・ccopusgo）。recon: [recon.md](./recon.md)（基準 origin/main fb036a2）。
- 状態: 設計案（Opus 自己審査は §11。独立した第二者レビューではない）。
- 社外秘: 指示書本文・仕入元原文は書かない。

## 1. 目的（PO の言葉）

「本番の解析システムと gemini が原文抽出、システムが解析の試作システムを本番に切り替えて実運用したい…今後は本番で運用しつつ、調整を進めたい」（2026-10-09、引き継ぎ §冒頭）。

利用者に見える変化:
- 新着の LINE 投稿は、Gemini が原文の行を書き写し（v102）、システムが商品・状態・価格・数量を決める。
- 要確認ページに「出どころ（Gemini／システム）」の列が付き、理由が日本語（英語画面では英語）で出る。
- Gemini の書き写しを人が直したら、その投稿はシステム解析をやり直す（recon §0-1 P1）。
- システム解析の要確認を人が直したら、その件は配信に回り、追加で配信される（同 P1）。
- 戻すときは v6 に1か所の設定で戻せる。

## 2. 受入条件（KGI）

| # | 基準（○×で判定） | 検証方法 |
|---|---|---|
| K1 | 切替後に取り込んだ投稿の analysis_results.engine_version がすべて v102 の定数 | 本番 SELECT（engine_version 別件数、切替時刻以降） |
| K2 | v6 に戻した後に取り込んだ投稿の engine_version がすべて v6 の定数 | 同上 |
| K3 | review_reasons が空でない件は配信の出力に 0 件 | pytest（PostgreSQL）で fetch_output_rows を検査 |
| K4 | 要確認ページに出どころ列があり、理由コードが生の英字で表示される件が 0 | vitest ＋ 本番画面の目視（PO） |
| K5 | Gemini の書き写しを直して保存すると、同じ投稿の analysis_results が作り直される（computed_at が保存時刻以降） | pytest ＋ 本番の操作1回 |
| K6 | システム側の要確認を直すと配信が起動し、その件が配信の出力に入る | pytest ＋ 本番の操作1回 |
| K7 | v102 の Gemini 呼び出し1回ごとに llm_usage_events に purpose='line_extraction' の行が1行 | pytest ＋ 本番 SELECT |
| K8 | 同じ Gemini 応答から、本番経路と試作版（prompt_ab）で同じ件（商品・状態・単位・価格・数量・理由）が出る | pytest（保存済み応答の再計算。Gemini 呼び出しなし） |

## 3. 対象と対象外

対象: Celery の抽出タスクの分岐、v102 の結果の DB 書き込み、理由コード表、要確認ページ（本番タブの列・訳、投稿の要確認、Gemini 書き写しの修正、システム要確認の修正→配信）、再解析 API の分岐、費用台帳。

対象外:
- Gemini 抽出の指示書・仕入元ルール・応答スキーマの中身（Gemini 抽出担当セッションの受け持ち。recon §0 引き継ぎ）。
- 試作版のシステム解析の判定ロジックの変更（prompt_ab の結果を変えない。K8）。
- v6 の analyzer（tcg_analyzer_svc.py）の判定ロジック・v7 試運転。
- 予算での自動停止（recon G8。PO の依頼外。費用は台帳で測る）。
- 配信シートの書き方（全置換のまま。recon §3-1）。

## 4. 変更前後

### 4-1. 配線（変更後）

```
取り込み → extraction_jobs(pending) → Celery _run_extraction
  ├─ LINE_ANALYSIS_ENGINE=v6（既定）: 今のまま（v6 Gemini → extraction_items → analyze_extraction_job）
  └─ LINE_ANALYSIS_ENGINE=v102:
       ① Gemini 段: call_gemini_raw_copy_v8（指示書 key は DB、thinking high、V102 スキーマ）
          → extraction_items（1件=1行: source_lines・raw_price・raw_quantity・gemini_index）
          → extraction_jobs.gemini_unsure（Gemini の unsure 申告）・prompt_version（版の記録）
          → llm_usage_events（purpose='line_extraction'）
       ② システム段: extraction_items と原文から v102 の解析を実行
          → analysis_results（engine_version='v102-…'、review_reasons＝件の理由コード）
          → extraction_jobs.review_reasons（投稿単位の理由コード）
          → _merge_supplier_products（is_current、ADR-158）
  → 配信（今のまま。review_reasons があれば自動的に除外: recon §1-3）
```

- 切替は環境変数 `LINE_ANALYSIS_ENGINE`（docker-compose.yml の celery-worker と backend に `${LINE_ANALYSIS_ENGINE:-v6}`）。新しい名前なので本番 .env に無く、既定値がそのまま効く（recon §3-2）。切替・戻しは既定値を変える PR → デプロイ。緊急時は PO が .env に `LINE_ANALYSIS_ENGINE=v6` を書いて celery-worker を再作成する。
- 版は投稿ごとに extraction_jobs.prompt_version に残す（`v102:<prompt_key>:<sha256先頭12>`）。再解析・修正はこの値で v6 / v102 を振り分ける（設定ではなく投稿の記録で決める＝途中で設定を変えても混ざらない）。

### 4-2. DB（すべて追加のみ。DROP なし）

| 表 | 追加 | 意味（SSOT） |
|---|---|---|
| public.review_reason_codes（新） | code PK, source CHECK('gemini','system'), fix_stage CHECK('extraction','analysis'), i18n_key, created_at | 理由コードの正本。出どころ・直す工程・画面の言葉の鍵（PO P3）。画面の言葉そのものは ja.json/en.json（ADR-027） |
| public.extraction_items | source_lines INTEGER[] NULL, gemini_index INTEGER NULL | Gemini が書き写した行（飛び番を保持）と Gemini の出力順。v6 の行は NULL。line_start/line_end は min/max を入れ、既存画面との互換に使う |
| public.extraction_jobs | gemini_unsure JSONB NULL, review_reasons TEXT NULL | Gemini の unsure 申告（Gemini 段の出力）と投稿単位の理由コード（システム段の出力。カンマ区切り、analysis_results と同じ形） |

- 同じ事実を2か所に持たない: 件の理由は analysis_results.review_reasons だけ、投稿の理由は extraction_jobs.review_reasons だけ、出どころは review_reason_codes だけ。v102 の件の名前（raw_product_name）は Gemini の出力ではないので入れない（NULL）。画面は原文と source_lines から行の文字を組み立てる。
- `fix_stage` は PO P3 の表に1列足すもの（どの工程で直すかでやり直し先が決まる、P1）。
- **制約（ADR-1007）**: migration は構造の変更だけで、INSERT 等の値の操作は書かない（docs/adr/ADR-1007-migration-structure-only-run-once.md:31-37）。値は画面・CSV・テナント作成のコード・1回だけのデータ変更（PO 合意・DRY-RUN→COMMIT・docs/handoff に記録）のいずれか。review_reason_codes の初期行の入れ方は §9 Q3（PO 判断）。表の作成（構造）は migration で行える。

### 4-3. 理由コード表の初期行（出どころ・直す工程）

- gemini: gemini_unsure, gemini_unsure_invalid（Gemini が自分で書いた申告。v101.py:229）。fix_stage=extraction。
- system・extraction（書き写しの直しで解ける）: item_shape_invalid, price_not_in_lines, duplicate_price_line, quantity_no_number, possible_footer_line, heading_ship_with_own_ship, no_items, possible_missing_item, response_unreadable, ship, condition（迷う行）。
- system・analysis（マスタ・商品割当で解ける）: product_not_in_master, product_multiple, condition_unknown, condition_multiple_candidates, unit_unknown, category_unknown, extract_exception, および v6 の pid_unresolved, multi_candidate, note_unmatched, unit_unresolved, price_unresolved, excluded, empty_box, empty_box_ambiguous, empty_box_master_unavailable。
- 抜け漏れ防止: backend のテストで「コードが出しうる理由コード（定数）」がすべて表の初期行（migration ファイル）にあることを検査する。新しいコードは表に1行足すまで CI が通らない。

### 4-4. analysis_results への書き方（v102）

| 列 | 値 |
|---|---|
| extraction_item_id | 対応する extraction_items.id |
| product_id / pid_resolved / pid_basis | match_status='matched' なら product_id・TRUE。それ以外 NULL・FALSE。pid_basis='V102:'+match_status |
| unit_id / unit_canonical / unit_resolved | unit の canonical → load_lookup_maps()[2]。'none' は NULL・FALSE |
| condition_id / condition_canonical / condition_basis | condition の canonical → cond_entries の id。未解決（'none'・'不明'）は v6 と同じ FLAG_SINGLE（CN0008）で埋め、理由 condition_unknown 等が付くので配信されない |
| price_normalized / quantity_normalized | v102 の値（resolve_price_quantity。小数・万に対応、PO D3） |
| status / exclusion | v102 の status / status_effect |
| note_ja | **§9 Q1（PO 判断）** |
| work_id | products.work_id |
| needs_review / review_reasons | 件の review の kind を重複なしでカンマ結合。空でなければ TRUE |
| engine_version | 定数 `v102-f_c`（定義は1か所） |

- v6 専用の後処理（E3a/E5/E3b/E4・reanalysis_condition）は v102 では行わない（v102 は独自の単位・状態の解決を持つ）。is_current は共通の _merge_supplier_products を呼ぶ。

### 4-5. 再解析・修正の流れ（PO P1）

- Gemini 段の修正（fix_stage=extraction の理由、または投稿単位の理由）: 要確認ページの「投稿」タブ → 原文と Gemini の件（行・価格・数量）を表示 → 件の追加・削除・行/価格/数量の修正 → 保存で ①item_corrections に修正履歴（field_name='v102_items'、変更前後 JSON）②その投稿の extraction_items を置き換え ③システム段だけを再実行（Gemini は呼ばない）。
- システム段の修正（fix_stage=analysis の理由）: 既存の商品割当・状態確認・マスタ登録に加え、「確認済み（このままで良い）」を記録（item_corrections field_name='review_ack'、対象コード）。システム段の再実行でも確認済みのコードは付け直さない。修正で件の要確認が解けたら配信タスクを起動（全置換なので、解けた件が追加で出る）。
- 既存の再解析 API（/extraction-jobs/{id}/reanalyze）は prompt_version で v6 / v102 を振り分ける。v102 の投稿に v6 の analyzer を走らせない。

### 4-6. 画面（デザインシステム遵守、ADR-144・ADR-027）

- 本番タブ: 「出どころ」列を追加（Gemini／システム）。理由は API が返す i18n_key で t() 表示。未知コードは needsReview.reason.unknown（コード併記）。
- 投稿タブ（新）: 投稿単位・Gemini 段の要確認。DataTable／Modal／TextField／Button／Tabs の金型のみ。原文の行の色分けは既存の ShadowSourcePane があれば再利用（実装カードで確認）。
- 新規の生 input・色直値は禁止（ui-allow 例外も作らない）。

## 5. 実装の分割（1つずつ: マージ → デプロイ → 確認 → 次）

| 便 | 内容 | 危険パス | 本番の挙動 |
|---|---|---|---|
| A | review_reason_codes 表＋初期行、要確認 API に source/i18n_key、本番タブの出どころ列・訳 | migrations/ | v6 の要確認の表示が日本語化・出どころ列（全部システム） |
| B | 列追加（extraction_items・extraction_jobs）、v102 本番エンジン（既定 v6）、再解析の振り分け、費用台帳 | migrations/ | 変化なし（既定 v6） |
| C | 投稿タブ・Gemini 書き写しの修正 → システム段の再実行 | なし | v102 の投稿が無い間は空 |
| D | 確認済み記録・システム修正 → 配信起動 | なし | 要確認を直したとき配信が起動 |
| E | 既定を v102 に切替 | docker-compose.yml | **切替**（§9 の PO 回答が前提） |

- B の v102 部品は試作版のファイル（prompt_ab.py の _v102_row_fields・V102_PROMPT）を services 側へ移し、prompt_ab はそれを呼ぶ形にする（結果は変えない。K8）。試作版のファイルは複数セッションが直すため、B の PR 本文に変更点を明記する。

## 6. 代替案

| 案 | 不採用の理由 |
|---|---|
| 切替を DB 設定（tcg_distribution_settings）に置く | 配信設定の表で意味が違う。本番 DB の書込は PO の `!` が要る（引き継ぎ §6）。環境変数＋既定値なら PR で記録が残り、デプロイで戻せる |
| analysis_results に出どころ列を足す | 同じ情報が2か所になる（PO P3 で不採用） |
| Gemini の応答 JSON を投稿ごとにそのまま保存し、件の表を作らない | 既存の要確認画面・配信・訂正が extraction_items を起点にしており、別の置き場になる（データ分散） |
| v6 と並べて動かす | Gemini 呼び出しが2倍。v6 との比較は物差しにしない（PO 2026-10-07）。戻しは設定1つで足りる |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| v102 の要確認が多く配信件数が減る | 要確認は配信しない（PO 方針）。件数は切替後に本番 SELECT で測り PO に報告 |
| Gemini 費用 | 台帳で日次に測る。1投稿約 0.0079 USD（引き継ぎ §1、f_c・high の125投稿実績）。1日の投稿数は未確認（recon U3） |
| 抽出の失敗 | Gemini 呼び出しの失敗は既存どおり status='error'（再抽出 API が使える）。システム段の例外は投稿に extract_exception を付け、件を落とさない |
| 試作版ファイルの同時編集 | B の PR で移した関数名を本文に明記。マージ前に試作版ファイルを触る open PR を再確認 |
| 空箱の扱いが v6 と違う可能性 | B の実装カードで v102 の空箱の扱いを読み、無ければ PO に報告（推測で足さない） |

## 8. 戻し方

- E を戻す PR（既定 v6）→ デプロイ。以後の投稿は v6。切替中に取り込んだ投稿は prompt_version が v102 のまま残り、再解析は v102 で動く（混ざらない）。
- A〜D は revert で戻せる。migration は追加のみで、戻しは列・表を残したまま使わない（DROP は PO 本人の GO が必要なため行わない）。

## 9. PO に確認すること（E の前に必要。A〜D は待たずに進める）

| # | 内容 |
|---|---|
| Q1 | v102 は note_ja（配信シートの備考列）を作らない。切替後は備考列が空になる。v6 と同じ備考マスタで件の行から作るか、空でよいか |
| Q2 | 本番の現状値（recon U1〜U3: 自動解析・自動配信の設定、1日の投稿数）。PO の SELECT 実行か、読み取りの permit-danger |
| Q3 | 理由コード表の初期行（約30行）の入れ方。ADR-1007 により migration に INSERT を書けない。推奨: 1回だけのデータ変更（SQL を docs/handoff/v102-prod-switch/ に置き、DRY-RUN→COMMIT は PO が `!` で実行）。新しいコードを足すときも同じ手順。便 A・C・D の画面はこの表を使うため、Q3 の回答まで A・C・D は着手しない |

- 着手順の変更（Q3 による）: **B を先に行う**（B は理由コード表に依存しない。件の理由は今の review_reasons の形で書く）。A・C・D は Q3 の回答後。

## 10. 外部・過去事例の参照と我々への応用

- 外部事例: 該当なし。社内の試作版の正解表（G3 v2）での実測（引き継ぎ §2）を判断材料とし、外部の数値は使わない。切替方式（設定1つで戻せる段階切替）は一般的な feature flag の方式で、本設計の成功の証明には使わない。
- 過去事例（社内）と応用:
  - #4048 のデプロイで値を書く migration が商品マスタを上書きした事故（2026-10-08）→ 本設計の migration は構造のみ（ADR-1007）。理由コード表の値は 1回だけのデータ変更で入れる（§9 Q3）。
  - 2026-10-03 products の列数上限到達（列の追加・削除の繰り返し）→ 列は追加のみで、戻しでも DROP しない（§8）。
  - 試作版ファイルを複数セッションが同時に直して衝突した（#4072 と便B）→ 移した関数名を PR 本文に明記し、試作版の出力が変わらないことを K8 と test_v102_review_source.py で検査する。

## 維持の仕組み

| 何を守るか | 仕組み | 担当 |
|---|---|---|
| 本番経路と試作版で同じ結果（K8） | test_line_analysis_v102_pg.py（CI の PostgreSQL ジョブ） | CI |
| 要確認の件は配信しない（K3） | 同上（fetch_output_rows の検査） | CI |
| 理由コードの抜け漏れ | 便A で追加するテスト（§4-3） | CI |
| 既定は v6（切替は PR でのみ） | docker-compose.yml の既定値 `${LINE_ANALYSIS_ENGINE:-v6}` と get_engine のテスト | CI・PR レビュー |
| migration は構造のみ | migration-guard.yml（チェック3〜8） | CI |
| 費用 | llm_usage_events（purpose='line_extraction'）を切替後に日次で確認 | 設計担当 Opus（PO へ報告） |

## 11. 設計審査（Opus 自己審査。独立レビューではない）

- 判定: **APPROVE（便 B）／ A・C・D は Q3、E は Q1・Q2 の回答待ち**。
- 既存決定との整合: D2（先にシステム側を整える → A〜D の後に E）、D3（価格は v102 の正規化、要確認は配信しない、直したら再配信＝C・D）、D4（analysis_results に1本化）、D6（配信除外は既存の review_joins で成立、recon §1-3）、P1〜P3。
- SSOT: 件の理由・投稿の理由・出どころ・Gemini の行がそれぞれ1か所。
- 未解決: Q1・Q2、空箱（B のカードで確認）。
- 維持の仕組み: 理由コードの抜け漏れは CI テスト（§4-3）、v102 と試作版の一致は K8 のテスト。
