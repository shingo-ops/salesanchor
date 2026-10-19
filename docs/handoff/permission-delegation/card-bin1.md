# 実装カード 便1: Opus の権限の足し引きと台帳（permission-delegation）

発行: Claude Opus（設計統括）2026-10-19
根拠: design.md（第5版、Architect 第5回 APPROVE。§12）・recon.md・`docs/adr/ADR-1034-opus-permission-delegation-ledger.md`
PO 承認: 委任の方針（2026-10-19 の原文は recon §4）と範囲（同日「1」: 保留4項目を残し、ほかは Opus が足し引きする）
作業場所: ~/worktrees/salesanchor/release-permission-delegation-ledger（branch release/permission-delegation-ledger）。この外では書かない。

## やること（design.md の節に従う。書かれていない条件を足さない）

1. `scripts/dev/consent-audit.py`
   - 共通の関数 `item_sha8(item)` を置き、:329 の式を置き換える（結果の値は変えない）。
   - §4-2 の写しのキーと式をすべて足す。既存キー名の読み替え表、permits は照合から外す、新しいキーは「初回」。
   - §4-3: `--commit-snapshot` を付けたときだけ写しを更新する。照合の結果を `ABNORMAL_REASON=A/B/C/D/E` の行で出す（E は小分類 dirty/stale/sha/offline）。行は `ABNORMAL=` より前。`REVIEW_DUE=` も出す。rc は 0 のまま。B の `PR#n` は gh で確かめ、gh が使えなければ B。
   - 関数は home・now（と試験用の origin の URL・git の実行）を引数で受ける。パスを CLI の引数で受けない（:5 の方針）。
2. `scripts/dev/perm-change.py`（新規）
   - 副命令は apply・record・review・sync の4つ。終了コードは 0・1・3・4（§4-1）。
   - target 表は §4-1 の表どおりに辞書1つで持つ。
   - R0〜R4 の判定は §2-2 のとおり。目印は辞書1つにまとめる。英単語は語の境目で、句と日本語は部分一致で見る。読み取りの印は `*` を含まない文だけに効く。
   - 起動時の確かめ 1〜8 は §4-1 の順に行う。次の点はそのとおりに作る:
     - FETCH_HEAD が V と違えば exit 4。
     - 起動し直しの目印は `PERM_CHANGE_REEXEC=1` で、起動し直しは1回まで。
     - 照合した中身をそのまま import に使う（importlib.util.spec_from_file_location）。
   - 台帳の1行は §4-1 の形。prev_sha の鎖をつなぐ。ロックは mkdir＋trap 相当で、Python では try/finally で rmdir する。
   - 書き込みの前に控えを取る。一時ファイル→rename で書き、書いた後に読み直す。
   - 保留（exit 3）のときは §4-5 の台本を ~/CC報告ファイル-keep/permission-delegation/ に書く。台本の中で道具を呼ぶ形は PDL-1 と同じにする。
3. `scripts/permit-danger.sh`: §4-4 の permit_issued を1行追記する。追記に失敗しても券の発行は止めない。
4. `scripts/dev/permission-delegation-tests.py`（新規）: A1〜A18 のうち試験と書かれたものをすべて作る。
   - 本物の ~/.claude と ~/.salesanchor-tools には触らない。一時ディレクトリの home、GitHub 役の bare リポジトリ、一時の clone で再現する。
   - 既存の consent-audit の試験（A14）も同じ実行で通す。
5. `docs/handoff/permission-delegation/po-register-delegation.sh`・`po-unregister-delegation.sh`（新規）: §4-6 のとおり作る。
   - 型は `docs/handoff/design-approval-ticket/po-register-self-maintenance.sh` と同じ（控え→追加→読み直し→台帳に record）。
   - 足す文は §4-6 の PDL-1 の英文を一字一句そのまま使う。
   - unregister は PDL-1 の1件だけを外す。
6. `docs/handoff/permission-delegation/routine.json`（新規）: 今の定期実行の文（下の「参考」）に、§4-7 の手順1〜5を足す。
   - 手順1は sync を使う。exit 1 でも点検は走らせる。履歴は `git log --first-parent <V>` で引く。
   - 秘密や内部の弱点の文は書かない（公開リポジトリ）。
7. コミットとPR
   - 次のファイルを含めてコミットする: 設計の文書（design.md・recon.md・card-bin1.md・ADR-1034・ADR-1011 の備考・docs/adr/README.md）と上の実装すべて。
   - ADR を変えたら `node scripts/generate-adr-index.js` を実行する。
   - コミット文は feat: / docs: の型で、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
   - PR を作る前に `gh auth status` で shingo-cc であることを確かめる。push してから `gh pr create --base main --draft`。
   - PR本文に入れるもの: `### 標準ワークフロー確認`、変更・新規ファイルの全一覧、試験の合格数／総数、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。

