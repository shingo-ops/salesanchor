# MIG-04 Stage 2: Gemini 抽出移植 — 設計書

作成日: 2026-09-05  
ADR 参照: ADR-154  
recon 参照: `docs/handoff/tcg-gemini-extraction-stage2/recon.md`

---

## KGI

**Gemini 抽出パイプライン（stage 2）が本番で動作し、`extraction_jobs` + `extraction_items` に正しく書き込まれること。かつ GAS の抽出結果と同等のプロンプトが送信されること。**

受け入れ基準（PO が画面・ログで一義に判定できる粒度）:

| 基準 | 検証方法 |
|-----|---------|
| `extract_and_analyze_source_message(sm_id)` が `"status": "done"` を返す | Docker exec で直接呼び出し |
| `extraction_jobs.status` が `done` / `empty` / `error` のいずれかに更新される | DB 確認: `SELECT status FROM tenant_004.extraction_jobs ORDER BY extracted_at DESC LIMIT 1` |
| `extraction_items` に行が追加される（status='done' 時） | DB 確認: `SELECT COUNT(*) FROM tenant_004.extraction_items WHERE extraction_job_id = '<ej_id>'` |
| ログに `[gemini_extraction] calling Gemini API` が出る | `docker compose logs backend --tail=50` |
| `TCG_AUTO_ANALYZE` 未設定時ログに `解析はスキップ（フラグ未設定）` が出る | 同上 |
| Celery worker が `tcg.extract_source_message` タスクを認識する | `celery inspect registered` |

---

## 変更ファイル一覧

### 新規作成
| ファイル | 役割 |
|---------|------|
| `backend/app/services/gemini_extraction_svc.py` | Gemini API 呼び出し・レスポンスパース（GAS 完全準拠） |
| `backend/app/tasks/tcg_extraction.py` | Celery タスク定義 + 同期抽出ロジック（DB 書き込み） |
| `backend/tests/test_tcg_gemini_extraction.py` | 単体テスト 18 件（DB 不要・Gemini 実 API 呼び出しなし） |
| `docs/handoff/tcg-gemini-extraction-stage2/recon.md` | 現在地把握 |
| `docs/handoff/tcg-gemini-extraction-stage2/design.md` | 本ファイル |

### 既存ファイルへの追記
| ファイル | 変更内容 | 触らない範囲 |
|---------|---------|-----------|
| `backend/app/celery_app.py` | `"app.tasks.tcg_extraction"` を include リストに 1 行追記 | 既存 11 タスク定義・beat_schedule 全エントリ |
| `backend/requirements.txt` | `google-genai>=1.0.0` を追記 | `google-generativeai` は削除しない（inventory_parser_llm.py が使用中） |

### 変更しないファイル
- `backend/app/services/tcg_analyzer_svc.py`（origin/main の v2 をそのまま呼ぶ）
- migration ファイル一切（テーブルは作成済み）

---

## 設計詳細

### プロンプト連結（GAS 完全一致）

```python
# gemini_extraction_svc.py: call_gemini_extraction()
full_prompt = f"{PROMPT_TEXT}\n\n原文:\n{prompt_input}"
```

GAS `RawExtractionV2.js` の連結式: `PROMPT_TEXT + '\n\n原文:\n' + input` と完全一致。  
移植元 PR #3165 は `原文:\n` が欠落していた → Stage 2 で修正済み。

### スキーマ修飾（全 SQL に `tenant_004.` 付与）

```python
# tcg_extraction.py
TCG_SCHEMA = "tenant_004"

text(f"SELECT ej.id, sm.raw_text FROM {TCG_SCHEMA}.extraction_jobs ej ...")
text(f"UPDATE {TCG_SCHEMA}.extraction_jobs SET status = 'running' ...")
text(f"INSERT INTO {TCG_SCHEMA}.extraction_items ...")
text(f"UPDATE {TCG_SCHEMA}.extraction_jobs SET status = :status ...")
```

