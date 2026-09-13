# recon: sup-register-15

**日付**: 2026-09-05
**対象ADR**: ADR-154

---

## 1. 変更対象ファイル

| ファイル | 役割 |
|---|---|
| `migrations/20260905_120000_register_15_suppliers_t004.sql` | 仕入元 15件 + LINE チャンネル行の冪等登録 |
| `scripts/run_all_migrations.sh` | 上記 migration の実行登録 |

---

## 2. tcg_suppliers テーブル構造確認

引用: `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:99-110`

```sql
CREATE TABLE IF NOT EXISTS %I.tcg_suppliers (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code       VARCHAR(20) NOT NULL,
    name       TEXT        NOT NULL,
    is_active  BOOLEAN     NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (code)
);
```

登録カラム: `code` / `name` / `is_active`（id と created_at は DB 自動付与）

---

## 3. supplier_channels テーブル構造確認

引用: `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:192-199`

```sql
CREATE TABLE IF NOT EXISTS %I.supplier_channels (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID        NOT NULL REFERENCES %I.tcg_suppliers (id) ON DELETE CASCADE,
    channel     VARCHAR(50) NOT NULL,
    external_id TEXT,
    is_active   BOOLEAN     NOT NULL,
    CONSTRAINT uq_supplier_channels_channel_external UNIQUE (channel, external_id)
);
```

**UNIQUE (channel, external_id) と NULL の挙動確認**:
PostgreSQL は UNIQUE 制約において `NULL ≠ NULL` と扱うため、
`(channel='line', external_id=NULL)` 行は複数挿入しても制約違反にならない。
`ON CONFLICT (channel, external_id) DO NOTHING` はこのケースに対して機能しないため、
`NOT EXISTS` サブクエリで冪等性を担保する（本 migration で採用）。

---

## 4. 既存コードでの channel='line' 使用箇所

引用: `backend/app/services/tcg_line_import_svc.py:401`

```python
AND sc.channel = 'line'
```

本 migration で登録する `channel='line'` 行は、LINE エクスポート取り込み時に
`supplier_channels` を検索する既存ロジックと整合する。

---

## 5. 後日照合予定（統合候補メモ）

**後日、既存仕入元との同一性を照合して統合する予定。**

現時点での候補（確定ではなく要照合）:

| 新規登録（本PR） | 統合候補（既存） | 照合根拠 |
|---|---|---|
| SP0189 funスタッフ | 株式会社fun labo（既存コード不明） | 社名略称の可能性 |
| SP0197 Kei | けい（既存コード不明） | 読みが同一 |
| SP0202 大知 | たいち（既存コード不明） | 読みが同一 |
| SP0199 oyama / SP0200 やまちゃん | — | 同一人物の可能性（oyama = 山姓 + やまちゃん） |

照合は PO（Shingo）と DB データを突き合わせて判断。統合する場合は別カードで対応。

---

## 6. ALTER なし確認

`migrations/` 配下の全 `.sql` ファイルに `ALTER TABLE.*supplier_channels` / `ADD COLUMN.*supplier` の記述なし（grep 確認済み）。既存 15件以降の code 連番として SP0188〜SP0202 を採番。
