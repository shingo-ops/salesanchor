<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — migration-churn-guard（ADR-1005 Stage 0 ①②）

**対象ADR**: ADR-1005（docs/adr/ADR-1005-migration-run-once-ledger.md）Stage 0 ①②。設計は docs/handoff/migration-runner-redesign/design.md §2「段階0：安全網」に既定済み。
**recon**: docs/handoff/migration-churn-guard/recon.md
**日付**: 2026-10-06
**担当**: Sonnet（実装）

---

## 外部・過去事例の参照と我々への応用

- 事例1（社内の設計ドキュメント）: docs/handoff/migration-runner-redesign/design.md §2 事例3「PostgreSQL 16 公式（limits.html：削除した列も 1600 列の上限に数える）→ 後で消す列を前の手順で足す形を CI で禁止する」。本カードはこの設計をそのまま実装した（追加設計判断なし）。
- 事例2（2026-10-03 インシデント、社内）: `public.products.tcg_uuid` の ADD→DROP 繰り返しが 1600 列上限エラーを起こし、修正に PR 5本（#3958〜#3963）を要した。本カードの検出ロジックはこのパターン（登録順でADD→後でDROP）を再発前に機械検出することを目的とする。
- 該当なし：③（全件ドライラン対象範囲）は調査のみでワークフロー変更を行わないため、外部事例の応用は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ①：ADD→DROP の churn を含む PR 見本で CI チェックが失敗する | `node scripts/tests/test-migration-column-churn.js` ケース(a) |
| ①：allowlist 登録済みの組は成功する | `node scripts/tests/test-migration-column-churn.js` ケース(b) |
| ①：stale な allowlist エントリは失敗する | `node scripts/tests/test-migration-column-churn.js` ケース(c) |
| ①：ADD CONSTRAINT / DROP CONSTRAINT 等はカラムとして誤検出しない | `node scripts/tests/test-migration-column-churn.js` ケース(d) |
| ①：1つのALTER内の複数カンマ区切り句を個別検出する | `node scripts/tests/test-migration-column-churn.js` ケース(e) |
| ①：EXECUTE format + %I の動的SQLを検出し tenant.* に正規化する | `node scripts/tests/test-migration-column-churn.js` ケース(f) |
| ①：run_py が読む .sql ファイルも検出対象にする | `node scripts/tests/test-migration-column-churn.js` ケース(g) |
| ①：drop-then-add は警告のみで exit 0 を維持する | `node scripts/tests/test-migration-column-churn.js` ケース(h) |
| ①：現在の main（origin/main 相当）で未許可の churn が 0 件 | `node scripts/check-migration-column-churn.js` を実行し `MIGRATION COLUMN CHURN CHECK PASSED` を確認（本PRで実行済み・recon.md「検出結果」） |
| ②：二重登録が 0 件になる | `grep -cE '^run_(sql\|py)[[:space:]]' scripts/run_all_migrations.sh` の件数と `sort -u` 後の件数が一致。かつ `bash scripts/check-migration-duplicate-registration.sh` が成功 |
| ②：二重登録チェックの回帰テストが通る | `node scripts/tests/test-migration-duplicate-registration.js`（3ケース） |
| ワークフロー組み込み：actionlint でエラーが増えない | `actionlint .github/workflows/migration-guard.yml` の出力が本PR適用前（origin/main）と同一（shellcheck info 6件のみ、新規ステップに起因する指摘0件） |
| ワークフロー組み込み：関連パス以外のPRではスキップされる | `.github/workflows/migration-guard.yml` のチェック10 `if: steps.detect_churn_paths.outputs.relevant == 'true'` の条件分岐をレビューで確認（PR差分に migrations/**, scripts/run_all_migrations.sh, scripts/migrate_*.py, 本チェック自身、allowlist のいずれも含まれない場合は実行されない） |
| 既存チェックの回帰なし | `node scripts/tests/test-migration-registration-exists.js` が3ケース全PASS、`bash scripts/check-migration-registration-exists.sh --mode host --repo-root <repo>` が成功（316件、②の削除後の件数） |

---

## 技術 How・KPI

- KPI1（①）: allowlist 外の ADD→DROP churn 件数 → 本PR適用時点で0件（2件は調査の上でガード済みと確認し allowlist 登録。recon.md「allowlist 登録内容」参照）。
- KPI2（②）: `scripts/run_all_migrations.sh` の登録行の重複件数 → 1件（20260831_110000_create_tcg_analysis_tables_t004.sql の536行目）→ 0件。
- 技術選択: チェックスクリプトは Node.js（`scripts/check-migration-column-churn.js`）。理由: ①の要件（SQLコメント除去、EXECUTE format内の文字列解析、comma区切りのトップレベル分割、run_pyからの.sql参照抽出）は正規表現＋小さな状態機械の組み合わせで実装する必要があり、既存の同種チェック（`scripts/check-dangling-routes.js`, `scripts/check-ui-governance.js` 等）がすべてNode.jsで同様の文字列解析を行っている（recon.md 引用）。②は既存の `scripts/check-migration-registration-exists.sh`（bash）と同じ入出力パターン（`^run_(sql|py)[[:space:]]` の行走査）のため bash で実装し一貫性を保った。
- allowlist 形式: JSON配列（table/column/reason/reference必須）。CIで「reasonとreferenceが無いエントリ」はパース時に例外で止める（`loadAllowlist` 関数）。

---

## 弊害・トレードオフ

- 誤検出（false positive）のリスク → 対策: ADD CONSTRAINT/DROP CONSTRAINT/DROP DEFAULT/DROP NOT NULLを明示的に除外し、テストケース(d)で固定化。EXECUTE format内の解析は既存の実在パターン（%I、$q$ dollar-quote）を実データから抽出して正規表現を作成（recon.md citation参照）。
- 誤検出（false negative）のリスク：列名を動的に組み立てるSQL（`format('...%s...', column_name_var)`のような文字列結合）は検出できない → 対策: Architect審査で「列名を変数で組み立てている例は0件」と確認済み（docs/handoff/migration-runner-redesign/design.md §2 引用）。将来そのような書き方が増えたら本チェックは無力化するため、人手のレビュー（code-review）が最後の守り手として必要。
- allowlistの陳腐化（本当は危険な組が「ガード済み」と誤って登録される）リスク → 対策: 本PRではガードの存在をコード読解で1件ずつ確認し、reasonフィールドに具体的なガード条件を引用した（recon.md参照）。stale allowlistは自動検出（テストケース(c)）するが、「ガードが実は不十分」は機械検出できないため、allowlist追加時のPRレビューで人手確認が必要。
- run_py経由の.sql検出の網羅性 → 対策: 文字列リテラル「.sql」の正規表現抽出のみで、f-string結合などでファイル名を動的生成するコードは追えない。現状の26本のrun_pyスクリプトは全て静的な文字列リテラルでファイル名を書いており（recon.md引用: `scripts/migrate_inventory_sprint1.py:52`, `scripts/migrate_meta.py:60`）、現時点では影響なし。
- ③（調査のみ）: 全件ドライラン対象外の162件への対応は本PRの範囲外。範囲を広げないまま新しいmigrationが増え続けると、ドライランでカバーされる比率がさらに下がる → 対策: 別カードで「どれが拡張可能か」の判断を行う前提をrecon.mdの不明点リストに明記した。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/check-migration-column-churn.js` 実装・回帰テスト8ケース作成・実行 | Sonnet |
| 2 | origin/main 上の churn/警告を検出し、1件ずつガードの有無をコード読解で確認。ガード済みの2件を allowlist 登録 | Sonnet |
| 3 | 二重登録（536行目）削除・`scripts/check-migration-duplicate-registration.sh` 実装・回帰テスト3ケース作成・実行 | Sonnet |
| 4 | `.github/workflows/migration-guard.yml` にチェック10を追加・actionlint/YAMLロード確認 | Sonnet |
| 5 | ③の調査（`git log -L` で履歴確認、事実のみ記録） | Sonnet |
| 6 | recon.md / design.md 作成、PR起票 | Sonnet |

---

## 継続

- 完了後の監視: 新しいmigrationのPRが本チェックで赤になった場合、allowlistに追加する前に「ガードが実際に機能するか」を人手でコード読解すること（弊害・トレードオフ参照）。
- 次フェーズへの引き継ぎ: ADR-1005 Stage 1（テナント正本の一本化）・Stage 2（実行済み記録）は本カードの範囲外（docs/handoff/migration-runner-redesign/design.md §3・§4）。③（全件ドライラン対象範囲の拡張判断）は別カードでrecon.md不明点リストの件を解消すること。

## 維持の仕組み

- 守り手: `.github/workflows/migration-guard.yml`（チェック10として組み込み済み。登録チェックと同じ場所で継続）
- 守り手: `scripts/migration-column-churn-allowlist.json`（stale検出により、現在の実態と一致しない記載は自動でCI赤になる）
- 守り手: 人手で守る（allowlist追加時の「ガードが実際に機能するか」の確認。弊害・トレードオフ参照）
