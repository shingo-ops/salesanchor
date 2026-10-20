---
mode: handoff
---
# design: 単位が「個」・無記入の箱系の行は、値段で Box／Case／Pack を決める（v102）

> この文書は何か：仕入元が「箱」「カートン」と書かずに値段だけ書いた商品を、値段の大きさから箱・カートン・パックのどれかに決める作り方です。

親: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)

状態: **方針は PO が決めた**（2026-10-21）。起案は 2026-10-21、Opus。審査は下の「審査」にある。
- 現状の調べは [recon.md](./recon.md)（基準 origin/main `9c7275ea0`）
- 決定の記録は [ADR-1036](../../adr/ADR-1036-price-decides-unit.md)。ADR-1035 What 2（状態が語で決まったときは状態の単位を優先）の例外にあたる。
- 試算の生出力・原文つきの表は社外秘フォルダ（`~/CC報告ファイル-keep/needs-review-zero/price-unit-recon/` と同 `v2/`・`v3/`・`v4/`・`v5/`、棚卸しは `~/CC報告ファイル-keep/needs-review-zero/inventory/`）。この文書には件数・商品 id・状態コードだけを書く。

**この設計で承認する範囲は便1・便2 だけ**（①買取の物差し）。便3（③自社前日と、その前提の `unit_basis` の保存）・便4（状態の語の穴）・②他社は、それぞれ別の設計で file:line まで書いてから承認を取る。

## 目的（PO の言葉、2026-10-21）

> 単位も箱で区分も箱系だし状態がdamageだからdamaged sealed boxになるでしょ？そんな簡単な仕組みがなぜ出来ない？

> ダメージ・難あり・キズあり…念のため要確認に回します→要確認に回すのではなく3に進める。キズありまでは絞り込めたので3で単位を確定させる。

> 対象は単位も状態も書いていない行だけ→2.で状態が確定したパターン(キズあり、Opened)等の場合も3を適用させる

> パックは決めません→パックも確定させる

> 他社の販売価格は参考になるので採用する（略）状態の記載がない場合はデフォルト(Case,Sealed box,Unsearched pack,Searched packのどれか)、単位は価格から読み解く

> 買取→他社価格→自社前日価格の順に決まらなければ3段階で照合すればどれかで当たるはず

決まる順（PO の 1〜3）:
1. 単位の語が書いてあれば、その単位（今と同じ）。
2. 単位が「個」・無記入なら、状態の語で状態の**種類**（ダメージ・開封・サーチ済・シュリンクなし・既定）を決める。
3. Box／Case／Pack は値段で決める。物差しは ①買取 → ②他社の販売価格 → ③自社の前日までの価格 の順。

使う人から見て変わること（便1・便2）:
- 「エーフィ・ブラッキー（ダメージ有）@17,400」のような行が、要確認に回らず Damaged sealed box・Box で並ぶ（値段が箱の買取と同じ帯なので）。
- 「サーチ済 @160」のように箱の状態の語が当たっても値段が箱の 1/50 の行は、Searched pack・Pack になる。
- 値段でも決まらない行は、今と同じ決め方（商品の区分の既定）のまま。新しく要確認には回さない。

## KGI と KPI

KGI（PO が ADR-1035 の便を始めるときに決めた。ADR-1035 の本文には書かれていないので、ここに書く）: v102 で生きている投稿の要確認タブを 0 件にし、同じ理由で再発させない。

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| G1 | 「状態の別候補」の要確認が、値段で単位が決まる行で外れる | 便2 の置き換え試験と反映後の再解析で、今 `condition_multiple_candidates` が付いている行のうち**値段で単位と状態が決まった行**を数え、反映後に理由が残る行を数える。決まらなかった行（比が帯の間・B の「決めない」の組・種類が 2 つ以上・単品語の印・対象外の区分）は理由ごとに件数だけ記録する。基準: 棚卸しの D（社外秘 `inventory/proposal.md`、2026-10-21）で「ダメージ・凹み」の 10 行は状態・単位とも正しいのに要確認だった | 値段で決まった行で理由が残る行 0 |
| G2 | 値段で決めて新しく生まれる誤り | 置き換え試験で変わる行を全件、Opus が原文で判定 | 0 |
| G3 | 要確認タブで新しく増える行 | `tab_true.sql` の数え方で反映の前後 | 0 |
| G4 | 同じ投稿を日を変えて再解析しても、物差しの値が変わらない（便1） | テストで「解析した時刻」を変えても中央値が同じ | 同じ |

## 対象と対象外

