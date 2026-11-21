# design — 要件の書類を作業の場面で目に入れる（2026-11-21・設計審査済み 5回目 APPROVE）

> この文書は何か: R1〜R4 を合格させる作り方・測り方・守り続ける仕組み。実装カードの元。
> 親: [../../specs/requirement-library/README.md](../../specs/requirement-library/README.md)／現在地: [recon.md](./recon.md)／KGI: [kgi.md](../../specs/requirement-library/kgi.md)／練習問題: [quiz.md](./quiz.md)
> 実装カード: [便1](./card-bin1.md)・[便2](./card-bin2.md)・[便3](./card-bin3.md)（合流の順: 便1 と便3 → 便2）・[便2b](./card-bin2b.md)（変更後の測定で R2・R3 が届かなかった後に足した便）

## 1. 目的と利用者に見える変化

- 目的: AI が機能に触る前に、その場所の決まり（ADR・設計書）を必ず目にする。決まりと食い違う計画を「不具合」と取り違えない（11/13 の会社の新規登録の件）。
- 変化前: 決まりは索引を自分で引けば見つかる。索引は主要 ADR だけ（161 個が載っていない。recon §2）。
- 変化後: (1) すべての ADR が索引に載るか、載せない理由が書かれる。(2) AI が決まりのあるファイルを開くと、その場で「この場所の決まり」が1回だけ示される。(3) 要件の書類を読まずに「不具合」と結論しかけたら、止めて読ませ、記録に残す。

## 2. 対象と対象外

- 対象: `docs/adr/FEATURE-INDEX.md`（表に「コードの場所」列と除外表を足す）、新しい CI 検査（scripts/ci/ の下の3本と `.github/workflows/doc-index-reachability.yml` の段）、`.claude/hooks/` の見張り 2 本と `.claude/settings.json` の登録、見張りの試験（`.github/workflows/agent-hooks-test.yml`）、週次の数え（`scripts/dev/doc-entry-weekly-check.sh`）、練習問題の測定。
- 対象外: 製品コード・DB・画面・ADR 本文・workflow-lint.yml。

## 3. 作り方（便ごと。各便のあと練習問題で測る）

### 便1 目録を漏れなくする（R1）

- 言葉の決め: R1 の「設計仕様書」は `docs/specs/` 直下のフォルダ（今 56 個）。入れ子（例 `db-ssot/deal-removal`）は親の README から辿れることを既存の check_doc_index.py が見ているので、R1 では親フォルダ単位で数える。
- 索引の表の列を「機能キーワード｜正準 ADR｜設計書｜コードの場所｜補足」の 5 列にする（今は 3 列）。
  - 設計書: 索引から見た相対リンク `[…](../specs/<フォルダ>/…)`（入れ子の設計書を直接指してよい）。無ければ `-`。今「正準 ADR」欄にある設計書のリンク（FEATURE-INDEX.md:21 の bundle-sale・`:47` の specs/README）は設計書欄へ移す。
  - コードの場所: リポジトリ直下からの glob（例 `backend/app/routers/companies.py`）。複数は `、` で区切る。コードを持たない決まり（手順・運用だけ）は `-`。
  - glob の決まり（検査と見張りで同じ）: `/` で区切った段ごとに照らす。`*`・`?` は1段の中だけ（`/` をまたがない）。`**` だけの段は0段以上の何段にも当たる。この照らし方は新しい小さな部品 scripts/ci/feature_index_lib.py の1つの関数（索引の表の読み取りと glob の照らしの両方）にだけ書き、検査（便1）と見張り（便2）はどちらもこれを import する。CI は `python3 -I` で流す（`-I` では同じフォルダの部品を自動で読まない）ので、検査は先頭で `sys.path.insert(0, str(Path(__file__).resolve().parent))` を書いてから import する。見張りは自分のファイルの場所から `Path(__file__).resolve().parents[2] / "scripts" / "ci"` を足して import し、import に失敗したら終了コード 0 で何も返さない。Python 3.12 で動く標準ライブラリだけで書く（`PurePosixPath.full_match` は 3.13 からなので使わない）。
