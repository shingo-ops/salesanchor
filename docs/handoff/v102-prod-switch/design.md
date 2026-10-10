# design: 本番の LINE解析を試作版 v102 へ切り替える

- 作成: 2026-10-09 Claude Opus（設計担当・ccopusgo）。recon: [docs/handoff/v102-prod-switch/recon.md](./recon.md)（基準 origin/main fb036a2）。関係 ADR: ADR-154（LINE解析・配信）、ADR-158、ADR-1004、ADR-1007、ADR-027、ADR-144。基準の列はすべて ○× で判定する。
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

| # | 基準 | 検証方法 |
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
| public.review_reason_codes（新） | code PK, source CHECK('gemini','system'), fix_stage CHECK('extraction','analysis'), created_at | 理由コードの正本。出どころ・直す工程（PO P3）。画面の言葉は ja.json/en.json の `reviewReason.<code>`（ADR-027。鍵はコードから決まるので列に持たない＝§12-1） |
| public.extraction_items | source_lines INTEGER[] NULL, gemini_index INTEGER NULL | Gemini が書き写した行（飛び番を保持）と Gemini の出力順。v6 の行は NULL。line_start/line_end は min/max を入れ、既存画面との互換に使う |
| public.extraction_jobs | gemini_unsure JSONB NULL, review_reasons TEXT NULL | Gemini の unsure 申告（Gemini 段の出力）と投稿単位の理由コード（システム段の出力。カンマ区切り、analysis_results と同じ形） |

- 同じ事実を2か所に持たない: 件の理由は analysis_results.review_reasons だけ、投稿の理由は extraction_jobs.review_reasons だけ、出どころは review_reason_codes だけ。v102 の件の名前（raw_product_name）は Gemini の出力ではないので入れない（NULL）。画面は原文と source_lines から行の文字を組み立てる。
- `fix_stage` は PO P3 の表に1列足すもの（どの工程で直すかでやり直し先が決まる、P1）。
- **制約（ADR-1007）**: migration は構造の変更だけで、INSERT 等の値の操作は書かない（docs/adr/ADR-1007-migration-structure-only-run-once.md:31-37）。値は画面・CSV・テナント作成のコード・1回だけのデータ変更（PO 合意・DRY-RUN→COMMIT・docs/handoff に記録）のいずれか。review_reason_codes の初期行の入れ方は §9 Q3（PO 判断）。表の作成（構造）は migration で行える。

### 4-3. 理由コード表の初期行（出どころ・直す工程）

- gemini: gemini_unsure（Gemini が自分で書いた申告。v101.py:229）。fix_stage=extraction。
- system・extraction: gemini_unsure_invalid（Gemini の申告の形が不正だとシステムが見つけた。line_analysis_v102_svc.py:196,203 で source=system。2026-10-09 recon で訂正）。
- system・extraction（書き写しの直しで解ける）: item_shape_invalid, price_not_in_lines, duplicate_price_line, quantity_no_number, possible_footer_line, heading_ship_with_own_ship, no_items, possible_missing_item, response_unreadable, ship, condition（迷う行）。
- system・analysis（マスタ・商品割当で解ける）: product_not_in_master, product_multiple, condition_unknown, condition_multiple_candidates, unit_unknown, category_unknown, extract_exception, および v6 の pid_unresolved, multi_candidate, note_unmatched, unit_unresolved, price_unresolved, excluded, empty_box, empty_box_ambiguous, empty_box_master_unavailable。
- 注: unit_unresolved・price_unresolved・excluded は analyzer が書かず、要確認 API の SQL が導出する（tcg_condition_review_svc.py:141-146）。
- 抜け漏れ防止: §12-5 のテスト（初期行の SQL ファイル・コード側の定数・ja/en の訳を突き合わせる）。

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

- 本番タブ: 「出どころ」列を追加（Gemini／システム）。理由は `reviewReason.<code>` で t() 表示。表に無いコードは reviewReason.unknown（コード併記）。詳細は §12。
- 投稿タブ（新）: 投稿単位・Gemini 段の要確認。DataTable／Modal／TextField／Button／Tabs の金型のみ。原文の行の色分けは既存の ShadowSourcePane があれば再利用（実装カードで確認）。
- 新規の生 input・色直値は禁止（ui-allow 例外も作らない）。

