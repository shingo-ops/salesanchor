# recon — inventory-single-fetch

**仕事名**: inventory-single-fetch  
**日付**: 2026-10-14  
**対象ADR**: ADR-099（在庫モデル。FEATURE-INDEX で「在庫 / inventory」を検索）。画面の読込順序に関する ADR は見つからず  
**実測時の origin/main**: 74acffd889ccb2b0d73ffaa77e11e940e57a2ea8  
**担当**: Sonnet（Opus カード CARD-inventory-single-fetch.md に基づく）

---

## file:line 引用表（変更前）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/inventory/InventoryPage.tsx:131` | filtersLoaded の state（初期値 false） |
| `frontend/src/pages/inventory/InventoryPage.tsx:165` | load（useCallback）の開始。依存配列にフィルタ系 state を含む |
| `frontend/src/pages/inventory/InventoryPage.tsx:198` | api.get(/inventory?...) の直後に無条件で setItems（古い応答の無視なし） |
| `frontend/src/pages/inventory/InventoryPage.tsx:213` | useEffect で load を無条件に呼ぶ（フィルタ未読込でも1回目が飛ぶ） |
| `frontend/src/pages/inventory/InventoryPage.tsx:244` | 保存済みフィルタ GET /me/inventory-filters |
| `frontend/src/pages/inventory/InventoryPage.tsx:261` | finally で setFiltersLoaded(true)（取得失敗でも true になる） |
| `frontend/src/pages/inventory/InventoryPage.tsx:268` | 保存（PATCH）の effect。今回は触らない |
| `frontend/src/pages/inventory/InventoryPage.settings.test.tsx:1` | 既存テスト（vitest・api を vi.mock する流儀） |
| `docs/adr/FEATURE-INDEX.md:18` | 在庫関連 ADR の索引（ADR-099 / 093 / 014） |

## 事実

- 本番 nginx 実測（カード記載）: 1回の訪問で同じ URL の GET /inventory が2回（21:03:51 と 21:04:03）。
- 原因: 表示直後に既定値で load が走り、保存済みフィルタ到着で Set が作り直され load が再生成されて2回目が走る。
