# recon: migration 値書き込み検査の試験を CI で動かす（件2）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:11-13（#4481 件2）
> 基準: origin/main d56769477（2026-10-17 fetch 後）。worktree /Users/tanizawashingo/worktrees/salesanchor/release-migration-value-writes-test-ci
> 生出力: /tmp/CC報告ファイル/kenn2/（1_test_file.txt〜7_a.txt）

## 既存 ADR の検索
- 検索: `git grep -il "migration-guard\|protected-tables\|value-write" docs/adr/`（生出力 6_adr_lines.txt）
- docs/adr/ADR-155-product-master-ssot-csv-app.md:32 — migration-guard.yml にチェック7を追加し、共用マスタ表への INSERT/UPDATE/DELETE を CI で止める
- docs/adr/ADR-1007*.md:31（決定1 全マスタ表が対象）／:88（決定5 検査強化）
- docs/adr/ADR-1020-shared-product-required-fields.md — product_blank_confirmations を新設（便1）
- docs/adr/FEATURE-INDEX.md:19 — 関連行はこの1行のみ（ADR-1020／ADR-155／ADR-156）

## 事実
1. 試験 scripts/tests/test_migration_value_writes.py（288行・unittest 形式・DB 不要・環境変数不要）はどの workflow からも呼ばれていない。言及は .github/workflows/migration-guard.yml:403 のコメントだけ（5_grep.txt）。
2. ローカル実行 `python3 -m pytest scripts/tests/test_migration_value_writes.py -q` → 1 failed, 24 passed（3_pytest.txt）。失敗は scripts/tests/test_migration_value_writes.py:283 `self.assertEqual(len(names), 27)` の `28 != 27` だけ。
3. 28 は scripts/migration-guard/protected-tables.txt:11-38 の28行。28番目 :38 `product_blank_confirmations` は ae81ba18a（2026-10-16「ADR-1020便1」、#4396 で main へ）で一覧だけに追加され、試験の 27 は更新されなかった（2_log.txt）。
4. 一覧の見出し scripts/migration-guard/protected-tables.txt:2 は「唯一の正本」、.github/workflows/migration-guard.yml:400 は「表の数はここでなく、その一覧が決める」。試験 :283 は表の数をもう1か所に持っている（正本の重複）。
5. 検査本体 scripts/check-migration-value-writes.py は .github/workflows/migration-guard.yml:405-437 の3 step で動く。この job は main の Ruleset（id 15777895）の必須チェック「models.py に新 Column → deploy.yml にマイグレーション追記必須」（5_ruleset_main.json）。:433 「同じ job の step なので、必須チェックの名前は変わらない。paths: は付けない」。
6. 危険度: scripts/check-process-artifacts.js:117 `^scripts/` が危険パス → scripts/tests/・scripts/migration-guard/ の変更は GO 記録＋バックアップ確認欄が要る。.github/workflows/ は :135 実コード扱い（危険パスは deploy.yml :119・process-artifacts-gate.yml :122、PO 本人限定は workflow-lint.yml :49-51 のみ）。

## 未確認
- GitHub Actions の runner 上で試験の TempRepo（一時 git リポジトリ）が通るか → PR の CI ログで確かめる（design.md K2）。
