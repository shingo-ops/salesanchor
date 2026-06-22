# Recon — condition 語彙 SSOT（多軸正典）

> recon 基準: `shingo-ops/salesanchor` main `731f2be`（2026-06-22）

---

## 既存 ADR 検索結果

| キーワード | 結果 |
|---|---|
| `git grep -i "condition" docs/adr/` | ADR-093, ADR-099 が condition を定義 |
| `docs/adr/FEATURE-INDEX.md` | 在庫: ADR-099 / ADR-093 / ADR-014 |
| condition 多軸・正典・vocab に関する ADR | **該当なし**（本作業が初起案） |

---

## DB 現状

### public.inventory 列（`081_create_inventory.sql:29-45`）

```
id, supplier_id, product_id, condition VARCHAR(50) NOT NULL, quantity, unit_price,
status, notes_ja, notes_en, offered_at, expires_at, source, created_at, updated_at
```

- `raw_condition` 列 = **存在しない**
- 軸列（seal/search_cond/grade/damage）= **存在しない**

### UNIQUE キー現状

`uq_inventory_offer_key`（`20260602_180000_add_inventory_offer_type_ship_timing.sql:56-60`）:
```sql
ON public.inventory (
    supplier_id, product_id, condition,
    COALESCE(unit, ''), offer_type, COALESCE(ship_timing, '')
);
```

### condition CHECK 制約（`089_standardize_condition_values.sql:34-45`）

16 値: `shrink / no_shrink / sealed / damage / unsearched / searched / graded / grade_s / grade_a / grade_b / grade_c / grade_d / junk / bulk / normal / unknown`

---

## コード現状

### 単一マスタ（`backend/app/services/condition_vocab.py:5-129`）

- `UNIT_VALUES`: `piece / pack / box / case / set`
- `SEAL_VALUES`: `shrink / no_shrink / sealed / opened`
- `SEARCH_COND_VALUES`: `unsearched / searched`
- `GRADE_VALUES`: `s / a / b / c / d / normal / graded / junk / bulk`
- `CONDITION_VALUES`: `shrink / no_shrink / sealed / damage / unsearched / searched / graded / grade_s / grade_a / grade_b / grade_c / grade_d / junk / bulk / normal / unknown`
- `LEGACY_CONDITION_TO_CURRENT`: `shrink_yes / shrink_no / damaged / state_a_minus / state_a / state_b / new / used / opened` を current condition に寄せる（`opened` は `unknown`）
- `VER41_TO_CONDITION`: ver4.1 表記を current condition に寄せる

### Pydantic 型（`backend/app/schemas/inventory_offers.py:25-42`）

16 値 `InventoryCondition` Literal 定義。コメントに軸の自白あり:
- 封系 (box/case/set 主): shrink / no_shrink / sealed / damage
- サーチ系 (pack 主): unsearched / searched
- ランク系 (piece 主): graded / grade_s〜d / junk / bulk / normal
- 全単位: unknown

### ルールパーサ（`backend/app/services/inventory_parser.py:107-108,223-237,511-518,577-672,1097-1111`）

- `ParsedItem.condition`: `str | None`、current 16 値正典に寄せるコメントへ更新済み
- `ParsedItem.raw_condition`: 実装済みで、`_extract_blocks()` が元行 / 元ブロック全文を保持するよう修正済み
- `CONDITION_PATTERNS` は current condition に正規化済み:
  - `shrink_yes` / `shrink_no` は `shrink` / `no_shrink`
  - `damaged` は `damage`
  - `state_a_minus` / `state_a` は `grade_a`
  - `state_b` は `grade_b`
  - `new` / `used` は `unknown`
- `unit_default_search_cond()` が box / case の既定 search_cond を `unsearched` に返す（unit ベースのルール）

### LLM パーサ（`backend/app/services/inventory_parser_llm.py:64-81,102-125,159-180,299-317`）

- `LLMParsedItem` に `raw_condition` フィールドを追加済み
- `_OUTPUT_SCHEMA` に `raw_condition` を追加済み
- プロンプトは `CONDITION_VALUES` を列挙し、`raw_condition` に根拠テキスト全体を返すよう指示済み

### ja.json フロントエンド（`frontend/src/locales/ja.json`）

| 場所 | 内容 | 状態 |
|---|---|---|
| `:2233-2243` | `inventory.condition.*` 正典 16 値 | 正常（正典ブロック） |
| `:2233-2243` | 廃止コード (`new`/`usedA`/`opened`) | **削除済み** |
| `:2233-2243` | `conditionOptions.*` 重複ブロック | **削除済み** |
| `:2237-2243` | `"set": "セット / バルク"` | `"set": "セット"` へ分離済み |

---

## 情報損失の実証

`damage`（089 の condition 値）= ダメージあり、だが seal 情報を圧縮して消す。  
「Damaged sealed box」→ seal=sealed ＋ damage=true の 2 事実が必要。  
1 列方式では `damage` に潰れ「未開封」情報が消失する——これが多軸化の必然的根拠。

### 代表 fixture の `condition` 分布

`backend/tests/fixtures/inventory_aggregation/ver41_output.csv` を集計すると以下。

- `Sealed box`: 81
- `Case`: 27
- `Damaged sealed box`: 12
- `No shrink box`: 9
- `Single`: 8
- `Psa10`: 2
- `(なし)`: 1
- `Bulk`: 1
- `NULL`: 0

この fixture では `Sealed box / Case / Damaged sealed box / No shrink box` が主流で、`Single / Psa10 / (なし) / Bulk` は 089 の 16 値とは別の受け皿として残っている。

### 実 DB の `condition` 分布（read-only / dev-develop 経路）

read-only ロール `recon_ro` で `public.inventory` を SELECT した結果:

```text
 condition | n
-----------+----
 shrink    | 46
 sealed    | 38
 no_shrink |  8
(3 rows)
```

089 外 / NULL の洗い出し:

```text
 condition | n
-----------+---
(0 rows)
```

`unit × condition`:

```text
 unit | condition | n
------+-----------+----
      | shrink    | 46
      | sealed    | 38
      | no_shrink |  8
(3 rows)
```

所見:

- 実 DB の `public.inventory.condition` は 3 値のみで、089 外 / NULL は 0 件
- `unit` は空欄だが、`condition` は `shrink / sealed / no_shrink` に収束している
- `pg_constraint` には `inventory_condition_check` が見つからず、現 DB では `condition` の CHECK 強制は入っていない
- `recon_ro` は後始末済み。`\du recon_ro` で存在しないことを確認した

### migration 適用経路

- `.github/workflows/deploy.yml:152-157,438-454` は `scripts/run_all_migrations.sh` を呼ぶだけ
- `scripts/run_all_migrations.sh:165-173` が inventory への SQL migration 登録点
- `migrations/20260622_020000_add_inventory_raw_condition.sql:1-6` を追加し、`raw_condition` の段階 1 migration を runner に登録済み
- ただし `scripts/run_all_migrations.sh` には `migrations/089_standardize_condition_values.sql` の登録がないため、`inventory_condition_check` は current deploy path では届いていない

---

## ADR-093 前例（一意キー拡張）

`20260602_180000:27-29`: 「COALESCE'd 列を一意キーに追加・データ損失なし」と明記。  
今回も同じ手法（軸列追加→キー拡張→condition DROP）。低リスク反復。
