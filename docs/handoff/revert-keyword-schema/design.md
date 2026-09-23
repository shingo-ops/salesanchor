# design: revert-keyword-schema

## 相互参照

- recon: docs/handoff/revert-keyword-schema/recon.md
- 関連ADR: ADR-1001（public.products統合方針・共用マスタ参照原則）

## 変更内容

`backend/app/services/tcg_work_reference.py` の `load_work_reference()` における
キーワードクエリを `{schema}` → `public` に戻す（f-string解除含む）。

## 変更前後

```python
# 変更前（PR #3587 の誤変更）
row = session.execute(text(f"""
    ...
    FROM {schema}.product_search_keywords k WHERE k.product_id=p.id),
    ...
    FROM {schema}.product_exclude_keywords k WHERE k.product_id=p.id))
"""))

# 変更後（リバート）
row = session.execute(text("""
    ...
    FROM public.product_search_keywords k WHERE k.product_id=p.id),
    ...
    FROM public.product_exclude_keywords k WHERE k.product_id=p.id))
"""))
```

## 触らない範囲

- `load_work_reference()` のシグネチャ（`schema` 引数は残置、他箇所で使用の可能性）
- その他の関数

## KGI/KPI

| 基準 | 検証方法 |
|------|----------|
| `load_work_reference()` が `public.product_search_keywords` を参照する | コードレビュー（grep確認） |
| 既存テストがパスする | CI緑 |

## 外部・過去事例の参照と我々への応用

PR #3587 が誤ってスキーマをテナント固有に変更した事例。
共用マスタ（public スキーマ）からデータを参照するというアーキテクチャ原則に反する変更であり、
データ側でのコピーが正解（コードパスではなくデータを合わせる）。

## 維持の仕組み

守り手: Shingo（PO）のコードレビュー + CI

スキーマ参照の変更は必ず `public` が正しいかどうかをアーキテクチャレビューする。