4 件全件 f-string で確認済み（`grep -n` + awk で直後行が `f` であることを検証）。

### 解析発火フラグ

```python
# tcg_extraction.py: _run_extraction()
auto_analyze = os.environ.get("TCG_AUTO_ANALYZE", "").strip() == "1"
if final_status == "done":
    if auto_analyze:
        analysis_stats = analyze_extraction_job(session, extraction_job_id)
    else:
        logger.info("[tcg_extraction] 解析はスキップ（フラグ未設定）: ej=%s", ...)
```

- `TCG_AUTO_ANALYZE` 未設定 → 解析スキップ（既定 OFF）
- `TCG_AUTO_ANALYZE=1` → `analyze_extraction_job()` を呼ぶ
- `docker-compose.yml` への変数追加は今回対象外（既定 OFF のため不要）

### Celery タスク登録

```python
# tcg_extraction.py 末尾
@celery_app.task(name="tcg.extract_source_message", ...)
def extract_source_message_task(self, source_message_id: str) -> dict: ...
```

Redis 未起動時は `except` で catch してモジュールのみ提供（worker クラッシュしない）。

### google-genai SDK

`inventory_parser_llm.py` が `google-generativeai` (旧 SDK) を使用中のため、削除しない。  
新規の `google-genai>=1.0.0` は並存可能（別パッケージ）。

---

## 弊害・リスク

| リスク | 評価 | 対策 |
|-------|------|------|
| `google-genai` と `google-generativeai` の並存で名前衝突 | 低（別 PyPI パッケージ・別 import 名） | requirements.txt に両方明記 |
| `TCG_AUTO_ANALYZE` 誤設定で解析が意図せず発火 | 低（既定 OFF・文字列 "1" のみ ON） | テストで OFF/ON 両方検証済み |
| celery_app.py 追記が既存タスクを破壊 | 低（include リストへの append-only） | 既存 11 エントリ不変を diff で確認 |
| SQL スキーマ未修飾で tenant_004 以外のスキーマにアクセス | 排除済み | テスト `test_tcg_extraction_sql_has_schema_prefix` で機械的に検証 |

---

## 戻し方

```bash
# PRをリバートするだけ。migration なし・DB 変更なし
git revert <merge-commit>
```

---

## 外部・過去事例の参照と我々への応用

**GAS → Python Gemini API 移植の実績:**
- GAS の `UrlFetchApp.fetch` は同期 HTTP 呼び出し → Python 同期 SDK (`models.generate_content`) で同等実装
- `temperature=0` による冪等性確保は Gemini API 公式推奨パターン
- Celery タスクで外部 API を呼ぶ際の `try/except` + retry パターンは salesanchor 既存タスク（`avatar.py`, `refresh_meta_tokens.py`）と統一

**IMP-05 教訓（SQL スキーマ忘れ）の横展開:**
- `tcg_line_import_svc.py`（Stage 1）で確立した `TCG_SCHEMA = "tenant_004"` + `text(f"...")` パターンを踏襲
- ソースコード検査テスト（`test_tcg_extraction_sql_has_schema_prefix`）を追加して、f-string 忘れを CI で自動検出

---

## 維持の仕組み + 守り手

| 層 | 仕組み | 守り手 |
|----|--------|--------|
| SQL スキーマ修飾 | `TCG_SCHEMA` 定数 + f-string | `test_tcg_extraction_sql_has_schema_prefix`（CI で自動実行） |
| プロンプト GAS 一致 | `test_full_prompt_contains_genshi_prefix` | CI |
| 解析フラグ OFF 既定 | `TCG_AUTO_ANALYZE` 未設定で OFF | `test_auto_analyze_off_skips_analyze` |
| tcg_analyzer_svc.py 不変 | Stage 2 スコープ外（禁止ファイル） | PR 差分レビュー |
