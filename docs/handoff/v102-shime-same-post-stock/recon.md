<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 同じ投稿の〆が在庫行に効かない件（規則13）

**仕事名**: v102-shime-same-post-stock  
**日付**: 2026-10-19  
**対象ADR**: ADR-158（is_current の考え方。今回は ADR を変えない。理由は design.md §9）  
**担当**: Opus（Planner）。コードと本番DBの読み取りは Sonnet に任せ、Opus が生出力と実物を照合した

基準: origin/main 963712e6d（#4519 マージ後）。worktree release/shime-same-post-soldout。

---

## 1. 起きていること（本番DBの読み取り。生出力は /tmp/CC報告ファイル/shime-same-post-20261019/）

投稿 43e6cac8-9c48-46ce-a1f8-f212fbdf4762（仕入元ゆうき、2026-10-18 07:25Z）の原文（5_raw_43e6cac8.out）:

```
30th CELEBRATION カードセット 9種セット（ポケセンダンボール開封済み・検品のため）
10個＠19,000円

〆
```

解析 job 0d3d2a98 は2件に分かれた（3a_yuuki.out）。

| 件 | source_lines | line_start〜end | raw_quantity | raw_price | status | exclusion | 商品 | 状態 | is_current |
|---|---|---|---|---|---|---|---|---|---|
| 0 | [1, 2] | 1〜2 | 10個 | 19,000円 | In Stock | なし | 440301 | 14 | TRUE |
| 1 | [1, 4] | 1〜4 | none | none | Sold out | excluded | 440301 | 14 | TRUE |

- 件0 は配信の条件（下の §2-3）をすべて満たす（2a_examples.out の stock_distributable=True）。在庫表に「10個＠19,000円」が残る。
- 件1 は exclusion があり価格が無いので、要確認に「除外」「価格なし」で出る（前回調査 /tmp/CC報告ファイル/shime-check-20261019/）。これは今の設計どおり。

消してはいけない例 a33d2338-fce4-4c15-b9e3-5d9134b32447（倉田、5_raw_a33d2338.out、3b_kurata.out）:

| 件 | source_lines | 範囲 | raw_quantity | raw_price | status | 商品 | 状態 |
|---|---|---|---|---|---|---|---|
| 0 | [1,2,3,5,6,7] | 1〜7 | none | ¥7,000 | Sold out | 466088 | 14 |
| 1 | [1,2,3,9,10,11] | 1〜11 | 残り約400セット | ¥6,000 | In Stock | 466088 | 14 |

原文は「18日から出荷 セット/¥7,000 完売」「20日から出荷 セット/¥6,000 残り約400セット」。完売は ¥7,000 の分だけで、¥6,000 は在庫。

