# design — Gemini呼び出し前事前フィルタ

**対象ADR**: ADR-100  
**recon**: docs/handoff/pre-extraction-filter/recon.md  
**日付**: 2026-09-27  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: LINEシステム通知フィルタリング（Webhook受信の一般的なベストプラクティス）→ 我々への応用: 参加・退出・アナウンス等のシステム通知をキーワードで事前除外し、Gemini呼び出しコストを削減
- 事例2: キーワードベース事前フィルタ（メール/チャットのスパムフィルタ等）→ 我々への応用: knowledge_rulesテーブルの既存インフラを流用し、運用者がUIからフィルタルールを追加・変更可能に設計

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| message_exclude ルールにマッチしたメッセージが status='filtered' になること | テスト: `test_run_extraction_returns_filtered_when_pre_filter_matches` PASSED |
| message_exclude_no_digit + 数字なし → filtered | テスト: `test_run_extraction_no_digit_no_digit_filtered` PASSED |
| message_exclude_no_digit + 数字あり → Geminiに送る | テスト: `test_run_extraction_no_digit_condition` PASSED |
| ルールなし → 全メッセージGeminiに送る | テスト: `test_run_extraction_empty_rules_all_pass_to_gemini` PASSED |

---

## 動作フロー

```
メッセージ到着
  → 空チェック（既存: C94） → status='empty'
  → 事前フィルタ（C95）:
      層1 message_exclude キーワードにマッチ → status='filtered'
      層2 message_exclude_no_digit キーワードにマッチ ＋ 数字なし → status='filtered'
  → どれにも該当しない → Geminiに送る（従来どおり）
```

---

## 技術 How・KPI

- KPI: フィルタされたメッセージ数が extraction_jobs.status='filtered' として記録される
- 技術選択: knowledge_rules テーブル流用（理由: 既存インフラを拡張、新テーブル不要）

---

## 影響範囲

### 変更
- `backend/app/tasks/tcg_extraction.py`: フィルタ関数追加 + 空チェック直後に挿入
- `backend/app/services/tcg_analysis_dashboard_svc.py`: error_rate母数修正 + by_statusにfiltered追加
- `backend/app/routers/tcg_analysis_dashboard.py`: ExtractionByStatusスキーマ拡張

### フロントエンド
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx`: RULE_CATEGORIESに2値追加（管理UIでルール登録可能に）
- `frontend/src/locales/ja.json` / `frontend/src/locales/en.json`: i18nキー追加

### 変更しないもの
- DBスキーマ（migration不要）
- 既存の skip_condition 13件
- 初期キーワードデータ（POが管理画面から投入）

---

## 弊害・トレードオフ

- フィルタルール誤設定リスク → 対策: 管理UIからルール変更可能、filtered件数をダッシュボードで監視

---

## 戻し方

コミットをrevertするだけ。DBスキーマ変更なし。

---

## 維持の仕組み

- 守り手: 人手で守る（knowledge_rulesのカテゴリ追加時に管理UIのRULE_CATEGORIESとi18nキーを同時更新すること）
- 継続監視: ダッシュボードの filtered カウントを定期確認
