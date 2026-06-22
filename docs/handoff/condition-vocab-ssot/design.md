# Design — condition 語彙 SSOT（多軸正典）

> 正本: 最初のセッション取り決め ＋ ver4.1 の実挙動 ＋ 合意済み多軸モデル。
> recon 基準: main `731f2be`（2026-06-22）。
> 相互参照: `recon.md`（同ディレクトリ）

---

## KGI（承認ゲート）

tenant_006 で以下を満たし、結果を見て Shingo が GO:

1. 正典 vocab（梱包/封/サーチ/ランク/破損）を単一マスタ 1 ファイルに集約
2. ver4.1 語 → 多軸の決定的マッピングを確定（GAS 実挙動が根拠）
3. 散在語彙（parser の `shrink_yes` 等・ja.json の `new/usedA/opened` 等）を正典へ寄せ／廃止
4. CI 関所：正典外語彙混入で CI が赤（意図的混入で赤を実確認）
5. 原文 (raw) は最初の1片ではなく元行/元ブロック単位で保持する
6. 集計ゴールデンが正典 vocab でも 100%一致維持（基準=ver4.1 で不変）
7. 危険変更（列追加 migration・一意キー変更）は本番前 PO GO。tenant_4 に触れない

---

## 正典 — 多軸モデル（確定）

**原則: 1 セル 1 事実。該当しない軸は空欄。空欄(該当なし) ≠ unknown(不明)。**

| 軸 | 列名 | 正典値 | 主な梱包 | 埋め方 |
|---|---|---|---|---|
| 梱包 | `unit` | piece / pack / box / case / set | — | 解析（必ず出る）既存流用 |
| 封 | `seal` | shrink / no_shrink / sealed / opened | box / case / set | 解析。無ければ空欄 |
| サーチ | `search_cond` | unsearched / searched | pack | ルール既定は unit 由来（box/case→unsearched 自動）＋pack は実値 |
| ランク | `grade` | s / a / b / c / d / normal / graded / junk / bulk | piece | 解析 |
| 破損 | `damage` | true / false（BOOLEAN NOT NULL DEFAULT false） | 全梱包 | 解析。無ければ false |

### bulk の帰属仮置き（§7.2）

`bulk` は **grade 軸の暫定値**。バルク = 低グレードシングルの大量まとめ販売（質の属性、梱包形態ではない）。  
現行コードも `condition` に入り「piece 主」と注記済み（`inventory_offers.py:39`）。  
今回の段階 1 では **確認待ち（暫定grade）** として据え、段階 2 の backfill 前に最終確認する。  
`frontend/src/locales/ja.json:2237-2243` の `"set": "セット / バルク"` は「セット商品」の別文脈。バルクカードとは無関係——掃除時に `"set": "セット"` へ分離済み。

---

## §7 確定判断（4 論点）

### §7.1 condition 列：置換 (Replace)

「Damaged sealed box」で seal=sealed ＋ damage=true が同時に必要。  
現行 `condition='damage'` は seal 情報を消失させる。  
**再定義（seal のみへの絞り込み）では多軸を 1 列に収められない。**

採択: **段階的置換**

| 段階 | 内容 | GO 要否 |
|---|---|---|
| 段階 1（地盤） | raw_condition 列追加・単一マスタ・CI 関所・ja.json 掃除 | additive → GO 不要 |
| 段階 2a | 軸列追加（seal/search_cond/grade/damage）＋ condition から backfill | additive → GO 不要 |
| 段階 2b | UNIQUE キーを軸列へ移行（旧キー DROP → v2 新設） | **PO GO 必須** |
| 段階 3 | condition 列 DROP | **PO GO 必須** |

移行中は condition ＋ 軸列を**並行書き込み**。

### §7.2 bulk の帰属

→ grade 軸（上の正典表に反映済み）

### §7.3 一意キー最終構成

**全 4 軸 ＋ unit ＋ offer_type ＋ ship_timing の複合キー（段階 2b で切り替え）**

```sql
CREATE UNIQUE INDEX uq_inventory_offer_v2
    ON public.inventory (
        supplier_id, product_id,
        COALESCE(seal, ''),
        COALESCE(search_cond, ''),   -- 'search' は SQL 予約語を避け列名は search_cond
        COALESCE(grade, ''),
        damage,                       -- BOOLEAN NOT NULL DEFAULT false
        COALESCE(unit, ''),
        offer_type,
        COALESCE(ship_timing, '')
    );
```

