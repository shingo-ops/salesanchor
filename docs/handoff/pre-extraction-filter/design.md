# design: Gemini呼び出し前事前フィルタ

## 設計根拠

PO承認済みのタスク指示書に基づく実装。

## 動作フロー

```
メッセージ到着
  → 空チェック（既存: C94） → status='empty'
  → 事前フィルタ（C95）:
      層1 message_exclude キーワードにマッチ → status='filtered'
      層2 message_exclude_no_digit キーワードにマッチ ＋ 数字なし → status='filtered'
  → どれにも該当しない → Geminiに送る（従来どおり）
```

## KGI/KPI

| 基準 | 検証方法 |
|------|----------|
| message_exclude ルールにマッチしたメッセージが status='filtered' になること | テスト: `test_run_extraction_returns_filtered_when_pre_filter_matches` PASSED |
| message_exclude_no_digit + 数字なし → filtered | テスト: `test_run_extraction_no_digit_no_digit_filtered` PASSED |
| message_exclude_no_digit + 数字あり → Geminiに送る | テスト: `test_run_extraction_no_digit_condition` PASSED |
| ルールなし → 全メッセージGeminiに送る | テスト: `test_run_extraction_empty_rules_all_pass_to_gemini` PASSED |

## 外部事例

LINEシステム通知フィルタリングは一般的なWebhook受信実装のベストプラクティス。
キーワードベース事前フィルタはコスト効率のための標準的アプローチ。

## 影響範囲

### 変更
- `backend/app/tasks/tcg_extraction.py`: フィルタ関数追加 + 空チェック直後に挿入
- `backend/app/services/tcg_analysis_dashboard_svc.py`: error_rate母数修正 + by_statusにfiltered追加
- `backend/app/routers/tcg_analysis_dashboard.py`: ExtractionByStatusスキーマ拡張

### フロントエンド
- `KnowledgeAliasesTab.tsx`: RULE_CATEGORIESに2値追加（管理UIでルール登録可能に）
- `ja.json` / `en.json`: i18nキー追加

### 変更しないもの
- DBスキーマ（migration不要）
- 既存の skip_condition 13件
- 初期キーワードデータ（POが管理画面から投入）

## 戻し方

コミットをrevertするだけ。DBスキーマ変更なし。
