# 便2b-2 自動回収と片付けで「git の繋がり」を確かめ、自動回収を最新の道具の写しから動かす（Sales Anchor）作る係への指示書

- 設計: agent-console リポジトリ docs/handoff/discord-pdca/design.md 第14版（別リポジトリのためバッククォートなし） §4-5「filter の道と git の繋がりの確かめ」・§2 K17・§8 便2b-2・§15。ADR-1039（Accepted）。自動回収の正本 ADR-114。前の便のカード `docs/handoff/discord-pdca/bin2b0-sa-git-guard-card.md`
- 目的:
  1. 件の worktree の `.git` ファイル・`commondir`・`gitdir` が書き換えられ、git が偽の設定（filter の命令入り）を読む作業場所では、自動回収（`scripts/reaper-worktree.sh`）と片付け（`scripts/disk-janitor.sh`）がその作業場所に向けて git を動かさず、消さずに残す
  2. ログイン時と毎日 03:00 の自動回収を、古い本店の写し（`~/salesanchor`。origin/main より4600件以上古く、`scripts/git-safe.sh` が無い）ではなく、毎回 origin/main に取り直す道具の写し（`~/.salesanchor-tools`。04:00 の片付けと同じ）から動かす
- 調べた実物（origin/main c920a95。生出力 /tmp/CC報告ファイル/discord-pdca-bin2/54-recon-sa-link/、要約 summary.md）:
  - reaper: :35 で `scripts/git-safe.sh` を source（読めなければ終了コード 1）。:66-71 で cwd の `git rev-parse --git-common-dir` から `MAIN_REPO_ROOT` を決める。:106-135 はテスト用の走査（`REAPER_WORKTREES_DIR` 指定時。:131 `branch --show-current`）、:136-168 は本番の走査（`git -C MAIN_REPO_ROOT worktree list --porcelain`。最初の行＝元のリポジトリと detached は除く）。:178 からの部屋ごとの判定で作業場所に向けた git は :213・:224・:238・:245・:246。:358-360 が「使用中（削除しない）」の出し方
  - janitor: :24 で git-safe.sh を source。:33-36 で根（`DJ_ROOT_WORKTREES`=~/worktrees・`DJ_ROOT_AC_WT`=~/agent-console-wt・`DJ_ROOT_SALESANCHOR`=~/salesanchor・`DJ_ROOT_AGENT_CONSOLE`=~/agent-console）。:55-58 `DJ_REPOS`（agent-console・ebay-gas-automation・crm-app 2つ。salesanchor は入っていない）。R2 :306-338 は2つの根の下の `.git` ファイルを find で拾い、:290 `dj_wt_unused` の :298 `log -1` を動かす。どの元のリポジトリの worktree かは見ていない。R4 :388-420 は `DJ_REPOS` の各リポジトリで :397 `remote get-url` の後に reaper を呼ぶ。:139 `dj_skip <path> <理由>` が「残す」の出し方
  - 試験: `scripts/tests/test-reaper-safety.sh`（G1 :727-764 など。reaper はテスト用の走査で動かしている）・`scripts/tests/test-disk-janitor.sh`（`check "説明" コマンド` の形。:45-46 で根を一時フォルダに向け、:68-76 で作り物の元のリポジトリ `gitmain` と `git worktree add` の worktree を作る。J1/J2 :352-366）。**どちらも CI では走らない**（.github に参照0件）。手で回して記録を `docs/handoff/disk-janitor/evidence/` に残す決まり（#4758 も同じ）
  - 起動設定: 手元の `~/Library/LaunchAgents/jp.salesanchor.reaper-onlogin.plist` は WorkingDirectory=~/salesanchor で `bash scripts/reaper-worktree.sh --execute`、RunAtLoad=true、毎日 03:00。リポジトリの `ops/launchd/jp.salesanchor.reaper-onlogin.plist` には 03:00 の指定が無い（手元とずれている。62-plist-diff.txt）。片付けの plist（04:00・RunAtLoad=false）は手元とリポジトリが同じで、道具の写しの取り直しと確かめの後で動かす作り（31-plist-janitor-repo.txt :34）
  - 手順の正本: `docs/ops/runner-commands.md:202-228`（reaper は `launchctl load`、片付けは `bootstrap`）
  - 危険パス: `scripts/` と `ops/launchd/` はどちらも危険パス（`scripts/check-process-artifacts.js:115-125`）。マージには GO が要る
  - 手元の `realpath` は `/bin/realpath`

