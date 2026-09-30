# recon: PR 作成時の手元の関所で、CI と同じ process-artifacts 検査を実行できるか（2026-09-30、読み取りのみ）

- 基準: origin/main 6144412fdcbdab602ba2c4bd6c3937116ddeb6ee（ローカル作業ツリーは古いので不使用）。実験は `git show` で書き出したコピー（scratchpad `local-gate/`）で実施
- 発端: PR #3861 が CI の process-artifacts gate で「設計docに ADR 参照（ADR-158）がありません」で失敗（run 36654731634）。PR 作成時の手元の関所は通っていた

## 1. CI の検査（`scripts/check-process-artifacts.js`）
- 実行元: `.github/workflows/process-artifacts-gate.yml:44`（`node scripts/check-process-artifacts.js`、PR_NUMBER／BASE_SHA／HEAD_SHA／REPO／HEAD_REF／BASE_REF を実値で渡す）
- モック用の環境変数: `scripts/check-process-artifacts.js:11-20`（CHANGED_FILES、MOCK_ADDED_FILES、MOCK_ORIGIN_MAIN_FILES、MOCK_PR_BODY、MOCK_PR_AUTHOR）。コメント外に MOCK_MIGRATION_DROP_DETECTED（:54）、MOCK_EXTERNAL_API_CHANGE（:162）、MOCK_BASE_REF／MOCK_HEAD_REF（:171-175、:711-712）、MAINTENANCE_ENFORCE（:682）
- 設計書の検査 `validateDesignDoc`: `scripts/check-process-artifacts.js:383-499`（受入条件表 :452-465、recon 相互参照 :472-475、ADR 参照 :478-482）
- PR 番号に依存する検査: 維持の仕組み欄（`MAINTENANCE_GRACE_PR` :84、判定 :678-692）、触る／削除するファイルの宣言照合（`GRACE_THRESHOLD_PR` :821、:821-880）。どちらも `parseInt(PR_NUMBER) >= 2600` で、PR_NUMBER なしだと NaN のため**検査されない**
- GO 記録の検査 `validateGORecord`（:340-406）: PR_NUMBER に**依存せず**、危険変更（`DANGEROUS_PATTERNS` :110-117、`scripts/` を含む :112）またはユーザー影響変更があれば必ず実行。GO 記録がないと exit 1 になり、その先の検査（設計書の検査を含む）に**進まない**

## 2. 実験（PR #3861 の再現、PR_NUMBER なしのモック実行）
| 設計書 | PR 本文 | 結果 |
|---|---|---|
| 修正前（db564dbed^） | GO 記録あり | exit 1「設計docに ADR 参照（ADR-158）がありません」 |
| 修正前 | GO 記録なし | exit 1「PR本文に『### GO記録』セクションがありません」（ADR の検査まで進まない） |
| 修正後（db564dbed） | GO 記録あり | exit 0「process-artifacts gate PASSED」 |
| 修正後 | GO 記録なし | exit 1（GO 記録のエラーのみ） |
→ そのまま呼ぶと、PR 作成時（GO 記録はまだ書けない）は危険変更・ユーザー影響変更の PR が**すべて** GO 記録で止まり、設計書の不備は検出されない

## 3. 手元の関所（`scripts/dev/validate-pr-body.sh`、288行）
- 入力: 標準入力の PR 本文（:16）。検査は Python で CI のロジックを**手で写したもの**（:39、:51、:68、:106、:203、:226 に「CIスクリプトと同じロジック」とある）。`check-process-artifacts.js` は呼んでいない
- CI にあって手元にない検査: 設計書の ADR 参照・recon 相互参照・受入条件表、GO 記録（:278「GO記録はPR番号確定後のマージ前full gateで検査する」）
- 維持の仕組み欄は警告のみ（:224-239）
- 呼び出し元: `~/.claude/scripts/pr-body-guard.sh:111`（`gh pr create/edit --body(-file)` のときに発火、:19-30）、フック登録は `~/.claude/settings.json:57`。もう1つの呼び出し元は `scripts/gh-pr-create-safe.sh:132`
- node: v24.12.0（手元で実行可）

## 4. 影響範囲
- `scripts/` の変更は CI でも危険変更（`scripts/check-process-artifacts.js:112`）＝GO 記録が必須（PO のみの例外 :43-49 には該当しない）
- テスト: `scripts/tests/test-process-artifacts.js`（1555行）、`scripts/tests/test-pr-lifecycle.py` があるが、**どの workflow からも実行されていない**（全71 workflow を grep）

## 5. 未確認
- 2つの「2600」定数（:84、:821）が別に定義されている理由
- テスト2本が手動実行の想定かどうか