## 5. 実装の分割（1つずつ: マージ → デプロイ → 確認 → 次）

| 便 | 内容 | 危険パス | 本番の挙動 |
|---|---|---|---|
| A | review_reason_codes 表＋初期行、要確認 API に理由ごとの source・fix_stage、本番タブの出どころ列・訳（§12） | migrations/ | v6 の要確認の表示が日本語化・出どころ列（全部システム） |
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
| compose の既定値 v102／コードの既定値 v6（未設定時の安全側）。切替は PR でのみ | docker-compose.yml:218 の `${LINE_ANALYSIS_ENGINE:-v102}` と get_engine のテスト（test_line_analysis_v102_svc.py:42-50） | CI・PR レビュー |
| migration は構造のみ | migration-guard.yml（チェック3〜8） | CI |
| 費用 | llm_usage_events（purpose='line_extraction'）を切替後に日次で確認 | 設計担当 Opus（PO へ報告） |

## 11. 設計審査（Opus 自己審査。独立レビューではない）

- 判定: **APPROVE（便 B）／ A・C・D は Q3、E は Q1・Q2 の回答待ち**。
- 既存決定との整合: D2（先にシステム側を整える → A〜D の後に E）、D3（価格は v102 の正規化、要確認は配信しない、直したら再配信＝C・D）、D4（analysis_results に1本化）、D6（配信除外は既存の review_joins で成立、recon §1-3）、P1〜P3。
- SSOT: 件の理由・投稿の理由・出どころ・Gemini の行がそれぞれ1か所。
- 未解決: Q1・Q2、空箱（B のカードで確認）。
- 維持の仕組み: 理由コードの抜け漏れは CI テスト（§4-3）、v102 と試作版の一致は K8 のテスト。

## 12. 便A の詳細（2026-10-09 PO「y」＝Q3 は推奨案：初期行は1回だけのデータ変更）

recon: /tmp の調査結果を本節に転記（基準 origin/main 656817ddd）。理由コードの出どころは file:line で §12-2 の表に記す。

### 12-1. SSOT（同じ事実は1か所）
| 事実 | 置き場所（唯一） |
|---|---|
| 件の理由コード | analysis_results.review_reasons（カンマ区切り。既存） |
| 理由ごとの出どころ・直す工程 | public.review_reason_codes（新） |
| 画面の言葉 | ja.json / en.json の `reviewReason.<code>`（新しい名前空間に集約） |
| 出どころの言葉 | `reviewReason.source.gemini` / `reviewReason.source.system` |

- 訳の集約: 今は理由の訳が `pmgWorkflow.reviewReason.*`（3コード、ja.json:3814-3818）と `conditionReview.reasons.*`（6コード、ja.json:3853-3860）に分かれ、AnalysisDashboardPanel.tsx:1631-1642 は生のコードを出している。便A で `reviewReason.<code>` に集約し、この3画面（ImportWorkflowPanel.tsx:39-47・ConditionReviewPanel.tsx:74-75・AnalysisDashboardPanel.tsx:1639付近）と本番タブを同じ鍵に切り替え、古い2つの鍵の集合は削除する。
- i18n の鍵は列に持たない（コードから一意に決まる。持つと二重管理）。
- 要確認 API の既存の `condition_review.review_reasons`（文字列）は変えない（他の画面が使用）。新しく理由ごとの配列を足す。

