# recon: 状態ごとの単位と、区分「ブックレット系」（v102）

- 調査日: 2026-10-20 JST。コードは `origin/main` 95e623fd3（git fetch 後に読む）。本番は ADR-1024 の reader 鍵（SELECT のみ）で読む。
- 生出力・SQL・試算の台本はリポジトリの外に置く（`~/CC報告ファイル-keep/needs-review-zero/unit-by-condition/`。仕入元の原文を含むため、社外秘）。この文書には件数と場所だけを書く。
- 「現行行」は `analysis_results.is_current=true` かつ prompt_version が `v102:` で始まる行（4,598 行）。

## 既存 ADR の確認

`git grep -il "line_conditions\|unit_id\|プロモパック" docs/adr/` と `docs/adr/FEATURE-INDEX.md` で確かめた。

- ADR-1031（シングル系・プロモパック系の状態）: 区分ごとに状態の群を切り替える仕組み。今回の手本にする。
- ADR-1023（状態の価値順）: 群と順位の列（value_group・value_rank）。
- ADR-1021（バルク系の既定状態）: 区分で既定の状態を決める前例。
- ADR-1007（値は記録した SQL で入れ、migration には書かない）。
- ADR-1020（共用マスタの登録規則）。

## 事実

1. 状態ごとの単位は `public.line_conditions.unit_id` にある（`migrations/20260925_020000_conditions_add_def_unit_note.sql` で追加）。コードは `backend/app/services/gemini_raw_copy_v102_product_first.py:144-149` の SQL で、「状態の名前→単位の名前」の辞書にしている。
2. 状態の単位の今の値は次のとおり（本番 24 行）。
   - Case 系: Case(id12)・Damaged case(13)・空箱 Case(23) は Case(単位 9)。Opened case(20) だけが空。
   - Box 系: 6 行とも Box(10)。
   - Pack 系: Unsearched pack(22)・Searched pack(21)・AR confirmed pack(44) はどれも空。
   - プロモパック系: 未開封(60)・開封済み(61)・PSA10(62) はどれも空。
   - シングル系の 5 行・FLAG_SINGLE・Error・Bulk は空。
3. 単位は `public.line_units` にある。Case=9・Box=10・Pack=11・Piece=12・Booklet=17 で、Booklet は code UN0009、区分「冊子系」、別名「冊」。
4. 単位の決まり方は `backend/app/services/gemini_raw_copy_v102_product_first.py` の次の流れで決まる。
   - `:727` 原文の単位語を探す。
   - `:730` `resolve_unit_v2` で単位にする。
   - `:731` 状態を決める。
   - `:734` `_resolve_unit_from_state`（`:673-698`）で状態の単位を当てる。単位が空なら状態の単位で埋める（`:689-695`）。状態が原文の語で決まった場合（basis が `^R[123]:`、`:74`）は、状態の単位で上書きする（`:696-698`）。既定の状態（R4 以降）は、単位が空のときに埋めるだけ。セット系は Set を優先する（`:683-688`）。
5. 区分と状態の群の対応は、次の 4 か所で決まっている。
   - `backend/app/services/gemini_raw_copy_v102_product_first.py:581-584` の `_KUBUN_TO_VALUE_GROUP`
   - 群を v102 専用にする `backend/app/services/tcg_analyzer_svc.py:653` の `SCOPED_VALUE_GROUPS`
   - `backend/app/services/line_analysis_v102_svc.py:644` の `_SCOPED_GROUP_OF_KUBUN`
   - 並び順を決める `backend/app/services/tcg_result_order.py:11` の `VALUE_GROUP_ORDER`
6. value_group の CHECK 制約は、今は box・case・pack・promo_pack・single と NULL を許す（`migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql`）。
7. 商品区分は `public.tcg_product_categories` の現行 5 行（1 箱系・2 シングル系・4 セット系・9 バルク系・11 プロモパック系）。kubun_type は自由文字列。
8. 状態名・区分名・単位名は i18n のキーではなく、DB の値がそのまま画面に出る。状態の色は `frontend/src/features/inventory/conditionBadge.ts` で、名前が完全一致したときに決まる。知らない名前は灰色になる。
9. ADR-1031（PR #4523）で触ったファイル：
   - 設計: ADR・recon・design・card
   - 構造: migration 1 本と `scripts/run_all_migrations.sh`
   - コード: 上の 4 ファイル
   - テスト: 3 本
   - 記録 SQL: 01〜04 と README

## 試算（実際の関数 `_resolve_unit_from_state` を呼び、現行行の単位だけを計算し直した。書き込みはしていない）

| 変更 | 空→新しい単位 | 別の単位→新しい単位 | 変化なし |
|---|---|---|---|
| Unsearched pack→Pack | 10 | 4（Box→Pack 3・個→Pack 1） | 5 |
| Searched pack・AR confirmed pack→Pack | 0 | 0 | 110 |
| 未開封・開封済み（プロモパック系）→Pack | 4 | 0 | 8 |
| Opened case→Case | 0（現行行は 0） | 0 | 0 |
| ブックレット系で既定の状態の単位を Booklet にする（440415） | 2 | 0 | 1 |

- Box→Pack の 3 件は、原文で「BOX の価格の行」と「未サーチパックの価格の行」が 1 件にまとまっている行。状態がすでに Unsearched pack になっていて、今の単位 Box とも食い違っている。行の分け方の問題として、別に扱う。
- 要確認タブは 223 行。そのうち単位が理由の行は 64 行。上の変更でタブから外れるのは、Unsearched pack の 3 行、未開封の 2 行、440415 の 1 行。この 6 行には単位以外の理由が付いていない。
- 単位が理由で残る 58 行の内訳は FLAG_SINGLE 23・Single 20・Error 15。この変更では動かない。

## 未確認

- 再解析した後の、画面と配信の表示（試算は単位だけを計算した）。
- 「ブックレット無し」の書き方の実例。現行行で探した範囲では見つかっていない。
