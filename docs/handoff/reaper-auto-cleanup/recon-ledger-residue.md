# recon: 台帳残骸による worktree 滞留（2026-07-24）

> この文書は何か（専門用語なしの1行）:
> 使い終わった作業フォルダが片付かない原因を、実際に調べた事実だけで記録したもの。

親（あるべき姿）: ../../specs/reaper-auto-cleanup/README.md

実測日: 2026-07-23 〜 2026-07-24
実測時 origin/main SHA: f83e22ecaba5690f9140a7d39035fca2d7f376a1

## あるべき姿（PO自筆・2026-07-23）

終わったものは完了報告をする。勝手に作られない。終わったものはreaperが消す。機械的に対策する。

## 事実1: reaper は台帳の変更を除外していない

`scripts/reaper-worktree.sh:154` — `git status --porcelain` の出力が1行でもあれば UNSAVED=1 とし保護する。
`.claude-pipeline/` を除外する記述は同ファイル内に存在しない（全文 grep で確認）。

## 事実2: 未保存で保護された worktree の内訳（2026-07-24 実測・全数走査）

対象: /Users/tanizawashingo/worktrees/salesanchor 配下 95フォルダ

| 分類 | 件数 |
|---|---|
| A 台帳ファイルのみ変更 | 26 |
| B 台帳＋他ファイル | 1 |
| C 他ファイルのみ | 7 |

## 事実3: A群26件の内訳（実物の差分で確認）

| 種類 | 件数 | 内容 |
|---|---|---|
| A1 完了記録の追加のみ（削除0行） | 9 | 全件が main 宛マージ済みPRを持つ |
| A2-a 同一行の IN_PROGRESS → DONE 書き換え | 11 | 道具による状態更新 |
| A2-b 新規行の追加（IN_PROGRESS） | 5 | 作業開始の登録 |
| A2-c 別行の入れ替わり | 1 | feature-morimoto-inventory-ui-cleanup |

A2-a の実例（release/field-size-leads）:

    - | release/field-size-leads | ... | IN_PROGRESS | | main | base=origin/main・frontend/leads |
    + | release/field-size-leads | ... | DONE | #3017 | main | merged: PR #3017 / 5b68f48c50451e9e715808a12816bac7e1c288bc |

同一ブランチの同一行で、ステータス列のみが変わっている。人の手による編集と判別できる差分は、26件中に確認されなかった。

## 事実4: 台帳に書き込む道具は3つ。いずれも commit しない

`active-work.md` を参照する全59ファイルを走査し、書き込み処理を持つものを抽出（2026-07-23 実測）:

- `scripts/ledger-update.sh:43` — `open(path, "w").write(...)`
- `scripts/backfill-active-work-done.sh:125-126`
- `scripts/release-worktree.sh:63`

`git add` / `git commit` のヒット数（同日実測）: ledger-update.sh 0件 / backfill-active-work-done.sh 0件 / reaper-worktree.sh 0件 / register-pr.sh 0件 / cleanup-worktree.sh 0件 / release-worktree.sh 0件 / new-worktree.sh 0件 / gh-pr-merge-safe.sh 0件

## 事実5: reaper 自身も台帳の DONE 更新を呼ぶ

`scripts/reaper-worktree.sh:306` — 削除処理の中で `ledger-update.sh <branch> --status DONE` を実行する。commit はしない。

## 事実6: 道具はすべて本店の台帳を対象にする

`ledger-update.sh` は `git rev-parse --git-common-dir` から MAIN_REPO_ROOT を算出する。
worktree 内で実行した場合の実測（2026-07-23）: git-common-dir = `/Users/tanizawashingo/salesanchor/.git` → MAIN_REPO_ROOT = 本店。

`register-pr.sh:32` / `gh-pr-merge-safe.sh:37` / `validate-pr-ownership.sh:42` も `${MAIN_REPO_ROOT}/${AGENT_ACTIVE_WORK_REL}` の形で本店を指す（2026-07-24 実測）。うち gh-pr-merge-safe.sh と validate-pr-ownership.sh は書き込み処理を持たない。

## 事実7: 本店と worktree の台帳は別ファイル

2026-07-23 実測（inode 比較）: 本店 inode 345074877 / worktree(release-header-btn-mold-1) inode 344841224。`diff` の結果は「中身が違う」。

`release/header-btn-mold-1` の完了記録行は worktree 側の台帳に存在するが、本店の台帳・origin/main の台帳・全コミット履歴のいずれにも存在しない（`git log --all -S` で確認）。

## 事実8: 書き込み時刻はマージ完了の直後

release-header-btn-mold-1 の実測（2026-07-23）:

- 04:55:23 — 当該 worktree の最終コミット（reflog）
- 05:06:28 — PR #2981 のマージコミット `1a291b84` 作成
- 05:07:55 — worktree 側の台帳が更新（stat）

当該 worktree の reflog には 05:07 前後のエントリが存在しない（最終は 04:55 の merge）。git 操作による書き換えではない。

## 未確定（推測で埋めないこと）

worktree 側の台帳ファイルを書き換えた主体は特定できていない。リポジトリ内の道具はすべて本店を対象とするため、worktree 側の変更を説明できない。書き込み時刻はマージ完了の1分27秒後。

## 滞留の構造（事実1〜8から言えること）

worktree 側の台帳に未コミットの状態更新が残る → reaper が `git status --porcelain` で1行でも検出すると「未保存あり」として保護する（事実1）→ マージ済みの worktree が削除されない → worktree が上限100に達する。

対策後に回る見込み件数: 20件（A1の9件＋A2-aの11件）。
