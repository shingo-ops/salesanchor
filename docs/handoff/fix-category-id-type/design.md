# design: product_category_id type mismatch fix

## recon 参照
docs/handoff/fix-category-id-type/recon.md

## ADR 参照
- ADR-155 Phase 3B: product_category_id → public.tcg_product_categories (INTEGER PK) 移行済み
- ADR-156 Phase 3A: product_kind_id → public.product_kinds (INTEGER PK) 移行済み

## 変更方針

### Backend
`ProductDetailUpdate.product_category_id: UUID | None` → `int | None`

根拠:
- DB カラム `public.products.product_category_id` は INTEGER（ADR-155 で移行済み）
- サービス側 SQL はすでに CAST なしで整数として扱っている
- manufacturer_id は UUID のまま変更しない（TCG_SCHEMA.tcg_manufacturers は UUID PK）

### Frontend
`product_category_id: draft.product_category_id || null` → `product_category_id: draft.product_category_id ? Number(draft.product_category_id) : null`

根拠:
- Select コンポーネントは id を文字列として保持する
- product_kind_id・work_id は同じパターンで Number() 変換済み（line 134）
- 文字列のまま送ると Pydantic v2 が int フィールドを拒否する（strict モードでなくても型不一致はエラー）

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| カテゴリーIDを変更して保存しても 422 エラーが発生しない | ブラウザで商品詳細ドロワーを開き、product_category_id を変更して保存 → 200 レスポンス |
| manufacturer_id の変更が引き続き正常動作する | ブラウザで manufacturer_id を変更して保存 → 200 レスポンス |
| Pydantic バリデーションエラーが消える | backend ログに `validation error for ProductDetailUpdate` が出ない |

## 影響範囲

- 呼び出し元: `PUT /api/v1/tcg/products/detail/{product_code}` のみ
- 変更ファイル: 2 ファイル（router + frontend コンポーネント）
- 削除ファイル: なし

## 外部・過去事例の参照と我々への応用

Pydantic v2 では `int` フィールドに文字列を渡すと `ValidationError` を返す（strict デフォルトでなくても JSON からの文字列は拒否される）。FastAPI の公式ドキュメントでも「JSON body の型は Python 型と一致させる」ことが前提とされている。本件は ADR-155 の DB 移行後にルータースキーマの追従が漏れた典型的なドリフト。同パターンの再発防止は `## 維持の仕組み` 参照。

## 維持の仕組み

守り手: code-reviewer（ルーター変更時に PUBLIC_INTEGER_LOOKUPS と型の一致を確認）

- サービス側（`backend/app/services/tcg_product_detail_svc.py`）の `PUBLIC_INTEGER_LOOKUPS` dict と `LOOKUPS` dict を見れば、どのフィールドが INTEGER か UUID かが一目で分かる。ルーター変更時はこの dict と照合する。
- フロントエンド `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx` line 134 のパターン（`Number()` 変換）を分類フィールド追加時の標準とする。

## 戻し方
git revert で本 PR コミットを打ち消す。DB スキーマ変更なし。
