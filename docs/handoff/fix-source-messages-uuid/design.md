# design: fix-source-messages-uuid

## KGI

`GET /super-admin/suppliers/{id}/source-messages` が 500 を返さず 200 でデータを返す。

## 変更設計

### backend/app/schemas/central_masters.py

変更前:
```python
from datetime import date, datetime
from typing import Optional
```

変更後:
```python
from datetime import date, datetime
from typing import Optional
from uuid import UUID
```

変更前:
```python
class SupplierSourceMessage(BaseModel):
    id: int
```

変更後:
```python
class SupplierSourceMessage(BaseModel):
    id: UUID
```

### frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx

変更前:
```typescript
interface SupplierSourceMessage {
  id: number;
```

変更後:
```typescript
interface SupplierSourceMessage {
  id: string;
```

## 触らない範囲

- `super_admin_suppliers.py` のSQL・ロジック: 変更不要（DBが uuid を返す、Pydantic が UUID として受け取るだけ）
- その他エンドポイント: 影響なし

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| エンドポイントが 200 を返す | 本番で `GET /super-admin/suppliers/{id}/source-messages` にアクセスして 200 確認 |
| 500 エラーが消える | 本番ログで source-messages 500 エラーが出ないことを確認 |

## 外部事例

Pydantic v2 の UUID 型サポート: `uuid.UUID` を型アノテーションに使用すると UUID 文字列を自動変換する（公式ドキュメント準拠）。

## 弊害・リスク

なし（スキーマ型の正規化のみ・DB変更なし・APIレスポンスの `id` フィールドが UUID 文字列で返るのは元々そのはずだった）
