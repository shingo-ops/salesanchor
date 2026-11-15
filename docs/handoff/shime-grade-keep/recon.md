# recon: 品質の言葉つきの〆が、別の品質の在庫まで閉じる件

状態: 現在地の調査済み（2026-11-13、Opus が本番の読み取り専用の道で直接確認）。基準: origin/main `e930f1b24`（2026-11-13 12:25 JST）。

社外秘の扱い: 仕入元名・原文は書かない。原文と問い合わせの生の出力は作業記録 `~/CC報告ファイル-keep/shime-auto-check/daily/20261113_1200/`（リポジトリ外）にある。以下の「ファイル名.txt」はそこを指す。

## 1. 起きたこと（観測事実）

- 11/13 02:35 JST の投稿 X（仕入元 S）に、同じ商品（product_id 420436）のカートンが2行ある（raw_a.txt・prior.txt）。
  - 行 cc01bec5: 「A品」と書いた行。残3・1カートン 180,000。状態 Case、根拠 `R4:単位既定`（状態は語でなく単位の既定で決まった）。
  - 行 3acb0463: 「テープに切れ込みがある品」と書いた行（原文の行 3・6・7）。残1・170,000。状態 Case、根拠 `R4:単位既定`。
  - 両方とも raw_state は空（detail.txt）。
- 11/13 09:19 JST の投稿 Y（同じ仕入元）の1行目が「そのカートン 切れ込み有り〆」。行 cad02664: 状態 Case・Sold out・根拠 `R4:単位既定`・is_current True（detail.txt）。
- 結果: A品の行 cc01bec5 も is_current False になった（cur.txt・after.txt）。配信は `ar.is_current = TRUE` の行だけを読む（`backend/app/services/tcg_distribution_svc.py:373`・`:496`・`:539`）。A品3カートンは「売り切れ」と同じ扱いで外に出ない。
- 14:07 JST の時点で、Y より後にこの仕入元からこの商品の投稿は無い（after.txt）。

## 2. 仕組み（コードの実物）

1. 状態の判定は、その件の行を全部つないだ文 `block` で行う（`backend/app/services/gemini_raw_copy_v101.py:964`）。`block` は `resolve_condition_v2` に `raw_state` として渡る（`backend/app/services/gemini_raw_copy_v102_product_first.py:825`）。
2. `resolve_condition_v2` は状態の辞書（public.line_conditions の search_kw / exclude_kw）を `block` に当てる。どれにも当たらないと箱系大は Case（`R4:単位既定`）になる（`backend/app/services/tcg_analyzer_svc.py:950-963`）。
3. 状態の辞書（dict.txt）に「切れ込み」「A品」はどの状態の search_kw にも無い。カートンの開封の状態（CN0009 Opened case）の語は「カートンテープカット・テープカット済・テープカット・テープ切」。今回の行は「テープ」と「切」の間に別の字が入っていて、「テープ切」と続いていないので当たらない。カートンの傷みの状態（CN0002 Damaged case）にも「切れ込み」は無い。
4. 〆の行は状態が語で決まっていないので、前の在庫の状態を引き継ぐ候補になる（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:47-54`・`:369`）。前に同じ状態（Case）の在庫があるので規則12d で引き継ぎをせず、〆の行は Case のまま（同 `:462-470`）。規則12h（設定 keep_words）は値段・数の無い箱の仲間の取り残しにだけ働く。今回、投稿 Y の追加の相手（analysis_soldout_extra_targets）は 0件（extra.txt）で、12h は相手を作っていない。〆の行は 12d の `continue` のとおり Case のまま。
5. 現行の行の決め方: 同じ仕入元の (商品, 状態) の組ごとに、最新の投稿を1つ決め、その投稿の行だけを現行にする（`backend/app/services/tcg_analyzer_svc.py:2044-2047`・`:2111-2117`・`:2119-2148`）。投稿 Y が (420436, Case) の最新になったので、投稿 X の (420436, Case) の2行（A品と切れ込み）が両方とも現行から外れた。
6. 要確認の印（needs_review）はこの現行の決め方に入らない（`_merge_supplier_products` の対象は `pid_resolved = TRUE` だけ。`tcg_analyzer_svc.py:2050-2056`）。配信は needs_review の行を読まない（`tcg_distribution_svc.py:374`・`:497`）。→ 〆の行を要確認にするだけでは、A品は外れたまま（隠れる害は同じで、要確認が1件増える）。
7. 再解析での直しは ADR-1032 の見張りに止められる: 古い投稿 X の行が「新しく現行になる」には、(i) 同じ仕入元のより新しい投稿に同じ商品の行が無い か (ii) 付け直しの前から現行だった が要る（`backend/app/services/tcg_analyzer_svc.py:2121-2138`）。投稿 Y に同じ商品の行がある限り (i) は成り立たず、A品の行は前から現行でないので (ii) も成り立たない。→ 辞書を直して X・Y を再解析しても、A品の行は現行に戻らない（コードの読み取りによる。試験では未確認）。
8. 語を足したときの当たり方の前提（2026-11-15 設計審査1回目の指摘を受けて作業記録で確認）:
   - id 13（Damaged case）の exclude_kw は空（dict.txt の xkw 欄）。今回の文が除外語で外れることはない。
   - 投稿 X で「切れ込み」を含む原文の行は6行目の1行だけ。その行を件の行に持つ解析行は 3acb0463 だけ（kirekomi.txt。件の行の一覧 source_lines との照合）。A品の行 cc01bec5 の件の行は 3〜4 行目（detail.txt）。A品の行の `block` にこの語は入らないので、A品の行は Case のまま。
   - 6行目の文は Opened case の語（「テープ切」など）にも Case の語にも当たらない形（recon §2-3）。当たる状態は Damaged case の1つだけなので、価値の順位で選び直す場面（`backend/app/services/tcg_analyzer_svc.py:879-883`）にならない。
   - 投稿 Y の〆の行は語で状態が決まり（Damaged case）、引き継ぎの候補から外れる（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:47-54`・`:375`）。

