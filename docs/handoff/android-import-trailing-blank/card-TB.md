# 実装カード TB: Android 取込で本文末尾の空行を除き、同じ投稿の2通目を作らない（便TB）

設計者: Opus（2026-10-12）。PO 決定（原文）: 「本文の最後の空行を取り除いてから比べるようにすれば、2通目は作られません。…この修正は進められます。→進めてくれ」

## 背景（事実・確認済み）
- Android パーサ backend/app/services/tcg_line_android_parser.py:46-47 は空行も `'\n' + line` で本文に足す。投稿がファイル末尾のときは空行が無く、後続投稿があると直後の空行が本文末尾の "\n" になる。
- 再利用判定 backend/app/services/tcg_line_import_svc.py:391-404 は raw_sha256 と raw_text の完全一致。"\n" 1つの差で新しい source_message が INSERT され、前の行は superseded（:449-460）。
- 本番: 同形の組 24 組（初出 2026-09-20）。source_messages 2,534 件中 末尾 "\n" 87・末尾 "\n\n" 3・末尾 半角/タブ/全角空白 70（うち全角 4）。根拠 /tmp/CC報告ファイル/v102-unit-state-set/prod/dup/ingest/・/tmp/CC報告ファイル/android-trailing-nl/tail_kinds.out。

## 0. 着手前の確認（読み取り。前提と違えば NEEDS_DECISION）
0-1. INSERT 経路が _write_source_messages（tcg_line_import_svc.py:431 付近）だけで、import_line_export（:700 付近）と保留ジョブ確定 backend/app/routers/tcg_line_import.py:622 付近の両方がこれを通るか。保留ジョブ（import_jobs.pending_messages）に保存された entry の raw_text/sha256 が、確定時に _write_source_messages へそのまま渡るか。
0-2. entry["raw_text"] と entry["sha256"] を作る場所（build_provider_entries :302 付近）と、_write_source_messages より前にそれらを使う箇所（プレビュー・件数・ログ等）の全列挙（呼び出し元全走査、file:line）。
0-3. 既存テスト: tcg_line_android_parser・tcg_line_import_svc・_write_source_messages のテストファイルと、本文末尾の "\n" を期待しているテストの有無。
0-4. 既存 ADR: `git grep -il -E "line.?import|source_messages|android" docs/adr/` と docs/adr/FEATURE-INDEX.md。該当 ADR 番号と、本変更が触れる記述（再利用判定・raw_text の定義）を報告。
0-5. preflight: `./scripts/dev/executor-preflight.sh`。

## 1. 変更（この2点だけ。パーサの行処理・PC 用パーサ・他の経路は触らない）
1-1. 本文の正規化関数を tcg_line_import_svc.py に1つ置く（既存の sha256_text の近く）。
  - 名前例: `normalize_message_body(text: str) -> str`
  - 動作: 本文の末尾にある「改行と、その後ろの空白だけの行」をすべて取り除く。正規表現 `\n[ \t\r\n　]*\Z` を空文字に置換。
  - 最後の内容行の行末空白（例 "円 "）は残す（既存 70 件の本文と食い違わないため）。先頭・途中は一切変えない。
  - 文字クラスは定数にし、1-2 の SQL と同じ集合（半角空白・\t・\r・\n・U+3000）を使う。
1-2. _write_source_messages の先頭（entry ごと）で raw_text をこの関数で正規化し、sha256 も正規化後の本文から計算し直す（sha256_text）。以降の INSERT・再利用判定はその値を使う。0-1/0-2 で entry を先に使う箇所があり結果が変わるなら NEEDS_DECISION。
1-3. 再利用判定の SQL（:391-404）を次に変える（移行期の取りこぼし防止。既に "\n" 付きで保存された投稿を同じものと見なす）:
  - 変更前: `raw_sha256 = :sha256 AND raw_text = :body`
  - 変更後: `(raw_text = :body OR regexp_replace(raw_text, E'\n[ \t\r\n　]*$', '') = :body)`（scid・line_posted_at の条件はそのまま）
  - 正規表現は 1-1 と同じ文字集合。SQL 文字列内の E'' のエスケープが Python 側で崩れないこと（実 PG テストで確認）。
1-4. 既存の保存データは変更しない（UPDATE・DELETE なし。migration なし）。

## 2. テスト（既存の作法に合わせる）
- normalize_message_body: "a\n"→"a"、"a\n\n"→"a"、"a\n 　\n"→"a"、"a "→"a "（行末空白は残す）、"a\nb"→"a\nb"、""→""、"\na"→"\na"。
- _write_source_messages: 末尾 "\n" 付き entry が来ても、保存される raw_text・raw_sha256 は正規化後。
- 再利用判定（実 PG テストがあればそれで）: 既存行 "本文\n" に対し、新 entry "本文" または "本文\n" → reused（新規 INSERT なし・superseded 更新なし）。既存 "本文" に新 "本文\n" → reused。本文が1文字でも違う → 新規 INSERT（従来どおり）。
- Android パーサの既存テストは不変で通ること。

## 3. 手順
1. `bash scripts/new-worktree.sh release/android-import-trailing-blank --claude` → 0-5。Bash は `cd <worktree> && …` を単独で。
2. 0 → 実装 → テスト → ruff・pytest（変更に関係するテストと tcg_line_import 系全部、PG テストがあれば含む）。npm run check:all は frontend 無変更なら省略理由を記す。
3. このカードを docs/handoff/android-import-trailing-blank/card-TB.md に置く（recon.md・design.md は設計者が書く）。
4. commit（push しない）。

## 停止条件
0 で前提が違う・他の経路を変えないとできない・テストが通らない → NEEDS_DECISION / BLOCKED。フックに止められたら言い換えず止まる。本番 DB・本番コンテナには触れない。最終行 DONE / BLOCKED: / NEEDS_DECISION:。
