# 便2b-2 自動回収と片付けで「git の繋がり」と「本店の繋がり」を確かめ、自動回収を最新の道具の写しから動かす（Sales Anchor）作る係への指示書

- 設計: agent-console リポジトリ docs/handoff/discord-pdca/design.md 第14版（別リポジトリのためバッククォートなし） §4-5「filter の道と git の繋がりの確かめ」（(b) 6条件・(b') 本店の繋がり・(c) 古い本店の台本を動かさない）・§2 K17・§8 便2b-2・§11・§15。ADR-1039（Accepted）。自動回収の正本 ADR-114。前の便のカード `docs/handoff/discord-pdca/bin2b0-sa-git-guard-card.md`
- 目的:
  1. 件の worktree の `.git` ファイル・`commondir`・`gitdir` が書き換えられ、git が偽の設定（filter の命令入り）を読む作業場所では、自動回収（`scripts/reaper-worktree.sh`）と片付け（`scripts/disk-janitor.sh`）がその作業場所に向けて git を動かさず、消さずに残す
  2. 本店の `.git/commondir`・`config.worktree` が仕込まれているときは、自動回収が本店に向けた git（fetch・worktree list・remove・branch -D・prune）を動かさず、何も消さずに終わる
  3. ログイン時と毎日 03:00 の自動回収と、`scripts/new-worktree.sh` が呼ぶ自動回収を、古い本店の写し（`~/salesanchor`。origin/main より4600件以上古く、`scripts/git-safe.sh` が無い）の台本で動かさない
- 入れる順番: この PR が先（マージ→設計者が道具の写し `~/.salesanchor-tools` を取り直し→ログイン時の起動設定を入れ替え）。そのあと agent-console v0.46.3（作業場所の作成の台本を道具の写しから動かす）を入れる。作る係は PR を作るところまで
- 調べた実物（origin/main c920a95。生出力 /tmp/CC報告ファイル/discord-pdca-bin2/54-recon-sa-link/・/tmp/CC報告ファイル/discord-pdca-bin2/59-recon-main-git/summary.md、審査の生出力 /tmp/CC報告ファイル/discord-pdca-bin2/58-review-sa-card/review-out.txt・/tmp/CC報告ファイル/discord-pdca-bin2/58-review-2b2-card/）:
  - reaper: :35 で `scripts/git-safe.sh` を source（読めなければ終了コード 1）。:66-71 で cwd の `git rev-parse --git-common-dir`（相対なら :70 `--show-toplevel`）から `MAIN_REPO_ROOT` を決める。本店に向けた git は :83 `fetch`・:168・:401 `worktree list`・:482 `rev-parse --git-common-dir`・:501 `worktree remove --force`・:506 `branch -D`・:522 `worktree prune`。:106-135 はテスト用の走査（`REAPER_WORKTREES_DIR` 指定時。:131 `branch --show-current`）、:136-168 は本番の走査（最初の行＝元のリポジトリと detached は除く）。:178 からの部屋ごとの判定で作業場所に向けた git は :213・:224・:238・:245・:246。:358-360 が「使用中（削除しない）」の出し方
  - janitor: :24 で git-safe.sh を source。:33-36 で根（`DJ_ROOT_WORKTREES`=~/worktrees・`DJ_ROOT_AC_WT`=~/agent-console-wt・`DJ_ROOT_SALESANCHOR`=~/salesanchor・`DJ_ROOT_AGENT_CONSOLE`=~/agent-console）。:55-58 `DJ_REPOS`（1行に「パス|owner/repo|行き先」。agent-console・ebay-gas-automation・crm-app-current・crm-app-canonical-20260830。salesanchor は入っていない）。R2 は :312 の根の繰り返しで、:335 の find が拾った `.git` ファイルごとに :316 で `wt` を決め、:318-326 で候補 `cands` を集め、:327 で候補が無ければ次へ、:328 で `dj_wt_unused`（:290。:298 `log -1`）。R4 :388-420 は `DJ_REPOS` の各リポジトリで :397 `remote get-url` の後、:404-407 で `( cd "${path}" && … bash DJ_REAPER )`。:139 `dj_skip <path> <理由>` が「残す」の出し方
  - `scripts/new-worktree.sh`: :49 `REPO_ROOT` は cwd の `git rev-parse --show-toplevel`。:65 `REAPER_SCRIPT="${REPO_ROOT}/scripts/reaper-worktree.sh"`、:67 `bash "${REAPER_SCRIPT}" --execute 2>/dev/null || true`。`${REPO_ROOT}/scripts/` を指す所はこの1か所（:83 は案内の文）。agent-console は v0.46.3 からこの台本を道具の写しから cwd=本店で動かす
  - GitHub Actions `.github/workflows/reaper-schedule.yml`: :13 毎日 03:00 JST、:17-19 main への push のたび、:47-56 で self-hosted の Mac の上で cwd=~/salesanchor のまま、最新の checkout の reaper を `--execute` で動かす。**この PR をマージした時点で、新しい確かめ付きの reaper が本番で `--execute` される**（起動設定の入れ替えより前）
  - 試験: `scripts/tests/test-reaper-safety.sh`（G1 :727-764 など。reaper はどれもテスト用の走査で動かしている。:611 などは `cd` で作り物の元のリポジトリを cwd にする）・`scripts/tests/test-disk-janitor.sh`（`check "説明" コマンド` の形。:45-46 で根を一時フォルダに向け、:68-76 で作り物の元のリポジトリ `gitmain` と `git worktree add` の worktree を作る。:176 の WT_NOGIT（`gitdir: /nonexistent-gitdir`）。J1/J2 :352-366）。**どちらも CI では走らない**。手で回して記録を `docs/handoff/disk-janitor/evidence/` に残す決まり（#4758 も同じ）
  - 起動設定: 手元の `~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist` は WorkingDirectory=~/salesanchor で `bash scripts/reaper-worktree.sh --execute`、RunAtLoad=true、毎日 03:00。リポジトリの `ops/launchd/jp.salesanchor.reaper-onlogin.plist` には 03:00 の指定が無い（手元とずれている）。:7-9 に「Hikky-dev-Mac に適用する場合」の説明。片付けの plist（04:00・RunAtLoad=false）は道具の写しの取り直しと確かめの後で動かす作り（`ops/launchd/jp.salesanchor.disk-janitor.plist:34`）
  - 手順の正本: `docs/ops/runner-commands.md:202-228`（reaper は `launchctl load`、片付けは `bootstrap`）
  - ADR-114 の決まりの一覧の書き方: `- **見出し（日付 R11）**：本文`（ADR-114:85）
  - 危険パス: `scripts/` と `ops/launchd/` はどちらも危険パス（`scripts/check-process-artifacts.js:115-125`）。マージには GO が要る
  - 手元の `realpath` は `/bin/realpath`（launchd の PATH にある）
  - 審査の実測: 本物の worktree（salesanchor 50・agent-console 5・ebay-gas-automation 2・crm-app-current 7）と元のリポジトリ4つは、6条件で誤って落ちるものが0件。R2 が拾う `.git` ファイル71件のうち、salesanchor・agent-console・ebay-gas-automation・crm-app-current のどれとも合わないのは、salesanchor-docs-staging 1・salesanchor-public 1・`~/.local/share/salesanchor/recovery/code-staging-recovery` 2・置き場の消えた1件。node_modules を持つものは今も「ガード: シンボリックリンク」などで残されている（`~/Library/Logs/disk-janitor.log:3019-3021`）

## 決めたこと
- `scripts/git-safe.sh` に関数を2つ足す（source 時は定義だけで何も実行しない、は今のまま）。合えば 0、合わなければ `GIT_SAFE_LINK_REASON` に理由の短い日本語を入れて 1 を返す。実パスは `realpath` で取り、`realpath` が無い・失敗したら 1（残す側）。ファイルの中身は `$(cat …)`（末尾の改行は除かれる）で読み、「1行だけ」は「`wc -l` が 1 以下で、読んだ中身に改行を含まない」とする（改行の無い1行のファイルも合格）。パスの末尾の `/` は除いてから比べる:
  - `git_safe_main_ok <元のリポジトリの最上位>`:
    1. `<元>/.git` が本物のディレクトリ（`[ -d ] && [ ! -L ]`）
    2. `<元>/.git/commondir` が無い（`[ ! -e ] && [ ! -L ]`）
    3. `<元>/.git/config.worktree` が無い（同じ）
  - `git_safe_link_ok <作業場所> <元のリポジトリの最上位>`。まず `git_safe_main_ok <元>`。P=作業場所、C=`realpath <元>/.git`:
    1. P の実パスが `<元>` の実パスと同じなら、`P/.git` が本物のディレクトリで実パスが C なら 0
    2. それ以外は worktree として: `P/.git` が本物のファイル（`[ -f ] && [ ! -L ]`）、1行だけで `gitdir: <G>` の形。G が相対なら P を起点。`dirname "$(realpath G)"` が `C/worktrees`
    3. `G/commondir` の中身（相対なら G の実パスを起点）の実パスが C
    4. `G/gitdir` の中身（相対なら G の実パスを起点）の実パスが `P/.git` の実パス
    5. `G/config` と `G/config.worktree` が無い
- reaper:
  - :71 の後（本店に向けた :83 の fetch より前）で確かめる。合わなければ「元のリポジトリの git の繋がりを確かめられない（<理由>）。何も消さない。本店の最上位で動かしてください」と出して終了コード 1（3回目の審査 L4: new-worktree.sh :83 の案内に従って worktree の中で動かした人に、直し方が分かるように）:
    - 本番の走査のとき（`REAPER_WORKTREES_DIR` が空）: cwd が本店の最上位であることを求める。`git_safe_link_ok "${PWD}" "${PWD}"`（中で `git_safe_main_ok` も通る）に加え、`realpath "${MAIN_REPO_ROOT}"` と `realpath "${PWD}"` が同じであること。cwd が worktree や下のフォルダなら落ちる（再審査 M1: worktree の `.git` ファイルが辻褄の合う偽の本店を指すと、worktree の申告どおりの本店を確かめても防げないため。自動の呼び元＝起動設定・Actions・片付けの R4・agent-console はどれも cwd=本店の最上位）
    - テスト用の走査のとき: 今の試験は作業場所の最上位などから動くので、`git_safe_link_ok "${PWD}" "${MAIN_REPO_ROOT}"` にとどめる
    - 本店の `commondir` が偽の置き場を指すと `MAIN_REPO_ROOT` が偽の置き場の親になり、cwd と食い違うのでここで落ちる
    - 人や AI が worktree の中から `bash scripts/new-worktree.sh` を動かすと、new-worktree.sh :67 の `2>/dev/null || true` で自動回収は黙って飛ばされる（消す側には倒れない）。PR 本文に書く
  - :66・:70 の `rev-parse` は確かめより前に動く。命令が動かないことを試験 G8 で確かめる
  - 本番の走査のとき（`REAPER_WORKTREES_DIR` が空のとき）だけ、:178 の部屋ごとの判定の最初（チェック 0 の前）で `git_safe_link_ok "${WORKTREE_PATH}" "${MAIN_REPO_ROOT}"` を確かめる。合わなければ新しい入れ物 `SKIP_LINK` に「ブランチ名（理由）」を入れて `continue`（その部屋には git を1回も動かさず、消さない）。出力は :358-360 の書き方に合わせて「🔗 git の繋がりが本店と合わない（削除しない）: N 件」
  - テスト用の走査（:106-135）には部屋ごとの確かめを足さない（作り物の部屋は worktree ではないため。本番の起動設定・片付けの R4・Actions がこの変数を使っていないことは審査で確かめ済み。完了の確認8 でもう一度確かめる）
- `scripts/new-worktree.sh`: :65 を `REAPER_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/reaper-worktree.sh"` にする（自分と同じ置き場の自動回収を動かす。reaper :35 と同じ書き方。:67 の `--execute` と :76 の上限のときの dry-run の両方がこの変数を使う）。cwd は今のまま。ほかの行は変えない
- 残る弱さ（受け入れる）: 目的3 の new-worktree.sh の分は、agent-console v0.46.3 が new-worktree.sh 自身を道具の写しから動かす道でだけ成り立つ。人や AI が本店で `bash scripts/new-worktree.sh` を動かすと、今後も本店の写しの自動回収が動く（本店の写しを最新に保つのは別の話。この便では扱わない）。PR 本文に1行書く
- 3回目の審査の記録だけの指摘（PR 本文に書く）: J5 は確かめを外しても `remote get-url` の失敗で偽の reaper が呼ばれないことがあるので、判定は理由の文で行う（L5）。テスト用の走査の本店の確かめを外しても落ちる試験は無い（本番の呼び元はこの変数を使わないので害は無い。L7）
- janitor:
  - 新しい一覧は作らない。R2 で照らす元のリポジトリは、`DJ_ROOT_SALESANCHOR` と、`DJ_REPOS` の各行の「パス」（`|` の前）。読み出しは R4 :394 と同じ書き方にする
  - R2: :327 と :328 の間（候補を集めた後・`dj_wt_unused` の前）で、照らす元のリポジトリのどれか1つと `git_safe_link_ok "${wt}" <元>` が合うかを見る（無い元のリポジトリは飛ばす）。どれとも合わなければ各候補を `dj_skip "<候補>" "git の繋がりが知っている元のリポジトリと合わない（残す）: <理由>"` にして次へ。理由は最後に照らした元のリポジトリのもの
  - R4: :397 の `remote get-url` の前で `git_safe_link_ok "${path}" "${path}"`。合わなければ `dj_skip "${path}" "git の繋がりを確かめられない（残す）: <理由>"` で次へ
  - 照らす一覧に無い元のリポジトリ（salesanchor-docs-staging・salesanchor-public・recovery の写しなど）の worktree は、残す側に倒す。今もこれらの node_modules は残されているので、消す・残すは変わらず、理由の文だけが変わる
- 起動設定（`ops/launchd/jp.salesanchor.reaper-onlogin.plist`）:
  - ProgramArguments の3つ目を次の形にする（XML の中では `&&` を `&amp;&amp;`、`>&2` を `&gt;&amp;2` と書く。片付けの plist :34 と同じ。`--dry-run` は reaper の知らない引数で、`--execute` 以外は dry-run になる＝reaper :41-44）。道具の写しの取り直しと確かめは片付けの plist :34 と同じ4つ（fetch・未保存なし・`checkout --detach origin/main`・HEAD が origin/main）:
    `T=/Users/tanizawashingo/.salesanchor-tools; { <取り直しと確かめの4つを && で繋ぐ>; } || { echo "reaper: 道具のコピーの更新・確認に失敗したため実行しない" >&2; exit 1; }; cd /Users/tanizawashingo/salesanchor || exit 1; bash "$T/scripts/reaper-worktree.sh" --execute; rc=$?; [ "$rc" -eq 0 ] || echo "reaper: 自動回収が終了コード $rc で終わった" >&2; exit "$rc"`
    （審査 L6: 取り直しの失敗と、自動回収そのものの失敗を別の文にする）
  - cwd を本店にするので、`MAIN_REPO_ROOT`・台帳・ledger-lookup.sh の動きは今と同じ（Actions :47-56 と同じ形で、毎日動いている）
  - 毎日 03:00 の `StartCalendarInterval` を足す（手元の実物に合わせる）。RunAtLoad=true・KeepAlive=false・ログの置き場は今のまま
  - 冒頭の説明:
    - 配置を `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist`、停止を `launchctl bootout gui/$(id -u)/jp.salesanchor.reaper-onlogin` にする
    - 「古い本店の写しで動かさない理由（ADR-1039 便2b-2）」を1行
    - 「RunAtLoad=true なので、bootstrap した瞬間に `--execute` が1回走る（今の `launchctl load` も同じ）。入れ替える前に、3つ目の引数の `--execute` を `--dry-run` にした形を手で1回動かして通ることを確かめる」を1行（審査 L5）
    - 「ログイン直後にネットワークが繋がらないと取り直しが失敗して、その回は動かない（消す側には倒れない）。受け入れる（毎日 03:00 と Actions で動く）」を1行（審査 L6）
    - 「Hikky-dev-Mac に適用する場合」に、`T=` を `/Users/hitoshi/.salesanchor-tools`、`cd` を `/Users/hitoshi/salesanchor` にすることを足す（審査 L4）
  - `docs/ops/runner-commands.md:202-228` の reaper の手順を同じ書き方に直す
  - 時刻の重なり: 03:00 は Actions の定期（:13）と同じ時刻、04:00 は片付け。重なっても、ロックの待ち（起動設定では待たない）か道具の写しの git の失敗で「実行しない」側に倒れる（消す側に倒れない）。足す仕組みは無い
- 正本の文書: `docs/adr/ADR-114-worktree-auto-cleanup.md` の決まりの一覧の R11（:85）の後に、同じ形で `- **git の繋がりの確かめと最新の台本（2026-10-26 R12）**：作業場所・本店に向けた git の前に `scripts/git-safe.sh` の `git_safe_link_ok`（本店は `git_safe_main_ok`）で git の繋がりを確かめ、合わない部屋は消さない。本店が合わない、または本番の走査を本店の最上位以外で動かしたときは何も消さずに終了コード 1。片付けの R2 は本店と片付けの対象のリポジトリの一覧に照らし、どれとも合わない作業場所は残す。ログイン時・03:00 の自動回収は最新の道具の写しから動かし、`scripts/new-worktree.sh` は自分と同じ置き場の自動回収を動かす（ADR-1039 便2b-2）。` を足し、履歴の行を今の書き方に合わせて足す。`node scripts/generate-adr-index.js` を実行して `docs/adr/README.md` を作り直す

## 守ること
- 下に書いた変更だけ。ほかの判定・文・既存の試験の期待は変えない。例外は `scripts/tests/test-disk-janitor.sh:176` の説明の文（WT_NOGIT は git の繋がりの確かめで先に残されるようになるので、「git の繋がりが合わない・git log が失敗する（L1）」に直す。期待（node_modules が残る）は変えない。審査 L2）
- 試験の作り物は `mktemp -d` の下に作り、既存の片付けの作りに合わせる。新しい消し方を足さない。作り物の元のリポジトリには、`$HOME/worktrees` の下の名前と重ならない名前（例 `linkcheck-main-<乱数>`）を付ける（自動回収のゴーストの検出が `$HOME/worktrees/<元の名前>` を読むため）
- 変える1行は**同じ長さの書き換え**にする（例: 中身 `1\n` の追跡しているファイルを `2\n` にする。長さが変わると git が中身を読まずに「変更あり」と決めて filter が呼ばれず、対照が作れない。審査 M1・H2）
- 本物の部屋に向けて `--execute` を動かさない。確かめは dry-run だけ
- 手元の `~/Library/LaunchAgents/` の入れ替えと道具の写しの取り直しは、マージと GO の後に設計者（Opus）が行う。作る係はしない

## 変更
1. `scripts/git-safe.sh`: `git_safe_main_ok`・`git_safe_link_ok`
2. `scripts/reaper-worktree.sh`: 本店の確かめ・本番の走査の部屋ごとの確かめ・`SKIP_LINK` の出力
3. `scripts/new-worktree.sh`: :65
4. `scripts/disk-janitor.sh`: R2・R4
5. `scripts/tests/test-reaper-safety.sh` に足す（作り物の元のリポジトリ: `git init`・`f.txt`（`1\n`）を1回 commit・`git init --bare` の偽の remote に push。偽の置き場＝元の `.git` を写して `worktrees` を除き、`config` に `[filter "evil"]`・`clean = touch <印>; cat`、`info/attributes` に `*.txt filter=evil`。reaper は**本番の走査**で dry-run: cwd=作り物の元のリポジトリ、`REAPER_WORKTREES_DIR` を空、`REAPER_SKIP_FETCH=1`、R9-g と同じく試験用の `REAPER_LOCK_DIR` を付ける（本物のロックとぶつかって skip にならないように。3回目の審査 L6）、既存の偽の gh と台帳の作りを使う）:
   - 作り物の作り: G4・G5・G6 はそれぞれ別の `git worktree add` の worktree にする。偽の remote に push した後、元のリポジトリで `fetch origin` する（G6 の HEAD が `refs/remotes/origin/*` から届くように。既存の R9-g :604 と同じ）
   - G4 偽の置き場（commondir）: `git worktree add` の worktree の `f.txt` を `2\n` にし、その `commondir` を偽の置き場に向ける
     - 対照: その worktree で `git -c core.fsmonitor=false -c core.hooksPath=/dev/null status --porcelain --ignore-submodules=all` を動かして**印ができる**こと（できなければ FAIL）。印を消す
     - reaper の dry-run で印ができず、出力の「git の繋がりが本店と合わない」にその部屋が入り、削除候補に入らないこと
   - G5 偽の gitdir: 同じく worktree の `.git` ファイルを偽の gitdir（`.git/worktrees/<名>` の中身を写し、`commondir` を偽の置き場に向けたもの）に向ける。印ができず、「合わない」に入ること（対照は取らない）
   - G6 正しい worktree: 同じ作り物の正しい worktree が「合わない」に入らず、今の判定どおり（DONE＋未保存なしなら削除候補）になること
   - G7 元のリポジトリの `.git` をシンボリックリンクにした作り物で、終了コード 1・何も消さないこと
   - G9 cwd が worktree: 正しい worktree（G6）を cwd にして本番の走査の dry-run を動かし、終了コード 1・「何も消さない」の文が出ること（再審査 M1 の確かめ）
   - G8 本店の `commondir`: 元のリポジトリの `f.txt` を `2\n` にし、`.git/commondir` を偽の置き場の絶対パスにする。対照: 元のリポジトリで上書き付きの `git diff --no-ext-diff --no-textconv --ignore-submodules=all --numstat` を動かして**印ができる**こと。印を消してから reaper の dry-run を動かし、終了コード 1・「何も消さない」の文が出る・印ができないこと（:66・:70 の `rev-parse` で印ができたら FAIL）。終わったら `commondir` を消す
6. `scripts/tests/test-disk-janitor.sh` に足す（既存の `gitmain` を使う。照らす一覧に入れるため、試験の `DJ_REPOS` に `${GM}|owner/gm|main` の1行を足す。`DJ_ROOT_SALESANCHOR` は R_SA の試験（:39-46・:82・:99・:142・:156-157・:178・:207-254・:361-364。3回目の審査 L3 で実物に合わせた）が使うので向け直さない。副作用として R4 が gitmain について「origin が想定と違う」の行を1行多く出す。既存の :196・:198 の期待は今のまま通る（:124-130 の作り。再審査 M4））:
   - J3: R2 の対象になる worktree（`mk_nm`）の追跡しているファイルを同じ長さで変え、`commondir` を偽の置き場に向ける。偽の置き場は別の試験ファイルの G4 を写さず、この試験の中で gitmain の `.git` を写して `worktrees` を除き、`config` に `[filter "evil"]`・`clean = touch <印>; cat`、`info/attributes` に `README.md filter=evil` を書いて作る。書き換えるのは gitmain が追跡している `README.md`（中身を作りで確かめ、同じ長さで1文字変える。3回目の審査 L2）。対照として、その worktree で上書き付きの `git diff --no-ext-diff --no-textconv --ignore-submodules=all --numstat` で印ができること（`git log` は作業場所のファイルを読まないので対照にならない）。印を消す。書き換えたファイルと worktree の更新日時を既存の試験と同じやり方（既存の古い日時にする関数）で古い日時に戻す（確かめが無ければ削除候補に入る作りにするため）。dry-run で印ができず、その node_modules が「残す」に入り、理由に新しい文「git の繋がりが知っている元のリポジトリと合わない」が含まれること（判定はこの文で行う。再審査 M3）
   - J4: 照らす一覧に無い元のリポジトリの worktree の node_modules が「残す」に入り、同じ新しい文が出ること
   - J5（R4）: `DJ_REPOS` の1行に `.git/commondir` を置いた作り物のリポジトリを入れ、dry-run で、そのリポジトリについて偽の reaper が呼ばれない（既存の REAPER_LOG に出ない）ことと、理由「git の繋がりを確かめられない（残す）」が出ること
   - 既存の R2 の試験（`WT_DEL`・`WT_ACDEL` など）の期待が今のままで通ること
7. `ops/launchd/jp.salesanchor.reaper-onlogin.plist`・`docs/ops/runner-commands.md`: 上の「決めたこと」
8. ADR-114 と `docs/adr/README.md`
9. この指示書は設計者がこのブランチに先に記録済み。作る係は書き換えない

## 完了の確認（生出力を /tmp/CC報告ファイル/discord-pdca-bin2/57-impl2b2-sa/ に保存）
1. `bash -n scripts/git-safe.sh scripts/reaper-worktree.sh scripts/disk-janitor.sh scripts/new-worktree.sh`
2. `shellcheck`（手元にあれば。無ければ「無い」と記録）
3. `bash scripts/tests/test-reaper-safety.sh`（全件の生出力。この作業場所の最上位を cwd にして回す）
4. `bash scripts/tests/test-disk-janitor.sh`（全件の生出力。同じく最上位で回す）
5. 見分ける力: 次をそれぞれ一時的に外して 3・4 を回し、落ちることを確かめてから戻す（生出力を残す。戻した後の `git diff` に外した跡が無いこと）
   - reaper の部屋ごとの `git_safe_link_ok` → G4・G5 が落ちる
   - janitor R2 の呼び出し → J3・J4 が落ちる
   - janitor R4 の呼び出し → J5 が落ちる
   - reaper :71 の後の確かめ → G7・G8・G9 が落ちる
6. 変更前（origin/main の写し。`scripts/` ごと用意する。git-safe.sh・ledger-lookup.sh が同じ置き場に要るため。reaper :35・:195）と変更後の reaper を、どちらも cwd=~/salesanchor の dry-run で動かす。両方の回で「=== reaper 結果 ===」が出ている（ロックで飛ばされていない）ことを確かめる。「消す」と「残す」に入る部屋の**顔ぶれ**の差が0件であること（新しい「合わない」に入る部屋が1つでもあれば止まって報告）。片付けも変更前後の dry-run（`DJ_LOG_FILE` は空）で、R2・R4 の「消す」と「残す」に入る場所の顔ぶれの差が0件であること。理由の文だけが変わった場所は、場所と前後の理由を一覧にして残す。時刻の差で変わる行があれば書き出す
7. `plutil -lint ops/launchd/jp.salesanchor.reaper-onlogin.plist` と `bash -n -c "$(plutil -extract ProgramArguments.2 raw -o - ops/launchd/jp.salesanchor.reaper-onlogin.plist)"`（命令の文の書き方の確かめ。動かしはしない。3回目の審査 L1）。作る係は3つ目の引数を動かさない（道具の写しを触らない）。3つ目の引数の `--execute` を `--dry-run` にした形を手で1回動かす確かめは、マージ後・入れ替えの前に設計者が行う（再審査 M2）
8. `git grep -n REAPER_WORKTREES_DIR -- ops scripts docs/ops .github ':!scripts/tests'` で、本番の起動設定・片付け・Actions がこの変数を使っていないこと（reaper の説明とテスト用の分岐以外0件）
9. `git grep -n 'scripts/reaper-worktree.sh' -- scripts ops .github` で、自動回収を呼ぶ所を全部書き出し、PR 本文の影響範囲に入れる（new-worktree.sh :65-68・:76・janitor R4・起動設定・Actions :47-56 と :62-65 の dry-run）
10. 3・4・5・6・7 の生出力を `docs/handoff/disk-janitor/evidence/` に、前の便のファイルを上書きしない名前 `link-check-<内容>.txt`（例 `link-check-test-reaper-safety.txt`・`link-check-dryrun-diff.txt`）で残す（審査 L8）
11. `node scripts/check-process-artifacts.js` を PR 前に回す（使い方は scripts/ の実物で確かめる）
12. 作業前の決まり: この作業場所（`release/discord-pdca-bin2b2-sa-link-card`）で `./scripts/dev/executor-preflight.sh` を通す。指示書の記録の上に1コミット（共著者行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`gh auth status` で shingo-cc を確かめて `gh pr create --base main`。PR 本文はテンプレートから作り、`### 標準ワークフロー確認` の節・触ったファイルの一覧・影響範囲（9 の一覧）・「危険パス（scripts/・ops/launchd/）を含むため GO が要る」・「マージすると Actions（reaper-schedule.yml）が新しい確かめ付きの reaper で `--execute` する（完了の確認6 がその関所）」・「Evaluator は画面のファイル変更 0 のため省く」・「手元の起動設定の入れ替えと道具の写しの取り直しはマージ後に設計者が行う」・「agent-console v0.46.3 はこの PR の後に入れる」を書く

## 想定分岐
- G4・G8・J3 の対照で印ができない → 作りを1回見直す（`info/attributes` の置き場・属性の付いたファイルが同じ長さで変わっているか）。それでも出なければ止まって報告（下調べと食い違うため）
- G8 で :66・:70 の `rev-parse` の段で印ができる → 止まって報告（確かめを `rev-parse` より前に動かす作りを設計で決め直す）
- 本番の走査の reaper を試験で動かせない（偽の gh・台帳・fetch の省略が足りない）→ 足りない物を書き出して止まって報告する。テスト用の走査に確かめを足して代わりにしない
- reaper の :71 の後の確かめで、既存の試験（cwd が元のリポジトリの最上位でない試験など）が落ちる → 確かめを緩めずに止まって、どの試験の cwd が何かを報告する
- 完了の確認6 で顔ぶれの差が出る（本物の部屋が「合わない」に入る・消す側から残す側へ移る場所がある）→ 止まって、その部屋の `.git`・`commondir`・`gitdir` の中身（パスだけ）を報告する
- 既存の試験が今の origin/main でも落ちる → 変更前の写しで同じ試験を回し、同じく落ちるなら PR 本文に書いて進む。変更後だけ落ちるなら止まって報告する
- `check-process-artifacts.js` や PR 起票の見張りに止められた → 言い換えずに止まって報告する

## 外部・過去事例の参照と我々への応用
- git 公式の説明（gitattributes の filter の節）: 設定に filter の定義が無ければ属性は何もしない。gitrepository-layout の commondir: "If this file exists, $GIT_COMMON_DIR … will be set to the path specified in this file"。git-worktree の説明: worktree の `.git` ファイルは `gitdir:` で `$GIT_COMMON_DIR/worktrees/<名>` を指し、その中の `commondir` が元の置き場を指す。この便は、その繋がりが元のリポジトリと一致することと、元のリポジトリに `commondir` が無いことを確かめ、偽の設定を読む道を塞ぐ
- 下調べと審査の実測（git 2.39.3）: worktree の `commondir`、または本店の `.git/commondir` を偽の置き場に向けると、上書き付きでも filter の命令が動いた（/tmp/CC報告ファイル/discord-pdca-bin2/53-exp-link/out.txt・/tmp/CC報告ファイル/discord-pdca-bin2/56-review79/review-out.txt）。ほかの事例の数は使わない

## 維持の仕組み
- 守り手: 自動回収・片付け・`scripts/git-safe.sh`・`scripts/new-worktree.sh`・起動設定を変える PR の設計者（Opus）。その PR で G4〜G9・J3〜J5 を手で回し、記録があるかを審査で確かめる
- 確かめの正本は `scripts/git-safe.sh` の `git_safe_main_ok`・`git_safe_link_ok` の1か所。作業場所・本店に向けた git を足すときはここを通す決まりを ADR-114 R12 に書く
- 試験は CI では走らないため、上の PR で手で回し、記録を `docs/handoff/disk-janitor/evidence/` に残す（既存の決まりのまま。CI に載せることは別の便の候補）
- 起動設定の手元とリポジトリのずれは、入れ替えの後に `diff` で0行を確かめる（設計者がマージ後に行う）

## 戻し方
- この PR を戻す PR を出してマージし、設計者が道具の写しを取り直し、ログイン時の起動設定を前の版で入れ直す（`bootout` の後に前の版を `bootstrap`）。agent-console v0.46.3 が入っていれば、先に `bash scripts/ac-update.sh v0.46.2` で戻す（道具の写しの台本に頼る側を先に外す）
