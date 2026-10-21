# 実装カード（発行済み 2026-10-18 Opus）— 型番の後ろの「-数字」には当てない

> この文書は何か：型番の厳格な照合 `_strict_code_pattern` の正規表現の右端に「直後がハイフン類＋数字なら当たらない」条件を足す作業指示書です。直すのは `backend/app/services/extraction_judgement_svc.py` の4か所（定数2行・組み立て1行・説明文1行）と、試験の追加だけです。
> **状態：発行済み。設計審査は APPROVE（design.md §12）、U1〜U4 は design.md §11-1 で決めた。PO の実装承認は取得済み（2026-10-18、PO 原文「y」）。PR 本文には「followup・soldout_ref 経路は試算していない（U2）」と書く。**

読んだ節（引いた guards）: docs/handoff/design-partner-card-ops/guards/00-common.md, guards/04-worktree.md, guards/05-pr.md, guards/10-executor.md, guards/11-lint.md

本カードの許可・禁止は過去便の禁止条項をすべて上書きする。

- 設計: docs/handoff/mark-exact-match/design.md（§2-1 が変更の正本。変えてはいけない）
- 事実確認: docs/handoff/mark-exact-match/recon.md（origin/main 035b0145e で確認済み）
- 対象ADR: ADR-1006（方針は変えない）・ADR-135・ADR-136
- 危険便: いいえ（`migrations/`・`deploy.yml`・`scripts/` を触らない）。ただし `backend/app/services/` はユーザーに影響する変更なので、本番反映前に GO 記録が要る（Opus が記入）
- 担当: 実装 Sonnet／コード審査・GO 記録・マージ・反映確認・K3〜K5 の実測 Opus

## 0. カード発行前チェック（design-partner.md §5.5。発行者が○×を確定する）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ（`(?![…])` など） | ○ |
| 2 | 下書き禁止：PR は ready で作る（`--draft` を付けない） | ○（§10） |
| 3 | 報告の宛先：完了報告の本文に生出力を全文含める | ○（§10） |
| 4 | 1便1目的 | ○（型番に「-数字」を当てないことだけ） |
| 5 | 既存ブランチ：`release/mark-exact-match` は本件専用で作成済み。`new-worktree.sh` を再実行しない。起点は `origin/release/mark-exact-match`（設計文書の push 後）または既存 worktree | ○（§3） |
| 6 | 書式は実例で示す（PR 欄「触るファイル:」は同一行・カンマ区切り） | ○（§10） |
| 7 | 合格基準を出力まで縛る（行数レンジ・正常時の出力文言・main との差分に削除なし） | ○（§5-3・§5-4） |
| 8 | 件数だけで停止条件を作らない（名前を出す手順を対で置く） | ○（§5-1 は落ちた試験名を出す） |
| 9 | 出力量に上限のない一覧を使わない | ○（`| tail -n`・`-q` を指定） |
| 10 | 報告様式3点：停止時の3項目／終端合図と受領確認／報告冒頭の宛先 | ○（§7・§10） |
| 11 | 期待値は実測から引く（行番号は目安、置換は前後の一致で指定） | ○（§4。行番号は 035b0145e 時点の参考） |
| 12 | 停止は不可逆・本番影響に限り、数値の食い違いは記録のみで続行 | ○（§7） |
| 13 | 委任文の定型4点：sleep しない／ファイルは Write/Edit で書く／`validate-pr-body.sh` で exit 0／フックに止められたら言い換えず原文を報告 | ○ |
| 14 | 社外秘（仕入元の ID・名前・投稿原文）を試験にも本文にも入れない | ○（§8） |

GO の記録（Opus が記入）: （未記入。実装 PR の `### GO記録` に転記する）

## 0-2. 常設ルール定型文
docs/ai-agents/executor-preamble.md の逐語原本を、カードの前に投入する（コピペ元はこのファイルに限る）。

## 受領確認
作業を始める前に、報告の冒頭へ「本報告はカード 型番の後ろの -数字 に当てない（mark-exact-match）の実行結果である」と書くこと。

## 1. 範囲
入れる:
1. `backend/app/services/extraction_judgement_svc.py` に定数2行を足し、`_strict_code_pattern` の組み立て行1行を変え、docstring に1行足す（§4-1〜§4-3）
2. `backend/tests/test_extraction_judgement_svc.py` の `TestMatchProductStrictCodes` に試験を足す（§4-4）

