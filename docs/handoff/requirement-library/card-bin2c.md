---
mode: handoff
---
# 実装カード 便2c: 決まりの中身も声かけの文に入れる（R3）

親: [design.md](./design.md) §3 便2c・§3 便2・§3 便2b・§4（R3 の行）

- 状態: カード作成済み（2026-11-21 Opus）。PO の決定: 2026-11-21 チャット「1」（「新規登録ボタンを消すと決め、決まりを書類に書き、声かけの文にも中身を入れてから測り直す」への回答）。マージの判断は Opus（GO 委任）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・マージ判断。
- 区分: B（見張りの台本とその試験だけ）。
- 枝: `release/requirement-library-bin2c`。着手の前提: このカード・design.md の便2c の節・ADR-097 の「#### 6.」が origin/main にあること。無ければ止める。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（クラウドは push まで） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（文の形を変えるだけ） | ○ |
| 5 | 起点の明示（origin/main から新しい枝） | ○（§5 手順1） |
| 6 | PR 欄の書式 | ○（§6。Opus が書く） |
| 7 | 合格基準を出力まで縛る（触るファイル 2 つ・削除 0 件） | ○（§5 手順6） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（件数の停止なし） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式（停止の3点・終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点 | ○（§4） |

## 1. 目的（便2c で見える変化）

- 会社の行に当たるファイルを読むと、AI に「この場所には決まりがあります: ADR-060・ADR-058・ADR-097・ADR-089・ADR-126・ADR-127。決まりの要旨: 会社はリードの子。作る道は受信箱から送る登録フォームでお客様が登録する道だけ（ADR-097）。画面から手で作る道（顧客情報の「新規登録」ボタン）は直さず撤去する（ADR-097 §6）。…。計画の前に docs/specs/customer-management/README.md・docs/specs/db-ssot/deal-removal/design.md を読んでください。」が渡る。
- 上の例の「…。」は、このカードで中略したしるし。会社の行の補足は 205 字で切られないので、本物の出力には「…」は出ず、補足の全文が入る。
- いつ出るか（拾い方・印・1会話1回）は変えない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `.claude/hooks/requirement-context.py` | 文を作る1行を、補足の欄を入れる形に替える |
| `.claude/hooks/test_requirement_context.py` | 試験を 3 つ足す（今の 10 個は変えない） |

触らないもの: `scripts/ci/feature_index_lib.py`・`docs/adr/FEATURE-INDEX.md`・`.claude/settings.json`・`.claude/hooks/requirement-bug-claim.py`・`.github/workflows/`・製品コード。

## 3. 作るものの決まり（design.md §3 便2c が正）

### 3-1. 文の形

- 今の `sentences.append(f"この場所には決まりがあります: {label}（{kw}）。{tail}")` を、次の決まりの文に替える。`label`・`tail`・`kw`（印に書く）の作り方は変えない。
- `note = row["note"].strip()`。
- `note` が空か `-` なら、文は `f"この場所には決まりがあります: {label}。{tail}"`。
- そうでなければ、先に `note` の最後が `。` ならその `。` を1つ取る（`。。` にしない）。次に `note` が 400 字（Python の `len`）を超えるとき `note = note[:400] + "…"` とする。文は `f"この場所には決まりがあります: {label}。決まりの要旨: {note}。{tail}"`。
- 機能キーワード（`kw`）は文に出さない。

### 3-2. 試験 `test_requirement_context.py`（足す 3 つ）

今の見本のリポジトリの作り方を使う。見本の索引は試験ごとに `docs/adr/FEATURE-INDEX.md` を書き直してよい（`setUp` の見本の索引は変えない）。

1. 今の見本（補足 `補足`）で `backend/app/x.py` を `Read` → `additionalContext` に `決まりの要旨: 補足。` が入り、`見本機能` は入らない。
2. 補足の欄が `-` の索引で同じく読む → `決まりの要旨` が入らない。
3. 補足の欄が `あ` を 401 個並べた文字の索引で同じく読む → `"あ" * 400 + "…"` が入り、`"あ" * 401` は入らない。

## 4. 委任の決まり

- 長く待たない（`sleep` で待たない）。ファイルは Write・Edit で書く。
- 見張り（フック）に止められたら、言い換えて同じことをしない。止められた文と理由を報告する。
- PR は作らない（push まで）。`--no-verify` を使わない。
- 止めるのは次のときだけ: 着手の前提が満たされない／今の 10 個の試験のどれかが文の形を替えると通らない（その試験の名前と出力を報告）／push が拒否された。

## 5. 手順（1 手順 1 コマンド。各コマンドは作業場所のフルパスへの cd で始める）

1. `cd /home/user/salesanchor && git fetch origin main` のあと `bash scripts/new-worktree.sh release/requirement-library-bin2c --claude`（最後の Claude 起動の失敗は無視してよい）。以降は表示された作業場所で行う。
2. 前提の確認: `git ls-tree --name-only origin/main docs/handoff/requirement-library/card-bin2c.md` に1行出ること。`git show origin/main:docs/adr/ADR-097-sa-customer-registration-form.md | grep -c '#### 6. 会社は画面から手で作らない'` が 1 であること。`grep -c 'この場所には決まりがあります: {label}（{kw}）' .claude/hooks/requirement-context.py` が 1 であること。違えば止める。
3. §3-1・§3-2 を作り、`python3 -I .claude/hooks/test_requirement_context.py 2>&1 | tail -20` が成功すること（13 件）。
4. 本物の索引での確かめ（`<作業場所>` は手順1 で表示された実際のパス。流し直すときは session_id の末尾の番号を毎回変える）:
   - `printf '%s' '{"session_id":"card-check-c1","cwd":"<作業場所>","tool_name":"Bash","tool_input":{"command":"sed -n 1,5p backend/app/routers/companies.py"}}' | python3 -I .claude/hooks/requirement-context.py` の出力に `決まりの要旨: 会社はリードの子` と `新規登録` が入ること。
5. commit する（1 commit でよい）。
6. `git diff --name-only origin/main...HEAD` が `.claude/hooks/requirement-context.py`・`.claude/hooks/test_requirement_context.py` の2行ちょうどであること（違えば止める）。あわせて `git diff --stat origin/main...HEAD | tail -4`・`git diff --diff-filter=D --name-only origin/main...HEAD | head -5`（0 件）・`git diff origin/main...HEAD -- .claude/hooks/requirement-context.py` を報告に貼る。
7. `git -C <作業場所> push -u origin release/requirement-library-bin2c` を単独で流す。

## 6. PR（Opus が作る）

- Opus が `gh pr create --base main --head release/requirement-library-bin2c` で作る。クラウドは作らない。

## 7. 完了報告

- 冒頭に「便2c 完了報告」か「便2c 停止報告」。
- 貼るもの（生のまま）: 手順2 の出力・手順3 の試験の出力・手順4 の出力全文・手順6 の出力・push の結果の最後 5 行・`git log --oneline origin/main..HEAD`。
- 停止のときは 3 点: どの手順で・何が出たか・何をしていないか。
- 最後の行に `DONE` か `BLOCKED: <理由>`。
