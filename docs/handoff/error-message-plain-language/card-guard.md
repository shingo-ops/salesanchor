---
mode: handoff
---
# 実装カード 便0: 失敗の文の決まりを機械で守る見張り（G1・W1・W2）

親: [design.md](./design.md) §2-2（A1・A2）・§5・§8・§11。ADR: [ADR-1071](../../adr/ADR-1071-plain-language-error-messages.md)。

- 状態: カード作成済み（2026-11-08 Opus）。
- 実装承認: PO 2026-11-08 の選択「1」（アプリ全体の決まりで進める。まず止める仕組みを作り、その後に今の文を画面ごとに直す）。同日 PO が「マージ、デプロイまで完走」を委任。マージと本番への反映の GO は Opus が委任（ADR-1003）に基づき別に出す。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 区分: 試験・検査の台本・CI の変更の判定条件だけ。製品の動き（API・画面）は変えない。migrations・deploy.yml・本番 scripts/ は触らない。
- 作業する枝: `release/error-text-guard`（設計の文書とこのカードが載って push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（見張りを作るだけ。今の文は直さない） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/error-text-guard） | ○（§5 手順1） |
| 6 | 書式は実例で示す（数え方の決まりと自己点検の例を全部書く） | ○（§3） |
| 7 | 合格基準を出力まで縛る（触るファイル以外 0） | ○（§5 手順9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後の文で探す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

## 1. 目的（便0 で起きること）

- G1: サーバーの Discord 連携のファイルだけを変えた PR でも、画面の対応表との突き合わせ試験が走る（今は画面側を変えたときしか走らない穴）。
- W1: サーバーの失敗の応答（`HTTPException` の detail）に、新しく文を直書きすると CI が落ちる。今ある分は基準値の表に記録し、減ったら表を下げるよう CI が促す。
- W2: 画面の文言（`ja.json`）に、失敗の文なのに次にすることが無い文を新しく足すと CI が落ちる。今ある分は基準値の一覧に記録する。
- 今ある文は直さない（便2 以降）。

## 2. 触るファイル（これ以外は触らない）

| # | ファイル | 新規/変更 |
|---|---|---|
| 1 | `.github/workflows/e2e.yml` | 変更（detect-changes の filters に 1 行と注記 2 行） |
| 2 | `backend/tests/test_error_detail_guard.py` | 新規 |
| 3 | `backend/tests/error_detail_baseline.json` | 新規（台本で作る。手で数えない） |
| 4 | `frontend/scripts/check-error-text-next-action.js` | 新規 |
| 5 | `frontend/scripts/error-text-next-action-baseline.json` | 新規（台本で作る。手で数えない） |
| 6 | `frontend/package.json` | 変更（scripts に 1 行・`check:all` に 1 つ足す） |

## 3. 作る中身（design §5・§11 が正。食い違えば design に従い、報告に書く）

### 3-1 `.github/workflows/e2e.yml`（G1）

`detect-changes` の `filters` の `frontend:` の一覧の最後（`- '.github/workflows/e2e.yml'` の行の後）に足す:

```yaml
              # ADR-1071: 画面の対応表とサーバーの理由コードの突き合わせ試験を、サーバーだけ変えた PR でも走らせる。
              # 理由コードの対応表を新しく作ったら、その理由コードを出すサーバーのファイルをここに足す（design.md §8）。
              - 'backend/app/routers/discord_oauth.py'
```

他の行は変えない。

### 3-2 `backend/tests/test_error_detail_guard.py`（W1・新規）

数え方（この決まりのとおりに作る。判断に迷ったら作らずに NEEDS_DECISION）:

