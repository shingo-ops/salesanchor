# TCG Migration Log — 未対応タスク

GAS → サーバー移植の実施済み・未対応一覧。

---

## 実施済み

| 日付 | 内容 | ブランチ/PR |
|------|------|------------|
| 2026-09-01 | `normalizeEn_` / `matchOneKw_` / `tokenAndMatch_` / `matchKeyword_` 移植 (name-first-v2) | release/tcg-keyword-matching |
| 2026-09-01 | `product_search_keywords` / `product_exclude_keywords` 再インポート (593件/128件 + UNIQUE制約) | release/tcg-keyword-matching |
| 2026-09-01 | kubun 状態解決エンジン v2 実装 (name-first-v2-cond-r4): `resolve_unit_v2` / `resolve_condition_v2` / R1〜R4 移植 + migration (conditions に priority/search_kw/exclude_kw 追加 + seed) | release/tcg-keyword-matching / PR #3188 |
| 2026-09-01 | R5:パック既定 追加 (`applyPackConditionDefault` 移植) + `load_condition_entries` ORDER BY code ASC タイブレーカー修正 | release/tcg-cond-r5-fix / PR #3190 |

---

## 訂正記録 (2026-09-01)

**誤報告**: 「`units.kubun` 列が本番 DB に存在しない」と前セッションで報告した。

**事実**: `units.kubun` 列は既存かつ全 8 行に値投入済み（UN0001:箱系大 〜 UN0008:条件つき）。

**実際に欠けていたのは**: Python コード（旧 `load_lookup_maps()`）が `units.kubun` を SELECT していなかったこと。
migration で ALTER TABLE が不要だった理由もこれ（列は存在し、値も正しかった）。

今回の v2 実装で `load_lookup_maps()` に `unit_alias_to_info`（alias → (canonical, kubun)）クエリを追加し、解決済み。

---

## 未対応（後続タスク）

### T-1: PRICE / QUANTITY 正規化ルール移植

- **GAS 実装**: `SystemResolverV2.gs:662-663` — `normalizeNumericField_('PRICE', ...)` / `normalizeNumericField_('QUANTITY', ...)`
- **GAS ルール内容** (正規化ルール シート):
  - PRICE: `@`, `円`, `¥`, `￥`, `,`, ` `, `　` を除去 (7件)
  - QUANTITY: `,`, ` `, `　` を除去 (3件)
- **サーバー現状**: `tcg_analyzer_svc.py` の `_parse_numeric()` で部分対応 (全角数字変換のみ)
- **影響**: 価格・数量の解析精度
- **優先度**: 中

### T-2: CONDITION / NOTE / STATUS / UNIT 正規化ルール移植

- **GAS 実装**: `SystemResolverV2.gs:197, 614` — `normalizeTextField_`
- **GAS ルール内容**: 装飾記号除去 (22〜29件/フィールド) + 日付表記正規化 (NOTE: 7パターン)
- **サーバー現状**: 未実装
- **影響**: 装飾記号 (■●▲等) を含む商品名・状態テキストの照合精度
- **優先度**: 中

### T-3: 単位証拠ルール E2/E3 移植（実測影響: 11行）

- **GAS 実装（5ファイルセット・相互依存）**:
  - `AnalysisV2UnitInference.gs` (E2: 価格帯から unit 推定 — applyUnitInferenceToAnalysisV2)
  - `UnitInference.gs` (E2ライブラリ: buildPriceBands_ / inferUnitByPriceBand_)
  - `AnalysisV2UnitRecovery.gs` (E3: 商品名から unit 復旧 — recoverUnitFromProductName)
  - `AnalysisV2UnitFromCondition.gs` (condition 逆引き — deriveUnitFromCondition)
  - `AnalysisV2ConditionRecalc.gs` (unit 復旧後の condition 再計算 — recalcConditionFromResolvedUnit)
