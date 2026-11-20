# recon: 1行に品名を並べて〆る投稿（品名A、品名B〆）

関連: `docs/handoff/shime-bundle-close/recon.md`（縦に並べて〆る形）、`docs/handoff/shime-bundle-close/design.md`

調べた日: 2026-11-16（Opus。コードは `git show origin/main:` で読んだ。数は本番の読み取り鍵で数えた）。社外秘のため、仕入元名・人名・原文はここに書かない（原文と投稿の一覧は社外秘の作業記録 `bundle-design/oneline/` にある）。

## 1. 起きたこと（観測）
- 2026-11-16 の朝の〆の点検（手順2c）で、×1件「まとめ〆の閉じ漏れ」。投稿は1行だけで「品名A、品名B〆」の形。
- 保存された件は1件だけ（行1、品名A の商品、Sold out、照合は matched_followup）。品名B の商品は、同じ仕入元の同じ日の前の投稿の In Stock の行が is_current=True のまま残った。
- これは縦の形（品名の行が並び、その下に〆だけの行）とは別の形。縦の形の直し（便1〜便3）は「行ごとに1件」を前提にしており、1行の形は対象外（design.md §3-1 条件5「自分の名前の行」が無いので2件目は落ちる）。

## 2. 直近30日の数（読み取り鍵。候補の一覧は作業記録 `oneline/cand.txt`）
- 1行に「、」「,」「/」で区切った語と〆の語がある行を持つ v102 の投稿を拾い、目で仕分けた（163行。大半は注意書きの文）。
- 本物の「1行に品名を並べて〆」: **3投稿**（10/28・11/04・11/16）。3投稿とも、並んだ品のうち少なくとも1つが閉じていない。
  - 2投稿: 件は1件・照合は ambiguous（候補が2商品）・`product_multiple` で要確認 → どちらの商品も閉じていない。
  - 1投稿: 件は1件・照合は matched_followup で片方の商品に決まった → もう片方が閉じていない（§1）。
- 似ているが別の物（直してはいけない）: 状態の名前を2つ並べて〆る形1件、等級を並べる「PSA9 …, PSA8 … 売り切れ」1件、「パック、商品名〆」1件（「パック」は商品名ではない）、商品名の中に「・」「&」を含む〆3件、値段と数を並べた行（数の区切りのカンマ）1件。

## 3. コードの今の動き（origin/main）
- 件の照合: `backend/app/services/gemini_raw_copy_v102_product_first.py:946-948` `resolve_product_first` は件の行全体から照合文を作り `match_text_g2` で照合する。`:318-343` `match_product_g2` は候補が2つ以上なら ambiguous。→ 「品名A、品名B〆」は候補2つの ambiguous になる（読み取り鍵で見た2投稿の `pid_basis=V102:ambiguous`・`review_reasons=product_multiple` と合う）。
- 後処理の順: `backend/app/services/gemini_raw_copy_v101.py:1541-1556` `_extract_v102` は、作品で決める（`_apply_context_work` :1277）→ 直前の投稿で決める（`_apply_followup` :1302）→ 〆の相手を過去の在庫から決める（`_apply_soldout_ref` :1327）→ 規則12（`_apply_soldout_inherit` :1352）。
- 〆の相手を過去の在庫から決める規則: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:313-314` 規則10「複数を指す言葉が無く、当たる商品が2つ以上なら決めない」。→ 1行に2品の〆はここで止まる（2投稿の観測と合う）。
- 規則12: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:440-470` `decide_soldout_inherit` は、商品が直接決まった完売の件1つにつき、その**1商品**の取り残しだけを相手にする（12d・12e・12g・12h）。
- 複数の商品を閉じる受け皿はすでにある: 件の `soldout_targets` に複数の (商品, 状態) を並べると、`backend/app/services/line_analysis_v102_svc.py:1211-1214` で先頭の相手を書く行の状態にし（`_apply_soldout_targets` :944-967）、残りを `analysis_soldout_extra_targets` に書く（`_extra_targets` :969-、`_write_extra_targets`）。規則11（複数語の〆）がこの道で2商品以上を閉じている（`backend/app/services/gemini_raw_copy_v101.py:1334` の説明）。
- 保存済みの件から後処理だけをやり直して前後の差を見る道具がある: `backend/app/tools/v102_replay_diff.py`（Gemini を呼ばない・DB は読むだけ。列に `soldout_targets` を含む）。

## 4. 未確認
- 11/16 の投稿で、件が直前の投稿で決める段（`_apply_followup`）の前に ambiguous だったか（matched_followup になった理由）。手元で本番の名簿を使って流していないため未確認。実装の最初に、`v102_replay_diff` でこの投稿を流し、段ごとの照合の状態を記録して確かめる（design-oneline.md §6 の手順1）。
- 11/04 の投稿のように型番だけを並べた区切りが、区切りごとの照合で1商品に決まるか（型番だけで決めてよい中分類かどうか）。同じく手順1で確かめる。

## 5. 既存 ADR の検索
- `git grep -i "〆\|soldout\|完売" origin/main -- docs/adr/` の範囲で、〆の相手を複数の商品に広げる決まりを定めた ADR は無い。〆の規則は設計書（`docs/handoff/v102-shime-same-post-stock/`、`docs/handoff/shime-box-all-states/`、`docs/handoff/shime-bundle-close/`）が正。