1. 対象: `backend/app` の下の全 `.py`（`Path(__file__).resolve().parents[1] / "app"` から `rglob("*.py")`）。キーはそこからの道すじに `app/` を付けた形（例 `app/routers/discord_oauth.py`）。区切りは `/`。
2. 各ファイルを `ast.parse` する。解析に失敗したファイルがあれば試験を赤にする（名前を出す）。
3. `ast.walk` で `ast.Call` を探し、呼び先の名前（`ast.Name` なら `id`、`ast.Attribute` なら `attr`）が `HTTPException` のものだけ見る。
4. detail の取り方: キーワード `detail` があればその値。無ければ位置引数が 2 つ以上あるとき 2 つ目。どちらも無ければ数えない。
5. 違反とするもの（どちらかに当たれば 1 件。1 つの呼び出しは最大 1 件）:
   - (a) detail の式の中（`ast.walk(detail)`）の文字列の定数（`ast.Constant` で値が `str`）のどれかに、日本語の文字（正規表現 `[぀-ヿ一-鿿]`）がある。dict・f 文字列・連結の中も含む。
   - (b) detail が文字列の定数か f 文字列（`ast.JoinedStr`）で、その定数部分をつないだ文字列が識別子の形（正規表現 `^[A-Za-z0-9_.:\-]*$`、空も識別子の形とする）でない。
6. 例外: 呼び出しの行（`node.lineno`）か、そのすぐ上の行に `error-detail-exempt:` と空でない理由（正規表現 `error-detail-exempt:\s*\S`）があれば数えない。
7. ファイルごとの件数（0 のファイルは載せない）を辞書にする。

基準値の表 `backend/tests/error_detail_baseline.json`: `{"app/...py": 件数, ...}`。キーで並べ、2 空白の字下げ、最後に改行。前例 `frontend/scripts/loading-clear-baseline.json` と同じ形。

試験（関数名はこのとおり）:

- `test_detail_guard_self_check`: 数える関数に、文字列で次のソースを渡し、件数を確かめる（一時ファイルを使ってもよい）。
  - `raise HTTPException(status_code=400, detail="入力が正しくありません")` → 1
  - `raise HTTPException(status_code=404, detail="not_found")` → 0
  - `raise HTTPException(404, "Item not found")` → 1（位置引数・英語の文）
  - `raise HTTPException(status_code=403, detail={"reason": "permission_denied"})` → 0
  - `raise HTTPException(status_code=409, detail={"message": "重複しています"})` → 1
  - `raise HTTPException(status_code=400, detail=f"{field}")` → 0
  - `raise HTTPException(status_code=400, detail=f"{field} は必須です")` → 1
  - `raise fastapi.HTTPException(status_code=400, detail="壊れています")` → 1（`ast.Attribute`）
  - 1 行上に `# error-detail-exempt: 外部サービス向けの応答` がある `raise HTTPException(status_code=400, detail="Bad signature")` → 0
  - 1 行上に `# error-detail-exempt:` だけ（理由が空）がある `raise HTTPException(status_code=400, detail="Bad signature")` → 1
  - 上の 10 個をまとめた 1 つのソースで合計 6
- `test_detail_guard_no_increase`: 今の件数が基準より多いファイルが 0 件。赤のときの文は、ファイルごとに `増えた: app/... 基準 N → 今 M`、続けて「サーバーは文を作らず理由コードを返し、文は画面の対応表で出す（ADR-1071）。前例 frontend/src/features/discord-connect/discordConnectError.ts。外部サービス向けなどで文が要るときは、その行かすぐ上の行に error-detail-exempt: <理由> を書く」。
- `test_detail_guard_no_stale_baseline`: 今の件数が基準より少ないファイルが 0 件。赤のときの文は `減った: app/... 基準 N → 今 M（backend/tests/error_detail_baseline.json のこの行を M に下げる。0 なら行を消す）`。
- 解析の失敗は `test_detail_guard_no_increase` の中で赤にする。

試験は DB・ネットワークを使わない（`ast` と `json` と `pathlib` と `re` だけ）。conftest の DB の準備が要る印（marker）は付けない。