### 12-2. 初期行（29行）
| code | source | fix_stage | ja | en | 出す場所 |
|---|---|---|---|---|---|
| pid_unresolved | system | analysis | 商品を特定できない | Product not identified | tcg_analyzer_svc.py:1104・tcg_condition_review_svc.py:142 |
| multi_candidate | system | analysis | 商品候補が複数ある | Multiple product candidates | tcg_analyzer_svc.py:1106 |
| note_unmatched | system | analysis | 備考の変換先が見つからない | No match for the note | tcg_analyzer_svc.py:1108 |
| empty_box | system | analysis | 空箱かどうかの確認が必要 | Empty box needs confirmation | tcg_analyzer_svc.py:1578 |
| empty_box_ambiguous | system | analysis | 空箱の説明があいまい | Empty-box description is ambiguous | tcg_analyzer_svc.py:1578 |
| empty_box_master_unavailable | system | analysis | 空箱の状態定義が使えない | Empty-box definition unavailable | tcg_analyzer_svc.py:1576 |
| unit_unresolved | system | analysis | 単位を特定できない | Unit not identified | tcg_condition_review_svc.py:143 |
| price_unresolved | system | analysis | 価格を読み取れない | Price not readable | tcg_condition_review_svc.py:144 |
| excluded | system | analysis | 除外の対象 | Excluded | tcg_condition_review_svc.py:145 |
| item_shape_invalid | system | extraction | Gemini の出力の形が正しくない | Gemini output has an invalid shape | gemini_raw_copy_v101.py:169 |
| price_not_in_lines | system | extraction | 価格が原文の行に無い | Price not found in the source lines | gemini_raw_copy_v101.py:169 |
| duplicate_price_line | system | extraction | 同じ価格の行が重なっている | Duplicate price line | gemini_raw_copy_v101.py:169 |
| ship | system | extraction | 発送の行かどうか確認が必要 | Check whether this is a shipping line | gemini_raw_copy_v101.py:53,561 |
| condition | system | extraction | 状態の行かどうか確認が必要 | Check whether this is a condition line | gemini_raw_copy_v101.py:53,561 |
| quantity_no_number | system | extraction | 数量に数字が無い | Quantity has no number | gemini_raw_copy_v101.py:1047 |
| possible_footer_line | system | extraction | 末尾の定型文かもしれない | May be a footer line | gemini_raw_copy_v101.py:1047,1119 |
| unit_unknown | system | analysis | 単位が分からない | Unit unknown | gemini_raw_copy_v101.py:1048 |
| category_unknown | system | analysis | 商品の種類が分からない | Category unknown | gemini_raw_copy_v101.py:1048 |
| heading_ship_with_own_ship | system | extraction | 見出しと件の両方に発送の記載がある | Shipping stated in both heading and item | gemini_raw_copy_v101.py:1049 |
| no_items | system | extraction | 商品が1件も取れていない | No items extracted | gemini_raw_copy_v101.py:1050 |
| possible_missing_item | system | extraction | 取りこぼしの可能性がある | An item may be missing | gemini_raw_copy_v101.py:1050 |
| product_not_in_master | system | analysis | 商品マスタに無い | Not in the product master | gemini_raw_copy_v102_product_first.py:70 |
| product_multiple | system | analysis | 商品候補が複数ある（新方式） | Multiple product candidates (new method) | gemini_raw_copy_v102_product_first.py:71 |
| condition_multiple_candidates | system | analysis | 状態の候補が複数ある | Multiple condition candidates | gemini_raw_copy_v102_product_first.py:68 |
| condition_unknown | system | analysis | 状態が分からない | Condition unknown | gemini_raw_copy_v102_product_first.py:67 |
| gemini_unsure | gemini | extraction | Gemini が自信なしと申告 | Gemini reported it is unsure | gemini_raw_copy_v101.py:229 |
| gemini_unsure_invalid | system | extraction | Gemini の申告の形が正しくない | Gemini's report has an invalid shape | gemini_raw_copy_v101.py:229・line_analysis_v102_svc.py:203 |
| response_unreadable | system | extraction | Gemini の応答を読めない | Gemini response unreadable | line_analysis_v102_svc.py:66 |
| extract_exception | system | analysis | 解析の途中でエラーが起きた | Error during analysis | line_analysis_v102_svc.py:67 |

- 追加の鍵: `reviewReason.unknown`「登録されていない理由（{{code}}）」/ "Unregistered reason ({{code}})"、`reviewReason.source.gemini`「Gemini」/"Gemini"、`reviewReason.source.system`「システム」/"System"、`reviewReason.separator`「、」/", "、`needsReview.source`「出どころ」/"Source"。

