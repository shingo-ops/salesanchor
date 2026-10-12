# recon: 生成型の横展開（便C-4、OwnInventoryPage）

- 基準: origin/main `2cdbcc9b3`（BASE_OK。worktree 作成直後の HEAD と一致）
- 親テーマ: cross-dept-integrity-foundation（PR #3942）。根拠: ADR-1005。前提の便C-2（PR #4009）は本番反映済み。
- 調査: Sonnet（読み取りとローカル実行）。判断: Opus

## 事実
- 生成の配線は #4009 で入っている。`frontend/package.json:50-51`（predev・prebuild）と `.github/workflows/frontend-check.yml:30`（tsc 前の生成 step）。この便では触らない。
- 対象画面の API:
  - `frontend/src/pages/inventory/OwnInventoryPage.tsx:44` の GET /own-inventory（`OwnInventoryRow[]`）
  - POST /own-inventory/{id}/{kind} は戻り値を使っていない。この便では変えない。
- backend: `backend/app/routers/own_inventory.py:58-61` で response_model は `list[OwnInventoryResponse]`。型の定義は `backend/app/schemas/own_inventory.py:42`。
- 手書き型は `OwnInventoryRow`（変更前は `frontend/src/pages/inventory/OwnInventoryPage.tsx:16`）。`ActionKind` と `PendingAction` は画面内だけで使う型なので対象外。
- 照合表（手書き型と生成型 `OwnInventoryResponse`、14フィールド。比べた項目は名前・型・null・省略）:

| フィールド | 手書き | 生成 | 一致 |
|---|---|---|---|
| id | number | number | 一致 |
| tenant_id | number | number | 一致 |
| product_id | number | number | 一致 |
| physical_qty | number | number | 一致 |
| reserved_qty | number | number | 一致 |
| available_qty | number または null | number または null | 一致 |
| unit_price | number または null | string または null | 違う |
| condition | string または null | string または null | 一致 |
| status | string | string | 一致 |
| note_ja | string または null | string または null | 一致 |
| note_en | string または null | string または null | 一致 |
| antique_ledger_id | number または null | number または null | 一致 |
| created_at | string | string | 一致 |
| updated_at | string | string | 一致 |

  - 省略できるフィールドの違いは無い（両方とも全フィールドが必須）。
- 違いは1つだけ。`unit_price` は、手書きが number、実際の形が string（backend が `Decimal`、`backend/app/schemas/own_inventory.py:49`）。
  - 画面で使っている: `frontend/src/pages/inventory/OwnInventoryPage.tsx:139` の `row.unit_price.toLocaleString()`。
  - 型を string にしても `toLocaleString()` は string に対して型エラーにならず、tsc は通る。実行時の値は元から string なので、別名にしても表示は変わらない。表示ロジックは変更しない。
  - 注意（既存の挙動）: 実際の値が string のため、`toLocaleString()` は桁区切りにならず、値がそのまま表示される。数値として桁区切りに直す変更は、この便の範囲外。
