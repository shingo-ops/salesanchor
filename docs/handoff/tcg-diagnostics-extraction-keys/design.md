# design: tcg-diagnostics-extraction-keys

**対象 ADR**: ADR-154, ADR-027
**recon**: docs/handoff/tcg-diagnostics-extraction-keys/recon.md

## 設計方針

既存の固定 SQL 診断 API（`_ALLOWED_KEYS` + `_QUERIES`）に、抽出パイプラインの
ヘルス監視用キーを4つ追加する。既存の作法（TCG_SCHEMA 定数・f-string・SELECT のみ）を踏襲し、
外部入力を SQL に渡さない設計を維持する。

## 追加キーと SQL 設計

| キー | 目的 | LIMIT |
|------|------|-------|
| extraction-errors | Gemini エラーで終了したジョブの一覧（最新100件） | 100 |
| extraction-pending | 処理待ちジョブの一覧（最古優先・最大100件） | 100 |
| extraction-running-stale | 10分超 running のままのジョブ（例外未捕捉残留の検出） | なし（全件・通常0件想定） |
| analysis-missing | done 済みジョブで analysis_results が存在しない照合漏れ | なし（全件・通常0件想定） |

### extraction-running-stale の閾値
`soft_time_limit=100秒`（Celery task 定義）の約 6 倍余裕を持たせた 10 分を採用。
DB 側で `INTERVAL '10 minutes'` を直値で埋め込み（変更時はコード修正で対応）。

### analysis-missing の NOT EXISTS
`NOT EXISTS (SELECT 1 FROM analysis_results WHERE extraction_item_id = ei.id)` で
任意の extraction_items に analysis_results が欠落しているジョブを検出。
部分的欠落（一部 items のみ未照合）も含む。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 4キーが `_ALLOWED_KEYS` に追加されている | `backend/app/services/tcg_diagnostics_svc.py:19` を grep |
| 4 SQL が `_QUERIES` に追加されている | 同ファイル `_QUERIES` dict に4エントリ存在 |
| 4キーのテストがそれぞれ 200 + 形状検証 | `backend/tests/test_tcg_diagnostics.py` pytest PASS |
| 未知キーエラーに8キー全てが含まれる | `test_unknown_key_returns_400` PASS |
| DiagnosticsDrawer に4セクション追加 | `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx` に4つの `DiagnosticsSection` がある |
| extraction-running-stale と analysis-missing の行が赤表示 | `highlight={() => true}` がある |
| ja.json / en.json のキー数が一致 | `sections` 8キー / `columns` 18キー が両ファイルに存在 |

## ハイライトロジック

- `extraction-running-stale`: `highlight={() => true}` — 行が存在する時点で異常（0件正常）
- `analysis-missing`: `highlight={() => true}` — 行が存在する時点で異常（0件正常）
- `extraction-errors` / `extraction-pending`: highlight なし（情報表示のみ）

## 設計選択

### highlight={() => true} の採用理由
行が存在すること自体が異常を意味するため、行ごとの値条件なしに全行赤表示。
件数0のとき `DiagnosticsSection` は "データなし" 表示になるため赤は一切出ない。

### LIMIT 100 の採用（errors/pending のみ）
エラー蓄積が大量の場合に UI が崩れないよう上限を設ける。
stale/missing は通常0件想定のため LIMIT なし。

## 外部・過去事例

- OWASP Top 10 A03 Injection: 固定 SQL マップ方式（Stored SQL Map）でインジェクションを防止
- ADR-154 §設計判断: `_ALLOWED_KEYS` frozenset による完全一致制限
- 既存 DiagnosticsDrawer の orphan-messages: `highlight={(row) => Number(row.null_channel_count) !== 0}` ― 行値ベースの条件ハイライトの先例

## 維持の仕組み

守り手: `backend/tests/test_tcg_diagnostics.py` — 8キー全ての `200 + 形状` テスト + `400 + キー一覧` テストが、新キー追加忘れ・削除・キー名変更を検出する
