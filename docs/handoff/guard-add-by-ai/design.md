# design: AI が足した見張りを記録できる道（草案・2026-11-09）

状態: 設計案作成済み（第11版。§13 は実装に向けた補足。9回目の審査 REVISE の必須3件・推奨2件を §13-7 と便1カードに反映）／設計審査済み（クラウドでの設計審査 10回目 APPROVE・2026-11-09 09:58 UTC・opus。推奨2件は便1カードに反映済み。§12-11。8回目も APPROVE・08:43 UTC。1〜7回目の REVISE は全部反映済み。8回目の推奨2件も反映済み。§12）／§9 は PO 決定済み（2026-11-09「1」＝案1）／ADR-1072 は PO 承認済み（2026-11-09「1」。承認と実装の開始を選んだ返事）／便1 の実装は G5-4 で NEEDS_DECISION（§12-12 で P の決め方を設計の意図に合わせて直した。実装は出し直し）／便1 の実装 PR はマージ前の審査で REQUEST_CHANGES（§12-13 で入れ替えの条件を足した。便1カード §13 で直す）。／便4（§13-14・第18版。共通の台本の命令の形を見張る install-form-guard。PO 決定 2026-11-10「1」）は設計案作成済み・設計審査待ち。
根拠: recon.md（同じフォルダ）。関係 ADR: ADR-1034・ADR-1033・ADR-1029。

## 1. 目的（PO の言葉から）
- PO の言葉（2026-11-09）:「原則私はエンジニアではないから見張りを足すのはあなたと実行者だけ」。
- 今は、AI が設計し PR で入れた見張りでも、~/.claude に入れるのは PO の `!`、記録には PO の「1」（本文にハッシュの入った同意票）が要る。記録の道が無いので、週次点検で毎回「異常」に出る（11/02・11/09）。
- 目的: 見張りを足す・強める作業は AI だけで最後まで進み、週次点検に異常として出ないこと。見張りを外す・弱める変更は、今までどおり必ず異常として見つかること。

## 2. KGI（PO が週次点検の1行で○×を判定できる形）
| 番号 | 基準 | 今 | 目標 | 測り方 |
|---|---|---|---|---|
| K1 | GitHub main にマージ済みの PR から入れた見張り（足す・組に足す）が、週次点検の `ABNORMAL_REASON=B` に出る件数 | 11/09 で3件 | 導入後の毎週 0件 | 週次点検の出力の B の行を数える |
| K2 | 見張りを外す・組から抜く・PR に無い中身に書き換える・試験を消す・確認を飛ばす返事を足す変更が B に出る割合 | 100%（今は全部出る） | 100% のまま | 試験（A3〜A5・A8・A9・A11・A12）で各1件ずつ作り、全部 B に出ること |
| K3 | 見張りを入れるために PO が `!` を打つ回数 | mac-test-guard で1回 | 0回（導入時の1回を除く） | 新しい見張りの設計書の「導入」の欄に PO の `!` が無いこと |

## 3. 対象と対象外
- 対象: ~/.claude/settings.json の hooks（user:hooks）と ~/.claude/scripts/ の見張りの本体（hook_files）のうち、正本が `scripts/agent-hooks/<名前>/` のフォルダにあり、そのフォルダに台帳札 「guard-manifest.json」（§5-0）があるもの。
- 対象外のまま（B が出る）: `scripts/agent-hooks/` の直下に置かれた見張り（例: master-register-rules-guard.py）、札の無いフォルダ、正本がリポジトリに無い見張り。
- 対象外（今までどおり PO の「1」）: 見張りを外す・弱める変更、permissions.deny / ask / defaultMode、確認を省く設定、autoMode.soft_deny / environment、danger_ops、本番の設定。

## 4. 変更前後
| | 変更前 | 変更後 |
|---|---|---|
| 見張りの正本 | リポジトリの `scripts/agent-hooks/<名前>/`（置き方は見張りごとにばらばら。直下に置いたものもある） | 同じフォルダに台帳札 「guard-manifest.json」 を置いたものだけが対象（§5-0） |
| ~/.claude へ入れる台本 | 見張りごとの install.sh を PO が `!` で流す | 全部の見張りで共通の台本 `scripts/agent-hooks/install-guard.sh <名前>` を1本だけ使う。Opus か実行役が流す。自動判定の例外 HKI-1 で通す（§6） |
| 台帳への記録 | PO の「1」で `consent:` の record（無いと B） | 共通の台本が最後に `perm-change.py record --po-ref PR#<n>` を書く（§6） |
| 点検の確かめ | user:hooks・hook_files の PR 番号は通らない（consent-audit.py:906） | 「強める変更」に限り PR 番号で通す（§5） |
| 外す・弱める | PO の `!`＋「1」 | 変わらない |
| 共通の台本そのものの変更 | （無い） | PO の「1」が要る（§5-5） |

変更するファイル（実装の便で触るもの。これ以外は触らない）:
- `scripts/dev/consent-audit.py`: §5 の分岐を足す。今の hook_files の要素は `sha8(相対パス)|中身8桁` でパスそのものを持たない（consent-audit.py:656）ので、札からパスを引く処理を足す。
- `scripts/dev/perm-change.py`: record に `--replaced-by`・`--batch`・`--old-json` を足す（今の record の引数は perm-change.py:739-745 で、この3つは無い）。
- 「scripts/agent-hooks/install-guard.sh」（新規）と、その試験。
- 「scripts/agent-hooks/mac-test-guard/guard-manifest.json」（新規。1つ目の対象）。
- `.github/workflows/agent-hooks-test.yml`: mac-test-guard の試験と install-guard.sh の試験を足す。checkout（今の :23・:34。fetch-depth の指定が無く浅い取得）に `fetch-depth: 0` を足す（§5-1〜5-4 の一覧の 6 が履歴を読むため）。
- `scripts/dev/permission-delegation-tests.py`: A1〜A5・A7〜A12 の試験を足す。
- 審査役（reviewer）の定義 `.claude/agents/reviewer.md`（リポジトリの版）: §5 の末尾の確認項目2行を足す。理由: 公式の説明（code.claude.com/docs/en/sub-agents の優先順位の表）では、同じ名前の担当はプロジェクトの `.claude/agents/`（優先3）が利用者の `~/.claude/agents/`（優先4）より優先される。リポジトリには ほかに `docs/agents/reviewer.md`（GPT 向けの古い説明。担当として読まれない）がある。~/.claude の版は AI は変えない。

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
- 点検と台本が読む札は、PR #n のマージの版の札（`git show <PR #n のマージ>:scripts/agent-hooks/<name>/guard-manifest.json`）。今の main の札や、手元の写しの札は読まない。札が無い版を指す PR 番号なら B（台本も止まる）。例外は §5-4 の試験の検査だけで、そこでは「前に入れていた版」（一覧の 6）の札も読む。前に入れていた版に札が無ければ、中身の書き換え（4.）は B（今の review-gate・confidential-quote-guard がこれに当たる）。札を足す PR では本体を変えない（札だけを足し、本体の直しは次の PR にする）。
- `hooks[].after` は並べる位置の目印で、パスではない。書けるのは、既にある命令の末尾のファイル名（`/` を含まない。形は `^[A-Za-z0-9_.-]+$`）。例: 「mac-vm-guard.py」。台本は、同じ event と matcher の組で、命令の末尾がこの名前のフックの直後に足す。見つからなければ組の最後に足す。点検は `after` を判定に使わない（足した位置は §5-3 の「同じ順」で確かめる）。
- `files`・`tests`・`hooks[].file` に書ける名前は、フォルダの中の相対パスだけ。形は `^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$` で、`..` の区切りと `/` で始まる名前は拒む（例: 「../review-gate/gate.py」 と書いて別の見張りのファイルを上書きする道をふさぐ）。台本と点検の両方で拒み、拒んだら台本は止まり、点検は B にする。
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
   - 比べる元 P は「前に入れていた版」のマージ（一覧の 6 で決める）。比べる先は PR #n のマージ。試験の範囲 T は、P の版の札の `tests` と PR #n の版の札の `tests` を合わせたもの（間の PR で札から名前だけ消してから、次の PR で試験を消す道をふさぐ）。
   - `git diff --no-renames <P> <PR #n のマージ>` で、T のファイルに `-` の行が0行。
   - P の版の札の `tests` にあって PR #n の版の札の `tests` に無い名前が0件。
   - PR #n の版の札の `tests` の全部が、GitHub main の `.github/workflows/agent-hooks-test.yml` の jobs の steps の `run:` の行で呼ばれている（注釈の行は数えない。YAML として読み、`run` の値の中に試験のパスがあること）。
   - 試験を足す行だけで無効にする道の検査: 同じ diff で T のファイルの `+` の行に、語の区切りつきで（正規表現の `\b` は、語の端が英数字のときだけその側に付ける。`skip` は前後に付けるので `skipping` は当たらない。`exit(0)` は前にだけ付けるので行末の `sys.exit(0)` にも当たる）`skip`・`xfail`・`exit 0`・`exit(0)`・`set +e` の語が1つでもあれば B。今ある行（test_review_gate.sh:53・:356 の `exit 0` など）は `+` の行にならないので当たらない。今ある試験の書き方で行を足すと B になるが、これは安全側として受け入れる（PO の「1」で記録する）。
   - CI の検査（GitHub main の agent-hooks-test.yml を YAML として読む）: T の試験を呼ぶ step の `run` の値に `|| true`・`|| :`・`; true`・`|| exit 0`・`set +e`・` -k `・`--deselect` があるもの、その step か job に `continue-on-error: true` があるもの、その step か job の `if:` があるもの（今の agent-hooks-test.yml の試験の step と job には `if:` が無い）は B。
   - この2つで見つからない書き方（早い `return`、T に入らない補助ファイルの書き換え、文字列を組み立てて隠す書き方）は、審査役の確認項目と §8 の 1 の受け入れたリスクで持つ。