- 対象: v102 の保存処理（`backend/app/services/line_analysis_v102_svc.py:1115` の `_write_results` の中、便BB の位置＝`backend/app/services/line_analysis_v102_svc.py:1147`）。商品が特定済み・価格あり・商品の区分が箱系で、**価格行に単位の語が無い（「個」を含む）**行。状態の語の有無は問わない（PO の 2.）。
- 対象外（今のまま）:
  - 単位の語がある行（PO の 1.）。値段とのずれは今の便UP（`unit_price_mismatch`）が要確認にする。
  - まとめ売り（ADR-1027）・バルク・セット系・サプライ系・ブックレット系・プロモパック系・シングル系・鑑定品。
  - 人が単位・状態・価格を直した行、〆（excluded）の行。
  - 単品語の印（`単品語あり・要確認(…),`）が付いた行。今の便BB と同じく外す（`backend/app/services/v102_buyback_unit_svc.py:128`）。単品かもしれない行を箱の値段で決めないため。
  - ②他社の販売価格・③自社前日: 別の設計（上の「承認する範囲」）。

## 決め方（変更後）

### A. 物差しと帯（比 r ＝ 行の価格 ÷ 物差し）
| 段 | 物差し | Box | Case | Pack | この設計 |
|---|---|---|---|---|---|
| ①買取 | 同じ商品の買取 BOX（と BOX_SHRINK）の中央値。**その行の投稿日時より前**の記録で、店ごとにその時点で最新の値、30 日以内 | 0.5 ≤ r < 2 | r ≥ 6 | r ≤ 0.2 | 便1・便2 |
| ②他社 | 未決 | — | — | — | 別設計（PO が店を決めた後） |
| ③自社前日 | 同じ商品の v102 行のうち単位の語で確定した行だけの単位ごとの中央値（別投稿 3 件以上・仕入元をまたぐ）。帯は「各単位の中央値に対して 0.5 ≤ r < 2 に入る単位がちょうど 1 つ」で、①の帯とは別の決め方 | — | — | — | 別設計（便3） |

- ①で決まらなければ、便3 ができるまでは今の決め方のまま。
- 帯の数字は既存の設定（`tcg_distribution_settings` の `unit_buyback_box_min`=0.5・`box_max`=2・`case_min`=6）を使い、Pack の上限 `unit_buyback_pack_max`=0.2 を足す。日数 `unit_buyback_max_age_days` は 7 → 30（試算で 7 日より正解 +8・外れ ±0）。
- 試算では Pack の帯を「1 箱のパック数 n で割った値の 0.4〜1.6 倍」にする案（ii）も比べた。正解が 9 件減り外れは変わらない（社外秘 `v2/sim_v2.txt`）ので、単純な (i) r ≤ 0.2 を採る。

### B. 状態の決め方（単位が値段で決まったとき）
状態の語が当たった「種類」を、値段で決まった単位の群の状態に写す。

| 状態の種類（今当たる状態） | Box | Case | Pack |
|---|---|---|---|
| 既定（語なし。語で決まった CN0003・CN0001・CN0007 も同じ） | CN0003 Sealed box | CN0001 Case | CN0007 Unsearched pack |
| ダメージ系（CN0004／CN0002 の語） | CN0004 Damaged sealed box | CN0002 Damaged case | 決めない（今のまま） |
| 開封（CN0006 Opened box／CN0009 Opened case） | CN0006 | CN0009 | 決めない（今のまま） |
| サーチ済（CN20261008072213 Searched box／CN0010 Searched pack） | CN20261008072213 | 決めない（今のまま） | CN0010 Searched pack |
| シュリンクなし（CN0005） | CN0005 | 決めない（今のまま） | 決めない（今のまま） |

- サーチ済の語（Searched box）が当たり、値段が Pack の帯の行は Searched pack・Pack にする。「サーチ済」は箱でもパックでも使う語で、PO の方針（パックも確定させる・状態の種類を写す）の範囲。試算では 4 行（120〜680 円）で、4 行とも原文はパック（今の Searched box・Box が誤り）。
- 「決めない（今のまま）」の組は、値段と状態の語が食い違っている。今の決め方を残し、便UP の検査に任せる。試算では状態が語で決まった 474 行で、この組は 0 件（社外秘 `v2/state_cross.txt`。食い違い 4 件はすべて サーチ済×Pack で、表の対象）。
- 「未開封」「未サーチ」のように語で CN0003・CN0001・CN0007 に決まった行は「既定」と同じ種類にする。どれも各群の「手を付けていない」状態で、語が無い既定と意味が同じため（例: 未開封 @箱の 1/50 → Unsearched pack・Pack）。
- **別の区分の状態の語も見る。** 箱系で解いた行に、箱以外の区分の状態の語（例: Opened case の「テープカット」、`backend/app/services/gemini_raw_copy_v102_product_first.py:653-665` の `_other_kubun_hits`）が当たると、状態は既定の Sealed box のまま `condition_multiple_candidates` が付き、当たった code は product_first の戻り値 `review_extra`（`backend/app/services/gemini_raw_copy_v102_product_first.py:638`・`:760`）に入り、件を組み立てるとき件の `review` 一覧へ `{"line": ..., "kind": "condition_multiple_candidates", "codes": [...]}` の形で混ぜ込まれる（`backend/app/services/gemini_raw_copy_v101.py:920`。件に `review_extra` の key は無い: `backend/app/services/gemini_raw_copy_v101.py:945-967`）。`apply_buyback_units` では `item["review"]` の中の `kind == "condition_multiple_candidates"` の要素の `codes` を読む。`review_reasons` に `condition_multiple_candidates` があるのに codes が 1 つも取れない行は何もしない（理由も外さない）。種類は次のように決める。
  - 今の状態から決めた種類（上の表の行）と、`codes` の各 code の種類（同じ表で引く）を集める。今の状態の種類が「既定」（語なしの既定だけでなく、語で決まった CN0003・CN0001・CN0007 も含む。上の表の「既定」行と同じ定義）で `codes` がある行は、既定を数えず `codes` の種類だけを使う（例: 「未開封 テープカット」→ 今 CN0003・codes [CN0009] → 種類は開封の 1 つ）。
  - 集めた種類がちょうど 1 つならその種類で写す（例: 「テープカット」×Case の帯 → CN0009 Opened case、×Box の帯 → CN0006 Opened box）。2 つ以上、または表に無い code があれば何もしない（理由も外さない）。
  - 試算の状態×単位の照合（474 行）は R1〜R3 の行だけで、この形の行は数えていない【未確認】。K2 の全件判定で見る。