## 決めたこと
- `scripts/git-safe.sh` に関数 `git_safe_link_ok <作業場所> <元のリポジトリの最上位>` を足す（source 時は定義だけで何も実行しない、は今のまま）。合えば 0、合わなければ `GIT_SAFE_LINK_REASON` に理由の短い日本語を入れて 1 を返す。実パスは `realpath` で取り、`realpath` が無い・失敗したら 1（残す側）。P=作業場所、C=`realpath <元>/.git`:
  1. `<元>/.git` が本物のディレクトリ（`[ -d ] && [ ! -L ]`）
  2. P の実パスが `<元>` の実パスと同じなら、`P/.git` が本物のディレクトリで実パスが C なら 0
  3. それ以外は worktree として: `P/.git` が本物のファイル（`[ -f ] && [ ! -L ]`）、1行だけで `gitdir: <G>` の形。G が相対なら P を起点。`dirname "$(realpath G)"` が `C/worktrees`
  4. `G/commondir` の中身（相対なら G の実パスを起点）の実パスが C
  5. `G/gitdir` の中身（相対なら G の実パスを起点）の実パスが `P/.git` の実パス
  6. `G/config` と `G/config.worktree` が無い
  - 末尾の改行は除く。P の末尾の `/` は除いてから比べる
- reaper:
  - :71 の後で `git_safe_link_ok "${MAIN_REPO_ROOT}" "${MAIN_REPO_ROOT}"` を確かめ、合わなければ「元のリポジトリの git の繋がりを確かめられない。何も消さない」と出して終了コード 1
  - 本番の走査のとき（`REAPER_WORKTREES_DIR` が空のとき）だけ、:178 の部屋ごとの判定の最初（チェック 0 の前）で `git_safe_link_ok "${WORKTREE_PATH}" "${MAIN_REPO_ROOT}"` を確かめる。合わなければ新しい入れ物 `SKIP_LINK` に「ブランチ名（理由）」を入れて `continue`（その部屋には git を1回も動かさず、消さない）。出力は :358-360 の書き方に合わせて「🔗 git の繋がりが本店と合わない（削除しない）: N 件」
  - テスト用の走査（:106-135）には足さない（作り物の部屋は worktree ではないため。本番の起動設定・片付けの R4 がこの変数を使っていないことを完了の確認8で確かめる）
- janitor:
  - 設定に `DJ_LINK_MAINS`（改行区切りの元のリポジトリの最上位。既定は `DJ_ROOT_SALESANCHOR` と `DJ_ROOT_AGENT_CONSOLE` の2行）を足す（:30-60 の1か所）
  - R2: :337 で拾った各 `wt` について、`cands` を集めた後・`dj_wt_unused` の前で、`DJ_LINK_MAINS` のどれか1つと `git_safe_link_ok "${wt}" <元>` が合うかを見る。どれとも合わなければ各候補を `dj_skip "<候補>" "git の繋がりが元のリポジトリと合わない（残す）: <理由>"` にして次へ
  - R4: :397 の `remote get-url` の前で `git_safe_link_ok "${path}" "${path}"`。合わなければ `dj_skip "${path}" "git の繋がりを確かめられない（残す）: <理由>"` で次へ
- 起動設定（`ops/launchd/jp.salesanchor.reaper-onlogin.plist`）:
  - ProgramArguments の3つ目を、片付けの plist :34 と同じ取り直しと確かめの後に `cd /Users/tanizawashingo/salesanchor && bash "$T/scripts/reaper-worktree.sh" --execute` を動かす1行にする（失敗時は「reaper: 道具のコピーの更新・確認に失敗したため実行しない」を標準エラーに出して終了コード 1）。cwd を本店にするので、`MAIN_REPO_ROOT` は今と同じ本店のまま
  - 毎日 03:00 の `StartCalendarInterval` を足す（手元の実物に合わせる）。RunAtLoad=true・KeepAlive=false・ログの置き場は今のまま
  - 冒頭の説明の配置コマンドを `launchctl bootstrap gui/$(id -u) …`・停止を `launchctl bootout gui/$(id -u)/jp.salesanchor.reaper-onlogin` にし、「古い本店の写しで動かさない理由（ADR-1039 便2b-2）」を1行足す
  - `docs/ops/runner-commands.md:202-228` の reaper の手順を同じ書き方に直す
  - 道具の写しの取り直しが片付け（04:00）と重なった場合は、片方の git が失敗して「実行しない」側に倒れる（消す側に倒れない）。これは今の片付けと同じ扱いで、足す仕組みは無い