基準値の表を作る手順は §5 手順4。表は台本の数え方そのもので作る（手で数えない・手で直さない）。

### 3-3 `frontend/scripts/check-error-text-next-action.js`（W2・新規）

前例 `frontend/scripts/check-loading-clear.js` の形（冒頭の説明・自己点検・増減の両方で赤）に合わせる。ES module（`import`）で書く。

数え方:

1. `frontend/src/locales/ja.json` を読み、葉の文字列を全部集める。キーは階層を `.` でつなぐ。配列の要素は番号を道すじに入れる（例 `a.b.0`）。
2. 失敗の文: 値が正規表現 `/失敗|エラー|できません/` に当たる。
3. 次にすることがある: 値が正規表現 `/もう一度|お試し|連絡|確認して|ください/` に当たる。
4. 違反: 失敗の文で、次にすることが無いもの。
5. 例外: 基準値のファイルの `exempt` に、キーと空でない理由があるものは違反にしない。理由が空（空白だけを含む）の行があれば、それ自体を赤にする。

基準値のファイル `frontend/scripts/error-text-next-action-baseline.json`:

```json
{
  "exempt": {},
  "keys": [
    "（今の違反のキーを並べ替えて全部）"
  ]
}
```

`exempt` は空で作る（今回は誰も例外にしない）。`keys` は台本で作る（§5 手順4）。

赤になる時:

1. 違反なのに `keys` に無い（新しく足した）→ `増えた: <キー>「<文>」`
2. `keys` にあるのに違反でない（直した・消した）→ `減った: <キー>（scripts/error-text-next-action-baseline.json の keys からこの行を消す）`
3. `exempt` の理由が空 → `例外の理由が空: <キー>`

赤のときの最後の説明文（3 行）:

- 「失敗の文には、何が起きたかと次にすることを書く（ADR-1071）。例: 時間切れにより連携できませんでした。もう一度お試しください。」
- 「次にすることの語: もう一度・お試し・連絡・確認して・ください のどれか」
- 「失敗の文でない見出しなどは、scripts/error-text-next-action-baseline.json の exempt にキーと理由を書く」

自己点検（動くたびに最初に行う。失敗したら `自己点検に失敗（数え方が壊れている）` で exit 1）。作り物の辞書で:

- `{ "a": { "x": "保存に失敗しました", "y": "保存に失敗しました。もう一度お試しください。", "z": "エラー" }, "b": ["読み込めません", "読み込めませんでした。管理者に連絡してください。"] }` と、基準 `{ "exempt": { "a.z": "表の見出し" }, "keys": ["a.x"] }` で問題 0 件
- 同じ辞書に `"a.w": "送信できませんでした"` を足すと問題 1 件（増えた）
- 元の辞書で `a.x` を `"保存に失敗しました。もう一度お試しください。"` に変えると問題 1 件（減った）
- 基準の `exempt` を `{ "a.z": " " }` にすると問題 2 件（理由が空・増えた）

成功のときの 1 行: `✅ error-text-next-action: 基準どおり（違反 N 件・例外 M 件）`。

### 3-4 `frontend/package.json`

