# 実装カード 便1: まとめて〆る投稿の受け取り側（受け取り側のコードと試験だけ）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

- 設計: `docs/handoff/shime-bundle-close/design.md` §3-1・§3-2（設計審査3回目 APPROVE、3e62c569a）
- recon: `docs/handoff/shime-bundle-close/recon.md`
- 実装承認: PO 2026-11-12「1」（指示文と受け取り側の両方を直す）＋ ADR-1003 の委任の下で設計審査 APPROVE。
- 発行: Opus（設計担当）2026-11-12

## カード発行前の照合（design-partner.md §5.5）
| 項目 | 結果 |
|---|---|
| 1 記号を壊さない（パス・名前はバッククォート） | ○ |
| 2 下書き禁止 | ○ PR は作らない（push まで。PR は Opus が作る） |
| 3 報告の宛先 | ○ 最後の発言に生出力を全文 |
| 4 1便1目的 | ○ 受け取り側のコードと試験だけ（指示書・DB は便2・便3） |
| 5 既存ブランチは起点明示 | ○ 新しい枝を new-worktree.sh で作り、設計の枝を merge で取り込む |
| 6 書式は実例で | ○ commit 文の例を下に書いた |
| 7 合格基準を出力まで縛る | ○ 下の「合格の形」 |
| 8 件数と名前を対で | ○ 落ちた試験は名前を出す |
| 9 出力に上限 | ○ pytest は `-q` と `--tb=short`、diff は `--stat` |
| 10 報告の3点 | ○ 下の「報告」 |
| 11 行番号を停止条件にしない | ○ 置き換えは前後の文字で指定 |
| 12 停止は2段 | ○ 下の「止まる条件」 |
| 13 委任文の4点 | ○ sleep 禁止・Write/Edit で書く・PR は作らない（validate は Opus）・止められたら言い換えない |

## 作業場所（この順で。git は1命令ずつ流す）
1. `bash scripts/new-worktree.sh release/shime-bundle-close-bin1 --claude` を流し、出てきた作業場所に入る。以後の作業はその中だけで行う。
2. `git fetch origin` → `git merge --no-ff origin/release/shime-bundle-close-design -m "merge design docs"`（設計書を取り込む。rebase はしない）。
3. `./scripts/dev/executor-preflight.sh` を流す（落ちたら止まる）。

## 直すもの（`backend/app/services/gemini_raw_copy_v101.py` だけ）
A. `parse_v101_response`
- `seen_price_lines: set[int] = set()` を `accepted_by_price_line: dict[int, list[dict]] = {}` に替える（価格の行 → その行を価格の行に持つ受理済みの件の一覧）。
- `if price_line in seen_price_lines:` の所を次の形にする:
  - `price_line in accepted_by_price_line` で、かつ `not _bundle_shime_ok(...)` のときだけ、今までどおり duplicate_price_line で落とす（errors と rejected の書き方は今のまま）。
  - 受理した件は `accepted_by_price_line.setdefault(price_line, []).append(<受理した件>)` で記録する。
- 受理した件のキーは今と同じ（新しいキーを足さない）。
- 説明文（docstring）の「価格の行が重複」の所に、1文足す: 「ただし v102 で、価格 none の件どうしが同じ売り切れの行を持ち、ほかに重なる行が無く、自分の名前の行があるときは受理する（まとめて〆る投稿。design shime-bundle-close §3-1）。」
B. 新しい関数 `_bundle_shime_ok(obj, numbers, price_line, lines, status_entries, keep_rejected, accepted_same_line) -> bool` を `parse_v101_response` のすぐ上に足す。design §3-1 の条件1〜5を、この順にそのまま書く（全部 True のときだけ True）。
- 条件1: `keep_rejected` が True。
- 条件2: 今の件の price と、`accepted_same_line` の全部の件の price が、前後の空白を除いて小文字で `none`（ファイル内の `_NONE` を使う）。
- 条件3: `_is_sold_out(lines[price_line - 1], status_entries)` が True。
- 条件4: `accepted_same_line` のどの件とも、`set(numbers) & set(件["lines"]) == {price_line}`。
- 条件5: 今の件の lines のうち、次の全部に当たる行が1行以上ある: `accepted_same_line` のどの件の lines にも入っていない／`lines[n-1].strip()` が空でない／`_is_sold_out` が False／`re.search(r"\w", 行)` に当たる／`re.fullmatch(r"\s*【[^】]*】\s*", 行)` に当たらない。
C. 同じファイルの4か所の辞書を「先に来た件を残す」にする。今の文字で探して置き換える（行番号は使わない）:
- `by_price_line = {it["price_line"]: i for i, it in enumerate(items)}`（2か所）→
  ```
  by_price_line: dict = {}
  for i, it in enumerate(items):
      by_price_line.setdefault(it["price_line"], i)
  ```
