# 追補2：価格と数量はシステムが決める（新方式 v7）／ルールのない仕入元は試運転しない（2026-09-30）

状態：**設計確定（PO 合意済み・2026-09-30）／Opus 自己審査済み／実装は未着手**
- 親
  - `docs/handoff/gemini-extract-role-split/design.md`
  - `docs/handoff/gemini-extract-role-split/supplier-rules-design.md`
- 根拠
  - `docs/handoff/gemini-extract-role-split/recon.md`（現在地の調査。v7 の書き写し・判定の配線）
  - `docs/handoff/gemini-extract-role-split/supplier-block-evidence.md`
  - 本番の全1,688投稿の機械集計（§2）

## 1. PO の決定（原文・2026-09-30 チャット）
- 「geminiに商品ブロックごとに原文を細分化させる→その中からシステムが仕入元ルールと単位のルールをヒントに解析する」（Opus「その理解で合っています」→ PO「完全に合意」）
- 「まずは この設計で必要なものを把握しながら整理して設計をする、設計まで完了したら記録して、実際に実装をする、その後で照合試験をする、ルールに不足しているものもあるようなので充填してからABテストに移りたい」
- 品質を最優先する（誤判定ゼロ ＞ 精度の向上 ＞ 費用）。

## 2. 事実（file:line・実測）
| # | 事実 | 根拠 |
|---|---|---|
| F1 | 今は Gemini が「どれが価格か・どれが数量か」を欄に分けて書き写し、システムは `_parse_numeric` で数値にするだけ | `backend/app/services/extraction_shadow_svc.py:280-281`、本番 `extraction_prompt_config.raw_copy_extraction` v1 |
| F2 | `_parse_numeric` は数字・`.`・`,` 以外をすべて捨てる。「24万」は 24 になる。「10,000／12,100」は 1000012100 になる（数字がつながる） | `backend/app/services/tcg_analyzer_svc.py:896-916`、実行で確認 |
| F3 | 書き写しの原文照合は raw_price・raw_state・raw_ship の3欄だけで、raw_quantity は照合していない | `backend/app/services/extraction_shadow_svc.py:55` |
| F4 | 単位の辞書は DB の `public.units` と `public.unit_aliases` にある。2026-09-30 に本番を読み取りで確認した結果は、10単位・別名とcanonicalを合わせて45語。Booklet（冊）と MasterCarton があり、Box の別名に「OX」がある。「packs」「CTN」「P」は登録されていない | `backend/app/services/tcg_analyzer_svc.py:91-120`、本番 SELECT（`/tmp/CC報告ファイル/coverage/units.txt`） |
| F10 | 照合試験（1版目）の結果：在庫行26,040行のうち23,814行（91.5%）が決まった。在庫行がある116社のうち、87社が90%以上、29社が90%未満だった | `/tmp/CC報告ファイル/coverage/coverage2.tsv` |
| F11 | 1版目の実装に12件の実例を通した。値を黙って誤る例は0件だった。ただし次の3種類で、必要以上に確認に回っていた（multiple_values または unresolved）<br>(a)「23500円/ 1BOX」（1BOXあたりの価格）を数量の候補に数えた<br>(b) 商品名の中の数（「ARバルク、100枚セット」）を候補に数えた<br>(c) 単位の別名が辞書にない（packs、CTN） | `/tmp/CC報告ファイル/coverage/check3.py` の出力 |
| F5 | 試運転は `supplier_context` の有無に関係なく全ジョブで動く | `backend/app/tasks/tcg_extraction.py:522-537` |
| F6 | `extraction_shadow_results.evidence` は書き込みだけで、読む側が無い | 調べた結果、読み手は0件 |
| F7 | 確認待ち画面は review_items の item を生の文字列のまま表示している（`verify_copied` がそのまま出る） | `frontend/src/pages/super-admin/NeedsReviewListPage.tsx:394-411` |
| F8 | 目印（円・¥・@・在庫・単位）で向きが決まった16,911行を正解として測った結果：「大きいほうが価格」98.7%、「カンマ付きが価格」99.4%、「4桁以上が価格」99.1%。外れた行はすべて、単価が安く数が多い商品 | `/tmp/CC報告ファイル/supplier-posts-all/heuristics.txt` |
| F9 | 目印のない「数字@数字」「数字×数字」は4,227行。仕入元ごとに見ると向きはそろっていた（N&U は2,440行すべて価格@数量、SIG系はすべて数量@価格） | 同上 (d) |

## 3. 役割分担（変更後）
1. Gemini（変更なし）
   - 商品ブロックに区切り、原文のまま書き写す。
   - 書き写した RAW_PRICE と RAW_QUANTITY は、システムにとっては「ヒント」として扱う。