- 正本の文書: `docs/adr/ADR-114-worktree-auto-cleanup.md` の R の一覧の R11 の後に「R12: 作業場所に向けた git の前に `git_safe_link_ok` で git の繋がりを確かめ、合わない部屋は消さない。ログイン時・03:00 の自動回収は最新の道具の写しから動かす（ADR-1039 便2b-2）」と、履歴の行を今の書き方に合わせて足す。`node scripts/generate-adr-index.js` を実行して `docs/adr/README.md` を作り直す

## 守ること
- 下に書いた変更だけ。ほかの判定・文・既存の試験の期待は変えない
- 試験の作り物は `mktemp -d` の下に作り、既存の片付けの作りに合わせる。新しい消し方を足さない
- 本物の部屋に向けて `--execute` を動かさない。確かめは dry-run だけ
- 手元の `~/Library/LaunchAgents/` の入れ替えは、マージと GO の後に設計者（Opus）が行う。作る係はしない

## 変更
1. `scripts/git-safe.sh`: `git_safe_link_ok`
2. `scripts/reaper-worktree.sh`: 元のリポジトリの確かめ・本番の走査の部屋ごとの確かめ・`SKIP_LINK` の出力
3. `scripts/disk-janitor.sh`: `DJ_LINK_MAINS`・R2・R4
4. `scripts/tests/test-reaper-safety.sh` に足す:
   - G4 偽の置き場（commondir）: 作り物の元のリポジトリ（`git init`・1回 commit・`git init --bare` の偽の remote に push）と `git worktree add` の worktree を作る。偽の置き場＝元の `.git` を写して `worktrees` を除き、`config` に `[filter "evil"]`・`clean = touch <印>; cat`、`info/attributes` に `*.txt filter=evil`。worktree の `commondir` を偽の置き場に向け、`f.txt` を変える
     - 対照: その worktree で `git -c core.fsmonitor=false -c core.hooksPath=/dev/null status --porcelain` を動かして**印ができる**こと（できなければ FAIL）。印を消す
     - reaper を**本番の走査**で dry-run（cwd=作り物の元のリポジトリ、`REAPER_WORKTREES_DIR` を空、`REAPER_SKIP_FETCH=1`、既存の偽の gh と台帳の作りを使う）して、印ができず、出力の「git の繋がりが本店と合わない」にその部屋が入り、削除候補に入らないこと
   - G5 偽の gitdir: 同じく worktree の `.git` ファイルを偽の gitdir に向ける。印ができず、「合わない」に入ること（対照は取らない）
   - G6 正しい worktree: 同じ作り物の正しい worktree が「合わない」に入らず、今の判定どおり（DONE＋未保存なしなら削除候補）になること
   - G7 元のリポジトリの `.git` をシンボリックリンクにした作り物で、終了コード 1・何も消さないこと
5. `scripts/tests/test-disk-janitor.sh` に足す（既存の `gitmain` を使う。`DJ_LINK_MAINS` に `gitmain` を入れる）:
   - J3: R2 の対象になる worktree（`mk_nm`・古い更新日時）の `commondir` を、G4 と同じ偽の置き場に向ける。対照として上書き付きの `git log -1` で印ができること、dry-run で印ができず、その node_modules が「残す」に入り理由が出ること
   - J4: `DJ_LINK_MAINS` に無い元のリポジトリの worktree の node_modules が「残す」に入ること
   - 既存の R2 の試験（`WT_DEL` など）の期待が今のままで通ること
6. `ops/launchd/jp.salesanchor.reaper-onlogin.plist`・`docs/ops/runner-commands.md`: 上の「決めたこと」
7. ADR-114 と `docs/adr/README.md`
8. この指示書は設計者がこのブランチに先に記録済み。作る係は書き換えない

