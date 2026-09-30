# design：抽出エラー一覧を「未対応・対応中・対応完了」で見分ける

- 作成：2026-09-30（Opus 設計担当）
- 状態：方針は PO が合意済み（2026-09-30「合意、進めて良い」）。設計審査は §9（同じ AI による自己審査）
- 根拠：[docs/handoff/extraction-error-handling-status/recon.md](./recon.md)
- 関連 ADR：ADR-154（新しい診断表を作らず extraction_attempts を使う）、ADR-144（UI は金型部品のみ）、ADR-027（UI 文字列は i18n）、ADR-067（デザイントークン）、ADR-1003（GO の委任）

## 1. 目的（KGI）
- エラーの記録は消さない
- 一目で「まだ手を付けていないもの」が分かり、二重の再実行が起きないようにする

| KGI | 判定（○×） |
|---|---|
| 再実行したエラーが「未対応」から消える | 再実行を押した直後に一覧を読み直すと、そのジョブは「未対応」に無く、「対応中」か「対応完了」にある |
| 記録が消えない | 「対応完了」タブに、9/29 の再実行成功分（19 件）が、最初に失敗した日時つきで出る |
| 二重の再実行が起きない | pending または running のジョブ ID で retry-extraction を呼ぶと、enqueued=0、skipped=件数 が返る |
| 件数が合う | 3つのタブの件数の合計が、failed の attempt を持つジョブの数と一致する（本番の 2026-09-30 時点で 54＋0＋137＝191） |

