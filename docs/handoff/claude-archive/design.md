# 残すデータを毎日 HDD へ写し、写した物と消す分を Mac から片付ける 設計（第3.1版）

状態: 設計案（Opus 作成、2026-10-15）。第1版 Fable REVISE（review-design-1.md）→ 第2版 Fable APPROVE 条件付き（review-design-2.md）→ 第2.1版で C1〜C3 追記 → 第3版 Fable APPROVE 条件付き（review-design-3.md）→ 第3.1版で C4〜C6・低指摘を追記。PO 実装承認: 2026-10-15 の PO 回答「Y」（下記の原文2件。Opus の提示文に「y なら設計を直して審査に出し、合格したら実装・マージ・導入まで進めます」と明記したうえでの回答）。

PO の決定（2026-10-15、原文）:
- 実装の y/n に対して「Y→移したものはすぐに消してもいいと考えているがどうか？直近7日以内に会話がアクティブに進んでいないセッションについては終わったセッションだと判断してアーカイブしていく、アーカイブしたデータはMAC側には保持しない、必要な場合はHDD側に見に行けばいいと考えるがどうか？」
- Opus の提示（「HDD に写ったことを確かめた物だけ消す」「memory・~/CC報告ファイル-keep・agent-console で開いているセッションは Mac に残す」「弊害: 7日より前のセッションは Mac から再開できない／HDD 1台だけになる」）に対して「Y」。

## 1. 目的（PO に見える変化）
- Claude の会話・担当の記録・設計文書・PO の画像が、毎日 HDD の鍵付きの入れ物へ足される（HDD 側では何も消えない）。
- 7日動いていないセッションの記録と、7日より古い文書・画像は、HDD に写ったことを確かめてから Mac から消える（Mac には残さない。見るときは HDD を開く）。
- 写さない生出力・作業メモも、HDD への写しが成功している間だけ、7日より古い物から Mac から消える。
- Mac に残す: 記憶（memory）、~/CC報告ファイル-keep、agent-console で開いているセッション、history.jsonl、agent-console のデータ。
- HDD をつないでいない日が3日続くと、Mac に通知が出る。

## 2. 現在地（事実）
- 仕分けの正本: ~/CC報告ファイル-keep/archive-sort/classification.md（PO 承認済み）。
- 初回の写し（2026-10-15 09:24-09:30）: 生出力 /tmp/CC報告ファイル/archive-sort/initial-copy/（counts.txt・sha.txt・sample.txt・enc.log・commands.md・recount.txt）。入れ物 "/Volumes/HIGHLIFEJPN HDD/claude-archive.sparsebundle"（enc.log: encrypted YES、AES）。ボリューム名 ClaudeArchive。合言葉はキーチェーン（service=claude-archive-hdd, account=archive）。
  - counts.txt の tmpmd・images 行は 0（担当の集計誤り）。再集計は recount.txt（§11 で記録）。
