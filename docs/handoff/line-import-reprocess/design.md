# 設計: LINE取り込み自動化 3改修

recon: `docs/handoff/line-import-reprocess/recon.md`
対象ADR: ADR-027（i18n強制）、ADR-072（テナントスキーマプレフィクス強制）

## 変更1: already_imported を成功表示

### How
TcgLineImportPage.tsx の result.review_status !== "pending_review" セクションで、
already_imported 判定による警告色条件式を削除し、常に成功色（--color-success-border / --color-success-bg）と t("tcgLineImport.importComplete") を表示する。

### KPI / 検証方法
同一ファイルを再アップロードしたとき、画面に成功色バナーが表示される。

### 弊害
なし。バックエンドの動作は変えない。already_imported キーは API レスポンスに残るが UI では使わなくなる。

## 変更2: 未解決仕入元の自動登録

### How
import_line_export() の step 4b として、resolve_suppliers() が返す unresolved リストに対して
public.suppliers INSERT + UPDATE supplier_code + tenant_004.supplier_channels INSERT を実行し、
得られた sp_code を resolved_msgs に追加する。unresolved_count は常に 0 になるため
step 5 は常に「全件解決済み」パスを通る。

既存の pending_review 分岐は削除する。resolve/commit エンドポイントは維持する（既存保留ジョブ対応のため）。

参照元ロジック: `backend/app/routers/tcg_line_import.py`

### KPI / 検証方法
未登録仕入元を含む .txt アップロード後、public.suppliers に該当 line_name の行が追加され、
review_status='ok' で返ること。

### 弊害
- 誤った仕入元名がそのまま登録される可能性（意図的な設計: PO 確認済み）
- 既存の「保留→手動確認→commit」フローは使われなくなるが、APIは残す

## 変更3: 解析完了後の自動配信

### How
_run_recorded_extraction() の step 6 で、TCG_AUTO_ANALYZE=1 かつ TCG_AUTO_DISTRIBUTE=1 の時、
analyze_extraction_job() 正常完了後に _enqueue_auto_distribute() を呼び出す。
auto_distribute_after_analysis_task は asyncio.run() で run_distribution() を同期呼び出しする。

### KPI / 検証方法
TCG_AUTO_DISTRIBUTE=1 環境下で extraction 完了後に run_distribution() が呼ばれること（ログ確認）。

### 弊害
- 安全装置 #8/#8b/#8c が pending ジョブを検知した場合はスキップ（正常動作）
- needs_review=TRUE アイテムは run_distribution() の確定フィルターで除外済み

## 外部・過去事例の参照と我々への応用

- 同パターンは `backend/app/routers/tcg_line_import.py` の resolve action='create' に実装済み（ロジック転用）。
- asyncio.run() での async → sync 呼び出しは Python 公式推奨パターン（Celery worker は同期コンテキストのため）。
- 守り手: run_distribution() の安全装置 #8/#8b/#8c が外部事例として機能（未完了ジョブがあれば自動スキップ）。

## 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | 同一ファイル再アップロードで成功色バナー表示 | 同じ .txt を2回アップロード → 2回目に緑色バナー表示 |
| 2 | 未登録仕入元が自動登録される | 未登録の display_name を含む .txt アップロード → `SELECT * FROM public.suppliers WHERE line_name = '対象名'` で1行取得 |
| 3 | 自動登録後 review_status='ok' | 上記アップロードの API レスポンスで `review_status === 'ok'` |
| 4 | TCG_AUTO_DISTRIBUTE=1 で解析後自動配信 | 環境変数設定下で extraction 完了 → Celery ログに run_distribution 呼び出し記録 |
| 5 | needs_review=TRUE アイテムは配信されない | 要確認アイテム含む解析結果 → 配信後のシートに該当行なし |
| 6 | 既存テスト全通過 | CI green |

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_line_import.py` — 自動登録フローの CI 回帰テスト
- 守り手: `backend/app/services/tcg_distribution_svc.py:run_distribution()` — 安全装置 #8/#8b/#8c で未完了ジョブ・needs_review をブロック
- TCG_AUTO_DISTRIBUTE 環境変数を 0 または未設定にすることで自動配信を無効化できる
- 既存の resolve/commit エンドポイントは維持するため、手動登録フローは引き続き使用可能