5. 時刻の条件（§5 の分岐だけに使う）: 今の PR 番号での確かめは「マージの時刻が、前回の写しの時刻（since。保留の行は held_ts）より後」を求める（consent-audit.py:911-913）。このため、前回の点検の後に入れても、マージが前回の点検より前なら通らない。§5 の分岐ではこれを使わず、次の2つにする。
   - PR #n のマージの時刻が、record の行の時刻より前。
   - record の行の時刻が、前回の写しの時刻（since。保留の行は held_ts。今の consent-audit.py:912 と同じ選び方）より後で、点検の now より前。now は今の record_ok（consent-audit.py:878）に引数が無いので、run_permissions（:997）から渡し足す。
   これで、前回の点検より前にマージされ、後から入れた見張りも、入れた週の点検で B に出ない。古い PR 番号を後から何度も使う道は、§8 の 5（同じ po_ref と item_hash の組は1回）と、下の 6 でふさぐ。
6. いちばん新しい版の条件（古い版へ戻して弱める道をふさぐ）:
   - PR #n は、record の行の時刻の時点で、GitHub main で `scripts/agent-hooks/<name>/` を最後に変えたマージであること（`git log --first-parent origin/main --until=<行の時刻> -1 --format=%H -- scripts/agent-hooks/<name>/` が PR #n のマージと同じ）。古い PR 番号（例: v1 を入れた PR#a）で、後の版（v2）から古い版へ戻すことはこれで通らない。
   - 4. の試験の比べる元（P）は、PR #n の1つ前のマージではなく、前に入れていた版にする。新しく足す見張り（前回の写しに同じパスが無い）は 4. に当たらないので P は要らない。点検は、前回の写しの hook_files の同じパスの中身8桁を、main の `scripts/agent-hooks/<name>/` の履歴（first-parent のマージ）から探し、見つかったマージから PR #n のマージまでの差分で 4. を確かめる。同じ中身が複数のマージにあるときは、PR #n から first-parent を遡って最初に当たったマージから、同じ中身が途切れずに続く範囲のいちばん古いマージを使う（間に札だけを変えた PR があっても、それを P にしない。§12-12）。前に入れていた版が main の履歴に無ければ B。
   - 履歴が浅い取得（`git rev-parse --is-shallow-repository` が true）のときは、この条件を確かめられないので、台本は止まり、点検は B にする。
   - 古い版の中身を新しい PR でもう一度入れ直す（戻す PR）は、この条件では通る。試験の行が消えていれば 4. で B になる。試験を残したまま本体だけ戻すものは、審査役の確認項目と §8 の 1 の受け入れたリスクで持つ。

### 5-5. 強める変更とは数えないもの（必ず B）
- 本体の中に、確認を飛ばす返事や、実行する中身を書き換える返事を返す処理があるもの。点検は札の `files` と `hooks[].file` にあるファイルだけを読む（`tests` の試験ファイルは読まない。試験は止める見本として `--approve` などを書くことがあるため）。語は大文字と小文字を区別して当てる（`APPROVE` の文を出す review-gate を誤って止めないため）。次のどれかが1行でもあれば B にする（台本も同じ検査で止まる）。
  - 3回目の審査での実測（2026-11-09・大文字小文字を区別しない git grep）: mac-test-guard は0件。review-gate は gate.py の `APPROVE` の文で10行（4回目の審査で数え直し。大文字小文字を区別すると0件。gate.py:7・:48・:50 は大文字の `APPROVE`）。confidential-quote-guard は本体の guard.py が0件で、試験 tests/test_guard.py:401 の `--approve` だけ。上の当て方なら、どれも B にならない見込み。実装の便で A8 の2件目の試験として確かめる。
  - `permissionDecision` と `allow` が同じ行にある。
  - `approve` の語がある。
  - `updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext` の語がある。
  語の一覧の根拠は Claude Code の公式の hooks の説明（code.claude.com/docs/en/hooks。Context7 `/websites/code_claude` で 2026-11-09 に確認）: PreToolUse は `updatedInput` で実行する中身を差し替えられる。PermissionRequest は `decision.behavior: "allow"` で確認を代わりに通し、`updatedPermissions` で許可を足せる。PostToolUse は `updatedToolOutput` で結果を差し替えられる。文字列を組み立てて隠す書き方は機械では見つけきれないので、審査役の確認項目（下）と ADR の受け入れたリスクで持つ。
- 共通の台本 「install-guard.sh」 と点検の判定の部分（consent-audit.py の §5 の分岐）を変える PR。台帳に置いた台本の sha256 と GitHub main の台本が違えば B。PO の「1」で台帳の値を更新する。
- 札の `files` や `hooks` から消えた名前があるもの（外す変更）。

あわせて、PR #n は ADR-1029 の審査（新しく起動した opus の審査役の APPROVE）を通ってマージされていることを条件にする（既にマージの見張りで強制されている）。審査役の確認項目に2行を足す。「この PR は見張りの止める範囲を狭めていないか」「確認を飛ばす返事（allow・approve）を返す道を作っていないか」。

## 6. 入れる道（共通の台本 install-guard.sh）
- 置き場所は 「scripts/agent-hooks/install-guard.sh」（1本だけ）。見張りごとの install.sh は作らない。既にある mac-test-guard・confidential-quote-guard・review-gate の install.sh は残すが、AI は流さない（HKI-1 の対象外）。
- 台本の手順（どこか1つでも失敗したら settings.json に触らず `INSTALL_FAILED:` で止まる）:
  1. 引数は名前1つだけ。`^[a-z0-9-]+$` に合わない・フォルダや札が無い・引数が2つ以上なら止まる。
  2. 入れ先は `$HOME/.claude` に固定する。環境変数 CLAUDE_DIR は読まない（今の mac-test-guard/install.sh:8 の形を使わない）。
  3. 走らせる前に、~/.salesanchor-tools が変更なし（`git status --porcelain` が空）で、HEAD が `git ls-remote origin refs/heads/main` と同じで、浅い取得でない（`git rev-parse --is-shallow-repository` が false）ことを確かめる。
  4. §5-5 の確認を飛ばす返事の検査を正本に当てる。
  5. 札の `files` を `~/.claude/scripts/<name>/` へ写し、原本と比べ、読み取り専用にする。
  6. 札の `tests` を写した先に向けて流す。
  7. settings.json の控えを取り、札の `hooks` の命令を足す（`after` の命令の直後。既にあれば足さない）。外す処理は持たない。
  8. JSON として読み直してから置き換える。
  9. PR 番号は `git log --first-parent origin/main -1 --format=%s -- scripts/agent-hooks/<name>/` の「Merge pull request #n」から取る。取れなければ記録せず止まる。
  10. 変わった要素ごとに `perm-change.py record --po-ref PR#<n>` の行を書く（§5-3 の batch と E_old の JSON を含む）。