- 調査: /tmp/CC報告ファイル/archive-sort/design-recon/recon.md と 01〜12。
  - disk-janitor（origin/main scripts/disk-janitor.sh）: 規則 R1〜R4（:4-8）、既定 dry-run・--execute（:11-12, :349-355）、dj_guard はディレクトリ専用（:96 `[ -d ]`）・物理パス一致（:97-99）、dj_act は `rm -rf`（:151）、R1 は DJ_ROOTS 全体を走査（:194-196）、mkdir ロック＋trap（:33, :360-365）、ログ 1MB 1世代（:336-345）、dj_canon（:372-377）。plist は ~/.salesanchor-tools を fetch → きれいなら origin/main に detach checkout → 実行（ops/launchd/jp.salesanchor.disk-janitor.plist:34）。
  - Claude Code は projects の jsonl・subagents・tool-results・plans を cleanupPeriodDays（既定30日・設定なし）で消す（公式 https://code.claude.com/docs/en/claude-directory）。
  - agent-console: activity 7日（server/config.ts:48）、uploads 新しい100件（server/config.ts:53、server/uploads.ts:94）。boards・routine-audit.jsonl の削除処理は検索で見つからない（網羅性未確認）。
  - rsync は /usr/bin/rsync（openrsync、2.6.9 互換）。使える: -a -n -i -m -R --include/--exclude --files-from --stats -E。使えない: --info=progress2 --mkpath（review-design-1.md 末尾表、実測）。
  - macOS に timeout コマンドは無い。/tmp は /private/tmp への symlink。
  - agent-console の開いているセッション一覧: dataDir/open-sessions.json、形は `{"version":1,"items":[{"id","roleId","name","cwd","branch"?,"claudeSessionId"?}]}`（agent-console origin/main server/session-store.ts:9, :15-23, :54-59）。claudeSessionId は取れたときだけ。退避側の同名ファイルを合わせる仕組みがある（server/held-merge.ts:7-11）。
  - ~/.claude/projects/<slug>/ の中身: `<uuid>.jsonl`（会話）と `<uuid>/`（subagents/・tool-results/）と `memory/`。
  - /private/tmp/claude-501 の構造: `<slug>/<uuid>/images/`（PO の画像、6か所）、`<slug>/<uuid>/scratchpad/`（作業メモ。中に Playwright の images/ が14か所）、`<slug>/<uuid>/tasks/a*.output`（~/.claude/projects への symlink）と `b*.output`（通常ファイル）。
- 未確認: dataDir の容量（ac-routine-guard が担当の読み取りを止めた）。launchd の下でログインキーチェーンが読めるか（K3 で確かめる）。

## 3. 対象と対象外
- 対象（salesanchor リポジトリ、`bash scripts/new-worktree.sh release/claude-archive --claude`、origin/main 起点）:
  - 新規 scripts/claude-archive.sh（毎日写す＋写した物を Mac から片付ける §4-11）、scripts/tests/test-claude-archive.sh
  - 新規 ops/launchd/jp.salesanchor.claude-archive.plist（毎日 03:30。disk-janitor と同じ型: ~/.salesanchor-tools を fetch → きれいなら origin/main に detach checkout → `bash scripts/claude-archive.sh`、汚れていれば exit 1。RunAtLoad=false・KeepAlive=false、StandardOut/StandardError を ~/Library/Logs/claude-archive.out/.err、EnvironmentVariables は PATH のみ）
  - scripts/disk-janitor.sh に R5・R6 と dj_guard_file・dj_act_file を追加（既存 dj_guard・dj_act・R1〜R4 の本文は変えない）、scripts/tests/test-disk-janitor.sh に試験追加
  - docs/handoff/claude-archive/{recon.md,design.md}（本書と classification.md を移す）と evidence/（design-recon の 01〜12・recon.md、initial-copy の counts.txt・recount.txt・sha.txt・sample.txt・enc.log・commands.md）。R5 で /tmp の生出力が消えるため。
- 対象外: Claude Code の cleanupPeriodDays、agent-console のコード、~/.claude の file-history・plugins 等（Claude Code 自身の掃除に任せる）、HDD 上の既存の物（mac-archive-20261014）、圧縮、CI の workflow（§10）。

## 4. 毎日写す（scripts/claude-archive.sh）
`set -euo pipefail` は使わず各手順の rc を見る（1項目の失敗で残りを止めないため）。`set -x`・`bash -x` 禁止。合言葉はシェル変数に入れず、パイプで直接渡す。

差し替え変数（試験用。既定値は本番）: CA_HDD_MOUNT（/Volumes/HIGHLIFEJPN HDD）、CA_IMAGE（$CA_HDD_MOUNT/claude-archive.sparsebundle）、CA_SECURITY_CMD（security）、CA_HDIUTIL_CMD（hdiutil）、CA_RSYNC_CMD（/usr/bin/rsync）、CA_OSASCRIPT_CMD（osascript）、CA_LOG_FILE（~/Library/Logs/claude-archive.log）、CA_LAST_OK（~/Library/Logs/claude-archive.last-ok）、CA_LOCK_DIR（/tmp/claude-archive.lock.d）、CA_NOW（現在の UNIX 秒）、各写し元（CA_SRC_PROJECTS ほか §4-4 の表の各元）、CA_DATADIR（$HOME/Library/Application Support/agent-console）。

