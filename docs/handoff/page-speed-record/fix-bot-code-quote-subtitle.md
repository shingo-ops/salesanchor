# 実装カード: Bot 空欄コードの 500 と見積副題の翻訳漏れ

作成: POの委任に基づくClaude Opus（設計）。2026-10-31。見本データを入れる作業中に本番で見つけた不具合 2 件。

## 最初に読むもの
(1) scripts/agent-hooks/cloud/rules.md（必ず従う）
(2) AGENTS.md の「ブランチと作業場所」

## PO の承認
PO が 2026-10-31 に「見つけた不具合2つを直す」を選んだ（返事「1」）。この直しの実装承認です。範囲は下の 2 件だけ。

## 守ること
- `rm` は使わない。一時フォルダは `mktemp -d` で新しく作る。
- Python は `python3.12 -m venv "$(mktemp -d)/venv"`（無ければ `uv venv --python 3.12 <場所>`）で venv を作り、その venv の bin/pip・bin/python だけを使う。backend の試験に要る依存は backend/requirements*.txt から入れる。どちらでも作れなければ出力全文を書いて BLOCKED:。
- reset・rebase・force・merge・--no-verify は使わない。PR は作らない（コード変更を含むため、手元で作る）。push まで。

## 作業場所
枝 release/fix-bot-blank-code-quote-subtitle は、このカードだけを載せて push 済み。rules.md の「すでに push 済みの枝の続き」の手順で作業場所を作り、`git switch -C release/fix-bot-blank-code-quote-subtitle origin/release/fix-bot-blank-code-quote-subtitle` のあと `git rev-parse HEAD` と `git rev-parse origin/release/fix-bot-blank-code-quote-subtitle` が同じことを貼る。

## 直し 1: Bot をコード空欄で登録すると必ず 500 になる
事実（本番 10/31 に画面で 2 回再現・ログ `StringDataRightTruncationError: value too long for type character varying(20)`）:
- backend/app/routers/bots.py:140 `bot_code = explicit_code if explicit_code else f"BOT-PENDING-{uuid.uuid4().hex}"` → 12+32=44 文字。
- 列は 20 文字まで（migrations/020_create_bots_and_senders_view.sql:33・backend/app/services/tenant.py:670）。INSERT の直後に `BOT-{id:05d}` へ置き換える作り（bots.py:166-169）は正しい。仮の番号だけが長すぎる。
変更:
- bots.py に関数を 1 つ足す（create_bot の上、モジュールの関数として）:
```python
def _pending_bot_code() -> str:
    """自動採番の前に一時的に入れる仮コード。列 VARCHAR(20) に収まる 20 文字。"""
    return f"BOT-P-{uuid.uuid4().hex[:14]}"
```
- bots.py:140 を `bot_code = explicit_code if explicit_code else _pending_bot_code()` に変える。
- それ以外の bots.py の行は触らない。列の長さ・migration・schema は変えない。
試験（backend/tests/test_bots_owner_users.py の末尾に足す。既存の seeded 固定具と書き方に合わせる）:
- `test_pending_bot_code_fits_column`: `_pending_bot_code()` を 100 回呼び、すべて長さ <= 20 で "BOT-P-" で始まること。
- `test_create_bot_blank_code_gets_sequential_code`: `bot_code` に "" を入れた payload（`_payload` の `code or ...` は空文字を置き換えてしまうので、dict を作ってから `payload["bot_code"] = ""` とする）で POST し 201、返った `bot_code` が `f"BOT-{id:05d}"` と等しいこと。record_audit_log は既存試験と同じく patch する。
- 試験の DB は SQLite で長さを強制しないため、長さは 1 つ目の試験で確かめる。

## 直し 2: 見積の新規作成画面の副題が「quotes.createSubtitle」のまま出る
事実: frontend/src/pages/quote-create/QuoteCreatePage.tsx:141 が `subtitleKey="quotes.createSubtitle"` を使うが、frontend/src/locales/ja.json・en.json の "quotes" の塊（1652 行目から）にそのキーが無い。請求書は invoices.createSubtitle があり「新しい請求書を作成します」/「Create a new invoice」。
変更:
- ja.json の "quotes" の塊の "newQuote" の次の行に `"createSubtitle": "新しい見積を作成します",` を足す。
- en.json の同じ位置に `"createSubtitle": "Create a new quote",` を足す。
- tsx は触らない。ほかのキーは触らない。