## 完了の確認（生出力を /tmp/CC報告ファイル/discord-pdca-bin2/57-impl2b2-sa/ に保存）
1. `bash -n scripts/git-safe.sh scripts/reaper-worktree.sh scripts/disk-janitor.sh`
2. `shellcheck`（手元にあれば。無ければ「無い」と記録）
3. `bash scripts/tests/test-reaper-safety.sh`（全件の生出力）
4. `bash scripts/tests/test-disk-janitor.sh`（全件の生出力）
5. 見分ける力: `git_safe_link_ok` の呼び出しを一時的に外して 3・4 を回し、G4・G5・J3 が落ちることを確かめてから戻す（生出力を残す。戻した後の `git diff` に外した跡が無いこと）
6. 変更前（origin/main の写し）と変更後の reaper を、どちらも cwd=~/salesanchor の dry-run で動かし、「消す」「残す」の一覧の差が0件であること（新しい「合わない」に入る部屋が1つでもあれば止まって報告）。片付けも変更前後の dry-run（`DJ_LOG_FILE` は空）で、R2・R4 の候補と残すの差が0件であること。時刻の差で変わる行があれば書き出す
7. `plutil -lint ops/launchd/jp.salesanchor.reaper-onlogin.plist`。その3つ目の引数を、`--execute` を `--dry-run`（reaper の dry-run の引数を実物で確かめる）に置き換えて1回だけ手で動かし、道具の写しの取り直しと dry-run が通ること（`~/.salesanchor-tools` が汚れていない・HEAD が origin/main になったこと）
8. `git grep -n REAPER_WORKTREES_DIR -- ops scripts docs/ops ':!scripts/tests'` で、本番の起動設定・片付けがこの変数を使っていないこと（reaper の説明とテスト用の分岐以外0件）
9. 3・4・5・6 の生出力を `docs/handoff/disk-janitor/evidence/` の既存の書き方に合わせて残す
10. `node scripts/check-process-artifacts.js` を PR 前に回す（使い方は scripts/ の実物で確かめる）
11. 作業前の決まり: この作業場所（`release/discord-pdca-bin2b2-sa-link-card`）で `./scripts/dev/executor-preflight.sh` を通す。指示書の記録の上に1コミット（共著者行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`gh auth status` で shingo-cc を確かめて `gh pr create --base main`。PR 本文はテンプレートから作り、`### 標準ワークフロー確認` の節・触ったファイルの一覧・「危険パス（scripts/・ops/launchd/）を含むため GO が要る」・「Evaluator は画面のファイル変更 0 のため省く」・「手元の起動設定の入れ替えはマージ後に設計者が行う」を書く

## 想定分岐
- G4・J3 の対照で印ができない → 作りを1回見直す（`info/attributes` の置き場・属性の付いたファイルが変わっているか）。それでも出なければ止まって報告（下調べと食い違うため）
- 本番の走査の reaper を試験で動かせない（偽の gh・台帳・fetch の省略が足りない）→ 足りない物を書き出して止まって報告する。テスト用の走査に確かめを足して代わりにしない
- 完了の確認6 で差が出る（本物の部屋が「合わない」に入る）→ 止まって、その部屋の `.git`・`commondir`・`gitdir` の中身（パスだけ）を報告する
- `~/worktrees` の下に salesanchor でも agent-console でもない元のリポジトリの worktree がある → 止まって報告する（`DJ_LINK_MAINS` の既定を決め直す）
- 既存の試験が今の origin/main でも落ちる → 変更前の写しで同じ試験を回し、同じく落ちるなら PR 本文に書いて進む。変更後だけ落ちるなら止まって報告する
- `check-process-artifacts.js` や PR 起票の見張りに止められた → 言い換えずに止まって報告する

## 外部・過去事例の参照と我々への応用
- git 公式の説明（gitattributes の filter の節）: 設定に filter の定義が無ければ属性は何もしない。git-worktree の説明: worktree の `.git` ファイルは `gitdir:` で `$GIT_COMMON_DIR/worktrees/<名>` を指し、その中の `commondir` が元の置き場を指す。この便は、その繋がりが元のリポジトリと一致することを確かめ、偽の設定を読む道を塞ぐ
- 下調べの実測（git 2.39.3）: `commondir` を偽の置き場に向けると、上書き付きでも filter の命令が動いた（/tmp/CC報告ファイル/discord-pdca-bin2/53-exp-link/out.txt）。ほかの事例の数は使わない

## 維持の仕組み
- 守り手: 自動回収と片付けを変える PR の設計者（Opus）。PR の審査で G4〜G7・J3・J4 の記録があるかを確かめる
- 確かめの正本は `scripts/git-safe.sh` の `git_safe_link_ok` の1か所。作業場所に向けた git を足すときはここを通す決まりを ADR-114 R12 に書く
- 試験は CI では走らないため、自動回収か片付けを変える PR で手で回し、記録を `docs/handoff/disk-janitor/evidence/` に残す（既存の決まりのまま）
- 起動設定の手元とリポジトリのずれは、入れ替えの後に `diff` で0行を確かめる（設計者がマージ後に行う）
