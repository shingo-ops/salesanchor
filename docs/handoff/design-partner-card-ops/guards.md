# guards.md — 停止ポイントの SSOT（作業の種類ごと・実測のみ）

> この文書は何か（専門用語なしの1行）:
> カードを出す前に「この作業ならここを見る」を引く対応表と、各作業で止まる形・回避形・機械検査の式。

- 日付: 2026-09-07
- 実測: CARD-GUARD-RECON-02（フック・スクリプト・関所の現物を1,523行で開示）。origin/main 916a7416 時点。
- 併記: 並行する全設計パートナーセッションからの停止事例 約60件。本セッションで裏を取っていないものは「未検証」と明記。
- 姉妹文書: card-ops.md（カードの書き方）。本書は「止まる場所」。
- 使い方: 常設指示には §0 の対応表だけを置く。本文は該当する節だけ引く。
- 未読: check-process-artifacts.js は897行中200行のみ読了（`触るファイル:` 解析 201行付近・GO記録判定 296行付近が未読）。`~/.claude/agent-tokens.json` の `danger_ops` 配列の中身が未読。

---

## 0. 対応表（常設指示に置くのはこれだけ）

| これから出すカードの作業 | 読む節 |
|---|---|
| git・ファイルの読み取りだけ | §1 |
| 本番 DB を読む | §2 |
| ファイルを作る・書き換える | §3 |
| worktree・ブランチを作る | §4 |
| PR を作る | §5 |
| マージする | §6 |
| migration を作る | §7 |
| VPS・SSH を触る | §8 |
| gh コマンドを使う | §9 |
| 実行役が交代した／Codex を使う | §10 |
| どのカードでも | §11 の検査式に通す |

---

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

## 2. 本番 DB の読み取り

**psql ガードの実装（実測）**: 独立ファイルは存在しない。`~/.claude/scripts/agent-danger-hook.sh` 内の1ブロック。**`git remote get-url origin` が `shingo-ops/salesanchor` を含むときだけ発火**。

ブロックする5パターン（正規表現・IGNORECASE）:
1. `ssh\b.*\bpsql\b.*<\s*\S` — ssh+psql < file
2. `ssh\b.*\bpsql\b.*-f\s+\S` — ssh+psql -f file
3. `\|\s*(?:ssh…psql|docker…psql|psql)\b` — pipe to psql
4. `docker\b.*\bexec\b.*-i\b.*\bpsql\b.*<\s*\S` — docker+psql < file
5. `docker\b.*\bexec\b.*\bpsql\b.*-f\s+\S` — docker+psql -f file

加えて `psql …-c "…"` のダブルクォート内に `INSERT INTO`・`UPDATE \w`・`DELETE FROM`・`CREATE `・`ALTER `・`DROP `・`TRUNCATE `・`GRANT `・`REVOKE ` があればブロック。

**訂正（重要）**: 不等号そのものは条件に**入っていない**。止まるのは `psql` の後ろに `< 非空白` が続くリダイレクト形。`WHERE x < 5`（空白あり）は通る。ただし確実を期すなら `BETWEEN` を使う。

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| 接続先を「recon.md と同じ方式」等で間接指定 → 実行役が独自探索し、**認証情報が出力ファイルに記録された** | ホスト・コンテナ・ロール・DB名・コマンドを**逐語**で書く | CARD-PMG-CHECK-01（事故・未検証） |
| `-e PGOPTIONS='-c default_transaction_read_only=on'` を書かない | 必ず付け、手順1で `SHOW transaction_read_only;` が on を確認してから次へ | CG-10・本セッション全便 |
| ヒアドキュメント `<<'SQL'` で SQL を渡す | パターン1に当たる。`-c` 方式で1クエリずつ | 事例2・2026-09-06 実測 |
| 先読み `(?<!` を含む SQL | `<` がパターン1に当たる。`substring()` で代用 | 2026-09-06 実測 |
| `-c "… IN ('pending')"` のシングルクォートが SSH 経由で `\047` のまま渡る | ドル引用符 `$$pending$$`、または `GROUP BY` で全件集計 | 事例1（未検証） |
| `DELETE FROM` 等を**ファイルに書くだけ**でも `danger_ops` の部分一致で止まる | 本文に危険語を書く手順を避ける。解除は PO が `bash scripts/permit-danger.sh "<op>"`（**1回限り・30分で失効**） | H-03・実測（permit の仕組み） |
| `~/.claude/permits/` に直接アクセス | 自己発行は別ガードで禁止（`permits-guard`）。必ず `permit-danger.sh` 経由 | 実測 |
| 接続先ホスト名を実測せず書く → `Could not resolve hostname` | `~/.ssh/config` の Host 名を先に実測。`ssh -G` は解決後の IP を返す | DBSSOT-RECON-03・D-02（未検証） |