- 自動判定の例外 HKI-1（PO が導入時に `!` で1回だけ足す。ADR-1034 の PDL-1 と同じ形）: 文の正本は §6-1 の引用ブロック（足す台本が実行のたびにそこから読む）。
- 台本の版の確かめ（手順3）は台本が自分で行う。書き換えられた台本は、その確かめも飛ばせる。外す・弱める変化を最後に見つけるのは週次点検だけ（台本の変更は §5-5 で B、settings.json と本体の変化は §5 に当たらなければ B）。台本の確かめは事故を防ぐためのもので、守りの本体は点検である。
- 今週の3件は記録し直さない: 11/09 の週次点検で写しが確定済み（~/.claude/logs/permission-snapshot.json の更新 2026-11-09 14:01 JST。`29ac3748` と `3ba846f5` がそれぞれ1件入っていることを Opus が grep で確認）。来週の点検では差として出ないので、後から記録しても使われない。3件は 11/09 の点検の記録に B として残したままにする（中身は外す・弱める変化0件と調べ済み。~/CC報告ファイル-keep/consent-weekly/20261109-inject-analysis.md）。
- 実物で初めて通す確かめ（K1 の最初の1回）は、札を足す PR を共通の台本で入れたときに行う。mac-test-guard は中身が変わらないので hook_files・user:hooks の差は出ず、記録の行も書かれない（台本は「差が無い」と出して終わる）。差が出る最初の見張りの導入で K1 を測る。
- 1つ目の対象は mac-test-guard。札を足す PR で、test_guard.py を CI（agent-hooks-test.yml）に足す。今の CI が流しているのは review-gate と master-register の試験だけ（.github/workflows/agent-hooks-test.yml:25・:36。mac-test-guard と confidential-quote-guard の試験は呼ばれていない。Opus が 2026-11-09 に `git grep agent-hooks origin/main -- .github/workflows/` で確認）。

### 6-1. 自動判定の例外 HKI-1 の文（正本。PO が `!` で足す・外す台本がここから読む）
- 足す: `bash ~/.salesanchor-tools/docs/handoff/guard-add-by-ai/po-register-hki.sh consent:<鍵>`。外す: 同じフォルダの `docs/handoff/guard-add-by-ai/po-unregister-hki.sh`（§8 の戻し方）。どちらも PDL-1 の台本と同じ形（控え→変更→読み直し→台帳に record）。
- 下の1行は行頭から書く。台本はこの節の中で行頭が `> HKI-1:` の行を1つだけ探す。2つ以上・0なら何も変えずに止まる。文を変えると item_hash が変わるので、変えるときは設計の改版として扱う。

> HKI-1: Allowed only for a Bash command that is exactly `bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <name>` on a single line, where `<name>` matches `^[a-z0-9-]+$`, with no other arguments, no environment variable prefix (for example `CLAUDE_DIR=`), no pipe, no `;`, `&&` or `||`, no newline, no `$(`, no backquote, and no redirection. The script itself refuses to run unless ~/.salesanchor-tools is clean and equal to GitHub main. It only adds guard hooks listed in a reviewed and merged guard-manifest.json; it never removes or loosens hooks. Running any per-guard install.sh or rollback.sh, any other script under ~/.salesanchor-tools or ~/.claude, or editing settings files directly is still Self-Modification.

## 7. 代替案
| 案 | 中身 | 採らない理由 |
|---|---|---|
| A 今のまま | PO の `!` と「1」 | PO の原則に反する。毎週異常が出て、本当の異常が埋もれる |
| B 見張りは全部 PR 番号で通す | 外す変更も通す | Opus は自分でマージできるので、見張りを外すことも AI だけで済む。ADR-1034 が閉じた穴が開く |
| C 点検から見張りを外す | 数えない | 弱める変更も見つからなくなる |
| D1 見張りごとの install.sh を例外で通す（第1版） | 名前の形だけで通す | 1回目の審査で不採用。Opus が自分でマージした install.sh なら中身を問わず通り、外す処理も入れられる |
| D2（採る） 共通の台本1本＋台帳札＋強める変更だけ PR 番号で通す | §5・§6 | 台本は1本に固定して PO の「1」で守る。見張りごとに変わるのは札と本体だけで、点検が機械で判定できる |

## 8. リスクと対処
1. 試験を消さずに、本体だけで止める範囲を狭める。または、§5-4 の語と CI の検査に当たらない書き方（早い `return`、T に入らない補助ファイルの書き換え、文字列を組み立てて隠す書き方）で試験を無効にする。対処: §5-4 の試験の条件（CI で流れる試験に限る・語と CI の検査）と審査役の確認項目。残る分は受け入れたリスクとして ADR に書く。
2. 本体に確認を飛ばす返事・中身を書き換える返事を隠して入れる（文字列を組み立てるなど）。対処: §5-0 の event の一覧と §5-5 の機械の検査と審査役の確認項目。残る分は ADR に書く。
3. 見張りの本体はフックとして何でも実行できる（設定ファイルを書き換える処理を入れるなど）。対処: 審査役の確認項目と週次点検（設定の変化は今までどおり B に出る）。残る分は ADR に書く。
4. HKI-1 の文が広く読まれ、ほかの台本まで通る。対処: 命令の形を1つに固定し、台本の中でも版を確かめる。導入後に A6 で、通らないことを確かめる。
5. 1つの PR を何度も使う。対処: 今の「同じ po_ref と item_hash の組は1回」をそのまま使う（permission-delegation/design.md:195）。
6. 審査役が中身を読まずに APPROVE できる（ADR-1029:40）。Opus は自分でマージできる。対処: この2つは新しい ADR に受け入れたリスクとして書き、PO の承認を取る。
- 戻し方: HKI-1 を外す台本（PO の `!`）と、consent-audit.py の §5 の分岐を元に戻す PR。共通の台本で入れた見張りを外すのは、今までどおり見張りごとの rollback.sh を PO の `!` で流す。

### 8-1. ADR の扱い
- 新しい ADR（ADR-1072・起案済み・Proposed）を起こし、ADR-1034 の決定2（見張りは R4。PR 番号で説明できるのは repo の settings.json だけ。ADR-1034:16・:34）を一部改める。改めるのは「§5 の強める変更に限り、user:hooks と hook_files も PR 番号で説明できる」の1点だけ。外す・弱める・共通の台本の変更は ADR-1034 のまま。
- Why に書くこと: PO の言葉（2026-11-09）、毎週の B（11/02・11/09）、§8 の受け入れたリスク 1・2・3・6。
- この ADR が PO に承認されるまで、実装の便は出さない。

## 8-2. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。社内の決まり（誰が確認するか）の変更で、外の数値が設計の正しさを示さないため。
- 過去事例: 11/02 と 11/09 の週次点検で、AI が PR で入れた見張りが毎回 B に出た（recon.md の観測した事実 1・5）。応用: §5 の機械の判定で、足す・強める変更だけを PR 番号で通す。

## 9. PO の決定（2026-11-09。PO の返事「1」＝下の案1）
見張りの「中身の書き換え」を AI の確認だけで記録してよいか。
- 案1（採用）: 試験の行が1行も消えていない直しは AI で記録。試験を消す・変える直しと、外す変更は PO の「1」。
- 案2: 足す変更だけ AI で記録。中身の直しは全部 PO の「1」。
- 案3: 外す変更も含めて全部 AI で記録。

