# 実装カード 便1: Opus の権限の足し引きと台帳（permission-delegation）

発行: Claude Opus（設計統括）2026-10-19
根拠: design.md（第5版、Architect 第5回 APPROVE。§12）・recon.md・`docs/adr/ADR-1034-opus-permission-delegation-ledger.md`
PO 承認: 委任の方針（2026-10-19 の原文は recon §4）と範囲（同日「1」: 保留4項目を残し、ほかは Opus が足し引きする）
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-permission-delegation-ledger（branch release/permission-delegation-ledger）。この外では書かない。

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
- 今の定期実行の文: agent-console の定期実行 bb581a6f の promptText。写しは /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/cfca0e17-6522-48eb-a946-cc9ce9b5087e/scratchpad/routine-consent-weekly.json（読み取りだけ）。

## 触らない
- ~/.claude/ 配下、~/.codex/ 配下、~/.salesanchor-tools 配下、agent-console の実物。例外の文の登録は PO の `!` で行い、定期実行の差し替えは Opus が行う。
- 本店 /Users/tanizawashingo/salesanchor の作業ツリーと .claude/settings*.json。
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

## 報告
最後の返事は `DONE: PR #<番号> 試験 <合格数>/<総数>` か `BLOCKED: <理由1行>` か `NEEDS_DECISION: <1行>` の1行だけ。生出力は /tmp/CC報告ファイル/permission-delegation/bin1/ に保存する。
