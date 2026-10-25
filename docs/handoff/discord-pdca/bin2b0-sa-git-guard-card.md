# 便2b-0 自動回収と片付けの git に守りを付ける（Sales Anchor）作る係への指示書

- 設計: agent-console リポジトリ docs/handoff/discord-pdca/design.md 第13版（別リポジトリのためバッククォートなし） §4-5「守り」（:296-304）・§8 便2 の前提（:500）・§15（:719）。ADR-1039（Accepted）。自動回収の正本 ADR-114
- 目的: Discord 発のセッションが件の作業場所に仕込んだ設定（`core.fsmonitor`・`core.hooksPath`・入れ子のリポジトリ）が、囲いの外で動く自動回収（`scripts/reaper-worktree.sh`）と片付け（`scripts/disk-janitor.sh`）の git で動かないようにする
- 調べた実物（origin/main c233ec8。生出力 /tmp/CC報告ファイル/discord-pdca-bin2/38-recon-sa-reaper/）:
  - reaper が作業場所に向けて動かす git: :124 `branch --show-current`・:205 `status`・:223 `status --porcelain --untracked-files=all`・:230 `rev-parse -q --verify HEAD`・:231 `rev-list --count HEAD --not --remotes=origin`
  - reaper が元のリポジトリに向ける git（:59・:63・:76・:161・:382・:463・:482・:487・:503）は、この便では触らない（元のリポジトリの `.git/config`・`.git/hooks` は件のセッションの囲いで書けない。設計 §4-5・0-19）
  - janitor: :290 `git -C "${wt}" log -1 --format=%ct`・:389 `git -C "${path}" remote get-url origin`。reaper を呼ぶのは :397-399
  - `-c` の上書き・`--ignore-submodules` はどちらにも0件
  - 手元の git 2.39.3 で上書きを付けた `status --porcelain`・`rev-parse`・`rev-list --count`・`branch --show-current`・`log -1`・`remote get-url` は、付けないときと同じ返り値（07-git-probe.txt）
  - 2つの台本の試験 `scripts/tests/test-reaper-safety.sh`・`scripts/tests/test-disk-janitor.sh` は CI では走っていない（.github に参照0件）。手で回して記録を `docs/handoff/disk-janitor/evidence/` に残す作りになっている
  - `scripts/` は危険パス（`scripts/check-process-artifacts.js:117`）。マージには GO が要る

## 決めたこと
- 上書きの正本は新しいファイル `scripts/git-safe.sh` の1か所。中身は配列1つと説明だけ:
  - `GIT_SAFE_ARGS=(-c core.fsmonitor=false -c core.hooksPath=/dev/null)`
  - 先頭の説明: 囲いの外で作業場所に向けて動かす git はこれを付ける（ADR-1039・discord-pdca 設計 §4-5）。source して使う。source 時に何も実行しない
- reaper と janitor は `source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/git-safe.sh"` で読む。読めなければ、何も消さずに「git の守りを読めない」と出して終了コード 1 で終わる（消す側に倒さない）
- 上の reaper の5か所と janitor の2か所を `git "${GIT_SAFE_ARGS[@]}" -C …` にする
- reaper の `status` の2か所（:205・:223）に `--ignore-submodules=all` を付ける（入れ子のリポジトリの中で git を動かさない）
- **設計への追記（入れ子のリポジトリの部屋は消さない）**: `--ignore-submodules=all` を付けると、入れ子のリポジトリの中の未保存の変更が `status` に出なくなり、未保存の判定（:213-223）をすり抜けて部屋を消すおそれがある。そこで、チェック2 の初めに `git "${GIT_SAFE_ARGS[@]}" -C "${WORKTREE_PATH}" ls-files --stage` の中に mode `160000`（入れ子のリポジトリの印）の行が1つでもあれば `UNSAVED=1` にし、理由「入れ子のリポジトリがある（残す）」を今の保護の出し方に合わせて出す。`ls-files --stage` は入れ子の中に入らない。Sales Anchor は入れ子のリポジトリを使っていないので、今ある部屋の判定は変わらない（確かめは下の完了の確認7）
- 消す側の命令（:482 `worktree remove --force`・:487 `branch -D`）は変えない

## 守ること
- 下に書いた変更だけ。ほかの判定・文・既存の試験の期待は変えない
- 試験の作り物のリポジトリは `mktemp -d` の下に作り、試験の終わりに `trap` で片付ける（既存の試験の作り方に合わせる。`rm -rf` を使う既存の作りがあればそれに合わせ、新しい作りを足さない）
- 本物の部屋に向けて `--execute` を動かさない。確かめは dry-run だけ

## 変更
1. `scripts/git-safe.sh`（新規）
2. `scripts/reaper-worktree.sh`: source・5か所・`--ignore-submodules=all` の2か所・入れ子のリポジトリの保護
3. `scripts/disk-janitor.sh`: source・2か所
4. `scripts/tests/test-reaper-safety.sh` に足す:
   - G1 印の台本: 作り物の部屋で `core.fsmonitor` に「印のファイルを作る台本」を設定する（部屋の `.git` が指す置き場の config か、作り物の元のリポジトリの config。試験で再現できる方）。対照として上書きなしの `git -C <部屋> status` で印ができることを確かめて印を消し、reaper の dry-run を動かして印ができないこと
   - G2 入れ子のリポジトリ: 作り物の部屋に入れ子のリポジトリを commit した（mode 160000 がある）状態で、ほかの条件は消す対象になる部屋が、dry-run で「残す」に入り理由が出ること
   - G3 `scripts/git-safe.sh` が読めない（`DJ`/reaper の場所の写しから外した）とき、終了コード 1 で何も消さないこと（作れなければ省いて理由を書く）
