# design: AI が足した見張りを記録できる道（草案・2026-11-09）

状態: 設計案作成済み（第3版）／自己審査済み（同じ AI。§12）／§9 は PO 決定済み（2026-11-09「1」＝案1）／クラウドでの設計審査 1回目 REVISE（必須6件）・2回目 REVISE（必須4件・推奨3件）を反映済み・3回目は未実施／実装未着手。
根拠: recon.md（同じフォルダ）。関係 ADR: ADR-1034・ADR-1033・ADR-1029。

## 1. 目的（PO の言葉から）
- PO の言葉（2026-11-09）:「原則私はエンジニアではないから見張りを足すのはあなたと実行者だけ」。
- 今は、AI が設計し PR で入れた見張りでも、~/.claude に入れるのは PO の `!`、記録には PO の「1」（本文にハッシュの入った同意票）が要る。記録の道が無いので、週次点検で毎回「異常」に出る（11/02・11/09）。
- 目的: 見張りを足す・強める作業は AI だけで最後まで進み、週次点検に異常として出ないこと。見張りを外す・弱める変更は、今までどおり必ず異常として見つかること。

## 2. KGI（PO が週次点検の1行で○×を判定できる形）
| 番号 | 基準 | 今 | 目標 | 測り方 |
|---|---|---|---|---|
| K1 | GitHub main にマージ済みの PR から入れた見張り（足す・組に足す）が、週次点検の `ABNORMAL_REASON=B` に出る件数 | 11/09 で3件 | 導入後の毎週 0件 | 週次点検の出力の B の行を数える |
| K2 | 見張りを外す・組から抜く・PR に無い中身に書き換える・試験を消す・確認を飛ばす返事を足す変更が B に出る割合 | 100%（今は全部出る） | 100% のまま | 試験（A3〜A5・A8・A9）で各1件ずつ作り、全部 B に出ること |
| K3 | 見張りを入れるために PO が `!` を打つ回数 | mac-test-guard で1回 | 0回（導入時の1回を除く） | 新しい見張りの設計書の「導入」の欄に PO の `!` が無いこと |

## 3. 対象と対象外
- 対象: ~/.claude/settings.json の hooks（user:hooks）と ~/.claude/scripts/ の見張りの本体（hook_files）のうち、正本が `scripts/agent-hooks/<名前>/` のフォルダにあり、そのフォルダに台帳札 `guard-manifest.json`（§5-0）があるもの。
- 対象外のまま（B が出る）: `scripts/agent-hooks/` の直下に置かれた見張り（例: master-register-rules-guard.py）、札の無いフォルダ、正本がリポジトリに無い見張り。
- 対象外（今までどおり PO の「1」）: 見張りを外す・弱める変更、permissions.deny / ask / defaultMode、確認を省く設定、autoMode.soft_deny / environment、danger_ops、本番の設定。

## 4. 変更前後
| | 変更前 | 変更後 |
|---|---|---|
| 見張りの正本 | リポジトリの `scripts/agent-hooks/<名前>/`（置き方は見張りごとにばらばら。直下に置いたものもある） | 同じフォルダに台帳札 `guard-manifest.json` を置いたものだけが対象（§5-0） |
| ~/.claude へ入れる台本 | 見張りごとの install.sh を PO が `!` で流す | 全部の見張りで共通の台本 `scripts/agent-hooks/install-guard.sh <名前>` を1本だけ使う。Opus か実行役が流す。自動判定の例外 HKI-1 で通す（§6） |
| 台帳への記録 | PO の「1」で `consent:` の record（無いと B） | 共通の台本が最後に `perm-change.py record --po-ref PR#<n>` を書く（§6） |
| 点検の確かめ | user:hooks・hook_files の PR 番号は通らない（consent-audit.py:906） | 「強める変更」に限り PR 番号で通す（§5） |
| 外す・弱める | PO の `!`＋「1」 | 変わらない |
| 共通の台本そのものの変更 | （無い） | PO の「1」が要る（§5-5） |

