# design — SA-02 残課題 R1/R2: conversation_logs contact_id / company_id 補完

**仕事名**: SA-02 R1/R2 — conv_log_writer contact_id 追加 + 手動記録 company_id 補完  
**日付**: 2026-06-14  
**対象ADR**: ADR-096, ADR-095, ADR-072, ADR-135  
**担当**: Hikky-dev

---

## 1. Why（なぜやるか）

SA-02 KGI G1 を満たすために:

- **G1a**: `conversation_logs.contact_id` が常に NULL → KPI 計算・絞り込みに使えない
- **G1b**: 手動記録の `conversation_logs.company_id` が NULL → `v_company_stats` VIEW の `conversation_count` / `last_conversation_at` 集計から漏れる

migration は不要（両カラム既存）。コードの INSERT 文に追加するだけ。

---

## 2. What（何を変えるか）

### R1: `write_conversation_log()` に `contact_id` 対応を追加

| 変更 | 内容 |
|------|------|
| 追加ヘルパー | `_get_contact_id_for_lead(db, lead_id)` — `contacts WHERE lead_id=X ORDER BY is_primary_contact DESC, id ASC LIMIT 1` |
| シグネチャ変更 | `contact_id: int | None = None` オプション引数を追加（後方互換） |
| 自動解決ロジック | `contact_id` が None かつ `lead_id` がある場合、`_get_contact_id_for_lead` で補完 |
| INSERT 追加 | `contact_id` 列を INSERT に追加 |

**基準**: 呼び出し元が `contact_id` を明示する場合はそちらを優先（「渡せば確定」原則）。

### R2: `POST /leads/{lead_id}/conv-logs` に `company_id` 自動補完を追加

| 変更 | 内容 |
|------|------|
| import 追加 | `from app.services.conv_log_writer import _get_company_id_for_lead` |
| 自動補完 | INSERT 前に `company_id = await _get_company_id_for_lead(db, lead_id)` |
| INSERT 追加 | `company_id` 列を INSERT に追加 |
| audit_log 追加 | `new_data` に `company_id` を追加 |

---

## 3. How（どう実装するか）

### R1 実装詳細

```python
# 新ヘルパー（_get_company_id_for_lead の直後に配置）
async def _get_contact_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
    result = await db.execute(
        text("""
            SELECT id FROM contacts
            WHERE lead_id = :lead_id
            ORDER BY is_primary_contact DESC, id ASC
            LIMIT 1
        """),
        {"lead_id": lead_id},
    )
    row = result.first()
    return int(row[0]) if row else None

# write_conversation_log: シグネチャ追加
async def write_conversation_log(
    db, *, tenant_id, lead_id, channel_type, channel_identity=None,
    direction, sender=None, content_text=None, external_message_id=None,
    raw_payload=None, occurred_at,
    contact_id: int | None = None,   # ← 追加
) -> int | None:

# 自動解決（company_id 解決の直後）
    resolved_contact_id = contact_id
    if resolved_contact_id is None and lead_id:
        resolved_contact_id = await _get_contact_id_for_lead(db, lead_id)

# INSERT に contact_id 追加
```

### R2 実装詳細

```python
# conv_logs.py import 追加
from app.services.conv_log_writer import _get_company_id_for_lead

# create_conv_log: 重複チェック後・INSERT 前に追加
    company_id = await _get_company_id_for_lead(db, lead_id)

# INSERT: company_id 追加
```

---

## 4. 弊害・リスク

| リスク | 対処 |
|--------|------|
| `_get_contact_id_for_lead` が contacts 未作成リードで None を返す | NULL 許容列なので問題なし |
| `_get_company_id_for_lead` は deals テーブルを SELECT → 手動記録でも1クエリ増加 | 1 SELECT のみ。パフォーマンス許容範囲 |
| シグネチャ変更で呼び出し元が壊れる | `contact_id` はオプション引数（default=None）。後方互換あり |

---

## 5. 対象外（R3）

- `v_company_stats` VIEW の再確認（R3）: R1/R2 修正後の本番データ確認
- テスト追加 for webhook.py / dm_writer.py 呼び出しパス（呼び出し元はデフォルト None で後方互換）

---

## 6. 検証方法

| 基準 | 検証方法 |
|------|---------|
| `write_conversation_log` に `contact_id` パラメータがある | `inspect.signature()` テスト |
| `contact_id` が INSERT される | SQL 文の grep / mock テスト |
| `lead_id` あり・`contact_id` 省略時に自動補完される | `_get_contact_id_for_lead` が呼ばれることを mock で確認 |
| `lead_id=None` で両ヘルパーが呼ばれない | mock.assert_not_called |
| 手動記録 INSERT に `company_id` が含まれる | mock の call_args 確認 |
| audit_log に `company_id` が含まれる | `record_audit_log` の call_args 確認 |

---

## 7. 外部事例

ADR-096 §4「contact 粒度での集計」要件。`v_company_stats` は `LEFT JOIN conversation_logs cl ON cl.company_id = c.id` で集計しており、`company_id=NULL` のレコードは除外される。既存の webhook 経由ログは `_get_company_id_for_lead` で補完済みのため R2 の補完により手動記録も同等の挙動になる。

---

_作成: Hikky-dev / 2026-06-14_