## 10. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| A1 §5-1〜3 を満たす増・入れ替えが B に出ない | 試験（一時の HOME と一時の git リポジトリ。既存の permission-delegation-tests.py に足す） |
| A2 今週の3件と同じ形の3行（試験の中で作る）が記録で説明でき、B が0件 | 一時の HOME で、下の3行を一時の台帳に書いて点検を流す（`--commit-snapshot` なし）。点検の基準の時刻は固定する（前回の写しは commit=True・now=2026-11-09T04:00:00Z で取る。点検は run_audit の now を 2026-11-09T07:00:00Z にして呼ぶ。record の行の時刻は 2026-11-09T06:00:00Z）。流す日によって結果が変わらないこと。一時の git リポジトリに、今の main の mac-test-guard（#5049 の版・0e82884f7）に札を足したマージ PR#m を作る（マージ時刻は 2026-11-09T05:00:00Z）。一時の HOME の settings.json に、前の組（mac-vm-guard.py だけ。命令のパスは一時の HOME で書く）を置いて前回の写しを取る。次に、共通の台本の手順1〜8（写す・比べる・試験・settings に足す）と同じことを試験が行い、mac-test-guard を入れる（A2 では台本の手順10の記録は使わない。台本は perm-change.py を実時間で呼ぶため、行の時刻を固定できない。perm-change.py:759。台本に時刻を入れる口は作らない）。下の3行は、試験が `perm-change.main(["record", ...], home=<一時の HOME>, now=2026-11-09T06:00:00Z)` で書く（perm-change.py:755 は now を引数で受ける）。そのあと点検を流す。点検に渡す gh_view は偽物で、PR#m について `state=MERGED`・`mergedAt=2026-11-09T05:00:00Z`・`mergeCommit.oid=<一時のマージの sha>` を返す（consent-audit.py:909-916）。git_run は一時の git リポジトリに向ける。台本が実時間で記録する流れは A7 で確かめる。組と本体の sha8 は一時の HOME のパスで決まるので、行に書く値は試験の中で計算する（本番の `3ba846f5`・`062521a7` は使わない。本番の HOME とパスが違うと値が変わるため。consent-audit.py:457-459・:589）。行は3種: ① hook_files の増を PR#m ② user:hooks の増の組を PR#m・batch X ③ 前の組の減を PR#m・batch X・`--replaced-by <増の組の sha8>`・前の組の JSON。B が0件。あわせて、札の無い版（#5049 相当）の番号で書いた行は B になることを1件確かめる |
| A3 組から命令を抜く入れ替え・既にあるフックの `timeout` を縮める入れ替えが B | 試験（2件） |
| A4 PR に無い中身・札の無いフォルダ・`scripts/agent-hooks/` の直下のファイル・札に `../` や `/` で始まる名前を書いたもの・`PreToolUse` と `Stop` 以外の event が B（台本も止まる） | 試験（5件） |
| A5 札の `tests` に `-` の行がある PR・`tests` から名前が消えた PR・CI で呼ばれていない試験での中身の書き換え・2段の PR（PR#b で札から試験 t2 の名前だけ消し、入れない。PR#c で本体を変え t2 も消し、PR#c で入れる）・前に入れていた版に札が無い見張りで、札を足す PR が本体も変え試験を札に書かずに消したもの が B | 試験（5件） |
| A12 試験を足す行だけで無効にした PR が B。`skipping` の語だけの行は B にしない | 試験（7件: T の `+` の行に `skip`／T の `+` の行に `exit 0`／`run` に `|| true`／step に `continue-on-error: true`／step に `if: false`／T の `+` の行の末尾に `sys.exit(0)`／止めない見本: T の `+` の行に `skipping` だけ） |
| A6 AI が、見張りごとの install.sh・rollback.sh・`CLAUDE_DIR=` を前に付けた共通の台本・引数2つの共通の台本を走らせると止まる | 導入後に1回ずつ試す。止まったと判定する条件: Bash の結果が拒否で返り、settings.json の sha256 が試す前と同じ。4件の結果を keep に残す |
| A7 共通の台本が足すだけで、2回流しても命令は1件・台帳の行も1組 | 試験 |
| A8 §5-5 の語の一覧のどれかを、札の `files` か `hooks[].file` に含む見張りは、台本が止め、点検も B にする。試験ファイルだけにある語・大文字の `APPROVE` では止めない | 試験（語ごとに1件の7件: `permissionDecision` と `allow`・`approve`・`updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext`。止めない見本2件: 試験ファイルの `--approve`・本体の `APPROVE`。今の mac-test-guard・review-gate の gate.py・confidential-quote-guard の guard.py を当てて0件の1件） |
| A9 共通の台本が、~/.salesanchor-tools に変更がある・main と版が違う・名前の形が違うときに止まる | 試験（3件） |
| A10 前回の写しの時刻より8日前にマージし、写しの後で入れた見張りが、入れた週の点検で B に出ない。record の行の時刻がマージより前なら B | 試験（2件。now を固定する） |
| A11 古い PR 番号で古い版へ戻すと B。前に入れていた版が main の履歴に無いときも B | 試験（2件。一時の git リポジトリに v1（PR#a）・v2（PR#b）の2つのマージを作り、v2 を入れた後で v1 の中身を PR#a で記録する。もう1件は履歴に無い中身から書き換える）。あわせて、浅い取得の写しで台本が止まり点検が B になることを1件 |

## 11. 維持の仕組み
- 守り手: scripts/dev/consent-audit.py（週次点検。§5 の判定をここに置き、K1・K2 を毎週出す）
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
| 必須4 PR 番号の確かめはマージが7日以内でないと通らない。A2 が日付で変わる | §5-1〜5-4 の一覧の 5（時刻の条件）・A2（now を固定）・A10 |
| (3) HKI-1 が改行・`$(`・バッククォートを禁じていない。守りの本体は点検だと書くこと | §6（HKI-1 の文・台本の確かめの限界） |
| 推奨1 変更するファイルを書く | §4 の末尾 |
| 推奨2 「前回から登録済み」は確かめられない | §5-2 |
| 推奨3 CI の条件が注釈の行でも満たせる | §5-4 |

### 12-3. クラウドでの設計審査 3回目（2026-11-09 07:52 UTC・opus・読むだけ。判定 REVISE。2回目の指摘は全部直っていると確認）
| 指摘 | 直したところ |
|---|---|
| 必須1 古い PR 番号で古い版へ戻す道がある。試験の比べる元が PR の1つ前の版 | §5-1〜5-4 の一覧の 6（いちばん新しい版の条件・比べる元は前に入れていた版）・A11 |
| 必須2 語を当てるファイルの範囲と大文字小文字の扱いが無い。今の見張りを B にしうる | §5-5（札の files と hooks[].file だけ・大文字小文字を区別する・実測）・A8 |
| 推奨1 A10 が §4 の一覧に無い・表の順・§12-2 の書き方 | §4（A1〜A5・A7〜A11）・§10 の表の順・§12-2 |

### 12-4. クラウドでの設計審査 4回目（2026-11-09・opus・読むだけ。判定 REVISE。3回目の指摘は全部直っていると確認。6 の抜け道の確かめ（行の時刻は偽れない・同じ秒のマージも順が決まる・main の書き換えは B 側に倒れる）と、今の3つの見張りが B にならないことも確認）
| 指摘 | 直したところ |
|---|---|
| 必須1 札をどの版から読むかが無い。#5049 には札が無く、札を足す PR が最後のマージになるので A2 が成り立たない | §5-0（PR #n のマージの版の札だけ）・§6（今週の3件は札を足す PR の番号で記録）・A2（札を足した一時のマージで試す・札の無い版は B） |
| 推奨1 浅い取得だと 6 を確かめられない。CI の checkout に fetch-depth が無い | §5-1〜5-4 の一覧の 6（浅い取得なら止まる・B）・§4（fetch-depth: 0）・A11 |
| 推奨2 前に入れていた中身が複数のマージにあるときの選び方が無い | §5-1〜5-4 の一覧の 6（PR #n から遡って最初のもの） |
| 事実の直し §5-5 の「26行」は誤り | §5-5（10行・区別すると0件） |

### 12-5. クラウドでの設計審査 5回目（2026-11-09 08:11 UTC・opus・読むだけ。判定 REVISE。4回目の指摘は全部直っていると確認）
| 指摘 | 直したところ |
|---|---|
| 必須1 試験の検査の比べる元が版ごとに違う。2段の PR で試験を消せる | §5-0（例外）・§5-4（P と T・両方の札の tests を合わせる）・一覧の 6・A5 |
| 必須2 A2 の値が本番の HOME のパスに縛られ、一時の HOME では合わない | A2（値は試験の中で計算する） |
| 必須3 札の見本の `after` がフォルダの外のファイル名で、相対パスの決まりと合わない | §5-0（`after` は並べる目印。`/` を含まないファイル名） |
| 推奨 行番号の誤り（:900-901・:701） | §5 一覧の 5（:911-913・since より後）・§4（:656） |
| 未確認 11/09 の点検で写しが確定済みなら3件を記録しても使われない | Opus が確認: 確定済み（14:01 JST の写しに2つの値が入っている）。§6（記録し直さない・K1 は差が出る最初の導入で測る） |

### 12-6. クラウドでの設計審査 6回目（2026-11-09 08:19 UTC・opus・読むだけ。判定 REVISE。5回目の指摘は全部直っていると確認。時刻の条件は consent-audit.py:1033・:878・:997 で実装できると確認）
| 指摘 | 直したところ |
|---|---|
| 必須 前に入れていた版に札が無いと、試験の範囲が PR #n の札だけになり、札を足す PR で本体を変え試験を消すと通る | §5-0（札の無い前の版からの書き換えは B・札を足す PR では本体を変えない）・A5（5件目） |
| 推奨 試験に `-` の行を出さず、足す行（skip など）や `|| true` で試験を無効にできる | §5-4（語の一覧の検査を足す・残りは受け入れたリスク）・A12 |
| 推奨 保留の行で since の代わりに held_ts を使うかが無い | §5 一覧の 5（held_ts・now の渡し方） |
| 推奨 A2 の前回の写しを取る時刻が無い | A2（2026-11-09T04:00:00Z に固定） |
| 言い方 A2 の見出しの「今週の3件」が §6 の「記録し直さない」と合わない | A2（「今週の3件と同じ形の3行（試験の中で作る）」） |