- **実行順序**: UnitInference → UnitRecovery → UnitFromCondition → ConditionRecalc（この順に依存）
- **影響実測**: dry-run 1626件中 11件が GAS と異なる（v2: FLAG_SINGLE / GAS: Sealed box 5件 + Searched pack 6件）
  - 5件: 商品名に box 含む行 (例: `'OP-13 box'`, `'30th CELEBRATION BOX'`, `'白箱'`) → GAS は商品名から unit=箱系 を推定
  - 6件: 商品名に パック 含む行 (例: `'ストームエメラルダ パック'`, `'蒼空ストリームバラパック'`) → GAS は商品名から unit=パック系 を推定 → R5 適用
  - 全11件: `raw_unit=''`, `pid_resolved` ステータス要確認（YES なら UnitRecovery 対象、NO ならスキップ）
- **UnitRecovery 移植上の注意**:
  - 商品マスタ (japanese_title / english_title) の A-2 除外が必要（商品タイトルに単位語が含まれる場合は補正しない）
  - NFKC 正規化 + 最長一致 + 末尾一致 + ct/CT 単語境界 + 'ケース' 直前空白必須
  - 商品マスタ DB カラム存在要確認（japanese_title / english_title が products テーブルにあるか）
- **サーバー現状**: `resolve_unit_v2()` は alias lookup のみ。5ファイルセット全未実装
- **優先度**: 低〜中（11件 = 0.68%。現状許容範囲。次回着手対象）

### T-4: condition_aliases 大文字小文字の統一

- **GAS 実装**: `investigate2.gs:8104` — `alias.toLowerCase().replace(/\s+/g,' ')` で小文字化して map キーに格納
- **DB現状**: `condition_aliases.alias_text` に `'Opened box'` (大文字始まり) と `'opened box'` (小文字) の2行が混在
- **サーバー現状**: `resolve_condition()` は小文字 fallback あり (lowercase 2段階)
- **影響軽微**: lowercase fallback で吸収済み。ただし GAS 側に存在しない `'Opened box'` / `'opened box'` の追加起源が不明
- **要確認**: GAS の状態マスタに無いエントリを DB から削除するか確認 (PO判断)
- **優先度**: 低

### T-5: PRODUCT_NAME_MATCH 正規化ルール実装

- **GAS 定義**: `NormalizationRules.gs:9` — フィールド `PRODUCT_NAME_MATCH` が定義されている
- **GAS ルール**: priority=10 `^[■●▲・\s\d.]+` 除去, priority=20 `\s+` → ` ` 圧縮
- **GAS 実装状況**: `matchKeyword_` はこれを呼び出していない (GAS 側も未実装)
- **サーバー現状**: 未実装 (GAS と同水準)
- **影響**: GAS との差分は生じない。将来 GAS 側で実装されたタイミングで追従
- **優先度**: 低 (GAS 側実装後に追従)

---

## GAS 全ファイル棚卸し (2026-09-01)

リポジトリ: `~/sqr01_pullback2/` — 計64ファイル。解析パイプライン関連を全件列挙する。

### AnalysisV2*.gs 系（8ファイル）

