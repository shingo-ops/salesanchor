# 実装カード H: 状態の見出しを下の品目に使う（ADR-1041 便2 の改訂・設定が入るまで働かない）

設計者: Opus（2026-11-07）。PO の実装承認: 2026-11-07 チャット「１」（作り始める。本番に出す前にもう一度報告する）。本番の切り替え（設定の行を入れる）はこのカードの範囲外（PO の「切り替える」の後に Opus が行う）。
設計: `docs/handoff/v102-heading-and-unit/design-heading.md`（第4.7版・審査 APPROVE）の「H1」「H2」「H3」「コードの変え方」「試験」「受入条件」。ADR-1041 What 5。
社外秘: 仕入元名・人名・投稿の原文を、コード・テスト・コミット・報告に書かない。テストの原文は架空の文で作る。
生成器: クラウドの Sonnet（実装役）。応答の形は `.claude/agents/generator.md` に従う。
**本カードの許可・禁止は過去便の禁止条項をすべて上書きする。**

## カード発行前チェック（design-partner.md §5.5。設計担当の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 0 | 照合結果をこの表に出した | ○ |
| 1 | 記号を含む文字列はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が ready で作る（実装役は PR を作らない。`--draft` を付けない） | ○ |
| 3 | 完了報告の本文に生出力を全文含める（宛先は Opus） | ○ |
| 4 | 1 便 1 目的（見出しの直しのコードとテストと台本と data SQL。本番には触らない） | ○ |
| 5 | 既存ブランチ: 起点は `origin/release/v102-heading-condition`。new-worktree.sh は使わない。登録簿 `.claude-pipeline/active-work.d/release-v102-heading-condition.md` は登録済み | ○ |
| 6 | 書式は良い例と禁止形で示した（§6 の報告） | ○ |
| 7 | 合格基準は出力の文言・行数の範囲・削除なしまで書いた（§5） | ○ |
| 8 | 件数の確認には対象の名前を出す手順を対で置いた（§5 の 5-3） | ○ |
| 9 | 出力に上限の無いコマンドを使わない（`git diff --stat`・`grep -c`・`head` で絞る） | ○ |
| 10 | 受領確認・報告冒頭の一文・終端合図・停止時の 3 点を書いた（§6） | ○ |
| 11 | 期待値は実測から。行番号は停止条件にせず、置き換えは前後の文字の一致で指定した | ○ |
| 12 | 停止は 2 段（§7） | ○ |
| 13 | 定型 4 点: sleep しない／作成と編集は Write・Edit（ヒアドキュメント禁止）／PR 本文は Opus が `scripts/dev/validate-pr-body.sh` で確かめる（実装役は PR を作らない）／見張りに止められたら言い換えず止まる | ○ |

受領確認: 着手の前に「カード H を受領しました。起点は origin/release/v102-heading-condition です」と 1 行だけ書く。

## 役割と禁止

- 許可: `git fetch origin`・`git checkout -B release/v102-heading-condition origin/release/v102-heading-condition`（最初の 1 回だけ）・Read・Write・Edit・ruff・pytest・`git add`（下の §3 のファイルだけ）・`git commit`・`git push origin HEAD:release/v102-heading-condition`（fast-forward のみ）。
- 禁止: rebase・`--force`・reset・stash・pull・merge・`git switch -C`・new-worktree.sh・PR の作成・本番や DB への接続・Discord などへの通知・sleep・ヒアドキュメントでのファイル作成・Bash に psql の語を書くこと。§3 の外のファイルを変えること。

## 0. 着手前の確認（読み取り。ずれたら記録して続ける。中身が違えば NEEDS_DECISION）

0-1. `git log --oneline -1 origin/main` と `git log --oneline -3 origin/release/v102-heading-condition` を出す。
0-2. 次の位置の中身が設計の記述と同じことを確かめ、今の行番号を報告に書く（行番号のずれは記録のみ。中身が違えば止まる）:
- `backend/app/services/gemini_raw_copy_v101.py`: `_extract_one` の中の `if product_first is not None:` と、その直後の `unit_canonical, kubun, condition, basis = (` の 3 行。`_is_price_shaped`。`_status_context`（StatusContext を作る所）。
- `backend/app/services/gemini_raw_copy_v102_product_first.py`: `class ProductFirstMasters` の最後の欄 `kubun_allowed_units`、`load_product_first_masters` の `kubun_allowed_units=_load_kubun_allowed_units(session),`、`validate_kubun_allowed_units`、`_load_kubun_allowed_units`、`_resolve_condition`。
- `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`: `condition_decided_by_word`。
- `backend/app/services/v102_status_context.py`: StatusContext の欄 `owned_lines`。
- `backend/app/services/line_analysis_v102_svc.py`: `_call_gemini`・`run_v102_analysis`・`_response_from_rows`・`load_v102_masters`・`masters_with_followup`・`run_v102_pipeline`。

