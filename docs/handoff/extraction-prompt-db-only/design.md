# design: ハードコードプロンプト廃止 + エラーログページ

## 参照
- recon: docs/handoff/extraction-prompt-db-only/recon.md
- ADR-158, ADR-027, ADR-144

## 変更1: ハードコードプロンプト削除 + DB必須化

### 変更前
`_load_db_prompts()` は PROMPT_TEXT / WORK_ID_PROMPT_TEXT をフォールバックとして使用。DB取得失敗時は黙って旧定数で継続。

### 変更後
フォールバックを廃止。DB取得失敗・プロンプト未登録時は RuntimeError を発生させる。

| 基準 | 検証方法 |
|------|---------|
| PROMPT_TEXT/WORK_ID_PROMPT_TEXT がコードに存在しない | grep -rn "PROMPT_TEXT" backend/ |
| DB未登録時に RuntimeError が発生する | ユニットテストでモック注入 |
| ruff lint 通過 | ruff check backend/ |

### 影響範囲
- `backend/app/services/gemini_extraction_svc.py` — 定数削除 + 関数修正
- `backend/tests/test_tcg_gemini_extraction.py` — import 修正 + テスト修正

## 変更2: エラーログAPIエンドポイント

### 設計
- パス: `GET /api/v1/tcg/extraction-errors`
- 認証: require_super_admin
- パラメータ: offset, limit（ページネーション）
- JOIN: extraction_jobs → source_messages → supplier_channels → suppliers

| 基準 | 検証方法 |
|------|---------|
| エンドポイントが 200 を返す | API直接呼び出し |
| supplier_name が含まれる | レスポンスボディ確認 |

## 変更3: フロントエンド エラーログページ

### 設計
- 新規コンポーネント: `ExtractionErrorLogPanel.tsx`
- DataTable + Card 金型使用
- ページネーション（50件ずつ）
- i18n: analysisRules.errorLog.*

| 基準 | 検証方法 |
|------|---------|
| サイドバーから遷移できる | 画面確認 |
| テーブルにエラーが表示される | 画面確認 |
| ハードコード日本語なし | ESLint |

## 外部・過去事例の参照と我々への応用
- 既存: AnalysisDashboardPanel の recent_errors テーブル（同パターンで DataTable + Card 使用）
- 既存: supplier_pipeline API の extraction_jobs → source_messages → supplier_channels → suppliers JOIN パターン
- 我々への応用: 同じ JOIN パターンをエラーログ専用エンドポイントに流用。既存パターンと一致させることで実装差分を最小化。

## 維持の仕組み
- PROMPT_TEXT/WORK_ID_PROMPT_TEXT が残っていないことは `grep -rn "PROMPT_TEXT" backend/` で CI 時に確認可能
- DB必須化により、プロンプト未登録時は起動時ではなく抽出実行時に RuntimeError が発生する（運用で管理画面から登録済みであることが前提）

## 守り手（戻し方）
コード変更のみ（migration/DB変更なし）。PRを revert すれば元の状態に戻る。