### 12-7. クラウドでの設計審査 7回目（2026-11-09 08:34 UTC・opus・読むだけ。判定 REVISE。6回目の指摘は全部直っていると確認。今の CI と試験を誤って止めないと確認）
| 指摘 | 直したところ |
|---|---|
| 必須 A2 の行を台本で書くと実時間になり、行の時刻 06:00Z を満たせない | A2（入れる作業は試験が台本の手順1〜8と同じことを行い、3行は試験が perm-change.main に now=06:00Z を渡して書く。台本の記録は A7 で確かめる） |
| 推奨 `if:`・`|| exit 0`・`set +e`・`-k`・`--deselect` が検査に当たらない。`skip` が `skipping` にも当たる | §5-4（語は区切りつき・CI の検査に足す・残りの書き方を §8 の 1 に明記） |
| 推奨 A12 が §4 の試験の担当と K2 に無い | §4・K2 |

### 12-8. クラウドでの設計審査 8回目（2026-11-09 08:41 UTC・opus・読むだけ。判定 APPROVE。7回目の指摘3件は直っていると確認。perm-change.py:755・:785・:668 で A2 の行が書けると確認。今の CI と試験を誤って止めないと確認）
| 推奨 | 直したところ |
|---|---|
| 推奨1 `exit(0)` に後ろの `\b` を付けると行末の `sys.exit(0)` を見逃す（実際に流して確認） | §5-4（`\b` は語の端が英数字の側だけ）・A12（`sys.exit(0)` の1件） |
| 推奨2 A2 で gh_view を偽物で返すことが無い | A2（偽の gh_view の返す値と git_run の向け先） |

### 12-9. 自己審査（同じ AI。独立した第二者の審査ではない）
- 判定: APPROVE（8回目のクラウド審査の APPROVE に、推奨2件の反映を足したもの。推奨の反映は判定を変えない文の足しだけ）。
- 実装へ進む前に要るもの: ①ADR-1034 の決定2を一部改める ADR の起案と PO の承認（§8-1） ②実装カード ③PO の実装の承認。
- 手元での語の一覧の数え直しは、review-gate の見張りに止められたので行っていない（審査役の記録の台本に触れる形になったため。言い換えはしていない）。根拠は3回目の審査の実測だけで、A8 の試験で確かめる。
- 残る未確認: HKI-1 の文で、自動判定が AI の実行を実際に通すか（recon 未確認）。これは ADR の承認の後、導入の便で確かめる（A6 と同じ時）。通らなかったときは、K3 を満たせないことを PO に戻す。

### 12-10. クラウドでの設計審査 9回目（2026-11-09 09:41 UTC・opus・読むだけ。対象は §13 と便1カード。判定 REVISE。カードの §0 の14行は実物と全部同じと確認）
| 重さ | 指摘 | 直したところ（Opus が実物で確かめてから直した） |
|---|---|---|
| 必須 | 新しい2キーで、既にある試験 A5-0（tests:503 の数 24）と mutate（tests:475 の `split(":")`）が壊れる | §13-7・カード §7・§8・§9（例外2か所だけ変える） |
| 必須 | `--until` は commit の日時で選ぶが、merge_pr（tests:565）は今の時計で commit する | §13-7・カード §7（git_at・merge_pr_at） |
| 必須 | `rsplit("\|", 2)` だと matcher に `\|` を含む組を取り違える | §13-7・カード §5-5 の 9. |
| 推奨 | 印の外の部品を書き換えると、判定を弱めても guard_judge が変わらない | §13-7・カード §5-5 の 0. |
| 推奨 | 使う op を明記し、挙げていない組は False | §13-7・カード §5-5 の 0. |

### 12-11. クラウドでの設計審査 10回目（2026-11-09 09:58 UTC・opus・読むだけ。対象は §13 と便1カード a67d3057a。判定 APPROVE）

- 9回目の必須3件・推奨2件は全部 ○。§0 に足した4行（tests:80・475・503・565）は実物と一致。
- main 98a4fb4c5 の写しにカードどおり足して試験を流した結果: PASS=391 FAIL=4。元の main は PASS=389 FAIL=4。増えた2件は A5-guard_installer と A5-guard_judge（どちらも B が出て PASS）。FAIL 4件（A10-a・A10-b・test_a10・A14）は元の main でも同じで、写しの置き方によるもの。
- commit の日時を 05:00Z に固定したマージは `--until=06:00Z` で出て、`--until=04:59Z` で出ないことを一時のリポジトリで確かめた。

| 重さ | 指摘 | 直した場所 |
|---|---|---|
| 推奨 | 印の外で呼んでよい部品が「標準ライブラリだけ」で、9. の PyYAML と食い違う | 便1カード §5-5 の 0.（PyYAML の `yaml` を足した） |
| 推奨 | 1つの環境で2回マージすると、枝の名前が同じ "feat" のため `checkout -b` が失敗する | 便1カード §7（2回目から別の branch 名を渡す） |

### 12-12. 便1 の実装で見つかった食い違い（2026-11-09 10:16 UTC・クラウドの実装役が NEEDS_DECISION で停止）

- 事実: 試験 G5-4（A5 の「2段の PR」）だけが FAIL（変えた後 PASS=553 FAIL=1。変える前の main は 494/0）。原因は P の決め方。§13-4 と便1カードは「中身8桁が同じ最初の版」としていたため、札だけを変えた PR#b（本体の中身は PR#a と同じ）が P になり、T に t2 が入らなかった。
- §5-4 の本文は P を「前に入れていた版」とし、T を P と mc の札の和にして2段の PR をふさぐと書いている。食い違いは §13-4 の細部の側。
- 決定（Opus。PO が承認した設計の意図に合わせる直しで、方向は変えない）: 同じ中身が途切れずに続く範囲のいちばん古い版を P にする（実装役の案 a）。これで P は PR#a になり、カード §5-5 9. の「P の札の tests にあって mc の札の tests に無い名前があれば False」が当たって B になる。
- 案 b（札の tests から名前が消える変更自体を B）を選ばなかった理由: 同じ検査がカードに既にあり、P を正しく決めれば当たる。検査を2つに増やさない。
- 中身の書き換えを挟んで札だけ変えた版を入れる道（PR#b1 で札から t2 を消し本体も少し変えて入れる）は、そのときの P が PR#a になり同じ検査で B になる。
- 確かめ方: 出し直す実装で G5-4 を含む全試験が PASS になること。マージ前に新しい opus の審査役が直しを読む。
- 影響: §5-1〜5-4 の一覧の 6・§13-4・便1カード §5-5 9. の P の1行だけ。A11 の古い版へ戻す道は 8.（いちばん新しい版）で止めており、P の決め方とは別。

### 12-13. 実装 PR のマージ前の審査で見つかった穴（2026-11-09・新しく起動した opus の審査役・判定 REQUEST_CHANGES）

- 事実（審査役の指摘を Opus が実装の枝の consent-audit.py で読んで確かめた）: user:hooks の増の組を「入れ替え」（§5-1〜5-4 の 3.）で通す道は、同じ PR 番号で `replaced_by` が増の組の sha8 と同じ減の行があり、`_ga_user_remove` が通れば True を返す。`_ga_user_remove` は、減の行の `old_json` の sha8 が行の item_hash と同じことと、増の組が old_json の命令を同じ順に含むことしか見ていない。その old_json の組が前回の写しに本当にあり、今週の差分で減ったことは、どこでも確かめていない。
- 抜け道: 札のある見張りを PR でマージしたあと、settings.json に `[任意の命令, 見張りの命令]` の新しい組を足し、record で「増の行」と、存在しなかった組 `[任意の命令]` を old_json に書いた「減の行」を書く。点検の差分は増の1件だけで、増は入れ替えの道で通る。偽の減の行は、対応する減の要素が無いので一度も判定されない。B は0件になる。任意の命令は §5-5 の語の検査（札のファイルだけに当てる）にも、perm-change.py の秘密の値の検査にも当たらない。
- 原因: §5-1〜5-4 の 3. は「減の組 E_old と増の組 E_new が同じ束にある」とだけ書き、E_old が今週の差分の減の要素であることを条件にしていなかった。§13-4 の「減の要素が説明できなければ B が出るので、増だけを記録して逃げる道は無い」は hook_files の話で、user:hooks の入れ替えには当てはまらなかった。設計の入れ忘れが原因。
- 決定（Opus。ADR-1072 の「当たらない変化は今までどおり B」に合わせて条件を足す直しで、方向は変えない）:
  1. 増の組を入れ替えで通すときは、減の行の `<event>|<matcher>|<item_hash>` が、今週の差分の user:hooks の減の要素に入っていること。
  2. 減の組を入れ替えで通すときは、`<event>|<matcher>|<replaced_by>` が、今週の差分の user:hooks の増の要素に入っていること（左右を同じ厳しさにする）。
  3. 差分の要素の一覧は、点検（run_permissions）が判定に渡す。渡されないときは、入れ替えの道を通さない（B 側に倒す）。