変更するファイル（実装の便で触るもの。これ以外は触らない）:
- `scripts/dev/consent-audit.py`: §5 の分岐を足す。今の照合値は中身の sha8 だけでパスを持たない（consent-audit.py:701）ので、札からパスを引く処理を足す。
- `scripts/dev/perm-change.py`: record に `--replaced-by`・`--batch`・`--old-json` を足す（今の record の引数は perm-change.py:739-745 で、この3つは無い）。
- `scripts/agent-hooks/install-guard.sh`（新規）と、その試験。
- `scripts/agent-hooks/mac-test-guard/guard-manifest.json`（新規。1つ目の対象）。
- `.github/workflows/agent-hooks-test.yml`: mac-test-guard の試験と install-guard.sh の試験を足す。
- `scripts/dev/permission-delegation-tests.py`: A1〜A5・A7〜A9 の試験を足す。
- 審査役（reviewer）の定義: §5 の末尾の確認項目2行を足す。

## 5. 「強める変更」の定め方（点検が機械で判定する）
### 5-0. 台帳札 guard-manifest.json（点検が読む正本の対応表）
見張りのフォルダごとに1つ置く。形:
```json
{"name": "mac-test-guard",
 "files": ["guard.py"],
 "hooks": [{"event": "PreToolUse", "matcher": "Bash", "interpreter": "python3", "file": "guard.py", "after": "mac-vm-guard.py"}],
 "tests": ["test_guard.py"]}
```
- 名前は `^[a-z0-9-]+$`。フォルダ名と同じであること。
- `files`・`tests`・`hooks[].file`・`hooks[].after` に書ける名前は、フォルダの中の相対パスだけ。形は `^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$` で、`..` の区切りと `/` で始まる名前は拒む（例: `../review-gate/gate.py` と書いて別の見張りのファイルを上書きする道をふさぐ）。台本と点検の両方で拒み、拒んだら台本は止まり、点検は B にする。
- `hooks[].event` に書けるのは `PreToolUse` と `Stop` だけ。ほかの event（確認を代わりに出す PermissionRequest、文脈を足す UserPromptSubmit・SessionStart など）への登録は PO の「1」が要る（B）。
- 足す命令の組の欄は `type` と `command` だけ（`timeout` などほかの欄は札に書けない）。
- パスの対応は固定: 入れた先 `~/.claude/scripts/<name>/<file>` ⇔ 正本 `scripts/agent-hooks/<name>/<file>`。点検は sha8(`<name>/<file>`) を札から計算し、hook_files の要素（consent-audit.py:656 の `sha8(相対パス)|中身8桁`）と突き合わせる。
- 命令の形は固定: `<interpreter> <$HOME を展開した絶対パス>/.claude/scripts/<name>/<file>`（mac-test-guard の install.sh:34 と同じ形）。点検はこの文字列を札から作り、組の JSON と比べる。interpreter は `python3` と `bash` だけ。

### 5-1〜5-4. PR 番号 `PR#n` で説明できる変化（どれにも当たらなければ今までどおり B）
1. hook_files の増: 要素の相対パスが札の `files` のどれかで、中身8桁が、PR #n のマージの版の正本と一致し、PR #n の差分がそのフォルダを変えている。
2. user:hooks の増（新しい組）: 組のすべてのフックが、§5-0 の形で札の `hooks` から作れるフック（`{"type": "command", "command": <§5-0 の命令>}` と全部の欄が同じ）。前回の写しは組の sha8 しか持たない（consent-audit.py:589）ので、「前回から登録済み」は条件にしない。既にある命令と同じ組に足すときは 3. で扱う。
3. user:hooks の組の入れ替え: 減の組 E_old と増の組 E_new が、同じ束（下）にあり、同じ event と matcher で、E_old の各フックの中身（`type`・`command`・`timeout` など全部の欄）が E_new に同じ形で同じ順に入っていて、足したフックが 2. を満たす。命令の文字列だけでなく全部の欄を比べる（`timeout` を縮めて効きを弱める道をふさぐ）。減の行には `--replaced-by <E_new の sha8>` と E_old の JSON 全体を持たせる。点検は、行の JSON の sha8 が item_hash と同じことを確かめる。E_old の命令に秘密の値（`=` を含む引数・トークンの形）があれば、JSON を行に書かずに B のまま残す。
   - 束の決め方: 共通の台本の1回の実行で書いた行。行に同じ `batch:<実行の id>`（台本が作る乱数16桁）と同じ PR#n を持たせる。