## 2. file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_analyzer_svc.py:1951` | `_merge_supplier_products`。is_current は（商品, 状態）ごとに最新の job を選び、その job の行を全部 TRUE にする。行の status は見ない |
| `backend/app/services/tcg_analyzer_svc.py:1960` | docstring「同じ投稿の同じペアの行は、どれも TRUE のまま残る」 |
| `backend/app/services/tcg_distribution_svc.py:242` | `_sold_out_filter`。status が sold out の行を配信から外す（行ごと） |
| `backend/app/services/tcg_distribution_svc.py:362` | 配信の WHERE（is_current・needs_review・exclusion・単位・価格）。行ごとの判定で、同じ投稿の他の行は見ない |
| `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1` | 〆の規則の正本は docs/handoff/v102-shime-*/design.md の規則1〜12f と書かれている |
| `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:392` | `decide_soldout_inherit`（規則12）。同じ投稿の他件の状態は「引き継ぎ先から外す」ためだけに使い、在庫行の status は変えない |
| `backend/app/services/line_analysis_v102_svc.py:419` | `line_start = min(lines)`、`line_end = max(lines)`。範囲は件の行の最小〜最大 |
| `backend/app/services/line_analysis_v102_svc.py:606` | `_map_to_rows`。v102 の件と extraction_items の行を位置で対応付ける |
| `backend/app/services/line_analysis_v102_svc.py:1009` | `_write_results`。解析結果を保存する関数 |
| `backend/app/services/line_analysis_v102_svc.py:1036` | 人が直した値（販売状況を含む）を `apply_value_overrides` で base_values に重ねる |
| `backend/app/services/line_analysis_v102_svc.py:1041` | `_buyback_units` の後。ここで全件の base_values（product_id・condition_id・status・exclusion）と row（line_start・line_end・raw_price・raw_quantity）がそろう |
| `backend/app/services/line_analysis_v102_svc.py:1045` | ループ内の `_apply_soldout_targets`。〆に引き継ぎ先があるとき condition を上書きしうる |
| `backend/app/services/line_analysis_v102_svc.py:1220` | 既存の「仕入元が価格を書いているか」の判定（空・none を無しとみなす） |
| `backend/app/services/line_analysis_v102_svc.py:1369` | 解析で読む extraction_items の列（id・gemini_index・source_lines・line_start・line_end・raw_price・raw_quantity） |
| `backend/app/services/v102_human_decisions_svc.py:96` | `ValueOverrides`（status を含む） |
| `backend/app/services/v102_human_decisions_svc.py:524` | `apply_value_overrides`。status を重ねると、状態マスタの効果から exclusion も決める（:550） |
| `backend/app/services/v102_human_decisions_svc.py:554` | `status_available_by_human`。人が在庫あり側に直した件を尊重する既存の例 |
| `backend/app/tasks/tcg_extraction.py:736` | `reanalyze_v102_job`。Gemini を呼ばずに1投稿を解析し直し、is_current も付け直す |
| `backend/tests/test_line_analysis_v102_svc.py:556` | 人の判断を〆の処理が上書きしないことの既存テスト（作法の手本） |

## 3. 影響範囲（本番DBの読み取り、2a_count.out・2a_examples.out・4a_0f12b467.out・4b_0b17dbc1.out）

同じ投稿で、同じ（商品, 状態）の Sold out 行と In Stock 行が両方 is_current=TRUE の組は6組・4投稿。

| 投稿 | 商品 | エンジン | 〆の行に自分の価格 | 〆の範囲が在庫行の範囲を含む | 新しい規則で在庫行を完売にするか |
|---|---|---|---|---|---|
| 43e6cac8（ゆうき） | 440301 | v102 | なし | 含む（1〜4 ⊇ 1〜2） | する |
| a33d2338（倉田） | 466088 | v102 | ¥7,000 | 含まない（1〜7 ⊉ 1〜11） | しない |
| 0f12b467（倉田） | 440552 | v102 | ¥30,000 | 含まない（241〜244 ⊉ 221〜224） | しない |
| 0f12b467（倉田） | 424591 | v102 | ¥2,000 | 含まない（583〜586 ⊉ 588〜591） | しない |
| 0b17dbc1（倉田）2組 | 424591・424592 | 旧 v5 | — | — | 対象外（v102 の経路を通らない） |

## 4. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 〆の行の raw_price・raw_quantity が実データで何か | 3a_yuuki.out | ✅ 文字列 none |
| 2 | 判定に source_lines の包含を使えるか | 3a_yuuki.out | ✅ 使えない。〆の source_lines は [1, 4] で2行目を含まない。line_start〜line_end の範囲で比べる |
| 3 | 範囲で比べて倉田の例を消さないか | 3b_kurata.out・4a_0f12b467.out | ✅ 3組とも〆に価格があり、範囲も含まない |
| 4 | 人が販売状況を直した在庫行を上書きしないか | `backend/app/services/v102_human_decisions_svc.py:554` の作法 | ✅ 設計で除外する（design.md §3） |
| 5 | 1投稿だけ解析し直す手段 | `backend/app/tasks/tcg_extraction.py:736` | ✅ あり |
| 6 | 新しい ADR が要るか | 〆の規則1〜12f はすべて handoff の design.md が正本（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:1`） | ✅ 同じ作法で規則13とする |

**未解決ゼロ確認**: 全て解消済み

## 5. 補足
- 2c（本文に〆があるのに Sold out 行が一つも無い投稿 214件）は、本文が「〆ます！」だけで件が0の投稿を含み、取りこぼしの件数とは読めない。今回の対象外（design.md §2）。