## 2. 対象と対象外
- 対象：
  - `backend/app/routers/tcg_analysis_dashboard.py` の `list_extraction_errors`
  - `backend/app/services/tcg_diagnostics_svc.py` の `_ELIGIBLE_STATUSES`（job_ids で指定する場合）
  - `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx`
  - `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  - テスト
- 対象外：
  - DB の変更（表・列・migration は作らない）
  - `/tcg/diagnostics/extraction-errors`（別の API）
  - `scope="pending"` による再実行（DiagnosticsDrawer から使う。二重投入のおそれは別の便で扱う）

## 3. 区分の決め方（データの置き場所は1つのまま）
- 一覧に載るもの：**failed の attempt を1件以上持つジョブ**（`extraction_attempts.phase='failed'`）。記録はここにあり、消さない
- 対応状況は、**ジョブの今の状態**（`extraction_jobs.status`）から、その場で決める。保存はしない

| 対応状況 | extraction_jobs.status | Badge の variant |
|---|---|---|
| 未対応（unhandled） | error | danger |
| 対応中（in_progress） | pending、running | warning |
| 対応完了（resolved） | done、empty、filtered | success |

- 上の表にない状態が来たときは、未対応に入れる（見落とすよりは安全なため）。ログに warning を出す

## 4. API の変更（`GET /tcg/extraction-errors`）
- 問い合わせ：`status=unhandled|in_progress|resolved`（既定は unhandled）、`offset`、`limit`（今のまま）
- 応答（今の配列を、次の形に変える）：
```json
{
  "items": [ {
    "id": "...", "supplier_name": "...", "prompt_version": "...",
    "error_message": "...",            // 最新の failed の attempt の error_code（無ければ job の error_message）
    "error_category": "...", "error_detail": "...",   // 最新の failed の attempt の validation_result から
    "last_failed_at": "...",           // 最新の failed の attempt の started_at
    "first_failed_at": "...",          // 最初の failed の attempt の started_at
    "retry_count": 0,                  // そのジョブの attempt の数から 1 を引いた数
    "job_status": "error",
    "handling_status": "unhandled"
  } ],
  "total": 54,
  "counts": { "unhandled": 54, "in_progress": 0, "resolved": 137 }
}
```
- 並びは `last_failed_at DESC`
- SQL の要点：
  - failed の attempt を job ごとに集計する（最小・最大の started_at、件数）。最新の failed の validation_result は LATERAL で取る
  - 使う索引：`ix_pub_extraction_attempts_job_started`
  - `counts` は、同じ条件で status ごとに COUNT する
- 種別を「最新の attempt」ではなく「最新の **failed** の attempt」から取るように直す。いまは、再実行で成功したジョブだと、成功した attempt の空の結果が出てしまうため
- 呼び出し元は ExtractionErrorLogPanel だけなので、応答の形を変えても、ほかに影響は出ない（recon §2）

## 5. 再実行の受付
- `backend/app/services/tcg_diagnostics_svc.py`：job_ids で指定したときに受け付ける状態を、`{"error"}` だけにする。`scope="pending"` のほうは今のまま
- pending または running のジョブは skipped に数える。Celery には投入しない

## 6. 画面（ExtractionErrorLogPanel）
- カードの上に、金型の `Tabs`（variant="pill"、count つき）を置く
  - 並びは 未対応・対応中・対応完了。最初に選ばれているのは 未対応
- 列：
  - 対応状況（Badge）
  - 仕入元
  - エラー種別（Badge。今のまま）
  - エラー内容
  - エラー詳細
  - 再実行回数
  - 最初の失敗
  - 最新の失敗
  - プロンプトバージョン
- 行を選べる（selectable）のと、「選択したジョブを再実行」ボタンは、**未対応タブのときだけ**にする
- 再実行が成功したら、選択を外して、今のタブと件数を読み直す
- 「さらに読み込む」は、`items.length` と `total` を比べて出すかどうかを決める
- 使う部品は金型だけ（Tabs・DataTable・Badge・Button・Modal・Card・ContentToolbar）。色や大きさを直接書かない。新しい金型は作らない
- i18n：`analysisRules.errorLog.*` に次のキーを、ja と en の両方に足す
  - tab.unhandled、tab.inProgress、tab.resolved
  - handlingStatus（列名）、status.unhandled、status.inProgress、status.resolved
  - retryCount、firstFailedAt、lastFailedAt
  - 既存の createdAt は使わなくなる。消さずに残す

## 7. 基準と検証方法
| # | 基準 | 検証方法 |
|---|---|---|
| T1 | 区分の割り当てが §3 のとおり | backend のテスト：6つの状態それぞれで handling_status を確かめる（表にない状態は unhandled になる） |
| T2 | failed の attempt が無いジョブは、一覧に出ない | backend のテスト |
| T3 | 種別は、最新の failed の attempt から取る | backend のテスト：failed のあとに completed がある場合でも、failed 側の category が出る |
| T4 | counts と total が正しい | backend のテスト |
| T5 | pending と running は再実行を受け付けない | `tcg_diagnostics_svc` の実物を使ったテスト：enqueued=0、skipped=件数。Celery はモックする |
| T6 | 画面：タブの切り替え、未対応タブのときだけ選べる、読み直し | frontend のテスト（vitest）。i18n のキーが ja と en でそろっている（既存の CI） |
| T7 | UI の決まりを守っている | 既存の CI（UI governance gate、ADR-067 のチェック） |
| V1 | 本番で件数が合う | 反映したあと、画面のタブの件数が、本番 DB の読み取りの結果と一致する（§1） |

## 8. リスクと戻し方
- 応答の形が変わる → 呼び出し元は1か所だけ。フロントとバックを同じ PR で変える
- 対応完了の件数が多くなる → offset と limit で区切る。索引があるので問題ない
- 戻し方：PR を revert する（DB の変更はない）

## 9. 設計審査（Architect、同じ AI による自己審査）
- 判定：APPROVE
- 根拠：
  - 事実は recon にある
  - DB を変えない（ADR-154 の方針と一致する）
  - 受入条件は ○× で判定できる
  - 触るファイルは §2 のとおり
- 残っている未確認：なし。error_category の値の一覧は、バックエンドで決まった場所がない（recon）。ただし表示は今の i18n のキーをそのまま使うので、今回の範囲には影響しない

## 10. 維持の仕組み
- 守り手: Opus 設計担当（エラー一覧を変えるときに §3 を見直す）／PO（区分の意味を変えたいときに判断する）
- 新しいジョブの状態を増やすときは、§3 の表に加える。表にない状態は、未対応に入るので見落とさない

## 11. 外部・過去事例
- 該当なし。社内の既存の記録（extraction_attempts）と、ADR-154 の方針を根拠にした