4. hook_files の中身の書き換え（同じパスで中身が変わる）【PO 決定 §9 案1】: 1. の条件に加え、次の全部を満たすこと。
   - PR #n の差分を `git diff --no-renames <マージの親1> <マージ>` で取り、札の `tests` にあるファイルに `-` の行が0行。
   - 札の `tests` から消えた名前が0件（前のマージの版の札と比べる）。
   - 札の `tests` の全部が、GitHub main の `.github/workflows/agent-hooks-test.yml` の jobs の steps の `run:` の行で呼ばれている（注釈の行は数えない。YAML として読み、`run` の値の中に試験のパスがあること）。
5. 時刻の条件（§5 の分岐だけに使う）: 今の PR 番号での確かめは「マージが今から7日以内」を求める（consent-audit.py:900-901・DAYS=7 は :30）。§5 の分岐ではこれを使わず、次の2つにする。
   - PR #n のマージの時刻が、record の行の時刻より前。
   - record の行の時刻が、点検の期間（今から7日）の中。
   これで、マージから7日以上たって入れた見張りも、入れた週の点検で B に出ない。古い PR 番号を後から何度も使う道は、§8 の 5（同じ po_ref と item_hash の組は1回）でふさぐ。

### 5-5. 強める変更とは数えないもの（必ず B）
- 本体の中に、確認を飛ばす返事や、実行する中身を書き換える返事を返す処理があるもの。点検は正本の全ファイルを読み、次のどれかが1行でもあれば B にする（台本も同じ検査で止まる）。
  - `permissionDecision` と `allow` が同じ行にある。
  - `approve` の語がある。
  - `updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext` の語がある。
  語の一覧の根拠は Claude Code の公式の hooks の説明（code.claude.com/docs/en/hooks。Context7 `/websites/code_claude` で 2026-11-09 に確認）: PreToolUse は `updatedInput` で実行する中身を差し替えられる。PermissionRequest は `decision.behavior: "allow"` で確認を代わりに通し、`updatedPermissions` で許可を足せる。PostToolUse は `updatedToolOutput` で結果を差し替えられる。文字列を組み立てて隠す書き方は機械では見つけきれないので、審査役の確認項目（下）と ADR の受け入れたリスクで持つ。
- 共通の台本 `install-guard.sh` と点検の判定の部分（consent-audit.py の §5 の分岐）を変える PR。台帳に置いた台本の sha256 と GitHub main の台本が違えば B。PO の「1」で台帳の値を更新する。
- 札の `files` や `hooks` から消えた名前があるもの（外す変更）。

あわせて、PR #n は ADR-1029 の審査（新しく起動した opus の審査役の APPROVE）を通ってマージされていることを条件にする（既にマージの見張りで強制されている）。審査役の確認項目に2行を足す。「この PR は見張りの止める範囲を狭めていないか」「確認を飛ばす返事（allow・approve）を返す道を作っていないか」。

## 6. 入れる道（共通の台本 install-guard.sh）
- 置き場所は `scripts/agent-hooks/install-guard.sh`（1本だけ）。見張りごとの install.sh は作らない。既にある mac-test-guard・confidential-quote-guard・review-gate の install.sh は残すが、AI は流さない（HKI-1 の対象外）。
- 台本の手順（どこか1つでも失敗したら settings.json に触らず `INSTALL_FAILED:` で止まる）:
  1. 引数は名前1つだけ。`^[a-z0-9-]+$` に合わない・フォルダや札が無い・引数が2つ以上なら止まる。
  2. 入れ先は `$HOME/.claude` に固定する。環境変数 CLAUDE_DIR は読まない（今の mac-test-guard/install.sh:8 の形を使わない）。
  3. 走らせる前に、~/.salesanchor-tools が変更なし（`git status --porcelain` が空）で、HEAD が `git ls-remote origin refs/heads/main` と同じことを確かめる。
  4. §5-5 の確認を飛ばす返事の検査を正本に当てる。
  5. 札の `files` を `~/.claude/scripts/<name>/` へ写し、原本と比べ、読み取り専用にする。
  6. 札の `tests` を写した先に向けて流す。
  7. settings.json の控えを取り、札の `hooks` の命令を足す（`after` の命令の直後。既にあれば足さない）。外す処理は持たない。
  8. JSON として読み直してから置き換える。
  9. PR 番号は `git log --first-parent origin/main -1 --format=%s -- scripts/agent-hooks/<name>/` の「Merge pull request #n」から取る。取れなければ記録せず止まる。
  10. 変わった要素ごとに `perm-change.py record --po-ref PR#<n>` の行を書く（§5-3 の batch と E_old の JSON を含む）。
