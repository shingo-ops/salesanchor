---
mode: handoff
---
# 実装カード 便3a-2: 本番の backend を作る入れ替え手順に、読み上げの鍵のつなぎを足す（鍵そのものは置かない）

親: [design.md](./design.md) §4-9・§12・§14。前の便: [card-bin3a.md](./card-bin3a.md)（#5585 本番反映済み・本番の backend には届かなかった）

- 状態: カード作成済み（2026-11-18 Opus）。PO 実装承認: 2026-11-18 の便3a 完了報告への PO の答え「1」（選択肢「手順書に鍵のつなぎ先を足す作業を、設計から本番反映まで進める【おすすめ】」）。
- 本番の鍵ファイルを置くこと・VPS の `.env` に値を書くことは、この便に入らない（便3b。PO 本人に直前にもう一度確かめる。kgi.md §3）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: B（本番 `scripts/blue-green-cutover.sh` を触る＝ADR-136 の危険 PR。GO は委任の範囲で Opus が発行し、GO 記録を PR 本文に書く）。`migrations/`・`deploy.yml`・backend のアプリのコード・`docker-compose.yml` は触らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力） | ○（§7） |
| 4 | 1便1目的（入れ替え手順に読み上げの鍵のつなぎを足し、同じ種類の入れ忘れを試験で止める） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外のファイルが無いこと） | ○（§5 手順6） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4・§6） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。

基準: origin/main 27a932373（2026-11-18 01:55・#5585 合流後）。行番号はこの時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便3a-2 で起きること）

### 1-1. 何が起きたか（Opus が 2026-11-18 02:00 ごろ本番で読み取りだけで確かめた事実）

- 本番の backend の箱（`astro-webapp-backend-1`）は `docker-compose.yml` からではなく、`scripts/blue-green-cutover.sh:85-109` の `docker run` で作られる（`.github/workflows/deploy.yml:519-524`）。
- そのため便3a で `docker-compose.yml` に足した 2 行は本番の箱に届かない。反映後の本番の箱に `GOOGLE_TTS_SA_KEY_FILE` の環境の値は無く（名前の数 0）、`/run/google-tts-sa.json` へのつなぎも無い（つなぎは tcg-sheets・attachments・geoip の 3 つ）。
- `scripts/blue-green-cutover.sh:84` は `.env` のキーを名前だけで渡す。鍵の場所を `.env` に書くと、VPS 上の場所（例 `/home/ubuntu/...`）がそのまま箱に入り、つなぎが無いので読めない。
- この入れ忘れを止めるはずの試験 `backend/tests/test_bg_cutover_volume_parity.py:28` は、`$` で始まる置き場（鍵ファイル）を対象から外し、環境の値は見ていない。2026-11-04 の geoip の入れ忘れ（ADR-1055 段C）と同じ種類の 2 回目。

### 1-2. 直す形

- 入れ替え手順の `docker run` に、compose の backend と同じ形のつなぎを足す。`.env` に `GOOGLE_TTS_SA_KEY_FILE` があり、そのファイルが VPS に在るときだけ、①そのファイルを箱の中の `/run/google-tts-sa.json` に読み取り専用でつなぎ、②箱の中の `GOOGLE_TTS_SA_KEY_FILE` を `/run/google-tts-sa.json` にする。
- `.env` に場所が書いてあってもファイルが無いときは、つながず警告の行を出し、入れ替えは続ける（読み上げは 503 のまま。反映全体を止めない）。`docker run --volume` は、無いファイルを指すとその場所に空のフォルダを作るため、先に `-f` で確かめる。
- `GOOGLE_TTS_SA_KEY_FILE` は名前だけで渡す一覧から外す（VPS 上の場所が箱に入らないようにする。同じ名前を 2 回渡したときの順番に頼らない）。
- 試験を 2 つ足し、同じ種類の入れ忘れを CI で止める（§3-2・§3-3）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `scripts/blue-green-cutover.sh` | §3-1 |
| `backend/tests/test_bg_cutover_volume_parity.py` | §3-2（試験を 2 つ足す。今ある 2 つの試験は変えない） |
| `backend/tests/test_bg_cutover_tts_key.py` | §3-3（新規） |
| `docs/handoff/secretary-voice/card-bin3a2.md` | このカード（手順1 の早送りで入る。中身は変えない） |
| `docs/handoff/secretary-voice/design.md` | §4-9 の追補（手順1 の早送りで入る。中身は変えない） |
| `docs/handoff/secretary-voice/review-opus.md` | 便3a-2 の設計の確かめの記録（手順1 の早送りで入る。中身は変えない） |

