# doc-agenda-nav 段0b 基準値（変更前）

design.md §8 の段0b の記録先。測定者: Opus（設計担当）＋Sonnet（数える作業）。K9 の表示は PO が新しい会話で取得。
生出力: /tmp/CC報告ファイル/an-stage1/stage0b/（リポジトリ外。本書には判定に使った値だけを写す）

## 基準時点

| 項目 | 値 |
|---|---|
| K8 の集団を確定した時刻 | 2026-10-23 14:43 JST（origin/main a20ebc5bc2121eedb341e899838e3fe2c642f208） |
| K8 の集団の最後の PR | #4686 |
| K9 を測った時点の main | 8b54381427c542ff470959753a4b0eb6c3062823（a20ebc5 から14コミット後） |
| 2つの時点で常時読込の文書に差が無いこと | `git diff --stat a20ebc5bc 8b5438142 -- CLAUDE.md AGENTS.md .claude/` が空（終了コード0） |
| 入口の行数（8b5438142） | CLAUDE.md 120行・AGENTS.md 281行（`git show 8b5438142:<file> \| wc -l`） |

## K8 守られた回数

### 集団（head が release/ で始まり main へマージされた PR、マージ時刻の新しい順に10件。release/doc-agenda-nav* は除く）

#4686 #4683 #4685 #4684 #4680 #4678 #4679 #4677 #4676 #4673（`gh pr list -R shingo-ops/salesanchor --state merged --base main --limit 60` から抽出）

### 強制の有無（draft/AGENTS.entry.md の行ごと。CI・Ruleset・フック・husky を確認）

file:line はすべて a20ebc5bc の時点（scripts/check-process-artifacts.js は 8b5438142 以降、127行目以降が1行ずれる）。行3-10・37 は事実の記述やリンクで、行動の決まりではないため対象外。