## 3. ファイルを作る・書き換える

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| 「〜に本文を書く」と**散文で**指示 → Codex は組み立てず、確認コマンドだけ実行して停止 | ファイルを作る**コマンド**を書く（ヒアドキュメント全文を同梱） | CARD-OPS-PR-05・CARD-PMG-OP-01 |
| `<本文ファイル>` 等のプレースホルダ → 着手前に停止 | 未確定の値は、それを作る手順を先に置く | CARD-OPS-PR-03 |
| ヒアドキュメント本文が長い（157行）→ 実行役が「安全に転記できない」と停止 | 107行は通過、157行は不可（境界は未特定）。長い本文は PO がファイルを配置し、カードは検算だけにする | CARD-OPS-PR-03b／PR-04 |
| ヒアドキュメントは末尾改行を1つ落とす → 行数−1・md5 不一致 | md5 を停止条件にしない。検算は行数±1と末尾3行 | CARD-OPS-PR-02 |
| `apply_patch` を複数箇所に順に当てる → 1つ外れると後続が全滅、ファイルは無傷で「やったつもり」 | 1カード1箇所。新規は丸ごと書く | CARD-GAS-FRESH-01（未検証） |
| `apply_patch` で Delete と Add を同一パッチ → 失敗 | 1パッチ1ファイル1操作 | CARD-GAS-FRESH-08（未検証） |
| 543行・約20KB の HTML を `apply_patch` で新規作成 → 原因不明で失敗 | **未解決**。行数の境界を実測する | CARD-GAS-FRESH-09（未検証） |
| `Write` ツールで `~/.claude/permits/` に書く | worktree-only-guard がブロック（実測） | 実測 |
| 合格基準の `grep` パターンがインデント決め打ち → 偽停止 | パターンは実測してから書く。`^ *` で吸収 | CV-22（未検証） |
| 検出語にコメント文中の語（`DELETE`）→ 説明文に当たって止まる | 検出語は本文に現れない形にする | CV-22（未検証） |

## 4. worktree・ブランチ

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `git worktree add` で直接作る → pre-commit が規約外の場所からの commit を拒否 | `bash scripts/new-worktree.sh <ブランチ名>`（`~/worktrees/salesanchor/` 配下・active-work.md に自動登録） | CARD-PMG-FIX11-09・CV-44（未検証） |
| 別セッションの worktree に触る | `worktree-access-guard.sh` が「別セッションのworktreeへのアクセスは禁止」でブロック | 実測 |
| ブランチ名が `release/*` `hotfix/*` 以外で main 向け PR | `gh-pr-create-safe.sh` が**ハードブロック**（§5） | 実測 |
| 上流が origin/main を指す → `git push` 拒否 | `git push -u origin HEAD` | CV-43・MERGE-FIX-05（未検証） |
| 既存ブランチに `-b` で再作成 → already exists | 既存なら `-b` 無しで `git worktree add <path> <branch>` | CARD-BENCH-PR-02 |
| 正本に他便の先約 → 停止 | 触る前に `git grep -n "<ファイル名>" -- .claude-pipeline/` で先約確認（§6.5） | W-01・CARD-DP-RECON-03b |
| ローカル main に未解決コンフリクト → checkout 拒否 | ローカル main を起点にしない。origin/main から worktree | CARD-BENCH-RECON-02 |
| ディスク残量 → ENOSPC で worktree 作成が中途半端に失敗 | 手順0で `df -h .`。2Gi 未満なら止める | CARD-BENCH-PR-01 |
| マージ後 `cleanup-worktree.sh` が worktree とブランチを自動削除する | 削除される前提で、必要なファイルは先に退避 | 実測（gh-pr-merge-safe.sh 末尾） |

