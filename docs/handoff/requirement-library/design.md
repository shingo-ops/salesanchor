# design — 要件の書類を作業の場面で目に入れる（草案 2026-11-21・審査前）

> この文書は何か: R1〜R4 を合格させる作り方・測り方・守り続ける仕組み。実装カードの元。
> 親: [../../specs/requirement-library/README.md](../../specs/requirement-library/README.md)／現在地: [recon.md](./recon.md)／KGI: [kgi.md](../../specs/requirement-library/kgi.md)／練習問題: [quiz.md](./quiz.md)

## 1. 目的と利用者に見える変化

- 目的: AI が機能に触る前に、その場所の決まり（ADR・設計書）を必ず目にする。決まりと食い違う計画を「不具合」と取り違えない（11/13 の会社の新規登録の件）。
- 変化前: 決まりは索引を自分で引けば見つかる。索引は主要 ADR だけ（151 個が載っていない。recon §2）。
- 変化後: (1) すべての ADR が索引に載るか、載せない理由が書かれる。(2) AI が決まりのあるファイルを開くと、その場で「この場所の決まり」が1回だけ示される。(3) 要件の書類を読まずに「不具合」と結論しかけたら、止めて読ませ、記録に残す。

## 2. 対象と対象外

- 対象: `docs/adr/FEATURE-INDEX.md`（表に「コードの場所」列と除外表を足す）、新しい CI 検査、`.claude/hooks/` の見張り 2 本と `.claude/settings.json` の登録、練習問題の測定。
- 対象外: 製品コード・DB・画面・ADR 本文・`workflow-lint.yml`。

## 3. 作り方（便ごと。各便のあと練習問題で測る）

### 便1 目録を漏れなくする（R1）

- 言葉の決め: R1 の「設計仕様書」は `docs/specs/` 直下のフォルダ（今 56 個）。入れ子（例 `db-ssot/deal-removal`）は親の README から辿れることを既存の `check_doc_index.py` が見ているので、R1 では親フォルダ単位で数える。
- 索引の表の列を「機能キーワード｜正準 ADR｜設計書｜コードの場所｜補足」の 5 列にする（今は 3 列）。
  - 設計書: 索引から見た相対リンク `[…](../specs/<フォルダ>/…)`（入れ子の設計書を直接指してよい）。無ければ `-`。今「正準 ADR」欄にある設計書のリンク（`FEATURE-INDEX.md:21` の bundle-sale・`:47` の specs/README）は設計書欄へ移す。
  - コードの場所: リポジトリ直下からの glob（例 `backend/app/routers/companies.py`）。複数は `、` で区切る。コードを持たない決まり（手順・運用だけ）は `-`。
  - glob の決まり（検査と見張りで同じ）: `/` で区切った段ごとに照らす。`*`・`?` は1段の中だけ（`/` をまたがない）。`**` だけの段は0段以上の何段にも当たる。この照らし方は新しい小さな部品 `scripts/ci/feature_index_lib.py` の1つの関数（索引の表の読み取りと glob の照らしの両方）にだけ書き、検査（便1）と見張り（便2）はどちらもこれを import する。Python 3.12 で動く標準ライブラリだけで書く（`PurePosixPath.full_match` は 3.13 からなので使わない）。
- 151 個の ADR と、索引から指されていない設計仕様書のフォルダを、次の順で振り分ける。
  1. ADR の状態の欄の値（先頭 40 行で `ステータス`・`Status`・`状態` を含む最初の行の、見出しの語を除いた値）の**先頭の語**が Superseded・Deprecated・Rejected・廃止 のどれか → 末尾の新節「索引に載せない ADR・設計仕様書」に「番号かフォルダ｜理由（どれに置き換わったか）」で載せる。値の途中に「置き換え」等があるだけでは除外しない（例 ADR-1039 は Accepted なので載せる）。状態の欄が無い ADR は 2 へ。
  2. それ以外 → ADR の題名と本文の最初の節を読み、既存の行の機能キーワードに当たれば (a) その行の「正準 ADR」欄に足す。当たらなければ (b) 新しい行を作る。手順・運用だけの決まりは「横断・運用・プロセス」節に入れ、コードの場所は `-`。
  3. 設計仕様書のフォルダも同じ。対応する ADR の行の「設計書」欄に載せる。どの行にも当たらず状態が「完了・廃止」なら除外の節へ理由つきで載せる。
