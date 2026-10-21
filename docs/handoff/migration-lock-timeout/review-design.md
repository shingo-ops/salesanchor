# 設計審査 — migration-lock-timeout 便1

- 審査者: Claude Opus（Architect 役）。Planner と同じ AI による自己審査で、独立した第二者レビューではない。
- 対象: docs/handoff/migration-lock-timeout/design.md（2026-10-21 版）
- 判定: **APPROVE**

## 確かめたこと
1. 根拠: 原因（DROP が FK 先 products の AccessExclusiveLock を待ち、後続が並ぶ）は sandbox run 39570551782 の pg_locks とタイミングで観測済み。lock_timeout=1s の効き目と流し直しの成功も同じ run で観測済み（recon §4）。
2. 実物との整合: 置き換える範囲 `scripts/run_all_migrations.sh` :62-87 を origin/main 22f083083 で読んで確認。関数定義行 `run_sql() {` は TOTAL（:47 `^run_(sql|py)[[:space:]]`）にも `scripts/check-migration-registration-exists.sh` の `^run_sql[ \t]+` にも当たらない（今と同じ）。
3. 打ち切り: deploy.yml に timeout 指定は無く、ssh-action v1 既定 10m（action.yml:28-30）。最悪の追加 160秒＋通常最大138秒 ≒ 300秒 < 600秒。
4. 冪等: 流し直しの安全は CI の全件2周（migration-test.yml:1828-1839）に依る。既存の deadlock 再試行（c072445cf）と同じ前提で、新しい前提は足していない。
5. GO: 差分に migrations/ の追加・変更が無い（DROP を含む追加行なし）ので ADR-1003 の例外に当たらず、委任 GO で可。scripts/ を含むので ADR-136 の GO 記録は要る。
6. 受入条件: K1〜K5 は sandbox と CI で○×が出る。K6・K7 は本番の入れ替え3回が要り、セッション内で全部は終わらない可能性がある → 状態を「測定中」と分けて報告すること。
7. 試験の形: 本物の run_sql を sed で抜き出して使うので、試験用の写しが正本とずれない。

## 未解決（実装可否には影響しない）
- 8 ファイルの SET LOCAL 5s（便2・PO 判断）。run_py（便3）。遅い時間帯B の原因。
- K7 の2秒境界: Prometheus の bucket に 2 秒が無い場合の扱いを design §6 に書いた。測定時に境界の実物を記録する。
