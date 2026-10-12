# Design: 抽出プロンプトDB管理化

## 概要

Gemini抽出プロンプト（現在ハードコード）をDBで管理し、管理画面から編集可能にする。
同時にバグ3件を修正する。

## 変更一覧

### A. extraction_prompt_config テーブル新設
- "public.extraction_prompt_config"（supplier別ではなく、システム全体で共通）
- prompt_key: 'base_extraction' / 'work_id_extraction' の2種類

### B. API
- GET /super-admin/extraction-prompts — 全件取得
- GET /super-admin/extraction-prompts/{key} — 単一取得
- PUT /super-admin/extraction-prompts/{key} — upsert

### C. フロントエンド管理UI
- AnalysisRulesPage のサイドバーに「抽出プロンプト設定」タブ追加
- ExtractionPromptConfigTab.tsx 新設

### D. パイプライン配線
- DB値優先、なければハードコード定数にフォールバック

### E. バグ修正3件
1. _resolve_pid の '-' ガード追加
2. WORK_ID_PROMPT_TEXT の「コード」→「ID（数値）」矛盾修正
3. product_id=61 の product_code='-' を 'S-PS' に修正

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| extraction_prompt_config テーブルが存在する | "\d public.extraction_prompt_config" |
| GET/PUT APIが動作する | curl確認 |
| 管理画面でプロンプト表示・編集できる | ブラウザ確認 |
| "-" が _resolve_pid で None になる | テスト |
| product_id=61 の product_code が '-' でない | SELECT確認 |

## 外部・過去事例の参照と我々への応用

- 既存 "public.supplier_prompts" テーブル（migrations/087_create_supplier_prompts.sql）と同パターン
  - trigger関数名・インデックス命名規則・COMMENTパターンを踏襲
- 同期DB接続は "tcg_product_master_svc.py" の "_SYNC_DB_URL" パターンを踏襲
  - Celeryタスク内の同期関数のため asyncpg ではなく psycopg2 互換URLを使用

## 維持の仕組み

- 将来的なプロンプトバージョン管理: "version" カラムで追跡可能
- フォールバック: DBにレコードがない/空文字の場合はハードコード定数を使用（パイプライン停止しない）
- 守り手: pipeline-team（Shingo）
