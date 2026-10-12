# 開発データの自動片付け 設計（2026-10-13・草案 v1）

PO 原文（2026-10-13）:「他に不要なものも調査して溜まっていく現状を解消するための自動削除機能も実装する」、離席時「このセッションだけで最後まで完結させる…PRマージ、デプロイまで完走」、続けて「再開してくれ」。

根拠: /tmp/CC報告ファイル/disk-cleanup/phase2/summary.md（不要物の全容）、phase3/（reaper.txt・ac.txt・npm*.txt・node-modules.tsv・danger-paths.txt・shell-ci.txt・doc-scratchpad.txt）、exec/（段1の実行記録）。

## 1. 目的と成功条件
- 開発作業で増える「消しても作り直せる物」と「GitHub に同じ内容がある物」が、人の手なしで毎日片付き、たまり続けない。
- 判定（○×）:
  1. `npm config get cache` を ~・salesanchor・任意の worktree の3か所で実行すると、3つとも `/Users/tanizawashingo/.npm-shared-cache` を返す。
  2. 片付けの仕組みが毎日1回動き、ログ ~/Library/Logs/disk-janitor.log に、規則ごとの件数・容量・前後の df が残る。
  3. 初回実行の後、規則の対象（下の R1〜R4 で「消す」に当たる物）が0件になる（2回目の dry-run で候補0件）。
  4. 消してはいけない物（各規則の「保護」）は1件も消えていない（初回の実行前一覧と実行後一覧の照合）。

## 2. 原因と対処の対応（事実）
| たまる物 | 量（10/13） | 原因（事実） | 対処 |
|---|---|---|---|
| .npm-cache（43か所） | 7.7GB | ~/.npmrc `cache=./.npm-cache` が実行場所の相対パスとして解決される（phase3/npm.txt の実測: /tmp→/private/tmp/.npm-cache、~→~/.npm-cache、agent-console→agent-console/.npm-cache） | D1: 絶対パスに直す。R1: 残った散らばりを消す |
| 作業用コピーの node_modules | 9件 3.6GB | npm ci で作られ、作業用コピーが残る限り残る | R2: しばらく使っていない作業用コピーの node_modules を消す（package-lock.json から npm ci で作り直せる） |
| agent-console の旧版 | 17版 5.2GB（current v0.9.1） | ac_install_version が versions/<tag> に版を足すだけで、古い版を消す処理が無い（ac.txt、README:93） | R3: current と、その1つ前（ac-rollback.sh の切り戻し先）以外を消す |
| salesanchor 以外の作業用コピー | 段1 で 53件 9.6GB を手で回収 | reaper-worktree.sh は salesanchor だけを走査し、PR の行き先を main に固定している（reaper.txt:65,:282,:297,:235） | R4: reaper を他のリポジトリにも使えるようにし、同じ安全条件で回収する |

対処しない物（理由）:
- Claude Code の一時ファイル（/private/tmp/claude-501）と会話記録（~/.claude/projects）: 公式の保持期間（cleanupPeriodDays 既定30日）で、会話記録と一緒に消える（doc-scratchpad.txt 原文、doc-claude-directory.md:1534）。
- /tmp の報告ファイル: macOS の tmp_cleaner が毎日、3日触られていないファイルを消す（phase2 summary 項目6）。
- 旧 /Users/tanizawashingo/.npm-cache（1.1GB・HOME 直下で根の外）: root 所有のファイル18個があり、消すには sudo が要る。自動では触らない（PO に別途渡す）。
- Codex の会話記録 4.5GB、colima の停止中ディスク、Chrome の履歴、macOS Install Data: PO 個人のデータ・判断。自動では消さない（PO に別途 y/n）。
- git として読めない作業用コピー 113件: 中身が GitHub と一致するか判定できない物が大半（phase2 G-crm.tsv）。自動では消さない。

## 3. 変更（一度に1つ。D1 → 測定 → D2 → 測定）

### D1 npm キャッシュを1か所に（ローカル設定・リポジトリ外）
- ~/.npmrc の `cache=./.npm-cache` を `cache=/Users/tanizawashingo/.npm-shared-cache` に変える（1行）。`prefix=` の行は変えない。
- 前例: crm-app は 2026-08-25 b187243 で `cache=${HOME}/.npm-shared-cache` に変え、worktree 間でキャッシュを共有している（npm-crm.txt）。
- 測定: 判定1。変更前の値を記録してから変える。
- 戻し方: 1行を元に戻す（控えを ~/.npmrc.bak-20261013 に置く）。