## 5. PR を作る

**gh-pr-create-safe.sh の実装（実測）**: `--base` 未指定なら main を自動付与。**`--base main` かつ head が `release/*`・`hotfix/*` 以外ならハードブロック**。`GITHUB_ACTIONS` があればスキップ。

**関所（check-process-artifacts.js・897行中200行読了）の実測**

- 危険パス（GO記録必須）: `^migrations/`・`^scripts/`・`deploy.yml`・`frontend/src/pages-layout.css`・`docs/STANDARD-WORKFLOW.md`・`process-artifacts-gate.yml`・`PULL_REQUEST_TEMPLATE.md`
- 実コード: `frontend/src/`・`frontend/public/`・`backend/app/`・`backend/tests/`・`lp/src/`・`.github/workflows/`・`scripts/`
- 利用者影響（GO対象）: `frontend/src/`・`backend/app/routers/`・`services/`・`auth/`・`tasks/`・`discord_gateway/`
- 正本（書類のみでも照合する）: `docs/specs/**/ideal-state.md`・`kgi.md`・`docs/ai-agents/*.md`（lessons.d 除く）・`CLAUDE.md`・`AGENTS.md`
- 分類外は `unknown` → **安全側で本検査へ**（見落としではなく既定で厳しい）
- **GO を出せるのは `shingo-ops` と `Shingo` のみ**（`AUTHORIZED_GO_ISSUERS`）
- コード変更 PR を作れるのは `shingo-cc` と `Hikky-dev`（`AUTHORIZED_AUTHORS`）
- 維持の仕組み欄の猶予は PR#2600 まで（それ以降は必須）

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `gh pr create` を直接 → `.pr-number` が書かれず、後のマージで中断 | `bash scripts/gh-pr-create-safe.sh --title … --body-file <実在パス>` → 続けて `register-pr.sh`（`gh-pr-create-safe.sh` が呼ぶ） | 実測・#3303・#3313 |
| `触るファイル:` を箇条書き・改行・バッククォート付き | 同一行・カンマ区切り・バッククォートなし。`### 標準ワークフロー確認` の見出しの**中**に置く | 5セッションで実測・CI-24 |
| `削除するファイル:` の宣言漏れ | 1行でも削除があれば全列挙。rename は `{old => new}` | #3319・CV-06（未検証） |
| `### GO記録` の欠落・`### GO 記録`（空白入り）・プレースホルダ | 見出しは空白なし。発行者・日時・GO #番号。GO 前は欄を作らない | #3313・#3315・CI-26（未検証） |
| 危険パス・利用者影響パスを触る PR に GO記録が無い | 上の実測リストで判定。`scripts/` 配下は全部が危険パス | 実測・#3338 |
| `対象ADR:` が「対象外」・推測したファイル名 | `ls docs/adr/` で実在確認。`ADR-072-tenant-schema-prefix-enforcement.md` 等 | CV-34・#3303（未検証） |
| design.md に `## 維持の仕組み`・`## 外部・過去事例の参照と我々への応用`・`\| 基準 \| 検証方法 \|`・recon パス・ADR 番号のどれかが無い | `docs/handoff/_templates/design.md` の欄名をそのまま使う。5点必須 | F-01・CV-34・CV-40・CARD-KW-PR-02 |
| recon.md 内のバッククォート付きパスが実在しない | 実在しないパスにバッククォートを付けない | CV-10（未検証） |
| PR 本文を編集しても関所は自動再判定しない | 新しい run の databaseId が変わったことを確認 | design-partner.md §6.5 |
| 書式で往復する | 書式は実行役に委ね、赤なら自己修正を許可。設計側は中身3点だけ指定 | card-ops §8 |

## 6. マージ

**gh-pr-merge-safe.sh の実装（実測・全文読了）**

