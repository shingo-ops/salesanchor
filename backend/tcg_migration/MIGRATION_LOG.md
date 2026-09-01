# TCG Migration Log — 未対応タスク

GAS → サーバー移植の実施済み・未対応一覧。

---

## 実施済み

| 日付 | 内容 | ブランチ/PR |
|------|------|------------|
| 2026-09-01 | `normalizeEn_` / `matchOneKw_` / `tokenAndMatch_` / `matchKeyword_` 移植 (name-first-v2) | release/tcg-keyword-matching |
| 2026-09-01 | `product_search_keywords` / `product_exclude_keywords` 再インポート (593件/128件 + UNIQUE制約) | release/tcg-keyword-matching |

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

### T-3: 単位証拠ルール E2/E3 移植

- **GAS 実装**: `SystemResolverV2.gs:393-460` — E2_PRICE_X_QTY_UNIT / E3_PRODUCT_RESIDUAL
- **内容**: 価格×数量×単位の構造パターン (`{{UNIT}}` テンプレート展開) から単位を証拠推定
- **サーバー現状**: `resolve_unit()` は alias lookup のみ。E2/E3 未実装
- **影響**: 単位が明示されない行の推論精度
- **優先度**: 低〜中

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
