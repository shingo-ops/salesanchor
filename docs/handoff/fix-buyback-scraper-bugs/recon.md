# 買取スクレイパー不具合修正 — 現在地把握

## 調査日: 2026-09-22

## 発見した不具合（3件、全て実API/HTML取得で確認済み）

### 不具合1: シンソク — brands API パース誤り（致命的）

- **箇所**: `backend/app/services/buyback_scraper/shinsoku.py:87`
- **現状コード**: `brands: list[dict] = data.get("data", [])`
- **実APIレスポンス**: `{"ok": true, "data": {"brands": [...]}}`
- **原因**: `data.get("data", [])` は `{"brands": [...]}` という dict を返す。イテレートすると dict のキー `"brands"` を走査し、`brand.get("name")` でマッチせず全スキップ
- **影響**: シンソクのデータが**0件**になる
- **根拠**: `curl -s 'https://shinsoku-tcg.com/api/brands?context=yuso'` の実レスポンスで確認

### 不具合2: シンソク — ドラゴンボールのブランド名不一致

- **箇所**: `backend/app/services/buyback_scraper/shinsoku.py:34`
- **現状コード**: `"ドラゴンボール": "dragonball"` のみ
- **実APIレスポンス**: `{"name": "DB", "disp_name": "ドラゴンボール"}`
- **原因**: API の `name` フィールドは `"DB"` だが、マッピングに `"DB"` がない
- **影響**: ドラゴンボール全商品がスキップされる
- **根拠**: brands API の実レスポンスで確認

### 不具合3: ホムラ — 価格パース完全不能（致命的）

- **箇所**: `backend/app/services/buyback_scraper/homura.py:187`
- **現状コード**: `link.find_all(string=_PRICE_RE)` — `<a>` タグ内のテキストノードを検索
- **実HTML構造**: 
  - `<a>` タグには画像と h5（商品名）のみ
  - 価格は `<a>` の外側: `<span class="text-lg font-semibold text-gray-600">¥ 27,000</span>`
  - 祖先チェーン: `span > div > div > div > div > div > turbo-frame > div`
- **原因**: 価格テキストが `<a>` タグ内に存在しないため、`find_all(string=...)` が必ず空を返す
- **影響**: ホムラの価格が**全て null**になる（商品名は h5 から正常に取得できるが価格だけ欠落）
- **根拠**: `curl -s -g 'https://kaitori-homura.com/products?q[product_sub_category_id_eq]=128'` の実HTMLをBeautifulSoupで解析して確認
- **代替手段**: `button[data-product-id]` 要素に `data-product-id` / `data-product-name` / `data-product-price` 属性が全てある（全3ページ×40件/ページで確認済み）

## 価格単位の確認

- シンソク API: `postal_purchase_price_s: 16000000` = サイト表示 `¥16,000,000`（スクリーンショットで一致確認）
- **単位は円**（変換不要）
- ホムラ: `data-product-price: 27000` = サイト表示 `¥27,000`（HTML解析で確認）

## ページネーション確認

- ホムラ: `rel=next` リンクと「次のページ」テキストリンクの両方が存在
- `_has_next_page()` は正常動作（修正不要）