2. システム：書き写しの原文照合。raw_quantity を照合の対象に加える（F3）。
3. システム：価格と数量を決める（新しく作る。§4）
4. システム：検算し、食い違えば人の確認へ回す（新しく作る。§4-5）
5. システム：商品の照合（変更なし）

## 4. 価格・数量の決め方（`resolve_price_quantity`、純粋関数）
置き場所：`backend/app/services/extraction_judgement_svc.py`。DB にも LLM にもアクセスしない。

### 4-1. 入力
- `block`：ブロックの原文（line_start から line_end まで）
- `gemini_price` と `gemini_quantity`：Gemini が書き写した値
- `unit_aliases`：単位の別名。DB の `unit_aliases` と `units.canonical` から作る。コードに直接書かない。
- `order`：仕入元ルールの向き。`"price_first"`、`"quantity_first"`、`None` のどれか。

### 4-2. 対象にする行（値の行）
- ブロックの各行のうち、Gemini の price か quantity の数字（NFKC 後の数字列）を含む行を対象にする。
- どちらも none のときは、basis="none" で終わる。この場合は確認に回さない（完売の行などのため）。

### 4-2b. 商品名を値の対象から外す（F11-b への対処）
- 引数に `gemini_product_name` を加える。Gemini が書き写した RAW_PRODUCT_NAME を渡す。
- NFKC 後、各行で次のように扱う。
  - 行の中に商品名の文字列がそのまま含まれていれば、その部分を同じ長さの空白に置き換える。
  - 空白を除いた行が商品名に丸ごと含まれていれば、その行を対象から外す。
- 商品名が none のときは、何もしない。

### 4-3. 数値の取り出し
- 数値：`\d+(?:[,，]\d{3})*(?:\.\d+)?` を NFKC 後の文字列に当てる。
- 直後に「万」があれば、10,000倍する（例：24万 → 240000）。
- 次の数値は、品番の一部とみなして取り出さない。
  - 直前が英字または `-`（例：OP-17、PSA10、SV11B）
  - 直後が英字で、しかもその英字が単位の別名ではない（例：30th、M6a）
- カンマの位置が3桁ごとでない数値（例：`4,0000`）は、値としては読む。そのうえで理由 `irregular_comma` を付ける。
- 「単位あたりの価格」の表記は、数量として取り出さない（F11-a への対処）。
  - 対象：直前が `/`（空白を挟んでもよい）で、値が 1、直後が単位の別名の数値。
  - 例：`23500円/ 1BOX`、`¥280,000/1ケース`

### 4-4. 目印で決める（basis="marker"）
価格の目印
- 直後に `円` `万円` `万` がある
- 直前に `¥` `￥` がある
- 直前に `Y` があり、その前が英字ではない
- 直前に `単価` `価格` のラベルがある（`：` `:` と空白を挟んでもよい）
- 直前に `@` `＠` があり、同じ行に数量の目印が付いた別の数値がある

数量の目印
- 直後に単位の別名がある（大文字小文字を区別しない。最長一致）
- 直前に `在庫数` `在庫` `残り` `残` `数量` がある（`：` `:` と空白を挟んでもよい）

決め方
1. 値の行全体で、価格の目印が付いた数値が1つ、数量の目印が付いた数値が1つ（別の数値）なら確定。
   - 行をまたいでもよい（例：「■単価：￥27,500」と「■在庫数：17」）。
2. 同じ行の中で、片方だけに目印があり、目印の無い数値がもう1つだけあるなら、その目印の無い数値を残りの側とする。
   - 例：`27,500×18BOX` → 数量18が目印付き、27,500が価格
   - 例：`15BOX：19,500`
   - 目印の無い数値を行をまたいで補うことはしない。商品名の中の数字を取り込まないため。

### 4-5. 仕入元ルールの向きで決める（basis="rule"）
- 対象：目印のない `数値[@＠×xX]数値` の行
- `order` が price_first なら左が価格、quantity_first なら左が数量とする。
- `order` が None なら決めない。basis="none" とし、理由 `no_order_rule` を付けて確認に回す。

### 4-6. 検算（食い違えば needs_review=true、理由を記録）
| 理由 | 条件 |
|---|---|
| `multiple_values` | 価格か数量の候補が2つ以上ある（RAW_MULTI にも該当するもの）。値は確定させず None にする（F2 の「数字がつながる」問題を防ぐ） |
| `gemini_disagrees` | システムが決めた価格・数量の数字列と、Gemini が書き写した数字列が一致しない |
| `rule_vs_shape` | basis が rule のときだけ使う。「4桁以上が価格」と「カンマ付きが価格」のどちらかが、ルールの向きと逆になる。basis が marker のときは使わない（F8：外れは、目印のある安い単価の行に限られるため） |
| `irregular_comma` | 4-3 のとおり |
| `unresolved` | Gemini は値を書き写しているのに、システムが決められない |

