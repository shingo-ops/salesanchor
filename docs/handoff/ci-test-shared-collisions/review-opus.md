# review-opus: CI の試験どうしのぶつかり 便1

状態: Opus 自己審査（同じ AI による審査。独立した第二者の審査ではない）。マージ前の審査役（reviewer・opus）の判定は PR のコメントに残す。

## 設計の審査（2026-11-27）
- 原因（recon §2 の起きる順番）と直し方（共通の役割を消す行を外す）が1対1に対応している。
- 既存 ADR との食い違いは無い（recon §5）。
- 受け入れ基準 K1〜K4 は、どれも差分か記録で ○× を決められる。
- 判定: 便1は APPROVE。便2〜5は REVISE（recon §3・§4 の未確認が残る）。

## 実装の確かめ（commit ce9407a6e・Opus が手元で実行）
- 中身の違い: 6ファイルの変更前後を `ast.unparse` で比べた（コメントと整形の差は消える）。違いは次だけだった。
  - `_Cluster.__init__` の役割の有無の記録を外し、`cleanup()` を `pass` にした（test_ai_cloud_views・test_ai_job_assignments_db・test_ops_case_db）。
  - 役割の有無の記録と、後片付けの `DROP ROLE` の for 文を外した（test_ops_case_report_kind_migration・test_ops_case_router・test_ai_ro_views）。
  - `DROP DATABASE ... WITH (FORCE)` と `control.close()` は残っている。
- 行数が増えたのは、クラウドの担当が `ruff format` を6ファイルにかけたためである。上の比べ方で、整形の差に動きの違いは無かった。
- K2: `git grep -n "DROP ROLE" -- backend/tests` は `backend/tests/test_tenant_isolation_daily_check.py:217,254` の2行だけ（合格）。
- K1・K3・K4 は PR の CI と合流後の main で確かめる。

## K3 の確かめ（HEAD fc0ff20ac・2026-11-27）
- 結果: 不合格。PR の pytest は pass したが、skipped が main より1つ多い。
  - main の直近6回（run 45850364363・45747857274・45736754252・45639855180・45627383586・45584731851）は、どれも skipped 79。
  - PR の2回（run 45857839276・45858440452）は、どちらも skipped 80。
- 原因: `backend/tests/ops/test_ai_cloud_views.py:229-231` は `ai_reader` があると skip する。`ai_reader` を作るのは便1の6ファイルだけ（`git grep` の結果）。消さなくなったので、先に作られた役割が残って skip になる。
- 試験は -q で動くので、記録に試験ごとの結果は出ない。ほかの5ファイルの `pg_roles` の行は、無ければ作るものだけで、skip しない（`grep -n pg_roles` の結果）。
- 対処: `docs/handoff/ci-test-shared-collisions/design.md` §3-1 の「追加」の項。直したあとの PR で skipped が 79 に戻ることを K3 とする。

## 便2〜5の設計の審査（2026-11-27）
- 結果は design.md §12。便2〜5は APPROVE。
- B と C は PR 5669 で直っていた。クラウドの調べ（04b5cc9ba）は直した後のコードを読んでいたため、B の仕組みを説明できなかった。失敗の時刻と合流の時刻を並べて決着した（recon §6-1）。