- 対応は表（コードの定数）で持つ。状態マスタに行が増えても自動では広げない（足すときはこの表と ADR-1036 を直す）。

### C. 要確認の扱い
- 値段で単位が決まった行は、`unit_unknown`・`condition_unknown`・`condition_multiple_candidates`（箱と箱以外の区分に語が当たった件）を外す。単位・状態の両方が値段の帯で 1 つに決まっているため。
- **値段で決まった単位・状態が今の値と同じ行でも、外す理由が付いていれば外す。** PO の主例「ダメージ有 @17,400」は今すでに Damaged sealed box・Box で、`condition_multiple_candidates` だけが付いている。今の便BB は値が同じなら何もしない（`backend/app/services/v102_buyback_unit_svc.py:221-222`）ので、この形を変えないと主例の要確認が外れない。
- 値段で決まらない行は、今の決め方・今の要確認の理由をそのまま残す（新しい理由は付けない）。
  - 理由: 語なし 989 行から無作為に選んだ 60 行で、決まらない 15 行は 14 行が今の決め方で正しく、1 行は原文でも判断できない（下の「証拠」）。新しく要確認に回すとタブが増え、KGI に反する。

### D. 記録（basis）
| 行 | 値（単位・状態）が変わる | 値は同じで、理由だけ外す | 値も理由も変わらない |
|---|---|---|---|
| 状態が語で決まった行（`condition_decided_by_word(basis)` が真。R1〜R3 のほか R4a の語・`R3:MEMO:`・`EMPTY_BOX:explicit` を含む） | 状態は B の表の code。basis は今の basis の後ろに `|PRICE:①r=<比>` を足す（先頭は変えない） | basis の後ろに `|PRICE:①r=<比>` を足す | 何もしない（今と同じ） |
| 語なしの行（同じ判定が偽） | 今の便BB と同じ `BUYBACK:<状態> r=<比>` | basis は変えない（理由だけ外す） | 何もしない（今と同じ） |

