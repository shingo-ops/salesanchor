# 買取スクレイパー不具合修正 — 設計

## 目的

ADR-157 Phase 1 で実装した買取スクレイパーの致命的不具合3件を修正し、シンソク・ホムラ両店舗からデータを正常に取得できるようにする。

## 対象と対象外

### 対象
- `backend/app/services/buyback_scraper/shinsoku.py` — brands パース修正 + DB ブランドマッピング追加
- `backend/app/services/buyback_scraper/homura.py` — 価格パーサー全面改修

### 対象外
- API エンドポイント（変更なし）
- フロントエンド（変更なし）
- DB スキーマ（変更なし）
- Celery タスク（変更なし）

## 変更内容

### 修正1: shinsoku.py brands パース

| 基準 | 検証方法 |
|------|----------|
| brands API から 5 ブランドが取得できる | `data.get("data", {}).get("brands", [])` が 5 要素のリストを返す |
| ドラゴンボール商品が取得される | `_BRAND_TO_GAME` に `"DB": "dragonball"` が存在する |

**変更前**: `data.get("data", [])` → dict が返りイテレーション失敗
**変更後**: `data.get("data", {}).get("brands", [])` → ブランドリストが正しく返る

### 修正2: shinsoku.py DB ブランドマッピング

**変更前**: `"ドラゴンボール": "dragonball"` のみ
**変更後**: `"DB": "dragonball"` を追加（API の `name` フィールドと一致）

### 修正3: homura.py 価格パーサー改修

| 基準 | 検証方法 |
|------|----------|
| 商品 ID が取得できる | `button[data-product-id]` から取得 |
| 商品名が取得できる | `button[data-product-name]` から取得 |
| 価格が取得できる | `button[data-product-price]` から int 変換 |
| 重複排除が機能する | `external_id` による重複チェック維持 |

**変更前**: `<a>` タグ内テキストノード検索（価格が `<a>` 外にあるため常に null）
**変更後**: `button[data-product-id]` の data 属性から全情報を取得

### 副次変更

- `_PRICE_RE` 定数と `import re` を削除（使用箇所なし）

## リスクと対処

| リスク | 対処 |
|--------|------|
| ホムラがボタンの data 属性を変更する | サイト構造変更リスクは元のテキスト解析も同等。data 属性のほうがむしろ安定（Rails のフォームインフラ） |
| シンソク API 構造が変更される | `has_more` / `items` の構造は変更なし。brands のネスト修正のみ |

## 外部・過去事例の参照と我々への応用

バグ修正のため外部事例は不要。類似の先例として、BeautifulSoup の `find_all(string=...)` は要素内のテキストノードのみを対象とし、子要素には適用されないという既知の制約が今回の根本原因。公式ドキュメント（https://beautiful-soup-4.readthedocs.io/en/latest/#the-string-argument）にも記載があり、data 属性ベースのパース（`soup.find_all("button", attrs={"data-product-id": True})`）への切り替えが実績ある回避策。

## 受入条件

1. デプロイ後、Celery beat の次回実行で buyback_shop_products テーブルにシンソク・ホムラ両方のレコードが作成される
2. buyback_price_logs テーブルに価格データ（price_s が null でない）が記録される
3. フロントエンドの買取相場ページでデータが表示される

## 維持の仕組み

守り手: Hikky-dev（スクレイパー改修時にサイト HTML 構造を再確認する）

- シンソク: brands API のレスポンス構造変化は `_fetch_brands` 内の `logger.info` ログで件数を確認
- ホムラ: `button[data-product-id]` の欠落は `_parse_products` の戻り値が空になることで検知（Celery タスクのログに件数が出力される）

## recon 相互参照

`docs/handoff/fix-buyback-scraper-bugs/recon.md`