| ファイル | フェーズ | 処理概要 | サーバー相当 | 移植状況 |
|----------|---------|---------|-------------|---------|
| `AnalysisV2.gs` | Phase 0-3 | 解析V2シート作成・照合実行 (PID/unit/condition 解決の統括) | `analyze_extraction_job()` in `tcg_analyzer_svc.py` | ✅ 実装済み (PR #3188) |
| `AnalysisV2PackCondition.gs` | Phase 3 後処理 | R5:パック既定 — unit=パック系(UN0003) かつ FLAG_SINGLE 行を Searched pack に変換 | `resolve_condition_v2` R5 ブロック | ✅ 実装済み (PR #3190) |
| `AnalysisV2UnitInference.gs` | Phase 3 | 価格帯テーブルから unit を推定 (E2: PRICE_BAND) → 解析V2 X-AA列に書き込み | 未実装 | ❌ T-3: 低〜中優先度 |
| `AnalysisV2UnitRecovery.gs` | Phase 3 | 商品名から unit を復旧 (NAME_RECOVERY:*) / 未解決行に UNIT_UNRESOLVED フラグ | 未実装 | ❌ T-3: 低〜中優先度 |
| `AnalysisV2UnitFromCondition.gs` | Phase 3 後処理 | condition_canonical が Box/Pack 系 の行から unit を逆引き導出 | 未実装 | ❌ T-3: 低〜中優先度 |
| `AnalysisV2ConditionRecalc.gs` | Phase 3 後処理 | `unit_basis='NAME_RECOVERY:*'` かつ `R4:単位既定:単位不明` 行の condition を再計算 | 未実装 | ❌ T-3 依存: UnitRecovery 実装後に実施 |
| `AnalysisV2Dedup.gs` | 運用メンテ | 解析V2 の重複行削除 | 不要 (DB は冪等 UPSERT) | ✅ 移植不要 |

### 解析パイプライン依存ライブラリ（AnalysisV2 が呼ぶ非 AnalysisV2 ファイル）

| ファイル | 役割 | サーバー相当 | 移植状況 |
|---------|------|-------------|---------|
| `SystemResolverV2.gs` | `resolveRawExtractionV2Rows_()` — PID/unit/condition/qty/price/note 解決の中心 | `analyze_extraction_job()` | ✅ 実装済み |
| `NormalizationRules.gs` | `normalizeTextField_()` / `normalizeNumericField_()` — 正規化ルールシートを読み込み適用 | `_parse_numeric()` (数値のみ部分実装) | ⚠️ T-1/T-2未実装 |
| `UnitInference.gs` | `buildPriceBands_()` / `inferUnitByPriceBand_()` — 価格帯テーブル構築・推定ライブラリ | 未実装 | ❌ T-3依存 |
| `investigate2.gs` | `readUnitMaster()` / `readConditionMaster()` / `resolveCondition_()` | 各 lookup 関数 | ⚠️ 部分実装 |
| `ProviderScoringV2.gs` | `readProviderScoringV2Context_()` — 照合コンテキスト構築 | `analyze_extraction_job()` 内 | ✅ 実装済み |

### 非解析パイプライン（移植不要）

抽出V2入力系 (ExtractionV2*.gs 4件) / 出力系 (OutputV2.gs) / 商品マスタ管理 (ProductMasterV2*.gs 等 8件) / 状態マスタ管理 (ConditionMaster*.gs 等 5件) / 業務系 (在庫・Discord・Sync・CRM 等 10件) / 設定・インフラ (Config/Constants/Menu/Settings/AccessControl 等 7件) / 調査スクリプト (investigate*.gs / Y*_*.gs 等 12件) / デバッグ (2件) — 計49ファイル、全て移植不要。

---

## 見落とし分析 (2026-09-01)

### 構造的原因

AnalysisV2PackCondition.gs と AnalysisV2UnitRecovery.gs は、いずれも **Phase 3 後処理として独立した clasp run 関数**として設計されており、`runAnalysisV2()` 本体（AnalysisV2.gs）から呼び出されていない。

```
runAnalysisV2()          ← AnalysisV2.gs 本体
  └─ resolveRawExtractionV2Rows_()  ← SystemResolverV2.gs

# 後処理（本体から呼ばれない独立 clasp run）
applyPackConditionDefault()      ← AnalysisV2PackCondition.gs
recoverUnitFromProductName()     ← AnalysisV2UnitRecovery.gs
applyUnitInferenceToAnalysisV2() ← AnalysisV2UnitInference.gs
deriveUnitFromCondition()        ← AnalysisV2UnitFromCondition.gs
recalcConditionFromResolvedUnit() ← AnalysisV2ConditionRecalc.gs
```

コード追跡（呼び出しグラフを辿る方法）では発見できない設計。GASのシートベース処理では「順番にボタンを押す」運用が多く、呼び出し関係が暗黙の慣習になっている。

### 発見経緯

dry-run 数字の不一致（FLAG_SINGLE が GAS より多い）を起点に遡って調査した結果、GAS 側に `applyPackConditionDefault()` という後処理ステップが存在することが判明。同様の構造が他にないかを全ファイル棚卸しとして確定させたところ、4ファイル（UnitInference / UnitRecovery / UnitFromCondition / ConditionRecalc）が追加で発覚した。

### 再発防止策

1. **GAS 変更時は `~/sqr01_pullback2/` の全 .gs ファイルを diff する**（新ファイル追加を検知）
2. **本ファイル（MIGRATION_LOG.md）を GAS 変更の都度更新する**（棚卸し表を常に最新化）
3. **Phase 3 後処理ファイルは「本体から呼ばれない独立実行」として専用セクションで管理する**
4. **移植完了基準**: AnalysisV2*.gs 系 + 依存ライブラリの全件が ✅ になること

---

## 現在の到達点 (2026-09-01)

| 項目 | GAS | サーバー v2 | 一致率 | 状態 |
|------|-----|-------------|--------|------|
| 状態解決（condition） | 1626件実測 | 1626件 | 99.32% (1615/1626) | ✅ 許容範囲（残11件はT-3既知制限） |
| キーワードマスタ | search_kw 593件 / exclude_kw 128件 | 同件数 | 100% | ✅ |
| 商品マスタ | 268件 | 268件 | 100% | ✅ |
| 条件マスタ R1〜R5 | R5含む全ルール | R5 実装済み (PR #3190) | — | ✅ |
| 単位系（UnitInference/Recovery/FromCondition/ConditionRecalc） | 実装済み | 未実装 | — | ❌ T-3（次回着手） |
| 正規化ルール（PRICE/QTY/CONDITION/NOTE） | 全ルール | 数値のみ部分実装 | — | ⚠️ T-1/T-2（中優先度） |

---

## 次回着手: T-3 単位系まとめ実装方針 (2026-09-01 記録)

単位系5ファイルは相互依存のため、**1スプリントでまとめて実装する**。

### 実装対象（依存順）

1. `UnitInference.gs` (ライブラリ: buildPriceBands_ / inferUnitByPriceBand_)
2. `AnalysisV2UnitInference.gs` (E2: 価格帯推定 → 1に依存)
3. `AnalysisV2UnitRecovery.gs` (E3: 商品名復旧 → 商品マスタ A-2除外が必要)
4. `AnalysisV2UnitFromCondition.gs` (condition逆引き → condition解決後に実行)
5. `AnalysisV2ConditionRecalc.gs` (condition再計算 → 3に依存)

### 着手前の事前確認事項

- [ ] `products` テーブルに `japanese_title` / `english_title` カラムが存在するか確認（UnitRecovery A-2除外に必要）
- [ ] 単位未解決行の pid_resolved 分布を DB で確認（11件中何件が UnitRecovery 対象か）
- [ ] UnitInference の価格帯テーブル構築に使うデータが `extraction_items.raw_price` から取得可能か確認

### 実装しない

PR #3190 時点では実装対象外。PO承認後に別ブランチ/PRで実施。

### dry-run 最終結果 (2026-09-01, PR #3190 適用後)

| condition_canonical | GAS実測 | v2 (after) | 差分 | 備考 |
|--------------------|---------|------------|------|------|
| FLAG_SINGLE        | 764     | 775        | +11  | T-3: 商品名からunit推定不可 |
| Sealed box         | 468     | 463        | -5   | T-3: 箱名称が unit field に未記入 |
| Case               | 217     | 217        | 0    | ✅ |
| No shrink box      | 71      | 71         | 0    | ✅ |
| Searched pack      | 61      | 55         | -6   | T-3: パック名称が unit field に未記入 |
| Damaged case       | 17      | 17         | 0    | ✅ |
| Unsearched pack    | 12      | 12         | 0    | ✅ |
| Damaged sealed box | 11      | 11         | 0    | ✅ |
| Opened box         | 5       | 5          | 0    | ✅ |
| **合計**           | **1626** | **1626**  |      | |
| **一致率**         |         |            | **99.32%** (1615/1626) | 残11件はT-3既知制限 |

basis 分布 (v2 after):
- R1: 32, R2: 29, R3: 88, R4: 1423, R5: 54
