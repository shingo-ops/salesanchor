# design: buyback-score-matching

## 対象ADR
ADR-157 Phase 3: 買取商品マッチング自動化

## recon参照
docs/handoff/buyback-score-matching/recon.md

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| pending_review件数が減少する | POST /rematch 実行前後の件数比較 |
| match_candidates JSONに score と keywords が含まれる | DB直接確認またはAPIレスポンス確認 |
| 除外ワードヒット商品が候補に含まれない | テストケースで除外ワード商品を検証 |

## 設計概要

### スコア計算ロジック
```
score_product(product_name_norm, search_kws, exclude_kws):
  1. exclude_kws に1件でもヒット → return (-1, [])
  2. search_kws を全件評価:
     - match_one_kw(kw, product_name_norm) がTrueなら score += len(kw)
  3. return (score, matched_keywords)
```

### マッチング判定
```
candidates = [c for all products if score_product > 0]
if len(candidates) == 0 → unmatched
else:
  top_score = max(score)
  top_candidates = [c for c if c.score == top_score]
  if len(top_candidates) == 1 → auto (product_id = top.product_id)
  else → pending_review (product_id = NULL)
```

### 変更前後の例
```
買取商品: 「拡張パック ポケモンカード151 BOX」

【変更前】
match_keyword(): 「151」が最初にヒット → 即確定
他のキーワードは評価しない

【変更後】
PM0263: 「151」→3点 + 「ポケモンカード151」→9点 = 合計12点
PM0099: 「151」→3点のみ
→ 12点のPM0263を採用（スコア差で一意確定）
```

## 外部・過去事例の参照と我々への応用
- 情報検索分野のTF（Term Frequency）スコアリングと同様の考え方。長い・具体的なキーワードが高スコアになることで精度向上。
- 自社内の既存実装: `backend/app/services/tcg_analyzer_svc.py` の `match_one_kw()` は1キーワード単位のマッチを提供しており、それを組み合わせてスコア化する設計。
- 変更前のロジックは「最初のヒットで即確定」という貪欲法で、キーワード評価順序に依存する脆弱性があった。スコア式に変えることで順序非依存になる。

## 維持の仕組み
守り手: backend/app/services/buyback_scraper/product_matcher.py

- score_product() は純粋関数のため単体テスト可能
- match_one_kw() の実装変更があれば本ロジックも追随（依存関係が明示的）
- match_candidates JSONのschemaが変わった場合はフロント確認が必要（score/keywords キー）

## 影響範囲
- `backend/app/services/buyback_scraper/product_matcher.py` のみ
- DB schema変更なし
- API変更なし（戻り値の統計dict構造は同一）
- match_candidates JSONのキーが `keyword`/`kw_len` → `score`/`keywords` に変更

## 戻し方
`git revert <commit>` で即時復元可能（DB変更なし）

## 守り手
backend/app/services/buyback_scraper/product_matcher.py