1. ロック: mkdir "$CA_LOCK_DIR" ＋ trap（EXIT INT TERM）。trap は「開いた場合は detach、mktemp で作った場所は rmdir、ロック解除」を行う。
2. HDD の確認: "$CA_HDD_MOUNT" がディレクトリで、かつ "$CA_IMAGE" が在る。無ければ「HDD なし（名前が変わった可能性も含む）」とログに書き、手順7へ（終了コード 0、last-ok は更新しない）。
3. 開く:
   - 既に開いているか（C3）: `"$CA_HDIUTIL_CMD" info -plist | plutil -convert json -o - -` を python3 で読み、images[] のうち image-path が "$CA_IMAGE" と一致する物の system-entities[] にある mount-point を使う（開いたのは自分でないので detach しない）。読めない・無いときは自分で開く。key 名は K1 の前に何かを attach した状態の生出力で確かめ evidence/ へ保存（実機未確認のため）。
   - 無ければ `MP=$(mktemp -d /tmp/claude-archive-mnt.XXXXXX)` に、`"$CA_SECURITY_CMD" find-generic-password -s claude-archive-hdd -a archive -w | tr -d '\n' | "$CA_HDIUTIL_CMD" attach -stdinpass -nobrowse -mountpoint "$MP" "$CA_IMAGE"`。作成時は `P=$(security … -w)` の後 `printf '%s' "$P" | hdiutil create … -stdinpass`（末尾改行なし、initial-copy/commands.md）。`tr -d '\n'` は同じバイト列になる（合言葉は base64 44文字で途中に改行が無い）。合言葉はシェル変数に入れない。
   - 上限時間: 合言葉の取得から attach までのパイプライン全体で 150秒、detach 1回 120秒、rsync 1項目 60分。実装は「背景実行 → 1秒ごとに確認 → 超えたら kill」の関数1つ（macOS に timeout が無いため）。超えたら失敗。
   - 開けなければ失敗としてログ、手順7へ（exit 1）。
4. 写す（rsync -a、--delete を付けない＝足すだけ。元で消えた・改名した物は写し先に残る）。拡張属性は写さない（-E を付けない）。

| 項目 | 元 | 先（入れ物の中） | 書き方 |
|---|---|---|---|
| projects | ~/.claude/projects/ | claude/projects/ | `rsync -a SRC/ DST/` |
| history | ~/.claude/history.jsonl | claude/history.jsonl | `rsync -a SRC DST` |
| plans | ~/.claude/plans/ | claude/plans/ | `rsync -a SRC/ DST/` |
| keep | ~/CC報告ファイル-keep/ | CC報告ファイル-keep/ | `rsync -a SRC/ DST/` |
| tmpmd | /private/tmp/CC報告ファイル/ | tmp-CC報告ファイル-md/ | `rsync -a -m --include='*/' --include='*.md' --exclude='*' SRC/ DST/` |
| images | /private/tmp/claude-501/<slug>/<uuid>/images/ | claude-tmp-images/<slug>/<uuid>/images/ | 各 images ごとに `rsync -a -R "/private/tmp/claude-501/./<slug>/<uuid>/images/" DST/`（構造を保つ。scratchpad の下の images は対象外） |
| dataDir | $CA_DATADIR の boards/・routine-audit.jsonl・diff-comments.json・uploads/ | agent-console/ | 各々 `rsync -a`（launchd が実行するので Claude のフックは関わらない。agent-tokens・その他は写さない） |