## 参考
- 今の定期実行の文: agent-console の定期実行 bb581a6f の promptText。写しは 作業用の一時フォルダの routine-consent-weekly.json（読み取りだけ）。

## 触らない
- ~/.claude/ 配下、~/.codex/ 配下、~/.salesanchor-tools 配下、agent-console の実物。例外の文の登録は PO の `!` で行い、定期実行の差し替えは Opus が行う。
- 本店 ~/salesanchor の作業ツリーと .claude/settings*.json。
- consent-audit.py の同意の照合（match_ledger_keys など）の判定と出力の形。足すだけにする。

## 止まる条件（BLOCKED: / NEEDS_DECISION: で Opus に戻す）
- 実物の行番号が design.md と合わない。
- 試験が通らない原因が設計にある。
- フックに止められた（言い換えて再試行しない）。
- design.md に無い条件が必要になった。

## 追補（第6版・Reviewer REQUEST_CHANGES の直し、2026-10-19）
同じブランチ・同じ PR #4544 に追加コミットする（force push しない）。

1. HIGH-1（`scripts/dev/consent-audit.py`）: design §4-3 の第6版の段落どおり、record の行は category と held の行の有無にかかわらず po_ref を確かめる。確かめを通らない record の行では差分を説明しない（held 無し→A、有り→B）。PR の (po_ref, item_hash) の組は1回だけ。PR の確かめは PR 本文を使わず、mergeCommit の差分（`git diff <mergeCommit>^1 <mergeCommit>`、~/.salesanchor-tools の V の祖先であること）で行う。B の対象では PR#n を repo-allow・repo-hooks だけに受け付け、ほかは consent だけ。consent は同意票の本文に item_hash があることも確かめる。A7 を設計の新しい文どおりに直し、A19 の試験を足す（gh は偽の応答、mergeCommit は A17 の一時の git リポジトリ）。
2. MEDIUM-1（`scripts/dev/perm-change.py`）: design §2-2 の R0 を「狭い形」（受け入れの一覧と一致するもの）でなければ R0 に反転する。受け入れの一覧は設計の文のとおり辞書（集合）1つで持つ。先頭の語は「パスを外し、末尾の数字と点を外した名前」で比べる（R1 の rm も同じ）。`:*` は ` *` とみなす。rm で `*` を含む文は R0 の前に R1。A18 に設計の反例と狭い形の例をすべて足す。
3. MEDIUM-2（`docs/handoff/permission-delegation/routine.json`）: 道具を呼ぶ形を一字一句 `cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py ...` にする（絶対パスにしない）。
4. LOW-1: po-register / po-unregister の .sh で `$HOME` を使う箇所（道具を呼ぶ行）を `~` の形にする。
5. LOW-2: 両スクリプトの git の実行に環境変数 `GIT_NO_REPLACE_OBJECTS=1` を足す。
6. LOW-3: 控えのディレクトリ名に pid と乱数を入れ、`exist_ok=False` で作る。
7. LOW-4: `docs/handoff/permission-delegation/po_delegation_edit.py` の書き込みを一時ファイル→rename にする。
7b. design §4-5・§4-6（第6版）: po-register / po-unregister は po_ref を第1引数の `consent:<鍵>` で受け（`consent:` で始まらなければ何も変えず exit 1）、`record --po-ref` にそれを渡す。perm-change.py の保留の台本も `consent:<鍵>` を引数で受ける形にする（repo-allow・repo-hooks 以外で PR#n を書かない）。
8. LOW-5: po-register で台帳の record が失敗したら足した文を控えから戻し、失敗を出して終わる。
9. LOW-6: 試験 A2-j を強める（期待する保留の分類まで確かめる）、試験ファイル :259 付近の使っていない呼び出しを消す。
10. 試験をすべて走らせ、生出力を /tmp/CC報告ファイル/permission-delegation/bin1/tests-v6.txt に保存。PR 本文の試験数を書き換える。