## 確かめ（それぞれ命令と生出力を貼る）
(1) venv の python で `cd backend && <venv>/bin/python -m pytest tests/test_bots_owner_users.py -q`
(2) `python3 -c "import json;a=json.load(open('frontend/src/locales/ja.json'));b=json.load(open('frontend/src/locales/en.json'));print(a['quotes']['createSubtitle'],'|',b['quotes']['createSubtitle'])"`
(3) frontend の i18n キー一致の点検があれば流す（frontend/package.json の scripts と frontend/CLAUDE.md で探す。無ければ「無い」と書く）。
(4) `git diff --stat origin/main` と `git diff origin/main`

## 記録
このカード（docs/handoff/page-speed-record/fix-bot-code-quote-subtitle.md）の末尾に「## 実装の結果」の節を足し、確かめ (1)〜(3) の生出力を書く。

## commit と push
`fix: Bot空欄コードの500と見積副題の翻訳漏れを直す` で 1 commit（本文の最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`.claude-pipeline/active-work.d/` は commit しない。`git push -u origin release/fix-bot-blank-code-quote-subtitle`。pre-push が × なら直してから push。

## 最後の返事
1 行目に DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い> のどれか。続けて push した HEAD の sha、手順ごとの生出力。

## 実装の結果

(1) `cd backend && <venv>/bin/python -m pytest tests/test_bots_owner_users.py -q`
```
FAIL Required test coverage of 60% not reached. Total coverage: 29.53%
6 passed, 1 warning in 21.55s
```
（1 ファイルだけ流したため全体カバレッジの閾値で FAIL 表示。試験自体は 6 件すべて passed）

(2)
```
新しい見積を作成します | Create a new quote
```

(3) `node scripts/check-i18n-missing-keys.js`
```
✅ i18n key check PASSED (all prefixes)
   viewer 入口から届く viewer 外のファイル: 39 件
```

## 外部・過去事例の参照と我々への応用
外部事例は使わない。理由: 原因は「仮の値が列の長さを超える」という本リポジトリ内の事実（本番ログと migration の列定義）で特定でき、直し方も同じ関数の中の 1 行で閉じるため。
過去事例: 仕入先（SP-{id:05d}）・見積（QT-{id:05d}）は仮コードを入れずに INSERT 後に採番している（backend/app/routers の create_supplier・create_quote）。Bot は bot_code が NOT NULL のため仮コードが要る。そのため仮コードを列に収まる長さにする方を選んだ。

## 維持の仕組み
守り手: backend/tests/test_bots_owner_users.py（CI の pytest）, frontend/scripts/check-i18n-missing-keys.js（CI）
- 仮コードの長さは `test_pending_bot_code_fits_column` が毎回の CI で確かめる。列の長さを変えずに仮コードを長くすると、この試験が落ちる。
- 翻訳キーの抜けは frontend の `check-i18n-missing-keys.js`（CI）が見る。今回の抜けは、この点検が `subtitleKey` に渡す文字列を拾えずに見逃した。点検を広げるかは別の件として扱う（今回の範囲外）。
- 本番の画面の速さの記録（ADR-1053）が毎朝 Bot・見積の画面を開くので、表示の崩れに気づく道が残る。

## 参照と受け入れ基準
- 現在地の調べ: docs/handoff/page-speed-record/recon.md（画面の速さの記録の調べ。今回の不具合は見本データを入れる作業中に本番で見つけた）
- 対象 ADR: ADR-027（画面の文字はすべて翻訳キー経由・ja/en 同じキー）。直し 2 はこの決まりの抜けを埋める。

| 基準 | 検証方法 |
|---|---|
| 仮コードが 20 文字以内 | `test_pending_bot_code_fits_column` が通る（CI の pytest） |
| コード空欄の Bot 登録が 201 で `BOT-{id:05d}` になる | `test_create_bot_blank_code_gets_sequential_code` が通る。本番反映後、tenant 001 で画面からコード空欄で登録し 500 にならないこと（○×） |
| 見積の新規画面の副題が文として出る | 本番反映後に /quotes/new を開き「新しい見積を作成します」と出ること（○×） |
| ja/en のキーが一致 | `check-i18n-missing-keys.js` が PASSED |