| 行 | 決まり | 判定 | 根拠 |
|---|---|---|---|
| 17 | 不可逆操作は PO 確認（一覧） | 一部強制（workflow-lint.yml の変更と cloud 実行時のみ）。手元のフックは未確認。gh/git で数えられない | scripts/check-process-artifacts.js:42-51,85,366／scripts/agent-hooks/cloud/guard_pre_tool.py:98-119 |
| 17 | Branch Protection・Ruleset・必須チェックの変更 | 未確認。gh/git で数えられない | － |
| 19 | permit-danger.sh／会話の同意票で許可 | cloud は全面禁止。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:4 |
| 21 | ADR-025 暗号化済シークレットの手動投入禁止 | 一部強制（cloud の本番 DB 書込止めのみ）。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:108-119 |
| 25-28 | VPS は制限付き鍵・無制限鍵の使い方 | cloud は本番への ssh を止める。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:117-118 |
| 32 | release/* → main は PR 経由（head は release/*・hotfix/*） | CI で強制（必須チェックには入っていない） | .github/workflows/pr-base-check.yml:26-27／Ruleset の必須チェック一覧に無し |
| 32 | main/develop へ直接コミット・直 push 禁止 | 強制済み | Ruleset の pull_request 必須（`gh api repos/shingo-ops/salesanchor/rules/branches/main`）／~/.claude/scripts/worktree-only-guard.sh:149-152 |
| 33 | shingo-cc 名義で PR | 強制済み（docs-only 例外の扱いは未確認） | scripts/check-process-artifacts.js:38,808-811（必須チェック process-artifacts gate） |
| 34 | 作業場所は ~/worktrees 配下 | 強制済み（手元の commit のみ） | frontend/.husky/pre-commit:3-26 |
| 35 | main を消さない | 強制済み（develop は未確認） | Ruleset の deletion |
| 36 | 危険パスは GO 記録まで main にマージしない | 強制済み | scripts/check-process-artifacts.js:116-126,311-381 |
| 42 | PR 本文の標準ワークフロー確認欄 | 強制済み | scripts/check-process-artifacts.js:255-263／scripts/dev/validate-pr-body.sh:33-35 |
| 34 | origin/main 起点で作る | 強制なし・数えられる（候補） | 読んだ範囲に検査なし |
| 43 | executor-checklist.md に従う | 強制なし・数えられる（候補） | 読んだ範囲に検査なし |
| 41 | 作業前に executor-preflight.sh | 強制なし・痕跡が PR/git に残らない | `git grep -l executor-preflight a20ebc5bc -- .github scripts` は scripts/dev/executor-preflight.sh 自身のみ（範囲を付けないと文書を含め多数ヒットする） |
| 44 | docs/INDEX.md から辿る | 強制なし・gh/git で数えられない | docs/INDEX.md は未新設 |
| 11・12・13・45 | Legacy 削除禁止・ADR 確認・ADR 優先・領域別 AGENTS.md | 強制なし・「守った」を一義に決められない | － |

未確認（今回は読んでいない）: agent-danger-hook.sh、/usr/local/bin/node の見張り、worktree-access-guard.sh、review-gate/gate.py ほか、CI 77本のうち上記以外。

### 候補2つの計数

| PR | 最初の commit の親は main の祖先か | 遅れ（main の first-parent で未取込の数） | 本文の「executor-checklist」の回数 |
|---|---|---|---|
| #4686 | はい | 0 | 0 |
| #4683 | はい | 1 | 0 |
| #4685 | はい | 0 | 0 |
| #4684 | はい | 0 | 0 |
| #4680 | はい | 0 | 0 |
| #4678 | はい | 0 | 0 |
| #4679 | はい | 0 | 0 |
| #4677 | はい | 0 | 0 |
| #4676 | はい | 0 | 0 |
| #4673 | はい | 0 | 0 |

コマンド: `gh pr view N --json commits` の最初の commit の親 P について `git merge-base --is-ancestor P origin/main`、`git rev-list --first-parent --before=<最初のcommitの日時> origin/main ^P --count`、`gh pr view N --json body -q .body | grep -c executor-checklist`。

### 判定

- 行34（origin/main 起点）: 10/10 が満たし、遅れも0か1。変更前から満点で、入口の作り替えの効果を示せない → 不採用。
- 行43（executor-checklist）: 0/10。PR テンプレート（.github/PULL_REQUEST_TEMPLATE.md、72行）に語が無く、決まりも本文への記載を求めていない。語の有無は「従ったか」を表さない → 不採用。
- **結論: K8 は入口の効果測定に使えない**（design.md §8 段0b ④）。PO へ戻した。
- PO 決定（2026-10-23、原文「1」）: 守られた回数での比較はやめ、K9（会話の始まりに読む量）と K10（目次を開いた割合）で比べる。
- design.md:37 と docs/specs/doc-agenda-nav/kgi.md の K8 の扱いへの反映は、後続の PR で行う（本 PR は測定記録のみ）。

## K9 会話の始まりに読む量

新しい会話（作業場所 release-doc-agenda-nav-baseline、HEAD 8b5438142）で何も話しかけずに /context を実行した表示。

| 区分 | トークン |
|---|---|
| 合計 | 65.2k / 200k（33%） |
| System prompt | 2.9k |
| System tools | 20.6k |
| MCP server instructions | 2.5k |
| Custom agents | 1k（8本） |
| **Memory files** | **19.7k（6ファイル）** |
| Skills | 4.8k（27本） |
| Messages | 13.8k |

- Memory files の内訳（表示の上位3つ）: ~/.claude/projects/-Users-tanizawashingo-salesanchor/memory/MEMORY.md 10.4k、CLAUDE.md 4.5k、~/.claude/CLAUDE.md 2.7k。
- 本テーマの作り替えで直接変わるのは Memory files（入口の文書）。変更後もこの区分を主に比べる。
- 【未確認】何も話しかけていないのに Messages が 13.8k ある理由。変更後の比較では、同じ条件で取った値どうしを比べる。

## K10 目次を開いた割合

- 変更前の値: 0（docs/INDEX.md は 8b5438142 に存在しない＝`git cat-file -e` の終了コード128）。
- 実測（2026-10-23、K12 と同じ20回）: **0/20**。docs/INDEX.md を含む道具の呼び出しは0件（[k12/result.tsv](./k12/result.tsv) の INDEX 列）。
- 数え方の変更（Opus 判断、2026-10-23）: 当初の「会話の記録で事後に確かめる」（design.md の維持の仕組み）は、下の K12 の事実1・2により使えない。K12 と同じ実行で数える。

## K12 必要な手順書まで開いた割合

### 過去の会話記録からは測れない（事実）

1. 会話記録（~/.claude/projects/ 配下）への Bash は見張り consent-guard が例外なく止める（~/.claude/scripts/agent-danger-hook.sh:242-260、docs/handoff/conversation-consent/design.md:133「読み取り専用の例外は作らない」）。正規の読み方は Read/Grep（同 design.md:122-135）だが、本セッションの担当には Grep ツールが無かった。scripts/dev/consent-audit.py は同意台帳との突き合わせ専用で、開いたファイルを数える機能は無い（:293、引数 :1028-1031）。
2. K8 の10件の PR 本文で「設計仕様書（あるべき姿）」にページ名があるのは #4677 の1件だけ（5件は「対象外」、4件は行なし）。過去の作業から「開くべき手順書」を一義に決められない。

→ PO 決定（2026-10-23、原文「1」）: 練習問題を AI に解かせて測る。

### 練習問題と条件（測定前に固定）

- 題・正解の集合・実行条件・数え方: [k12-tasks.md](./k12-tasks.md)（sha256 `820449563a838968f8c0d319fbfdc38c65ac18d848bcd2d93444ec053646dd5e`。測定前に取った値と同じ）。
- 正解の手順書の確認: 候補12組を origin/main の本文で照合し、正解が1つに決まらない2組（現在地調査・作業カード）を除いた（照合の生出力はリポジトリ外 /tmp/CC報告ファイル/an-stage1/k12/pairs.md）。T2・T10 は手順の所在が2か所に分かれているため、2本どちらでも正解とした。
- 実行の場所: origin/main 137b117eb42b7ae6d40cde5d68042e6bb51ffeb2 の detached 写し。docs/INDEX.md は無い（`test -e` で確認）。各回の後に写しの `git status --porcelain` が空であることを確認（20回とも空）。
- 実行: [k12/runall.sh](./k12/runall.sh)（題は [k12/prompts.tsv](./k12/prompts.tsv)）。`claude -p … --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none`。この Mac に `timeout` が無いため、600秒の上限は `perl -e 'alarm 600; exec @ARGV'` で付けた。claude の版は 2.1.309。
- 数え方: [k12/count.py](./k12/count.py)。assistant 行の tool_use の input に正解のパスが含まれれば「開いた」。

### 結果（[k12/result.tsv](./k12/result.tsv)）

| 題 | 1回目 | 2回目 |
|---|---|---|
| T1 画面に選ぶ欄を足す | 0 | 0 |
| T2 作業場所とブランチ | 0 | 0 |
| T3 commit・PR 前の確認 | 0 | 0 |
| T4 新しい依頼の進め方 | 0 | 0 |
| T5 秘密の値の入れ替え | 0 | 0 |
| T6 監視の通知 | 0 | 0 |
| T7 週次通知が届かない | 0 | 0 |
| T8 まとめ売りの新しい書き方 | 1 | 0 |
| T9 PO の相談を設計に | 0 | 0 |
| T10 画面の文字を足す | 0 | 0 |

- **K12 = 1/20**（T8 の1回目が `cat docs/runbooks/bundle-sale-new-wording.md` で開いた）。**K10 = 0/20**。
- 20回中15回は道具の呼び出しが0回（呼び出しがあったのは T1 の2回・T7 の2回・T8 の1回目）で、会話の始まりに自動で入る指示だけで答えた（tool_use 数の列）。
- 費用: 20回の total_cost_usd の合計 2.8363 ドル。全20回の終了コード0。
- T10: frontend/CLAUDE.md の文字列は最終回答と result 行にだけ出た。自動読込が起きたかは stream-json からは判別できない【未確認】。数えたのは道具の呼び出しだけ。

## 手順（変更後に同じ条件で測る）

1. K9: origin/main から作った新しい作業場所で `claude` を起動し、何も話しかけずに `/context` を実行して表示を記録する。
2. K10・K12: 段3c マージ後の origin/main の detached 写しで、k12-tasks.md を変えずに k12/runall.sh と同じ条件で20回実行し、k12/count.py で数える。k12-tasks.md の sha256 が上の値と同じことを先に確かめる。
3. K11: 段3a・3b・3c・4 の各段のマージ前に、design §5-2 の表で入口以外へ行く行ごとに移動先を grep し、在る行の数 / 移す行の数を PR 本文に書く。

## 変更後（段3c マージ後、2026-10-24 測定）

測定者: Opus（K9・記録）＋Sonnet（K10・K12 の実行と数える作業。[card-measure-after.md](./card-measure-after.md)）。生出力: /tmp/CC報告ファイル/an-measure-after/ と /tmp/CC報告ファイル/an-k9-*.txt（リポジトリ外）。

### K9 会話の始まりに読む量

前後を同じ条件にするため、変更前も取り直した。条件: 測る版の detached 写しで `claude -p "/context" --no-session-persistence`（claude 2.1.310）。上の「K9」節（対話画面で取った 19.7k）とは取り方が違うので、比べるのはこの表の2列どうし。

| 区分 | 変更前（8b5438142） | 変更後（4bd48fa42） |
|---|---|---|
| Memory files 全体 | 19.8k | 17.7k |
| うち自動メモリの索引（MEMORY.md、本テーマの対象外） | 10.5k | 10.5k |
| **K9（MEMORY.md を除く）** | **9.3k** | **7.2k**（目標 6.5k 以下に 0.7k 届かず） |
| うちリポジトリの入口（CLAUDE.md・AGENTS.md） | CLAUDE.md 4.5k ほか | CLAUDE.md 194・AGENTS.md 2.2k（計 約2.4k） |
| うち利用者側の4本（~/.claude/CLAUDE.md 2.7k・~/kb/AGENTS.md 1k・rules 2本 1.15k） | 約4.85k | 約4.85k（変更なし） |

- 判定: **K9 未達**。リポジトリ側は減ったが、残りの大半は利用者側の4本（段7の対象）。

### K10・K12（練習問題20回）

- 条件: 変更前と同じ（k12-tasks.md の sha256 一致、claude の引数同じ）。違いは版（4bd48fa42、docs/INDEX.md あり）と claude 2.1.310。数える道具の決め打ちを外した版で変更前の生出力を数え直し、K12 1・K10 0 を再現した（差は T1-1 の終了コード列だけ）。
- 結果（[k12/result-after.tsv](./k12/result-after.tsv)）: 20回とも終了コード0、写しの汚れなし。

| 題 | 1回目 | 2回目 |
|---|---|---|
| T1〜T7・T9・T10 | 0 | 0 |
| T8 まとめ売りの新しい書き方 | 1 | 0 |

- **K10 = 0/20**（変更前 0/20）。**K12 = 1/20**（変更前 1/20。同じ T8 の1回目が docs/runbooks/bundle-sale-new-wording.md を開いた）。目標（各 10/20 以上）に届かず、変化なし。
- 道具の呼び出しがあったのは6回（T1 の2回・T2-2・T4-2・T8-1・T10-2）、残り14回は0回。呼び出しの中身は、ファイル名やコードを grep・ls で直接探すもので、docs/INDEX.md を開いた回は無い（/tmp/CC報告ファイル/an-measure-after/tooluses.txt）。
- 費用: 合計 2.8806 ドル（変更前 2.8363 ドル）。

### 判定と次への申し送り

- 【事実】入口を短くしても、練習問題では AI は目次も手順書もほぼ開かず、最初から入っている指示だけで計画を答えた（20回中14回は道具0回）。
- 【未確認】開かない理由。plan モードの `-p` で「計画だけ」を求めた題の形が影響しているか、入口の「目次から辿る」の書き方が弱いのかは、今回の記録からは分けられない。
- K10・K12 を動かすには、入口の書き方とは別の手立て（題の出し方の見直し、または目次を開かせる仕組み）の検討が要る。どれを採るかは PO 判断。

## 原因調べ（目次を開かない理由を分ける、2026-10-25）

PO「1」（2026-10-25。開かない理由を先に確かめる）。作業指示: [card-k10-diagnose.md](./card-k10-diagnose.md)。版は測り直しと同じ 4bd48fa42、claude 2.1.310、各条件10題×1回。生出力: /tmp/CC報告ファイル/an-diag/（リポジトリ外）。

| 条件 | 題の後ろの文 | 入口（写しの AGENTS.md:44） | K10（count.py） | K10（読む道具だけ） | K12 | 費用（ドル） |
|---|---|---|---|---|---|---|
| A（測り直し、20回） | 「計画だけを…」 | そのまま | 0/20 | 0/20 | 1/20 | 2.8806 |
| B | 「だけ」を外した文 | そのまま | 1/10 | 1/10 | 1/10 | 1.8352 |
| C | 「計画だけを…」 | 強い書き方 | 1/10 | 1/10 | 0/10 | 1.7058 |
| D | 「だけ」を外した文 | 強い書き方 | 5/10 | 4/10 | 3/10 | 2.1422 |

- 文と強い書き方の1行: [k12/suffix-plan.txt](./k12/suffix-plan.txt)・[k12/suffix-open.txt](./k12/suffix-open.txt)・[k12/agents-line44-strong.txt](./k12/agents-line44-strong.txt)。結果: [k12/diag-B.tsv](./k12/diag-B.tsv)・[diag-C.tsv](./k12/diag-C.tsv)・[diag-D.tsv](./k12/diag-D.tsv)。30回とも終了コード0、写しの汚れなし。
- 【事実】count.py の数え方の欠け: 道具の呼び出しの入力に INDEX の文字列があれば数えるため、AI が計画を書き出した文（plan モードの Write）に docs/INDEX.md と書いただけの回も「開いた」に入る。D の T10 がこれに当たる（Write だけで、Read・Bash・Grep・Glob での INDEX の呼び出しは無い）。読む道具（Read・Bash・Grep・Glob）だけで数え直すと D は 4/10。A・B・C と変更前の20回は、どちらの数え方でも値が同じ（/tmp/CC報告ファイル/an-diag/strict-out.txt）。
- 判定（実行前に固定した決まり、カード §5）: B・C はともに 1/10。D は count.py で 5/10 なら「両方そろって初めて動く」、読む道具だけで 4/10 なら「どれにも当たらない → 決めずに PO に示す」。数え方で判定が分かれるため、Opus は決めずに PO に示す。
- 【事実】強い書き方と「だけ」を外した文の両方がそろった D でだけ、目次を開く回が増えた（B・C は A と同程度）。
- 【事実】D でも目次を開いたあと正解の手順書まで開いたのは一部（T1・T8 は開いた、T5・T6 は別の文書を読んだ）。T3 は目次を通らずに正解を開いた。
- 【未確認】10回ずつでは回数が少なく、1〜2回の差は偶然の範囲を出ない。

## 入口の案内を強めた後の測り直し（2026-10-25）

PO「1」（2026-10-25。入口の案内文を強い書き方に正式に変え、頼み方を実際の依頼に近づけ、本当に開いたときだけ数えて、前後を20回ずつ測る）。作業指示: [card-entry-strong.md](./card-entry-strong.md)。生出力: /tmp/CC報告ファイル/an-v2/（リポジトリ外）。

- 変更: AGENTS.md:44 を k12/agents-line44-strong.txt の1行に置き換えた（行数は53のまま）。
- 条件: k12-tasks.md「2026-10-25 の改定」（題の後ろは k12/suffix-open.txt、読む道具だけで数える `count.py <dir> 2 read`）。claude 2.1.310。
- 変更前の版 8b5438142（02:43:29〜03:02:14 JST）、変更後の版 06fb27719（03:02:36〜03:21:09 JST）。40回とも終了コード0、写しの汚れなし。

| 区分 | 変更前（8b5438142） | 変更後（06fb27719） |
|---|---|---|
| K10 目次を開いた回 | 0/20 | **7/20**（目標 10/20 に3回届かず） |
| K12 正解の手順書を開いた回 | 4/20 | **13/20**（目標 10/20 以上） |
| 道具の呼び出し（合計） | 42 | 68 |
| 道具を1回も使わなかった回 | 7/20 | 2/20 |
| 費用（ドル） | 3.9572 | 3.8117 |

- 結果: [k12/result-v2-before.tsv](./k12/result-v2-before.tsv)・[k12/result-v2-after.tsv](./k12/result-v2-after.tsv)。
- 判定（実行前に固定した決まり、カード §5）: **K12 合格**（13 ≥ 10）、**K10 未達**（7 < 10）。
- 【事実】Opus が生出力の写しで数え直し、2つの表と一致した。書く道具を含めた数え方（any）でも同じ値（/tmp/CC報告ファイル/an-v2/count-any-*.txt）。
- 【事実】目次を開いた7回は、どれも Bash の grep・head で docs/INDEX.md を読む呼び出し（/tmp/CC報告ファイル/an-v2/opus-check.txt）。
- 【事実】変更後の内訳。目次を開いて正解も開いた回は4（T6 の2回・T8-2・T9-1）。目次を開かずに正解を開いた回は9（T1・T3・T7・T10 の各2回と T8-1）。目次を開いたが正解を開かなかった回は3（T4 の2回・T5-1）。
- 【事実】変更前の K12 は 4/20 で、前の条件（「計画だけ」・書く道具も数える）での 1/20 と違う。条件を変えたので、前の条件での値とは比べない。
- 【未確認】題ごとに2回ずつで、同じ条件を繰り返したときのばらつきの幅は確かめていない。