### 12-3. 変更前後
- DB: migration で表を作る（構造のみ。CHECK でコードの形・source・fix_stage を制限）。初期行は docs/handoff/v102-prod-switch/data/review_reason_codes/ の SQL を、デプロイ後に precheck→dryrun→commit→verify（ADR-1007:33-36）。
- API（GET /tcg/analysis-results）: 各件に `review_reason_details: [{code, source, fix_stage}]` を追加。元は今の `condition_review.review_reasons` を「,」で分けたもの（順番そのまま・重複なし）。表に無いコードは source・fix_stage を null。表の読み込みは1リクエスト1回、置き場所は新しい1ファイル（services/review_reason_codes_svc.py）。
- 画面（本番タブ）: 「出どころ」列を追加（その件の理由の出どころを重複なしで gemini→system の順に並べる。出どころが1つも分からなければ「—」）。「確認理由」列は review_reason_details の各コードを t(`reviewReason.<code>`) で訳して separator で結ぶ。訳が無いコードは reviewReason.unknown。
- 3画面の訳の切り替え（§12-1）。
- 使う金型: 既存の DataTable の列定義だけ（新しい部品・色・生の要素を作らない）。

### 12-4. 本番での順番と、間の状態
1. PR マージ → デプロイ（表は空）。この間、本番タブの理由は訳が出る（訳は ja.json にある）が、出どころは「—」になる（表が空なので）。要確認の判定・配信は何も変わらない（API の足し算だけ）。
2. 初期行を書く（precheck で表が空・アプリの DB 利用者が SELECT できることを確認 → dryrun で29行・ROLLBACK → commit → verify で29行が SQL ファイルと一致）。
3. 本番 API を読み取りで確認（出どころが入る）。

### 12-5. 維持の仕組み（抜け漏れ防止のテスト）
- 初期行の SQL ファイルのコード集合 ＝ ja.json の `reviewReason` のコード鍵 ＝ en.json の同じ鍵（追加鍵 unknown・source・separator を除く）。
- コード側で名前の付いた理由コードの定数（v101 の REJECTED_*・ROLE_SHIP/ROLE_CONDITION・:1047-1050 の定数・UNSURE_*、product_first の :67-71、line_analysis_v102_svc の :66-67、tcg_empty_box_rules の定数）がすべて初期行にある。
- 初期行の各コードの文字列が backend/app のどこかに現れる（使われない行を残さない）。
- 新しい理由コードを足すときは「コード＋ja/en＋この SQL の型で1行の追加データ変更」が揃わないと CI が通らない。

## 13. 便C・便D の詳細（2026-10-09 PO「便C・便D を進める」）

recon（基準 origin/main f0d710185、file:line は本節に転記）。本番の読み取り（2026-10-09）: extraction_jobs 2,396件のうち v102 は0件、自動解析・自動配信はオン（celery-worker の TCG_AUTO_ANALYZE=1・TCG_AUTO_DISTRIBUTE=1）、エンジン v6、1日の解析投稿数は直近14日で58〜97件。

### 13-1. PO の規則（2026-10-09 原文）
「要確認を直して回す際も投稿日時が古ければ解析して記録だけ残す、投稿日時が最新の商品であれば配信リストに加える」
- 事実: 「最新」は is_current で決まる。単位は同じ仕入元（supplier_channel_id）の (product_id, condition_id) で、`ORDER BY sm.received_at DESC, ar.computed_at DESC` の1位だけ TRUE（backend/app/services/tcg_analyzer_svc.py:1802-1819）。received_at は LINE の投稿時刻（backend/app/services/tcg_line_import_svc.py:303,312-313、取り込み時刻は created_at）。配信は is_current=TRUE かつ cr.needs_review IS FALSE 等（backend/app/services/tcg_distribution_svc.py:260-267）。
- よって規則は「直す→解析し直す→is_current を付け直す→配信」で満たせる。古い投稿の件は解析・記録はされるが is_current=FALSE なので配信に出ない。