入れない（触らない）:
- `_strict_code_hits`・`_value_hits`・`_code_candidate_basis`・`_keyword_matches`・`_exclude_hit`・`match_product`・`has_word_boundary`
- `gemini_raw_copy_v102_followup.py`・`gemini_raw_copy_v102_soldout_ref.py`・`gemini_raw_copy_v102_product_first.py`・`v102_gap_lines.py`
- v6（`tcg_analyzer_svc.py`）・`tcg_product_code_collision_svc.py`・frontend・マスタ・`migrations/`・`.github/workflows/`・`scripts/`
- 既存の試験（変更も削除もしない）
- 再解析（Opus が別に行う）

## 2. 前提の事実（recon.md の引用）
| # | 事実 | 根拠 |
|---|---|---|
| 1 | 変更する関数と組み立て行 | `backend/app/services/extraction_judgement_svc.py:173-198`（組み立て行 `:197`） |
| 2 | 区切り文字の定数の末尾 | `backend/app/services/extraction_judgement_svc.py:158`（`_CODE_SEPARATOR_RE = …`） |
| 3 | 試験クラスと追加位置 | `backend/tests/test_extraction_judgement_svc.py:662`（クラス）・`:700-704`（直前の試験）・`:706`（直後の試験） |
| 4 | `_product` ヘルパーと `_hits` | `backend/tests/test_extraction_judgement_svc.py:109-124`・`:665-667` |

## 3. 作業場所
- 既存の worktree: `/Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match`（ブランチ `release/mark-exact-match`）。`new-worktree.sh` は再実行しない
- 最初に `./scripts/dev/executor-preflight.sh || exit 1` を実行し、出力を `/tmp/CC報告ファイル/mark_exact_match_impl/preflight.txt` に保存
- 設計文書が未 push なら、実装前に `git fetch` と `git status` を保存して報告（push は Opus の指示後）

## 4. 作り方
各置換は「前後の一致」で場所を決める（行番号は目安。ずれていたら記録して続行）。編集は Edit ツールで行う。

### 4-1. 定数2行を足す（`_CODE_SEPARATOR_RE = …` の行の直後）
前（実物）:
```python
_CODE_SEPARATOR_RE = "[" + "".join(re.escape(ch) for ch in _CODE_SEPARATOR_CHARS) + "]*"
```
後（上の1行はそのまま。続けて次の3行を足す。コメント1行＋定数2行）:
```python
# 型番の直後が「ハイフン類＋数字」（例 EB02-003 の -003＝カード番号）のときは、その型番には当てない。
_CODE_HYPHEN_CHARS = "-‐‑–—―−ー"
_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE = "(?![" + "".join(re.escape(ch) for ch in _CODE_HYPHEN_CHARS) + "][0-9])"
```

### 4-2. 組み立て行を変える（`_strict_code_pattern` の最後の `pattern = …`）
前（実物）:
```python
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])")
```
後:
```python
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])" + _CODE_NOT_BEFORE_HYPHEN_DIGIT_RE)
```

### 4-3. docstring に1行足す
`_strict_code_pattern` の docstring の最後の段落（`値の中で記号があった隙間だけ、…` で始まる文）の直後、閉じの `"""` の前に、次の1行を足す（行頭の空白は4つ）:
```
    値の直後が「ハイフン類＋数字」（カード番号の形。例 EB02-003）のときは当たらない（_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE）。
```

### 4-4. 試験を足す（`TestMatchProductStrictCodes` の中、`test_hyphen_and_no_hyphen_both_hit_either_form` の最後の行の直後・`test_apostrophe_variants_hit` の前）
ファイルの先頭で `pytest` が import 済みか確認する。**import 済みでなければ**、ファイル先頭の import 群に `import pytest` を足す（`from app.services.extraction_judgement_svc import (` の前の行。標準ライブラリ・サードパーティの順に合わせる）。`TestMatchProductStrictCodes` の中では既存の `self._hits(text, products, **kwargs)` を使う。クラス内メソッドとして次の6本を足す（インデントは既存の試験と同じ4つ）:

