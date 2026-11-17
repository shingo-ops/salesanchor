---
mode: handoff
---
# 実装カード 便3a: 読み上げの鍵の置き場を backend の設定に足す（鍵そのものは置かない）

親: [design.md](./design.md) §4-9・§12・§14。前の便: [card-bin2b.md](./card-bin2b.md)（#5582 本番反映済み）

- 状態: カード作成済み（2026-11-18 Opus）。PO 実装承認: 2026-11-18 の便2b 完了報告への PO の答え「1」（選択肢「鍵を置く作業に進む【おすすめ】」）と「PRマージ、デプロイまで完走させてくれ」。
- 本番の鍵ファイルを置くこと・VPS の `.env` に値を書くことは、この便に入らない（便3b。PO が鍵を作った後、PO 本人に直前にもう一度確かめる。kgi.md §3）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: A（`docker-compose.yml` の backend の 2 行だけ。`migrations/`・`deploy.yml`・本番 `scripts/`・backend のコードを触らない）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力） | ○（§7） |
| 4 | 1便1目的（鍵の置き場の 2 行だけ） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外のファイルが無いこと） | ○（§5 手順5） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順5） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4・§6） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。

基準: origin/main dba18c50d（2026-11-18・#5583 合流後）。行番号はこの時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便3a で起きること）

backend が読み上げの鍵ファイルを読めるように、`docker-compose.yml` の backend に「鍵の場所」と「鍵ファイルを読み取り専用でつなぐ」2 行を足す。VPS の `.env` に `GOOGLE_TTS_SA_KEY_FILE` が無い今は、backend の環境の値が空になり、今と同じく読み上げは 503（`tts_not_configured`）を返す（`backend/app/services/secretary_tts.py:72-74`）。

### 1-1. design.md §4-9 からの変え方（Opus の設計の追補）

design.md §4-9 は「形は `docker-compose.yml:127`・`:162` と同じ」としていた。その形（`${X:-/dev/null}:${X:-/dev/null}:ro`）をそのまま写すと、鍵が 2 つとも未設定の環境（CI・手元）で backend に `/dev/null:/dev/null:ro` が 2 本並び、つなぐ先が重なる。重なったときの Docker の動きは確かめていない。そこで、つなぐ先を読み上げ専用の固定の場所にし、重ならない形にする。値の有無で切り替えるのは Compose の `${VAR:+replacement}`（値があれば replacement、無ければ空。Docker 公式 `reference/compose-file/interpolation.md`、2026-11-18 Context7 で確認）。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `docker-compose.yml` | §3（backend の `environment` に 1 行・`volumes` に 1 行） |
| `docs/handoff/secretary-voice/card-bin3a.md` | このカード（手順1 の早送りで入る。中身は変えない） |
| `docs/handoff/secretary-voice/design.md` | §4-9 の追補（手順1 の早送りで入る。中身は変えない） |

celery-worker・celery-beat・ほかのサービスは変えない（読み上げを呼ぶのは backend だけ）。

## 3. 作るものの決まり（`docker-compose.yml` の `backend:` の中だけ）

- `environment:` の `- WEBPUSH_VAPID_SUBJECT=${WEBPUSH_VAPID_SUBJECT:-}` の行（目印 158 行）の次に、次の 2 行を足す:
  - `      # ADR-1080 便3: 読み上げ（Google Text-to-Speech）の鍵。.env に GOOGLE_TTS_SA_KEY_FILE（VPS 上の鍵ファイルの場所）があるときだけ値が入り、無ければ空（読み上げは 503）`
  - `      - GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:+/run/google-tts-sa.json}`
- `volumes:` の `- ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro` の行（目印 162 行）の次に、次の 1 行を足す:
  - `      - ${GOOGLE_TTS_SA_KEY_FILE:-/dev/null}:/run/google-tts-sa.json:ro`
- 字下げは周りの行と同じ（空白 6 個＋`- `）。ほかの行は変えない。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントや python/cat で書かない。
- PR は作らない（§6）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／§2 の表に無いファイルを変えないと確かめが通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く。
- 本番・Google に接続しない。鍵の値・`.env` を作らない・読まない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降は毎回その作業場所へ cd してから流す。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/secretary-voice-bin3a-impl
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。違えば NEEDS_DECISION: で止まる。
    cd 作業場所 && git merge --ff-only origin/release/secretary-voice-bin3a
    期待する出力: このカードと design.md の追補を足す commit 1 つが早送りで入る。早送りにならなければ NEEDS_DECISION: で止まる。

手順2 §3 を作る。

手順3 形の確かめ（docker が無い環境なら、その旨を書いて 3-2 だけ流す）
    3-1: cd 作業場所 && docker compose config --quiet
    3-2: cd 作業場所 && grep -n "GOOGLE_TTS\|google-tts" docker-compose.yml
    期待する出力: 3-1 は何も出ず終了 0（docker がある場合）。3-2 は注記 1 行・環境の行 1 行・つなぐ行 1 行の 3 行で、3 行とも backend の範囲（`backend:` と `frontend:` の行の間）にある。

手順4 commit
    cd 作業場所 && git add docker-compose.yml
    commit 文は Write でファイルに書き（1行目 `feat: wire the read-aloud key file into backend compose (ADR-1080 bin3a)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat

手順5 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表の 3 ファイルだけ。`docker-compose.yml` は追加 3 行・削除 0 行。表に無いファイルがあれば名前を書いて止まる。

手順6 push（PR は作らない）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/secretary-voice-bin3a-impl
    期待する出力: 手順4 の commit と同じ番号。

## 6. 受入条件と PR

| 基準 | 検証方法 |
|---|---|
| backend の環境に `GOOGLE_TTS_SA_KEY_FILE` が 1 行・つなぐ行が 1 行 | 手順3-2・Opus が diff で照合 |
| 鍵が無い今、本番の backend の `GOOGLE_TTS_SA_KEY_FILE` は空・読み上げの口は今と同じ動き | 反映後に Opus が本番の backend の環境の値の長さ（0）を読む。値は出さない |
| 反映が成功し、backend が健康 | deploy の結果・`/api/health` |
| 触るのは §2 の 3 ファイルだけ | Opus が `git diff --stat` で照合 |

PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使い ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。欄の良い例: `触るファイル: docker-compose.yml, docs/handoff/secretary-voice/card-bin3a.md, docs/handoff/secretary-voice/design.md`（1行・カンマ区切り）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。`区分: A`・`対象ADR: ADR-1080`。

## 7. 報告

- 冒頭に「本報告はカード 便3a（読み上げの鍵の置き場）の実行結果である」と書く。
- 受領確認: 最初に「カード 便3a を受領」と1行書く。
- 手順1・3・4・5・6 の要点の行を生で貼る。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容`。

END OF CARD
