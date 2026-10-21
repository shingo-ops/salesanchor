# recon: 写した値段に等級（PSA8 など）が入ると値段が空になる件

- 日付: 2026-10-21（JST）
- 基準: origin/main 7d8b5f732（worktree `release/price-grade-strip`）
- 社外秘の材料（原文・仕入元・生出力）: PO の手元の記録フォルダ `box-error189/price-grade/`・`price-impact/`（リポジトリに置かない）
- 既存 ADR の確認: ADR-1031（状態・PSA の2群）・ADR-1035（要確認0件化）。値段の読み方を定めた ADR は無い（`docs/adr/FEATURE-INDEX.md` と `git grep -il "single_number\|price_unresolved" docs/adr/` で 0件）

## 1. 何が起きているか（観測事実）

- 本番の v102 では、Gemini が値段の欄を原文のまま写す（指示書 raw_copy_v101_f_ct の値段の欄「その件の価格の文字を、そのまま写す」）。等級を外せという決まりは指示書に無い。
- 値段を決める処理（gemini_trust の経路。本番の v102 はすべてこの経路）:
  - `backend/app/services/line_analysis_v102_svc.py:367` が `gemini_trust=True` で `extract_items` を呼ぶ。
  - `backend/app/services/gemini_raw_copy_v101.py:939-944` で、値段は `_single_number(item["price"])`、数量は `_single_number(item["quantity"])` で決める。
  - `backend/app/services/gemini_raw_copy_v101.py:864-875` の `_single_number` は、数字のかたまり（`:861` の `_NUMBER_RUN_RE`）がちょうど1つのときだけ数を返す。万・千・億・k（`:859`）があれば None。
  - 値段が None で写しに数字があれば、`:1300-1301` で price_unresolved が付き、要確認になる。
- 「7,500円(PSA8)」は数字のかたまりが「7,500」と「8」の2つなので None になる。
- 原文から値段を読む別の処理 `backend/app/services/extraction_judgement_svc.py:724` の `resolve_price_quantity`（行ごとの数字の取り出しは `:589-636` の `_extract_line_numbers`）は、`:603` の規則「英字か - の直後の数字は取らない（Y の直後と、数字に挟まれた x は例外）」で PSA8 の 8 を取らない。このため 7500 を読める。ただしこの値は `:941-944` の price_source_mismatch の比較だけに使われ、値段そのものには使われない。
- `_single_number` の製品コード内の呼び出しは2か所だけ: `:882` の `_fill_from_copy`（gemini_trust でない v102。本番では通らない）と `:940`。

## 2. 本番データ（reader 鍵・読み取りのみ・2026-10-21）

- v102 の解析結果は 34,796 行。写しの値段に等級の語（PSA・BGS・CGC・ARS・鑑定 など、全角を含む）があるのは 11 行で、すべて古い投稿（is_current=False・2投稿）。現行 4,675 行には 0 行。
- 11 行の形: 半角かっこ＋円が 8 件、全角かっこ・円なしが 3 件。等級は PSA6〜PSA9。11 行とも原文から読んだ値段とは一致する。
- 英字を含む写しの値段は 172 種・1,185 行（11 行を含む）。

## 3. 試し計算（本番の 1,185 行と合成の形。読み取りのみ）

| 案 | 中身 | 1,185 行: 空→値 | 値→別の値 | 値→空 |
|---|---|---|---|---|
| P1/P2 | 等級の語（PSA/BGS/CGC/ARS）をコードに書いて外す | 11 | 0 | 0 |
| F1 | 英字か - の直後の数字は数えない（例外なし） | 11 | 0 | 10（`Y100,000/単価` など） |
| **F2** | **`backend/app/services/extraction_judgement_svc.py:603` の規則そのまま（Y と数字x数字の例外つき）** | **11** | **0** | **0** |
| F3 | F2＋直後が英字の数字も外す | 16 | 0 | 2（`¥19,000BOX`） |

- F2 の合成の形での結果: 全角 `ＰＳＡ９`・小文字 `psa10`・`PSA 10`・先頭の `PSA10 7,500円`・`BGS9.5`・`CGC 10` は空→7500。値段の欄が `PSA10` だけの場合は 10→空。`y100,000`（小文字）・`JPY100,000`・`x100`・`Y-100` は値→空（本番に 0 件）。
- 値→別の値（値段が違う数に変わる）は、どの案・どの形でも 0 件。

## 4. 等級の名前の正本

- 等級の状態は `public.conditions`（本番 view `ai_ro.public__line_conditions`）の CN0015〜CN0018・CN0022 の5行。いずれも PSA だけで、BGS・CGC・ARS の行は無い。
- 5行だけを選ぶ列は無い（note の「鑑定品」は解析に渡る dict に入らない。canonical の「PSA」始まりで選ぶには、コードに PSA と書くことになる）。
- コードには `backend/app/services/tcg_product_guards.py:6` にも PSA の正規表現がある（単品の印。BGS・CGC は無い）。