### D2 毎日の片付け（salesanchor リポジトリ・PR）
新規 `scripts/disk-janitor.sh`、新規 `ops/launchd/jp.salesanchor.disk-janitor.plist`、`scripts/reaper-worktree.sh` に1つの環境変数を追加、試験 `scripts/tests/test-disk-janitor.sh`。

共通の作り:
- 既定は dry-run（候補と容量の一覧だけ）。`--execute` で実際に消す。
- 多重起動の防止は reaper と同じ mkdir ロック（/tmp/disk-janitor.lock.d、trap EXIT INT TERM。memory feedback_macos_lock_mechanism）。
- 消す場所は、下の「根」の下だけ。消す直前に、絶対パスであること、根の下であること、シンボリックリンクでないこと、名前が規則の名前と一致することを確かめ、1つでも違えばその件は消さない。
  - 根: /Users/tanizawashingo/worktrees、/Users/tanizawashingo/agent-console-wt、/Users/tanizawashingo/salesanchor、/Users/tanizawashingo/agent-console、/Users/tanizawashingo/Library/Application Support/agent-console/versions
- 根・閾値・対象リポジトリは、スクリプト冒頭の設定ブロック1か所にまとめ、上書き用の環境変数を持たせる（試験で一時ディレクトリに差し替えるため）。
- ログは標準出力。LaunchAgent が ~/Library/Logs/disk-janitor.log と .err に受ける。最初と最後に `date` と `df -h /System/Volumes/Data` を出す。規則ごとに「消した／飛ばした（理由）」の件数と容量を出す。

R1 散らばった .npm-cache
- 対象: 根の下の、名前が `.npm-cache` のディレクトリ。深さ4まで（`find -P <根> -maxdepth 4 -type d -name .npm-cache -prune`）。
- 保護: D1 の設定先 /Users/tanizawashingo/.npm-shared-cache（実行時に `npm config get cache` で得た値と同じパスは消さない）。npm のプロセス（`pgrep -x npm` が1件以上）が動いている時は R1 全体を飛ばす。
- 前提: D1 の後でのみ有効にする（`npm config get cache` が根の下の相対の場所を返すなら R1 全体を飛ばして警告）。

R2 使っていない作業用コピーの node_modules
- 対象: 根のうち worktrees と agent-console-wt の下で、`.git` がファイルである（git の作業用コピーである）ディレクトリ。その直下と frontend/ 直下の node_modules。
- 消す条件（すべて）: 同じ場所に package-lock.json がある。作業用コピーの中の、node_modules・.npm-cache・dist を除くファイルの最新の更新が14日より前。そのディレクトリを作業中の場所にしているプロセスが無い（reaper と同じ lsof の判定）。
- 保護: 本体（salesanchor・agent-console 本体）は対象外。

R3 agent-console の旧版
- 対象: versions/ の下の版ディレクトリ（名前が `v<数>.<数>.<数>`）。
- 残す: current のシンボリックリンクが指す版、その版の1つ前（semver 順。ac-rollback.sh:16-29 の切り戻し先）、いずれかのプロセスが開いている版（`lsof +D` は遅いので `lsof -c node` 等で versions/<tag> を含むパスを持つプロセス）。
- current が読めない、または指し先が無い時は R3 全体を飛ばす。

R4 salesanchor 以外の作業用コピー（reaper を使う）
- reaper-worktree.sh に `REAPER_BASE_BRANCH`（既定 main）を足し、PR の行き先の判定（reaper.txt:235,:282,:297 の `"main"`）をこの値にする。既定は main なので、salesanchor の動きは変わらない。
- disk-janitor.sh は、設定ブロックの対象リポジトリごとに、そのリポジトリを作業場所にして `REAPER_REPO_NAME=<origin の owner/repo> REAPER_BASE_BRANCH=<行き先> REAPER_ACTIVE_WORK_FILE=/dev/null bash <salesanchor>/scripts/reaper-worktree.sh --execute` を呼ぶ。owner/repo は `git remote get-url origin` から取り、取れなければそのリポジトリを飛ばす。
- 対象リポジトリと行き先（事実: 段1 の審査で確認した PR の baseRefName）: /Users/tanizawashingo/agent-console → main、/Users/tanizawashingo/ebay-gas-automation → develop、/Users/tanizawashingo/crm-app-current → develop、/Users/tanizawashingo/crm-app-canonical-20260830 → develop。
- 安全条件は reaper のまま（未コミット0、全コミットが origin から到達可能、PR がマージ済みか閉じ、使用中でない、fetch 失敗なら0件）。

