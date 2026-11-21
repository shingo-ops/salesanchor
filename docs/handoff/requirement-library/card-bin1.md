---
mode: handoff
---
# 実装カード 便1: 目録を漏れなくする（索引の 5 列化・除外の節・CI 検査）

親: [design.md](./design.md) §3 便1・§4（R1 の行）・§6・§8

- 状態: カード作成済み（2026-11-21 Opus）。設計は審査 5 回目で APPROVE（design §9）。PO の実装承認: 2026-11-21 のチャットで、KGI の選択肢1に「…PRマージ、デプロイまで完走させてくれ。」（全文は会話記録）。マージの判断は Opus（GO 委任）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・マージ判断。
- 区分: B（文書・CI の検査・試験だけ。`migrations/`・`deploy.yml`・本番の `scripts/` を触らない）。
- 枝: `release/requirement-library-bin1`（origin/main から新しく作る）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（クラウドは push まで） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（目録の網羅と検査だけ。見張りは便2・便3） | ○ |
| 5 | 起点の明示（origin/main から新しい枝） | ○（§5 手順1） |
| 6 | PR 欄の書式 | ○（§6。Opus が書く） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外の削除が無いこと） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順4） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式（停止の3点・終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行（ただし §5 手順4 の Superseded 4 本だけは止める） | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・フックに止められたら言い換えない・PR は作らない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。

基準: origin/main 6fb18f607（2026-11-21）。行番号はその時点の目印。

## 1. 目的（便1で見える変化）

- `docs/adr/FEATURE-INDEX.md` に、すべての ADR が「正準 ADR」欄か新しい除外の節のどちらかで載る。設計仕様書のフォルダも「設計書」欄か除外の節で載る。
- 載っていない ADR・設計仕様書が出ると、CI「doc index reachability」が赤になる。
- 練習問題 10 題の正解の ADR が「コードの場所」つきの行に載る（便2 の見張りが使う）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `scripts/ci/feature_index_lib.py`（新規） | 索引の表の読み取り・glob の照らし・ADR の状態の先頭の語の取り出し（design §3 便1 の決まりどおり） |
| `scripts/ci/check_feature_index.py`（新規） | 検査本体 |
| `scripts/ci/test_check_feature_index.py`（新規） | 検査の試験 |
| `.github/workflows/doc-index-reachability.yml` | 今の step の後ろに step「Check feature index」を足す |
| `docs/adr/FEATURE-INDEX.md` | 5 列化・振り分け・除外の節 |
| `docs/handoff/requirement-library/r1_count.py` | 触らない（設計の枝で直し済み。この枝には無い。§5 手順8 は設計の枝のものを使う） |

触らないもの: ADR 本文・`docs/adr/README.md`（自動生成）・`docs/specs/` の中身・`.claude/`・製品コード・`workflow-lint.yml`・必須チェックの設定。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. 部品 `feature_index_lib.py`（標準ライブラリだけ・Python 3.12 で動く・`PurePosixPath.full_match` を使わない）

- `match_glob(pattern, relpath) -> bool`: `/` で区切った段ごとに照らす。`*`・`?` は1段の中だけ（段の中の照らしは `fnmatch.fnmatchcase` を1段ずつ使ってよい）。`**` だけの段は0段以上に当たる。
- `read_index(text) -> (rows, excluded)`: 見出しの1列目が「機能キーワード」の表の行（5 列: 機能キーワード｜正準 ADR｜設計書｜コードの場所｜補足）と、除外の節の表の行を返す。「ADR 候補バックログ」の表は読まない。
- `adr_ids_in(cell)`: 正準 ADR 欄から `ADR-((?:SA-)?\d+)` を拾い、先頭の 0 を除いた番号にする。
- `status_word(text)`: design §3 便1 の 1 の「状態の値の取り方」どおり（先頭 40 行・3 つの形・飛ばす行・`*` の取り方・表の項目名の `*` も取る・`| 項目 | 内容 |` の表も読む）。

### 3-2. 検査 `check_feature_index.py --root <dir>`

