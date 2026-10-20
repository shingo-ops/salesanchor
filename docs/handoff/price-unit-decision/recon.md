# recon: 値段で単位（と状態）を決める仕組み（v102・箱系／セット系）

調べた日: 2026-10-21。基準は origin/main `9c7275ea098666d1066f64c0bb8c404ab8740e3e`（読み取りだけ）。本番は reader 鍵で ai_ro のビューだけを読んだ。
生出力と試算の原文は社外秘フォルダにある（仕入元の名前・原文を含むので、リポジトリには入れない）。この文書には件数・商品 id・状態コードだけを書く。
ラベル: 【事実】=ファイルか出力で確かめた／【推測】／【未確認】
略記: PF=`backend/app/services/gemini_raw_copy_v102_product_first.py`、TA=`backend/app/services/tcg_analyzer_svc.py`、LA=`backend/app/services/line_analysis_v102_svc.py`、BB=`backend/app/services/v102_buyback_unit_svc.py`、UP=`backend/app/services/v102_unit_price_check_svc.py`

## 1. 既存 ADR・設計の検索

検索: `git grep -il` で 単位／unit／買取／buyback／相場 を `docs/adr` に対して実施。`docs/adr/FEATURE-INDEX.md` は同じ語で 0 件（【事実】索引に単位・買取の行は無い）。

| 文書 | 関係 |
|---|---|
| `docs/adr/ADR-1035-condition-unit-and-booklet-category.md` | 状態ごとの単位。状態が原文の語（R1〜R3）で決まったら状態の単位を優先、既定の状態（R4 以降）は単位が空のときだけ埋める（本文 What 2）。ステータスは Proposed（2026-10-20）。設計は `docs/handoff/condition-unit-booklet/design.md` |
| `docs/adr/ADR-1021-bulk-condition-state.md` | バルク系の既定の状態 Bulk の basis は「R6」。R4 で始めない＝買取換算の候補に入れない |
| `docs/adr/ADR-1023-condition-value-rank.md` | 同じ群で語が複数当たるとき価値の低い側を採る（value_rank） |
| `docs/adr/ADR-1027-bundle-sale-reading.md` | まとめ売り（N単位セット）は相場・買取単位の判定から外す（本文 6） |
| `docs/adr/ADR-1028-product-packaging-table.md` | 入数の正本 `public.product_packagings`（Case→Box、Box→Pack の数） |
| `docs/adr/ADR-157-buyback-price-logger.md` | 買取価格の取得（`buyback_price_logs`） |
| `docs/handoff/v102-buyback-unit/design.md`（便BB。ADR は無い） | 買取価格との比で Sealed box／Case に決める。:2 表で閾値 0.5／2／6／7日、:4 で他社販売価格・同じ仕入元は不採用、パックは次の便 |
| `docs/handoff/v102-unit-price-check/design.md`（便UP。ADR は無い） | 相場とずれた単位を要確認にするだけ。「価格で単位を書き換える」は不採用（:29） |
| `docs/handoff/v102-unit-state-set/` | 単位が「個」などのとき状態から単位を決め直した前例 |

【事実】単位を「値段で決める」ことを定めた ADR は無い（便BB・便UP は handoff の design だけ）。【未確認】docs 全体の網羅 grep はしていない（docs/adr と上の handoff のみ）。
採番: 次の ADR は **ADR-1036**（`docs/adr/` の最大は ADR-1035。`git grep ADR-1036` は 0 件、open PR の検索も 0 件）。

## 2. 現在の単位・状態の決め方（Q1〜Q4。基準 9c7275ea0）

### Q1 単位の語があるとき
【事実】
- 確定させる。別名表 `public.unit_aliases` を引く（TA:60-72 `_UNIT_ALIAS_SQL`、TA:117-129）。語の探し方は PF:511 `find_unit_product_first`、照合は TA の `resolve_unit_v2`（TA:817-842）。
- 商品の分類（箱系）と書かれた単位（例: 箱系商品に「パック」）が食い違っても、要確認にする処理は無い。単位は書かれたまま（Pack）で、状態はパック系で解かれる。ただし相場ずれがあれば便UP が要確認にする。
- 状態による単位のやり直し: PF:65 `BOX_RECHECK_UNIT_KUBUNS`（単位区分が 空・不明・条件つき・複合・数量専用 のとき箱系として状態を解く）。PF:683 `_resolve_unit_from_state`（セット系は単位が無ければ Set／サプライ系は状態の単位 Bag／単位なし・箱系×条件つきは状態の単位／状態が R1〜R3 で単位違いなら状態の単位）。