- 自動判定の例外 HKI-1（PO が導入時に `!` で1回だけ足す。ADR-1034 の PDL-1 と同じ形）:
  > HKI-1: Allowed only for a Bash command that is exactly `bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <name>` on a single line, where `<name>` matches `^[a-z0-9-]+$`, with no other arguments, no environment variable prefix (for example `CLAUDE_DIR=`), no pipe, no `;`, `&&` or `||`, no newline, no `$(`, no backquote, and no redirection. The script itself refuses to run unless ~/.salesanchor-tools is clean and equal to GitHub main. It only adds guard hooks listed in a reviewed and merged guard-manifest.json; it never removes or loosens hooks. Running any per-guard install.sh or rollback.sh, any other script under ~/.salesanchor-tools or ~/.claude, or editing settings files directly is still Self-Modification.
- 台本の版の確かめ（手順3）は台本が自分で行う。書き換えられた台本は、その確かめも飛ばせる。外す・弱める変化を最後に見つけるのは週次点検だけ（台本の変更は §5-5 で B、settings.json と本体の変化は §5 に当たらなければ B）。台本の確かめは事故を防ぐためのもので、守りの本体は点検である。
- 1つ目の対象は mac-test-guard。札を足す PR で、test_guard.py を CI（agent-hooks-test.yml）に足す。今の CI が流しているのは review-gate と master-register の試験だけ（.github/workflows/agent-hooks-test.yml:25・:36。mac-test-guard と confidential-quote-guard の試験は呼ばれていない。Opus が 2026-11-09 に `git grep agent-hooks origin/main -- .github/workflows/` で確認）。

## 7. 代替案
| 案 | 中身 | 採らない理由 |
|---|---|---|
| A 今のまま | PO の `!` と「1」 | PO の原則に反する。毎週異常が出て、本当の異常が埋もれる |
| B 見張りは全部 PR 番号で通す | 外す変更も通す | Opus は自分でマージできるので、見張りを外すことも AI だけで済む。ADR-1034 が閉じた穴が開く |
| C 点検から見張りを外す | 数えない | 弱める変更も見つからなくなる |
| D1 見張りごとの install.sh を例外で通す（第1版） | 名前の形だけで通す | 1回目の審査で不採用。Opus が自分でマージした install.sh なら中身を問わず通り、外す処理も入れられる |
| D2（採る） 共通の台本1本＋台帳札＋強める変更だけ PR 番号で通す | §5・§6 | 台本は1本に固定して PO の「1」で守る。見張りごとに変わるのは札と本体だけで、点検が機械で判定できる |

