# 実装カード: 固定コマンドの説明の行を今の形に直す（説明だけ）

- 発行: Claude Opus（設計担当）・2026-11-28
- PO 承認: 2026-11-28 しんごさん「1」（説明書きの直しと記録の書き足しをまとめて出す）
- 根拠: docs/handoff/dev-tenant001-writer/bin4-measure.md「便3 (4)」と「追い: 読む鍵」。本番の固定コマンドは本番の `.env` を先に渡す形に直っている。compose の頭の説明だけが古い。
- 区分: 説明の行だけ。動き・設定の値は変えない。

## 触ってよいファイル（この 2 本の、下に書いた行だけ）

1. `docker-compose.ai-dev001-writer.yml` の 4 行目
2. `docker-compose.ai-reader.yml` の 4 行目

## 手順

### 1. 作業場所

- `git fetch origin release/ai-key-fixed-cmd-comment`
- `bash scripts/new-worktree.sh release/ai-key-fixed-cmd-comment --claude` で作業場所を作り、その中でだけ作業する。

### 2. 直す前に実物を確かめる

- `sed -n '3,4p' docker-compose.ai-dev001-writer.yml` の出力が次の 2 行と 1 文字も違わないこと。違えば何も直さず `BLOCKED:` で止める。

```
# 固定コマンド（便3 で authorized_keys に入れる）:
#   docker compose -f <絶対パス>/docker-compose.ai-dev001-writer.yml run --rm -T --no-deps ai-dev001-writer
```

- `sed -n '3,4p' docker-compose.ai-reader.yml` の出力が次の 2 行と 1 文字も違わないこと。違えば止める。

```
# 固定コマンド（便3b で authorized_keys に入れる）:
#   docker compose -f <絶対パス>/docker-compose.ai-reader.yml run --rm -T --no-deps ai-reader
```

### 3. 直す（Edit で 4 行目だけ置き換える）

- `docker-compose.ai-dev001-writer.yml` 4 行目を次の 1 行にする:

```
#   docker compose -f <絶対パス>/docker-compose.ai-dev001-writer.yml --env-file <絶対パス>/.env --env-file <書く役の env>/ai-dev001-writer.env run --rm -T --no-deps ai-dev001-writer（本番の .env を先に渡す。無いと BACKEND_IMAGE が空で古い完成品になる）
```

- `docker-compose.ai-reader.yml` 4 行目を次の 1 行にする:

```
#   docker compose -f <絶対パス>/docker-compose.ai-reader.yml --env-file <絶対パス>/.env --env-file <読む役の env>/ai-reader.env run --rm -T --no-deps ai-reader（本番の .env を先に渡す。無いと BACKEND_IMAGE が空で古い完成品になる）
```

### 4. 直したあとの確かめ（生の出力を報告に貼る）

- `git diff --stat` が 2 ファイル・各 1 行の追加と 1 行の削除だけであること。
- `git diff` の変わった行が、どちらも `#` で始まる行だけであること。
- `python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]; print('yaml ok')" docker-compose.ai-dev001-writer.yml docker-compose.ai-reader.yml` が `yaml ok` を出すこと（yaml が無ければ、その旨を報告に書き、この確かめは飛ばす）。

### 5. 保存

- `git add docker-compose.ai-dev001-writer.yml docker-compose.ai-reader.yml`
- commit 文は Write でファイルに書き、`git commit -F <そのファイル>`。1 行目は `docs(compose): fixed command comments pass production .env first`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push -u origin release/ai-key-fixed-cmd-comment`（force なし）。
- PR は作らない。

## 触らない範囲

- 2 本の 4 行目より後ろ（`image:`・`environment:`・`volumes:` など）。
- ほかの compose ファイル（`docker-compose.ai-reader-http.yml`・`docker-compose.ai-reader-cloud-http.yml`・本体の `docker-compose.yml`）。
- `.github/workflows/`・`migrations/`・`scripts/`・backend・frontend。

## 想定の分岐

- 手順 2 で行が違う → 直さず `BLOCKED: 4 行目が想定と違う` と、実際の 3〜4 行目を貼って止める。
- 見張りに止められた → 言い換えず `BLOCKED:` と止めた見張りの文面を貼って止める。
- push が拒否された → force せず `BLOCKED:` で止める。

## 終わりの報告

- 最後の行は `DONE` か `BLOCKED: <理由>`。
- 手順 4 の生の出力と、push した commit の番号を書く。