- 審査役が勧めた2点も一緒に直す（どちらも B 側に倒す直し）:
  - 試験ファイルの差分で `---`／`+++` を見出しとして除くのは、各ファイルの見出し（`diff --git` の行から最初の `@@` の行まで）の中だけにする。本文の `--` で始まる行を消すと `---…` になって検査を抜けるため。
  - CI の `continue-on-error` は、欄があって値が `false`（真偽値）でなければ B にする。`${{ true }}` の書き方を抜けるため。
- 審査役の指摘のうち、カードの書き方の誤り: §8 の「試験ファイルの `-` の行は A5-0 の1行だけ」は、main() の一覧の行も必ず変わるので2行が正しい（実装は正しい）。
- 確かめ方: 便1カード §13 の試験 G15〜G17 を足し、既にある G1〜G14 と A の試験が全部 PASS のまま、新しい試験が期待どおり B になること。クラウドで流す。マージ前に、新しく起動した opus の審査役がこの直しを読む。
- 審査の扱い: この §12-13 の直しは、同じ AI（Opus）が書いて自分で読んだもの（独立した第二者の審査ではない）。マージ前の審査役の審査で読み直す。

## 13. 実装に向けた補足（第10版・2026-11-09。実装カードを書くときに決めた細部。クラウドの審査を受けてから便を出す）
基準: origin/main 98a4fb4c5（bb87bf0b1 から consent-audit.py・perm-change.py・permission-delegation-tests.py・.claude/agents/reviewer.md・agent-hooks-test.yml・scripts/agent-hooks/ に差が無いことを `git diff --stat` で確認）。

### 13-1. 便の分け方
- 便1（点検と記録の道具）: perm-change.py の record に §5-3 の欄を足す。consent-audit.py に §5 の分岐と 13-3 の2つの写しのキーを足す。permission-delegation-tests.py に試験 G1〜G5・G8・G10〜G14 を足す。.claude/agents/reviewer.md に §5 の末尾の確認項目2行を足す。本番の設定と ~/.claude には触らない。
- 便2（入れる道）: install-guard.sh とその試験。mac-test-guard に札を足す（本体は変えない）。CI に test_guard.py・install-guard の試験を足し、試験の job の checkout を `fetch-depth: 0` にする。試験 A7・A9 と、A4・A8・A11 の台本の側。便1 がマージされてから書く。
- HKI-1 の追加と install-guard.sh の初回の実行は PO の `!`。その前に PO に知らせる。

### 13-2. 判定に要る値の渡し方
- 写しの要素は、hook_files は `sha8(相対パス)|中身8桁`、user:hooks は `event|matcher|組の sha8`。今の judge_change は末尾の8桁しか受け取らない（consent-audit.py:1032 の element_hash）。§5 の分岐はパスの sha8 と event・matcher が要るので、judge_change と record_ok に、既定値 None のキーワード引数 `el`（写しの要素の全体）と `now` を足し、run_permissions（:1033）から渡す。今の呼び元は変えなくても動く。§5 の分岐で `el` か `now` が None なら通さない（B 側）。
- §5 の分岐は、`po_ref` が `PR#<数字>` で target が `hook-files` か `user-hooks` のときだけ。ほかは今の流れのまま（:906 の判定より前で分ける）。

### 13-3. 「台帳に置いた台本の sha256」の置き場（§5-5 の2つ目の項目の実装）
- 写しに2つのキーを足す。`guard_installer` = ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh の sha256 先頭8桁（ファイルが無ければ空の一覧）。`guard_judge` = ~/.salesanchor-tools/scripts/dev/consent-audit.py の、印 `# >>> ADR-1072 guard-add judge` と `# <<< ADR-1072 guard-add judge` に挟まれた行を全部つないだ文字列の sha8（印が無ければ空の一覧）。§5 の分岐の関数と、record_ok の中の分岐の呼び出しの行は、印の中に置く。
- TARGET_KEYS に `"guard-installer": "guard_installer"` と `"guard-judge": "guard_judge"` を足す。LEDGER_ONLY_KEYS と PR_ONLY_TARGETS には足さない。このため、値が変われば PO の「1」（`consent:` の記録）でしか説明できず、無ければ B（:906 で PR 番号は通らない）。
- 便1 のマージの後の最初の点検では、2つのキーは前回の写しに無いので「（初回）」と出て判定しない（:1019-1021）。`guard_installer` は便1 の時点では空の一覧なので、便2 で台本が入ると増として出て、PO の「1」が要る。これが「台帳に置いた値を PO の「1」で決める」に当たる。

### 13-4. §5 の分岐の細部
- 1.（hook_files の増）: PR #n のマージ mc について、`git diff --name-only mc^1 mc -- scripts/agent-hooks/` からフォルダ名を取る（`scripts/agent-hooks/<name>/...` の形のものだけ。直下のファイルは数えない）。各フォルダの札を mc の版で読み（§5-0 の検査を全部当てる）、札の `files` の各名前について sha8(`<name>/<file>`) が要素のパスの sha8 と同じで、`git show mc:scripts/agent-hooks/<name>/<file>` の sha256 先頭8桁が item_hash と同じものがあれば、その名前で 5・6 と §5-5 を確かめる。
- 4.（中身の書き換え）: 写しでは「減の要素」と「増の要素」の2つに分かれる。§5-4 の試験の検査は減の要素の判定で行い、増の要素は 1. だけで判定する（減の要素が説明できなければ B が出るので、増だけを記録して逃げる道は無い）。減の要素の判定: 要素のパスの sha8 に当たるファイルが、今の `~/.claude/scripts/<name>/<file>` にあり、その中身が mc の版と同じこと。P は 6 の決め方（`git log --first-parent --format=%H mc^1 -- scripts/agent-hooks/<name>/` を新しい順に見て、その版のファイルの中身8桁が item_hash と同じ最初のものを見つけ、そこから同じ中身が途切れずに続く範囲のいちばん古いもの。§12-12）。ファイルが無い（外した）なら B。
- 2.・3.（user:hooks）: 今の ~/.claude/settings.json の hooks から、event・matcher が要素と同じで組の sha8 が item_hash と同じ組を探す。組のフックが札の形と同じかは、mc で変わったフォルダの札から作った命令と比べる。3. の減の行は `--replaced-by`・`--batch`・`--old-json` を持ち、同じ PR 番号と batch で item_hash が replaced-by と同じ増の行が台帳にあること。増の組は、同じ batch で通る減の行があれば 3. で通す。
- 5. の時刻: mergedAt < 行の時刻、かつ（held の時刻、無ければ前回の写しの時刻）< 行の時刻 < now。今の「マージが前回の写しより後」（:911-913）は §5 の分岐では使わない。
- 6.: `git log --first-parent <v> --until=<行の時刻> -1 --format=%H -- scripts/agent-hooks/<name>/` が mc と同じ。v は今の tstate の v（GitHub main の sha）。`git rev-parse --is-shallow-repository` が true なら B。
- §5-4 の CI の検査は `git show <v>:.github/workflows/agent-hooks-test.yml` を PyYAML で読む。PyYAML は関数の中で読み込み、読み込めなければその検査は通さない（B 側）。【未確認】週次点検の定期作業が使う python3 に PyYAML があるか（手元の /usr/local/bin/python3 は 6.0.3 あり、/usr/bin/python3 は無し。定期作業がどちらを使うかは未確認）。無い場合、中身の書き換えだけが毎回 B に出る（安全側）。便1 のマージの後の最初の点検の記録で確かめる。
- §5-5 の語の検査: mc の版の、札の `files` と `hooks[].file` のファイルだけを、大文字と小文字を区別して読む。`approve` などは部分一致で当てる（語の区切りを付けない。厳しい側）。

