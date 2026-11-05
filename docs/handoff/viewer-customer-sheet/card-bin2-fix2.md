# 2つ目の作業（請求先フォーム）直し2 — 実装カード（main 取り込みのぶつかりを解く）

- 対象 PR: #5137（ブランチ `release/viewer-billing-form-bin2`）
- 親カード: docs/handoff/viewer-customer-sheet/card-bin2.md（PO 実装承認 2026-11-04「1」）
- 起票: Claude Opus（設計担当）2026-11-05。新しい機能・表・API・画面は足さない

## §1 観測事実

- `gh pr update-branch 5137` が `Cannot update PR branch due to conflicts` で止まった。
- `git merge-tree --write-tree --name-only origin/main 4aa0439cc` の結果、ぶつかりは `scripts/run_all_migrations.sh` の1か所だけ（他のファイルは自動で合わさる）。
- ぶつかりの中身（末尾の登録行）:
  - main 側: `# discord-server-management 便1b: …` と `run_sql migrations/20261106_100000_tenant_discord_config_purpose_pk.sql`
  - このブランチ側: `# viewer-customer-sheet 便2: …` と `run_sql migrations/20261105_120000_create_viewer_billing_profiles.sql`
- 2つの migration は別の表を触る（`tenant_discord_config` と `viewer_billing_profiles`／`viewer_login_tokens`）。互いに依存しない。
- `.github/workflows/migration-guard.yml` のチェック5は刻印の重複だけを見る（順番は見ない）。2つの刻印は重複しない。

Opus の決定（2026-11-05）: 両方の行（コメント行と run_sql 行の2行ずつ）を残し、刻印の早い順に並べる。つまり、このブランチの2行（20261105_120000）を先、main の2行（20261106_100000）を後にする。

## §2 触るファイル

| ファイル | 変えること |
|---|---|
| `scripts/run_all_migrations.sh` | ぶつかり記号（`<<<<<<<`・`=======`・`>>>>>>>`）を消し、§1 の決定の順で4行を残す。ほかの行は1字も変えない |

触らない: そのほか全部（migration の SQL・試験・画面を含む）。自動で合わさったファイルの中身も手で変えない。

## §3 手順

1. `git fetch origin`。ブランチ `release/viewer-billing-form-bin2` を取り出し、HEAD がこのカードのコミットであることを `git log --oneline -2` で確かめる。
2. `git merge origin/main --no-ff --no-edit`（このカードで1回だけ許す。rebase・reset・force は禁止のまま）。
3. ぶつかりが `scripts/run_all_migrations.sh` 以外にも出た → 止まる（`git merge --abort` してから BLOCKED:）。
4. §2 のとおり直す。`grep -c '^<<<<<<<\|^=======\|^>>>>>>>' scripts/run_all_migrations.sh` が 0。
5. 確かめ（生出力を報告に残す）:
   - `grep -n "20261105_120000\|20261106_100000" scripts/run_all_migrations.sh` が2行で、20261105_120000 の行番号が小さい
   - `bash -n scripts/run_all_migrations.sh` が exit 0
   - `git diff origin/main -- scripts/run_all_migrations.sh` が、このブランチの2行を足すだけ
6. `git add scripts/run_all_migrations.sh` → `git commit --no-edit`（合わせのコミット）。push は `git push origin release/viewer-billing-form-bin2` 単独。`git ls-remote` で番号を確かめる。

## §4 受入条件

| 基準 | 検証方法 |
|---|---|
| ぶつかりが解けた | GitHub の PR #5137 が「conflicts」でない・ぶつかり記号 0 |
| 両方の migration が登録されている | §3-5 の grep・CI「migration-guard」pass |
| ほかを変えていない | `git diff origin/main HEAD --stat` が、合わせ前の PR の変更ファイル一覧と同じ |

## §5 報告

- 受け取ったら最初に「カード 便2 直し2 を受領」と1行書く。
- 報告は PR コメントにしない。最後の返事に §3-5 の出力を書く（報告ファイルは作らない）。
- 止まったら最後の行を `BLOCKED:` か `NEEDS_DECISION:` で終える。終えたら `DONE: ` と push した HEAD の40桁。

END OF CARD
