# recon: 対策③（旧台帳の掃き出し）の現在地（2026-07-25）

> この文書は何か（専門用語なしの1行）:
> 古い台帳に取り残された行が何本あり、片付ける道具がなぜ動かないかを、実際に調べた事実だけで記録したもの。

親（あるべき姿）: ../../specs/ledger-guard/ideal-state.md
設計: ../../specs/ledger-guard/design-phase2.md

実測日: 2026-07-24 〜 2026-07-25

## 事実1: 引っ越し（便1〜便3）は完了している

- 便1（窓口3本の新設）: `scripts/ledger-lookup.sh` / `ledger-update.sh` / `ledger-view.sh` が実在
- 便2（読み手の付け替え）: `scripts/reaper-worktree.sh:138` と `:304` が `ledger-lookup.sh` 経由で読む
- 便3（書き手の切替）: `scripts/new-worktree.sh:135` は `active-work.d/` に登録する。本体には書かない
- 便3（凍結宣言）: 本体 `.claude-pipeline/active-work.md` の1行目に「【凍結アーカイブ】この台帳への新規登録は廃止されました」が実在
- 便3（pre-commit例外の撤去）: `frontend/.husky/pre-commit` に `active-work` の記述なし

## 事実2: 旧本体に418行が残っている

`.claude-pipeline/active-work.md` のテーブル行数 418。

| 状態 | 件数 |
|---|---|
| DONE | 310 |
| IN_PROGRESS | 86 |
| REVIEW | 5 |

生存行（IN_PROGRESS + REVIEW）91件のうち、`active-work.d/` に登録が無いものが 86件。

## 事実3: 生存86件の内訳（全数実測）

| 群 | 件数 | 判定根拠 |
|---|---|---|
| A マージ済み | 35 | `gh pr list --state all` で state=MERGED |
| B-1 CLOSED | 4 | state=CLOSED（claude-impl/20260604-074511 / feature/morimoto/qa-smoke-playwright-package / release/strict-test-green / release/strict-test-red） |
| B-2 OPEN | 26 | state=OPEN |
| C PRなし | 21 | PR が1件も無い |

C群21件のうち、`git ls-remote --heads origin` でリモートに存在するのは `feature/desk-check-tool` の1件のみ。残り20件はリモートに存在しない。

## 事実4: 本体から分割へ移す道具は存在しない

`scripts/` 配下で `active-work.d` を参照するのは 5ファイル（ledger-update / ledger-lookup / ledger-view / new-worktree / tests）。いずれも既存行を分割側へ移す処理を持たない。

## 事実5: 過去の掃き出し便は「足すだけ」だった

PR #2957「掃き出し便（退避61行の保全）」の差分は `.claude-pipeline/active-work.md` の +63 -0。削除ゼロ。行の移動や削除は行っていない。

## 事実6: 既存の棚卸し道具には安全な判定基準がある

`scripts/backfill-active-work-done.sh` の冒頭コメントに明記:

- gh で merged かつ base=main → DONE に更新
- closed（未マージ）→ 更新しない（安全側）
- PR なし → 更新しない（確証なし）

## 事実7: その道具はこの環境で動作しない

`scripts/backfill-active-work-done.sh:44` が `mapfile` を使用している。

実測（2026-07-25）:
- 環境の bash: `/bin/bash` GNU bash version 3.2.57(1)-release
- `mapfile` は bash 4.0 以降の組み込みコマンド。3.2 には存在しない
- `/bin/bash -c 'type mapfile'` の結果: `type: mapfile: not found`
- Homebrew 版 bash は `/opt/homebrew/bin/bash` `/usr/local/bin/bash` のいずれにも存在しない

## 事実8: 失敗が成功として報告される

同スクリプトは `set -e` を持たない（`grep -n "^set "` の結果: 指定なし）。

`mapfile` が失敗すると配列 `IN_PROGRESS_BRANCHES` は空のままとなり、`:55` の `if [ "${#IN_PROGRESS_BRANCHES[@]}" -eq 0 ]` が真となって「✅ IN_PROGRESS エントリなし」を出力し `exit 0` で終了する。

実測: dry-run 実行時、実際には86件が存在するにもかかわらず「エントリなし」と表示された。 `--execute` を付けた場合も同じ経路を通るため、何も更新せず成功として終了する。

`scripts/` 配下で `mapfile` を使うファイルは同スクリプト1件のみ。`readarray`（別名）の使用は0件。

## 未確定（推測で埋めないこと）

- B-2（OPEN 26件）を分割側へ移す手順は未設計。移す道具が存在しない（事実4）
- C群20件（リモートに存在しない）を「完了」と記録してよいかは未確認。既存道具の基準では「確証なし＝更新しない」に該当する
- `mapfile` 以外に bash 4.0 以降の機能を使っているスクリプトが在るかは未調査

## 次に着手すべきこと

1. `backfill-active-work-done.sh` の `mapfile` を bash 3.2 互換の書き方へ修正（危険操作・GO必須）
2. 修正後に dry-run で35件が検出されることを実測
3. GO を得て `--execute` を実行し、A群35件を DONE 化
4. B-2（26件）の移行手順を設計（対策③の本体）