段階 2b まで旧 `uq_inventory_offer_key`（condition ベース）を保持。

### §7.4 raw 列の置き場

| 対象 | 変更 |
|---|---|
| DB | `public.inventory` に `raw_condition TEXT` 追加（`migrations/20260622_020000_add_inventory_raw_condition.sql:1-6`） |
| ルールパーサ | `ParsedItem.raw_condition` 実装済み（`backend/app/services/inventory_parser.py:107-108`）。DB に書く INSERT 側は、**最初の1片ではなく元行/元ブロックの原文**をそのまま保存するように修正済み（`inventory_parser.py:577-672`, `:1097-1111`） |
| LLM パーサ | `LLMParsedItem` に `raw_condition: str \| None` フィールド追加（`backend/app/services/inventory_parser_llm.py:64-81`）。`_OUTPUT_SCHEMA` にも追加（`:102-125`）。プロンプトに「状態の根拠テキストを raw_condition に返せ」を追記（`:159-180`） |
| unit 既定 | `box / case → search_cond=unsearched` は `backend/app/services/condition_vocab.py:63-113` の unit helper で保持 |

JSONB `raw_attributes` は YAGNI（将来必要なら別 ADR）。

---

## ver4.1 語 → 多軸 決定的マッピング

| ver4.1 の表記 | unit | seal | search_cond | grade | damage | 根拠 |
|---|---|---|---|---|---|---|
| Sealed box | box | shrink | — | — | false | GAS stepF2: 残る Sealed box = シュリンク有 確定 |
| No shrink box | box | no_shrink | — | — | false | GAS stepF2 の対 |
| Damaged sealed box | box | sealed | — | — | **true** | 多軸なら未開封情報を消さない（旧 1 列方式の取りこぼし解消） |
| Case | case | sealed | unsearched（unit 既定） | — | false | ver4.1 はカートンのシュリンク有無を区別しない |
| Unsearched pack | pack | — | unsearched | — | false | — |
| FLAG_SINGLE | piece | — | — | — | — | 集計対象外（ver4.1 と同じ） |

---

## conform 表

### ルールパーサ → 正典

| 既存（地形） | file:line | 寄せ先（正典） |
|---|---|---|
| parser `shrink_yes` | `backend/app/services/inventory_parser.py:223-237,511-518` | seal=shrink |
| parser `shrink_no` | `backend/app/services/inventory_parser.py:223-237,511-518` | seal=no_shrink |
| parser `damaged` | `backend/app/services/inventory_parser.py:223-237,511-518` | damage=true |
| parser `state_a_minus` | `backend/app/services/inventory_parser.py:223-237,511-518` | grade=a（A- は grade 粒度に丸め・原文で復元可） |
| parser `state_b` | `backend/app/services/inventory_parser.py:223-237,511-518` | grade=b |

### LLM / UI `condition` → 正典

| 現行の 1 列 condition | file:line | 寄せ先（正典） |
|---|---|---|
| `shrink` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | seal=shrink |
| `no_shrink` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | seal=no_shrink |
| `sealed` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | seal=sealed |
| `damage` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | damage=true |
| `unsearched` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | search_cond=unsearched |
| `searched` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | search_cond=searched |
| `graded` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | grade=graded |
| `grade_s` / `grade_a` / `grade_b` / `grade_c` / `grade_d` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | grade=s/a/b/c/d |
| `junk` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | grade=junk |
| `bulk` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | grade=bulk（暫定） |
| `normal` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | grade=normal |
| `unknown` | `backend/app/services/inventory_parser_llm.py:169-180` / `frontend/src/locales/ja.json:2233-2243` | 未確定時の受け皿 |
| `new / usedA / opened` | `frontend/src/locales/ja.json:2233-2243` | **廃止・削除** |
| `conditionOptions.*` 重複ブロック | `frontend/src/locales/ja.json:2233-2243` | 単一マスタ参照に統合 |
| `"set": "セット / バルク"` | `frontend/src/locales/ja.json:2237-2243` | `"set": "セット"` へ分離 |

---

## 段階計画（実装ハンドオフ単位）

### 段階 1：地盤（危険なし・先行可）

1. **単一マスタ 1 ファイル**を新設（`backend/app/services/condition_vocab.py`）
   - 正典 vocab（seal/search_cond/grade/damage の各値セット）
   - ver4.1 → 多軸マッピング辞書
   - parser `shrink_yes` 等の旧語 → 正典語 conform マップ