| # | 試験名 | 入力 | 期待 |
|---|---|---|---|
| 1 | `test_code_does_not_hit_card_number_with_hyphen_digits` | 商品 `eb02=_product(id_=1, mark="EB-02")`・`card=_product(id_=2, mark="EB02-003")`。本文 `"EB02-003 チョッパーズ 50@1700"` と `"EB02-003 / 20個@1000"` の各々 | `strict_codes=True` で `[eb02]` のみ → `()`、`[eb02, card]` → `(2,)`。さらに `"EB02-003 / 20個@1000"` を `strict_codes` なし・`[eb02]` のみ → `(1,)`（既定の動作は変わらない） |
| 2 | `test_code_still_hits_other_writings`（`pytest.mark.parametrize`） | 商品 `_product(id_=1, mark="OP-01")`。本文: `"OP01"`・`"OP-01"`・`"【OP-01】"`・`"OP01×2"`・`"ＯＰ－０１"`・`"OP-01 BOX"`・`"OP01-BOX"`・`"OP-01-BOX"` | 各々 `strict_codes=True` で `(1,)` |
| 3 | `test_code_does_not_hit_card_number_any_hyphen`（`pytest.mark.parametrize`） | 商品 `_product(id_=1, mark="OP-01")`。本文: `"OP01-001"`・`"OP01-001 リーダー"`・`"OP01−001"`・`"OP01‐001"`・`"OP01ー001"` | 各々 `strict_codes=True` で `()` |
| 4 | `test_code_hits_when_both_card_number_and_plain_code_in_text` | 商品 `_product(id_=1, mark="OP-01")`。本文 `"OP01-001 と OP-01 BOX"` | `strict_codes=True` で `(1,)` |
| 5 | `test_code_like_search_keyword_does_not_hit_card_number` | 商品 `_product(id_=1, search_keywords=("EB02",))` | 本文 `"EB02-003"` → `()`、本文 `"EB02 BOX"` → `(1,)`（`strict_codes=True`） |
| 6 | `test_code_like_exclude_keyword_does_not_exclude_on_card_number` | 商品 `_product(id_=1, mark="ABC12", exclude_keywords=("EB02",))`。`match_product(本文, [商品], strict_codes=True).status` | 本文 `"ABC12 EB02-003"` → `"matched"`、本文 `"ABC12 EB02"` → `"unmatched"` |

- 手元で検証済みの試験本体（このカードの§4-4 と同じ内容。**コピーして使ってよい参考実装**）: `/tmp/CC報告ファイル/mark_exact_match_design/test_draft_for_card.py`。クラス外の関数として書いてあるので、クラス内メソッドにする場合は `self` を足し、`_hits(...)` を `self._hits(...)`、`_product` は既に同ファイルにあるので `from tests…` の import 行は不要。
- 設計時の手元実測: 現行コードで落ちる試験 = 1・3・5・6、案R1 で全 17 ケース緑（`draft_tests_result.txt`・`draft_tests_exact_result.txt`）。

## 5. 確かめ方（担当が実行し、出力を `/tmp/CC報告ファイル/mark_exact_match_impl/` に保存して、完了報告の本文に全文を含める）
手順1: 追加試験の確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match/backend && python3 -m pytest tests/test_extraction_judgement_svc.py -q -n0 --no-cov -p no:cacheprovider > /tmp/CC報告ファイル/mark_exact_match_impl/pytest_judgement.txt 2>&1; tail -n 5 /tmp/CC報告ファイル/mark_exact_match_impl/pytest_judgement.txt
期待する出力: 末尾に `passed` を含み、`failed` を含まない。落ちた試験があれば、その試験名を全て報告に書く（件数だけにしない）。

手順2: v102 系ほかの関連試験
    cd /Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match/backend && python3 -m pytest tests/test_extraction_judgement_svc.py tests/test_extraction_judgement_cond_terms.py tests/test_gemini_raw_copy_v102_followup.py tests/test_gemini_raw_copy_v102_score_select.py tests/test_gemini_raw_copy_v102_match_g2.py tests/test_gemini_raw_copy_v102_soldout_ref.py tests/test_gemini_raw_copy_v102_name_only.py tests/test_line_analysis_v102_svc.py tests/test_v102_buyback_unit.py tests/test_tcg_keyword_matching.py -q -n0 --no-cov -p no:cacheprovider > /tmp/CC報告ファイル/mark_exact_match_impl/pytest_related.txt 2>&1; tail -n 3 /tmp/CC報告ファイル/mark_exact_match_impl/pytest_related.txt
期待する出力: 設計時の実測は `1154 passed, 1 warning, 12 errors`（追加試験を足す前）。追加後は passed が 1154 より多く（追加ケース数ぶん）、failed が 0。12 errors は `soldout_ref` の DB 付き試験で `GITHUB_ACTIONS` 未設定のため手元では走らない（CI では走る）。errors の件数が 12 以外でも記録のみで続行し、エラー名を報告に書く。