### 4-7. 出力
- `price_normalized` と `quantity_normalized` は、この関数の結果に置き換える。`_parse_numeric` は使わない。
- `evidence` に `{"price_qty": {"basis": …, "reasons": […], "price_line": n, "quantity_line": n}}` を加える。DB の変更は無い（F6）。
- review_items に `{"item": "price_qty", "reason": "理由をカンマ区切り", "candidates": []}` を加える。

## 5. 仕入元ルールの向き（order）の読み方
- `extraction_order_pattern` が JSON 配列なら、`"price"` と `"quantity"` のどちらが先に出るかで決める。
- JSON 配列でないとき（`price_at_qty` などの旧い略語）は None とする。旧い略語の書き換えは、ルールを埋める作業で行う（supplier-rules-design.md §5-2）。

## 6. ルールのない仕入元は試運転しない
- 判定の関数：`has_required_supplier_rule(supplier_context)`。price_format、qty_format、order_pattern の3つが、どれも空白を除いて空でなければ True。
- 置き場所：`backend/app/services/extraction_shadow_svc.py`
- 呼び出し元：`backend/app/tasks/tcg_extraction.py:522-537`。False のときは run_shadow_for_job を呼ばず、`logger.info("[tcg_extraction] shadow skipped: no supplier rule supplier_id=%s ej=%s")` を出す。
- 旧方式（本番）は変えない。

## 7. 画面（確認待ち）
- 「止まった項目」の列で、item を i18n の表示名に変える。
  - キー：`shadowReview.itemLabel.product`、`.verify_copied`、`.price_qty`。キーが無いときは生の文字列を出す。
- `price_qty` の理由コードも i18n の表示名にする。
  - キー：`shadowReview.priceQtyReason.<code>`
- ja.json と en.json は同じキーにする（ADR-027）。UI の部品は既存の DataTable をそのまま使い、新しい部品は作らない（ADR-144）。

## 8. 変更するファイル（全部）と、触らない範囲
| 種別 | ファイル |
|---|---|
| 変更 | `backend/app/services/extraction_judgement_svc.py`（resolve_price_quantity と order の読み取りを追加） |
| 変更 | `backend/app/services/extraction_shadow_svc.py`（_judge_block で使う、_VERIFY_FIELDS に raw_quantity を追加、has_required_supplier_rule、unit_aliases を渡す） |
| 変更 | `backend/app/tasks/tcg_extraction.py`（試運転の前の判定） |
| 変更 | `frontend/src/pages/super-admin/NeedsReviewListPage.tsx`、`frontend/src/locales/ja.json`、`frontend/src/locales/en.json` |
| 追加 | `backend/tests/test_extraction_judgement_svc.py` と `backend/tests/test_extraction_shadow_svc.py` に試験を追加 |
| 触らない | migration、deploy.yml、本番の scripts、v6 の経路、Gemini の指示文（DB）、`_parse_numeric`（v6 で使っているため） |

- DB の構造は変わらない。この PR 自体は本番の動きを変えない。試運転は停止中（EXTRACTION_SHADOW_ENABLED=0）のため。

## 9. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 原文の実例で、価格・数量・根拠の区分が期待どおりになる | 単体試験（§10 の実例をすべて入れる） |
| 「10,000／12,100」が 1000012100 にならない | 単体試験で multiple_values になり、値が None になる |
| 「24万」が 240000 になる | 単体試験 |
| ルールのない仕入元では試運転が呼ばれない | 単体試験（3欄が空の context で run_shadow_for_job が呼ばれない） |
| 旧方式に影響がない | 既存の v6 の試験がすべて緑 |
| 画面の表示名 | i18n のキーが ja と en でそろっている（CI）。表示は Evaluator が確認する |

