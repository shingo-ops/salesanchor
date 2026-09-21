# design: import-tab-summary-card

## 目的・KGI

インポートタブを非エンジニアが一目で状態を把握できるUIに改善する。

| 基準 | 検証方法 |
|------|---------|
| 1枚のカードで全体状態が即時判断できる | 信号灯ヘッダー（緑/黄/赤）が表示される |
| matchRate >= 80% かつ pending=0 のとき緑 | ブラウザ確認 |
| CTAは pendingCount > 0 の場合のみ表示 | pending=0 時にボタンが消える |

## 設計詳細

### 信号灯ロジック

- headerSignal: GREEN if matchRate >= 80% AND pendingCount === 0; YELLOW if matchRate >= 60% OR pendingCount > 0; RED if matchRate < 60%
- matchRate = (1 - unresolved_rate) * 100（ポジティブフレーミング）
- pendingSignal: GREEN if 0, YELLOW if > 0

### 既存 API との対応

既存の `/tcg/analysis-dashboard/import-summary` レスポンスのみ使用。バックエンド変更なし。

| 表示項目 | APIフィールド |
|---------|------------|
| 処理済みメッセージ | `active_message_count` |
| 名前の一致率 | `1 - unresolved_rate` |
| 要対応 | `pending_review_count` |

## 外部・過去事例の参照と我々への応用

- Stripe Dashboard の取引サマリーカード: 1カードに状態+数値+CTAを集約し、問題がある場合のみアクションボタンを表示するパターン。CTAをconditionalに表示することで不要なクリックを減らす。
- GitHub Actions の workflow run サマリー: 信号灯（緑/黄/赤）で全体状態を即時判断、詳細は展開で確認。

## 維持の仕組み

守り手: ADR-027（i18n lint）・ADR-067（デザイントークン lint）・ADR-144（UIガバナンス）が既存CIで継続的に検証。

信号灯閾値（80%/60%）は既存の解析タブ（`getSignalLevel` 関数）と統一。変更時は解析タブも同時変更が必要。

## 影響範囲

- 変更: ImportTabContent 関数内のみ（AnalysisDashboardPanel.tsx 399-574行）
- 影響なし: バックエンド・他タブ・他コンポーネント
- 触らない範囲: ExtractionTabContent, AnalysisTabContent, DistributionTabContent, 全 API エンドポイント

## 戻し方

`git revert <commit-sha>` で即時戻し可能。DBマイグレーションなし。
