# design — 手元の担当（サブエージェント）の書き換え・保存・送り出しをフックで止める

- 状態: 設計案（第1版 2026-10-26）。審査前
- 関連: [recon.md](recon.md)・[ADR-1045](../../adr/ADR-1045-local-subagent-write-guard.md)・ADR-1029（前例）・ADR-1011:39（フックは AI がパッチ、PO が `!` で反映）
- PO の決定（2026-10-26）: 「1」重い実装と試験はクラウド、手元の担当は Mac の中を見る短い調べものだけ。「１」その決まりを仕組みで守らせるため、手元の担当の書き換え・保存・GitHub への上げを全部止める

## 1. あるべき姿

手元の Mac で Opus 本体が呼び出した担当（Sonnet・Opus のどちらでも）は、読む・数える・一覧を見ることはできるが、ファイルを書き換える道具を使えず、git に保存（commit など）も GitHub への送り出し（push・PR 作成など）もできない。決まりを破ろうとするとフックが止め、「クラウドに任せてください」と出る。Opus 本体とクラウドの作業は今までどおり。

## 2. KGI（PO の決定「１」から。○×で判定）

| # | 成功条件 |
|---|---|
| G1 | 手元の担当が Write・Edit・MultiEdit・NotebookEdit を使おうとすると止まる |
| G2 | 手元の担当が Bash で git の保存・送り出し（§5-3 の一覧）や GitHub への書き込み（§5-3 の gh の一覧）をしようとすると止まる |
| G3 | Opus 本体の同じ操作は止まらない |
| G4 | 手元の担当の読むだけの命令（git log・git status・git diff・gh pr view・ls・cat など）は止まらない |
| G5 | 審査役の流れ（審査役が VERDICT を返す → 記録 → 本体がマージ）が今までどおり回る |
| G6 | 試験の台本がリポジトリにあり、CI で自動で流れる |

対象外: 担当が Bash の命令文でファイルを書き換えること（`>`・`sed -i`・`tee` など）は止めない（§7 受け入れるリスク）。クラウドの見張り（scripts/agent-hooks/cloud/）は変えない。

## 3. KPI

- K-a: 導入後、手元の担当の Write/Edit/MultiEdit/NotebookEdit が通った件数 = 0（agent-console の活動記録の PostToolUse で agent_id 付きの行を数える。数えるのは本体）
- K-b: 導入後、本体の操作が誤って止められた件数 = 0（guard の log に agent_id 無しの止めが出ないことで見る。仕組み上 0 になる）

## 4. recon の要点（詳細は recon.md）

- 担当の呼び出しには agent_id が入り、本体には入らない（公式文書・実際の記録 49/54 件と 131/51 件。recon.md §1・§2）。model は入らないので agent_id の有無で分ける。
- 審査役は SubagentHandback で返すだけで、書き換えも commit も要らない（recon.md §3）。→ 例外の担当を作らず一律に止められる。
- 前例: review-gate の install/rollback/CI の型（recon.md §5）。命令文の読み方はクラウドの guard_pre_tool.py の scan_text を使い回す。

## 5. design

### 5-1. 置くもの（リポジトリ）

| ファイル | 役割 |
|---|---|
| scripts/agent-hooks/local-subagent-guard/guard.py | PreToolUse（matcher `Write\|Edit\|MultiEdit\|NotebookEdit\|Bash`）。§5-2 の判定 |
| scripts/agent-hooks/local-subagent-guard/test_guard.sh | 試験。偽の入力 JSON で §8 の全行を確かめる。本物の ~/.claude には触れない |
| scripts/agent-hooks/local-subagent-guard/install.sh | PO が `!` で実行。guard.py と scripts/agent-hooks/cloud/guard_pre_tool.py を ~/.claude/scripts/local-subagent-guard/ へ写し、settings.json の PreToolUse に 1 項目足す。review-gate/install.sh と同じ型（冪等・バックアップ `.bak-local-subagent-guard-<時刻>`・JSON 確認後に置き換え） |
| scripts/agent-hooks/local-subagent-guard/rollback.sh | PO が `!` で実行。足した 1 項目を消し、写したディレクトリを消す |
| .github/workflows/agent-hooks-test.yml | job を 1 つ足し `bash scripts/agent-hooks/local-subagent-guard/test_guard.sh` を流す（既存の review-gate の job は変えない） |
| docs/adr/ADR-1045-local-subagent-write-guard.md・docs/adr/README.md | ADR と索引（`node scripts/generate-adr-index.js`） |

