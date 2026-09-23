# Design: 仕入元抽出ルール実装

## KGI

仕入元ごとの抽出ルールをDBに保持し、Geminiプロンプトに注入することで
unit_ng件数を削減できる基盤を整備する。

| 基準 | 検証方法 |
|---|---|
| `/super-admin/suppliers/{id}/extraction-rules` PATCH → GET で保存値が返る | API呼び出しで確認 |
| `extraction_notes` を設定した仕入元のGemini呼び出しでプロンプトにルール文字列が含まれる | ログ確認 |
| 1行壊れ + N行正常のGeminiレスポンスで N件が extraction_items に保存される | テスト確認 |
| `public.unit_aliases` で `冊`, `OX`, `ﾏｽﾀｰｶｰﾄﾝ` が解決できる | SELECT確認 |

## 設計決定

### suppliers テーブルへの直接列追加
- `supplier_prompts` テーブルとは別に `extraction_*` 列を `suppliers` に追加
- 理由: ルール内容は仕入元に1:1で存在し、NULL許容のため別テーブル不要

### parse_extraction_response 戻り値変更
- `list[dict]` → `tuple[list[dict], list[dict]]` (items, parse_errors)
- 行単位で try/except を囲み、成功行を部分保存
- ヘッダー欠落は従来通り全体 ValueError（前提条件違反のため）

### supplier_context 注入経路
- Celeryタスク `_run_extraction()` → `_run_recorded_extraction()` → `extract_message()` → `call_gemini_extraction()`
- DBアクセスはタスク層で実施し、サービス層には dict を渡す（サービス層の同期DB依存を回避）

## 影響範囲

- `parse_extraction_response` の戻り値変更: 呼び出し元3ファイルを全修正済み
  - `backend/app/tasks/tcg_extraction.py`
  - `backend/tests/test_tcg_gemini_extraction.py`
  - `backend/tests/test_tcg_work_id.py`
  - `backend/tests/test_tcg_extraction_record_integrity_pg.py`
- `call_gemini_extraction` のシグネチャ変更: 後方互換（`supplier_context=None` デフォルト）

## 戻し方

- Migration は additive-only のためロールバック不要（列はNULL許容）
- コード変更は git revert で戻せる

## 外部・過去事例の参照と我々への応用

- Gemini系の部分保存パターン: エラー行をスキップして続行するアプローチは
  ChatGPT Batch API などでも採用される標準パターン。
  今回は行単位 try/except でエラーを `parse_errors` に収集し、成功行は保存する。
- 仕入元ルール注入: OpenAI Assistants API の System Message 活用パターンと同様に、
  仕入元固有のコンテキストをシステムプロンプトに注入することで抽出精度を向上させる。

## 維持の仕組み

- `extraction_*` 列は NULL 許容のため、ルール未設定の仕入元は従来通り動作する
- `supplier_context` パラメータはオプション（`None` デフォルト）のため後方互換
- `parse_extraction_response` の戻り値変更は全呼び出し元で対応済み
