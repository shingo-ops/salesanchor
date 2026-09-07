# design: sup-register-15

参照 recon: docs/handoff/sup-register-15/recon.md

## 目的

GAS 仕入元マスタに存在するが DB 未登録の仕入元 15名（SP0188〜SP0202）を
`tenant_004.tcg_suppliers` と `tenant_004.supplier_channels` に冪等登録する。

ADR-154 準拠: GAS データを正典とし、Python/DB 側を GAS に寄せる。

---

## 方針

- **追加専用**: 既存行の UPDATE/DELETE は行わない（`backend/CLAUDE.md` additive-only 原則）
- **冪等**: `ON CONFLICT (code) DO NOTHING`（tcg_suppliers）+ `NOT EXISTS` サブクエリ（supplier_channels）
- **採番**: 既存最大コードの翌番 SP0188 から SP0202 まで連番
- **channel**: `'line'` 固定（既存の `tcg_line_import_svc.py:401` と整合）
- **external_id**: NULL（LINE グループ ID は未取得。後日 GAS 側と照合して設定予定）

---

## NULL UNIQUE の根拠

PostgreSQL UNIQUE 制約は `NULL ≠ NULL` のため、
`UNIQUE (channel, external_id)` において `external_id=NULL` は複数行を許容する。
本 migration では `NOT EXISTS` サブクエリで二重挿入を防ぐ。

---

## 基準と検証方法

| 基準 | 検証方法 |
|---|---|
| 15件が tcg_suppliers に登録される | `SELECT count(*) FROM tenant_004.tcg_suppliers WHERE code BETWEEN 'SP0188' AND 'SP0202'` → 15 |
| 各仕入元に supplier_channels(line) が1件 | `SELECT count(*) FROM tenant_004.supplier_channels sc JOIN tenant_004.tcg_suppliers s ON sc.supplier_id=s.id WHERE s.code BETWEEN 'SP0188' AND 'SP0202' AND sc.channel='line'` → 15 |
| 冪等（再実行で件数変化なし） | migration を 2 回実行しても上記件数が変わらない |
| run_all_migrations.sh に登録済み | `grep 20260905_120000 scripts/run_all_migrations.sh` で1行 hit |

---

## 外部・過去事例の参照と我々への応用

GAS 仕入元マスタ（`Latest24LineImport.js`）を正典として採用。
過去の教訓（ADR-154）: GAS 側に仕入元が存在しても DB 未登録のまま放置すると、
`tcg_line_import_svc.py` の `import_line_export` がその仕入元のメッセージをスキップする。
本 migration で 15名を登録することで、スキップされていたメッセージが取り込み対象になる。

---

## 維持の仕組み

守り手: 人手で守る（migration は一回限りの data patch。CI による継続ガードは不要）

後日対応予定:
- `external_id` に LINE グループ ID を設定する別 migration（GAS から取得後）
- 統合候補（funスタッフ / Kei / 大知 / oyama↔やまちゃん）の同一性照合と統合
