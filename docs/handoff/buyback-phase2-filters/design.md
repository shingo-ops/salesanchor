# design: buyback-phase2-filters

**対象ADR**: ADR-157
**recon**: docs/handoff/buyback-phase2-filters/recon.md

## 変更概要（4変更）

### Change 1: Backend — sort/order params + counts_by_game

| 変更箇所 | 変更前 | 変更後 |
|---------|-------|-------|
| `buyback_prices.py:120-121` | limit/offset のみ | sort/order Query params を追加 |
| `buyback_prices.py:132-141` | なし | ホワイトリスト辞書 `_SORT_WHITELIST` + sort_col/sort_dir 決定 |
| `buyback_prices.py:179` | `ORDER BY p.card_game, p.shop_code, p.product_name` | `ORDER BY {sort_col} {sort_dir} NULLS LAST` |
| `buyback_prices.py:66-69` | `total: int` のみ | `counts_by_game: dict[str, int]` フィールド追加 |
| `buyback_prices.py:209-228` | なし | counts_by_game サブクエリ（shop/product_type フィルタのみ反映） |

**SQLインジェクション対策**: sort_col はホワイトリスト外入力に対し `l.price_s` にフォールバック。

### Change 2: Frontend — product_type フィルタ

| 変更箇所 | 変更前 | 変更後 |
|---------|-------|-------|
| `BuybackPricesPage.tsx:108` | なし | `const [productType, setProductType] = useState<string>("")` |
| `BuybackPricesPage.tsx:135` | なし | `if (productType) params.append("product_type", productType)` |
| `BuybackPricesPage.tsx:155` | `[page, shop, cardGame, sortKey, sortDir, t]` | `productType` を追加 |
| `BuybackPricesPage.tsx:280-288` | なし | `productTypeOptions` 配列定義 |
| `BuybackPricesPage.tsx:335-340` | shop SelectControl のみ | product_type SelectControl を隣に追加 |

### Change 3: Frontend — タブ件数 + 空タブ非表示

| 変更箇所 | 変更前 | 変更後 |
|---------|-------|-------|
| `BuybackPricesPage.tsx:48-51` | `total: number` のみ | `counts_by_game: Record<string, number>` 追加 |
| `BuybackPricesPage.tsx:110` | なし | `const [countsByGame, setCountsByGame] = useState<Record<string, number>>({})` |
| `BuybackPricesPage.tsx:143` | なし | `setCountsByGame(res.counts_by_game ?? {})` |
| `BuybackPricesPage.tsx:289-307` | 全ゲームタブを固定表示 | count > 0 のゲームのみ + "全タイトル" 常時表示 |

### Change 4: i18n keys

追加キー: `allTypes / typePack / typeCarton / typeShrink / typeNoShrink / typeSpecialSet / typeFilter`
対象ファイル: `frontend/src/locales/ja.json`, `frontend/src/locales/en.json`

## 触るファイル一覧

- `backend/app/routers/buyback_prices.py` — sort/order/counts_by_game 追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx` — フィルタ/タブ更新
- `frontend/src/locales/ja.json` — i18n キー追加
- `frontend/src/locales/en.json` — i18n キー追加
- `docs/handoff/buyback-phase2-filters/recon.md` — 本ドキュメント
- `docs/handoff/buyback-phase2-filters/design.md` — 本ドキュメント

## 守り手
- `backend/app/routers/buyback_prices.py` — buyback API エンドポイント
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx` — buyback 画面

## KGI/KPI（検証方法）

| 基準 | 検証方法 |
|-----|---------|
| `GET /buyback-prices?sort=price_a&order=asc` が price_a 昇順で返る | APIレスポンス items[0].price_a ≤ items[1].price_a |
| `GET /buyback-prices` レスポンスに `counts_by_game` キーが存在する | JSON に `counts_by_game: { "pokemon": N, ... }` が含まれる |
| `GET /buyback-prices?product_type=BOX` が BOX のみ返す | items の全行 product_type === "BOX" |
| 画面で product_type フィルタが機能する | "BOX" 選択後に非BOX行が消える |
| 件数0のゲームタブが非表示になる | データが0件のゲームのタブが DOM に存在しない |

## 外部・過去事例の参照と我々への応用
- FastAPI Query params ホワイトリストパターン: SQLAlchemy + text() + f-string ホワイトリスト（本番コードベース既存パターン踏襲） → 我々への応用: `_SORT_WHITELIST` 辞書でフォールバック付き安全 sort 実装
- React state + useEffect deps パターン: 既存 shop/cardGame フィルタと同一パターン → 我々への応用: productType を同じ deps 配列に追加し一貫性を保つ

## 戻し方
- git revert このブランチのコミット、または PR をクローズ
- DB マイグレーションなし → 戻しにロールバック不要