- 161 個の ADR と、索引から指されていない設計仕様書のフォルダを、次の順で振り分ける。
  1. ADR の状態の値の**先頭の語**が Superseded・Deprecated・Rejected・廃止 のどれか → 末尾の新節「索引に載せない ADR・設計仕様書」に「番号かフォルダ｜理由（どれに置き換わったか）」で載せる。値の途中に「置き換え」等があるだけでは除外しない（例 ADR-1039 は Accepted なので載せる）。状態の欄が無い ADR は 2 へ。
     - 状態の値の取り方（feature_index_lib.py の1つの関数に書く）: 先頭 40 行を上から見て、最初に当たった形で決める。`ADR-` で始まる行と、見出しの語の後に `:`・`：`・`|` も行末も来ない行（例「…状態を実現する」）は飛ばす。
       - 表の行 `| ステータス | X |`（`Status`・`状態` も同じ。項目名の前後の `*` と空白は取ってから比べる。例 ADR-110 の `| **状態** | Accepted |`）→ 2 列目の X。表の見出しが `| 項目 | 内容 |` でも同じに読む。
       - `ステータス: X`・`**Status**: X`・`- 状態：X` の形 → `:`・`：` の後ろの X。
       - 見出しだけの行 `## Status`・`## ステータス`・`## 状態` → 次の空でない行。
       - X から `*`・`>`・`-`・空白を前後で取り、空白か `（`・`(` までを先頭の語とし、その語の両端の `*` も取る。
     - 3回目・4回目の審査が実物で数えた Superseded は 4 本（ADR-020・ADR-028・ADR-1009・ADR-138）。実装役は除外した一覧を PR 本文に貼り、4 本と違えば止めて Opus に知らせる。
     - 除外の節の理由欄には置き換え先を書く。置き換え先が ADR でないとき（ADR-028 はスクリプトと手順書）は、そのファイル名をそのまま書く。
     - 今「正準 ADR」欄にある Superseded の ADR は、その行から外す。FEATURE-INDEX.md:32（password_hash の行）の ADR-138 は外し、その行の正準欄を ADR-1013 にする。`:51`（24時間保守運用の行）の ADR-1009 は外す（ADR-1039 は `:53` に既にあるので足さない）。外した方は除外の節へ載せる。
     - 同じ番号のファイルが2つ以上ある番号（2026-11-21 の実物で 15 個。うち状態が違うのは 10 個で、除外になるのは ADR-138 の 1 組だけ）は、状態をファイルごとに見る。除外の節にはファイル名で載せる（例 ADR-138-remove-password-hash.md）。生きているファイル（例 ADR-138-funnel-dashboard-stage1.md）は振り分けの 2 で、その中身に合う行（ファネル・ダッシュボードの行。無ければ新しい行）の正準欄に載せる。
     - このため、同じ番号が除外の節（ファイル名）と正準欄（番号）の両方に出てよい。両方に出てよいのは、その番号のファイルが2つ以上あり、除外の節にファイル名で載っているときだけ。それ以外で両方に出たら検査は落とす。検査は、番号のファイルのうち1つでも除外でないものがあれば、その番号が正準欄に載っていることを求める。
  2. それ以外 → ADR の題名と本文の最初の節を読み、既存の行の機能キーワードに当たれば (a) その行の「正準 ADR」欄に足す。当たらなければ (b) 新しい行を作る。手順・運用だけの決まりは「横断・運用・プロセス」節に入れ、コードの場所は `-`。
  3. 設計仕様書のフォルダも同じ。対応する ADR の行の「設計書」欄に載せる。どの行にも当たらず状態が「完了・廃止」なら除外の節へ理由つきで載せる。
