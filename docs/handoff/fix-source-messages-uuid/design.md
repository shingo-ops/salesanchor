# design: fix-source-messages-uuid

- recon: docs/handoff/fix-source-messages-uuid/recon.md
- 対象ADR: ADR-085

## KGI

`GET /super-admin/suppliers/{id}/source-messages` が 500 を返さず 200 でデータを返す。

## 変更設計

### backend/app/schemas/central_masters.py

変更前:
```
from datetime import date, datetime
from typing import Optional
```

変更後:
```
from datetime import date, datetime
from typing import Optional
from uuid import UUID
```

変更前:
```
class SupplierSourceMessage(BaseModel):
    id: int
```

変更後:
```
class SupplierSourceMessage(BaseModel):
    id: UUID
```

### frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx

変更前:
```
interface SupplierSourceMessage {
  id: number;
```

変更後:
```
interface SupplierSourceMessage {
  id: string;
```

## 触らない範囲

- backend/app/routers/super_admin_suppliers.py のSQL・ロジック: 変更不要（DBが uuid を返す、Pydantic が UUID として受け取るだけ）
- その他エンドポイント: 影響なし

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| エンドポイントが 200 を返す | 本番で GET /super-admin/suppliers/{id}/source-messages にアクセスして 200 確認 |
| 500 エラーが消える | 本番ログで source-messages 500 エラーが出ないことを確認 |

## 外部・過去事例の参照と我々への応用

Pydantic v2 公式ドキュメント（https://docs.pydantic.dev/latest/concepts/types/）では `uuid.UUID` を型アノテーションに使用すると文字列 UUID を自動変換する。同様のパターンは本プロジェクト内の他スキーマ（例: line_messages 関連）でも採用実績あり。今回は同じパターンを source_messages.id に適用する。

## 弊害・リスク

なし（スキーマ型の正規化のみ・DB変更なし・APIレスポンスの id フィールドが UUID 文字列で返るのは元々そのはずだった）

## 維持の仕組み

守り手: CI ruff（Python型チェック）、CI ESLint（TypeScript型チェック）
