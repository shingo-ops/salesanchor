# recon: プロモパック系に状態「雑誌付き」を足す前の現状

基準: origin/main 38613d7d7。本番の値は reader 鍵の読み取り（ai_ro の view）で 2026-10-20 13:10Z に取得。
原文・仕入元名を含む生出力は社外秘の保管場所に置き、ここには件数と仕組みだけを書く。
調べは Sonnet、まとめは Opus（2026-10-20）。

## 既存 ADR の検索

- ADR-1007（migration は構造のみ・値は記録 SQL）
- ADR-1023（状態の価値順。「状態を足すときは群と順位を決めて値を入れる」）
- ADR-1031（群 single / promo_pack と区分「プロモパック系」）
- ADR-1035（状態ごとの単位と区分「ブックレット系」。「状態を足すときは単位も同時に決める」）

line_conditions を足す手順だけを書いた専用の正本は、docs/specs・docs/handoff の両方で見つからなかった。手順の正本は上の4つの ADR の「維持の仕組み」と、記録 SQL の前例（docs/handoff/single-promo-pack-conditions/data/、docs/handoff/condition-unit-booklet/data/bin2/）。

## 【事実】状態を決める仕組み

### 読み込み

| 何 | 場所 |
|---|---|
| 状態の行の読み込み。priority>0 かつ is_active、priority 昇順 → app_kubun 長い順 → code 昇順 | backend/app/services/tcg_analyzer_svc.py:656 |
| 群 single / promo_pack / booklet は include_scoped_groups=True のときだけ返す | backend/app/services/tcg_analyzer_svc.py:653（SCOPED_VALUE_GROUPS） |
| v102 は群ごとに scoped_cond_entries へ分ける | backend/app/services/line_analysis_v102_svc.py:208-232 |
| 区分がプロモパック系なら群 promo_pack の行だけで判定 | backend/app/services/gemini_raw_copy_v102_product_first.py:585（_KUBUN_TO_VALUE_GROUP）、:592（_resolve_scoped_condition）、:619（_resolve_condition） |
| 群の中で canonical から状態 id を引く（canonical は群の中で重ならないこと） | backend/app/services/line_analysis_v102_svc.py:653（_scoped_condition_id） |

### 既定（R8）

- 状態名「未開封」と basis「R8:プロモパック既定」はコードの定数。gemini_raw_copy_v102_product_first.py:91、:94。
- id60（CN0020 未開封）は search_kw が空。match_keyword は search_kw が空だと当たらない（tcg_analyzer_svc.py:336）。つまり id60 は検索で当たらず、既定としてだけ返る。
- 流れはこうなる。
  - 何も当たらないと resolve_condition_v2（tcg_analyzer_svc.py:882）は R4b の FLAG_SINGLE を返す（:955-962）。
  - それを _resolve_scoped_condition が既定の未開封・R8 に置き換える（product_first.py:605-607）。

### 2つ以上当たったとき

- 層1: _pick_lowest_value（tcg_analyzer_svc.py:861、:942 から呼ばれる）。
  - 当たった行が全部同じ群で value_rank が全部あれば、value_rank が最大の行を採る。
  - どれかの value_rank が NULL なら、並びの先頭を採る。
- 層2: プロモパック系だけ、当たった code が2つ以上なら要確認（condition_multiple_candidates）を付ける。gemini_raw_copy_v102_product_first.py:608-615。

### 単位

- 状態の単位は、次のどちらかで状態の単位が今の単位と違うときに優先される（理由 state_word）。gemini_raw_copy_v102_product_first.py:678-704。
  - 単位が空のとき。
  - 基準が R1〜R3 のとき。
- 状態の行の priority=2 は basis R2 になる。

### 実コードでの確認（本番の id60/61/62 の値で _resolve_scoped_condition を実行）

| 入力 | 結果 |
|---|---|
| 雑誌付き袋とじ未開封 | 未開封・R8・要確認なし |
| 袋とじ未開封 | 未開封・R8 |
| 雑誌付き 未開封 開封済み | 開封済み・R2 |
| 雑誌無し 開封 | 開封済み・R2 |

- 今の規則では「雑誌付き」と「雑誌無し」は、どちらも状態が未開封になり、区別されない。
- 仮の行（priority 2・REGEX・群 promo_pack）を実コードに足した試算もした。結果は次のとおり。
  - 「雑誌付き袋とじ未開封」は雑誌付き（R2）になる。
  - value_rank=4 だと、「雑誌付き 開封済み」は雑誌付きが採られ、要確認が付く。
  - value_rank が NULL だと、開封済みが採られ、要確認が付く。

## 【事実】本番の状態マスタ（群 promo_pack と、使用中の code）

| id | code | canonical | priority | match_type | unit_id | value_rank |
|---|---|---|---|---|---|---|
| 60 | CN0020 | 未開封 | 10 | KEYWORD（search_kw 空） | 11 Pack | 1 |
| 61 | CN0021 | 開封済み | 2 | REGEX `(?<!未)開封(?!前\|していない\|なし\|不可)` | 11 Pack | 2 |
| 62 | CN0022 | PSA10 | 2 | REGEX | 空 | 3 |

- 全26行の code は、CN0001〜CN0024 と、CN+14桁が2つ。CN0025 は未使用。
- value_rank の CHECK は >=1 の整数だけ。value_group の CHECK は box / case / pack / promo_pack / single / booklet。

## 【事実】区分11（プロモパック系）と、雑誌に関する語の件数（v102・直近30日）

- 区分11は10商品。
- 「雑誌」「付録」「本誌」の語が出るのは 424590（モンキー・D・ルフィ P-159 肉ルフィ）だけ。「雑誌」は23件で、「付録」「本誌」は0件。
- 424590 の147件の書き方の内訳。

| 種類 | 件数 | 今の現行の結果 |
|---|---|---|
| 「雑誌付き」 | 15 | 現行3件。3件とも 未開封・Booklet |
| 「雑誌無し」 | 8 | 現行2件。未開封・Pack 1件、未開封・Piece 1件 |
| 雑誌の語なし | 124 | 現行7件 |

- 「雑誌付き」と「開封」が同じ件に出る例は0件。「開封」を含む5件は、どれも雑誌の語なしの件。
- 区分11の外でも、雑誌の語は出る。424591（シングル系）・440413・466058 と、商品なしの件。群 promo_pack の行は区分11の商品にしか使われないので、ここは影響を受けない（product_first.py:585）。

## 【事実】画面

- 在庫表の状態の色: frontend/src/features/inventory/conditionBadge.ts:16 の名前一致表にない状態は灰色になる。未開封・開封済み・PSA10 も表になく、灰色。
- 状態名は i18n を通らない（DB の canonical をそのまま表示）。
- 状態の管理画面（backend/app/routers/super_admin_conditions.py:115-125、:161-）は value_group / value_rank を受け付けない。群のある状態は記録 SQL で入れる前提。

## 【未確認】

- GAS 在庫一覧が状態名をどう表示するか。コードがこのリポジトリになく、読んでいない。
- value_rank の重複を禁じる UNIQUE があるか。今回の値は重複しないので、影響はない。
- 解析結果が状態 id を外部キーで参照しているか。戻し方に関わるので、01_precheck で確かめる。
- 現行でない古い結果（Error / FLAG_SINGLE）が出た理由。
