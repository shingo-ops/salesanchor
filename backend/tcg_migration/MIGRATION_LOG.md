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
| 2026-09-01 | E3a (`recoverUnitFromProductName`) + E5 (`recalcConditionFromResolvedUnit`) 移植 — dry-run 専用。migration: analysis_results に unit_basis 等 4列追加 | release/tcg-e3a-e5-unit-recovery |
| 2026-09-03 | PARITY-02 Phase D 統合: C-1/C-7/Status + C-3/C-6 (E3a+E5) + C-4/C-5 (E3b+E4) を `analyze_extraction_job` に統合 / ENGINE_VERSION 統一: `name-first-v2` / GAS Phase 3 実行順序: 正規化→照合→E3a→E5→E3b→E4 | release/tcg-parity02-phase-d-integrate |
| 2026-09-03 | `match_keyword()` GAS 準拠修正: キーワード未登録商品を候補にしない (`!srchStr → return`) / MULTI 1340→46件、pid_resolved 286→1294件（79.6%） | release/tcg-parity02-match-keyword-fix |
| 2026-09-03 | PARITY-03 Phase 3: tcg_products に mark/english_title 列追加・268商品データ投入（シート直読み）。充填率: mark 239/268 (89.2%), english_title 251/268 (93.7%) | PR #3246 |
| 2026-09-03 | PARITY-03 Phase 3 BE: 商品マスタ登録 API (B-1〜B-5 + R-1) + mark/english_title B-1/B-3対応 | PR #3239 |
| 2026-09-03 | PARITY-03 Phase 3 item_corrections: 修正履歴テーブル作成（append-only, field単位）| PR #3243 |

---

## mark/english_title 充填率 調査メモ (2026-09-03)

### PR #3246 調査値（シート直読み）

- 取得方法: `clasp run y1406DumpProductMasterV2Page` を 3バッチで実行（~/sqr07_work）
- mark: NULL **29件** / filled 239件 (89.2%)
- english_title: NULL **17件** / filled 251件 (93.7%)

### セッション3 文書ベース値（参考）

- mark: NULL 20件 (92.5%)
- english_title: NULL 7件 (97.4%)

### 差異の記録

- 差異: mark +9件、english_title +10件（実測の方が NULL が多い）
- 差異の原因: **【未確認】** シートへの追加 or 集計範囲の違いによる可能性
- 採用値: **シートの実測値を正とした**（コードベースのシード値ではなく clasp 直読み値）

---

## E3a + E5 実装 (2026-09-01)

### GAS → Python 関数対応表

| GAS 関数 | GAS ファイル:行 | Python 関数 | Python ファイル |
|----------|----------------|------------|----------------|
| `unitRecoveryNorm_` | AnalysisV2UnitRecovery.gs:30-32 | `unit_recovery_norm()` | tcg_unit_recovery_svc.py:119-127 |
| `unitRecoveryBuildTerms_` | AnalysisV2UnitRecovery.gs:91-104 | `build_unit_recovery_terms()` | tcg_unit_recovery_svc.py:134-170 |
| `unitRecoveryFindTerm_` | AnalysisV2UnitRecovery.gs:40-59 | `find_term()` | tcg_unit_recovery_svc.py:177-212 |
| `recoverUnitFromProductName` | AnalysisV2UnitRecovery.gs:134-276 | `recover_unit_from_product_name()` | tcg_unit_recovery_svc.py:219-332 |
| `condRecalcCollectTargets_` | AnalysisV2ConditionRecalc.gs:86-138 | `recalc_condition_from_recovered_unit()` | tcg_unit_recovery_svc.py:339-459 |
| `recalcConditionFromResolvedUnit` | AnalysisV2ConditionRecalc.gs:217-276 | (同上、dry-run のみ) | (同上) |

### E2/E4 除外理由

- **E2** (`applyUnitInferenceToAnalysisV2`): 価格帯テーブルから unit を推定するフェーズ。
  unit_inferred 列のみに書き込み、condition には影響しない。
  GAS 側でも E3a の後に実行されるため、E3a が先行する必要あり。
  現時点では影響行 0 のため未実装（将来タスク T-3 残置）。

- **E4** (`inferUnitFromCondition`): condition_canonical が Box/Pack 系の行から unit を逆引き。
  現在のデータセットで対象行 0 件のため未実装（将来タスク T-3 残置）。

### PM0264 について（実機確認 2026-09-02 訂正）