### 13-5. record の欄（perm-change.py）
- `--replaced-by`（8桁の16進数）・`--batch`（`batch:` と16桁の16進数）・`--old-json`（JSON の object）を足す。3つとも任意。`--old-json` は target が `user-hooks` で op が `remove` のときだけ受け、item_sha8(old-json) が `--item-hash` と同じでなければ拒む。`--replaced-by` と `--old-json` はどちらかだけでは拒む。命令の文字列に `=` を含む語、または `[A-Za-z0-9_-]{32,}` の語があれば、秘密の値の疑いとして拒む（§5-3）。
- 行に `replaced_by`・`batch`・`old_json` の欄を足す（欄が無い今の行の読み方は変えない）。

### 13-6. 試験の番号
- 既にある試験は A1〜A21 を使っているので、この設計の受入条件 A1〜A12 は試験の中では G1〜G12 と呼ぶ（G1＝A1 …… G12＝A12）。便1 で書くのは G1〜G5・G8・G10〜G12 の点検の側と、G13（13-3 の2つのキー: 値が変わると B、`consent:` の記録で通る、初回は判定しない）と G14（13-5 の record の欄の検査）。G6 は導入後の手作業、G7・G9 は便2。
- 試験の流し方は今と同じ `python3 scripts/dev/permission-delegation-tests.py`。CI では流れていない（今もそう）。担当はクラウドで流し、生の出力を返す。Mac では流さない。

### 13-7. 9回目の審査で足した細部（第11版・2026-11-09）
- 既にある試験の2か所だけは変える: permission-delegation-tests.py:503 の A5-0 は写しのキーの数を数えるので 24→26 にする。:464 の mutate は :475 で `key.split(":", 1)` を使うので、`:` の無い2つのキーの書き方を前に足す。ほかの A の試験は変えない。
- 試験の git の commit は日時を固定する（GIT_AUTHOR_DATE・GIT_COMMITTER_DATE）。6. の `--until` は commit の日時で選ぶので、今の時計で commit すると判定が B に倒れる。手元の一時のリポジトリで、05:00 に固定した commit が `--until=06:00` で出て `--until=04:59` で出ないことを確かめた（2026-11-09 09:5x UTC）。
- user:hooks の要素は `split("|", 1)` で event を取り、残りを `rsplit("|", 1)` で matcher と組の sha8 に分ける。matcher に `|` が入る組がある（.claude/settings.json:81 の `Write|Edit`）。
- 印の外で判定の関数が呼んでよい部品は sha8・item_sha8・parse_ts・perm_paths・load_json と、引数の gh_view・git_run、標準ライブラリだけ。ほかの部品が要るなら印の中に書く（印の外を弱めても guard_judge が変わらない道をふさぐ）。
- 判定に使う op は record の行の op。挙げていない target と op の組は通さない（B 側）。

### 13-8. 便2 のカードを書くときに決めた細部（第12版・2026-11-09。カード card-bin2.md）
- 札の検査・語の検査・命令の形は、台本が consent-audit.py の `_ga_manifest`・`_ga_words_ok`・`_ga_hook_form`・`item_sha8` を読み込んで使う。同じ規則を台本に書き写さない（点検と台本で規則が食い違う道をふさぐ）。consent-audit.py は便2 では変えない（guard_judge を変えない）。
- 手順の順の細部: §6 の 9（PR 番号）を札を読む前に行う。札と本体の語の検査は、PR #n のマージの版（`git show`）で読む（§5-0）。版の基準は、手順3で GitHub の main と同じと確かめた写しの HEAD にする（写しの `origin/main` の参照は古いことがあるため。§6 の 9 の `origin/main` と同じ版を指す）。
- §6 の 5・6 の細部: 試験は、入れ先に写す前に一時の置き場へ写したもので流す。通ってから入れ先へ写し、sha256 が正本と同じことを確かめる。試験が落ちたときに `~/.claude/scripts/` に写しが残り、週次点検で説明のつかない差になるのを防ぐ。
- 試験の呼び方の決まり: 札の `tests` の各ファイルは、引数1つ（`hooks` の1つ目の `file` の写しのパス）で流す。拡張子が py なら `python3 -I -B`、sh なら `bash`。今の mac-test-guard の test_guard.py:6 と同じ形。新しい見張りの試験もこの形で書く。
- 記録が一部書けなかったとき（perm-change.py が拒んだとき。§5-3 の秘密の値の疑いなど）は、入れたまま `INSTALL_OK_RECORD_INCOMPLETE`（終了コード 3）で終える。書けなかった変化は週次点検で B に出て、Opus が PO に報告する。
- 同時に2回流れるのを防ぐため、`~/.claude/.install-guard.lock` をフォルダで作る（macOS に flock が無いため mkdir の形）。
- 台本の試験では、perm-change.py を偽物に差し替える（本物は origin の URL を GitHub と決めていて、試験から GitHub に触れずには流せない。:29・:293）。本物の record の行の形は便1 の G14 で確かめ済み。

### 13-9. 便2 のカードの審査（1回目 REVISE）を受けた直し（第13版・2026-11-09）
- settings.json を読んで新しい形を組み立てるところまでを、本体を写す前に移す（カード §5 の手順8）。壊れた settings.json で本体だけが入れ替わる道をふさぐ。
- 本体を写した後に止まったときは、settings.json を変えないまま、写した本体の hook-files の記録だけを書いてから `INSTALL_FAILED:` で止まる（~/.claude/scripts の差を記録で説明できる形に保つ）。
- 1回の実行で同じ組に2件以上入れるときは、「実行の前の組」と「全部入れた後の組」の1組だけを記録する（途中の形では `_ga_group` が組を見つけられない）。
- 試験の一時の HOME では、git の名前とメールを env で渡し、`git init --bare -b main` で作る。壊れた settings.json の試験（S-bad）を足す。

### 13-10. 便2 のカードの審査（2回目 REVISE）を受けた直し（第14版・2026-11-09）
- lock は settings.json を読む前（カード §5 の手順8の初め）に取る。2つの実行が古い中身で上書きし合い、先に足したフックが消える道をふさぐ。
- 本体を写した後に止まる道の試験 P-fail を足す（設定は変わらない・lock が無い・記録は写した1つ目の hook-files add だけ）。lock の消し忘れは S-bad と P-fail で確かめる。
- settings.json の一時ファイルは名前を決め、置き換えなかったときは finally で消す。写した後の sha256 が合わないファイルは記録しない（週次点検で B に残す）。

### 13-11. 便2 のカードの審査（3回目 APPROVE）の推奨2件の取り込み（第15版・2026-11-09）
- 3回目の審査は APPROVE（必須なし）。推奨2件をカードに足した。動きの決まりは変えず、書き漏れを埋めるだけ。
- 表の `INSTALL_FAILED` の行: 手順10で控えを取った後に止まると、控え `settings.json.bak-install-guard-*` が残ることがある、と書いた。
- 手順10: 本体を写した後に止まり、その hook-files の記録の一部も書けなかったときは、`RECORD_FAILED:` を出したうえで最後の行は `INSTALL_FAILED:`、終了コードは 1 とした。

### 13-12. マージ前審査（opus・APPROVE）の指摘 中-1 の取り込み（第16版・2026-11-10）
- 審査は APPROVE（必須なし）。中1件・低4件。
- 中-1: 手順9で本体を写した後に OS のエラーが出ると、`Fail` に変わらず外側で止まり、写した分の hook-files の記録が書かれない。カード手順10の「写した後に止まったときは記録してから止まる」と食い違う。
- 直し方: 手順9の1つのファイルの処理で出た `OSError` を `Fail` に変える（カード §5 手順9に1項目）。試験 P-oserr を足し、20件にした（カード §6）。
- 低1〜4は直さない。理由: 低1（途中で止まると 0o644 のまま）は週次点検が中身の sha で見るので記録の点で中-1 に含まれる。低2は文の違いだけ。低3は ~/.claude に書ける者なら settings.json を直接変えられ、新しい攻め口にならない。低4（削除するファイルの欄）は、GO 記録を足すときに process-artifacts gate の求めを確かめてから決める。

