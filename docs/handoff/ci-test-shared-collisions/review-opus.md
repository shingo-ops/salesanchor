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
