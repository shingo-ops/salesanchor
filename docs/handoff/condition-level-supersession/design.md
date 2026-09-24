# design: condition-level supersession (ADR-158 補正)

## 参照

- recon: `docs/handoff/condition-level-supersession/recon.md`
- ADR: `docs/adr/ADR-158-product-level-supersession.md`

## 問題

ADR-158 の実装では `_merge_supplier_products()` が product_id 単位で照合。
同一商品でコンディションが複数あるとき（例: PM_0001 × Sealed / PM_0001 × Damaged）、
新メッセージに Sealed のみ含まれると、Damaged の旧行まで is_current=FALSE にされる。

## 解決策

照合キーを `product_id` → `(product_id, condition_id)` ペアに変更。
PostgreSQL の `unnest(array[], array[])` を使い EXISTS サブクエリで照合。

## 変更前後

### 変更前

```sql
AND ar_old.product_id = ANY(:product_ids)
```

### 変更後

```sql
AND EXISTS (
    SELECT 1 FROM unnest(:product_ids::integer[], :condition_ids::integer[]) AS t(pid, cid)
    WHERE ar_old.product_id = t.pid AND ar_old.condition_id = t.cid
)
```

## 基準・検証方法

| 基準 | 検証方法 |
|------|----------|
| 新メッセージに含まれないコンディションの旧行が is_current=TRUE のまま残る | 同一商品・複数コンディションのテストデータで _merge_supplier_products() 実行後に確認 |
| 新メッセージに含まれるコンディションの旧行が is_current=FALSE になる | 同上 |

## 外部・過去事例の参照と我々への応用

PostgreSQL unnest(array, array) による並列展開は公式サポート（9.4以降）。
EXISTS + unnest パターンは、複合キーによる IN 句の代替として標準的な手法。
`unnest(a[], b[])` は対応する要素をペアとして返すため、(product_id, condition_id)
の複合照合に適用できる。

## 維持の仕組み

守り手: _merge_supplier_products() の変更時は (product_id, condition_id) ペア照合が
維持されているか確認すること。unnest 引数の順序（product_ids, condition_ids）と
SQL の t(pid, cid) エイリアスの対応が崩れないよう注意。

## 影響範囲

- 変更ファイル: `backend/app/services/tcg_analyzer_svc.py`
- 呼び出し元: `analyze_extraction_job()` のみ（同ファイル内）
- migration なし

## 戻し方

`git revert` で本コミットを戻す（照合が product_id 単位に戻る）。
