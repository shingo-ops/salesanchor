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

## 外部事例
該当なし（自社既存ロジック改善のため）

## 影響範囲
- `backend/app/services/buyback_scraper/product_matcher.py` のみ
- DB schema変更なし
- API変更なし（戻り値の統計dict構造は同一）
- match_candidates JSONのキーが `keyword`/`kw_len` → `score`/`keywords` に変更

## 戻し方
`git revert <commit>` で即時復元可能（DB変更なし）

## 守り手
backend/app/services/buyback_scraper/product_matcher.py