Python 3 標準ライブラリだけ。guard_pre_tool.py は写したディレクトリから `import guard_pre_tool` で読み、`scan_text` だけを使う（他の関数・danger_ops.json は使わない。recon.md §5 のとおり読み込み時に外部ファイルを読まない）。

### 5-2. guard.py の判定（上から順に、最初に当たったもの）

1. 標準入力が JSON の辞書として読めない → 何もせず exit 0（本体か担当か分からず、本体を止めないため。§7）
2. `agent_id` が無い、または空 → exit 0（Opus 本体）
3. `tool_name` が Write・Edit・MultiEdit・NotebookEdit → 止める（G1）
4. `tool_name` が Bash: `tool_input.command` が文字列でなければ止める。文字列なら `guard_pre_tool.scan_text(command)` を通した文字列に §5-3 の正規表現を当て、どれかに当たれば止める（G2）。当たらなければ exit 0（G4）
5. それ以外 → exit 0

止めるときは exit 2、stderr に次の 1 行（担当の名前は agent_type をそのまま入れる）:
`手元の担当（<agent_type>）は、ファイルの書き換え・git の保存・GitHub への送り出しをしません（ADR-1045）。調べた結果を本体に返してください。書き換えが要る作業はクラウドで行います。`

止めたときだけ `~/.claude/scripts/local-subagent-guard/guard.log` に 1 行（時刻・agent_type・tool_name・当たった規則の名前）を足す。命令文そのものは書かない（秘密が混じりうるため）。log が書けなくても止めることは変えない。

### 5-3. Bash で止める命令（scan_text の後の文字列に当てる）

- git の保存・送り出し: `\bgit(\s+(-C\s+\S+|-c\s+\S+|--[\w-]+(=\S+)?))*\s+(commit|push|merge|rebase|cherry-pick|revert|am|tag)\b`
  （`git -C dir commit`・`git -c k=v push`・`cd x && git push`・`bash -c 'git commit …'`・`$(git push)` も当たる。scan_text は区切りごとに読むだけの区間（grep 等）を消し、git commit / gh の区間では引用符の中身を消す）
- GitHub への書き込み: `\bgh\s+(pr\s+(create|merge|edit|comment|review|close|reopen|ready)|issue\s+(create|edit|comment|close|reopen)|release\s+(create|edit|delete|upload)|repo\s+(create|edit|delete|fork)|workflow\s+run|run\s+(rerun|cancel))\b`
- gh api の書き込み: `\bgh\s+api\b` があり、かつ `(-X|--method)[ =]*(POST|PUT|PATCH|DELETE)` か `(\s-f\s|\s-F\s|--field|--raw-field|--input)` がある
- 決まった台本: 名前に gh-pr-merge-safe.sh・check-pr-merge-ready.py・new-worktree.sh を含む命令（正規表現は三つの名前の点を `\.` にして `|` でつなぐ）

読むだけの git（log・status・diff・show・fetch・ls-remote・rev-parse・branch の一覧）と gh（pr view・pr list・pr checks・api の GET）は当たらない。`echo "git push"` のような文字の中の語にも当たる（止める側に倒す。担当だけなので本体には影響しない。§7）。

### 5-4. 今のフックとの関係