5. 確かめる: 各項目ごとに「rsync の rc」「元の件数（find -type f | wc -l）」「先の件数」「`rsync -ani` の行数（記録のみ）」をログに1行。失敗の条件は ①rc≠0 ②元が1件以上なのに先が0件。追記中の jsonl で -ani が 0 にならないのは失敗にしない。元が無い項目（例: images が0か所）は「元 0」と記録して成功扱い。
実行順（C5。この番号どおりに実装する）:
6. last-ok: 写しの全項目が成功した時点で "$CA_LAST_OK" に CA_NOW を書く（C2）。どれか項目が失敗なら書かない。
7. 片付け: 写しが全項目成功したときだけ、入れ物が開いている間に §4-11 を行う。片付けの失敗はログと exit 1 にするが last-ok には影響させない。
8. 閉じる: 自分で開いた場合は `hdiutil detach "$MP"` を 10秒間隔で最大3回試し、成功したら rmdir "$MP"。それでも失敗したら「detach 失敗」を別にログし exit 1（last-ok はそのまま）。Spotlight の索引停止（mdutil）は入れない。
9. 通知: last-ok が無いか、CA_NOW − last-ok が 3日（259200秒）を超えるとき、`"$CA_OSASCRIPT_CMD" -e 'display notification "HDD への写しが3日以上できていません。HDD をつないでください" with title "Claude アーカイブ"'`。
10. 終了とログ: "$CA_LOG_FILE"、1MB 超で .1 に1世代（disk-janitor と同じ）。写しの失敗・片付けの失敗・detach 失敗のどれかがあれば exit 1、HDD なしは exit 0。

11. 写した物を Mac から片付ける（PO 決定。既定は dry-run＝一覧だけ、plist は `--execute` を付ける。disk-janitor と同じ型）
- 前提: 当日の写しが全項目成功した（§4-5）。1つでも失敗した日は片付けをしない（ログ「片付け見送り」）。
- 古さ: CA_MOVE_DAYS（既定 7）。CA_NOW − mtime > CA_MOVE_DAYS×86400。
- 対象と単位:
  | 単位 | Mac 側 | 古さの判定 | 消す物 |
  |---|---|---|---|
  | セッション | ~/.claude/projects/<slug>/<uuid>.jsonl と ~/.claude/projects/<slug>/<uuid>/ | jsonl と <uuid>/ 配下の全ファイルの mtime の最大が古い | jsonl と <uuid>/ 配下の全ファイル（空になったディレクトリも消す） |
  | 計画 | ~/.claude/plans/ の各ファイル | そのファイルの mtime | そのファイル |
  | 文書 | /private/tmp/CC報告ファイル の各 *.md | そのファイルの mtime | そのファイル |
  | 画像 | /private/tmp/claude-501/<slug>/<uuid>/images/ の各ファイル | そのファイルの mtime | そのファイル |
