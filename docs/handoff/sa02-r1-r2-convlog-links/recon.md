# recon — SA-02 残課題 R1/R2: conversation_logs contact_id / company_id 補完

**仕事名**: SA-02 R1/R2 — conv_log_writer contact_id 追加 + 手動記録 company_id 補完  
**日付**: 2026-06-14  
**対象ADR**: ADR-096, ADR-095, ADR-072, ADR-135  
**担当**: Hikky-dev

---

## ADR 検索結果

```
git grep -i "conversation_log\|conv_log" docs/adr/
```

| ADR | 関連 |
|-----|------|
| ADR-096 | 顧客マスタ／CRMデータモデル — conversation_logs 設計の正本 |
| ADR-095 | SSOT・派生値禁止・ポカヨケ原則 |
| ADR-072 | write endpoint の db.commit() 直後に reset_tenant_context() 必須 |
| ADR-135 | develop マージ = 本番投入可の宣言。migration なし・deploy.yml 変更なしのため通常フロー |

---

## 問題の所在（SA-02 KGI実測 2026-06-14 より）

| 残課題 | 未達箇所 | file:line |
|--------|---------|-----------|
| R1 | `write_conversation_log()` が `contact_id` を INSERT しない | `backend/app/services/conv_log_writer.py:29-42`（引数に contact_id なし）/ `conv_log_writer.py:64-91`（INSERT に contact_id なし） |
| R2 | 手動記録 POST が `company_id` を INSERT しない | `backend/app/routers/conv_logs.py:278-296`（INSERT に company_id なし） |

---

## file:line 引用表

### Backend — conv_log_writer.py（R1 対象）

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/services/conv_log_writer.py:29-42` | `write_conversation_log()` 引数定義 — contact_id 引数なし |
| `backend/app/services/conv_log_writer.py:61` | `company_id = await _get_company_id_for_lead(db, lead_id) if lead_id else None` — 流用パターン確認 |
| `backend/app/services/conv_log_writer.py:64-91` | INSERT 文 — contact_id 列なし |
| `backend/app/services/conv_log_writer.py:107-121` | `_get_company_id_for_lead()` — contacts 用 helper の参考実装 |

### Backend — contacts テーブル構造（R1 参照）

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/schemas/contact.py:7` | contacts テーブル列: `id, tenant_id, company_id, contact_code, lead_id, is_primary_contact, ...` |
| `backend/app/schemas/contact.py:100` | `lead_id: int \| None = Field(default=None)` — 出自リード |
| `backend/app/schemas/contact.py:106` | `is_primary_contact: bool = Field(default=False)` — ソート優先度に使用 |

### Backend — conv_logs.py（R2 対象）

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/routers/conv_logs.py:278-296` | 手動記録 INSERT — company_id 列なし |
| `backend/app/routers/conv_logs.py:298-308` | audit_log new_data — company_id なし |

### migration — conversation_logs スキーマ（列確認）

| 引用先 | 確認内容 |
|--------|---------|
| `migrations/20260604_090000_create_conversation_logs.sql` | `contact_id` 列 — 既存（migration 不要） |
|  | `company_id` 列 — 既存（migration 不要） |

### テスト（既存）

| 引用先 | 確認内容 |
|--------|---------|
| `backend/tests/test_conv_log_writer.py:28` | import test: `write_conversation_log`, `_get_company_id_for_lead` |
| `backend/tests/test_conv_log_writer.py:36-45` | signature test: required params set |
| `backend/tests/test_conv_log_writer.py:103-130` | 正常パス: `_get_company_id_for_lead` を patch |
| `backend/tests/test_conv_log_writer.py:169-193` | `lead_id=None` で company helper が呼ばれないこと |
| `backend/tests/test_conv_logs_router.py:98-131` | `test_create_conv_log_manual_channel_success` — company_id 未考慮 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | contacts テーブルに `lead_id` 列はあるか | `backend/app/schemas/contact.py:100` で確認済み | ✅ 解消済み |
| 2 | `is_primary_contact` 列は contacts に存在するか | `backend/app/schemas/contact.py:106` で確認済み | ✅ 解消済み |
| 3 | `conversation_logs` に `contact_id` 列は既存か | `migrations/20260604_090000_create_conversation_logs.sql` 既存確認済み | ✅ 解消済み |
| 4 | migration が必要か | 列は既存。SQL の INSERT 対象列を追加するだけ。migration 不要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