- 11/13 の件は (a): 「会社」の行に ADR-097 と `docs/specs/db-ssot/deal-removal/design.md` を足す。
- 練習問題の 10 題の正解の ADR は、必ず「コードの場所」が `-` 以外で 1 つ以上のファイルに当たる行に載せる（便2の見張りが働くため）。glob は実装役が実物で決め、カードの完了報告に 11 行分（正解の ADR は 11 個。Q9 は ADR-1056 と ADR-1078 の2つ）を貼る。
- 新しい検査 scripts/ci/check_feature_index.py（r1_count.py より厳しい数え方）:
  - 数える ADR: `docs/adr/` 直下で、名前が正規表現 `^ADR-((?:SA-)?\d+)(?=[-_.])` に当たり .md で終わるファイル。番号は先頭の 0 を除いた数字（`SA-` つきはそのまま `SA-17` のように）で、同じ番号の複数ファイルは1つと数える。r1_count.py も同じ形に直し、2026-11-21 に流した値は 番号 226・索引が指す 65・指さない 161。
  - ADR は「正準 ADR」欄か除外の節の1列目にある番号だけを「載っている」と数える（補足欄の文の中の番号は数えない）。
  - 設計仕様書のフォルダは「設計書」欄か除外の節の1列目のリンクを `docs/adr/` から解いて（`posixpath.normpath`）、`docs/specs/<フォルダ>/` で始まれば「載っている」と数える。
  - 読む表は、見出しの1列目が「機能キーワード」の表と除外の節の表だけ（「ADR 候補バックログ」の表は読まない）。
  - 「コードの場所」が `-` でない行で、glob が `git ls-files` のどのファイルにも当たらなければ失敗。
  - 1 件でも抜けか当たらない glob があれば終了コード 1 と一覧を出す。doc-index-reachability.yml の今の step（`:29-37`。`exit "$rc"` で終わる）は変えず、その後ろに新しい step「Check feature index」を足し、`run` に `python3 -I scripts/ci/check_feature_index.py --root .` と `python3 -I scripts/ci/test_check_feature_index.py` の2行を書く（step は既定の `bash -e` なので、どちらかが失敗すれば step が赤になる）。この workflow は main 宛ての PR・main への push・合流待ちの列・毎週月曜に流れる（`:6-15`）。新しい必須チェックは作らない。
- 試験 scripts/ci/test_check_feature_index.py: ADR の抜け・補足欄だけに書かれた番号・設計仕様書の抜け・当たらない glob・バックログの表の番号を数えない の 5 つの見本と、glob の照らし（`*` が `/` をまたがない・`**` が0段にも当たる）を確かめ、正しい見本で成功する。
- 数が多いので、実装は「検査と試験」と「振り分け」を同じ PR の別 commit にする。振り分けの結果（何をどこへ）を一覧にして PR 本文に貼る。

### 便2 開いた瞬間に決まりを見せる（R2・R3）

- .claude/hooks/requirement-context.py（PostToolUse、対象 `Read|Edit|Write|MultiEdit`）: tool_input の file_path を索引の「コードの場所」と照らし、当たった行の「正準 ADR と設計書のパス」を `hookSpecificOutput.additionalContext` で返す。
- パスの照らし方: file_path は絶対パスで来る（作業場所 `~/worktrees/...` でも、クラウドの `/home/user/salesanchor` でも）。file_path のある場所で `git rev-parse --show-toplevel` を流して、その直下からの相対パスにしてから、scripts/ci/feature_index_lib.py の照らしの関数で glob と照らす（`fnmatch` は使わない）。索引もその同じ直下の `docs/adr/FEATURE-INDEX.md` を読む（本店の古い写しを読まない）。リポジトリの外のファイルは何もしない。
- 同じ行は1つの会話で1回だけ。印は `${TMPDIR:-/tmp}/requirement-context/<session_id>` に機能キーワードを1行ずつ書く。当たらなければ何も返さない。
- どんな失敗（索引が読めない・入力が壊れている・git が無い）でも終了コード 0 で何も返さず、作業を止めない。
- 登録: `.claude/settings.json` に `"PostToolUse"` 節を新しく足し、`matcher` は `Read|Edit|Write|MultiEdit`、`command` は `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/requirement-context.py"`、`timeout` 5 秒。既存の節は変えない。
- 試験 .claude/hooks/test_requirement_context.py: 当たる・当たらない・2回目は黙る・壊れた入力・リポジトリ外 の 5 つ。
- 試験を流す場所: `.github/workflows/agent-hooks-test.yml`。job `requirement-hooks` と paths の `.claude/hooks/requirement-*`・`.claude/hooks/test_requirement_*` は便3 が作る（便3 を先に合流する）。便2 はその job に step を1つ足し、paths に `scripts/ci/feature_index_lib.py`・`docs/adr/FEATURE-INDEX.md` を足す。この workflow の変更は CLAUDE.md の不可逆操作の一覧（workflow-lint.yml だけ）に当たらない。
- 文の形:「この場所には決まりがあります: ADR-097（会社はリードの子）。計画の前に docs/specs/db-ssot/deal-removal/design.md を読んでください。」

### 便2b コマンドで読んだときも決まりを見せる（R2・R3）

