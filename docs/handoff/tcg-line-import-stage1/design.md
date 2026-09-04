# MIG-04 Stage 1: LINE エクスポート取り込み — 設計書

作成日: 2026-09-05  
ADR 参照: ADR-027, ADR-067, ADR-072  
recon 参照: `docs/handoff/tcg-line-import-stage1/recon.md`

---

## KGI

**LINE GAS からサーバーサイドへの取り込みパイプライン（stage 1）が本番で動作し、`source_messages` + `extraction_jobs` + `import_jobs` に正しく書き込まれること**

KPI（PO が画面・ログで一義に判定できる粒度）:
| KPI | 検証方法 |
|-----|---------|
| POST /api/v1/tcg/line-import が 200 を返す | curl or UI アップロード |
| import_jobs に行が追加される | `SELECT * FROM import_jobs ORDER BY created_at DESC LIMIT 1` |
| 同一ファイル再送で `"status": "already_imported"` が返る | UI で同ファイルを再送 |
| source_messages に is_active=TRUE 行が追加される | DB 確認 |
| 旧 is_active=TRUE 行が superseded_by 設定済みで FALSE になる | DB 確認 |
| GET /api/v1/tcg/line-import/history が履歴を返す | UI の履歴テーブル |

---

## 変更ファイル一覧

### 新規作成
| ファイル | 役割 |
|---------|------|
| `backend/app/services/tcg_line_import_svc.py` | LINE テキストパース・サプライヤー解決・DB 書き込みロジック |
| `backend/app/routers/tcg_line_import.py` | FastAPI ルーター（3 エンドポイント） |
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx` | アップロード UI・履歴テーブル（ADR-027 i18n 対応済み） |
| `backend/tests/test_tcg_line_import.py` | 単体テスト 29 件（DB 不要・parse/resolve/build/window ロジック網羅） |
| `docs/handoff/tcg-line-import-stage1/recon.md` | 現在地把握 |
| `docs/handoff/tcg-line-import-stage1/design.md` | 本ファイル |

### 既存ファイルへの追記
| ファイル | 変更内容 | 触らない範囲 |
|---------|---------|-----------|
| `backend/app/main.py` | `tcg_line_import` の import + `include_router` を追記 | 既存 6 ルーターの import/include 行 |
| `frontend/src/App.tsx` | `TcgLineImportPage` の import + Route を追記 | 既存全ルート |
| `frontend/src/locales/ja.json` | `tcgLineImport` キーブロックを末尾追加 | 既存全キー |
| `frontend/src/locales/en.json` | 同上 | 既存全キー |
| `frontend/src/index.css` | 8 変数を :root + :root.force-dark に追加 | 既存変数定義 |

---

## 設計詳細

### 24h ウィンドウ自動計算（新機能）
**Why**: GAS の `Latest24LineImport` は「直近24時間」しか取り込まない設計。旧 PR のコードは `window_start` パラメーターを受け取るだけで自動計算がなかった。

**How**:
```python
# tcg_line_import_svc.py:import_line_export()
if effective_window_start is None and window_hours > 0:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    effective_window_start = cutoff.strftime("%Y-%m-%d %H:%M:%S")
```

- `window_hours=24`（デフォルト）: 直近 24h のメッセージのみ取り込み
- `window_hours=0`: フィルタなし（ファイル全体取り込み）
- `window_start` 明示指定時: 自動計算をスキップ（既存挙動を優先）

### エンドポイント
```
POST   /api/v1/tcg/line-import           multipart/form-data → ImportResultResponse
GET    /api/v1/tcg/line-import/history   → list[ImportJobResponse]
GET    /api/v1/tcg/line-import/unresolved → UnresolvedResponse
```
全エンドポイントに `require_super_admin` 依存注入。

### パースロジック（バグ修正含む）
GAS `parseLatest24LineExport` の Python 移植。以下のバグを修正:
- **日付境界バグ**: 旧コードは日付行到達時に `current_msg = None` するだけで未確定メッセージを破棄していた。`date_m` ブロックの先頭に `if current_msg: messages.append(current_msg)` を追加。

### サプライヤー解決
`display_name` の最長プレフィックス一致 → `tcg_suppliers.name` → `supplier_channels WHERE channel='line'`。未解決は取り込みを継続し `unresolved_display_names` に列挙。

### 冪等化
`import_jobs.raw_sha256 UNIQUE` 制約（スキーマ側）+ アプリ側チェック（`import_line_export` の先頭）。同一ファイルの再送は `"status": "already_imported"` を返しDB書き込みをスキップ。

### Celery エンキュー
`_enqueue_extraction()` は `app.tasks.tcg_extraction` を動的 import。stage 1 では task 未登録のため import エラーを catch → ログのみ。本番 worker は接続エラーにならない。

---

## 弊害・リスク

| リスク | 評価 | 対策 |
|-------|------|------|
| main.py への追記が既存ルーターを破壊 | 低（append-only） | grep で既存 include_router が不変かを確認済み |
| CSS 変数追加が既存 UI の色を変更 | 低（新変数のみ追加） | check-dark-parity PASSED |
| `--color-error` を新規定義することで既存 `var(--color-error)` が変わる | 低（値が妥当な赤） | 既存 TSX/CSS は `--color-error` 未定義のまま使用（CSS fallback = ブラウザデフォルト空白）→ 新定義によりむしろ意図通りの赤が出る |
| 24h ウィンドウで本番データが切り詰められる | 中 | `window_hours=0` エスケープハッチで全件取り込み可 |

---

## 戻し方
```bash
# PRをリバートするだけ。migration なし・DB 変更なし
git revert <merge-commit>
```

---

## 外部事例
GAS → Python LINE パーサの移植は日本国内 B2B SaaS で一般的。主なパターン:
- Celery + Redis で非同期 Gemini 抽出（本実装の stage 2 相当）
- SHA-256 冪等化は LINE Bot SDK の公式推奨パターンに準拠
- Supplier prefix-match はグループチャット内の複数アカウント対応の標準手法