2. `public.inventory` に `raw_condition TEXT` を追加（`migrations/20260622_020000_add_inventory_raw_condition.sql`）
3. ルールパーサの INSERT 経路に `raw_condition` を書く修正
4. LLM パーサに `raw_condition` フィールドを追加
5. **CI 関所設置**（`deprecated-columns-check.yml` / `process-artifacts-gate.yml` の型を流用）
   - 正典外の条件語が ja.json・プロンプト・パーサに混入したら赤
   - 動作確認: 意図的混入 1 件 → CI 赤を確認してから完成扱い
6. ja.json 廃止コード掃除（recon で参照元確認後）

### 段階 2：ほどく（PO GO ゲートあり）

1. 軸列追加（`seal TEXT / search_cond TEXT / grade TEXT / damage BOOLEAN NOT NULL DEFAULT false`）
2. 既存 condition から軸列への backfill UPDATE（mapping は conform 表を使用）
3. パーサ（ルール＋LLM）を正典 vocab で書き直し。ルール既定（box/case→unsearched）を vocab config で管理
4. 集計・ゴールデン・smoke を**正典 vocab で作り直し**（実マイグレ済みの本物スキーマで緑）
5. **PO GO 後**：UNIQUE キーを `uq_inventory_offer_v2`（軸列ベース）へ切り替え

### 段階 3：condition 廃止（PO GO 後・別フェーズ）

- condition 列を deprecated にし、最終的に DROP（PO GO 必須）

---

## 関所（enforcement）設計

三重構造（既存型流用・新発明ゼロ）:

| 層 | 実装 | 守る範囲 |
|---|---|---|
| ① DB CHECK | 089 の系譜。軸列追加後は各軸に CHECK 制約 | DB レベルで弾く |
| ② unit test | vocab マスタとパーサ出力の一致チェック | コード |
| ③ CI 走査ゲート（本命） | `deprecated-columns-check.yml` / `process-artifacts-gate.yml` 型を流用 | ja.json・プロンプト・全テキストファイル |

### 実 DB 所見（2026-06-22 read-only）

- `public.inventory.condition` は `shrink / sealed / no_shrink` の 3 値に収束していた
- 089 外 / NULL は 0 件だった
- ただし `pg_constraint` に `inventory_condition_check` は存在せず、現 DB では `condition` の CHECK 強制は未実装

「落ちて初めて成果物」: 正典外の語を 1 件わざと混ぜ CI が赤になるのを実確認してから完成扱い。

---

## 危険変更・GO ゲート

- `raw_condition` 列追加 = additive → GO 不要
- 軸列追加・backfill = additive → GO 不要
- UNIQUE キー変更（旧 DROP → v2 新設）= **PO GO 必須**
- condition 列 DROP = **PO GO 必須**

tenant_006 検証まで CI で進め、**本番 (tenant_4) 投入前に必ず Shingo の GO**。

---

## 外部・過去事例欄

- **内部前例（最良手本）**: 梱包(unit)軸独立化（`inventory_offers.py:17`）＋ ADR-093 の一意キー拡張（データ損失なし）。同じ手順の反復。
- **ゲート前例（実在）**: `deprecated-columns-check.yml` / `process-artifacts-gate.yml`。
- **一般原則**: 「正規コード＋原文 passthrough（タグ付き enum + lookup + raw 保持）」= 丸めの不可逆損失を避ける定石。多軸 = この定石を状態に適用。

---

## 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| 単一マスタに正典 vocab が定義されている | `cat backend/app/services/condition_vocab.py` で全値確認 |
| パーサが正典語以外を出力しない | unit test: parser 出力 vs vocab マスタの set 比較 |
| CI 関所が正典外語彙を弾く | 意図的混入 PR → CI が赤になることを確認 |
| raw_condition が DB に保存される | INSERT 後 `SELECT raw_condition FROM public.inventory LIMIT 5` |
| LLM パーサが raw_condition を返す | test_inventory_parser_llm.py で mock 確認 |
| 集計ゴールデン 100%一致維持 | 既存ゴールデンテスト緑 |
| 廃止語が ja.json から消えた | `grep -n "usedA\|\"new\"\|\"opened\"" frontend/src/locales/ja.json` = 0 件 |
| tenant_006 での動作確認 | 実オファー INSERT → 在庫表表示 → condition 軸値確認 |