## 3. 作るものの決まり

### 3-1. `scripts/blue-green-cutover.sh`

- 目印 83-84 行の `ENV_ARGS=()` と `while` の行を、次の形にする（`GOOGLE_TTS_SA_KEY_FILE` を飛ばす `continue` を足すだけ）:

```bash
ENV_ARGS=()
while IFS= read -r _k; do
  # ADR-1080 便3a-2: 読み上げの鍵の場所は下の TTS_ARGS で箱の中の場所に置き換えるので、名前では渡さない
  [ "$_k" = "GOOGLE_TTS_SA_KEY_FILE" ] && continue
  ENV_ARGS+=(--env "$_k")
done < <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "${REPO_DIR}/.env" | tr -d '=')
```

- その直後（`docker run -d \` の前）に次を足す:

```bash
# ADR-1080 便3a-2: 読み上げ（Google Text-to-Speech）の鍵。docker-compose.yml の backend と同じ形
# （環境 GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json・鍵ファイルを /run/google-tts-sa.json に読み取り専用でつなぐ）。
# .env に場所があり、そのファイルが在るときだけつなぐ。無ければつながない（読み上げは 503 のまま・入れ替えは続ける）。
TTS_ARGS=()
if [ -n "${GOOGLE_TTS_SA_KEY_FILE:-}" ]; then
  if [ -f "${GOOGLE_TTS_SA_KEY_FILE}" ]; then
    TTS_ARGS=(--volume "${GOOGLE_TTS_SA_KEY_FILE}:/run/google-tts-sa.json:ro" --env GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json)
    echo "  読み上げの鍵: つなぐ"
  else
    echo "  ⚠️ 読み上げの鍵: .env の場所にファイルが無いのでつながない（読み上げは 503 のまま）"
  fi
else
  echo "  読み上げの鍵: .env に場所が無いのでつながない"
fi
```

- `docker run` の引数の `"${ENV_ARGS[@]}" \` の行の次に `  "${TTS_ARGS[@]}" \` を 1 行足す。
- 鍵の場所の値（パス）を echo しない。ほかの行は変えない。

### 3-2. `backend/tests/test_bg_cutover_volume_parity.py` に足す試験 2 つ

1. `test_cutover_has_every_backend_fixed_file_mount`: compose の backend の `volumes` のうち、文字列で、つなぎ元が `$` で始まり、つなぎ先（2 つ目）が `/` で始まるもの（今は `${GOOGLE_TTS_SA_KEY_FILE:-/dev/null}:/run/google-tts-sa.json:ro` の 1 つ）を拾う。拾えた数が 1 以上であることを確かめ、それぞれについて、入れ替え手順に `--volume "<何か」:「つなぎ先」[:ro]"` の形がちょうど 1 つあることを確かめる（正規表現 `--volume\s+"[^"]*:` ＋ つなぎ先 ＋ `:ro`（読み取り専用のとき）＋ `"`）。無ければ名前つきで落とす。
2. `test_cutover_sets_every_replaced_backend_env`: compose の backend の `environment` のうち、値が `${名前:+置き換え}` の形のもの（今は `GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:+/run/google-tts-sa.json}` の 1 つ）を拾う。拾えた数が 1 以上であることを確かめ、それぞれについて、入れ替え手順に `--env 名前=置き換え` がちょうど 1 つあり、かつ `[ "$_k" = "名前" ] && continue` がちょうど 1 つあることを確かめる。無ければ名前つきで落とす。

