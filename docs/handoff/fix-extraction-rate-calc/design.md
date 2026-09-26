# design: fix-extraction-rate-calc

## KGI

「抽出成功率が正しく計算される」 = 挨拶のみ提供者（Akiho等）が成功率0%と表示されない。
POが画面で確認可能。

## 変更方針

### 計算式変更

**変更前**: `done / total` （total = 全ステータスの合計）
**変更後**: `done / (done + error)` （empty/pending/running を除外）

根拠: empty は「商品データなし」で処理結果ではない。running/pending は未完了。
成功率 = done が done+error 中何割か、という意味が正確。

| 基準 | 検証方法 |
|------|--------|
| 挨拶のみ提供者が成功率0%と表示されない | Extractionタブのランキングに表示されない |
| done+error=0 の提供者がランキングから消える | extractionSupplierRows フィルタで除外 |
| エラーがある提供者の成功率が正しく計算される | done/(done+error) の手計算と一致 |

### 影響範囲

変更箇所（フロントエンド計算ロジックのみ。バックエンド変更なし）:

1. `AnalysisDashboardPanel.tsx:839-843`
   - `extractionDenominator = done + error` を新設
   - `extractionSuccessRate = done / extractionDenominator`

2. `AnalysisDashboardPanel.tsx:852-862`
   - トレンドグラフの分母を `extraction_done + extraction_error` に変更
   - errorRate も同じ分母で統一

3. `AnalysisDashboardPanel.tsx:864-875`
   - `.filter((s) => s.extraction.done + s.extraction.error > 0)` を追加
   - empty のみの提供者をランキングから除外

### 呼び出し元

- `ExtractionTabContent` コンポーネント内のみ。外部から渡される prop を変更しない。
- バックエンド API の変更なし。

### 戻し方

git revert で該当コミットを打ち消す。フロントのみ・DBスキーマ変更なし。

### 外部事例

該当なし（計算ロジックのシンプルな定義修正）。

### 守り手

TypeScript 型チェック（ `SupplierExtractionInfo.done / .error` は `number` 型で確定）
