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

1. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:839-843`
   - `extractionDenominator = done + error` を新設
   - `extractionSuccessRate = done / extractionDenominator`

2. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:852-862`
   - トレンドグラフの分母を `extraction_done + extraction_error` に変更
   - errorRate も同じ分母で統一

3. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:864-875`
   - `.filter((s) => s.extraction.done + s.extraction.error > 0)` を追加
   - empty のみの提供者をランキングから除外

### 呼び出し元

- `ExtractionTabContent` コンポーネント内のみ。外部から渡される prop を変更しない。
- バックエンド API の変更なし。

### 戻し方

git revert で該当コミットを打ち消す。フロントのみ・DBスキーマ変更なし。

## 外部・過去事例の参照と我々への応用

同様の事例: 計算指標から「評価対象外」ステータスを除外する手法は標準的な実践。
例) 調査統計で「N/A」回答を成功率分母から除く。
我々への応用: empty = 商品データ不在の自然な結果。done/fail の二項評価に馴染まない。
「挨拶しか来ない提供者を0%と評価するのは誤り」という事業要件を数式で表現する。

## 維持の仕組み

守り手: TypeScript（`SupplierExtractionInfo.done` / `error` は `number` 型で保護）

計算箇所は `ExtractionTabContent` コンポーネント内の `extractionDenominator` 変数1箇所に集約。
将来の変更時は `extractionDenominator` を検索すれば全利用箇所が把握できる。