### Q2 単位が「個」・無記入で状態の語があるとき
【事実】状態から単位を決める（PF:683 `_resolve_unit_from_state`）。状態の単位は `line_conditions.unit_id`。複数の状態に語が当たるときは、同じ群で value_rank が揃っていれば価値の低い側（ADR-1023、PF の `prefer_lowest_value=True`）、そうでなければ先に当たった行。
- `condition_multiple_candidates`: PF:102 で定義。箱系として解いたのに別区分の状態行にも語が当たるとき（PF:653 `_other_kubun_hits`）、またはプロモパック系で 2 行以上当たるときに付く。付けるだけで状態は変えない。価格は見ない。

### Q3 単位も状態も語で決まらないとき、値段で決める仕組み
- (a) 買取価格＝便BB【事実】: 呼び出し LA:962 `_buyback_units`・LA:1147。対象判定 BB:134 `is_candidate`、語の有無 BB:118 `has_no_unit_and_condition_word`、決定 BB:106 `decide_code`／BB:194 `apply_buyback_units`、物差しの SQL BB:54 `_MEDIAN_SQL`。比 r＝価格÷同じ商品の買取 BOX 中央値。0.5≤r<2 は Sealed box／Box、r≥6 は Case、その間は決めない。Pack は決めない。対象外: 単位か状態が語で決まった件（basis が R4 で始まらない）、まとめ売り、セット系、人が直した件。
- (b) 他社の販売価格【事実】: 仕組みも表も無い。設計で不採用（`docs/handoff/v102-buyback-unit/design.md` §4）。優先順位「買取>他社の販売価格>提供者固有の販売価格」は PO の発言（同 :1）。
- (c) 自社の前日までの価格【事実】: 単位を「決める」仕組みは無い。便UP が要確認を付けるだけ（LA:981 `_unit_price_mismatches`、UP:54 `_MARKET_SQL`、UP:124 `is_unit_price_mismatch`）。単位ごとの中央値（別投稿 min_posts 件以上）と比べ、倍率 ratio 超でずれ、かつ別単位の相場の方が近いときだけ `unit_price_mismatch`。単位・価格は書き換えない。

### Q4 先に勝つ順（保存時 LA:1115 `_write_results`）
【事実】人の判断 → 単位の語 → 状態 → 状態から単位の決め直し → まとめ売り（LA:1024 `_apply_bundle`）→ バルク価格 → 人が直した値 → 便BB（LA:1147）→ 規則13（〆）→ 便UP（LA:1149、理由を付けるだけ）→ 人の状態判断と〆の相手からの写し（LA:899 `_apply_soldout_targets`、最後に勝つ）→ 価格の引き継ぎ（価格のみ）。

## 3. 本番の事実（2026-10-20 15:48Z〜2026-10-21 JST 取得、reader 鍵）

### 3-1 閾値
【事実】`ai_ro.public__tcg_distribution_settings`: `unit_buyback_box_min`=0.5、`unit_buyback_box_max`=2、`unit_buyback_case_min`=6、`unit_buyback_max_age_days`=7。隣に `unit_price_check_ratio`=3、`unit_price_check_min_posts`=3、`unit_price_check_single_ratio`=5。

### 3-2 買取表（`public.buyback_shop_products` の match_status=auto）
| 種別 | 行数 | 最新の更新 | 備考 |
|---|---|---|---|
| BOX | 142 行（139 商品） | 10/20 16:00Z | 便BB が使う |
| BOX_SHRINK | 83 | 10/12 | 7 日ルールで今は物差しにならない |
| BOX_NO_SHRINK | 40 | 10/12 | 便BB は使わない |
| CARTON | 23 | 10/12 | 便BB は使わない・更新停止 |
| PACK | 40 行（38 商品） | 10/20 | 便BB は使わない |
| SPECIAL_SET | 12 | — | — |
| OTHER | 1 | — | — |