- 足した理由（観測）: 変更後の練習問題（[quiz/r3-judgement-after.md](./quiz/r3-judgement-after.md) §3）で、20 回の道具の呼び出し 187 件のうち `Bash` が 159 件・`Read` が 18 件だった（生の記録 raw.tgz を数えた）。Q1 の 2 回は `backend/app/routers/companies.py` などを `sed -n`・`grep` で読み、便2 の見張り（対象 `Read|Edit|Write|MultiEdit`）は一度も文を出さなかった。設計で `Bash` で読む道を入れ忘れたのが原因。
- 変えること（便2 の見張りを広げる。新しい見張りは作らない）:
  - `.claude/settings.json` の `"PostToolUse"` の `matcher` を `Read|Edit|Write|MultiEdit|Bash` にする（この1行だけ）。
  - `.claude/hooks/requirement-context.py`: `tool_input.file_path` があれば今と同じ。無くて `tool_name` が `Bash` なら、`tool_input.command` から読んだファイルを拾い、1つずつ今と同じ照らし方（`git rev-parse --show-toplevel`・`feature_index_lib.match_glob`・印）にかける。文の形・印・1会話1回は便2 と同じ。
- コマンドからファイルを拾う決まり:
  - `shlex.shlex(command, posix=True, punctuation_chars=True)`（`whitespace_split=True`）で語に分ける。引用符が閉じていないなどで分けられなければ、空白で分ける。語は先頭から 200 個まで。
  - `-` で始まる語は飛ばす。`*`・`?`・`[` を含む語は `glob.glob` で広げる（1語 50 件まで）。
  - 語は入力の `cwd`（公式の hooks の説明の共通の入力。2026-11-21 Context7 `/websites/code_claude` で確かめた）からの相対として解く。絶対パスはそのまま。`cwd` が無ければ相対の語は使わない。
  - 実在するファイル（`os.path.isfile`）だけを使う。フォルダは使わない（`grep -r frontend/src` のように広すぎて、関係の薄い決まりまで一度に出るため）。ファイルは 1 回の呼び出しで 50 個まで。
  - 照らす前に同じファイルを1つにまとめる。`git rev-parse` は同じフォルダで1回だけ流し、1回の待ちは 1 秒まで。見張りの登録の timeout が 5 秒なので、照らし始めてから 3 秒を過ぎたら残りのファイルは照らさず、それまでに当たった分だけを出す。
- 机上の確かめ（Opus、2026-11-21）: 上の決まりを変更後の生の記録 20 回の `Bash` に当てると、Q1-1 は2回目のコマンドで `backend/app/routers/companies.py` に当たり ADR-097 の行が出る。文の数は1会話で 0〜10（最大は Q9-2）。
- 試験: 便2 の 5 つはそのまま残し、次の 5 つを足す。相対パスの `sed -n` で当たる／`*` の語で当たる／フォルダだけでは出ない／実在しないファイルの語では出ない／引用符の閉じない壊れたコマンドでも終了コード 0。
- 測り方: 合流の後、変更前・変更後と同じ練習問題 20 回を流し（`quiz/after2/`）、R2・R3 を数え直す。R2 18 以上・R3 0 で合格。
- 拾えない書き方（限り）: `cd backend && sed -n 1p app/x.py` のように同じ命令文の中で `cd` した後の相対の語（入力の `cwd` は `cd` の前のため）、`git -C <場所>`・`git show origin/main:<パス>`、`~`・`$VAR` を含む語。机上の確かめの数はこの限りを入れた数で、`cd` 付きの読み方が増えれば R2 の見込みに響く。
- 対象外: `Grep`・`Glob` の道具（練習問題の 20 回で 0 件だった）。索引・`scripts/ci/feature_index_lib.py`・便3 の見張り。
- 戻し方: `matcher` を元の4つに戻す revert で、便2 のときの動きに戻る。

### 便3 読まずに「不具合」を止める（R4）

