# Recon: fix-import-active-count

## 調査対象
インポートタブの「メッセージ数」KPIカードが `total_messages`（非アクティブ含む全量）を表示している問題。

## 事実確認

### 変更対象ファイル
`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:453-463`

現状:
- ラベル: `t("analysisRules.dashboard.importMessages")` → "メッセージ総数" / "Total Messages"
- 値: `data.total_messages`

### ImportSummary インターフェース確認
`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:127-136`
- `total_messages: number` — supersede済み含む全量
- `active_message_count: number` — is_active=TRUE のみ

### i18nキー確認
`frontend/src/locales/ja.json:3913` — `"importActiveMessages": "有効メッセージ"`
`frontend/src/locales/en.json:3913` — `"importActiveMessages": "Active Messages"`
両キーとも既存。追加不要。

## ADR検索結果
- ADR-027: i18n強制（既存キー使用・問題なし）
- ADR-067: デザイントークン（変更なし）
- ADR-144: UIガバナンス（既存金型のみ・変更なし）