## 1. 変更（`gemini_raw_copy_v102_product_first.py`）

1-1. `ConditionHeadingRule` を足す: `@dataclass(frozen=True)`、欄 `max_lines: int` と `sentence_end_re: re.Pattern[str]`。
1-2. `ProductFirstMasters` の最後（`kubun_allowed_units` の欄の後）に、注釈 1 行と欄 `condition_heading: ConditionHeadingRule | None = None` を足す。注釈の例: `# ADR-1041 What 5：状態の見出しの規則。設定 v102_condition_heading から読む。None なら働かない`
1-3. 定数 `_CONDITION_HEADING_KEY = "v102_condition_heading"`。SQL は既存の `_KUBUN_ALLOWED_UNITS_SQL`（`SELECT value FROM public.tcg_distribution_settings WHERE key = :key`）を使い回す（新しい SQL を作らない）。
1-4. 純粋な関数 `validate_condition_heading(raw: str | None) -> ConditionHeadingRule | None`。設計 H3 の検査の表のとおり:
- `raw is None` → `logger.debug(...)` だけで None（info・warning にしない）。
- JSON として読めない → warning・None。
- 値が `{}` → ログなし・None。
- dict でない／key の組が `{"max_lines", "sentence_end", "trailing_chars"}` と違う（知らない key・欠け）→ warning・None。
- `max_lines` が bool、または int でない、または 1〜5 の外 → warning・None。
- `sentence_end` が list でない、空、または要素に「str でない」か「空の文字列」がある → warning・None。
- `trailing_chars` が str でない → warning・None（空の文字列は可）。
- 通れば式 `re.compile("(" + "|".join(re.escape(w) for w in sentence_end) + ")[" + re.escape(trailing_chars) + r"\s]*$")` を作り `ConditionHeadingRule(max_lines, 式)` を返す。
- warning の文は `[condition_heading]` で始め、値そのものは出さない（既存の `[kubun_unit_fix]` の文と同じ書き方）。
1-5. `_load_condition_heading(session) -> ConditionHeadingRule | None`: `_KUBUN_ALLOWED_UNITS_SQL` を `{"key": _CONDITION_HEADING_KEY}` で流し、値（行が無ければ None）を `validate_condition_heading` に渡す。
1-6. `load_product_first_masters` の `kubun_allowed_units=_load_kubun_allowed_units(session),` の次の行に `condition_heading=_load_condition_heading(session),` を足す。docstring に 1 行足してよい。
- 語・記号（`。`・`ます` など）をこのファイルにもどのファイルにも書かない（テストの中だけ可）。

## 2. 変更（`gemini_raw_copy_v101.py`）

2-1. `_heading_block(lines: list[str], first_line: int, owned: frozenset[int] | set[int], rule: ConditionHeadingRule) -> tuple[str, int] | None` を足す。中身は設計 H1 の正本のコードと同じ動き（`_is_price_shaped` を使う）。
2-2. `_heading_condition(item, lines, product_first, ctx, status_context) -> tuple[str, str] | None` を足す。順に:
- `ctx.product_first` が None・`ctx.product_first.condition_heading` が None・`status_context` が None・`product_first` が None なら None。
- `basis = product_first["condition_basis"]`。`condition_decided_by_word(basis)` が真、または `basis` が `"R4:単位既定"` でも `"R5:パック既定"` でも終わらないなら None（末尾一致。`str.endswith` に 2 つの組を渡す）。
- `_heading_block(lines, min(item["lines"]), status_context.owned_lines, rule)` が None なら None。
- 見出しの文字を `_resolve_condition(heading_text, product_first["product_category"], product_first["unit_kubun"], ctx.cond_entries, ctx.cond_canonical_to_uuid, ctx.product_first.scoped_cond_entries)` に通す（引数の並びは既存の呼び出しと同じに合わせる。0-2 で確かめた並びが違えば止まる）。返り値の 1 つ目を新しい状態、2 つ目を `hb`、3 つ目は捨てる。
- `hb` が `単品語あり・要確認(` で始まれば None。`hb` から先頭の `R4c:商品分類既定>` を除いた残りが `re.match(r"^R[23]:", ...)` に当たらなければ None。
- 群: `groups(c) = {e.get("value_group") for e in ctx.cond_entries if e.get("canonical") == c}`。新しい状態と今の状態（`product_first["condition"]`）の両方で要素がちょうど 1 つ・None でない・等しいときだけ続ける。それ以外は None。
- 返り値 `(新しい状態, f"{hb}@見出し:L{見出しの最小行番号}")`。
- `product_first` の中の鍵の名前（`condition_basis`・`product_category`・`unit_kubun`・`condition`）は 0-2 で実物を確かめる。名前が違えば止まる（NEEDS_DECISION）。
2-3. `_extract_one` の差し込み: 前後の文字の一致で次を置き換える。