- 先頭で `sys.path.insert(0, str(Path(__file__).resolve().parent))` してから `feature_index_lib` を import する。
- 数える ADR: `docs/adr/` 直下で `^ADR-((?:SA-)?\d+)(?=[-_.])` に当たり `.md` で終わるファイル。番号は先頭の 0 を除く（`SA-` つきは `SA-17` の形）。
- 「載っている」: 正準 ADR 欄にある番号、または除外の節の1列目にある番号かファイル名。同じ番号のファイルが2つ以上あるときは design §3 便1 の 1 の最後の2項目どおり（ファイルごとに状態を見る・除外の節のファイル名と正準欄の番号の両方に出てよいのはこの場合だけ・1つでも除外でないファイルがあれば正準欄に要る）。
- 設計仕様書: `docs/specs/` 直下のフォルダ。「設計書」欄か除外の節の1列目のリンクを `docs/adr/` から `posixpath.normpath` で解き、`docs/specs/<フォルダ>/` で始まれば載っている。
- 「コードの場所」が `-` でない行で、glob（`、` 区切り）のどれかが `git ls-files` のどのファイルにも当たらなければ失敗。
- 出力: 抜けた ADR・抜けた設計仕様書・当たらない glob・両方に出てはいけない番号 を1行ずつ。最後に `SUMMARY missing_adr=<n> missing_spec=<n> dead_glob=<n> dup=<n>`。1 件でもあれば終了コード 1。

### 3-3. 試験 `test_check_feature_index.py`

- 一時フォルダに小さな見本のリポジトリ（`git init` して `git add`）を作って検査を流す。見本は design §3 便1 の試験の 5 つ（ADR の抜け・補足欄だけの番号は数えない・設計仕様書の抜け・当たらない glob・バックログの表の番号を数えない）＋同じ番号の2ファイル（片方 Superseded）＋正しい見本（成功）。
- glob: `backend/*.py` が `backend/a/b.py` に当たらない・`backend/**/b.py` が `backend/b.py` にも `backend/a/c/b.py` にも当たる。
- 状態: `| **状態** | Accepted |`・`**Status**: Superseded by ADR-1`・`## Status` の次の行 `Deprecated`・`ステータス：廃止（…）` の 4 形。
- `python3 -I scripts/ci/test_check_feature_index.py` で流れ、失敗があれば終了コード 1。unittest でよい。

### 3-4. CI

- `.github/workflows/doc-index-reachability.yml` の step「Check doc index reachability」（`exit "$rc"` で終わる）は変えない。その後ろに次を足す:

```yaml
      - name: Check feature index
        shell: bash
        run: |
          python3 -I scripts/ci/check_feature_index.py --root .
          python3 -I scripts/ci/test_check_feature_index.py
```

### 3-5. 索引 `FEATURE-INDEX.md`

- 冒頭の説明の「主要ドメインの正準 ADR だけを人手でキュレートする」を「すべての ADR を、正準 ADR 欄か末尾の『索引に載せない ADR・設計仕様書』のどちらかに載せる。CI（check_feature_index.py）が抜けを落とす。」に書き換える。
- 機能キーワードの表をすべて 5 列にする。既存の行の設計書欄は `-`、コードの場所は実物で決める（決まらなければ `-`）。正準 ADR 欄の設計書リンク（bundle-sale の行・「設計仕様書 / あるべき姿」の行の specs/README・「標準ワークフロー」の行の STANDARD-WORKFLOW.md）は設計書欄へ移す（STANDARD-WORKFLOW.md は `docs/specs/` ではないので設計書欄に置くだけで数えには入らない）。
- 振り分けは design §3 便1 の 1〜3 の順。password_hash の行は正準欄を ADR-1013 にし ADR-138 を外す。24時間保守運用の行から ADR-1009 を外す。`ADR-138-funnel-dashboard-stage1.md` は中身に合う行（無ければ新しい行）へ。
- 会社の行（「会社 / 顧客情報 …」）に ADR-097 と設計書 `[deal-removal](../specs/db-ssot/deal-removal/design.md)` を足し、補足に「会社はリードの子。受信箱から送る登録フォームでお客様が登録して作る」を足す。
- 練習問題の正解の ADR（097・1076・1083・1027・1022・1037・1032・1062・1056・1078・1071）の行は、コードの場所を `-` 以外にし、1 つ以上のファイルに当たる glob にする。それぞれの ADR 本文が名指ししているファイル・フォルダから選ぶ。
- 末尾（「ADR 候補バックログ」の前）に節「## 索引に載せない ADR・設計仕様書」と表 `| 番号・ファイル名・フォルダ | 理由（どれに置き換わったか） |` を足す。

