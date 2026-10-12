# recon：抽出エラー一覧の「未対応・対応中・対応完了」

- 作成：2026-09-30（Opus 設計担当）。事実の元は、サブエージェントの読み取り調査と、Opus による再確認（本番 DB の読み取り・origin/main）
- 基準：origin/main（2026-09-30 10:42 に fetch）

## 1. PO の要望（2026-09-30）
- 再実行したエラーが一覧に残ると、二重に再実行する恐れがある
- エラーの記録は残したい。消さずに、未対応・対応中・対応完了の状態で見分けたい
- 設計担当の案（新しい表や列は作らない。今の記録から3区分を出す。元の日時には戻さない。最新の失敗と再実行回数を出す）に、PO が「合意、進めて良い」と返答

## 2. 今の実装（origin/main）

| 事実 | 根拠 |
|---|---|
| エラー一覧の API は `GET /tcg/extraction-errors`（super_admin だけが使える）。`ej.status = 'error'` の行だけを返す。並びは `created_at DESC`。`offset`/`limit` で区切る | `backend/app/routers/tcg_analysis_dashboard.py:514-546` |
| 種別と詳細は、その**最新の attempt**（成功も含む）の `validation_result` から取る | `backend/app/routers/tcg_analysis_dashboard.py:535-540`、`:555-556` |
| 応答は配列だけで、合計件数を返さない | `backend/app/routers/tcg_analysis_dashboard.py:504-511`、`:516` |
| この API を呼ぶのは ExtractionErrorLogPanel だけ | `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx:88`（`git grep "extraction-errors"`。`/tcg/diagnostics/extraction-errors` は別の API で、`backend/app/services/tcg_diagnostics_svc.py:34` にある） |
| 再実行を受け付ける状態は `{"pending","error"}`。job_ids で指定すると、すでに pending のジョブも Celery にもう一度投入される | `backend/app/services/tcg_diagnostics_svc.py:140`、`:188`、`:233-238` |
| 再実行すると、error を pending に更新し、extraction_items を削除する（analysis_results は CASCADE で消える） | `backend/app/services/tcg_diagnostics_svc.py:210-230` |
| ジョブの状態は6つ：pending・running・done・empty・filtered・error | `backend/app/services/tcg_extraction_record_svc.py:78`（running）、`:235`（error）、`backend/app/tasks/tcg_extraction.py:315`（empty）、`:336`（filtered）、`:410`・`:479-488`（done/empty/error） |
| attempts の phase は4つ（started・received・completed・failed）。CHECK 制約で決まっている | `migrations/20260921_110000_pipeline_tables_public.sql:135-136` |
| attempts には `(extraction_job_id, started_at DESC, id DESC)` の索引がある | 本番 `pg_indexes`（ix_pub_extraction_attempts_job_started） |
| 画面は金型だけを使う（Card・DataTable・Button・Badge・Modal・ContentToolbar）。取得した件数が PAGE_SIZE と同じなら、続きがあるとみなす | `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx:9`、`:96` |
| 絞り込み用の金型 Tabs がある。件数の表示（count）と、variant の pill・underline に対応している | `frontend/src/components/Tabs.tsx:25-44` |
| Badge の variant は neutral・info・success・warning・danger | `frontend/src/components/Badge.tsx:16` |
| i18n の場所は `analysisRules.errorLog.*` | `frontend/src/locales/ja.json:4279-4306`、en.json も同じ位置 |
| `/tcg/extraction-errors` を直接確かめるテストはない。retry のテストは中身をモックしている | `backend/tests/test_tcg_diagnostics.py:267-322`、`backend/tests/test_tcg_work_matching_integration.py:829` |

## 3. 本番の数（2026-09-30、読み取りのみ）

| 数字 | 値 |
|---|---|
| ジョブの状態ごとの件数と、そのうち failed の attempt を持つもの | done 1408（128）、empty 161（6）、error 54（54）、filtered 16（3） |
| error のジョブのうち、failed の attempt がないもの | 0 件。error の 54 件すべてに failed の attempt がある |
| attempts の総数 | 1,833 |
| 9/29 に作られたジョブ | 76。その内訳は done 20（うち再実行して成功したもの 18）、empty 1（再実行して成功）、error 54、attempt のないもの 1 |
| PO が 9/30 に再実行した分 | 19 件。9/30 00:43〜00:45 UTC に実行し、18 件が done、1 件が empty になった。同じジョブを2回再実行したものは 0 件。試運転は 16 件動いた |

## 4. 既存の ADR
- 検索した語：extraction_attempts、エラーログ、retry-extraction、再実行（`docs/adr/`）
- ADR-154：「新しい診断表を追加せず、既存の extraction_attempts を…」（`docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:140`）。今回の方針（表を増やさない）と一致する
- ADR-144（UI の部品は金型を使う）、ADR-027（i18n）、ADR-067（デザイントークン）：画面の変更は、この3つに従う
- この設計と食い違う ADR は、見つからなかった