変更前:
```python
        unit_canonical, kubun, condition, basis = (
            product_first["unit"], product_first["unit_kubun"], product_first["condition"], product_first["condition_basis"]
        )
```
変更後:
```python
        unit_canonical, kubun, condition, basis = (
            product_first["unit"], product_first["unit_kubun"], product_first["condition"], product_first["condition_basis"]
        )
        heading = _heading_condition(item, lines, product_first, ctx, status_context)
        if heading is not None:
            condition, basis = heading
```
- `status_context` が `_extract_one` の引数名と違えば、実物の名前に合わせる（記録のみ）。`product_first` の辞書そのものは書き換えない。
- import: `condition_decided_by_word` を `gemini_raw_copy_v102_soldout_ref` から、`ConditionHeadingRule` と `_resolve_condition` を `gemini_raw_copy_v102_product_first` から。循環 import になったら関数の中で import する（記録のみ）。

## 3. 新設するファイル（これ以外は変えない）

3-1. `backend/app/tools/v102_replay_diff.py`: 設計「試験」の 1〜7 のとおり。引数 `--posts <投稿 id のファイル>`・`--out <JSONL>`・`--heading-setting <JSON ファイル>`（任意）と、差の道具の小さな入口 `diff <前の JSONL> <後の JSONL> --out-dir <ディレクトリ>`（列ごとの差の件数を `summary.tsv`、状態が変わった件を `changed.tsv` に書く）。最初に `line_analysis_v102_svc._call_gemini` を「呼ばれたら RuntimeError」に差し替える。書き込み・`commit`・`pg_advisory_xact_lock` を呼ばない。DB は環境変数の接続先を読むだけ（既存の `backend/app/tools/prompt_ab_recompute.py` の接続の仕方に合わせる）。
3-2. `backend/tests/test_v102_condition_heading.py`（DB を使わない）:
- 設定の検査: 設計 H3 の表の全行（key 無し → None で warning も info も出ない（caplog）／`{}`／JSON 不正／`max_lines` が `True`・`0`・`6`・`"3"`／`sentence_end` が `[]`・`[""]`・`"。"`／`trailing_chars` が `1`／知らない key／key の欠け／正しい値）。
- 設定の式: 入れる値（設計 H3 の JSON）から作った式と、式 `(。|ます|ません|ございます|おります|です|下さい|ください)[!！。\s]*$` が、次の行で同じ真偽になる: `在庫ございます！`・`よろしくお願い致します。`・`未開封です!`・`。`・`未サーチ品`・`傷あり`・`各10パック単位`・`ご確認下さい 　`。
- `_heading_block` の境目（架空の文。行のリストと owned を手で作る）: 設計の受入条件「単体」の全項目と、止まり方の表の 5 行。
- `_heading_condition`: rule が None → None／件に語がある印（例 `R3:未サーチ`）→ None／`R4:単位既定:単位不明` → None／見出しが R2・R3 で群が同じ → 置き換わり印が `R3:<語>@見出し:L<n>`／群が違う（パックの語が箱の件）→ None／`単品語あり・要確認(` で始まる → None／群の列が None → None。cond_entries は架空の最小の行で作る。
- 100 字: `"R3:未サーチ@見出し:L12" + "x" * 100` を 100 字で切っても `condition_decided_by_word` が真。
- K5: 設計の受入条件 K5 のとおり。印 `R3:未サーチ@見出し:L12` の件と `R3:未サーチ` の件の組を、札 7・3・4 × 値段の帯（パック／箱／ケース／どれでもない）で `v102_buyback_unit_svc.is_candidate`・`decide_kind`・`with_decision` と `gemini_raw_copy_v102_soldout_ref._narrow_by_condition`・`_is_inherit_candidate` に通し、状態・単位・`_is_inherit_candidate` の真偽が同じ、印は `@見出し:L` から後を除いた先頭が同じ。物差し（ConditionMap・BuybackSettings）は既存のテストの作り方を `git grep -l "decide_kind" backend/tests | head -5` で探して合わせる。
- K0: `ProductFirstMasters` を `condition_heading=None` で作ったとき、`_heading_condition` が全部の形で None を返す。既存の `backend/tests/test_gemini_raw_copy_v102_product_first.py` と `backend/tests/test_v102_status_context.py`・`backend/tests/test_v102_heading_ship_review.py` が変更なしで通る。
- 台本: `v102_replay_diff` を import し、差し替えの関数を呼んだ後に `line_analysis_v102_svc._call_gemini(...)` が RuntimeError を出す。差の道具に小さな JSONL 2 つ（架空）を渡し、`summary.tsv` の数と `changed.tsv` の行が期待どおり。
3-3. `docs/handoff/v102-heading-and-unit/data/heading-precheck.sql`・`heading-dryrun.sql`・`heading-commit.sql`・`heading-rollback.sql`・`heading-verify.sql`: 同じフォルダの `precheck.sql`・`dryrun.sql`・`commit.sql`・`rollback.sql`・`verify.sql` と同じ形で、key を `v102_condition_heading`、値を設計 H3 の JSON と一字一句同じ文字列（`{"max_lines": 3, "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"], "trailing_chars": "!！。"}`）、note を `状態の見出しの規則（ADR-1041 What 5）: 文の終わりの語・記号と塊の最大行数。{} は取り消し（働かない）。コードの検査に通らない値は使われない` にする。先頭の注釈の「便1」「v102_kubun_allowed_units」を「見出し」「v102_condition_heading」に変える。本番には流さない。