### 13-2. 今の不足（事実）
| # | 不足 | 根拠 |
|---|---|---|
| G1 | v102 のシステム段は人の判断（item_corrections）を読まないため、再実行で手で決めた商品が戻る | backend/app/services/line_analysis_v102_svc.py に item_corrections の参照0件、UPSERT は product_id 等を上書き（:546-565） |
| G2 | 商品を手で決めても v102 の理由（product_not_in_master・product_multiple）が残り、配信されない | backend/app/services/item_corrections_svc.py:59-73 は product_id 等3列のみ更新、cr.needs_review は review_reasons から計算（backend/app/services/tcg_condition_review_svc.py:139-168） |
| G3 | 「このままで良い」を記録して理由を解く仕組みが無い（review_ack はコードに0件） | grep |
| G4 | 直した後に配信を起動する経路が無い。配信は全置換で、同時起動の排他・間引きが無い | backend/app/services/tcg_distribution_svc.py:515-518、排他の文字列0件 |
| G5 | 商品を A→B に直すと、A の組の is_current が付け直されない（_merge_supplier_products はこの投稿の今の組だけ見る） | backend/app/services/tcg_analyzer_svc.py:1794-1801 |
| G6 | Gemini の書き写しを画面で直す API・画面が無い。Gemini 段を取り直すと件の id が全部変わり、人の判断の記録が宛先を失う | backend/app/services/line_analysis_v102_svc.py:394-407、backend/app/services/tcg_extraction_record_svc.py:171 |

### 13-3. SSOT（人の判断の置き場所は1か所）
- 人の判断はすべて public.item_corrections（既存。FK なし・field_name は自由文字列、migrations/20260921_110000_pipeline_tables_public.sql:320-334）に追記で残す。analysis_results は「判断を反映した結果」で、正本ではない。
- v102 のシステム段は、件ごとに item_corrections の**有効な**最新の判断を読み、結果に反映する（G1〜G3）。
- 使う field_name:
  | field_name | 意味 | human_value |
  |---|---|---|
  | product_id（既存） | 商品の決定 | 商品 id（文字列） |
  | condition_review（既存） | 状態の決定 | 既存の JSON（decision・condition_id 等） |
  | review_ack（新） | 「このままで良い」 | JSON `{"v":1,"codes":[理由コード…]}` |
  | v102_lines / v102_price / v102_quantity（新） | Gemini の書き写しの直し | 直した後の値（lines は JSON 配列） |
  | v102_item_added / v102_item_deleted（新） | 件の追加・削除 | 追加後／削除前の件の JSON |
- 判断が**有効**の条件: その判断の corrected_at が、同じ件の最後の書き写しの直し（v102_lines/price/quantity/item_added の corrected_at の最大）より後であること。書き写しを直したら、それより前の商品・状態・確認済みの判断は無効（件の中身が変わったので見直す）。Gemini 段を取り直した件は id が新しくなるので、古い判断は自然に無効。

### 13-4. 便D（人の判断を残す・理由を解く・配信）
1. v102 のシステム段（run_v102_analysis）に「判断の読み込み」を足す:
   - 商品: 有効な最新の product_id の判断があれば、その件の商品をその id に固定してから状態・単位を決める（試作版は商品→箱→状態→単位の順に決めるため、後から上書きでは状態・単位がずれる）。固定は試作版の商品決定（backend/app/services/gemini_raw_copy_v102_product_first.py:470-506 resolve_product_first）に「固定の商品 id」を渡す口を1つ足して行う。固定時は status='matched' と同じ扱いで、pid_basis='MANUAL'。固定が無い件の結果は今と1文字も変わらない（K8 を保つ）。
   - 状態: 有効な最新の condition_review（decision が confirm/correct、選んだ状態が is_active）があれば、その condition_id を使い、理由 condition_unknown・condition_multiple_candidates を外す。condition_basis='MANUAL_CONDITION_REVIEW'。
   - 確認済み: 有効な最新の review_ack の codes にある理由は外す。
2. is_current の付け直し（G5）: 解析の前の組（product_id, condition_id）と後の組の和集合で付け直す。_merge_supplier_products に「追加で付け直す組」を受ける任意の引数を足す（無指定なら今と同じ）。
3. 起動: v102 の件に判断を保存した API（POST /tcg/items/{id}/corrections、状態の確認の保存、便C の保存、確認済みの保存）は、保存後に Celery タスク「その投稿のシステム段をやり直す→is_current を付け直す→配信を予約」を積む。
4. 配信の間引き（G4）: 配信の予約は Redis のキー（SET NX、有効60秒）で1回にまとめ、60秒後に1回だけ run_distribution を起動する（その間の直しはまとめて反映される）。TCG_AUTO_DISTRIBUTE=1 のときだけ。既存の止め装置（未完了の解析・抽出があれば中止）はそのまま。
5. 「確認済み」の API: POST /tcg/items/{id}/review-ack（super_admin、body: source_message_id・codes）。codes は review_reason_codes にあるコードに限る。
6. 対象: v102 の件だけ（prompt_version が `v102:`）。v6 の件の扱いは変えない（本番は今 v102 が0件なので、本番の挙動は便E まで変わらない）。

