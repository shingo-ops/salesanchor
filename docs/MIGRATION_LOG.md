# MIGRATION_LOG

このファイルはTCGマイグレーションの実施記録と結果を記録する。

---

## MIG-04: LINE取り込みの接続（方式A: エクスポートファイルのアップロード）

**実施期間**: 2026-08-30  
**実施者**: shingo-ops (claude-sonnet-4-6)  
**統合ブランチ**: `feat/tcg-migration-phase4`  
**main への PR**: 作成後停止（未マージ）

### 概要

GAS 運用（LINE エクスポートファイル → Gemini 抽出 → 商品照合）をサーバーサイドに移植し、
並行運用できる状態を実現する。

---

### Phase 1: 現行取り込み仕様確認 (READ ONLY)

| 項目 | 仕様 |
|------|------|
| ファイル形式 | UTF-8 テキスト (.txt) |
| 日付行パターン | `^(\d{4})\.(\d{2})\.(\d{2})\s+.+$` |
| 時刻行パターン | `^(\d{1,2}):(\d{2})\s+(.+)$` |
| 継続行 | 日付・時刻行でない行 → 直前メッセージに `\n\n` で追加 |
| SQR-05 | 同一 SP_ID の全メッセージを `\n\n` で結合、1行として保存 |
| モデル | gemini-3.6-flash（GAS デフォルト） |
| プロンプト | `RAW_EXTRACTION_V2_PROMPT_TEXT`（7列パイプ区切り） |

詳細仕様: `~/Documents/mig04_backup/mig04_report.md` §Phase 1

---

### Phase 2: アップロード取り込み (mig04/import → PR #3160)

**実装ファイル**:
- `backend/tcg_migration/alembic/versions/20260830_000000_mig04_import_tables.py`
  - `import_jobs` テーブル作成
  - `extraction_jobs.prompt_version` カラム追加
- `backend/app/services/tcg_line_import_svc.py`
  - `parse_line_export`, `resolve_suppliers`, `build_provider_entries`, `import_line_export`
- `backend/app/routers/tcg_line_import.py`
  - `POST /api/v1/tcg/line-import`, `GET /api/v1/tcg/line-import/history`, `GET /api/v1/tcg/line-import/unresolved`
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx`

**検収**: `backend/tcg_migration/tests/test_acceptance.py` 12件 PASS

---

### Phase 3: Gemini 構造化の接続 (mig04/gemini → PR #3160)

**実装ファイル**:
- `backend/app/services/gemini_extraction_svc.py` (google-genai SDK, gemini-3.6-flash)
- `backend/app/services/tcg_analyzer_svc.py` (name-first-v1 エンジン)
- `backend/app/tasks/tcg_extraction.py` (Celery タスク)

**モデル移行メモ**: `gemini-2.5-flash` → このAPIキーでは404。GASデフォルトの `gemini-3.6-flash` に統一。

**Gemini 検証結果** (2026-08-30, VS-01 3仕入元, Gemini消費 3/200リクエスト):

| SP_CODE | raw行数 | 既存件数(GAS) | 新規件数(Python) | 差分 | Jaccard |
|---------|--------|------------|----------------|------|---------|
| SP0004  | 323    | 91         | 91             | 0    | 0.969   |
| SP0011  | 52     | 14         | 14             | 0    | 1.000   |
| SP0023  | 625    | 198        | 198            | 0    | 0.967   |

**判定**: プロンプト移植は忠実（行数完全一致、商品名 Jaccard 0.967〜1.000）

---

### Phase 4: 並行運用比較レポート (mig04/parallel → PR #3161)

**実装ファイル**:
- `backend/app/services/tcg_parallel_report_svc.py`
- `backend/app/routers/tcg_parallel_report.py`
  - `GET /api/v1/tcg/parallel-report`
- `frontend/src/pages/super-admin/TcgParallelReportPage.tsx` (UNVERIFIED)

**比較結果** (2026-08-30, 1,626件, 44仕入元):

| 指標 | compat-v1 (GAS) | name-first-v1 (Server) | 差分 |
|------|----------------|------------------------|------|
| PID解決率 | 78.8% | 52.0% | **-26.8%** |
| PID解決数 | 1,282/1,626 | 845/1,626 | -437 |

改善: 2仕入元 / 後退: 34仕入元 / 変化なし: 8仕入元

**考察**: name-first-v1 のキーワード整備が切り替えの前提条件。
後退が大きい仕入元（例: SP0122, SP0139, SP0044）から優先的にキーワードを追加する必要がある。

---

### Phase 5: 検収 (mig04/acceptance → PR #3162)

**テストファイル**: `backend/tcg_migration/tests/test_mig04_acceptance.py`

| 検収条件 | テスト数 | 結果 |
|---------|---------|------|
| 冪等性（DB制約確認） | 2 | ✅ PASS |
| supersede カラム確認 | 2 | ✅ PASS |
| 未知投稿者ロジック（単体） | 2 | ✅ PASS |
| Gemini記録カラム確認 | 1 | ✅ PASS |
| import_jobs スキーマ確認 | 2 | ✅ PASS |
| sha256 ユーティリティ（単体） | 2 | ✅ PASS |
| Phase 3 比較値不変 | 3 | ✅ PASS |
| SQR-05 ロジック（単体） | 2 | ✅ PASS |
| システムイベント除外（単体） | 1 | ✅ PASS |
| 回帰（MIG-02 基準値） | 4 | ✅ PASS |
| **合計** | **21** | **✅ 全 PASS** |

既存 MIG-02 テスト: 12/12 PASS（回帰なし）

---

### Gemini 消費数

| フェーズ | リクエスト数 | 備考 |
|---------|------------|------|
| Phase 3 検証 | 3 | SP0004, SP0011, SP0023 各1回 |
| **合計** | **3/200** | 残り 197 |

---

### 成果物

| 成果物 | 場所 |
|--------|------|
| 統合ブランチ | `feat/tcg-migration-phase4` |
| main への PR | 作成後停止（未マージ） |
| 実施レポート | `~/Documents/mig04_backup/mig04_report.md` |
| 並行比較データ | `GET /api/v1/tcg/parallel-report` |
| Phase 5 テスト | `backend/tcg_migration/tests/test_mig04_acceptance.py` |

---

### 次フェーズへの申し送り事項

1. **name-first-v1 キーワード整備**: PID解決率 78.8% → 52.0% の差は主にキーワード不足。
   後退幅が大きい仕入元から着手する。

2. **Celery + Redis**: Phase 3 の抽出タスクは Celery 設計だが、
   ローカル検証は Redis なしで直接呼び出した。
   本番稼働前に Redis を有効化してエンドツーエンドを確認すること。

3. **テナント DB 対応**: `myapp_db` は TCG 専用スキーマのみ。
   本番 DB との統合時に Alembic マイグレーションを実行すること。

4. **未知投稿者の登録 UI**: Phase 2 で「未登録一覧」は API から取得できるが、
   画面からの `tcg_suppliers` への登録導線は未実装。