## 3. 規模（本番の読み取り）

| 問い | 値 | 出典 |
|---|---|---|
| 直近180日、原文に「切れ込み」を含む行（全仕入元） | 2行（今回の投稿 X の1行と投稿 Y の1行だけ） | kirekomi.txt（AUDIT rows=2 result=ok） |
| 直近30日、1投稿に同じ商品×状態の In Stock が値段違いで2行以上ある組 | 1,233組（386投稿・43仕入元）。多くは数量の段ごとの値段で、まだ分けていない | dup.txt |
| そのうち次の同じ組の行が Sold out の組 | 11組 | dup.txt・dup_soldout.txt |
| 11組のうち、品質の違う2行の片方だけの〆で両方が閉じたもの | 1組（今回） | dup_soldout.txt（Opus が11組を1件ずつ確認） |

11組の残り（記録のため）: 数量の段ごとの値段が8組。「状態の言葉が辞書と少し違う」ために2行が同じ状態になった組が2つある（1組は、開封済みを表す言い回しが辞書の語と一字違いで当たらなかった。もう1組は、包装なしと傷ありを並べた言い回しが、包装なしの状態だけになった）。この2組は〆の文が状態を書いておらず、両方閉じたのは正しいか判断できない（不明）。本件の範囲外。

## 4. 既存の ADR・設計の検索

- `git grep -i -e "A品" -e "切れ込み" -e "グレード" -e "品質の違" -- docs/adr docs/handoff`: 〆で品質を分ける ADR・設計は無い。
- 関係する ADR: ADR-1032（現行の行の復活の見張り）、ADR-1035（状態・単位と要確認0件化）、ADR-1023（状態の価値の順位）、ADR-1073（箱の〆の全状態、規則12h）。
- 状態の辞書を本番で変えた前例: `docs/handoff/condition-unit-booklet/data/`（01_precheck・02_apply・03_verify・04_rollback の SQL と README）。

## 5. 未確認

- 「テープに切れ込みがある品」を、仕事の上で「傷みのあるカートン」と「開封済みのカートン」のどちらとして扱うか（事業の判断。PO に聞く）。
- 投稿 X の A品3カートンが今も売れ残っているか（仕入元に聞かないと分からない）。