- 11/13 の件は (a): 「会社」の行に ADR-097 と `docs/specs/db-ssot/deal-removal/design.md` を足す。
- 練習問題の 10 題の正解の ADR は、必ず「コードの場所」が `-` 以外で 1 つ以上のファイルに当たる行に載せる（便2の見張りが働くため）。glob は実装役が実物で決め、カードの完了報告に 10 行分を貼る。
- 新しい検査 `scripts/ci/check_feature_index.py`（r1_count.py より厳しい数え方）:
  - ADR は「正準 ADR」欄か除外の節の1列目にある番号だけを「載っている」と数える（補足欄の文の中の番号は数えない）。
  - 設計仕様書のフォルダは「設計書」欄か除外の節の1列目のリンクを `docs/adr/` から解いて（`posixpath.normpath`）、`docs/specs/<フォルダ>/` で始まれば「載っている」と数える。
  - 読む表は、見出しの1列目が「機能キーワード」の表と除外の節の表だけ（「ADR 候補バックログ」の表は読まない）。
  - 「コードの場所」が `-` でない行で、glob が `git ls-files` のどのファイルにも当たらなければ失敗。
  - 1 件でも抜けか当たらない glob があれば終了コード 1 と一覧を出す。`doc-index-reachability.yml` の run に検査と試験の2行を足す（この workflow は全 PR で流れる。新しい必須チェックは作らない）。
- 試験 `scripts/ci/test_check_feature_index.py`: ADR の抜け・補足欄だけに書かれた番号・設計仕様書の抜け・当たらない glob・バックログの表の番号を数えない の 5 つの見本と、glob の照らし（`*` が `/` をまたがない・`**` が0段にも当たる）を確かめ、正しい見本で成功する。
- 数が多いので、実装は「検査と試験」と「振り分け」を同じ PR の別 commit にする。振り分けの結果（何をどこへ）を一覧にして PR 本文に貼る。

### 便2 開いた瞬間に決まりを見せる（R2・R3）

- `.claude/hooks/requirement-context.py`（PostToolUse、対象 `Read|Edit|Write|MultiEdit`）: tool_input の file_path を索引の「コードの場所」と照らし、当たった行の「正準 ADR と設計書のパス」を `hookSpecificOutput.additionalContext` で返す。
- パスの照らし方: file_path は絶対パスで来る（作業場所 `~/worktrees/...` でも、クラウドの `/home/user/salesanchor` でも）。file_path のある場所で `git rev-parse --show-toplevel` を流して、その直下からの相対パスにしてから、`scripts/ci/feature_index_lib.py` の照らしの関数で glob と照らす（`fnmatch` は使わない）。索引もその同じ直下の `docs/adr/FEATURE-INDEX.md` を読む（本店の古い写しを読まない）。リポジトリの外のファイルは何もしない。
- 同じ行は1つの会話で1回だけ。印は `${TMPDIR:-/tmp}/requirement-context/<session_id>` に行番号を1行ずつ書く。当たらなければ何も返さない。
- どんな失敗（索引が読めない・入力が壊れている・git が無い）でも終了コード 0 で何も返さず、作業を止めない。
- 登録: `.claude/settings.json` に `"PostToolUse"` 節を新しく足し、`matcher` は `Read|Edit|Write|MultiEdit`、`command` は `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/requirement-context.py"`、`timeout` 5 秒。既存の節は変えない。
- 試験 `.claude/hooks/test_requirement_context.py`: 当たる・当たらない・2回目は黙る・壊れた入力・リポジトリ外 の 5 つ。
- 試験を流す場所: `.github/workflows/agent-hooks-test.yml` に job を1つ足し、`on.pull_request.paths` に `.claude/hooks/requirement-*`・`.claude/hooks/test_requirement_*`・`scripts/ci/feature_index_lib.py`・`docs/adr/FEATURE-INDEX.md` を足す。この workflow の変更は CLAUDE.md の不可逆操作の一覧（`workflow-lint.yml` だけ）に当たらない。
- 文の形:「この場所には決まりがあります: ADR-097（会社はリードの子）。計画の前に docs/specs/db-ssot/deal-removal/design.md を読んでください。」

### 便3 読まずに「不具合」を止める（R4）

