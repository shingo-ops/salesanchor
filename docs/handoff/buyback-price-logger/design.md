# design: buyback-price-logger (ADR-157 Phase 1)

## KGI

外部買取店（シンソク / 買取ホムラ）の買取価格が自動取得されDBに蓄積され、
UIの買取相場ページで閲覧可能になる。

## KPI・検証方法

| 基準 | 検証方法 |
|------|---------|
| マイグレーション適用後に buyback_shop_products / buyback_price_logs テーブルが存在する | `\dt public.buyback*` で確認 |
| シンソクスクレイパー実行後 buyback_price_logs に5件以上レコードが挿入される | `SELECT count(*) FROM public.buyback_price_logs WHERE shop='shinsoku';` |
| 買取ホムラスクレイパー実行後 buyback_price_logs に5件以上レコードが挿入される | `SELECT count(*) FROM public.buyback_price_logs WHERE shop='homura';` |
| /buyback-prices ページが表示され DataTable にデータが表示される | ブラウザで画面確認 |
| 商品クリックで価格推移グラフ（recharts）が Drawer に表示される | ブラウザで Drawer 開いて確認 |
| Celery beat が4時間ごとに buyback_scraper タスクを実行する | Flower / Celery ログで確認 |

## アーキテクチャ設計

### DBテーブル設計（public スキーマ）

```sql
-- 外部買取店の商品マスタ
public.buyback_shop_products (
  id SERIAL PRIMARY KEY,
  shop TEXT NOT NULL,           -- 'shinsoku' | 'homura'
  shop_product_id TEXT,         -- 外部ID
  title TEXT NOT NULL,
  brand TEXT,
  category TEXT,
  product_type TEXT,            -- 'BOX' | 'カートン' | 'パック' | 'プロモ'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 買取価格ログ（時系列）
public.buyback_price_logs (
  id SERIAL PRIMARY KEY,
  shop_product_id INT REFERENCES public.buyback_shop_products(id),
  price INT,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);
```

### スクレイパー設計

- `BaseScraper`: 非同期 fetch + retry ロジック
- `ShinsokuScraper`: REST API（JSON レスポンス）、5ブランド × 4種別
- `HomuraScraper`: BeautifulSoup4 で HTML パース、13サブカテゴリ

### Celery タスク

- `beat_schedule`: `buyback-scraper` タスクを4時間ごと（`crontab(minute=0, hour='*/4')`）に実行

### API エンドポイント

- `GET /buyback-prices` — 一覧（フィルタ: shop / brand / product_type）
- `GET /buyback-prices/{id}/history` — 特定商品の価格推移（直近30件）

### フロントエンド設計

- `BuybackPricesPage.tsx`: DataTable（金型）+ フィルタ（SelectControl 金型）
- Drawer（金型）: 商品クリックで recharts LineChart 表示
- ナビゲーション: DesktopShell/MobileShell に「買取相場」リンク追加
- i18n: ja/en 28キー（buybackPrices.* 名前空間）

## 外部・過去事例の参照と我々への応用

- スクレイパー定期実行: 既存 Celery beat パターン（`backend/app/celery_app.py` beat_schedule）を踏襲
- BeautifulSoup4: 既存 `backend/requirements.txt` に未記載のため追加（lxml も同様）
- DataTable + recharts 組み合わせ: `frontend/src/pages/` の既存ページパターン（DesktopShell/Drawer）を踏襲
- ADR-072 reset_tenant_context: buyback_prices ルーターは public スキーマのみ使用するため tenant context リセット不要（write エンドポイントなし）

## 維持の仕組み

- 守り手: Hikky-dev（スクレイパー仕様変更対応）/ Shingo（外部店舗選定・追加判断）
- Celery beat の定期実行ログを Flower で監視
- 外部サイト構造変更でスクレイパー停止した場合: ログから検知 → スクレイパー修正 → 再デプロイ

## 弊害・リスク

- 外部サイトの HTML 構造変更でスクレイパーが停止する可能性
- 外部サイトのレート制限でブロックされる可能性 → retry + exponential backoff で対応
- migrationに public スキーマへの DDL を含むため、PO GO 必須

## 戻し方

- DBロールバック: `DROP TABLE public.buyback_price_logs; DROP TABLE public.buyback_shop_products;`
- コードロールバック: PR をリバートして再デプロイ
