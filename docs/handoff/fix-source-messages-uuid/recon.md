# recon: fix-source-messages-uuid

## 調査日時
2026-09-24

## 問題の所在

### バックエンドスキーマ
`backend/app/schemas/central_masters.py:448`

```python
class SupplierSourceMessage(BaseModel):
    id: int          # ← DB は uuid 型なので Pydantic バリデーションエラー
    raw_text: str
    created_at: datetime
```

### エンドポイント
`backend/app/routers/super_admin_suppliers.py:928-955`

`GET /super-admin/suppliers/{supplier_id}/source-messages`

SQL で `sm.id` を SELECT して dict に格納し `SupplierSourceMessage` に渡す。
`source_messages.id` は DB 上 uuid 型 → `int` スキーマが拒否して 500。

### フロントエンド型
`frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:49-53`

```typescript
interface SupplierSourceMessage {
  id: number;  // ← UUID は string として渡される
  raw_text: string;
  created_at: string;
}
```

`message.id` の使用箇所: `messages[messageIndex].created_at` / `.raw_text` のみ参照。
キーとして `id` は使われていないため `string` 変更で挙動変化なし。

## 既存 ADR 検索結果

`git grep -i "source_messages" docs/adr/` → 該当なし（ADRなし・スキーマ型修正のみ）

## 影響範囲

- 変更ファイル: 2件
- migrations: 不要（DB スキーマ変更なし）
- 他エンドポイントへの影響: なし（`SupplierSourceMessage` スキーマは当該エンドポイントのみが使用）