**誤判断（前セッション）**: 「PM0264 はルール上回収されるべき」と判断していた。

**事実（実機確認）**:
```sql
SELECT code, japanese_title FROM tenant_004.tcg_products
WHERE code IN ('PM0263','PM0264','PM0265');
-- PM0263 | 30th CELEBRATION
-- PM0264 | FUTURISTIC BOX    ← 'BOX' を含む
-- PM0265 | 30th CELEBRATION プレミアムデッキセット
```

**結論**: PM0264.japanese_title = 'FUTURISTIC BOX' → A-2 除外が適用される（norm_term='BOX' ∈ norm_jp）。
GAS 側も masterRec=undefined ではなく A-2 以前の問題（E3a 再実行漏れ）だったが、
Python 側は tcg_products.japanese_title で正しく A-2 を適用するため **回収しない**。
GAS・Python ともに 11件で完全一致する。

### PM0263-PM0265 (30周年カード) の注意

PM0263/PM0264/PM0265（30周年カード）は過去にも「マスタ未登録に戻る」問題が発生した商品群。
商品マスタ側の is_active フラグやコード変更に注意が必要。

---

## 訂正記録 (2026-09-01)

**誤報告**: 「`units.kubun` 列が本番 DB に存在しない」と前セッションで報告した。

**事実**: `units.kubun` 列は既存かつ全 8 行に値投入済み（UN0001:箱系大 〜 UN0008:条件つき）。

**実際に欠けていたのは**: Python コード（旧 `load_lookup_maps()`）が `units.kubun` を SELECT していなかったこと。
migration で ALTER TABLE が不要だった理由もこれ（列は存在し、値も正しかった）。

今回の v2 実装で `load_lookup_maps()` に `unit_alias_to_info`（alias → (canonical, kubun)）クエリを追加し、解決済み。

---

## 指摘済み差異の追跡失敗記録（教訓）

### 経緯

`match_keyword()` の `search_kw_str 空 → 全マッチ` 差異は、Phase D 統合前の
GAS-Python 対照表作成セッション（2026-09-03 前半）で既に指摘されていた。

```
GAS: investigate2.gs:10048 matchPid_
  if (!pid || !srchStr) return;  ← キーワード未登録の商品はスキップ
Python: if not search_kw_str: return True, "(既定)"  ← 全ヒット（誤）
```

にもかかわらず Phase D PR（#3218）に修正が含まれないまま main マージされた。
Phase E 測定（2026-09-03）で MULTI 1340件という数字が出て初めて発見・修正された。

### 原因

対照表の差異は口頭指摘に留まり、**タスクとして残置されなかった**。
MIGRATION_LOG の `未対応タスク（T-N）` セクションへの登録がなかったため
次の実装担当が把握できなかった。

### 再発防止策

GAS-Python 対照表で差異を発見した場合は、その場で以下のいずれかを行う:
1. 即時修正して PR に含める
2. 修正できない場合は MIGRATION_LOG の `未対応タスク` に番号を振って登録する
   - 対応必須フラグ（`TODO: 実装前に修正必要`）を明記する

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

### T-3: 単位証拠ルール E2/E3/E4/E5 移植（実測影響: 11→12行）

