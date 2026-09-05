# DIST-R3 recon: received_at 空欄・時刻ずれ

## 調査日: 2026-09-05

---

## 実測事実

### GAS の latest24Iso_() が JST 文字列を返す（タイムゾーンなし）

`sqr06_devsnapshot/Latest24LineImport.gs:18`

```javascript
function latest24Iso_(date, time) { return date + ' ' + ('0' + time).slice(-5) + ':00'; }
```

- `date` は LINE エクスポートの日付行（`2026.09.03 水曜日` など）をハイフン変換したもの（`:57`）
- 出力例: `"2026-09-03 01:19:00"` — タイムゾーン情報なし・JST のローカル時刻文字列

### 手動スクリプト50件は JST aware で保存済み（正しい見本）

`backend/tcg_migration/MIGRATION_LOG.md:369-409`

```
| 新規分（本スクリプト） | 50件 | JST タイムスタンプあり |
```

```python
received_at = datetime.strptime(dt_str, "%Y.%m.%d %H:%M:%S").replace(tzinfo=JST)
```

DB には `01:19:00+09:00` として保存済み。配信 SQL の `AT TIME ZONE 'Asia/Tokyo'` で `01:19:00 JST` として正確に表示される。

### 移行306件は received_at が元から NULL（GAS側にデータなし）

`backend/tcg_migration/MIGRATION_LOG.md:256,268`

- `tenant_004.source_messages` の `received_at` カラムは移行時点で全306件 NULL
- GAS スプレッドシートにも `received_at` に相当するデータなし
- `ingest_to_prod.py` はソース側の値をそのままコピーするため NULL が伝播

### tcg_line_import_svc.py:435 が UTC として保存していた（修正前）

`backend/app/services/tcg_line_import_svc.py:433-436`（修正前）

```python
received_at_dt = datetime.strptime(
    entry["received_at"], "%Y-%m-%d %H:%M:%S"
).replace(tzinfo=timezone.utc)   # ← UTC として保存（誤り）
```

GAS から `"2026-09-03 01:19:00"`（JST）が来ても、`+00:00` として DB に保存。

### 配信 SQL の AT TIME ZONE 変換

`backend/app/services/tcg_distribution_svc.py:210-211`

```sql
COALESCE(TO_CHAR(sm.received_at AT TIME ZONE 'Asia/Tokyo',
                 'YYYY-MM-DD HH24:MI:SS'), '')  AS posted_at,
```

`+00:00` で保存されたデータに `AT TIME ZONE 'Asia/Tokyo'` を適用すると **+9時間ずれ** て表示される。

---

## 案 B（配信 SQL 変更）が不可な理由

手動スクリプト分50件は `+09:00`（正しい）で保存済み。
`AT TIME ZONE 'Asia/Tokyo'` を外すと、これら50件が逆に `-9時間` ずれる。

案 B は既存の正しいデータを壊すため単独では不可。

---

## 修正対象

| ファイル | 変更箇所 | 変更内容 |
|---|---|---|
| `backend/app/services/tcg_line_import_svc.py:24` 付近 | JST 定数追加 | `JST = timezone(timedelta(hours=9))` |
| `backend/app/services/tcg_line_import_svc.py:435` | tzinfo 変更 | `.replace(tzinfo=timezone.utc)` → `.replace(tzinfo=JST)` |
| `backend/tests/test_tcg_line_import.py` | テスト追加 | JST 定数・変換・DB パラメータの3件 |

配信 SQL（`tcg_distribution_svc.py`）は変更しない。