- .claude/hooks/requirement-bug-claim.py（Stop）: transcript_path を読み、最後の返事に「不具合・バグ」があり、その会話で `docs/adr/` か `docs/specs/` を1度も読んでいなければ、1回だけ `decision: block` で「要件の書類を読んでから判定してください」と返す（`stop_hook_active` が真なら止めない）。
- 登録: `.claude/settings.json` の今の `"Stop"` 配列（`:93-97`。中は dispatch.sh の1つ）の後ろに、2つ目の要素 `{ "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/requirement-bug-claim.py\"", "timeout": 10 } ] }` を足す。既存の要素は変えない。クラウドの環境でこの見張りが動くかは確かめていないので、R4 の本測定は Mac の会話だけと決めている（下の記録の項）。
- 「読んだ」の判定: transcript の tool_use のうち、Read の file_path か Bash・Grep・Glob の入力に `docs/adr/` か `docs/specs/` を含むものが1つでもあれば読んだとする（count.py の数え方と同じ考え）。
- 止めた回を `~/.claude/requirement-library/bug-claims.log` に1行ずつ書く（日本時間の日時・session_id・返事の最初の 40 字）。クラウドの使い捨て環境の分は消えるので、R4 の本測定は Mac の会話だけを数えると決める（クラウド分は練習問題の補助で見る）。
- 週1回の数え（便3の成果物）: 既にある `scripts/dev/doc-entry-weekly-check.sh` に、記録の過去 7 日の行数を `BUG_CLAIMS_7D=<数>` で出す節を足す。1 以上なら `add_ng "BUG_CLAIMS_7D=<数>"`（`:20` の関数）で RESULT=NG にする。記録が無いときは `BUG_CLAIMS_7D=0`。
  - このスクリプトは Mac の agent-console の定期作業「入口の文書 週次点検」（毎週月曜 16:00 日本時間・Opus。Mac の `~/Library/Application Support/agent-console/routines.json` で 2026-11-21 に確かめた）が流し、NG なら PO に知らせる。定期作業の設定は変えない。
  - R4 の「今」欄は、便3 の後の最初の月曜の結果で Opus が書く。
- どんな失敗でも終了コード 0 で止めない。試験は 読まずに不具合→止める・読んでから不具合→止めない・stop_hook_active→止めない・壊れた入力 の 4 つ。試験は便2 と同じ agent-hooks-test.yml の job で流す。

## 4. 合格の判定

|基準|検証方法|
|---|---|
| R1 索引（正準 ADR 欄・設計書欄）にも除外の節にも無い ADR・設計仕様書のフォルダ 0 | CI check_feature_index.py が成功（PR の検査結果に出る抜けの数 0） |
| R2 20 回中 18 回以上で正解の書類を開く | 便2のあと quiz を流し count.py の `R2` 値 |
| R3 決まりに触れずに反する計画 0 | 同じ 20 回の答えを quiz.md §2 の表で Opus が判定（r3-judgement.md） |
| R4 読まずに「不具合」0 | 便3の見張りの記録を週1回数える（本測定）。補助に count.py の `R4aux` |
| 見張りが作業を壊さない | 見張りの試験（当たる・当たらない・壊れた入力で終了コード 0） |

## 5. 代わりの案と選んだ理由

- 案A CLAUDE.md に全 ADR の一覧を入れる → 90 行の上限（`frontend/scripts/check-claude-size.js`）と ADR-1040 の「入口は短く」に反する。不採用。
- 案B 索引だけ直して見張りを作らない → 今も「引く義務」はあるのに引かれなかった（recon §4）。R2 が上がらない見込みが高いので、便1のあと測って確かめる。
- 案C（採用）索引を正本にし、見張りはその索引を読むだけ。決まりの置き場は索引1か所のまま（データを分散させない）。

## 6. 危ないことと対処

- 見張りの文が多すぎて邪魔 → 同じ行は会話で1回・当たったときだけ。
- 「不具合」の語は正しい不具合報告にも出る → 止めるのは「決まりの書類を1度も読んでいない」ときだけ・1回だけ。
- 索引の「コードの場所」が古くなる → 便1の CI で、glob が1つのファイルにも当たらない行を失敗にする。
- 戻し方: 便ごとに PR を分ける。見張りは `.claude/settings.json` の登録を外す revert で消える。

## 7. 外部・過去事例の参照と我々への応用

- 確かめたもの: Eliav（指示を作業の場面に近づけると従う率が上がる趣旨）。出典と数は proposal 原稿の表を Opus が読んで確認済み。
- まだ確かめていないもの: CybeDefend・Vercel・Lance Martin・Coombs・Rulestack の数。**本設計の合格の根拠には使わない**。根拠は自分の練習問題の前後比較だけ。

## 8. 維持の仕組み

守り手: .github/workflows/doc-index-reachability.yml（便1 で足す「Check feature index」の段。索引の漏れがあれば CI が落ちる）

- 関係する決まり: ADR-1040（文書を入口から辿れる形にする）・ADR-121（設計仕様書と索引の義務）・ADR-097（会社はリードの子）。現在地は docs/handoff/requirement-library/recon.md。
- 新しい ADR を足すと、索引に行か除外表が無ければ CI が落ちる（便1）。
- 見張りの記録は週1回数える（便3）。数え忘れは agent-console の週次点検で見る。
- 練習問題（quiz）は残し、索引や見張りを変えたら流し直す。