- `owners = {it["price_line"]: it for it in items}` → 同じ形で `owners.setdefault(it["price_line"], it)`。
- `owners = {it["price_line"]: it for it in adjusted}` → 同じ形で `adjusted` を回す。
- 型の注記は周りの書き方に合わせる。インデントはその場所のまま。

## 触らないもの
`_unpriced_line`、`_is_sold_out` の中身、`backend/app/services/line_analysis_v102_svc.py`、`backend/app/services/gemini_raw_copy_v10.py`、`backend/app/tools/prompt_ab.py`、既存の試験ファイル全部、DB、`migrations/`、`.github/`、`scripts/`、指示書の定数、`docs/`（取り込んだ設計書も書き換えない）。

## 試験（新しいファイル `backend/tests/test_v102_shime_bundle.py` を Write で作る）
- 冒頭の説明文に「設計: docs/handoff/shime-bundle-close/design.md §3-2。商品・原文はすべて架空。」と書く。
- 道具（`_it`・`_resp`・`_STATUS`・売り切れの言葉の表）は、`backend/tests/test_gemini_raw_copy_v101.py` の同じ名前の物を読み、必要な分だけこのファイルに写して使う（ほかの試験ファイルを import しない）。
- 試験の名前は `test_t1_...` 〜 `test_t12_...` とし、design §3-2 の T1〜T12 を1つずつ書く。原文は「型番AA-01」「型番BB-02」「型番CC-03」「〆」のような架空の文字だけを使う。
- T2 と T7 は `test_gemini_raw_copy_v101.py` の `_extract_keep` と同じ呼び方（`extract_v101_items(..., v102_fixes=True, review_reasons=True)`）で確かめる。
- T10 は `backend/tests/test_v102_human_decisions.py` の `_fixed_products`（または `_prepare_v102`）の呼び方を読み、同じ形で、T1 の2件が rejected にならず2件とも残ることを確かめる（DB を使わない）。Sold out まで確かめる道が DB なしで無ければ、残ることだけを確かめ、報告に「T10 は残ることだけ」と書く。
- T6・T3 は今までどおり落ちることを確かめる。

## 確かめ（全部流して生出力を残す）
1. `cd backend && python -m pytest tests/test_v102_shime_bundle.py -q --tb=short`
2. `cd backend && python -m pytest tests/test_gemini_raw_copy_v101.py tests/test_v102_gap_lines.py tests/test_v102_human_decisions.py tests/test_gemini_raw_copy_v102_soldout_ref.py tests/test_v102_bundle.py -q --tb=short`
3. `git diff origin/main --stat`
4. `git diff origin/main -- backend/app/services/gemini_raw_copy_v101.py`

## 合格の形
- 確かめ1: 12件以上 passed、failed 0。
- 確かめ2: failed 0（DB が要って skipped になる物は数だけ書く）。
- 確かめ3: 変わったファイルは `backend/app/services/gemini_raw_copy_v101.py`・`backend/tests/test_v102_shime_bundle.py`・設計の枝から取り込んだ `docs/handoff/shime-bundle-close/` の3つ（recon.md・design.md・card-bin1.md）と `.claude-pipeline/active-work.d/` の登録だけ。消した行（deletions）は gemini_raw_copy_v101.py の置き換えた所だけ。
- 合わないときも止まらず、値と名前を報告に書く（判定は Opus が行う）。

## commit と push
- commit 文は Write でファイルに書いて `git commit -F <ファイル>` で流す。良い例: `fix(v102): accept bundle shime items sharing one sold-out line (design shime-bundle-close bin1)`。最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push -u origin release/shime-bundle-close-bin1` を単独で流す。
- PR は作らない。マージしない。

## 止まる条件（止まるのはこれだけ）
- push・commit がフックや見張りに止められた／作業場所が作れない／merge が衝突した／確かめ1で failed が出て、直し方が設計の §3-1 の文の中に無い。
- 止まるときは言い換えて再試行しない。

## 守ること
- Bash に psql の語を書かない。sleep しない。ファイルの作成と編集は Write/Edit で行う（ヒアドキュメント禁止）。git は1命令ずつ流す。
- 本番・DB・外部の道具には触らない。

## 報告（最後の発言。1発言600字以内に分け、番号を付ける）
- 冒頭: 「本報告はカード 便1 shime-bundle-close の実行結果である」。
- 確かめ1〜4の生出力（4 は長ければ要点ではなく前半と後半を分けて全文）。
- push した枝と HEAD。
- 止まったとき: 止まった手順の番号／最後に流した命令／止まった理由の原文。
- 最後の行: `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。

（カードここまで）
