# design: migration 値書き込み検査の試験を CI で動かす（件2）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:11-13（#4481 件2）。recon: [recon.md](./recon.md)
> 状態: 設計案作成済み・設計審査済み（Opus 自己審査、APPROVE）。PO 2026-10-17 チャットで件2着手に「y」、マージ・デプロイまでの完走を委任。

## KGI（○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | この PR の CI で、必須チェック「models.py に新 Column → deploy.yml にマイグレーション追記必須」の job に新しい step「migration 値書き込み検査の試験」があり、ログに `Ran 25 tests` と `OK` が出る | `gh run view --log` の該当 step |
| K2 | ローカルで試験が 25 件すべて通る（失敗 0） | `python3 scripts/tests/test_migration_value_writes.py` の終了コード 0 |
| K3 | 試験が落ちたら job が赤になる（step に `continue-on-error` が無く、試験が失敗時に非0で終わる） | ローカルで一覧から4表の1つ（supplier_aliases）の行を消した状態で実行し終了コード≠0 → 戻す／yml に continue-on-error が無いこと（訂正 2026-10-17: 当初は「任意の1行」と書いたが、数を持たない設計なので4表以外の行を消しても落ちない。実測は /tmp/CC報告ファイル/kenn2/impl/k3.txt・k3b.txt） |
| K4 | 表の数の正本が一覧1か所だけになる（試験に数の直書きが無い） | `grep -n "assertEqual(len(names)" scripts/tests/test_migration_value_writes.py` が0件 |
| K5 | main マージ後、main への push で動く workflow がすべて成功（または変更と無関係な既存失敗だけ） | `gh run list --branch main --commit <merge sha>` |

## 変更（3ファイル＋文書）
1. scripts/tests/test_migration_value_writes.py:283 — `self.assertEqual(len(names), 27)` を、重複行が無いことの確認に置き換える。
   - 前: `self.assertEqual(len(names), 27)`
   - 後: 一覧の非コメント行を list で読み、`self.assertEqual(len(lines), len(set(lines)), "重複した表名がある")`（数は一覧が決める・recon 事実4）
   - :279-282 の4表を含む確認はそのまま。
2. scripts/migration-guard/protected-tables.txt:10 の後に経緯1行を追記: `ae81ba18a（2026-10-16、ADR-1020 便1）で product_blank_confirmations を足した（28 表）。` 表の行は触らない。
3. .github/workflows/migration-guard.yml:437 の後（チェック7b の直後、チェック9 の前）に step を1つ追加:
   ```yaml
      # 検査本体の試験（scripts/tests/test_migration_value_writes.py）。DB 不要。
      # 同じ job の step なので、必須チェックの名前は変わらない。paths: は付けない。
      - name: migration 値書き込み検査の試験
        run: |
          python3 scripts/tests/test_migration_value_writes.py -v
   ```
4. 文書: 本 design.md・recon.md、docs/handoff/found-untouched-20261017/handoff.md の件2に「便: docs/handoff/migration-value-writes-test-ci/design.md」を追記、active-work.d の台帳。

## 触らない範囲
- 検査本体 scripts/check-migration-value-writes.py、許可一覧 value-write-allowlist.tsv、dryrun-exclusions.tsv（件3）、migrations/（件4）、deploy.yml（件1）、workflow-lint.yml、Ruleset（必須チェックの名前は変えない）。

## 代替案
- A 数を28に直すだけ: 次に表を足すと同じ失敗が起きる（今回の原因そのもの）→ 不採用。
- B 新しい workflow/job を作る: 必須チェックへの登録（Ruleset 変更＝PO 確認の不可逆操作）が要る → 不採用。既存必須 job への step 追加なら登録不要（migration-guard.yml:433 の前例）。

## リスクと対処
- runner で TempRepo の git が失敗する（git user 未設定など）→ PR の CI で K1 を確かめ、赤なら原因を直してから進む。
- 試験の追加で全 PR の migration-guard が数秒長くなる → ローカル実測 25件で数秒（3_pytest.txt）。許容。

## 危険パス・GO
- scripts/ を触るため危険変更（scripts/check-process-artifacts.js:117）。DB・本番データ・migrations/ は触らないため、バックアップは不要（本番へ書くものが無い）。
- GO は POの委任に基づくClaude Opus発行（PO 2026-10-17 チャット原文:「PRマージ、デプロイまで完走させてくれ」）。PR 本文に GO 記録を残す。

## 外部・過去事例の参照と我々への応用
- 不要。理由: 既存 job へ試験 step を足す作業で、同リポジトリ内の前例（migration-guard.yml:433 チェック7b、deploy-script-test.yml:38-41）が直接の根拠になるため。

## 維持の仕組み
- 守り手: migration-guard の必須チェック。一覧に表を足しても試験は落ちない（数を持たない）。試験が壊れれば全 PR の必須チェックが赤になる。