LaunchAgent
- ops/launchd/jp.salesanchor.disk-janitor.plist: 毎日 04:00（reaper の 03:00 の後）、RunAtLoad=false、KeepAlive=false、WorkingDirectory=/Users/tanizawashingo/salesanchor、ProgramArguments は `bash -lc "bash scripts/disk-janitor.sh --execute"`、ログは上記。
- 設置はマージ後に、docs/ops/runner-commands.md:204-217 と同じ手順（cp と launchctl）で行い、`launchctl list | grep disk-janitor` で確認する。

## 4. 受入と検証
| 基準 | 検証方法 |
|---|---|
| D1 | 変更前後で、~・/Users/tanizawashingo/salesanchor・残っている worktree 1つで `npm config get cache` の出力を記録。後は3つとも /Users/tanizawashingo/.npm-shared-cache |
| 試験 | scripts/tests/test-disk-janitor.sh を一時ディレクトリで実行し、R1〜R4 それぞれの「消す」「保護」の場合がすべて期待どおり（消すべき物が消え、保護が残る）。reaper の既存試験 scripts/tests/test-reaper-safety.sh が変更後も全件成功 |
| dry-run | マージ前に、実機で `bash scripts/disk-janitor.sh`（dry-run）の全出力を保存。候補一覧を設計者が見て、保護に当たる物が候補に入っていないことを確認 |
| 初回実行 | 設置後に1回 `--execute` を手で実行し、前後の df・規則ごとの件数と容量を記録。直後の dry-run で候補0件 |
| 保護 | 実行前に、保護に当たる物（D1 の設定先、本体、current と1つ前の版、使用中の作業用コピー、未保存のある作業用コピー）の一覧を取り、実行後にすべて残っていることを確認 |
| 毎日動く | 翌日以降、~/Library/Logs/disk-janitor.log に日付の新しい実行の記録がある（PO または次のセッションで確認） |
| 品質 | `bash -n` 両スクリプト、shellcheck（入っていれば）、CI 必須がすべて成功 |

## 5. 安全と戻し方
- 消す物は、作り直せる物（.npm-cache・node_modules・agent-console の版はタグからビルド可能 ac.txt）か、GitHub に同じ内容がある物（R4）だけ。
- 戻し方: LaunchAgent を `launchctl bootout` で止め、PR を revert。D1 は控えから戻す。消した物は、npm ci・ac-install・`git worktree add` で作り直す。
- 本番（サーバー・DB）には触れない。scripts/ は関所の危険パスだが、GO 委任の例外（DROP・secrets・ruleset 等）には当たらない。

## 6. 外部事例
不要。仕組みは既存の reaper と LaunchAgent（ADR-114、memory feedback_launchd_oneshot_pattern）の前例をそのまま使う。npm キャッシュの共有は crm-app の前例（b187243）。

## 7. 維持の仕組み
- 守り手: scripts/tests/test-disk-janitor.sh、scripts/tests/test-reaper-safety.sh、ログ ~/Library/Logs/disk-janitor.log。
- 守っていないもの: CI はシェルの試験を実行しない（shell-ci.txt の事実）。試験は変更時に手で実行して記録する。