- 冒頭の説明文（docstring）の最後に 1 行足す: 「鍵ファイルを固定の場所につなぐ行と、値を置き換える環境の行も同じく見る（ADR-1080 便3a: 読み上げの鍵の入れ忘れ）。」

### 3-3. `backend/tests/test_bg_cutover_tts_key.py`（新規）

偽の `docker` を `PATH` の先頭に置き、本物の `scripts/blue-green-cutover.sh` を `bash` で流して、`docker run -d` に渡った引数を確かめる。本物の docker・VPS・ネットワークには触れない。

- 準備（pytest の `tmp_path` の中）: `REPO_DIR` に使うフォルダを作り、その中に `.env` を書く。偽の `docker` は、受けた引数を 1 呼び出し 1 行で `calls.log` に足し、`ps` は何も出さず終了 0、それ以外（`image inspect`・`run`・`exec`・`network`・`inspect`・`stop`・`rm`・`rename`・`update`）は終了 0。
- 流し方: `subprocess.run(["bash", 「リポジトリの scripts/blue-green-cutover.sh」], env={"PATH": "「偽のbin」:" + 元の PATH, "REPO_DIR": 「tmp の場所」, "BG_HEALTH_TIMEOUT": "3"}, timeout=60)`。終了 0 を確かめる（health の待ちで 3 秒かかる）。
- `calls.log` の `run -d` で始まる行を 1 行取り出して見る。3 つの場合:
  1. 鍵ファイルが在る（`.env` に `GOOGLE_TTS_SA_KEY_FILE=「tmp に作った空の json の場所」` と `OTHER_KEY=x`）: `--volume 「その場所」:/run/google-tts-sa.json:ro` と `--env GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json` がある。`--env GOOGLE_TTS_SA_KEY_FILE`（`=` が続かない形）は無い。`--env OTHER_KEY` はある。
  2. `.env` に場所はあるがファイルが無い: `/run/google-tts-sa.json` を含まない。`GOOGLE_TTS_SA_KEY_FILE` を含まない。標準出力に「ファイルが無いのでつながない」がある。
  3. `.env` に `GOOGLE_TTS_SA_KEY_FILE` が無い（`OTHER_KEY=x` だけ）: `/run/google-tts-sa.json` を含まない。`GOOGLE_TTS_SA_KEY_FILE` を含まない。
- 調べる語は空白で区切った引数の並びで比べる（`calls.log` は `"$*"` の 1 行なので、`split()` した並びの中に `--volume` の次が `「場所」:/run/google-tts-sa.json:ro` であることを見る）。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントや python/cat で書かない。
- PR は作らない（§6）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／§2 の表に無いファイルを変えないと確かめが通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く。
- 本番・Google に接続しない。鍵の値・本物の `.env` を作らない・読まない（試験の中の `tmp_path` の `.env` は作ってよい）。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降は毎回その作業場所へ cd してから流す。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/secretary-voice-bin3a2-impl
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。違えば NEEDS_DECISION: で止まる。
    cd 作業場所 && git merge --no-edit origin/release/secretary-voice-bin3a2
    期待する出力: このカード・design.md の追補・設計の確かめの記録が入る（main が進んでいれば早送りでなく取り込みの commit が 1 つできるが、それで良い）。衝突が出たら NEEDS_DECISION: で止まる。

手順2 §3-1・§3-2・§3-3 を作る。

手順3 台本の形の確かめ
    cd 作業場所 && bash -n scripts/blue-green-cutover.sh
    cd 作業場所 && grep -n "GOOGLE_TTS\|google-tts\|TTS_ARGS" scripts/blue-green-cutover.sh
    期待する出力: 1 つ目は何も出ず終了 0。2 つ目は §3-1 の行だけ。

