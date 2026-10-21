# Opus 審査記録: 値段で単位を決める（ADR-1036、承認範囲は便1・便2）

審査役: reviewer（Opus、同一AIの別エージェント。独立した第二者レビューではない）。相談役: Fable（PO の指示で相談）。どちらも読み取りのみ・checkout 禁止。

| 回 | 対象 | 審査役 | Fable | 主な指摘 |
|---|---|---|---|---|
| 1 | 86e69f306 | REVISE | REVISE | 値が同じ行で要確認が外れない（主例が直らない）／ADR-1035 What 2 の例外の明記／KGI・KPI 表／カードで決める事項の残り／略記 |
| 2 | ca5dc8fed | REVISE | REVISE | 語で決まった CN0003・CN0001・CN0007 の扱い／直す既存テストの列挙／G1・K5 の母数／SAVEPOINT 内での呼び出し／D 表の分け方／recon の行番号（審査役）。テープカット等の別区分の語で Case 帯を CN0001 にしてしまう（Fable） |
| 3 | 0e47be8a4 | REVISE | REVISE | 別区分の codes は件の `review_extra` ではなく `item["review"]` の要素にある／`masters.get` に／直すテスト 2 件の抜け（審査役）。同じ置き場所の誤り＋「既定」の定義が 2 通り読める（Fable） |
| 4 | 279aa793e | REVISE | APPROVE | 「既定」の判定順が 1 段落の中で食い違い、語なしで Error・FLAG_SINGLE の行が何もしなくなる読み方ができる（審査役） |
| 5 | 09dd2a261 | APPROVE | APPROVE | なし |

VERDICT: APPROVE