## 8. リスクと対処
1. 試験を消さずに、本体だけで止める範囲を狭める。対処: §5-4 の試験の条件（CI で流れる試験に限る）と審査役の確認項目。残る分は受け入れたリスクとして ADR に書く。
2. 本体に確認を飛ばす返事・中身を書き換える返事を隠して入れる（文字列を組み立てるなど）。対処: §5-0 の event の一覧と §5-5 の機械の検査と審査役の確認項目。残る分は ADR に書く。
3. 見張りの本体はフックとして何でも実行できる（設定ファイルを書き換える処理を入れるなど）。対処: 審査役の確認項目と週次点検（設定の変化は今までどおり B に出る）。残る分は ADR に書く。
4. HKI-1 の文が広く読まれ、ほかの台本まで通る。対処: 命令の形を1つに固定し、台本の中でも版を確かめる。導入後に A6 で、通らないことを確かめる。
5. 1つの PR を何度も使う。対処: 今の「同じ po_ref と item_hash の組は1回」をそのまま使う（permission-delegation/design.md:195）。
6. 審査役が中身を読まずに APPROVE できる（ADR-1029:40）。Opus は自分でマージできる。対処: この2つは新しい ADR に受け入れたリスクとして書き、PO の承認を取る。
- 戻し方: HKI-1 を外す台本（PO の `!`）と、consent-audit.py の §5 の分岐を元に戻す PR。共通の台本で入れた見張りを外すのは、今までどおり見張りごとの rollback.sh を PO の `!` で流す。
- 外部事例: 使わない。社内の決まり（誰が確認するか）の変更で、外の数値が設計の正しさを示さないため。

### 8-1. ADR の扱い
- 新しい ADR を起こし、ADR-1034 の決定2（見張りは R4。PR 番号で説明できるのは repo の settings.json だけ。ADR-1034:16・:34）を一部改める。改めるのは「§5 の強める変更に限り、user:hooks と hook_files も PR 番号で説明できる」の1点だけ。外す・弱める・共通の台本の変更は ADR-1034 のまま。
- Why に書くこと: PO の言葉（2026-11-09）、毎週の B（11/02・11/09）、§8 の受け入れたリスク 1・2・3・6。
- この ADR が PO に承認されるまで、実装の便は出さない。

## 9. PO の決定（2026-11-09。PO の返事「1」＝下の案1）
見張りの「中身の書き換え」を AI の確認だけで記録してよいか。
- 案1（採用）: 試験の行が1行も消えていない直しは AI で記録。試験を消す・変える直しと、外す変更は PO の「1」。
- 案2: 足す変更だけ AI で記録。中身の直しは全部 PO の「1」。
- 案3: 外す変更も含めて全部 AI で記録。

## 10. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| A1 §5-1〜3 を満たす増・入れ替えが B に出ない | 試験（一時の HOME と一時の git リポジトリ。既存の permission-delegation-tests.py に足す） |
| A2 今週の3件が下の3行の記録で説明でき、B が0件 | 11/09 の写しの複製を一時の HOME に置き、下の3行を一時の台帳に書いて点検を流す（`--commit-snapshot` なし）。点検の基準の時刻は固定する（run_audit の now を 2026-11-09T07:00:00Z にして呼ぶ。record の行の時刻は 2026-11-09T06:00:00Z）。流す日によって結果が変わらないこと。行: ① hook_files `29ac3748\|9e086e1e` を PR#5049 ② user:hooks `PreToolUse\|Bash\|3ba846f5` を PR#5049・batch X ③ user:hooks `PreToolUse\|Bash\|062521a7` の減を PR#5049・batch X・`--replaced-by 3ba846f5`・E_old の JSON。PR#5049 は GitHub main で mac-test-guard のフォルダを最後に変えたマージ（0e82884f7。その前は #5039 の c758ea8d8） |
| A3 組から命令を抜く入れ替え・既にあるフックの `timeout` を縮める入れ替えが B | 試験（2件） |
| A4 PR に無い中身・札の無いフォルダ・`scripts/agent-hooks/` の直下のファイル・札に `../` や `/` で始まる名前を書いたもの・`PreToolUse` と `Stop` 以外の event が B（台本も止まる） | 試験（5件） |
| A5 札の `tests` に `-` の行がある PR・`tests` から名前が消えた PR・CI で呼ばれていない試験での中身の書き換えが B | 試験（3件） |
| A6 AI が、見張りごとの install.sh・rollback.sh・`CLAUDE_DIR=` を前に付けた共通の台本・引数2つの共通の台本を走らせると止まる | 導入後に1回ずつ試す。止まったと判定する条件: Bash の結果が拒否で返り、settings.json の sha256 が試す前と同じ。4件の結果を keep に残す |
| A7 共通の台本が足すだけで、2回流しても命令は1件・台帳の行も1組 | 試験 |
| A8 §5-5 の語の一覧のどれかを含む見張りは、台本が止め、点検も B にする | 試験（語ごとに1件。`permissionDecision` と `allow`・`approve`・`updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext` の7件） |
| A10 マージから8日たって入れた見張りが、入れた週の点検で B に出ない。record の行の時刻がマージより前なら B | 試験（2件。now を固定する） |
| A9 共通の台本が、~/.salesanchor-tools に変更がある・main と版が違う・名前の形が違うときに止まる | 試験（3件） |