- 未結び付き（unmatched）: BOX 47・PACK 90。取得元は 2 店。
- 【事実】Case の買取（CARTON）・Pack の買取（PACK）は表にあるが便BB は読まない。CARTON と BOX_SHRINK は 10/12 以降更新が無い。
- 【推測】止まった理由は取得側の種別分類が BOX に寄せられたこと（未確認）。
- 付き方【事実】: 直近 30 日の v102 現行行に出る Box／Case／Pack 商品 316 のうち、7 日以内の買取あり 98（31%）、日数を問わなければ 128。

### 3-3 他社販売価格
【事実】ai_ro の表一覧と `migrations/` の CREATE TABLE 検索で、価格系は `buyback_shop_products`／`buyback_price_logs`（買取）だけ。他社（カードショップ等）の販売価格の表は無い。docs の検索（他社・販売価格・相場・competitor）にも設計は無い。
【推測】便BB 設計の「他社」は店の販売価格ではなく「他の仕入元の投稿の v102 行」を指していた可能性（表が無いため）。意味はPOに確認したい（【未確認】）。

### 3-4 自社の物差し（直近 30 日 = v102 開始 9/25 以降）
【事実】v102 現行行（Box／Case／Pack、まとめ・引継ぎ・Sold out・買取判定済・在庫なしを除く）2570 行のうち、価格行に単位の語があり保存単位と一致した行（正解行）1573、語なし 989（正解不明）。
- 正解行だけで「商品×単位」の中央値（別々の投稿 3 件以上）が作れる商品: Box 100／Case 24／Pack 10。語の有無を問わない便UP 流なら Box 126／Case 42／Pack 16。
- 同じ仕入元だけだと、前日までの別投稿が 3 件に届く行は 0（1573 行中）。仕入元をまたぐ必要がある。
- 試算（単位の語を消して比で判定、物差しの時点は「今」）: 買取（便BB どおり 7 日内）単独 正解 923／外れ 1／不決 649。自社前日まで（全仕入元・3 投稿以上）単独 正解 966／外れ 0／不決 607。買取→自社前日の連続 正解 1228／外れ 1／不決 344。外れ 1 件は商品 id 42（2026-10-11、価格 22000、正解 Pack・判定 Box）。
- 【推測】正解行は単位の語がある行なので、語なしの 989 行でも同程度に当たるかは未観測。

### 3-5 状態マスタの語と単位（`line_conditions`）
【事実】
- 箱: CN0003 Sealed box、CN0004 Damaged sealed box、CN0005 No shrink box、CN0006 Opened box、CN20261008072213 Searched box、CN0011 Empty box。ケース: CN0001 Case、CN0002 Damaged case、CN0009 Opened case。パック: CN0007 Unsearched pack、CN0010 Searched pack、CN0013 AR confirmed pack。
- 「ダメージ・難あり・凹み・傷み」の語は CN0004（Box）と CN0002（Case）の両方の検索語に入っている → 語だけでは Box か Case か決まらない。「キズあり」の語は無い（「傷み」のみ）。
- 「シュリンクなし／無し／シュリなし／no shrink」は CN0005。Case 側に相当する状態は無い。
- 「開封」単独は CN0003（未開封）に入る。Opened box は「ペリ無」系と「検品のため開封済み」、Opened case は「テープカット」系。
- Pack の状態はサーチ系だけ（ダメージ等の Pack 行は無い）。

### 3-6 入数
【事実】`public.product_packagings`: Case→Box の数が登録された商品 109（12〜60）、Box→Pack の数が登録された商品 134（4〜30）。
【事実】Pack の価格の実比（Pack 価格÷箱の買取中央値）は 0.01〜0.05 中心で、「箱の 1/n」付近の帯だと外す→不決になる行が多い。

## 4. 未確認
- 他社販売価格の意味（3-3）。
- 語なし行（989 行）での当たり具合。
- 買取の時点を「その行の投稿日時より前」に揃えたときの当たり具合（`buyback_price_logs` の日時で絞る試算は別途）。
- ADR-1035 の Accepted 化の時期。