手順3: 変更ファイルの確認（mainとの差分）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match && git diff --stat origin/main -- backend > /tmp/CC報告ファイル/mark_exact_match_impl/diff_stat.txt; cat /tmp/CC報告ファイル/mark_exact_match_impl/diff_stat.txt; git diff origin/main -- backend/app/services/extraction_judgement_svc.py | grep -c '^-[^-]'
期待する出力: `backend/app/services/extraction_judgement_svc.py` が 1 ファイルで追加 5 行・削除 1 行前後（組み立て行の置換による 1 行削除のみ）、`backend/tests/test_extraction_judgement_svc.py` は追加のみ（削除 0 行）。最後の `grep -c` は 1（削除は組み立て行のみ）。1 でなければ停止せず記録して Opus に判定を委ねる。

手順4: 触っていないファイルの確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match && git diff --name-only origin/main > /tmp/CC報告ファイル/mark_exact_match_impl/changed_files.txt; cat /tmp/CC報告ファイル/mark_exact_match_impl/changed_files.txt
期待する出力: `backend/app/services/extraction_judgement_svc.py`・`backend/tests/test_extraction_judgement_svc.py` と `docs/handoff/mark-exact-match/` 配下・`.claude-pipeline/active-work.d/` 配下の登録ファイルだけ。これ以外のパスが出たら、そのパスを報告に書く（記録のみで続行）。

手順5: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match/backend && python3 -m ruff check app/services/extraction_judgement_svc.py tests/test_extraction_judgement_svc.py > /tmp/CC報告ファイル/mark_exact_match_impl/ruff.txt 2>&1; tail -n 5 /tmp/CC報告ファイル/mark_exact_match_impl/ruff.txt
期待する出力: `All checks passed!`。触っていない行の既存の指摘は直さず、報告に書く。

## 6. 分岐ごとの対処
| 分岐 | 対処 |
|---|---|
| 追加試験 1・3・5・6 のどれかが落ちる | 実装（§4-1〜4-3）を前後の一致で見直す。直せなければ、落ちた試験名と出力を報告して終える |
| 既存の試験が落ちた | 直さずに、落ちた試験名と出力を全て報告して終える |
| `pytest` が import されていない | §4-4 のとおり `import pytest` を足す |
| ruff が既存の違反を出す | 触った行以外は直さない。報告に書く |

## 7. 停止条件（肯定形・不可逆か本番影響があるものに限る）
次のいずれかに当たる場合のみ作業を止めて、「停止した手順番号／最後に実行したコマンド／停止した理由」を報告する（言い換えて再試行しない）:
- 設計 §2-1 と食い違う実装が必要になった
- §1 の「入れない」に挙げたファイルを変える必要が出た
- フック・分類器・CI に止められた
- `git push`・マージ・DB 書き込み・本番設定の変更が必要になった（このカードでは行わない）
行数・件数・文字列一致の食い違いは停止せず、値を報告に書いて続行する。

## 8. 社外秘
試験データ・PR 本文・コミットメッセージに、実在の仕入元の ID・名前・投稿原文を入れない。試験の文は上の架空・型番だけの短い文のみ。

## 9. 戻し方
本 PR を revert する。DB の変更はない。

## 10. PR と報告
- 作成前に `gh auth status` で `shingo-cc` 名義を確かめる
- commit の末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- commit メッセージの例: `fix: 型番の照合で「型番-数字」(カード番号)には当てない`
- PR は `scripts/gh-pr-create-safe.sh` で `--base main` に **ready（`--draft` を付けない）** で作る。本文は `.github/pull_request_template.md` 起点。`### 標準ワークフロー確認` に recon・design・このカード・ADR-1006 を書き、「触るファイル:」を同一行・カンマ区切りで全列挙する。
  - 良い例: `触るファイル: backend/app/services/extraction_judgement_svc.py, backend/tests/test_extraction_judgement_svc.py, docs/handoff/mark-exact-match/recon.md, docs/handoff/mark-exact-match/design.md, docs/handoff/mark-exact-match/card-implement.md`
  - 禁止形: 箇条書きで1行ずつ書く／行をまたいで書く
- 本文の末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる
- マージは Opus が行う。担当はマージしない。sleep しない。CI の完了を待たず PR の URL を報告する
- 完了報告の本文に、§5 の各出力（ファイルに保存したものの全文）を含める
- 報告の冒頭に「本報告はカード 型番の後ろの -数字 に当てない（mark-exact-match）の実行結果である」と書く。1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。事実だけを書く

## 11. 反映後の確認（Opus が行う。担当は行わない）
K3（v102 現行行の再計算・変化行の全件列挙）・K4（想定文が 424591 単独）・K5（デプロイの4観測）は design.md §5。台本は Opus が書き、PO が `!` で実行する。

## 12. 報告欄（担当が追記）

（未記入）

END OF CARD
