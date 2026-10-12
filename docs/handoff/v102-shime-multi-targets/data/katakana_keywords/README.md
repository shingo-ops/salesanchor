# カタカナの検索ワード 2 語の登録（product_search_keywords）

## 目的
仕入元がカタカナで書く商品名（「30th セレブレーション BOX」など）を、v102 の商品照合で商品に結びつける。
読む側: `backend/app/services/extraction_shadow_svc.py:86-106`（load_product_entries）→ `backend/app/services/gemini_raw_copy_v102_product_first.py`（照合）。マスタはジョブごとに読み直す（キャッシュなし）。

## PO 決定
2026-10-11 y（設計者経由。候補表を提示し、2 語に絞って y/n）。

## 登録内容
`public.product_search_keywords` に 2 行（同じ product_id と keyword が既にあれば入れない）。
| product_id | position | keyword |
|---|---|---|
| 440406（30th CELEBRATION） | 2 | 30th セレブレーション |
| 125081（30th CELEBRATION FUTURISTIC BOX） | 2 | 30th フューチャリスティック |

## 選んだ根拠（本番の全投稿 100,670 行で、足す前と後の照合結果を比べた。読み取りのみ）
- 30th セレブレーション：新しく商品が決まる行 8・悪くなる行 0。
- 30th フューチャリスティック：新しく決まる行 2。「30th CELEBRATION フューチャリスティック BOX」の 1 行は、今は 440406 に決まっているが、2 候補の要確認に変わる（原文は「30th CELEBRATION フューチャリスティック BOX 100@65000」で FUTURISTIC の BOX を指す。商品名「30th CELEBRATION FUTURISTIC BOX」は 125081 のため、今の 440406 の決定は誤り）。
- 見送り：3rd アニバーサリー（16 行のうち 4 行が英語版・中国版の投稿で、別商品として扱うかが未決のため保留）、セレクション 5/10（今は決まっている 16 行が決まらなくなる）。
- 行ごとの記録は社外秘のため repo に置かない（集計値のみ）。

## 手順（本番書き込みは commit.sql のみ）
1. `precheck.sql` — 対象 2 商品が各 2 行（position 0・1）、2 語はどこにも無い、全件 2954、2 商品とも is_active
2. `dryrun.sql` — INSERT 0 2 と 6 行が見えて ROLLBACK
3. `commit.sql` — 登録
4. `verify.sql` — 2 商品が各 3 行、全件 2956

実行記録: 2026-10-10T22:18Z（UTC）に Opus が precheck（期待どおり）→ dryrun（INSERT 0 2 → ROLLBACK）→ commit（INSERT 0 2 → COMMIT、22:18:40Z）→ verify（440406 = {30th CELEBRATION, 30周年 CELEBRATION, 30th セレブレーション}、125081 = {30th FUTURISTIC, 30周年 FUTURISTIC, 30th フューチャリスティック}、全件 2956）。書き込みは PO 発行の permit-danger チケット（psql write）で実行。

## 戻し方
`rollback.sql` — product_id と keyword の組が一致する 2 行だけを DELETE。DELETE 2 を確認してから COMMIT。

## 測り方
`verify.sql` の全件 = 2956、2 商品が各 3 行。戻した後は各 2 行・全件 2954。
