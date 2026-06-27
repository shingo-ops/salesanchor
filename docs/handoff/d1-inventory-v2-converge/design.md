# design — D-1: public.inventory(B在庫) v2形収束migration

**仕事名**: d1-inventory-v2-converge  
**日付**: 2026-06-24  
**対象ADR**: ADR-143  
**参照recon**: docs/handoff/d1-inventory-v2-converge/recon.md  
**担当**: Terminal CC

---

## §1 問題定義

本番 `public.inventory` は v2形（condition列なし・uq_inventory_offer_key なし）に手当て済みだが、
repo の migration を `run_all_migrations.sh` でフル実行すると旧形（condition列あり・offer_key あり）に
到達する。新基盤立ち上げ時に旧形のテーブルが生成される。

---

## §2 Why/How

| 基準 | 内容 |
|------|------|
| **Why** | 新基盤 / CI が旧形テーブルを生成し本番との論理スキーマ不一致が継続するリスク排除 |
| **How** | 全在庫migration完了後の末尾に冪等収束migrationを1本追加（ADR-143 案ア） |
| **弊害** | 本番は no-op（IF EXISTS）。既存HELD・既存migrationへの変更なし。履歴汚染なし |
| **計画** | migration 1本 + run_all 3行 + ADR 1本 + README.md 自動更新 = 計4ファイル |

---

## §3 実装（署名diffと一致）

### 3-1: `migrations/20260624_140000_converge_inventory_v2.sql`（新規）

```sql
DROP INDEX IF EXISTS uq_inventory_offer_key;
ALTER TABLE public.inventory DROP COLUMN IF EXISTS condition;
```

### 3-2: `scripts/run_all_migrations.sh`（+3行: L451後末尾）

```bash
# D-1: public.inventory(B在庫) を v2形へ収束（冪等・本番no-op）。ADR-143。
run_sql migrations/20260624_140000_converge_inventory_v2.sql
```

### 3-3: `docs/adr/ADR-143-inventory-public-v2-canonical.md`（新規・36行）

Status: Accepted / Date: 2026-06-24

### 3-4: `docs/adr/README.md`（自動生成随伴変更）

`node scripts/generate-adr-index.js` による: カウント143→144 + ADR-143行1行追加。

---

## §4 KPI・検証方法

| KPI | 検証方法 | 期待結果 |
|-----|---------|---------|
| KPI1: フレッシュDB収束 | run_all 全実行後 `\d public.inventory` | 22列・condition列なし・uq_inventory_offer_key なし・uq_inventory_offer_v2 あり |
| KPI2: 2回目 no-op | 同DBで run_all 再実行 | エラー0・差分0（IF EXISTS により冪等） |
| KPI3: migration-guard 緑 | CI チェック2（run_all 登録確認） + チェック5（timestamp 重複なし） | 全チェック通過 |
| KPI4: 本番 no-op | 本番デプロイ後 row 数確認 | 92件のまま変化なし |

---

## §5 外部事例

該当なし（PostgreSQL IF EXISTS 冪等パターンは確立済み標準手法）。

---

## §6 継続リスク

- **HELD migration（030000/050000）温存**: run_all からは引き続き未実行。本番手動GO用履歴として残す。
- **列 ordinal 順**: 追加履歴差により本番と異なり得るが論理スキーマ（列集合・型・制約・INDEX）は一致。