## 11. 維持の仕組み
- 週次点検（agent-console の定期作業）が毎週 K1・K2 を出す。B が出たら今までどおり Opus が中身を調べて PO に報告する。
- 新しい見張りの設計書は「正本は `scripts/agent-hooks/<名前>/`、札は guard-manifest.json、試験は agent-hooks-test.yml で流す、導入は AI が install-guard.sh」を書く。
- 審査役の確認項目（§5 の末尾の2行）は reviewer の定義に足す。

## 12. 設計審査
### 12-1. クラウドでの設計審査 1回目（2026-11-09 07:27 UTC・opus・読むだけ。判定 REVISE）
| 指摘 | 直したところ |
|---|---|
| 必須1 パスの対応と命令の読み方が無い。直下のファイルがある | §5-0（札・パスと命令の形を固定）・§3（直下は対象外） |
| 必須2 E_old の JSON 全体が無いと sha8 と照らせない。束が未定 | §5-3（JSON 全体・batch の id） |
| 必須3 足す見張りが確認を飛ばす返事を返せる | §5-5・A8・審査役の確認項目 |
| 必須4 試験の名前の決め方で漏れる。改名で抜ける。CI で流れているか未確認 | §5-4（札の tests・`--no-renames`・CI の条件）。CI は Opus が確かめた: 今は流れていない（§6 の末尾） |
| 必須5 HKI-1 が走る前に版を確かめない。CLAUDE_DIR で入れ先を変えられる。見張りごとの install.sh が何でも通る | §6（共通の台本1本・手順2と3・HKI-1 の文）・§5-5（台本の変更は PO の「1」）・A6・A9 |
| 必須6 ADR-1034 との食い違いの扱いが無い | §8-1 |
| 推奨 A2 の記録の形・A6 の止まった判定が無い | §10 の A2・A6 |

### 12-2. クラウドでの設計審査 2回目（2026-11-09 07:41 UTC・opus・読むだけ。判定 REVISE）
| 指摘 | 直したところ |
|---|---|
| 必須1 組の比較が命令の文字列だけ。timeout を縮められる | §5-2・§5-3（全部の欄を比べる）・§5-0（札に書ける欄は type と command だけ）・A3 |
| 必須2 札の名前に `../` を書くと別の見張りを上書きできる | §5-0（相対パスの形・台本と点検の両方で拒む）・A4 |
| 必須3 event に制限が無い。updatedInput などが素通り | §5-0（PreToolUse と Stop だけ）・§5-5（語の一覧。公式の説明で確認）・A8 |
| 必須4 PR 番号の確かめはマージが7日以内でないと通らない。A2 が日付で変わる | §5-5 の 5（時刻の条件）・A2（now を固定）・A10 |
| (3) HKI-1 が改行・`$(`・バッククォートを禁じていない。守りの本体は点検だと書くこと | §6（HKI-1 の文・台本の確かめの限界） |
| 推奨1 変更するファイルを書く | §4 の末尾 |
| 推奨2 「前回から登録済み」は確かめられない | §5-2 |
| 推奨3 CI の条件が注釈の行でも満たせる | §5-4 |

### 12-3. 自己審査（同じ AI。独立した第二者の審査ではない）
- 判定: 3回目のクラウド審査の結果を待つ。
- 残る未確認: HKI-1 の文で、自動判定が AI の実行を実際に通すか（recon 未確認）。これは ADR の承認の後、導入の便で確かめる（A6 と同じ時）。通らなかったときは、K3 を満たせないことを PO に戻す。