- `scripts` の `"check:loading-clear"` の行の次に `"check:error-text-next-action": "node scripts/check-error-text-next-action.js",` を足す。
- `check:all` の最後の `\"npm run check:loading-clear\"` の後に ` \"npm run check:error-text-next-action\"` を足す（同じ書き方・空白 1 つで区切る）。
- 他は変えない。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。基準値の 2 つの JSON だけは §5 手順4 の台本の出力で作る。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面・§3 の数え方の決まりで決められない場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。
7. Bash に psql の語を書かない。commit 文は `-m` で渡す。git は 1 命令ずつ流す。
8. 1 つの発言は 600 文字以内。長い報告は番号付きの発言に分ける。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. 作業場所を公式の台本で作る。`<main>` はクラウドが最初に置いたリポジトリの場所（例 `/home/user/salesanchor`）。次を 1 つずつ流し、出力を報告に書く。Bash ツールの timeout 引数は 600000 にする。
   - (1a) `cd <main> && git fetch origin release/error-text-guard main`
   - (1b) `cd <main> && git branch --list release/error-text-guard`。出力が空であること。空でなければ消さずに BLOCKED で終える。`git checkout -B` は使わない。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/error-text-guard`。`--claude` は付けない。出力は head・tail などのパイプに通さない。
   - (1d) `ls -1d "$HOME/worktrees/salesanchor/release-error-text-guard"` と `git -C <main> worktree list`。両方にその場所が出ること。出なければ BLOCKED。以後の `<repo>` はこの場所の絶対パス。
   - (1e) push 済みの枝を普通の merge で取り込む: `cd <repo> && git merge --no-edit origin/release/error-text-guard 2>&1 | tail -10`。続けて `cd <repo> && git merge-base --is-ancestor origin/release/error-text-guard HEAD; echo rc=$?`（合格: rc=0）と `cd <repo> && git log --oneline -3`。衝突したら `git merge --abort` をして BLOCKED（衝突したファイル名を書く）。
   - 台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない。
2. `cd <repo> && git merge-base --is-ancestor origin/main HEAD; echo rc=$?` の結果を記録する（0 でなくても続け、報告に書く）。
2-2. Python 3.12 の venv `/tmp/v312` を作り、依存を入れる。1 つずつ流して出力を報告に書く。
   - (a) `python3.12 --version; echo rc=$?`。rc=0 なら (b1)、0 でなければ (b2) へ。
   - (b1) `python3.12 -m venv /tmp/v312; echo rc=$?`
   - (b2) `uv venv --python 3.12 /tmp/v312; echo rc=$?`。これも 0 でなければ BLOCKED で終える。
   - (c) `/tmp/v312/bin/python --version` が `Python 3.12.` で始まること。違えば BLOCKED。
   - (d) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。rc=0 でなければ BLOCKED。(b2) の uv で作ったときだけ、代わりに `cd <repo>/backend && uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。
   - 以後の `python` はすべて `/tmp/v312/bin/python`。
2-3. frontend の依存を入れる: `cd <repo>/frontend && npm ci > /tmp/npm-ci.txt 2>&1; echo rc=$?` と `tail -20 /tmp/npm-ci.txt`。rc=0 でなければ BLOCKED。
3. §3-1〜§3-4 を Edit／Write で作る。基準値の 2 つの JSON はまだ作らない。
4. 基準値を台本で作る:
   - (4a) W1: 試験ファイルの数える関数を使い、`backend/app` の今の件数で `backend/tests/error_detail_baseline.json` を書き出す。書き出しは試験ファイルに `if __name__ == "__main__":` の入口を作り、`cd <repo>/backend && /tmp/v312/bin/python tests/test_error_detail_guard.py --write-baseline` で書く形にする（数え方を 2 か所に置かないため）。続けて `cd <repo>/backend && /tmp/v312/bin/python -c "import json;d=json.load(open('tests/error_detail_baseline.json'));print(len(d), sum(d.values()))"`。
   - (4b) W2: 同じく台本に `--write-baseline` の入口を作り、`cd <repo>/frontend && node scripts/check-error-text-next-action.js --write-baseline` で `keys` を書く（`exempt` は空）。続けて `cd <repo>/frontend && node -e "const b=require('./scripts/error-text-next-action-baseline.json');console.log(b.keys.length, Object.keys(b.exempt).length)"`。
   - 期待の目安（Opus が 2026-11-08 に origin/main `857fa2721` で数えた値）: W1 は str と f 文字列だけで 722 件（日本語 659・英語の文 63）。§3-2 の (a) は dict などの中の日本語も数えるので、これより多くなる（dict 12・その他 4 が日本語）。W2 は 209 件。違っても止まらず、数を報告に書く。
