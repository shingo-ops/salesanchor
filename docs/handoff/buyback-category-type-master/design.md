# design: buyback-category-type-master

## KGI

カテゴリタブが type_master.name_ja で動的表示され、フロントのハードコード（CATEGORY_LABELS 6件、CardGame 固定値リスト）が完全排除される。

## recon 参照

docs/handoff/buyback-category-type-master/recon.md 参照。

## ADR 参照

ADR-157（買取相場機能設計・SSOT方針）。

## 変更概要

### バックエンド (backend/app/routers/buyback_prices.py)

1. category パラメータを str | None から int | None（type_master.id）に変更
2. カテゴリ別件数クエリを bsp.card_game から p.work_id, tm.name_ja（type_master JOIN）に変更（swing/non-swing 両variant）
3. counts_rows を fetchall し counts_by_category（work_id str → count）と category_names（work_id str → name_ja）を分離生成
4. カテゴリフィルタを bsp_f.card_game = :category から p.work_id = :category（整数直接比較）に変更
5. SELECT の category フィールドを subquery から p.work_id に変更
6. items の dict key を "category" から "work_id" に変更
7. レスポンスに category_names を追加

### フロントエンド

- buybackTypes.ts: ByProductItem.category: string を work_id: number に変更
- buybackTypes.ts: ByProductResponse に category_names: Record<string, string> 追加
- buybackTypes.ts: CardGame を "all" | string（オープン型）に変更
- BuybackByProductPage.tsx: CATEGORY_LABELS ハードコードブロック削除
- BuybackByProductPage.tsx: categoryNames state 追加、API レスポンスから設定
- BuybackByProductPage.tsx: タブラベルを categoryNames[key] ?? key で動的解決

## 検証テーブル

| 基準 | 検証方法 |
|------|---------|
| カテゴリタブが type_master.name_ja で表示される | 本番でタブラベルをDBの SELECT name_ja FROM type_master WHERE id = work_id と照合 |
| CATEGORY_LABELS ハードコードが消えている | grep -r "CATEGORY_LABELS" frontend/src/ → 0件 |
| 重複タブが解消 | タブ一覧が中分類マスタID単位で1件ずつ表示される |
| カテゴリフィルタが work_id ベースで動作 | タブクリック → URL ?category=<int> → テーブルが正しく絞り込まれる |
| ruff lint pass | ruff check backend/app/routers/buyback_prices.py → All checks passed! |

## 外部・過去事例の参照と我々への応用

該当なし（内部SSOTへの統一作業）。同様のパターンとして、type_master をタブ表示に使う設計は既に analysis_rules 等で採用済み。

## 維持の仕組み

- type_master.id は products.work_id の FK制約により整合性保証
- CI ruff + TypeScript コンパイルチェック
- type_master はDBマスタテーブル1箇所のみ（SSOT）。新カテゴリ追加はDBレコード追加のみでフロント変更不要