### 13-5. 便C（Gemini の書き写しを画面で直す）
1. API（super_admin）:
   - GET /tcg/v102/posts?status=needs_review: 投稿単位の理由（extraction_jobs.review_reasons）か、fix_stage='extraction' の理由を持つ件がある v102 の投稿の一覧（仕入元・投稿時刻・理由・件数）。
   - GET /tcg/v102/posts/{job_id}: 原文の行（番号つき）と件（id・gemini_index・source_lines・raw_price・raw_quantity・件の理由）。
   - PUT /tcg/v102/posts/{job_id}/items: 直した後の件の全体（既存の件は id 付き、新しい件は id なし）。サーバーで検査（行番号は 1〜原文の行数の整数・重複なし、価格・数量は文字列で長さ上限、件は1件以上）。変わった件だけその場で更新（id を変えない＝人の判断の宛先を保つ）、追加・削除も行い、すべて item_corrections に記録（13-3）。gemini_index は最小の行番号順に振り直す（件の並びを原文の順に保つ）。保存後は 13-4 の 3 と同じタスクを積む。
2. 画面: 要確認ページに「投稿」タブを追加（Tabs 金型）。一覧は DataTable、行を押すと Modal（xl）で原文（ShadowSourcePane、選んだ件の行範囲を色付け）と件の表（DataTable、セルに TextField 金型：行番号「3,5,7」・価格・数量、削除・追加・保存は Button 金型）。新しい部品・色・生要素・ui-allow を作らない。文言は ja/en。
3. 本番タブの行を押したとき、その件の訂正（既存の ItemComparison・ConditionReviewPanel・ProductMasterDrawer）と「確認済み」ボタンを Drawer 金型で開く（便D の画面）。

### 13-6. 分割（1つずつ: マージ→デプロイ→確認→次）
| PR | 内容 | migration | 本番の挙動 |
|---|---|---|---|
| D1 | 13-4 の 1〜6（backend） | なし | 変化なし（v102 の投稿0件） |
| C1 | 13-5 の 1（backend API） | なし | 変化なし |
| CD2 | 13-5 の 2・3（frontend） | なし | 投稿タブ（v102 の投稿0件の間は空）、本番タブの行から訂正 Drawer |

### 13-7. 受け入れ基準
| # | 基準 | 検証方法 |
|---|---|---|
| D-K1 | 商品を手で決めた v102 の件は、システム段を何度やり直しても同じ商品・pid_basis='MANUAL' のまま、product_not_in_master・product_multiple が付かない | pytest（PostgreSQL） |
| D-K2 | 判断が無い件の結果は判断の読み込みを足す前と同じ（K8） | pytest：保存済み応答で前後一致 |
| D-K3 | 確認済みにした理由はやり直しでも付かない。書き写しを直した後は確認済みが無効になり、理由が戻る | pytest |
| D-K4 | 直した件が同じ仕入元×商品×状態で最新の投稿なら is_current=TRUE で配信の出力に入り、古い投稿なら FALSE で入らない | pytest（fetch_output_rows） |
| D-K5 | 商品を A→B に直すと、A の組で次に新しい投稿の件が is_current=TRUE に戻る | pytest |
| D-K6 | 60秒の間に5回直しても run_distribution の起動は1回 | pytest（Redis をモック） |
| C-K1 | 書き写しの保存で、変わっていない件の id が変わらず、変わった件・追加・削除がすべて item_corrections に残る | pytest |
| C-K2 | 不正な行番号（0・行数超え・重複・整数でない）は 422 で何も書かない | pytest |
| CD-K1 | 投稿タブ・訂正 Drawer が金型だけで作られ、文言が ja/en にある | vitest＋i18n 検査＋UI ガバナンス検査 |