- PR番号は `${WORKTREE_DIR}/.pr-number` から読む（`tr -d '[:space:]'` で空白除去）。**引数はすべて `gh pr merge` にそのまま渡る**
- チェック1: `.pr-number` が無い/空 → exit 1
- チェック2: `active-work.md` の PR# 列（6列目）と不一致 → exit 1
- リトライ: `not up to date` なら追従（`git merge origin/main` → `push` → `gh pr checks --watch --required`）を**最大2回**
- `rule violations|required status check|is not mergeable` → RULE_WAIT（30秒×3回、同一 HEAD で再マージ）
- コンフリクトは**自動解決しない**（即停止）
- 未知の拒否は安全のため停止
- 成功後、`cleanup-worktree.sh` が worktree とブランチを自動削除

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| `gh-pr-merge-safe.sh 3323`（番号を渡す）→ `gh pr merge 3323 3323` で失敗 | `bash scripts/gh-pr-merge-safe.sh --merge` | 実測・CARD-BENCH-MERGE-01 |
| 引数なし → 非対話でマージ方式が決まらず中断 | `--merge` 必須（このリポジトリは merge commit が正。CLAUDE.md:50 の記述は実態と逆） | CG-07b・実測 |
| `.pr-number` が無い・別の値・`cd` 失敗で本体リポジトリに書かれた | `register-pr.sh` が両方（`.pr-number` と台帳）を更新する。手で書かない | CARD-PRNUM-RECON-01 |
| BEHIND で拒否 | スクリプトが追従する。`--admin`/`--auto` は素通りに当たり禁止 | 実測・CI-10/20/30/31 |
| マージ完了を手元ログで判断 | GitHub 側（`mergedAt`/`mergeCommit`）で実測 | design-partner.md §6.5 |
| GO が実行役に届いていない | GO の文言は PO が実行役のウィンドウにも貼る。カードに「GO #番号 受領済み」を書く | CI-28（未検証） |

## 7. migration

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| ファイルを置くだけ → MIGRATION GUARD が落ちる | `scripts/run_all_migrations.sh` の末尾に `run_sql` を登録（現在188本） | CV-23・CARD-KW-RECON-03 |
| 検算に「スキーマ内の全テーブル数」等の全件カウント → 他の表を数えて例外 | 自分の担当範囲だけを数える | #3315（tenant_006）・常設指示 |
| テナントを推測 | tenant_001 = 空テスト、tenant_006 = Meta 審査専用（68表）。STANDARD-WORKFLOW.md:93 | #3315（未検証） |
| `migration-full-dryrun` は migrations 変更のある PR でしか走らない。集約は skipping を pass 扱い | 文書 PR の「pass」は実行ではない | CARD-KW-RECON-03 |
| 採番を推測 | root の `migrations/`。`YYYYMMDD_HHMMSS_説明_テナント.sql`。直近を実測してから採番 | CARD-BENCH-RECON-02 |
| アンカーが revert 済みで実在しない | `git show origin/main:` で実在確認 | CI-18（未検証） |
| migrations は CODEOWNERS で `@shingo-ops` 承認必須 | GO と承認は別。両方要る | 実測 |

## 8. VPS・SSH

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| 鍵を指定しない → `salesanchor-claude` は ForceCommand で監視4コマンドのみ | `manual-only/id_ed25519`（prod1）は PO の明示承認が必須。カードに「どの機体・どの鍵」を書く | 本セッション実測・§6-3 |
| 頼んだコマンドと無関係な定型出力が返る | 即停止（監視出力にすり替わっている） | design-partner.md §279 |
| 識別名を Host 名と思い込む | `~/.ssh/config` の Host 名を実測 | DBSSOT-RECON-03（未検証） |
| Codex の `sleep 180` が30秒で打ち切られる | 長い待ちは分割する | MERGE-FIX-08（未検証） |

## 9. gh コマンド（新規・実測）

**gh-scope-guard.sh が既定拒否で動いている。**

| 止まる形 | 回避形 | 出所 |
|---|---|---|
| 自分以外の PR への `gh` 操作 → 「PR#N は自分のPRではありません（許可なし）」 | 自分の PR（`.pr-number` の番号）だけ触る | 実測 |
| **`gh run view` / `gh run watch`** → 「所有権確認不可のため禁止」で既定拒否 | CI の失敗ログは `gh pr checks` で判定し、詳細が要るなら PO が画面で開く。`gh-pr-merge-safe.sh` 内の `gh pr checks --watch --required` は通る | 実測（**私の過去カードは止まる恐れがあった**） |
| 他セッションのブランチへの操作 | `claims` ファイルで所有権が管理されている | 実測 |