- 状態の basis の**先頭の規則記号（R2: など）は変えない**。〆の規則 11b が先頭で「語で決まったか」を見ているため（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:38-53`）。
- 語なしで値が同じ行の basis を変えないのは、品質の集計が basis の**末尾**で「既定で決まった行」を数えているため（`backend/app/services/tcg_supplier_quality_svc.py:17-18` の `CONDITION_FALLBACK_PATTERN` は `(R4:単位既定…|R5:パック既定)$`）。語で決まった行（R1〜R3）はもともとこの式に当たらないので、後ろに `|PRICE:` を足しても集計は変わらない。便BB の設計の「値が変わらない件では basis を書き換えない」は、語なしの行で守られる。
- 100 字で切るのは今と同じ（試算で追記後に 100 字を超える行 0、最大 53 字）。
- `unit_basis` はこの設計では扱わない（v102 は保存していない。便3 の別設計で保存の形を決める）。

## コードの変え方（file:line は origin/main `9c7275ea0`）

### 便1（時点）
- `backend/app/services/line_analysis_v102_svc.py:1458-1468` の `_POSTED_AT_SQL`／`load_posted_date` の隣に、日時のまま返す `load_posted_at(session, extraction_job_id)` を足す（同じ SQL を使う。`source_messages.line_posted_at`）。
- `backend/app/services/line_analysis_v102_svc.py:962` の `_buyback_units` の中で、対象がある（`backend/app/services/line_analysis_v102_svc.py:966` の判定が真）ときだけ、SAVEPOINT（`backend/app/services/line_analysis_v102_svc.py:969` の `session.begin_nested()`）の**中で** `load_posted_at` を 1 回呼び（失敗しても保存全体の取引を壊さない。今の except で「この投稿では決めない」になる）、`apply_buyback_units`（`backend/app/services/v102_buyback_unit_svc.py:194`）に `posted_at` を渡す。`posted_at` が None なら何もしない（今の values のまま）。reader で直近 30 日の 2525 job を数え、`line_posted_at` が NULL の job は 0（社外秘 `v5/null_posted.out`）。
- `backend/app/services/v102_buyback_unit_svc.py:155` の `load_medians` に `posted_at` を足し、`_MEDIAN_SQL`（`backend/app/services/v102_buyback_unit_svc.py:54-65`）を次の形にする。社外秘 `v3/sql/prod_form_median.sql` の形で、1573 行すべて試算と一致を確かめ済み。
  - 変更前: `JOIN LATERAL (… WHERE l.shop_product_id = sp.id ORDER BY l.fetched_at DESC, l.id DESC LIMIT 1)` と `AND sp.last_seen_at >= now() - make_interval(days => :days)`
  - 変更後: LATERAL の中に `AND l.fetched_at <= :posted_at AND l.fetched_at >= :posted_at - make_interval(days => :days)` を足し、`sp.last_seen_at` の条件を消す。
- 引数: `apply_buyback_units(..., posted_at)` と `load_medians(session, product_ids, max_age_days, posted_at)` の `posted_at` は**必須**（既定値なし。呼び忘れをテストで落とすため）。
- 直す既存テスト（壊れるので合わせる）:
  - `backend/tests/test_v102_value_overrides.py:204-209` `test_buyback_units_exclude_items_with_a_human_unit_or_price` の `fake_apply` の引数。
  - `backend/tests/test_v102_buyback_unit.py:185-188` `test_median_sql_keeps_the_agreed_conditions`: `sp.last_seen_at >=` の確認を、`l.fetched_at <= :posted_at` と `:posted_at - make_interval(days => :days)` の確認に替える。
  - `backend/tests/test_v102_buyback_unit.py:161-168`: SQL に渡す値の dict に `posted_at` を足す。
  - `backend/tests/test_v102_buyback_unit.py:71-72` の `_apply`・:158・:173: `posted_at` を渡す。
  - `backend/tests/test_v102_buyback_unit.py:203-212` の `_WriteSession`／`_Session.execute`: `_POSTED_AT_SQL` に投稿日時を返すようにし、:238・:249 の `_write_results` の試験が今どおり通るようにする。
- 足すテスト（`backend/tests/test_v102_buyback_unit.py`）: 投稿日時より後の値・31 日前の値を使わない、`posted_at` が None なら何もしない、`load_posted_at` が失敗したらこの投稿では決めない。
- 設定: 記録 SQL（ADR-1007）で `unit_buyback_max_age_days` を 7 → 30 にし、`note` 列を「買取価格による単位・状態の判定: 行の投稿日時より前の、この日数以内の買取の値だけを使う」に直す。ファイルは前例（`docs/handoff/v102-buyback-unit/data/`）と同じ形で `docs/handoff/price-unit-decision/data/bin1/{precheck,dryrun,commit,rollback,verify}.sql`。コードを先に反映し、その後に COMMIT する。
- 効き目: 今は再解析した時刻（now()）で物差しが変わり、同じ投稿でも再解析の日で結果が動く。変更後は投稿の時点で決まる。
- 触らない: 対象（`is_candidate`）・帯・状態・basis・`_write_results` の順序。

### 便2（対象を広げる・Pack・状態の写し・理由の外し方）
- 別名表: `_buyback_units`（`backend/app/services/line_analysis_v102_svc.py:962`）に引数 `unit_alias_to_info` を足し、`_write_results` から `masters.get("unit_alias_to_info") or {}` を渡す（`backend/app/services/line_analysis_v102_svc.py:1134` と同じ書き方。素の `_MASTERS` のテストを壊さない）（`backend/app/services/line_analysis_v102_svc.py:222-225` で作り、`backend/app/services/line_analysis_v102_svc.py:1134` で既に使っている）。`_buyback_units` の中の対象の判定（`backend/app/services/line_analysis_v102_svc.py:966`）と `apply_buyback_units` の両方に渡す。
- 対象 `is_candidate`（`backend/app/services/v102_buyback_unit_svc.py:134-144`）に引数 `unit_alias_to_info` を足し、今の条件 `has_no_unit_and_condition_word(item)`（`backend/app/services/v102_buyback_unit_svc.py:118-131`）に、次を **or** で足す。今の対象は今のまま残る。
  - 商品の分類が箱系（`item["product_category"] == PRODUCT_KUBUN_BOX`、`backend/app/services/gemini_raw_copy_v102_product_first.py:48`）**かつ** 単品語の印が無い（`condition_basis` が `_FLAG_NOTE_PREFIX` で始まらない）**かつ** 単位の語で Box／Case／Pack が決まっていない。
  - 「決まっていない」= `unit_basis["alias"]` が None、または `resolve_unit_v2(alias, unit_alias_to_info)[1]`（書かれた語の単位の区分）が `BOX_RECHECK_UNIT_KUBUNS`（`backend/app/services/gemini_raw_copy_v102_product_first.py:65-67`: 空・不明・条件つき・複合・数量専用）に入る。「個」は条件つき（UN0008）なのでここに入る。今の `alias is None` だけでは「個」の行を取りこぼす（`find_unit_product_first` `backend/app/services/gemini_raw_copy_v102_product_first.py:511-538` は「個」で alias="個" を残す）。
- 判定 `decide_code`（`backend/app/services/v102_buyback_unit_svc.py:106-115`）: 返り値を「単位の種類（Box／Case／Pack）と r」に変え、`r <= pack_max` で Pack を返す。Pack は箱系の分類の行だけ（今の対象の行は Box／Case だけ。今と同じ）。
- 引数 `unit_alias_to_info` は `is_candidate`・`apply_buyback_units`・`_buyback_units` とも**必須**（既定値なし）。
- 状態の種類: `load_targets`（`backend/app/services/v102_buyback_unit_svc.py:164-172`）で B の表の全 code（CN0001〜CN0007・CN0009・CN0010・CN20261008072213）を引き、`condition_id → code` の逆引きも作る。行の今の `condition_id` からこの逆引きで code を出し、B の表の行（種類）を決める。種類は次の順で決める。(1) `condition_decided_by_word(basis)` が False の行は、今の状態（Error・FLAG_SINGLE を含む。`backend/app/services/gemini_raw_copy_v102_product_first.py:579-586`、`backend/tests/test_v102_buyback_unit.py:63-68`・`:236-240`）に関係なく「既定」。(2) True の行は逆引きで code を出し、CN0003・CN0001・CN0007 なら「既定」（B の表と同じ定義）、それ以外は B の表で引く。`condition_decided_by_word` は (1) と D 表の basis の書き分けに使い、語で決まった行の中の「既定」判定には使わない。`item["review"]` の中の `kind == "condition_multiple_candidates"` の要素の `codes` も B の「別の区分の状態の語も見る」どおりに使う。(2) で逆引きに無い状態（AR confirmed pack・空箱等）は何もしない。1 つでも引けなければ便全体で何もしない（今と同じ）。
- 写し先: B の表を定数（種類 × 単位 → 状態 code）で持つ。「決めない」の組は何もしない。
- 理由: `REASONS_DROPPED_WHEN_DECIDED`（`backend/app/services/v102_buyback_unit_svc.py:43`）に `condition_multiple_candidates` を足す。
- 同じ値の扱い（`backend/app/services/v102_buyback_unit_svc.py:221-222`）: 値が同じでも、`review_reasons` に外す理由があれば、理由を外した values にする（D の表の「値は同じで、理由だけ外す」）。外す理由が無ければ今どおり何もしない。
- basis（`with_decision` `backend/app/services/v102_buyback_unit_svc.py:180-191` の :186）: D の表どおり。
- 設定: `parse_settings`（`backend/app/services/v102_buyback_unit_svc.py:90-103`）に `unit_buyback_pack_max` を足す（キーが無いときは Pack を決めない＝今と同じ。あって `0 < pack_max < box_min` でなければ設定全体を不正として何もしない）。記録 SQL は `docs/handoff/price-unit-decision/data/bin2/{precheck,dryrun,commit,rollback,verify}.sql`（`unit_buyback_pack_max`=0.2、note「買取価格による単位・状態の判定: 比がこの値以下ならパック」の 1 行を足す）。
- 直す既存テスト: `backend/tests/test_v102_value_overrides.py:204-212` の `fake_apply`・`is_buyback_candidate` の差し替えの引数、`backend/tests/test_v102_buyback_unit.py:263-268`（`is_candidate` を引数 2 つで呼んでいる）、`backend/tests/test_v102_buyback_unit.py:191-197`（設定の key が 4 つの前提。`unit_buyback_pack_max` は無くてもよい key として足す）、`backend/tests/test_gemini_raw_copy_v102_unit_state_set.py:185`・`:189`（`bb.is_candidate(item, values)` を引数 2 つで呼んでいる）、`backend/tests/test_v102_value_overrides.py:220`（`svc._buyback_units(...)` の呼び出し）、便1 で直した `_apply` などの呼び出しに `unit_alias_to_info` を足す。
- 足すテスト: `backend/tests/test_v102_buyback_unit.py` に K1 の組。
- 触らない: `_write_results` の順序（人の直し `backend/app/services/line_analysis_v102_svc.py:1143` → 便BB `backend/app/services/line_analysis_v102_svc.py:1147` → 規則13 → 便UP → `_apply_decisions`）、便UP、規則13、〆の規則 11b、`backend/app/services/gemini_raw_copy_v102_product_first.py` の状態・単位の決め方、人が状態を直した行の skip（`backend/app/services/v102_buyback_unit_svc.py:203`）、`unit_basis`、DB の形。

## 便に分ける（変更は一度に 1 つ）

| 便 | 中身 | 区分 | 承認 |
|---|---|---|---|
| 便1 | ①買取の物差しの時点: 「今から N 日に見えた店」→「その行の投稿日時より前・30 日以内の、店ごとの最新の値」。対象・帯・状態は今の便BB のまま。設定 `unit_buyback_max_age_days` 7→30 と note は記録 SQL（ADR-1007） | コード＋記録 SQL | この設計 |
| 便2 | ①の対象を広げる: 「単位の語なし・「個」（状態の語は問わない）」の箱系の行へ、Pack（r ≤ 0.2）を足す、B の状態の写し、C の理由の外し方、D の記録。設定 `unit_buyback_pack_max`=0.2 は記録 SQL | コード＋記録 SQL | この設計 |
| 便3 | v102 の保存で `unit_basis` を書く（物差しを溜める）＋③自社前日の段 | コード | 別設計（早く溜めるため、便2 の次に最初に出す） |
| 便4 | 状態の語の穴: 「キズあり」「ノーシュリンク」をダメージ系・シュリンクなしの語に足す | 記録 SQL | 別設計 |
| 別設計 | ②他社の販売価格（取得元・表・更新） | — | PO が店を決めた後 |

各便は「本番反映 → 置き換え試験と同じ件の再解析 → 測る → 次の便」。

## 証拠（試算。2026-10-21、v102 直近 30 日、reader 鍵）

| 試し方 | 行 | 正解 | 外れ | 決まらない |
|---|---|---|---|---|
| 単位の語で正解が分かる行で、語を伏せて判定（①30日→③ちょうど 1 つ、Pack r≤0.2） | 1573 | 1360 | 1 | 212 |
| 同上の単位別 | Box 1268／Case 226／Pack 79 | Box 1146／Case 148／Pack 66 | Pack 1 | Box 122／Case 78／Pack 12 |
| 同上の段別（この設計は①だけ） | ①1272／③89 | ①1271／③89 | ①1／③0 | — |
| ①を本番の表の形の SQL（投稿日時より前・30 日・店ごとに最新・中央値）で再計算し、試算の Python と照合 | 1573 | 1573 行すべて同じ値 | — | — |
| 語なしの行から無作為 60 行（正解は Opus が原文で判定） | 60 | 45（45 行すべて今の単位とも一致） | 0 | 15（うち今の決め方で正しい 14、原文でも決められない 1） |
| Pack が正解の行 51 行（全件）＋ Case が正解の行 40 行（無作為）で、語を伏せた判定を Opus が原文で判定 | 91 | 決まった 54 行（Case→Case 21・Pack→Pack 31・Case→Box 1・Pack→Box 1）で外れ 0 | 0 | 37（プロモパック系の商品など。今のまま） |
|  ↳ 判定が今の単位と違う 2 行 | 2 | Case→Box の 1 行は原文「(5カートン+10BOX) @11,800 在庫70」で箱の値段＝判定が正しく今が誤り。Pack→Box の 1 行は「DXパック @18,000」で 1 パックの値段ではない（商品の当て先の問題。悪化ではない） | 0 | — |
| 便BB の対象を広げた後に便UP の「値段の相場ずれ」が新しく付く行（試算） | 989 | — | 新しく付く 0 | — |
| condition_basis の長さ（追記後の最大） | 現行最大 53 字 | 追記しても 100 字を超える行 0 | — | — |
| 状態が語で決まった行（R1〜R3）× 値段の単位 | 474 | 438 一致 | — | 32 |
|  ↳ 食い違い | 4 | — | — | 4 件とも 120〜680 円の Searched box（実はパック。今の誤り） |

- 外れ 1 件（商品 id 42、10/11、22,000 円、正解ラベル Pack・判定 Box・r 0.898）は、商品名に「パック」を含む箱で、正解ラベル側の誤りの疑い【推測】。外れ 0 を受入条件にはせず、置き換え試験で変わる行を原文で全件確かめる（K2）。
- 試算の「語なし」は、価格の行に箱・カートン・パックの語が無いかを単純な語の照合で見たもの（社外秘 `v3/v3_base.py:67-72`）。コードの条件（上の便2）とは定義が違い、v102 は `unit_basis` を保存していないので件数の突き合わせはできない【未確認】。このため便2 の K2 は本物のコードを現行全件に当て、K6 で差を全件列挙する。
- 決まらない 212 行の主因は「買取も自社の物差しも無い商品」（206 行）。②他社の販売価格が入ると減る見込み【推測】。

## 代替案

| 案 | 採らない理由 |
|---|---|
| 値段で決まらない行を要確認に回す（Opus の当初案） | 無作為 60 行で決まらない 15 行のうち 14 行は今の決め方で正しい。回すとタブが語なし行の 1/4 ほど増える |
| 状態の語があれば値段を見ない（今の便BB） | PO の 2.「状態が確定したパターンも 3 を適用」に反する。ダメージ系の箱・ケースの空振り（棚卸し D の 10 行）が残る |
| Pack の帯を「箱÷入り数」で決める | 正解が 9 件減り、外れは減らない |
| 価格で書かれた単位も書き換える（便UP を自動修正に） | PO の 1.（書いた単位が最優先）に反する。便UP の設計 `docs/handoff/v102-unit-price-check/design.md:29` でも不採用 |
| ②他社を先に作る | データが無く、取得元が未決。①③で 1573 行中 1361 行決まる（正解 1360） |
| ①〜③を 1 つの設計・承認でまとめる | ③は `unit_basis` の保存という別の変更が前提で、SQL・最少件数を file:line まで書けていない。開発ルール（実装カードで決めることを残さない）に合わせ、承認は便1・便2 に限る |

## リスクと対処

| リスク | 対処 |
|---|---|
| 買取の値が古い・つなぎ間違い | 投稿日時より前・30 日以内の値だけ。中央値。つなぎ間違いは便BB の設計どおり別課題 |
| 〆の判定（規則 11b）が変わる | basis の先頭を変えない（D）。K4 で〆の行の変化を見る |
| 品質の集計（既定で決まった行の数）が変わる | 語なしで値が同じ行の basis は変えない（D）。語で決まった行はもともと集計の式に当たらない |
| 便BB・便UP・人の判断との順序 | 位置は今の便BB と同じ（人が直した値の後、規則 13・便UP の前）。人の状態判断は今どおり最後に勝つ |
| 語なしの行の単位が変わると、便UP の自社の相場（単位ごとの中央値）も変わる。この波及は試算（新しく付く 0）に入っていない | 便2 の置き換え試験は便UP まで通して当て、K5 で要確認タブの増えた行 0 を見る |
| 「パック」が商品名に入る箱・「DXパック」のような箱に近いパック（外れ・Pack→Box の形） | 値段で決めるので語の影響は受けない。K2 で「今 Pack → 判定 Box」の行を名指しで全件列挙し、原文で判定する |

## 受入条件

便1（時点の変更）:

| 基準 | 検証方法 |
|---|---|
| K1-1 テストが通る: 物差しが投稿日時より前・30 日以内・店ごとの最新の値の中央値になる（投稿日時より後の値・31 日前の値を使わない）。`posted_at` が None なら何もしない。対象・帯・状態は今の便BB と同じ（G4） | CI |
| K1-2 置き換え試験（v102 直近 30 日の現行全件に便1 のコードを当てる）で変わる行は全件を原文で判定し、誤り 0。変わる行以外の変化 0 | 社外秘フォルダに全件表 |
| K1-3 本番反映・記録 SQL の COMMIT 後、K1-2 の変わる行の job を再解析し、試験どおり。要確認タブ（tab_true）で増えた行 0（G3） | reader で読む |

便2（対象を広げる・Pack・状態の写し）:

| 基準 | 検証方法 |
|---|---|
| K1 テストが通る: 語なし／「個」／ダメージ語／サーチ済語／シュリンクなし語／「未開封」「未サーチ」の語（既定と同じ種類）／別の区分の語だけが当たった行（例: テープカット×Case の帯 → Opened case、種類が 2 つ以上 → 何もしない）。この組の件は `item["review"]` に `{"kind": "condition_multiple_candidates", "codes": [...]}` を入れた形（`backend/tests/test_v102_buyback_unit.py:229-234` の `_v102_item` の形）で作り、codes が取れない行は何もしないことも確かめる × 比（Box・Case・Pack・帯の間）の組で、B の表どおりの単位・状態・basis（D の表）になる。**ダメージ語で今すでに Damaged sealed box・Box・`condition_multiple_candidates` の行が、Box の帯の値段で理由だけ外れ、basis の後ろに `|PRICE:①r=` が付く。** 語なしで値が同じ・理由ありの行は basis が変わらない。単位の語がある行・単品語の印の行・セット系・人が直した行は変わらない。`unit_buyback_pack_max` が無ければ Pack を決めない | CI |
| K2 置き換え試験（v102 直近 30 日の現行全件に**便2 のコード**を当てる。便UP まで通す）で、変わる行は**全件**を原文で判定し、誤り 0（G2）。「今 Pack → 判定 Box」の行は別に名指しで列挙する | 社外秘フォルダに全件表。Opus が原文で判定 |
| K3 置き換え試験で、変わる行以外の 商品・単位・状態・数量・価格 の変化 0 行 | 置き換え試験の突き合わせ |
| K4 〆（Sold out・excluded）の行の変化 0 行 | 同上 |
| K5 本番反映・記録 SQL の COMMIT 後、K2 で変わった行の job を再解析し、試験どおりに変わる。要確認タブ（tab_true の数え方）の前後で、増えた行 0（G3）。今 `condition_multiple_candidates` が付き値段で単位と状態が決まった行で、理由が残る行 0（G1。行数と、決まらなかった行の理由ごとの件数は K2 で記録する） | reader で読む |
| K6 試算との差の説明: ①判定関数（`decide_code` と B の表）を、語で正解が分かる 1573 行に直接当て（行の単位の語を伏せた入力を作る）、試算の①の段（決定 1272・外れ 1）と同じ件数。②K2 で、コードの対象と試算の「語なし」の定義が違う行を全件列挙し、差の理由がすべて定義の違い（例:「個」・語の照合の差）だけ | 置き換え試験 |

## 戻し方

- 便1: コードを revert。記録 SQL の rollback で日数を 7・note を元に戻す。変わった行は再解析で戻る。
- 便2: コードを revert。記録 SQL の rollback で `unit_buyback_pack_max` を消す（キーが無ければ Pack は判定しない）。変わった行は再解析で戻る。

## 維持の仕組み

- 帯の数字は設定（`tcg_distribution_settings`）で持つ。直すときは置き換え試験で外れ 0 を確かめてから。
- 状態の種類の写し（B の表）は ADR-1036 にも書き、状態マスタに行を足す設計では、この表に入れるかを決める（ADR-1035 の維持の仕組みと並べる）。
- 買取の CARTON・BOX_SHRINK の更新が 10/12 から止まっている（recon 3-2）。Case の判定は BOX の比で行うので便1 は影響を受けない。取得側の修正は別課題。
- 守り手: Opus（便ごとの置き換え試験と K2 の全件判定）。

## 接触面分析（6 面）

| 面 | 影響 | 対処 |
|---|---|---|
| ①人（PO・仕入れ担当） | 在庫表・要確認タブで、値段で決まった行の単位・状態が変わる（例: ダメージの箱が要確認から外れ Damaged sealed box で並ぶ）。人が直した行は変わらない | 各便の K で、変わる行を全件原文で判定してから反映。反映後に要確認タブの増減を測る |
| ②エージェント（Opus・Sonnet） | 置き換え試験と全件判定の手間が便ごとに要る | 守り手を Opus に固定（維持の仕組み） |
| ③機械（v102 の保存処理） | 便BB の位置で投稿日時を読む SQL が 1 回増える（対象がある job だけ）。物差しの SQL は 1 文 52〜56ms（ai_ro 上の実測） | 対象の行がある job だけ読む（今の便BB と同じ）。public 表での速さは便1 の K1-3 で job の処理時間を見る |
| ④データ（analysis_results・設定表） | 単位・状態・condition_basis・review_reasons が変わる。設定表に 1 key 追加・1 key 変更。品質の集計（`backend/app/services/tcg_supplier_quality_svc.py:17-18` の末尾一致）は D の表で影響なし | 設定は記録 SQL（ADR-1007）。basis の先頭の規則記号は変えない（〆の規則 11b） |
| ⑤本番 | deploy で反映。DB の形（列・表）は変えない。DB に入れるのは設定の値だけ（記録 SQL、ADR-1007） | 戻し方の表のとおり revert と設定の rollback |
| ⑥外部（仕入元・買取の店のサイト） | 影響なし。買取の取得（読むだけ）はそのまま | — |

## 外部・過去事例の参照と我々への応用

- 社内の前例: 便BB（`docs/handoff/v102-buyback-unit/design.md`）。買取の比で Box／Case を決め、置き換え試験 8 行・当たり 8。帯 0.5／2／6 は今回の 1573 行でも外れ 0（Box・Case）。
- 社内の前例: 便UP（`docs/handoff/v102-unit-price-check/design.md`）。自社の単位ごとの中央値（別投稿 3 件以上）で要確認を付ける。便3 の③はこの物差しを「語で確定した行だけ」に絞って使う予定。
- 外部事例: 該当なし。社内の仕入元の価格と買取価格の照合で、比べられる公開の実測値が無いため（便BB と同じ判断）。

## 未決（PO）

- ②他社の販売価格: どの店の値段を使うか（取得元）。決まるまで②の段は空のまま。

## 審査（Architect・同じ AI による自己審査。独立した第二者のレビューではない）

- 1 回目（HEAD 86e69f306）: 相談役 Fable REVISE・審査役 REVISE。主な指摘は「値が同じ行で要確認が外れない（主例が直らない）」「ADR-1035 What 2 の例外の明記」「KGI/KPI 表」「カードで決める事項の残り」「略記」。この版で反映した。
- 2 回目（HEAD ca5dc8fed）: Fable REVISE（テープカット等の別区分の語が review_extra の codes に入り、Case 帯で CN0001 にしてしまう）・審査役 REVISE（語で決まった CN0003/CN0001/CN0007、直す既存テストの列挙、G1/K5 の母数、SAVEPOINT 内での呼び出し、D 表の分け方、recon の行番号）。この版で反映した。
- 3 回目（HEAD 0e47be8a4）: Fable REVISE・審査役 REVISE（Fable: codes の置き場所が違う・「既定」の定義が 2 通り読める。審査役: codes は件の `review_extra` ではなく `item["review"]` の要素にある、`masters["unit_alias_to_info"]` は `.get` に、直すテスト 2 件の抜け）。この版で反映した。
- 4 回目（HEAD 279aa793e）: 審査役 REVISE（「既定」の判定順が 1 段落の中で食い違い、語なしで Error・FLAG_SINGLE の行が何もしなくなる読み方ができる）。判定順 (1)(2) に書き直した。
- 5 回目（HEAD 09dd2a261）: 審査役 APPROVE・相談役 Fable APPROVE（Fable は 279aa793e で APPROVE の後、09dd2a261 の差分も APPROVE）。設計合格（便1・便2）。PO 承認・実装承認は別。
