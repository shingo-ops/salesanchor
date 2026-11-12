<!-- backticked paths are full repo paths; new files outside this PR are not backticked -->
# 実装カード — 解析（システム段）の計算の間、DB の取引を開いたままにしない

**設計の正本**: `docs/handoff/analysis-tx-release/design.md` §5（変更前→変更後）・§6（弊害）・§2 KPI。このカードは手順と点検だけを足す。設計と食い違ったら設計が正。  
**設計審査**: クラウド architect 3 回目 APPROVE（`docs/handoff/analysis-tx-release/review-architect.md`）。  
**PO 承認**: 2026-11-12「1」（クラウドで設計を審査し、直す所を直してからクラウドに実装を頼む）。区分 A（ADR-1015）。GO 不要（migrations・deploy・本番 scripts を含まない）。  
**基準の main**: a86879767。設計の行番号は a3e93f053。間の差分は `backend/app/services/line_analysis_v102_svc.py` の別の直し（シングルセット系。+8 行）だけで、run_v102_analysis の中身は同じ。**今の main での位置**: `run_v102_analysis` は :1534（設計の :1526）、鍵 :1545（設計 :1537）、計算 :1576（設計 :1568）、付け直し :1586（設計 :1578）。設計の :1526 以降の行番号には +8 を足して読む。:596（Gemini 段の commit）より前の行は +2。  
**実装担当**: クラウドの Sonnet。**ブランチ**: release/analysis-tx-release-impl（origin/main から新しく作る）。

- 受領確認: 着手前に、報告の1行目へ「受領確認: analysis-tx-release card を読んだ」と書く。
- 読んだ節（Planner の照合）:
  - docs/handoff/design-partner-card-ops/guards/00-common.md: プレースホルダを残さない（パス・行番号は実名）・出力に上限（長い出力は tail で切る）・報告に無い出力を成功と扱わない（手順 8 で git log と ls-remote を確かめる）。○
  - docs/handoff/design-partner-card-ops/guards/03-file.md・docs/handoff/design-partner-card-ops/guards/05-pr.md: 触るファイルを §1 で全部挙げた。PR は Opus が手元で作る（Sonnet は push まで）。○

## 1. 触るファイル（これ以外は触らない）
- `backend/app/services/line_analysis_v102_svc.py` — 設計 §5-1。変えるのは `run_v102_analysis` と、新しい関数 `_read_v102_head`・`_read_v102_tail`・`_prepare_v102` と frozen dataclass `_V102Inputs`（同じファイル。`run_v102_analysis` のすぐ上に置く）だけ
- backend/tests/test_v102_analysis_tx_release.py（新規）— 設計 §5-2（K2・K3・K3b）

触らない: `_write_results`・`run_v102_pipeline`・`load_v102_masters`・`_merge_supplier_products` の中身、鍵の名前（`v102_analysis_lock_key`）、`backend/app/services/v102_human_decisions_svc.py`、`backend/app/services/v102_transcription_svc.py`、呼び出し元（`backend/app/tasks/tcg_extraction.py`・`backend/app/services/tcg_product_master_svc.py`・`backend/app/services/tcg_analyzer_svc.py`・`backend/app/tools/reextract_v6_with_v102.py`）、既存の試験ファイル、`migrations/`、`.github/`、`frontend/`、docs。

## 2. 手順
1. クラウドの事前確認（`scripts/dev/executor-preflight.sh` の4項目のうち、クラウドで確かめられる2つ）: `git config user.name shingo-cc` と `git rev-parse --verify origin/main`。どちらかが失敗したら BLOCKED:。残りの2つ（api.github.com への到達・gh の名義）はクラウドに gh が無いため流さない（2026-11-12 の1回目で preflight が [1/3] と [2/3] で FAIL して止まったことを受けた変更。前例 `docs/handoff/conversation-unification/card-bin1.md` §1 の 1）。そのあと origin/main から release/analysis-tx-release-impl を作る。
2. 呼び出し元の点検をやり直す（設計 §6 の 1 行目）。`backend/app/tasks/tcg_extraction.py` の run_v102_analysis を呼ぶ 2 か所と analyze_extraction_job を呼ぶ所、`backend/app/services/tcg_product_master_svc.py` の analyze_extraction_job を呼ぶ所、`backend/app/tools/reextract_v6_with_v102.py` の呼ぶ所の、それぞれ直前 30 行を生で出す。直前に commit が無く、書き込み（INSERT・UPDATE・DELETE）がある所があれば止まる。
3. 設計 §5-2 の試験 3 本を新しいファイルに書く（組み立ては `backend/tests/test_line_analysis_v102_pg.py` の fixture `v102`・`make_job`・`run_analysis` を import して使う）。K3 の保存は設計 §5-2 の書き方（`create_async_engine` ＋ `AsyncSession` ＋ `asyncio.run`、保存の前に `SET LOCAL lock_timeout = '2s'`、1 回目の計算の中だけ保存）。
   - この試験の実 DB の組み立て（`backend/tests/test_tcg_work_matching_integration.py` の fixture `pg`）は GitHub の自動確認の中でしか動かない（`GITHUB_ACTIONS` が true でないと止まる作り）。クラウドでは流さない。`GITHUB_ACTIONS` を自分で設定して動かそうとしない。
   - 試験ファイルだけを commit する（コードはまだ変えない）。そのあと `git branch release/analysis-tx-release-redcheck` で同じ位置に赤の確かめ用の枝を作り、`git push origin release/analysis-tx-release-redcheck` する。この枝は直す前の main に試験だけを足したもので、Opus が下書きの PR にして GitHub の自動確認で K2・K3 が赤、K3b が緑になることを確かめる（2026-11-12 の2回目で、クラウドに実 DB が無いと分かったことを受けた変更）。