5. `scripts/tests/test-disk-janitor.sh` に足す: J1 :290 の古さの判定が今どおり動くこと（既存の試験が通ればよい。足せる場合だけ、印の台本の確かめを1つ）
6. 正本の文書: `docs/adr/ADR-114-worktree-auto-cleanup.md` の R の一覧（:83 付近の R10 のあと）に1行「R11: 作業場所に向けた git は `scripts/git-safe.sh` の上書きを付け、`status` は入れ子のリポジトリに入らない。入れ子のリポジトリがある部屋は消さない（ADR-1039）」と、履歴の行（:161 付近の書き方に合わせる）を足す。`node scripts/generate-adr-index.js` を実行して `docs/adr/README.md` を作り直す
7. この指示書を `docs/handoff/discord-pdca/bin2b0-sa-git-guard-card.md` として同じ PR に入れる

## 完了の確認（生出力を /tmp/CC報告ファイル/discord-pdca-bin2/40-impl2b0/ に保存）
1. `bash -n scripts/git-safe.sh scripts/reaper-worktree.sh scripts/disk-janitor.sh`
2. `shellcheck`（手元にあれば。無ければ「無い」と記録）
3. `bash scripts/tests/test-reaper-safety.sh`（全件の生出力）
4. `bash scripts/tests/test-disk-janitor.sh`（全件の生出力）
5. 変更前（origin/main の写し）と変更後で、本物の元のリポジトリ（~/salesanchor）に向けた reaper の dry-run の「消す」「残す」の一覧を比べ、入れ子のリポジトリの理由以外で差が0件であること（dry-run だけ。両方の生出力を残す。時刻の差で変わる行があれば、その行を書き出す）
6. 3・4 の生出力を `docs/handoff/disk-janitor/evidence/` の既存の書き方に合わせて残すか、既存の置き場の決まりに従う（決まりが見つからなければ /tmp の生出力だけにして PR 本文に書く）
7. 本物の作業場所のうち mode 160000 を持つものの数（`git ls-files --stage` を各部屋で数えて）。0 であることを PR 本文に書く
8. `node scripts/check-process-artifacts.js` があれば PR 前に回す（使い方は scripts/ の実物で確かめる）
9. 作業前の決まり: `bash scripts/new-worktree.sh release/discord-pdca-git-guard --claude` で作業場所を作り、`./scripts/dev/executor-preflight.sh` を通す。1コミット（共著者行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`gh auth status` で shingo-cc を確かめて `gh pr create --base main`。PR 本文はテンプレートから作り、`### 標準ワークフロー確認` の節・触ったファイルの一覧・「危険パス（scripts/）を含むため GO が要る」・「Evaluator は画面のファイル変更 0 のため省く」を書く

## 想定分岐
- G1 の対照で印ができない（その作りでは fsmonitor が呼ばれない）→ 作り（config の置き場）を1回変えて試す。それでも出なければ G1 は「上書きありで結果が変わらない」だけを確かめ、PR 本文に再現できなかったことと生出力の置き場を書く
- 既存の試験が今の origin/main でも落ちる → 変更前の写しで同じ試験を回し、同じく落ちるなら PR 本文に書いて進む。変更後だけ落ちるなら止まって報告する
- 完了の確認5 で差が出る → 止まって報告する
- 本物の作業場所に mode 160000 を持つものが1つ以上ある → 止まって報告する
- `check-process-artifacts.js` や PR 起票の見張りに止められた → 言い換えずに止まって報告する

## 外部・過去事例の参照と我々への応用
- git 公式の説明では、`core.fsmonitor` と `core.hooksPath` はリポジトリの設定から読まれ、命令（台本）を動かせる。`-c` で渡した値は設定ファイルより優先される（git-config の説明「-c」と各項目の説明）。この便はこの優先の決まりを使い、作業場所の設定で命令が動かないようにする
- 過去の例: 同じ守りは設計 §4-5 が agent-console 側（差分の表示・PR の状態の git）にも決めており、agent-console の便2b-1 で同じ上書きを1か所の正本から付ける。数の実測は、本物の作業場所で入れ子のリポジトリを持つものが0か所（完了の確認7）であることだけを根拠にし、ほかの事例の数は使わない

## 維持の仕組み
- 守り手: 自動回収と片付けを変える PR の設計者（Opus）。PR の審査で G1〜G3・J1 の記録があるかを確かめる
- 上書きの正本は `scripts/git-safe.sh` の1か所。作業場所に向けた git を足すときはここを読む決まりを ADR-114 R11 に書く
- 守りの確かめは `scripts/tests/test-reaper-safety.sh` の G1〜G3 と `scripts/tests/test-disk-janitor.sh` の J1。CI では走らないため、自動回収か片付けを変える PR で手で回し、記録を `docs/handoff/disk-janitor/evidence/` に残す（既存の決まりのまま）