### 13-8. リスクと対処
| リスク | 対処 |
|---|---|
| 試作版ファイル（product_first）は別セッションも直す | D1 の PR 本文に追加した引数を明記。固定なしでは結果不変（D-K2） |
| 配信の起動が増える | 13-4 の 4 で60秒に1回へ間引く |
| 書き写しの直しで古い判断が無効になり、要確認が戻る | 仕様（件の中身が変わったら見直す）。画面で理由が見える |
| v6 の件は直しても配信が自動で走らない | 対象外（便E 後は新しい投稿は v102）。必要なら別便 |

### 13-9. 外部・過去事例
外部事例は使わない（社内の既存の仕組み ADR-158 の is_current と item_corrections の延長）。過去事例: v6 は「product_id の判断があれば再解析を飛ばす」方式（backend/app/services/tcg_analyzer_svc.py:1381-1394）で、判断が同値の確認でも再計算が止まる。本設計は飛ばさずに判断を反映して再計算する。

## 14. 便E（既定を v102 に切替）

### 14-1. 目的
本番の LINE解析エンジンを v6 から v102 に切り替える。新しい LINE 投稿は v102（指示書 raw_copy_v101_f_c）で抽出・解析される。

### 14-2. 変更前後
| 場所 | 変更前 | 変更後 |
|---|---|---|
| docker-compose.yml:218 | `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v6}` | `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v102}` |
| backend/app/services/line_analysis_v102_svc.py:100 get_engine | v6（未設定時） | 変えない（未設定・不明値は v6 の安全側） |

本番の .env には LINE_ANALYSIS_ENGINE が無い（件数 0、recon.md「Opus 確認 2026-10-10」）ため、compose の既定値がそのまま効く。compose の変更だけで切り替わる。本番は自動配信 ON（AUTO_DIST=1）。

### 14-3. PO 判断
備考列 note_ja が空になる件を PO が了承（2026-10-10）: 「このまま切り替えて良い、切り替え後に備考欄の設定は構築する」

### 14-4. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 デプロイ後 celery-worker の LINE_ANALYSIS_ENGINE=v102 | `docker compose exec -T celery-worker printenv LINE_ANALYSIS_ENGINE` |
| K2 切替後の新規抽出ジョブの prompt_version が `v102:` で始まる | extraction_jobs の最新行の prompt_version を読む（読み取り SQL、PO 実行） |
| K3 その投稿の analysis_results が作られ is_current が付く | 同投稿の analysis_results の行と is_current を読む |
| K4 自動配信が起動しシートが更新される | celery-worker ログの auto_distribute result と配信先シートの更新時刻 |
| K5 v6 の件は変わらない | 切替前の v6 の投稿の prompt_version・analysis_results 件数が切替前後で同じ |

### 14-5. 戻し方
既定を v6 に戻す PR。緊急時は PO が本番 .env に `LINE_ANALYSIS_ENGINE=v6` を書き celery-worker を再作成する。

### 14-6. 外部事例
外部事例は使わない。環境変数による版切替は便B（§4）で設計済みの仕組みの既定値を変えるだけで、新しい仕組みを足さない。

### 14-7. 維持の仕組み
| 何を守るか | 仕組み | 担当 |
|---|---|---|
| 未設定時は v6（安全側） | get_engine のテスト（test_line_analysis_v102_svc.py:42-50） | CI |
| compose の既定値 | PR レビュー。compose の既定値を検査するテスト・CI は無い（git grep で docker-compose.yml:218 以外に参照なし） | PR レビュー |
| 費用 | llm_usage_events（purpose='line_extraction'）を切替後に日次確認 | 設計担当 Opus |

---

## 15. 便PQ（v102 の価格・数量を Gemini の写しの数字で補う／数字にできない時は要確認）
設計: Opus（2026-10-10）。PO 承認: 「数字のみに整形することは出来る？」「→対策が必要」「PRマージ、デプロイまで完走させてくれ」。カード: card-PQ.md。根拠: recon.md §8。

### 15-1. 目的
本番の v102 で、Gemini の写しに数字があるのに price_normalized / quantity_normalized が NULL になる件（数量9件・価格4件、うち数量6件は要確認にならず配信）をなくす。補えない件は必ず要確認にして配信から外す。