## 10. 実行役の制約（CC / Codex）

| 観点 | CC | Codex | 出所 |
|---|---|---|---|
| カードに無い確認 | 補うことがある | 補わない | CARD-CODEX-PROBE-01 |
| プレースホルダ | 補って進むことがある | 着手前に停止 | CARD-OPS-PR-03 |
| 散文の指示 | 組み立てることがある | 実行しない | CARD-OPS-PR-05 |
| `rm` / `rm -f` | 実行する | 環境が拒否 | CI-32・CV-32 |
| 長いヒアドキュメント | 284行通過 | 107行通過・157行拒否 | CARD-KW-PR-02・CARD-OPS-PR-03b |
| コマンドのタイムアウト | 長い sleep 可 | 30秒で打ち切り | MERGE-FIX-08（未検証） |
| worktree のパスを文脈から補う | 補う | 補わない | CV-36（未検証） |
| カード形式でない指示書 | — | 正しく拒否 | 事例9（未検証） |
| 交代時 | 挙動確認カード（7観点）を1便挟む | 同左 | card-ops §2 |

## 11. card-lint 検査式（scripts/card-lint.sh に写す）

カードのテキストを入力に検査する。1つでも該当したら実行前に差し戻す。**式は未実測。スクリプト化の際に1本ずつ動かして直す。**

| # | 検査 | 対応する節 |
|---|---|---|
| L01 | 手順のコマンド行が `cd ` で始まらない | §1 |
| L02 | プレースホルダ（`<` と `>` に挟まれた日本語） | §3 |
| L03 | `END OF CARD` が無い | card-ops §5 |
| L04 | 受領確認の文言が無い | §5.5-10 |
| L05 | 出力先と列挙対象が同じディレクトリ | §1 |
| L06 | `psql` 行に `<<`・`< file`・`-f `・`\| psql`・書き込みSQL | §2 |
| L07 | `psql` があるのに `default_transaction_read_only=on` が無い | §2 |
| L08 | `gh pr create` を直接呼ぶ | §5 |
| L09 | `gh-pr-merge-safe.sh` に番号を渡す | §6 |
| L10 | `--body-file` の値が `<` で始まる | §3 |
| L11 | `rm ` を含む | §10 |
| L12 | `git worktree add` を直接呼ぶ | §4 |
| L13 | `-b` のブランチ名が `release/` `hotfix/` 以外 | §4・§5 |
| L14 | `--draft` | §5.5-2 |
| L15 | 停止時の報告経路が本文に無い | card-ops §3 |
| L16 | `timeout ` を使う | §1 |
| L17 | `git show $SHA:` を引用符なしで使う | §1 |
| L18 | `--admin` `--auto` | §6 |
| L19 | 出力上限の無い一覧系（`gh run list`・`git branch -r` 等） | §1 |
| L20 | 外側フェンスがバッククォート3つで、内側にも同じものがある | card-ops §5 |
| L21 | **`gh run view` / `gh run watch` を含む** | §9 |
| L22 | `~/.claude/permits/` への直接アクセス | §2 |
| L23 | 危険語（`DELETE FROM` 等）を本文に含む | §2 |

**検査式にできていない**（人手の照合 §5.5 に残す）: 散文指示の検出、行番号の決め打ち、期待値の見積り、worktree パスの実在。

---

## 維持の仕組み

- 守り手: `scripts/card-lint.sh`（§11 を写したもの・未作成）。実行役側の UserPromptSubmit フックで走らせるか、PO が貼る前に走らせる。
- 停止が起きたら: ①カード不備なら該当節に1行＋§11 に検査式を1本足す。②ガード正常作動・③想定外は記録のみ。
- KGI: lint を通過したカードでの①停止 = 0%。lint の差し戻し件数は別計上。
- 未読（次便で埋める）: check-process-artifacts.js の 201行付近（`触るファイル:` 解析）と 296行付近（GO記録判定）、`~/.claude/agent-tokens.json` の `danger_ops` 配列。