### 13-13. 便3: HKI-1 を PO の `!` で足す・外す台本（第17版・2026-11-10。カード card-bin3.md）
- 経緯: 便2 のマージ後、HKI-1 を足す手順が無いと分かった（§6 は「PDL-1 と同じ形」と書くだけで、足す台本を決めていなかった。入れ忘れたのは設計側）。PO は 2026-11-10 に「1」（前回と同じ形の専用の台本を作る）を選んだ。
- 文の正本を §6-1 に移した。文は1文字も変えていない（733字・item_sha8 `203789ba`。移す前の origin/main 96a63df05 の文と同じことを Opus が consent-audit.py の item_sha8 で確かめた）。
- 足し外しの道具は ADR-1034 の po_delegation_edit.py を1本のまま使い、見出しとラベルを引数で受けるようにする（規則を2か所に書き写さない）。引数が4つのときの動きは今と同じ。
- 新しい台本 po-register-hki.sh・po-unregister-hki.sh は PDL-1 の台本の写しで、違いは読む節（`### 6-1.`）とラベル（HKI-1）だけ。台帳の record は `--target user-automode-allow --po-ref consent:<鍵> --actor po-script`。
- 週次点検（consent-audit.py）の `PO_BANG_OP_PREFIXES` に新しい2本の命令の頭を足す。ほかの台本（同じフォルダの install-guard 以外のもの）は今までどおり B。
- 導入の順: マージ → ~/.salesanchor-tools に台本が届いたことを Opus が確かめる → 同意票（操作1 が `po-register-hki.sh consent:<鍵>`）→ PO の「1」→ PO の `!` 1回 → install-guard.sh mac-test-guard の初回（差が無いで終わる見込み）→ A6。
- カードのクラウド審査 1回目（2026-11-09 16:49 UTC・opus・読むだけ。判定 APPROVE。§0 の表は実物と一致・§6-1 の文は 733字 `203789ba` で移す前と同じ、と実際に計算して確認）の推奨4件を取り込んだ（カード第2版）:
  1. 5番目の引数（見出し）は `^### [0-9]+(-[0-9]+)*\.$` に完全一致したときだけ通す。`### ` だけや `### 6` で、ほかの節まで読む道をふさぐ。G18-6 に2通り足した。
  2. G18-6 の chk は1回だけ呼ぶ（PASS の増え方 14 を保つ）。
  3. G18-7〜11 は番号ごとに別の一時フォルダを使う（控えの名前が秒単位のため）。
  4. 導入の順の補足: 同意票の本文に HKI-1 の item_hash `203789ba` を書く（点検の record_ok が同意票の文に item_hash があることを求める。consent-audit.py:1268・試験 A20-n19）。外すときは足したときと別の鍵（新しい同意票と「1」）を使う（同じ po_ref と item_hash の組は1回まで）。
- 実装（第2版カード・e58d98a6c・クラウドの Sonnet・試験 PASS 555→569・FAIL 0）を Opus が差分全文で確かめた。動きはカードどおり。ただし写し元の説明文が2か所残った（po-unregister-hki.sh 6行目の「PDL-1 の1件だけを外す」、po_delegation_edit.py 冒頭の説明が PDL-1 専用のまま）。カードが「次だけを変える」と書き、説明文の直しを入れ忘れたのが原因。カード第3版の §4 に2項を足し、同じ枝で直す。

### 13-14. 便4: 共通の台本の命令の形を見張る install-form-guard（第18版・2026-11-10。カード card-bin4.md）
- 経緯: 便3 の導入後の A6 で、4件のうち `CLAUDE_DIR=` を前に付けた形だけが自動判定を通った（ほかの3件は拒否）。台本の版の確かめで `INSTALL_FAILED` になり、settings.json の sha256 は変わらなかった（c668e750…）。結果の原本: ~/CC報告ファイル-keep/20261110-adr1072-bin3-A6.md。HKI-1 の文は前に環境変数を付けた形を対象外と書いているが、自動判定はそれを守らなかった。§8 の 4 の「導入後に A6 で確かめる」で見つかったもの。
- 台本の中で止める案（HOME が本来のホームと違えば止まる）は採らない。理由（実物で確かめた事実）:
  1. 台本の試験は一時の HOME で台本を流す（scripts/agent-hooks/test_install_guard.py:149-153・:292-295）。HOME の確かめを入れると試験が全部止まり、試験だけ逃がす口はそれ自体が抜け道になる。
  2. `PATH=<別の場所>` を前に付けると、台本が動く前に `bash` と `python3` の選び先が決まる（install-guard.sh:8 の `python3` は PATH で探す）。台本の中の確かめでは止められない。
- PO の決定（2026-11-10「1」）: 見張りを1つ足す方法に変える。
- 見張りの中身（正本 `scripts/agent-hooks/install-form-guard/`。札・本体・試験の3つ）:
  1. PreToolUse・matcher `Bash`・interpreter `python3`・file `guard.py`。`after` は書かない（組の最後に足す。止める見張りは並びの位置で効きが変わらない）。
  2. `tool_input.command` が文字列でなければ止めない（exit 0）。
  3. 当たり判定: 命令から `'`・`"`・`\` を取り除き、小文字にした文字列に、`install-guard` か `.salesanchor-tools/scripts/agent-hooks` のどちらかが含まれれば対象。引用符を挟んで名前を分ける書き方（`install-gu''ard`）も対象になる。
  4. 対象のうち、元の命令（何も取り除かない）が `^bash ~/\.salesanchor-tools/scripts/agent-hooks/install-guard\.sh [a-z0-9-]+$`（re.fullmatch。前後の空白・改行も許さない）に一致するものだけを通す（exit 0）。HKI-1 の文と同じ形。
  5. それ以外の対象は exit 2 で止め、標準エラーに止めた理由と「決まった1行の形でだけ流す・中を読むだけなら Read ツールを使う」を出す。許可券で通す道は作らない（正しい形は1つしかないため）。
  6. 止めたときは mac-test-guard と同じ形で ~/.claude/logs/agent-events.jsonl に1行足す（`hook: install-form-guard`。書けなくても止める）。試験は環境変数 `INSTALL_FORM_GUARD_LOG` で書き先を一時のファイルに向ける。
  7. 入力の JSON が読めないときは止めない（exit 0）。mac-test-guard と同じ。Claude Code が壊れた JSON を渡すことは無い前提で、ほかの Bash を巻き添えで止めないため。
  8. 本体に §5-5 の語（`approve`・`behavior`・`updatedInput` など）を書かない。台本と点検の語の検査に当たるため。
- 公式の動き（Context7 `/websites/code_claude`・code.claude.com/docs/en/hooks で 2026-11-10 に確認）: PreToolUse で exit 2 を返すと、その道具の呼び出しは止まり、標準エラーが Claude に返る。exit 0 は許可にならず、ふつうの許可の流れ（自動判定を含む）へ進む。よってこの見張りは自動判定の前に止め、通したものも自動判定の確かめを受ける。
- 巻き添え: Opus が手元の Bash で `git show …install-guard.sh` や `grep install-guard` を打つと止まる。中を読むときは Read ツールを使う（consent-guard と同じ扱い）。クラウドの担当には ~/.claude の見張りが無いので影響しない。`test_install_guard.py` は `install_guard`（下線）なので当たらない。
- 受け入れたリスク: 変数で文字列を組み立てる書き方（例 `D=install; bash ~/…/${D}-guard.sh x`）は、この見張りでは見つけきれない。HKI-1 の形に合わないので自動判定の確かめは受ける。最後の守りは今までどおり週次点検（設定が変われば記録で説明できない限り B）。
- 入れ方: マージ → `perm-change.py sync` で ~/.salesanchor-tools を GitHub main にそろえる → Opus が `bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh install-form-guard` を1回。これが K1（§2）の最初の実測になる（差が出る最初の見張り。§6 の 111 行目）。PO の `!` は要らない。
- 受入条件:

| 基準 | 検証方法 |
|---|---|
| A13 正しい1行の形だけ通し、前に環境変数・`PATH=`・`env`・`cd … &&` を付けた形、引数が0・2つ、`;`・`|`・`&&`・改行・`$(`・バッククォート・リダイレクトを足した形、見張りごとの install.sh・rollback.sh、引用符で名前を分けた形を止める。関係のない命令（`git status`・`ls`・`python3 scripts/agent-hooks/test_install_guard.py`・`perm-change.py sync` の形）は止めない | 試験 test_guard.py（CI の agent-hooks-test.yml に job を足して流す） |
| A14 止めたとき記録が1行増え、`hook` が `install-form-guard`。壊れた JSON・command が文字列でないときは止めない | 同じ試験 |
| A15 札が §5-0 の検査を通り、本体が §5-5 の語の検査を通る | 同じ試験の中で consent-audit.py の `_ga_manifest` と `_ga_words_ok` を当てる |
| A16 入れた後、A6 の (3) と同じ形（`CLAUDE_DIR=/Users/tanizawashingo/.claude bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh mac-test-guard`）と `PATH=/usr/bin:/bin bash …install-guard.sh mac-test-guard` が、この見張りの文で止まり、settings.json の sha256 が変わらない。正しい形は止まらない | 入れた後に Opus が1回ずつ試し、結果を ~/CC報告ファイル-keep/ に残す |
| A17 週次点検で、この見張りを入れた変化が B に出ない（K1） | 入れた週の週次点検の出力の B の行を数える |