### 15-2. 変更前後
| 場所 | 変更前 | 変更後 |
|---|---|---|
| backend/app/services/gemini_raw_copy_v101.py:854-874 `_extract_one` | price_normalized / quantity_normalized = resolve_price_quantity の結果そのまま | `if v102:`（:886 付近）で、結果が None のときだけ `_fill_from_copy`（:842）で Gemini の写しの数字を採用。pq が値を持つ時は変えない |
| 同 :828 `_single_number`（新規） | なし | 写しに数字がちょうど1つの時だけ数にする。万・千・億・k を含む／0個／2個以上／小数は None |
| 同 :1181 `_item_reasons` | 数量・価格が NULL でも理由なし | 写しに数字があるのに補いの後も NULL なら `quantity_unresolved` / `price_unresolved` を review に足す |
| 理由コード quantity_unresolved | なし | 定数 :1153、frontend ja/en の reviewReason、整合テスト、表の1行（docs/handoff/v102-prod-switch/data/review_reason_codes/qu_*.sql、seed_20261010_quantity_unresolved.sql） |

補いの採用条件は2つ両方: ①数が1つに決まる ②その数が、その件の行（own_text）に独立した数として現れる（既存の `_quantity_not_in_text(..., v102=True)` と同じ判定を再利用）。補った印の理由コードは足さない。
理由が1つでも付けば line_analysis_v102_svc.py:559 で needs_review=True になり、配信から外れる（tcg_distribution_svc.py:262、既存の流れ）。読み取り時の price_unresolved の付与（tcg_condition_review_svc.py:144）は `SELECT DISTINCT reason` で重複を除くため、保存値に price_unresolved が入っていても二重にならない（:151 の除外条件は price_normalized が非 NULL の時だけ外すので、NULL のままなら残る＝正しい）。

### 15-3. 対象外（理由: 共有経路への波及）
v6・v10.1・shadow・`_price_of`（付け直し）・resolve_price_quantity 本体・_STOCK_START_RE と _mask_product_name の根本修正。いずれも v10.1 や他の経路と共有されており、v102 だけの補いで足りるため触らない。

### 15-4. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 保存値が非 NULL の価格・数量で、値が変わる件 = 0 | 置き換え試験（現行702件、旧・新コードを同じ入力で通し保存値と比較）: 0件 |
| K2 数量 NULL→値 9件前後・価格 NULL→値 4件前後 | 同試験: 数量9件・価格4件（2件は数量と価格の両方） |
| K3 数字があるのに NULL のまま残る件はすべて理由が付く | 同試験: 残る件 0（理由付与そのものは単体テストで確認） |
| K4 価格・数量以外の違い = 0 | 同試験: 旧コード対新コードで product_id・unit・condition・match_status・status・name・ship・理由コードの差 0件 |
| 補い／補えず理由／補わない（写しの数が原文に無い）／v10.1 回帰 | backend/tests/test_gemini_raw_copy_v101.py の test_pq_*・test_single_number |
| 理由コードの SSOT 整合 | backend/tests/test_review_reason_codes_consistency.py |

置き換え試験の限界: dump.json に状態マスタ・直前投稿・人の判断が無いため、それらは空・ダミーで実行した。K4 は旧コードと新コードの差であり、保存値の product_id・unit・condition との比較ではない。価格数量の order は投稿元ごとに旧コードが保存値を最もよく再現する順を選んだ。

### 15-5. 戻し方
この PR を戻す。表に入れた1行は qu_rollback.sql（その1コードだけ戻す）。戻した後は、補われた件の価格・数量が元の NULL に戻り、quantity_unresolved の理由は消える（再解析時）。

### 15-6. 外部事例
外部事例は使わない。新しい仕組みを足さず、既存の検算（_quantity_not_in_text）と既存の理由コードの流れに沿って、v102 の1か所に補いを足すだけのため。

### 15-7. 維持の仕組み
| 何を守るか | 仕組み | 担当 |
|---|---|---|
| 理由コードの表・コード・翻訳の一致 | tests/test_review_reason_codes_consistency.py（quantity_unresolved・price_unresolved を含む） | CI |
| 補い・補えず理由・v10.1 不変 | tests/test_gemini_raw_copy_v101.py の test_pq_*・test_single_number | CI |