## 9. 審査

- 1回目（2026-11-21 08:12、クラウドの審査役 Sonnet、対象 9799b8e2）: **REVISE**。直した点: R1 の設計仕様書の数え方を KGI に合わせた（設計書欄を新設）／検査は正準 ADR 欄と除外の節だけを数える／振り分けの順番と `-` の使い方を書いた／便2 のパスの照らし方・印の置き場・登録の形を書いた／便3 の「読んだ」の判定・記録の置き場・週次の数え方を書いた／recon の絶対パスを相対に直した。
- 2回目（2026-11-21 08:17、同、対象 2a2a08b7）: **REVISE**。直した点: 除外は状態の欄の先頭の語だけで決める／設計書のリンクは相対リンクを解いて数え、既存の2つを設計書欄へ移す／glob の照らしを共有の部品1つにし、`*`・`**` の意味を決めた／試験を流す workflow を決めた／週次の数えを既にある週次点検のスクリプトに足すと決め、流す定期作業を実物で確かめた。
- 3回目（2026-11-21 08:24、同、対象 e50bf991）: **REVISE**。直した点: `-I` で部品を読み込む書き方を決めた／便3の見張りの登録の場所と形を決めた／CI は今の step の後ろに別の step を足すと決め、流れる時を実物どおりに直した／ADR の状態の値の取り方を表・`:` の形・見出しの3つに書き分け、審査が数えた Superseded 4 本を照合の値にした。
- 4回目（2026-11-21 08:27、同、対象 8ea9ac23）: **APPROVE**（注記4つ）。注記への対応: 数える ADR のファイル名の形を決め、r1_count.py もそれに直して R1 の今の値を 161 に改めた／除外の理由欄に ADR 以外の置き換え先を書く決まりを足した／索引に載っている Superseded 2本の扱いを決めた／先頭の語の両端の `*` を取ると決めた。Opus が実物で確かめたとき、ADR-138 は同じ番号のファイルが2つ（Superseded と Accepted）あったので、状態をファイルごとに見る決まりを足した（審査の注記に無かった点）。
- 5回目（2026-11-21 08:31、同、対象 fb70aa45）: **APPROVE**（注記3つ）。実物で r1_count.py が 226・65・161 を出すこと、Superseded が 4 本であること、同じ番号のファイルが2つ以上ある番号が 15 個（状態が違うのは 10 個、除外になるのは ADR-138 だけ）であることを確かめた。注記への対応: ADR-138 は password_hash の行から外し、ファネルのファイルは中身に合う行に載せると書き直した／同じ番号が除外の節と正準欄の両方に出てよい場合を決めた／表の項目名の `*` を取り、`| 項目 | 内容 |` の表でも状態を読むと決めた。
- 6回目（2026-11-21、マージ前の審査役 Opus、PR #5646・対象 de1d143a2）: **APPROVE**（枝が main より古いことだけがマージを止める点。指摘8つ）。直した点: 便2 の印に書く中身を機能キーワードに揃えた／試験の job は便3 が作り便2 が step を足すと書き、合流の順（便1 と便3 → 便2）を書いた／便1 の貼る行を 11 行に直した／R4 補助の数え方を quiz/count.py に合わせて kgi に書いた／状態の欄を直した／§2 と README の境界に触るファイルを足した／カード3枚へのリンクを足した／recon の行番号のずれ・見張りの一覧の漏れ・古い数え方の説明を直した。あわせて便3 の見張りは、公式の hooks 説明（Stop の入力 `last_assistant_message`。transcript は書き終わる前に読まれることがあるため、こちらが勧められている）に従い、判定する文に `last_assistant_message` を優先し、無いときだけ transcript の最後の文を使うと決めた（card-bin3 §3-1・§3-3 も同じに直した）。
- 便2b の追加（2026-11-21、Opus）: 変更後の測定で R2 17/20・R3 2/20 となり、原因が `Bash` で読む道の入れ忘れだったため §3 に便2b を足した。PO の方向の承認: 2026-11-21 チャット「1」（「写すときも声をかけるように直し、もう一度20回解かせて確かめる」への回答）。クラウドの設計審査（2026-11-21）は REVISE（直す点3つ: 着手の前提・手順7 の合格の○×・確認用 session_id の付け替え。注記: 拾えない書き方の明記・試験の言い方の揃え・時間の上限）で、6 点とも design・カードに入れた。