- 足すのは PreToolUse の 1 項目だけ。worktree-only-guard・review-gate gate.py などの既存の項目は変えない。フックは全部が走り、どれか 1 つが止めれば止まる。
- review-gate の record.py（PostToolUse・SubagentHandback）は本体側で動くフックで、担当の Write ではない。審査役の流れは変わらない（G5）。
- ~/.claude/agents/*.md は変えない（担当の仕事の書き方は変えない。止められたら本体に返すことは stderr の文で伝わる）。

### 5-5. 導入・戻し方

- 導入: PR マージ後、本店の写しを main に合わせてから PO が `! bash scripts/agent-hooks/local-subagent-guard/install.sh`（ADR-1011:39）。新しく開いた会話から効く（開いている会話は設定を読み直すまで効かないことがある。試験 K5 は新しい会話で行う）
- 戻し方: PO が `! bash scripts/agent-hooks/local-subagent-guard/rollback.sh`。または install が作ったバックアップ `~/.claude/settings.json.bak-local-subagent-guard-<時刻>` を戻す

## 6. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| 担当の定義（~/.claude/agents/*.md）の tools から Write/Edit を外す | 名前の無い担当（general-purpose・Explore 以外の組み込み）には効かず、定義を変えれば外れる。bash の commit/push も止められない |
| 担当の model（sonnet）だけ止める | フックの入力に model が無い（recon.md §1） |
| Bash の書き換え（`>`・`sed -i`）も全部止める | 調べものの結果を /tmp に残す担当の作法（生出力をファイルへ）が壊れる。書き換えた物は保存・送り出しが止まるので外へ出ない |
| 止めずに記録だけ取る | PO の決定「１」は止めること |

## 7. 受け入れるリスク

- 担当は Bash の命令文でファイルを書き換えられる（`>`・`sed -i`・`python -c` など）。ただし保存と送り出しは止まるので、手元の作業場所の未保存の変更として残るだけ。本体が git status で見つけられる。
- 難しい書き方（変数で組み立てた命令・base64 で隠した命令など）は見抜けない。正規表現で読める範囲を止める。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 文字の中の語（`echo "git push"`）でも担当は止まる（誤った止め。担当だけ）。
- 担当が自分の調べた結果を Write で /tmp に残すことはできなくなる。Bash の `>` で残す（今の作法どおり）。

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 担当の Write・Edit・MultiEdit・NotebookEdit が止まる（exit 2・stderr に ADR-1045） | test_guard.sh: agent_id 付きの入力 4 種 |
| K2 本体（agent_id 無し・空）の Write と `git commit`・`git push` は exit 0 | test_guard.sh |
| K3 担当の保存・送り出しの書き方の違いが全部止まる: `git commit -m x`・`git -C /a commit`・`git -c a=b push`・`cd /a && git push`・`bash -c 'git push'`・`echo $(git push)`・`git merge x`・`git rebase main`・`git tag v1`・`gh pr create`・`gh pr merge 1`・`gh pr comment 1 -b x`・`gh api -X POST repos/a/b/issues`・`gh api repos/a/b/pulls -f title=x`・`bash scripts/gh-pr-merge-safe.sh --merge`・command が文字列でない | test_guard.sh |
| K4 担当の読むだけの命令は exit 0: `git log`・`git status`・`git diff origin/main`・`git -C /a log`・`git fetch`・`gh pr view 1`・`gh pr list`・`gh api repos/a/b/pulls`・`ls`・`cat x`・`grep "git push" f`・`git log --grep "commit"` | test_guard.sh |
| K5 JSON でない入力は exit 0 | test_guard.sh |
| K6 CI の agent-hooks-test で test_guard.sh が緑 | PR の checks |
| K7 実地: 導入後の新しい会話で、手元の担当（general-purpose・model sonnet）に /tmp の試しのファイルへの Write と、作業場所での `git commit --allow-empty -m test` を頼むと両方止まる。本体の Write は通る | 本体が会話で試し、結果を記録 |
| K8 実地: 審査役（reviewer・model opus）の審査 → VERDICT の記録 → マージの流れが 1 回通る | 次の PR のマージで確かめる |

## 9. 作業の分け方

- 便1（この設計の PR と実装を同じ PR にする）: クラウドの Sonnet が §5-1 のファイルを作り、test_guard.sh を流して push。本体が PR を作り、審査役の審査 → マージ。PO が `!` で install.sh。本体が K7・K8 を確かめる

## 維持の仕組み

- scripts/agent-hooks/** が変わる PR で CI（agent-hooks-test）が試験を流す。止めた件数は guard.log。週次の権限点検（ADR-1034）の対象に guard.log の件数を足すかは、導入後 1 週の件数を見て決める

## 10. 外部・過去事例の参照と我々への応用

外部事例は該当なし。Claude Code のフックで担当だけを止める公開の事例は探していない。根拠は公式文書の仕様（recon.md §1）と、この Mac の実際の記録（recon.md §2）で足りるため。過去事例として社内の ADR-1029（review-gate）を参照し、install・rollback・CI の型と、agent_id で担当を見分けるやり方（~/.claude/scripts/subagent-bash-wait-guard.py:37）をそのまま使う。