## 4. 手順

1. 受領確認の 1 行。
2. `git fetch origin` → `git checkout -B release/v102-heading-condition origin/release/v102-heading-condition` → `git log --oneline -1` を出す。
3. §0 → §1 → §2 → §3。
4. `cd backend && ruff check app/services/gemini_raw_copy_v101.py app/services/gemini_raw_copy_v102_product_first.py app/tools/v102_replay_diff.py tests/test_v102_condition_heading.py`（ruff の場所が違えばリポジトリの設定に合わせる。記録のみ）。
5. `cd backend && python -m pytest -q tests/test_v102_condition_heading.py tests/test_gemini_raw_copy_v102_product_first.py tests/test_v102_status_context.py tests/test_v102_heading_ship_review.py 2>&1 | tail -30`。DB が要るテストが手元で動かないときは、そのテストの名前と出力の末尾を報告に書く（記録のみ）。
6. `git add` は §1・§2・§3 のファイルだけ（ファイル名を並べて書く。`git add -A`・`git add .` は禁止）。
7. `git commit`。文は `feat(v102): 状態の見出しを下の品目に使う（設定 v102_condition_heading が入るまで働かない・ADR-1041 What 5）`、末尾に空行と `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。→ `git log -1 --stat | head -20`。
8. `git push origin HEAD:release/v102-heading-condition` → `git status -sb | head -1`。

## 5. 合格基準（実装役が出力を貼り、判定は Opus）

5-1. ruff: 出力が `All checks passed!`。
5-2. pytest: 最後の行が `N passed`（failed・error が 0）。
5-3. 変更の範囲: `git diff --stat origin/release/v102-heading-condition..HEAD | tail -15` を貼る。出てよいのは §1・§2・§3 のファイルだけ（8〜10 ファイル）。`git diff origin/release/v102-heading-condition..HEAD --numstat | head -20` も貼り、既存の 2 ファイル（`gemini_raw_copy_v101.py`・`gemini_raw_copy_v102_product_first.py`）の削除の数を書く。削除が 0 でなければ、削除した行の中身を `git diff origin/release/v102-heading-condition..HEAD -- <ファイル> | grep '^-' | grep -v '^---' | head -20` で貼る。
5-4. 語を書いていない: `git diff origin/release/v102-heading-condition..HEAD -- backend/app | grep -c 'ございます'` が `0`。0 でなければ、当たった行を `| head -10` で貼る。
5-5. 設定が無いときに働かない: 3-2 の K0 のテストが通っている（5-2 の出力にテスト名が出るよう `-q` の代わりに `-v` で `tests/test_v102_condition_heading.py` だけもう一度流し、`| grep -c PASSED` の数と `| grep -E 'FAILED|ERROR' | head -10` を貼る）。

## 6. 報告（宛先は Opus。完了報告の本文に生出力を全文含める）

- 冒頭の 1 行: `本報告はカード H の実行結果である`。
- 0-1・0-2 の結果（行番号の表）、§4 の 2・4・5・7・8 と §5 の各コマンドの生出力を、要約せずにそのまま貼る。
- 良い例: 「5-1 の出力: `All checks passed!`」。禁止形: 「ruff OK」「テストは通りました」だけの要約、表やチェックマークだけの報告。
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文、の 3 点。
- 最後の行: `DONE`、または `BLOCKED: <理由>`、`NEEDS_DECISION: <理由>` のどれか 1 行。その直前の行に `END OF REPORT H`。

## 7. 停止条件（2 段）

- 止まる（NEEDS_DECISION / BLOCKED）: §0 で中身が違う／`product_first` の鍵の名前・`_resolve_condition` の引数が設計と違う／§3 の外のファイルを変えないとできない／push が fast-forward にならない／見張りやフックに止められた（言い換えて再試行しない）／本番や DB に触る必要が出た。
- 記録して続ける: 行番号のずれ・テストの件数・ファイル数・ruff の場所・DB が要るテストが手元で動かない・循環 import の回避。

END OF CARD
