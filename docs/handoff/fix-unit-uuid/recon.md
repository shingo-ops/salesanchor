# recon — fix-unit-uuid（unit_id UUID 型不一致修正）

## 問題の事実

`backend/app/services/tcg_unit_recovery_svc.py:66-115` の `_UNIT_MASTER_ROWS` で、
`unit_id` フィールドが `"UN0001"`〜`"UN0008"` のコード文字列になっていた。

DB の `tenant_004.analysis_results.unit_id` は UUID 型であるため、
`kubun_to_unit` 経由で unit 復旧を実行すると以下のエラーが発生:

```
invalid input syntax for type uuid: "UN0002"
```

## 影響範囲（実測）

- 6 ジョブでエラー発生（R-1 API 再解析時）:
  - `8892d45c-803e-4bcd-a272-9058c2725ac1`
  - `0e220185-5643-4849-bc3d-7aca348c6c5e`
  - `e5d6a3c3-14b4-491d-b4db-5806311ef41c`
  - `ef572b32-1914-4ede-87de-dc1cf1dcafe3`
  - `77fb62b6-cd6b-4e4a-b27a-1b519db3dabd`
  - `43f92906-c568-41b6-ade7-b20c34e583c8`
- 6 ジョブ合計 131 行のうち 26 行が現行配信 707 件に未反映

## DB の正値（実測 2026-09-04）

`tenant_004.tcg_unit_master` から取得:

| code | unit_id（UUID） | canonical |
|------|----------------|-----------|
| UN0001 | c5a6371d-5296-45a3-913f-72f6315b4bb9 | Case |
| UN0002 | 8e980434-eeff-4233-be5c-bcd0ba1db992 | Box |
| UN0003 | 225a8677-b1eb-4cb4-b2f0-4df5827d899a | Pack |
| UN0004 | fb707fad-d096-439c-b1af-d411a4a7d18a | Piece |
| UN0005 | 9fffcb6c-9a77-4e89-b862-6c9868cfaf34 | Set |
| UN0006 | 07724cb8-085b-4ed0-b852-84ee20ce9f3c | 本 |
| UN0007 | 0df9b0c2-ac24-44b6-8dad-a10477c11b76 | 点 |
| UN0008 | 599b72ae-0aa2-4b76-b957-e7ce93369bf5 | 個 |

## 修正対象ファイル

- `backend/app/services/tcg_unit_recovery_svc.py:66-115` — `_UNIT_MASTER_ROWS`
