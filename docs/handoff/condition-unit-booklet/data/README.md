# ADR-1035 便1 記録 SQL（本番未適用）

状態の単位をデータで設定する（6 行の `line_conditions.unit_id`）。コードは変えない。本番に流すのは Opus（担当は流さない）。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql` | PRECHECK_OK が 4 行（状態 24 行・6 行の unit_id が NULL・line_units の 11 が Pack で 9 が Case・6 行の名前が設計どおり）。ROW 行 24 と PRIORITY 行 2 も出る |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | UPDATED pack 5・UPDATED case 1・CHECK_OK changed 6・CHECK_OK conditions 24。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 5 行（K1）。ROW 行 24 を 01 の ROW 行と突き合わせ、ほかの 18 行が同じであることを確かめる |
| 5 | `05_target_jobs.sql` で対象 job を数え、再解析 | 設計 K2〜K4 を測る（再解析はこの SQL では行わない） |

戻し: `04_rollback.sql`（ROLLBACK unit_id 6）→ 対象 job を再解析。

- 直す行は 22・21・44・60・61 を Pack（line_units 11）、20 を Case（同 9）。PSA10（62）は空のまま。
- WHERE は id と `unit_id IS NULL` の両方。変わった行数が 6 でなければ `1 / 0` で失敗し、COMMIT に進まない。
- AI 用の読み取り専用の道（ADR-1024）では複数の文を送れない。事前確認と対象 job の数え上げは、`ai_ro.public__*` のビューに読み替えて 1 文にして流す。