## 4. 委任の決まり

- 長く待たない（`sleep` で待たない）。ファイルは Write・Edit で書く（heredoc で長い文を書かない）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。止められた文と理由を報告して続けられる手順へ進む。
- PR は作らない（push まで）。`--no-verify` を使わない。
- 止めるのは次のときだけ: (1) §5 手順4 で除外になる ADR が 4 本（ADR-020・ADR-028・ADR-1009・ADR-138 の remove-password-hash）と違う (2) push が拒否された (3) design.md と実物が食い違い、どちらに従うか決められない。それ以外の数の食い違いは記録して続ける。

## 5. 手順（1 手順 1 コマンド。各コマンドは作業場所のフルパスへの cd で始める）

1. `cd /home/user/salesanchor && git fetch origin main release/requirement-library-design` のあと `bash scripts/new-worktree.sh release/requirement-library-bin1 --claude` で作業場所を作る（最後の Claude 起動の失敗は無視してよい）。以降は表示された作業場所で行う。
2. 設計を読む: `git show origin/release/requirement-library-design:docs/handoff/requirement-library/design.md` を全部読む。
3. §3-1〜§3-3 の 3 ファイルを作り、`python3 -I scripts/ci/test_check_feature_index.py` が成功することを確かめて commit する（commit 1: 検査と試験。CI の step もこの commit に入れる）。
4. `python3 -I scripts/ci/check_feature_index.py --root .` を流し、出力を `/tmp/CC報告ファイル/bin1-before.txt` に保存する（`| tail -5` で SUMMARY を見る）。状態で除外になる ADR ファイルの一覧を、部品の `status_word` を使う短い台本で `/tmp/CC報告ファイル/bin1-superseded.txt` に出し、ファイル名を全部報告に貼る。4 本と違えば止める。
5. §3-5 のとおり索引を直す。振り分けの結果を `/tmp/CC報告ファイル/bin1-assign.tsv`（`番号かフォルダ\t行の機能キーワードか除外\t理由`）に書く。
6. `python3 -I scripts/ci/check_feature_index.py --root .` が終了コード 0・`SUMMARY missing_adr=0 missing_spec=0 dead_glob=0 dup=0` になるまで直す。`python3 -I scripts/ci/check_doc_index.py --root . --strict | tail -3` も成功すること。
7. commit する（commit 2: 振り分け）。
8. `git show origin/release/requirement-library-design:docs/handoff/requirement-library/r1_count.py > /tmp/r1_count.py` のあと `python3 -I /tmp/r1_count.py . | head -3` を流し、出力を報告に貼る（索引の形が変わったので数えの値は参考。食い違いは記録だけ）。
9. `git diff --stat origin/main...HEAD | tail -8` と `git diff --diff-filter=D --name-only origin/main...HEAD | head -5`（削除が 0 件であること）を報告に貼る。
10. `git push -u origin release/requirement-library-bin1` を単独で流す（pre-push の検査が走る）。

## 6. PR（Opus が作る）

- Opus が `gh pr create --base main --head release/requirement-library-bin1` で作る。クラウドは作らない。

## 7. 完了報告

- 冒頭に「便1 完了報告」か「便1 停止報告」。
- 貼るもの（生のまま・全文）: 手順3 の試験の出力の最後 20 行・手順4 の SUMMARY と Superseded の一覧・手順5 の `bin1-assign.tsv` 全行・手順6 の SUMMARY・手順8・手順9 の出力・push の結果の最後 5 行・commit の `git log --oneline origin/main..HEAD`。
- 練習問題の正解の ADR 11 個の行（機能キーワード｜正準 ADR｜コードの場所）を貼る。
- 停止のときは 3 点: どの手順で・何が出たか（生出力）・何をしていないか。
- 最後の行に `DONE` か `BLOCKED: <理由>`。