## 追補2（第6版 改2・Reviewer 再審査の直し、2026-10-19）
同じブランチ・同じ PR #4544 に追加コミットする。コードの変更は Edit / Write の道具で行う（`python3 -c` や heredoc で書き換えない）。
1. MEDIUM-A（`scripts/dev/perm-change.py`）: design §2-2 の「R0 にしない形」(a)〜(e)（第6版 改4）のとおり、どの道具も受け入れの形に当てはまるときだけ R0 にしない判定にする。受け入れ一覧（Bash の命令・実行役・(b) の最初の段・MCP のサーバー）は辞書1つ。(a) の実行役と先頭の語のパス、(b) の `/` を1つ以上・最初の段・`.` 始まりの段の条件も入れる。A18 に design の改2〜改4 の反例と通る例をすべて足す。
2. LOW-A（`scripts/dev/consent-audit.py`）: §2-3 のキーは、確かめを通らない record の行しか無いときも B にする。試験を1件足す。
3. LOW-B: 試験は既に R0 を期待しているので変更不要（design の文を直した）。
4. LOW-D: PR 本文の「削除するファイル」から削除でないもの（ADR-1011・README.md・consent-audit.py）を「変更」へ移し、R0 の説明を design の改2 に合わせる。本文は Write で作ったファイルから `gh pr edit --body-file` で。
5. 試験をすべて走らせ、生出力を /tmp/CC報告ファイル/permission-delegation/bin1/tests-v6b.txt に保存。

## 追補3（第6版 改5・改6・Reviewer 再審査の申し送り、2026-10-19）
同じブランチ・同じ PR #4544 に追加コミットする。コードの変更は Edit / Write の道具で行う。
1. `scripts/dev/perm-change.py`: design §2-2 (a) の改6 の文のとおり、Bash は `*` の有無にかかわらず「記号（`;`・`&`・`|`・`>`・`<`・`` ` ``・`$`・改行）が無い」かつ「先頭の語の並びが R0_ACCEPT の Bash の受け入れの一覧と一致（`*` の無い文は一覧の語の後が `-` で始まらない語だけ）」のときだけ R0 にしない。実行役の一覧（bash_executors）は使わなくなるので R0_ACCEPT から外す。引号（`"`・`'`）や `\` を含む文は R0。一覧と比べる先頭の語は書かれたままの名前で比べる（パスや末尾の数字を外すのは R1 の rm だけ）。
2. `scripts/dev/permission-delegation-tests.py`: A18 に design の改5・改6 の反例と、改6 の通る例をすべて足す。既存の試験で改6 により期待が変わるもの（`*` の無い一覧外の Bash を R0 にしない前提の試験）があれば、design の文に合わせて期待を直し、どれを直したかを報告に1行で書く。design の文と矛盾する場合は NEEDS_DECISION:。
3. 文書の個人パスを `~` に置き換えた未コミットの変更（card-bin1.md・recon.md・design.md）も同じコミットに含める。
4. 試験の生出力は /tmp/CC報告ファイル/permission-delegation/bin1/tests-v6c.txt。PR 本文の試験数を更新（Write でファイルを作り、別コマンドで gh pr edit）。

## 追補4（Reviewer 再審査 APPROVE の申し送り、2026-10-19）
同じブランチ・同じ PR #4544 に追加コミットする。コードの変更は Edit / Write の道具で行う。試験の文字列はファイルの中にだけ書き、Bash の命令行には危険な語を打たない。
1. MEDIUM（`scripts/dev/permission-delegation-tests.py`）: 旧 R_EXAMPLES から消えた6件（コミット 2602e90b4 の差分で消えた R1〜R3 の Bash の例）を A18 の反例に戻し、`classify == "R0"` かつ apply で exit 3（設定は変わらない）を確かめる。あわせて perm-change.py の目印の「句」それぞれについて、`pc.rule_hit(<規則>, "Bash(grep * <句>)")` が True になる試験を足す。
2. LOW: A4 の R1・R2 に大文字の例を1件ずつ足す（`Bash(grep DELETE docs)`・`Bash(grep PUSH docs)`）。
3. LOW（`scripts/dev/perm-change.py:81` 付近）: R0_ACCEPT の Bash の一覧の説明を「Bash の受け入れの一覧（`*` の有無を問わない）」に直し、キー名を `bash_accept` に変える（参照箇所もすべて）。
4. LOW: design §2-2 (a) 2. に足した「`*` が語の途中にある文」の扱いの試験を A18 に足す（`Bash(grep foo*)` と `Bash(grep -r*)` は R0 ではない）。
5. design.md と card-bin1.md の未コミットの変更も同じコミットに含める。試験の生出力は /tmp/CC報告ファイル/permission-delegation/bin1/tests-v6d.txt。PR 本文の試験数を更新する（Write でファイルを作り、別コマンドで gh pr edit）。

## 報告
最後の返事は `DONE: PR #<番号> 試験 <合格数>/<総数>` か `BLOCKED: <理由1行>` か `NEEDS_DECISION: <1行>` の1行だけ。生出力は /tmp/CC報告ファイル/permission-delegation/bin1/ に保存する。
