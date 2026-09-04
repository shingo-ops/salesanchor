# MIG-04 Stage 1: LINE エクスポート取り込み — Recon

作成日: 2026-09-05  
ブランチ: `release/tcg-line-import-stage1`  
担当: Hikky-dev

---

## 前提調査（IMP-R1〜R3）

### 閉鎖した旧 PR（IMP-01 で完了）
| PR | ブランチ | 理由 |
|----|--------|------|
| #3159 | feature/mig04/import | origin/main から 440 コミット遅れ・main.py 競合（6 ルーター欠落） |
| #3160 | feature/mig04/analysis | 同上 |
| #3162 | feature/mig04/ui | 同上 |
| #3165 | feature/mig04/integration | 同上 |

全ブランチは閉鎖後も remote に保持（--delete-branch 禁止）。

### 移植元ブランチ
- `origin/release/tcg-migration-phase4` — サービス・ルーター・テスト取得先
- `origin/mig04/import` — フロント TcgLineImportPage 旧版（hex 汚染 12 件）

### スコープ確定（Stage 1 = Import-only）

**Stage 1 が書くテーブル:**
- `source_messages` (INSERT + UPDATE superseded_by)
- `extraction_jobs` (INSERT, status='pending')
- `import_jobs` (INSERT)

**Stage 1 が触らないもの:**
- `analysis_results` — `tcg_extraction.py → analyze_extraction_job()` 経由のみ。このファイルを含まない。
- `extraction_items` — 同上
- `tcg_extraction.py`, `gemini_extraction_svc.py`, `tcg_analyzer_svc.py` — 含まない
- `celery_app.py` の `include` リスト — stage 1 は tcg_extraction task を登録しない

### `_enqueue_extraction` の挙動
- `tcg_extraction.py` が worker に未登録のため、stage 1 では Celery エンキューは no-op（例外をキャッチしてログのみ）
- Redis/Celery は本番で稼働中だが、task が登録されるのは stage 2 以降

### マイグレーション確認
```
migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:23
```
`supplier_channels`・`source_messages`・`import_jobs` の 3 テーブルは既存マイグレーション済み → **新規 migration 不要**

### 関連 ADR
- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（全 UI 文字列 t() 経由）
- `docs/adr/ADR-072*` — write endpoint: db.commit() 後 reset_tenant_context() 必須
  → 本実装は super-admin 専用（tenant-context なし）、lint_tenant_schema.py OK 確認済み
- `docs/adr/ADR-067*` — デザイントークン強制（hex 禁止）

### 競合確認（append-only 戦略）
| ファイル | 戦略 |
|---------|------|
| `backend/app/main.py` | routers import + include_router を追記のみ（既存 6 ルーター不変） |
| `frontend/src/App.tsx` | import + Route を追記のみ（既存ルート不変） |
| `frontend/src/locales/ja.json` | tcgLineImport キーブロックを末尾追加（削除なし） |
| `frontend/src/locales/en.json` | 同上 |
| `frontend/src/index.css` | --color-error/success/warning 系 8 変数を :root + :root.force-dark に追加 |

### バグ発見: parse_line_export 日付境界バグ
- **症状**: 日付行が来たとき、直前のメッセージが破棄される
- **根拠**: `/backend/app/services/tcg_line_import_svc.py` の date_m ハンドラ内で `current_msg = None` 前に `messages.append(current_msg)` がなかった
- **修正**: `test_parse_multiple_date_blocks` でレッドを確認後、date_m ブロックに append 処理を追加（グリーン）

### CSS 変数: 追加対象
以下は `index.css` に未定義だったが `TcgLineImportPage` および既存ファイルで使用:
```
:root 追加:
  --color-error: #b91c1c
  --color-error-bg: #fef2f2
  --color-error-border: #fca5a5
  --color-success: #15803d
  --color-success-bg: #f0fdf4
  --color-success-border: #86efac
  --color-warning-bg: #fffbeb
  --color-warning-border: #fcd34d

:root.force-dark 追加（dark-parity 維持）:
  --color-error: #f87171
  --color-error-bg: rgba(239, 68, 68, 0.15)
  --color-error-border: rgba(239, 68, 68, 0.4)
  --color-success: #4ade80
  --color-success-bg: rgba(34, 197, 94, 0.12)
  --color-success-border: rgba(34, 197, 94, 0.4)
  --color-warning-bg: rgba(251, 191, 36, 0.12)
  --color-warning-border: rgba(251, 191, 36, 0.4)
```
