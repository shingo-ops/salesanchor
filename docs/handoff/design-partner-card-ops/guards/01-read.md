## 1. 読み取り（git・ファイル）

**worktree-only-guard.sh の実装（実測・全文読了）**

判定は3つだけ。それ以外は素通り。
1. リポジトリルートが `~/crm-app-new` か `/private/tmp/*` で `git (push|fetch)` → ブロック
2. **判定先ディレクトリのブランチが `develop` か `main` で `git commit`** → ブロック（`exit 2`）
3. `git push` に `--force`/`--force-with-lease` と `develop|main` → ブロック

判定先の決め方: 既定は `$PWD`。コマンドが `^[[:space:]]*cd[[:space:]]+<パス>` で始まり、**そのパスが実在すれば**（`[[ -d "$EXPANDED" ]]`）そこを見る。**実在しなければ `$PWD` に戻る**。

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| コマンドが `cd <パス>` で始まらない → `$PWD`（多くは main）で判定され `git commit` が止まる | **全コマンドを `cd <作業台のフルパス> && ` で始める**。変数代入・`echo`・`{` を先頭に置かない | 実測（上記コード）＋4セッションで再現 |
| `cd` のパスが存在しない → 同上（実在チェックで `$PWD` に戻る） | **パスは `git worktree list` で実測してから書く** | CARD-PMG-FIX11-11 |
| `git show $SHA:パス` を zsh が `${SHA:修飾子}` と解釈 → bad substitution | `git show "${SHA}:パス"` と囲む | CI-22（未検証） |
| `A && B` で A が `grep -c` の0件（exit 1）→ B が走らない | `;` で繋ぐ | 挙動差（未検証） |
| 出力に上限が無い → 転記崩れ・ディスク圧迫 | `head -N` / `tail -N` を必ず付ける | §5.5-9・CARD-BENCH-RECON-01（32GB） |
| 出力ファイルを列挙対象のディレクトリに置く → 自分を自分に書き足す | 出力先は列挙対象の外（`/tmp/CC報告ファイル/`） | CARD-BENCH-RECON-01 |
| `git diff origin/main` が両方向の差を出す | `git diff --cached $(git merge-base origin/main HEAD)` か `gh pr diff` | CI-23・CV-25（未検証） |
| `ls`/`find` だけで「無い」と判定 | `git show origin/main:<path>` で本店に確認してから言う | design-partner.md §8 |
| `timeout` が macOS に無い → exit 127 | 使わない | CG-07e（未検証） |
| 行番号を停止条件にする | 記録のみ。停止は不可逆操作にだけ付ける | §5.5-11/12 |