5. 試験と検査:
   - (5a) `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 -rA tests/test_error_detail_guard.py 2>&1 | tail -30`。timeout 引数は 600000。合格: 3 つ passed・赤 0。
   - (5b) `cd <repo>/frontend && npm run check:error-text-next-action 2>&1 | tail -10`。合格: `✅` の 1 行。
   - (5c) `cd <repo>/frontend && npx eslint scripts/check-error-text-next-action.js 2>&1 | tail -20; echo rc=$?`
   - (5d) `cd <repo>/backend && /tmp/v312/bin/python -m ruff check tests/test_error_detail_guard.py 2>&1 | tail -20` と `cd <repo>/backend && /tmp/v312/bin/python -m ruff format --check tests/test_error_detail_guard.py 2>&1 | tail -5`。赤なら `ruff format` で直し、直したことを報告に書く。
6. 見張りが本当に止めることの確かめ（試しの変更は commit しない。確かめたら必ず元に戻す）:
   - (6a) `backend/app/routers/discord_oauth.py` の関数 `discord_oauth_start` の中で、`{"reason": "permission_denied"}` を `"権限がありません"` に一時的に Edit で変える → (5a) を流し `test_detail_guard_no_increase` が赤で `増えた: app/routers/discord_oauth.py` が出ることを記録 → Edit で元に戻す → `cd <repo> && git diff --stat backend/app 2>&1 | tail -5` が空であること。
   - (6b) `frontend/src/locales/ja.json` の `discordConnect.error.unknown` の文の後ろに、一時的に同じ階層のキー `"tmpGuardCheck": "送信できませんでした"` を Edit で足す → (5b) を流し `増えた: discordConnect.error.tmpGuardCheck` が出て exit 1 を記録 → Edit で元に戻す → `cd <repo> && git diff --stat frontend/src/locales 2>&1 | tail -5` が空であること。
7. 予備（G1 の確かめ）: `cd <repo> && git diff origin/main -- .github/workflows/e2e.yml 2>&1 | tail -20`。足したのが §3-1 の 3 行だけであること。
8. `cd <repo> && git add .github/workflows/e2e.yml backend/tests/test_error_detail_guard.py backend/tests/error_detail_baseline.json frontend/scripts/check-error-text-next-action.js frontend/scripts/error-text-next-action-baseline.json frontend/package.json`
9. `cd <repo> && git diff --cached --stat | tail -20` を報告に書く。合格: 変えたファイルが §2 の 6 個だけ。違えば、違うファイル名を報告に書く。
10. commit: `cd <repo> && PATH=/tmp/v312/bin:$PATH git commit -m "feat(guard): error text guards W1/W2 and G1 trigger (ADR-1071 bin0)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。timeout 引数は 600000。続けて `cd <repo> && git log --oneline -3` と `cd <repo> && git diff origin/main...HEAD --name-only | tail -40` を報告に書く。合格: 設計の文書（`docs/handoff/error-message-plain-language/` の下・`docs/adr/ADR-1071-plain-language-error-messages.md`・`docs/adr/README.md`）と §2 の 6 個だけ。
11. push: `cd <repo> && PATH=/tmp/v312/bin:$PATH git push -u origin HEAD`。timeout 引数は 600000。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/error-text-guard` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 本報告はカード 便0（card-guard、失敗の文の見張り）の実行結果である。続けて、受領確認: カード末尾の合図 END OF CARD（END-OF-CARD-ERRMSG-GUARD）まで読んだ。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. 基準値の数（手順4）と、見張りが止めた確かめの出力（手順6）。
4. §3 と違う作り方をした所の一覧（無ければ「無し」）。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: 理由`、`NEEDS_DECISION: 問い`（理由・問いは文で書く） のどれか1つ。

END OF CARD（END-OF-CARD-ERRMSG-GUARD）