## 改訂 1（2026-10-13、Fable 設計審査 REVISE への対応。本節が上の記述より優先）
- F1（HIGH・R1 の使用中判定）: `pgrep -x npm` は使わない。実行の最初に `lsof -nP -F pn 2>/dev/null` を1回取り、候補ごとに「その .npm-cache の配下のパスを開いている・実行しているプロセス」が1件でもあれば、その候補を飛ばして理由を記録する（cwd・txt・fd を含む。今動いている MCP の npx 実体と _logs 書き込みを守る）。lsof が失敗したら R1 全体を飛ばす。
- F2（R4 台帳）: disk-janitor.sh は reaper を呼ぶとき `REAPER_ACTIVE_WORK_FILE=/dev/null` に加えて `ACTIVE_WORK_DIR=/nonexistent-disk-janitor` も渡す（ledger-lookup.sh:10-13 が先に読む台帳ディレクトリを無効にする）。
- F3（ADR）: ADR-114 に「REAPER_BASE_BRANCH（既定 main）で PR の行き先を変えられる。他リポジトリは disk-janitor から行き先を指定して呼ぶ」を追記し、`node scripts/generate-adr-index.js` を実行して README の差分をコミットに含める。
- F4（R4 本体ブランチの保護）: reaper に、worktree のブランチ名が main・develop・REAPER_BASE_BRANCH のいずれかと同じなら候補にしない保護を足す（salesanchor でも同じ。既存の動きは変わらない: 今の salesanchor の worktree に main/develop のものは無いことを実装時に確認して記録）。
- F5（R2 の判定方法）: 「使っていない」は次の2つがともに14日より前であること。(a) `find <wt> \( -name node_modules -o -name .npm-cache -o -name dist -o -name .sa-cache -o -name coverage -o -name storybook-static -o -name test-results -o -name playwright-report -o -name .git \) -prune -o -type f -newermt "<14日前>" -print -quit` が何も返さない（mtime で判定）。(b) `git -C <wt> log -1 --format=%ct` が14日より前。戻し方に「salesanchor は `npm ci --prefix frontend`、agent-console は `npm ci`（pre-commit の lint-staged が node_modules を使うため）」を書く。
- F6（自動で消すことの許可）: 毎日無人で消す（rm -rf を含む）ことは CLAUDE.md:38 の PO 確認の対象に当たるため、PO に y/n を1回だけ取り、答えを GO 記録に転記する。y の範囲は「根5か所の中で、R1〜R4 の条件に当たる物だけ」。
- F7（受入の追加）: 設置後に `launchctl print gui/$(id -u)/jp.salesanchor.disk-janitor` の出力（state・runs・last exit code）を記録し、`launchctl kickstart -k gui/$(id -u)/jp.salesanchor.disk-janitor` で1回すぐに動かしてログを確認する。plist はリポジトリの版に StartCalendarInterval（毎日 04:00）を必ず入れ、設置した物と `diff` して差が無いことを記録する（reaper の plist はリポジトリ版に日時が無い前例があるため）。ログの肥大化: 1回の出力は規則ごとの件数・容量と、消した物の先頭20件まで。ログが 1MB を超えたら disk-janitor.log.1 に移してから書く（1世代だけ）。
- F8（R4 の事実）: 対象と行き先は次で確定（origin の実測と、マージ済み PR 直近50件の base の分布）。/Users/tanizawashingo/agent-console → GEN-RYU-System/agent-console・main、/Users/tanizawashingo/ebay-gas-automation → GEN-RYU-System/bay-auto・develop、/Users/tanizawashingo/crm-app-current と /Users/tanizawashingo/crm-app-canonical-20260830 → GEN-RYU-System/crm-app・develop。owner/repo は実行時に origin から求め、上の値と違えばそのリポジトリを飛ばす。reaper は MAIN_REPO_ROOT を作業場所から決めるため、`( cd <repo> && <env> bash <salesanchor>/scripts/reaper-worktree.sh --execute )` のように別のシェルで呼ぶ。
- F9（R3）: current はシンボリックリンクの指し先の basename で比べる。現状は current=v0.9.1、1つ前=v0.7.0（ac-rollback.sh:16-20 と同じ決め方）。current より新しい版が versions/ にあれば、それも残す。
- F10（D1）: 値は `cache=/Users/tanizawashingo/.npm-shared-cache`。判定1は、各ディレクトリへ移動してから `npm config get cache` を実行する（`--prefix` では作業場所が変わらないため）。
- F11（範囲の実測）: R1 の候補は 57件（salesanchor 本体の .npm-cache・backend・frontend・lp を含む。本体の未コミットのファイルは名前が違うので対象外）。R2 は本体を対象外のまま。~/worktrees/crm-app/* の frontend/node_modules 2件は R2 の対象に入る（.git がファイルの作業用コピーのとき）。

## 審査と PO の決定
- Fable 設計審査: 1回目 REVISE（HIGH 1・MEDIUM 6）→ 改訂1 → 2回目 APPROVE（2026-10-13、architect-review-v1-rev1.yaml）。残った LOW: L1 (b) の git log が失敗したら KEEP。L2 (a) は checkout 時刻のファイルに当たるため、実質「作成から14日」が下限（意図どおり）。
- PO の決定（2026-10-13、F6 の y/n）: 「y」。質問文は「毎日朝4時に、人の手を通さずに自動で消してよいですか？ 消すのは、決めた5つの場所の中で、作り直せるものか GitHub に同じ内容があるものだけです」。範囲は根5か所の中で R1〜R4 の条件に当たる物だけ。

---

## 改訂 2（2026-10-13、設計者決定。上の記述より優先）
- npm の置き場は crm-app と同じ `/Users/tanizawashingo/.npm-shared-cache` に1本化する（旧 `.npm-cache` は root 所有のファイル18個で別担当の `npm ci` が EACCES）。`~/.npmrc` は `cache=/Users/tanizawashingo/.npm-shared-cache`。R1 の保護先（`DJ_NPM_CACHE_KEEP` 既定）も同じ。上の本文・F10 の `.npm-cache` の絶対パスは、この値に読み替える（本ファイル内の絶対パスは置換済み）。
- R1 の D1 確認は、`/` と HOME の2か所で `npm config get cache` を実行し、2つとも保護先と完全一致したときだけ行う（1つでも違えば R1 全体を飛ばして警告）。

## 実装での確定事項（実装担当・2026-10-13）
- 実装物: `scripts/disk-janitor.sh`（R1〜R4・dj_guard 1関数・設定は dj_config 1か所・`DJ_` 環境変数で上書き）、`scripts/reaper-worktree.sh`（`REAPER_BASE_BRANCH`・本体ブランチ保護）、`ops/launchd/jp.salesanchor.disk-janitor.plist`、`scripts/tests/test-disk-janitor.sh`、`scripts/tests/test-reaper-safety.sh`（B-a〜B-d 追加）。
- 一覧の出力上限: 実削除は先頭20件（ログ肥大化防止・F7）、dry-run は全件（`DJ_LIST_MAX` で上書き可）。
- ログ: `DJ_LOG_FILE` が指定されたら、スクリプト自身が 1MB 超で `.log.1` に退避してから追記する（plist が環境変数で指定）。launchd が掴む出力先は退避後に古い実体を指すため、スクリプトが自分で開き直す。
- PATH: plist の `EnvironmentVariables` に `~/.npm-global/bin` などを入れる（`npm config get cache` を R1 が実行時に確認するため）。
- 使用中の判定は reaper の cwd 判定より広く、`lsof -nP -F pn` に当該パス配下を開いているものが1件でもあれば使用中（R1〜R3 共通）。lsof 失敗・0行なら R1〜R3 を飛ばす。
- 実機 dry-run の結果は `docs/handoff/disk-janitor/evidence/` に保存（recon.md 参照）。

## 維持の仕組み
- 守り手: `scripts/tests/test-disk-janitor.sh`（R1〜R4 の「消す」「保護」・dry-run・ガード）、`scripts/tests/test-reaper-safety.sh`（`REAPER_BASE_BRANCH`・本体ブランチ保護を含む）、ログ `~/Library/Logs/disk-janitor.log`（1MB・1世代）。
- 変更のたびの手順: 関連スクリプトを変更したら両試験を手で実行し、生出力を `docs/handoff/disk-janitor/evidence/` に残す（CI はシェルの試験を実行しない: phase3/shell-ci.txt）。
- 毎日動くことの確認: 翌日以降、ログに新しい日付の「disk-janitor 開始」があること。止まったら `launchctl print gui/$(id -u)/jp.salesanchor.disk-janitor` の last exit code を見る。
- 範囲を広げるとき: 根の追加・規則の追加は ADR-114 の改訂＋PO の y/n（F6 の y は「根5か所の中で R1〜R4 の条件に当たる物だけ」）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要と判断（本文 §6）。理由: 既存の reaper（ADR-114）と LaunchAgent の前例をそのまま使う。
- 過去事例: crm-app は 2026-08-25 b187243 で `cache=${HOME}/.npm-shared-cache` に変え worktree 間でキャッシュを共有している（phase3/npm-crm.txt）。→ 応用: D1 で salesanchor 側も絶対パス1か所にそろえ、散らばりは R1 で片付ける。
- 過去事例: reaper の launchd 起動（ADR-114 PR-C・`ops/launchd/jp.salesanchor.reaper-onlogin.plist`）と一撃実行パターン（memory feedback_launchd_oneshot_pattern）。→ 応用: 同じ plist 形式で毎日 04:00 の日次実行にする。

## 関係する ADR
- ADR-114（docs/adr/ADR-114-worktree-auto-cleanup.md）: reaper の安全条件。本件で `REAPER_BASE_BRANCH` と本体ブランチ保護を追記（R10）。R4 は reaper の安全条件のまま。
- ADR-135（docs/adr/ADR-135-release-stowaway-prevention.md）: `scripts/` を含む実装は PO GO が出るまでマージしない。本 PR は危険パス（scripts/）を含むため GO 待ち。
- ADR-136（docs/adr/ADR-136-cc-bot-github-identity.md）: PR 作成は shingo-cc 名義。危険 PR の GO 手順（CLAUDE.md の ADR-136 項）に従う。
- ADR-1003（docs/adr/ADR-1003-go-delegation-to-opus.md）: GO 発行の委譲。ただし「毎日無人で消す」許可は PO の y/n（2026-10-13「y」）を GO 記録に転記する。
- CLAUDE.md:36 の「不可逆操作は必ず PO 確認」: 本件の rm -rf は PO の y（範囲: 根5か所の中で R1〜R4 の条件に当たる物だけ）で許可済み。