4. 設計 §5-1 の 1〜10 のとおりに `run_v102_analysis` を書き換える。守ること:
   - try の外で読む物（鍵・ctx・job・rows・早い return・マスタと unit_ids）と try の中で読む物（decisions 以降）の境目を今と同じにする。
   - 計算の前の `session.commit()` に、設計 §5-1 の 5 のコメントを付ける。
   - 1 回目の ValueError（ctx が無い）だけを呼び出し元へ送出する。2 回目の読みの ValueError は except で受ける。
   - やり直しの計算は 1 回だけ。ループにしない。
   - except の中身（rollback → `_set_job_review_reasons` → `_clear_job_review_detail` → commit → empty_stats）と、最後の記録の文は 1 文字も変えない。
5. クラウドで流せる試験だけ流す: `backend/tests/test_line_analysis_v102_svc.py`・`backend/tests/test_analysis_failed_record.py`・`backend/tests/test_adr1032_revival_guard.py`。実 DB の試験（新しい試験ファイル・`backend/tests/test_line_analysis_v102_pg.py`・`backend/tests/test_reextract_v6_with_v102_pg.py`・`backend/tests/test_v102_human_decisions.py` のうち fixture `pg` を使う物）は GitHub の自動確認に任せ、報告に「流していない」と書く。
6. `ruff check` と `ruff format --check` を触ったファイルに流す。
7. コードの変更を commit して release/analysis-tx-release-impl を push する。そのあと `git log -1 --oneline` と `git ls-remote origin refs/heads/release/analysis-tx-release-impl` で同じ sha が出ること、`git ls-remote origin refs/heads/release/analysis-tx-release-redcheck` が試験だけの commit の sha であることを確かめて停止する。PR は作らない（Opus が作る）。
8. Bash に psql の語を書かない（クラウドの見張りが中身を問わず止める。2026-11-12 の2回目で実測）。

## 3. 想定される分岐と停止する条件（迷ったらここを見る。ここに無い分岐は停止して、その時点で §4 の形で報告して終わる）
| 起きたこと | すること |
|---|---|
| 今の main の行番号が上の「今の main での位置」とずれる | 中身で同じ場所を探す。中身も違えば止まる |
| 手順 2 で、呼ぶ前に commit されていない書き込みが見つかる | その場所の生出力を出して止まる（呼び出し元は触らない） |
| 既存の試験が件を SimpleNamespace で渡していて `==` 比べで落ちる | 落ちた試験名と生出力を出して止まる（試験は直さない） |
| `backend/tests/test_line_analysis_v102_svc.py` の偽のセッションの試験で、commit の回数や begin_nested の回数の確かめが落ちる | 生出力を出して止まる |
| 実 DB の試験を流したくなる | 流さない。手順 3 のとおり GitHub の自動確認に任せる。流していない試験を「通った」と書かない |
| 手順 5 の試験が落ちる | 落ちた試験名と生出力を出して止まる（試験は直さない） |
| `save_value_override` の引数が設計 §5-2 と違う | 止まる。引数を推測して合わせない |
| 計算の差し替えの中から DB を読む物が見つかる（K2 が直した後も赤） | 止まる |
| 見張り（フック）に止められる | 言い換えずに BLOCKED: で止まる |

## 4. 報告の形
生出力をそのまま。①preflight の結果 ②手順 2 の点検の出力 ③`git diff --stat origin/main...HEAD` ④赤の確かめ用の枝の sha と push の結果 ⑤手順 5 の試験の出力 ⑥ruff の出力 ⑦HEAD の sha と push の結果。最後の行は DONE、BLOCKED: と理由、NEEDS_DECISION: と問い、のどれか。

## 5. 受け入れ（Opus が確かめる）
| 基準 | 検証方法 |
|---|---|
| §1 のファイルだけが変わる | `git diff --name-only origin/main...HEAD` |
| K2・K3: 旧 main で赤、直した後で緑 | 赤の確かめ用の枝の下書き PR の CI（赤）と、本 PR の CI（緑）。下書き PR はマージせず閉じる |
| K3b: 直した後も計算 1 回・「inputs changed」無し | 本 PR の CI |
| K4: 既存の 6 本が緑 | CI の pytest (SQLite + PostgreSQL RLS) |
| except の中身と記録の文が不変 | diff を Opus が読む |
| 審査役（reviewer・opus）APPROVE | マージ前に Opus が手元で起動する |

END OF CARD