手順4 試験（pip は直に使わない。py312-guard の案内どおり 3.12 の venv を作り、その中の python を使う）
    cd 作業場所 && (python3.12 -m venv /tmp/venv312 || uv venv --python 3.12 /tmp/venv312) && /tmp/venv312/bin/python -m pip install -q pytest pyyaml
    期待する出力: エラーなし。venv が作れない・入らないときは、その出力を書いて手順5 へ進む（CI で確かめる）。
    cd 作業場所/backend && /tmp/venv312/bin/python -m pytest tests/test_bg_cutover_volume_parity.py tests/test_bg_cutover_tts_key.py -q -p no:cacheprovider
    期待する出力: 全部合格（今ある 2 つ＋足した 2 つ＋新規 3 つ）。手元で pytest が動かない（依存が入らない）ときは、その出力を書いて手順5 へ進む（CI で確かめる）。
手順4 の続き（§3-1 を戻した状態で落ちることを確かめる）
    cd 作業場所 && git stash push scripts/blue-green-cutover.sh
    cd 作業場所/backend && /tmp/venv312/bin/python -m pytest tests/test_bg_cutover_volume_parity.py tests/test_bg_cutover_tts_key.py -q -p no:cacheprovider
    期待する出力: §3-2 の足した 2 つと、§3-3 の場合1・場合2 が落ちる（場合3 は戻しても合格のまま）。
    cd 作業場所 && git stash pop
    cd 作業場所 && git diff --stat
    期待する出力: §3-1 が戻っている（scripts/blue-green-cutover.sh に差分がある）。

手順5 commit
    cd 作業場所 && git add scripts/blue-green-cutover.sh backend/tests/test_bg_cutover_volume_parity.py backend/tests/test_bg_cutover_tts_key.py
    commit 文は Write でファイルに書き（1行目 `fix: wire the read-aloud key into the blue-green backend run (ADR-1080 bin3a-2)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat

手順6 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表の 6 ファイルだけ。表に無いファイルがあれば名前を書いて止まる。

手順7 push（PR は作らない）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/secretary-voice-bin3a2-impl
    期待する出力: 手順5 の commit と同じ番号。

## 6. 受入条件と PR

| 基準 | 検証方法 |
|---|---|
| 鍵ファイルが在るとき、入れ替えで作る箱に `/run/google-tts-sa.json` のつなぎと `GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json` が入る。VPS 上の場所は値として入らない | §3-3 の場合1（CI） |
| ファイルが無い・場所が無いとき、どちらも入らず、入れ替えは終了 0 | §3-3 の場合2・3（CI） |
| compose にある鍵ファイルのつなぎ・置き換えの環境を入れ替え手順に入れ忘れると CI が落ちる | §3-2（CI）・手順4 の戻した状態で落ちること |
| 鍵が無い今、本番の backend は今と同じ（`GOOGLE_TTS_SA_KEY_FILE` の名前の数 0・つなぎ 3 つ）・反映が成功し健康 | 反映後に Opus が本番の箱を読み取りで確かめる。deploy の結果・`/api/health` |
| 触るのは §2 の 6 ファイルだけ | Opus が `git diff --stat` で照合 |

PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使い ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。欄の良い例: `触るファイル: scripts/blue-green-cutover.sh, backend/tests/test_bg_cutover_volume_parity.py, backend/tests/test_bg_cutover_tts_key.py, docs/handoff/secretary-voice/card-bin3a2.md, docs/handoff/secretary-voice/design.md, docs/handoff/secretary-voice/review-opus.md`（1行・カンマ区切り）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。`区分: B`・`対象ADR: ADR-1080`・GO 記録の節あり。

## 7. 報告

- 冒頭に「本報告はカード 便3a-2（入れ替え手順の読み上げの鍵）の実行結果である」と書く。
- 受領確認: 最初に「カード 便3a-2 を受領」と1行書く。
- 手順1・3・4・5・6・7 の要点の行を生で貼る。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容`。

END OF CARD