- **GAS 実装**: `AnalysisV2UnitRecovery.gs` (E3a: 商品名から unit 復旧) / `AnalysisV2UnitInference.gs` (E2: 価格帯から unit 推定) / `AnalysisV2UnitFromCondition.gs` (E4: condition 逆引き) / `AnalysisV2ConditionRecalc.gs` (E5: unit 復旧後の condition 再計算)
- **E3a + E5 実装済み** (release/tcg-e3a-e5-unit-recovery / PR #3200): dry-run 専用。DB 書き込みなし
  - E3a: NAME_RECOVERY:* = 11行 (ﾊﾟｯｸ:6, box:3, BOX:1, 箱:1) — GAS 実測と一致
  - E5: R4:単位既定:単位不明 → condition 再計算
- **E2 未実装**: 価格帯推定 (unit_inferred のみ・condition 非影響・対象行は将来データ依存)
- **E4 未実装**: condition 逆引き (対象行 0 件)
- **優先度**: 低〜中（残 E2/E4 は影響行 0 件）

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

## AnalysisV2*.gs 棚卸し (2026-09-01)

GAS 解析パイプラインを構成する 7 ファイルの役割・移植状況一覧。

| ファイル | フェーズ | 処理概要 | サーバー相当 | 移植状況 |
|----------|---------|---------|-------------|---------|
| `AnalysisV2.gs` | Phase 0-3 | 解析V2シート作成・照合実行 (PID/unit/condition 解決の統括) | `analyze_extraction_job()` in `tcg_analyzer_svc.py` | ✅ 実装済み (PR #3188) |
| `AnalysisV2PackCondition.gs` | Phase 3 後処理 | R5:パック既定 — unit=パック系(UN0003) かつ FLAG_SINGLE 行を Searched pack に変換 | `resolve_condition_v2` R5 ブロック | ✅ 実装済み (PR #3190) |
| `AnalysisV2UnitInference.gs` | Phase 3 | 価格帯テーブルから unit を推定 (E2: PRICE_BAND) → 解析V2 X-AA列に書き込み | 未実装 | ❌ T-3: 低〜中優先度 |
| `AnalysisV2UnitRecovery.gs` | Phase 3 | 商品名から unit を復旧 (NAME_RECOVERY:*) / 未解決行に UNIT_UNRESOLVED フラグ | `recover_unit_from_product_name()` in `tcg_unit_recovery_svc.py` | ✅ 実装済み (dry-run) |
| `AnalysisV2UnitFromCondition.gs` | Phase 3 後処理 | condition_canonical が Box/Pack 系 の行から unit を逆引き導出 | 未実装 | ❌ T-3: 低〜中優先度 (対象行 0) |
| `AnalysisV2ConditionRecalc.gs` | Phase 3 後処理 | `unit_basis='NAME_RECOVERY:*'` かつ `R4:単位既定:単位不明` 行の condition を再計算 | `recalc_condition_from_recovered_unit()` in `tcg_unit_recovery_svc.py` | ✅ 実装済み (dry-run) |
| `AnalysisV2Dedup.gs` | 運用メンテ | 解析V2 の重複行 (照合日時='2026-08-23' 始まり) を削除 | 不要 (DB は冪等 UPSERT) | ✅ 移植不要 |

### dry-run 最終結果 (2026-09-01, PR #3190 適用後 / E3a+E5 適用前)

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

### E3a+E5 dry-run 期待結果（2026-09-02 実機確認で確定）

E3a (NAME_RECOVERY) 期待分布（GAS 実測と完全一致）:
- ﾊﾟｯｸ: 6, box: 3, BOX: 1 (PM0263), 箱: 1 = 合計 **11行**
- PM0264 は A-2 除外（jp_title='FUTURISTIC BOX' に 'BOX' 含む）

E5 (condition 再計算) 後の期待分布（= GAS 実測と完全一致）:
- FLAG_SINGLE: 764, Sealed box: 468, Case: 217, No shrink box: 71
- Searched pack: 61, Damaged case: 17, Unsearched pack: 12
- Damaged sealed box: 11, Opened box: 5
- **一致率: 1626/1626 = 100%**

---

## source_messages.received_at 全件 NULL 確認記録 (2026-09-02)

### 事実

- `tenant_004.source_messages` の `received_at` カラムは全306件が `NULL`
- DDL: `received_at TIMESTAMPTZ`（nullable、DEFAULT なし）
- 306件すべて NULL であることを本番 DB で実確認済み

### 原因

GAS 側が受信日時を記録していなかったため（LINE Bot の受信時刻を GAS スクリプトが保存する処理が存在しない）。  
投入パイプライン（`ingest_*.py`）は GAS データをそのまま DB に写すため、元が NULL のまま投入されている。

### 補足（「GAS と等価」報告の訂正）

前セッションで「受信タイムスタンプは GAS と等価」と報告したが、これは誤りを含む表現だった。  
正確には「GAS 側にも値がなく、DB 側も NULL → 両方とも空（＝等価ではあるが有効な値は存在しない）」が正しい。

### 影響

`received_at` ベースの時系列分析（「何時ごろ仕入れリストが来るか」等）は現状で不可能。

### 代替

`extraction_jobs.created_at`（`NOT NULL DEFAULT NOW()`）= パイプライン処理日時は利用可能。  
時系列分析が必要な場合は `extraction_jobs.created_at` を使うこと。

### 将来ガイダンス

将来 LINE から直接取り込む（GAS を経由しない）実装を行う際は、受信時刻を `source_messages.received_at` に記録すること。