- `.claude/hooks/requirement-bug-claim.py`（Stop）: transcript_path を読み、最後の返事に「不具合・バグ」があり、その会話で `docs/adr/` か `docs/specs/` を1度も読んでいなければ、1回だけ `decision: block` で「要件の書類を読んでから判定してください」と返す（`stop_hook_active` が真なら止めない）。
- 「読んだ」の判定: transcript の tool_use のうち、Read の file_path か Bash・Grep・Glob の入力に `docs/adr/` か `docs/specs/` を含むものが1つでもあれば読んだとする（count.py の数え方と同じ考え）。
- 止めた回を `~/.claude/requirement-library/bug-claims.log` に1行ずつ書く（日本時間の日時・session_id・返事の最初の 40 字）。クラウドの使い捨て環境の分は消えるので、R4 の本測定は Mac の会話だけを数えると決める（クラウド分は練習問題の補助で見る）。
- 週1回の数え（便3の成果物）: 既にある `scripts/dev/doc-entry-weekly-check.sh` に、記録の過去 7 日の行数を `BUG_CLAIMS_7D=<数>` で出す節を足す。1 以上なら `add_ng "BUG_CLAIMS_7D=<数>"`（`:20` の関数）で RESULT=NG にする。記録が無いときは `BUG_CLAIMS_7D=0`。
  - このスクリプトは Mac の agent-console の定期作業「入口の文書 週次点検」（毎週月曜 16:00 日本時間・Opus。Mac の `~/Library/Application Support/agent-console/routines.json` で 2026-11-21 に確かめた）が流し、NG なら PO に知らせる。定期作業の設定は変えない。
  - R4 の「今」欄は、便3 の後の最初の月曜の結果で Opus が書く。
- どんな失敗でも終了コード 0 で止めない。試験は 読まずに不具合→止める・読んでから不具合→止めない・stop_hook_active→止めない・壊れた入力 の 4 つ。試験は便2 と同じ `agent-hooks-test.yml` の job で流す。

## 4. 合格の判定

|基準|検証方法|
|---|---|
| R1 索引（正準 ADR 欄・設計書欄）にも除外の節にも無い ADR・設計仕様書のフォルダ 0 | CI `check_feature_index.py` が成功（PR の検査結果に出る抜けの数 0） |
| R2 20 回中 18 回以上で正解の書類を開く | 便2のあと quiz を流し `count.py` の `R2` 値 |
| R3 決まりに触れずに反する計画 0 | 同じ 20 回の答えを quiz.md §2 の表で Opus が判定（`r3-judgement.md`） |
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

## 7. 外部の事例

- 確かめたもの: Eliav（指示を作業の場面に近づけると従う率が上がる趣旨）。出典と数は proposal 原稿の表を Opus が読んで確認済み。
- まだ確かめていないもの: CybeDefend・Vercel・Lance Martin・Coombs・Rulestack の数。**本設計の合格の根拠には使わない**。根拠は自分の練習問題の前後比較だけ。

## 8. 守り続ける仕組み

- 新しい ADR を足すと、索引に行か除外表が無ければ CI が落ちる（便1）。
- 見張りの記録は週1回数える（便3）。数え忘れは agent-console の週次点検で見る。
- 練習問題（quiz）は残し、索引や見張りを変えたら流し直す。

## 9. 審査

- 1回目（2026-11-21 08:12、クラウドの審査役 Sonnet、対象 9799b8e2）: **REVISE**。直した点: R1 の設計仕様書の数え方を KGI に合わせた（設計書欄を新設）／検査は正準 ADR 欄と除外の節だけを数える／振り分けの順番と `-` の使い方を書いた／便2 のパスの照らし方・印の置き場・登録の形を書いた／便3 の「読んだ」の判定・記録の置き場・週次の数え方を書いた／recon の絶対パスを相対に直した。
- 2回目（2026-11-21 08:17、同、対象 2a2a08b7）: **REVISE**。直した点: 除外は状態の欄の先頭の語だけで決める／設計書のリンクは相対リンクを解いて数え、既存の2つを設計書欄へ移す／glob の照らしを共有の部品1つにし、`*`・`**` の意味を決めた／試験を流す workflow を決めた／週次の数えを既にある週次点検のスクリプトに足すと決め、流す定期作業を実物で確かめた。
- 3回目: 審査待ち。