- 消さない（対象外）: ~/.claude/projects/*/memory/ 配下、<uuid> が UUID の形でない物、history.jsonl、~/CC報告ファイル-keep、agent-console の dataDir、symlink（`-type f` かつ `! -L` のみ）。
- 開いているセッションを守る（C4）: 守る集合 = ①"$CA_DATADIR" の open-sessions*.json（open-sessions.json と退避側 open-sessions.tmux-held.json、agent-console server/held-merge.ts:57）の items[].claudeSessionId ②"$CA_SESSIONS_DIR"（既定 ~/.claude/sessions）の各 *.json の sessionId（動いている Claude Code 1つにつき1ファイル、終わると消える＝公式 claude-directory。ターミナル・tmux で直接動くセッションを守る。sessionId 以外のキーは読まない）。集合に入るセッションは古くても消さず、その `<slug>/<uuid>/images/` も消さない。①の open-sessions.json が無い・読めない・version≠1、または②で読めない .json が1つでもあるときは「セッション単位の片付けを全部見送り」とログ（他の単位は続ける）。
- 写ったことの確かめ（1ファイルずつ）: 入れ物の中の対応するファイル（§4-4 の表の先）が在り、`stat -f '%z %m'`（大きさと更新時刻）が Mac 側と一致する。rsync -a は更新時刻を保つ。1つでも一致しないファイルがあるセッションは丸ごと消さない（ログに理由）。一致したファイルだけを消す単位（計画・文書・画像）は、一致した物だけ消す。
- 消す直前にもう一度 mtime を見て、古さの条件を満たし、確かめた時の値から変わっていないことを確認する（その間に Claude が再開して書いた場合は消さない）。
- 消し方: `rm -f -- <ファイル>`、空ディレクトリは `rmdir`（中身があれば失敗して残る）。`rm -rf` は使わない。
- ログ: 単位ごとに「対象数・消した数・見送った数と理由・消した合計バイト」を1行。消したファイル名の一覧は入れ物の中の move-log/YYYYMMDD.txt に書く（Mac 側に残さない。HDD で何がいつ移ったか探せるように）。
- Claude Code 自身の30日削除はそのまま（Mac 側で7日より古い物は先に消えている）。

## 5. 消す（disk-janitor に R5・R6）
- 新設 dj_guard_file（絶対パス・`.`/`..` 無し・指定根の下・物理パス一致・`-f` かつ `! -L`・mtime が DJ_STALE_DAYS より古い）と dj_act_file（dry-run なら一覧のみ、--execute なら `rm -f --`、サイズは stat -f %z）。dj_guard・dj_act は変えない。
- 根は規則専用の変数を dj_config に足す: DJ_ROOT_TMP_CC（既定 /private/tmp/CC報告ファイル）、DJ_ROOT_CLAUDE_TMP（既定 /private/tmp/claude-501）、DJ_CA_LAST_OK（既定 ~/Library/Logs/claude-archive.last-ok）、DJ_CA_FRESH_SEC（既定 172800＝2日）。DJ_ROOTS には入れない（R1 の走査を広げない）。DJ_STALE_DAYS は既存の値を使わず R5/R6 用に DJ_TMP_STALE_DAYS（既定 7。PO 決定「移したものはすぐに消してもいい」に合わせ §4-11 と同じ日数）。
- 前提条件（PO に伝えた「HDD に写せたと確かめてから消す」、classification.md:35）: DJ_CA_LAST_OK があり、現在 − その値 ≤ DJ_CA_FRESH_SEC のときだけ R5・R6 を動かす。満たさなければ「R5/R6 見送り（HDD 写しが2日以上成功していない）」とログ。
- R5: `find -P "$DJ_ROOT_TMP_CC" -type f ! -name '*.md' -mtime +$DJ_TMP_STALE_DAYS` の各ファイル。
- R6: `find -P "$DJ_ROOT_CLAUDE_TMP" -mindepth 3 -maxdepth 3 -type d -name scratchpad` の各下にある全ファイル（`-type f -mtime +N`。中の images/ も消す）と、`<slug>/<uuid>/tasks/b*.output`（`-type f -mtime +N`）。`<slug>/<uuid>/images/` には触れない。a*.output は symlink なので `-type f` で外れる。ただし指す先が無い a*.output（宙に浮いた symlink、`-type l ! -e` 相当を `[ -L f ] && [ ! -e f ]` で判定）は7日を過ぎたら消してよい（symlink 自体だけを消し、指す先はたどらない）。
- 空になったディレクトリは消さない。使用中判定（lsof）は使わない（14日更新が無い作業ファイルを開き続ける用途が無い。消して困るのは Claude の作業中ファイルで、それは更新が新しい）。
- 7日の理由: PO 決定（7日動いていない物は終わった物とみなす）に揃える。

## 6. 代替案
- A. cleanupPeriodDays を伸ばし Mac に置き続ける: Mac のディスクを圧迫する（PO の懸念そのもの）。不採用。
- B. Time Machine: HDD が暗号化なしで、対象の選び分けができない。不採用。
- C. 採用案: 鍵付きの入れ物へ毎日足す。

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| HDD をつながない日が30日続くと、Claude Code が消した分が失われる | 3日で通知（§4-8） |
| 画面ロック中などでキーチェーンが読めない／ダイアログが出る | 150秒（§4-3 のパイプライン上限）で打ち切り失敗。K3 で実機確認。読めなければ停止して PO へ（設計を戻す） |
| 合言葉が Mac のキーチェーンにしかない | PO にパスワード管理へ控えてもらう（PO 作業。10/15 に依頼済み） |
| 写している最中にファイルが書かれる | 次の日に足される。片付けは大きさ・更新時刻の一致と消す直前の再確認で、書かれた物を消さない |
| Mac から消した物は HDD 1台だけになる（PO 了承済み） | HDD の故障で失う。2台目は別途 PO 判断（本設計の対象外） |
| 7日より前のセッションは Mac から再開できない（PO 了承済み） | HDD から写し戻せば再開できるかを K13 で確かめ、手順を残す |
| 開いているセッションを消して再開できなくなる | open-sessions*.json の claudeSessionId を守る。読めなければセッション単位を全部見送る |
| 写している最中に HDD が抜けると入れ物が壊れうる | 次回の attach 失敗がログと通知で分かる。修復は自動でしない（PO と相談） |
| Mac がスリープ中の 03:30 | launchd が起床後に1回まとめて実行（既存 jp.salesanchor.stop-log-digest-daily.plist と同じ） |
| 社外秘・PO が貼った値が HDD に載る | 暗号化した入れ物の中にだけ書く。入れ物の外とログに中身・合言葉を書かない（K5） |
| R5/R6 が消してはいけない物を消す | 規則専用の根・ファイル用ガード・.md と `<slug>/<uuid>/images/` の除外・dry-run 既定・HDD 写し成功が前提（K6） |

## 8. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 HDD をつないで手動で1回実行すると、§4-4 の全項目が rc=0、元が1件以上の項目は先も1件以上、入れ物が閉じ、last-ok が書かれる | 実機で1回。ログと hdiutil info の生出力を evidence/ へ。担当（Sonnet）が手で実行するときは ac-routine-guard が dataDir を禁じるため CA_DATADIR を存在しない場所にし（「元 0」）、dataDir 項目と open-sessions の読み取りは K3（launchd から実行）で確かめる。それまで §4-11 のセッション単位は見送りになる（設計どおり） |
| K2 HDD が無いと何も書かず「HDD なし」で exit 0、last-ok は変わらない | test-claude-archive.sh（CA_HDD_MOUNT を存在しない場所に） |
| K3 launchd から実行しても合言葉を読めて開ける | plist 導入後 `launchctl kickstart` で1回。ログに全項目 OK |
| K4 last-ok が3日より古い／無いと通知が呼ばれ、新しいと呼ばれない | 試験（CA_NOW・CA_LAST_OK・CA_OSASCRIPT_CMD をスタブ）。実機の通知表示は K3 と同時に目視 |
| K5 入れ物の外に書かない・ログに合言葉が出ない | 試験: スタブ security が目印文字列を返し、ログと標準出力・標準エラーに目印が0件。実機: 実行後に HDD 直下の ls が前と同じ |
| K6 R5・R6 は dry-run で対象を列挙し、.md・`<slug>/<uuid>/images/`・a*.output（symlink）・7日以内・根の外を消さない。last-ok が古い／無いと R5・R6 を見送る | test-disk-janitor.sh に追加（DJ_ROOT_TMP_CC・DJ_ROOT_CLAUDE_TMP・DJ_CA_LAST_OK・DJ_TMP_STALE_DAYS を差し替え） |
| K9 試験が本番の場所に触れない（C1） | test-disk-janitor.sh 冒頭の export ブロック（origin/main :45-48）に新4変数を一時ディレクトリ $T の下で追加し、--execute（:141）より前に「全ての根・last-ok が $T の下」を assert。test-claude-archive.sh も CA_* の全てがスタブまたは $T の下であることを assert してから実行（実機の security・hdiutil・HDD・osascript を呼ばない） |
| K10 detach が失敗しても、写しが全て成功していれば last-ok は書かれ、exit 1 とログ「detach 失敗」が残る（C2） | 試験（CA_HDIUTIL_CMD スタブの detach が3回失敗） |
| K7 1項目が失敗しても残りを写し、last-ok を更新せず exit 1 | 試験（CA_RSYNC_CMD スタブが1項目だけ rc=23） |
| K8 翌朝 03:30 の自動実行で last-ok が更新される | 翌日のログ |
| K11 片付けは、HDD 側と大きさ・更新時刻が一致したファイルだけを消し、memory・UUID でない物・open-sessions にあるセッション・7日以内・symlink を消さない。一致しないファイルが1つでもあるセッションは丸ごと残す。open-sessions が読めないとセッション単位を全部見送る。既定 dry-run では何も消さない | test-claude-archive.sh（CA_SRC_*・CA_DATADIR・CA_SESSIONS_DIR・写し先・move-log 先を $T の下に、CA_NOW・CA_MOVE_DAYS を差し替え、--execute あり／なし）。試験の筋（C6）: ①open-sessions にある／sessions/ にある／どちらにも無い の3セッション（全て8日前）で3つ目だけ消える ②写し先の1ファイルの大きさを変えるとそのセッションは丸ごと残る ③open-sessions.json の version:2 でセッション単位が全見送り（計画・文書・画像は続く） ④dry-run で実行前後の find 一覧が同一 ⑤memory/ と7日以内の物は --execute でも残る |
| K12 片付けの前後で、消したファイルが入れ物の中に在り、move-log に名前が載る | 実機 K1 の後に --execute で1回。前後の件数・df と move-log の行数を evidence/ へ |
| K13 HDD から戻して再開できる（PO の使い方の確認）: 片付けたセッション1つを入れ物から ~/.claude/projects/<slug>/ へ写し戻し（`<uuid>.jsonl` と `<uuid>/` の両方）、`claude --resume <uuid>` で過去の会話が表示されて続きを打てる【推測: 公式に明文なし】。写し戻した物も30日を過ぎると Claude Code が再び消し、7日動かなければ本仕組みが再び片付ける | 実機で1回（Opus が手順を残す）。できなければ「読んで要約し新しいセッションで続ける」だけを使い方として残し、PO に伝える |

## 9. PR と GO・戻し方
- ops/launchd と scripts/ は危険パス（scripts/tests/test-process-artifacts.js:149-150）。ADR-136 の手順で GO を記録する。GO は PO の委任（docs/adr/ADR-1003-go-delegation-to-opus.md、Accepted 2026-09-29）に基づき Opus が発行し、PR 本文 `### GO記録` に「POの委任に基づくClaude Opus発行」と書く。
- 毎日無人で消す（R5・R6・§4-11）ことの許可: PO の 2026-10-15「Y」2回（classification.md:3 の②、と冒頭の PO 決定）を根拠とし、原文を GO 記録に転記する。
- 戻し方（片付け）: plist から `--execute` を外せば一覧だけになる。消した物は入れ物の中に在るので、move-log を見て写し戻せる。
- 導入: マージ後、~/.salesanchor-tools が origin/main を取り込む形で plist を ~/Library/LaunchAgents に置き launchctl bootstrap（disk-janitor の導入手順に合わせる）。
- 戻し方: launchctl bootout で外す。R5・R6 は revert。HDD 上の物は残る（消さない）。

## 10. 維持する仕組み
- 毎日のログ（~/Library/Logs/claude-archive.log）と3日通知。
- 試験は CI に載せない（CI は ubuntu で hdiutil・security・osascript・openrsync が無く、既存 test-disk-janitor.sh も CI では回っていない）。PR 時に両試験を手動で実行し、生出力を docs/handoff/claude-archive/evidence/ に保存する。
- 守り手: scripts/tests/test-claude-archive.sh、scripts/tests/test-disk-janitor.sh。

## 11. 実装前の確認（工程0）
- 済（Opus 確認 2026-10-15）: 作成時の渡し方は commands.md のとおり末尾改行なし → §4-3 に `tr -d '\n'` で固定。K1 の最初に開けることを確かめ、開けなければ停止して Opus へ。
- 済: recount.txt で写し先 tmp-CC報告ファイル-md 3359件・claude-tmp-images 8件（元 3369件・8件。md の差10件は【推測】初回後に作られた物）。

## 外部事例
不要（Mac 1台の個人用の写しで、比べる外部の事例が設計を左右しない）。
