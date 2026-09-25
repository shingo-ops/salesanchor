# recon: supersession-global-latest

## 変更対象ファイルと行番号

- `backend/app/services/tcg_analyzer_svc.py:1561-1565` — 呼び出し元コメント
- `backend/app/services/tcg_analyzer_svc.py:1573-1663` — `_merge_supplier_products()` 関数本体

## 現状の問題点

### 旧ロジック（ADR-158 旧設計）

`_merge_supplier_products()` は「**自分より古いメッセージ**の同一(product_id, condition_id)行を FALSE にする」という方向更新ロジックだった。

問題: 古いメッセージを再解析（reanalyze）すると、より新しいメッセージの結果が TRUE のまま残っている状態で、その古いジョブの結果も TRUE になる可能性がある（`sm_old.received_at < (現在のジョブの受信日時)` という条件が「自分より古いもの」のみを対象にしているため、再解析時は「自分より新しいメッセージ」が保護されない）。

### 旧ロジックの条件の整理

```sql
-- 自分より古いメッセージかつ同一ペア → FALSE にする
sm_old.received_at < (SELECT sm2.received_at FROM ... WHERE ej2.id = :job_id)
```

この「方向更新」は再解析シナリオで整合性が壊れる:
- メッセージA（古い）を再解析 → メッセージB（新しい）の結果がTRUEのまま残り、Aの結果もTRUEになる（二重TRUE）

### 新ロジック（全体最新）

同一 `supplier_channel_id` の全メッセージに対して `ROW_NUMBER() OVER (PARTITION BY product_id, condition_id ORDER BY received_at DESC, computed_at DESC)` でランク付けし、各ペアの1位のみ TRUE、残りすべてを FALSE にする。

再解析やどのジョブからの実行でも常に「全体の中で最新」が TRUE になる。

## 関連ADR

- `docs/adr/ADR-158-product-level-supersession.md`（ADR-158 is_current 設計）

## 触らない範囲

- `_merge_supplier_products()` の呼び出し元（行1565）の関数呼び出し自体は変更なし
- 他の関数・ファイルは一切変更しない