## 10. 試験に入れる実例（原文の読み取り記録から）
| 行 | order | 期待する価格 / 数量 / 根拠 |
|---|---|---|
| `27,500×18BOX` | None | 27500 / 18 / marker |
| `40個＠27500円` | None | 27500 / 40 / marker |
| `在庫50/13500円` | None | 13500 / 50 / marker |
| `@19,000円/在庫15※潰れ破れなどあり` | None | 19000 / 15 / marker |
| `15BOX：19,500` | None | 19500 / 15 / marker |
| `■単価（税込）：￥27,500` ＋ `■在庫数：17`（2行） | None | 27500 / 17 / marker |
| `ボックス/¥25,000` ＋ `残り200`（2行） | None | 25000 / 200 / marker |
| `10900@152` | price_first | 10900 / 152 / rule |
| `ストームエメラルダ 100@11300` | quantity_first | 11300 / 100 / rule |
| `400＠518` | price_first | 400 / 518 / rule。rule_vs_shape は付かない（両方3桁で、カンマも無い） |
| `24万　在庫20` | None | 240000 / 20 / marker |
| `30円×3,000枚` | None | 30 / 3000 / marker（検算しない） |
| `¥4,0000/冊` ＋ `15冊` | None | 40000 / なし / 理由 irregular_comma（冊は単位にないため） |
| `@150,000円/在庫2` ＋ `@12,100円/在庫48` | None | None / None / multiple_values |
| `10900@152` | None | None / None / no_order_rule |
| `OP-17` ＋ `12,000×11BOX` | None | 12000 / 11 / marker（OP-17 の 17 は取り出さない） |
| `23500円/ 1BOX` ＋ `60点` | None | 23500 / 60 / marker（1BOX は単位あたりの表記として外す） |
| `¥280,000/1ケース` ＋ `5カートン` | None | 280000 / 5 / marker |
| `ARバルク、100枚セット` ＋ `@13000円 在庫1`（商品名は `ARバルク、100枚セット`） | None | 13000 / 1 / marker（理由なし） |
| `●アビスアイ　¥8,500　在庫38個`（商品名は `アビスアイ`） | None | 8500 / 38 / marker |
| `ストームエメラルダ 100@11300`（商品名は `ストームエメラルダ`） | quantity_first | 11300 / 100 / rule |
| `500packs/330円（未サーチ）` | None | 330 / なし / unresolved（packs は辞書に無い。辞書の補充で直す） |

- 試験で使う unit_aliases は、本番から読み取った45語（F4）と同じものにする。

## 11. 照合試験（実装の後に行う。本番は変えない）
- 試験の台：scratchpad の Python。実装した resolve_price_quantity をそのまま import して使う。
- 入力：`/tmp/CC報告ファイル/supplier-posts-all/` の全1,688投稿
- 数えるもの（仕入元ごと）
  - 在庫行（数字があり、目印か数字の組を含み、送料などの定型文の語を含まない行）の数
  - そのうち marker で決まった数、rule で決まった数、決まらなかった数
- 合格：115社それぞれで、決まった行の割合が 90%以上
- 90%に届かない仕入元は、原文を Opus が読み、不足を洗い出す。不足の例は次のとおり。
  - ルールの向きがない
  - 単位の別名がない（冊など）
  - 書き方の揺れ

## 12. そのあと（別便）
1. ルールの不足分を埋める（本番データの変更）
   - 対象
     - 115社の extraction_* の登録
     - 既存10社の order_pattern を JSON 配列に書き換える
     - 単位の別名の追加（冊・P など。照合試験の結果で決める）
   - 手順：対象の行と SQL を PO に見せて合意を得る → DRY-RUN → 実行
2. 試運転の再開（#3864 を戻す PR）→ A/B 比較（合格ラインは PO が決める）

## 12-2. 外部・過去事例の参照と我々への応用
- 過去事例（社内）
  - v6 は、Gemini に価格と数量の意味づけまで任せている。その結果を `_parse_numeric` で数値にしているため、「24万」を 24、「10,000／12,100」を連結した数値にしてしまう（F2）。この失敗が、意味づけをシステムに移す直接の根拠になっている。
  - 目印による判定の当たり具合は、全1,688投稿で実測した（F8・F10）。
- 外部事例
  - 今回の対象は、自社の仕入元の原文だけで成否を測れる「決定的な規則による解析」である。そのため、外部事例は使わない。
  - LLM で書き写し、規則で意味づけする構成（ハイブリッド）の外部事例の調査は、PO の構想（`project_line_message_type_routing_idea`）に着手するときに行う。

## 維持の仕組み
- 守り手: 設計担当（Opus）が判定の規則と試験の実例を管理する。Sonnet が試験を維持する。単位の別名は、単位マスタ画面（既存）で管理する。
- 目印の語は `backend/app/services/extraction_judgement_svc.py` の定数1か所だけに置く。単位の語は DB（`public.unit_aliases`）だけに置く。
- 試運転の確認待ちで `price_qty` の理由を集計し、多い理由から規則、または単位の辞書を直していく。

## 13. 自己審査（同じ AI による自己審査）
- 判定：**APPROVE（実装に進んでよい）**
- 確認したこと
  - SSOT：単位は DB から読む。仕入元ルールは suppliers から読む。結果は既存の列（evidence・review_items）に書く。表は増やさない。
  - 配線：呼び出し元とデータの流れを file:line で確認した（F1〜F7）。
  - 危険な変更：migration、deploy.yml、本番の scripts には触れない。試運転は停止中なので、本番の動きは変わらない。
  - 推測：目印の語はコード内の定数にする（1か所だけ）。単位の語は DB から読む。
- 残るリスク
  - 本番の unit_aliases の中身は【未確認】（F4）。照合試験の前に、読み取りで確かめる。
  - 1つのブロックに複数の値がある仕入元（カートンと BOX を1つのブロックに書く社）は、確認待ちが増える。細かく分けるのは次の改善として記録しておく。
