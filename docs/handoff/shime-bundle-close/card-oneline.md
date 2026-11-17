# 実装カード: 1行の並び〆（規則14）の受け取り側（コードと試験だけ）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

- 設計: `docs/handoff/shime-bundle-close/design-oneline.md` §3-1・§3-2（設計審査5回目 APPROVE、28b9fae6f。小さい指摘は 7cb25f9dc で直した）
- recon: `docs/handoff/shime-bundle-close/recon-oneline.md`
- 審査の記録: `docs/handoff/shime-bundle-close/review-oneline.md`
- 実装承認: PO 2026-11-17「1」（この設計どおりに作り始める）。
- 発行: Opus（設計担当）2026-11-17。照合した版: origin/main 337ebbd1b

## カード発行前の照合（design-partner.md §5.5）
| 項目 | 結果 |
|---|---|
| 1 記号を壊さない（パス・名前はバッククォート） | ○ |
| 2 下書き禁止 | ○ PR は作らない（push まで。PR は Opus が作る） |
| 3 報告の宛先 | ○ 最後の発言に生出力を全文 |
| 4 1便1目的 | ○ 規則14のコードと試験だけ（指示書・DB・便3の試験は触らない） |
| 5 既存ブランチは起点明示 | ○ 新しい枝を new-worktree.sh で作り、設計の枝を merge で取り込む |
| 6 書式は実例で | ○ commit 文の例を下に書いた |
| 7 合格基準を出力まで縛る | ○ 下の「合格の形」 |
| 8 件数と名前を対で | ○ 落ちた試験は名前を出す |
| 9 出力に上限 | ○ pytest は `-q` と `--tb=short`、diff は `--stat` |
| 10 報告の3点 | ○ 下の「報告」 |
| 11 行番号を停止条件にしない | ○ 置き換えは前後の文字で指定 |
| 12 停止は2段 | ○ 下の「止まる条件」 |
| 13 委任文の4点 | ○ sleep 禁止・Write/Edit で書く・PR は作らない・止められたら言い換えない |

## 作業場所（この順で。git は1命令ずつ流す）
1. `bash scripts/new-worktree.sh release/shime-oneline-bundle-impl --claude` を流し、出てきた作業場所に入る。以後の作業はその中だけで行う。
   - 最後に出る Claude Code 起動の失敗（`Input must be provided ...`）は、作業場所の作成とは関係ないので続ける。
2. `git fetch origin` → `git merge --no-ff origin/release/shime-oneline-bundle-design -m "merge design docs"`（rebase はしない）。
3. `./scripts/dev/executor-preflight.sh` は流さない（クラウドには gh の認証が無く必ず落ちる）。代わりに `git log -1 --oneline` と `git rev-parse --short origin/main` を流して報告に書く。
   - 未追跡の `.claude-pipeline/active-work.d/` の登録ファイルは commit しない。

## 最初の grep（設計 §3-1 の3。結果を報告に書く）
- `git grep -n "matched_followup\|matched_soldout_ref" -- backend/app frontend/src scripts`
- `git grep -n "SOLDOUT_INHERIT\|SOLDOUT_REF" -- backend/app frontend/src scripts`
- 出た所が `backend/app/services/gemini_raw_copy_v101.py`・`backend/app/services/gemini_raw_copy_v102_followup.py`・`backend/app/services/gemini_raw_copy_v102_soldout_ref.py`・`backend/app/services/gemini_raw_copy_v102_product_first.py`・`backend/app/services/line_analysis_v102_svc.py` の外にあれば、止まって `NEEDS_DECISION:` で返す。

## 直すもの
### A. `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`（純粋な関数と定数を足す。今の関数は変えない）
1. 定数（`MATCH_STATUS_MATCHED_SOLDOUT_REF = ...` の行のすぐ下）:
   - `MATCH_STATUS_MATCHED_LIST_SHIME = "matched_list_shime"`
   - `CONDITION_BASIS_SOLDOUT_LIST_SHIME = "SOLDOUT_LIST_SHIME"`  # 規則14：1行の並び〆
   - `_LIST_SHIME_SEPARATORS = re.compile(r"[、,，/／]")`（「・」「&」「＆」は入れない）
   - `_KIND_DEFAULT_BASES`: `gemini_raw_copy_v102_product_first` の `BASIS_SINGLE_DEFAULT`・`BASIS_BULK_DEFAULT`・`BASIS_PROMO_PACK_DEFAULT`・`BASIS_BOOKLET_DEFAULT`・`BASIS_SUPPLY_DEFAULT` を import して frozenset にする（値を書き写さない）。
2. `def is_kind_default_basis(basis: str | None) -> bool`: `_FLAG_NOTE_RE.sub("", basis or "")` が `_KIND_DEFAULT_BASES` のどれかと等しいとき True。
3. `def split_list_shime(text: str, sold_out_words: Sequence[str], match: Callable[[str], int | None]) -> tuple[int, ...] | None`（設計 §3-1 の1）:
   - `text` から `_strip_words(text, sold_out_words)` で〆の言葉を除き、`_LIST_SHIME_SEPARATORS` で分け、前後の空白を除いて空でない区切りだけ残す。
   - 区切りが2つ未満か6つ以上 → None。
   - どれかの区切りを NFKC にして空白で分けた語に `re.fullmatch(r"\d+", 語)` が1つでもある → None。
   - 区切りごとに `match(区切り)`。1つでも None、または同じ商品 ID が2回出る → None。
   - 全部当たれば区切りの順の商品 ID の tuple を返す。
4. `def list_shime_targets(product_id: int, extracted_with_i: Sequence[Mapping[str, Any]], i: int, posts: Sequence[SoldoutRefPost], fixed_products, *, box_rule, post_text: str) -> tuple[SoldoutTarget, ...]`（設計 §3-1 の2の相手の求め方）:
   - 1: `decide_soldout_inherit(extracted_with_i, posts, fixed_products, box_rule=box_rule, post_text=post_text).get(i)` があればそれを返す。
   - 2: 無ければ、`shime = _shime_condition(extracted_with_i[i])`、`same_post` を `decide_soldout_inherit` の中と同じ式で作り、`_stranded_stock(product_id, posts, same_post).get(shime)` があれば `(_soldout_target(product_id, shime, post, stock),)` を返す。
   - 3: どちらも無ければ `()`。
   - 型の注記は周りに合わせる（`Callable` が無ければ `collections.abc` から import）。

### B. `backend/app/services/gemini_raw_copy_v101.py`
1. import: `gemini_raw_copy_v102_soldout_ref` の import の並びに `CONDITION_BASIS_SOLDOUT_LIST_SHIME`・`MATCH_STATUS_MATCHED_LIST_SHIME`・`is_kind_default_basis`・`list_shime_targets`・`split_list_shime` を足す（名前の順は今の並びに合わせる）。`match_text_g2` が無ければ `gemini_raw_copy_v102_product_first` から足す。
2. 新しい関数 `_apply_list_shime(extracted, build, lines, masters, soldout_posts, sold_out_words, fixed_products, box_rule, post_text, followup_ref, unit_alias_to_info) -> list[dict]` を `_apply_soldout_ref` のすぐ上に足す。件 i ごとに、設計 §3-1 の2の条件1〜6を**この順に**見て、1つでも外れれば件は今のまま:
   - 条件1: `row.get("status_effect") == "excluded"` かつ `row.get("status") == "Sold out"` かつ `row.get("price_normalized") is None` かつ `row.get("quantity_normalized") is None`。
   - 条件2: `len(row["lines"]) == 1`。行の文字は `lines[row["lines"][0] - 1]`。
   - 条件3: `row.get("match_status") == "ambiguous"`。`group = split_list_shime(行の文字, sold_out_words, m)`（`m` は区切り s に対し `r = match_text_g2(s, masters)` で、`r.status == "matched"` なら `r.product_id`、ほかは None）が None でなく、`group` の全部が `row["match_candidates"]` にある。
   - 条件4: `i not in (fixed_products or {})`。
   - 条件5: `built = {p: build(i, p) for p in group}`。どの p でも `condition_decided_by_word(b) and not is_kind_default_basis(b)`（`b = built[p]["condition_basis"]`）が True なら動かない。
   - 条件6: ほかの件 j（j != i）のうち条件1の完売に当たらない件（在庫の件）の `product_id` と `match_candidates` に `group` の商品が1つでもあれば動かない。あわせて `followup_ref` が None でなければ、`message_id, ref_text = followup_ref` とし、`decide_followup(extracted, lines, build_reference_lines(ref_text, masters), units=unit_words(unit_alias_to_info), plural_words=masters.followup_plural_words)` を流す。在庫の件 j の決定の `product_id` が `group` にあれば動かない（渡す値は `_apply_followup` と同じ。変えない）。
   - 相手: `group` の順に p ごとに `with_p = [*extracted[:i], built[p], *extracted[i + 1:]]` を作り、`list_shime_targets(p, with_p, i, soldout_posts, fixed_products, box_rule=box_rule, post_text=post_text)` を取る。
   - 相手のある p が無ければ件は今のまま。あれば最初の p を先頭の商品 `head` とし、相手を `head` の物を先に、残りを `group` の順に並べ、`(product_id, condition_id)` の重なりは最初だけ残す。
   - 作り直した件: `{**built[head], "match_status": MATCH_STATUS_MATCHED_LIST_SHIME, "product_list_shime": {"separators": <行で見つかった区切りの字の list>, "products": list(group)}, "soldout_targets": [<_apply_soldout_inherit と同じ6つのキーの dict>], "soldout_target_basis": CONDITION_BASIS_SOLDOUT_LIST_SHIME}`。
3. `_extract_v102` の `if ctx.product_first is not None:` の中の先頭（`extracted = _apply_context_work(` の前）に足す:
   ```
   if soldout_posts:
       extracted = _apply_list_shime(
           extracted, build, lines, ctx.product_first, soldout_posts, ctx.sold_out_words, fixed_products,
           ctx.product_first.shime_box_all_states, "\n".join(lines), followup_ref, ctx.unit_alias_to_info,
       )
   ```
   ほかの行は動かさない。

### C. `backend/app/services/line_analysis_v102_svc.py`（2か所だけ）
- `gemini_raw_copy_v102_soldout_ref` の import に `MATCH_STATUS_MATCHED_LIST_SHIME` を足す。
- `_RESOLVED_MATCH_STATUSES = (` の tuple の最後に `MATCH_STATUS_MATCHED_LIST_SHIME` を足す。

## 触らないもの
`condition_decided_by_word`・`decide_soldout_inherit`・`_stranded_stock`・`_soldout_target` の中身、`parse_v101_response`、規則1〜13の関数、`backend/app/tools/`、既存の試験ファイル全部、DB、`migrations/`、`.github/`、`scripts/`、指示書の定数、`docs/`（取り込んだ設計書も書き換えない）。

## 試験（新しいファイル `backend/tests/test_v102_list_shime.py` を Write で作る）
- 冒頭の説明文に「設計: docs/handoff/shime-bundle-close/design-oneline.md §3-2。商品・原文はすべて架空。」と書く。
- 道具は `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`・`backend/tests/test_v102_bundle.py`・`backend/tests/test_v102_shime_bundle.py` の同じ働きの物を読み、必要な分だけこのファイルに写す（ほかの試験ファイルを import しない）。
- 名前は `test_t1_...` 〜 `test_t16_...`。設計 §3-2 の T1〜T16 を1つずつ書く。原文は「型番AA-01」「型番BB-02」「〆」のような架空の文字だけ。
- T1〜T5 は `split_list_shime` を直接、T6〜T8・T10〜T16 は `_extract_v102`（または `extract_v101_items(..., v102_fixes=True, ...)`。既存の試験の呼び方に合わせる）で確かめる。
- T9 は、既存の試験で `_RESOLVED_MATCH_STATUSES` を通す形（DB なし）があればその形で product_id・pid_resolved・pid_basis を見る。DB が要る形しか無ければ、DB なしで確かめられる所まで書き、報告に「T9 は〇〇まで」と書く。
- T15 の followup の形は、単位の語を含む直前の投稿の行で作る。

## 確かめ（全部流して生出力を残す）
1. `cd backend && python -m pytest tests/test_v102_list_shime.py -q --tb=short`
2. `cd backend && python -m pytest tests/test_gemini_raw_copy_v101.py tests/test_gemini_raw_copy_v102_soldout_ref.py tests/test_v102_bundle.py tests/test_v102_shime_bundle.py tests/test_line_analysis_v102_svc.py -q --tb=short`
3. `git diff origin/main --stat`
4. `git diff origin/main -- backend/app/services`

## 合格の形
- 確かめ1: 16件以上 passed、failed 0。
- 確かめ2: failed 0（DB が要って skipped になる物は数だけ書く）。
- 確かめ3: 変わったファイルは `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`・`backend/app/services/gemini_raw_copy_v101.py`・`backend/app/services/line_analysis_v102_svc.py`・`backend/tests/test_v102_list_shime.py` と、設計の枝から取り込んだ `docs/handoff/shime-bundle-close/` の4つ（recon-oneline.md・design-oneline.md・review-oneline.md・card-oneline.md）と `.claude-pipeline/active-work.d/` の登録だけ。消した行（deletions）は import の並びと `_RESOLVED_MATCH_STATUSES` の行だけ。
- 合わないときも止まらず、値と名前を報告に書く（判定は Opus が行う）。

## commit と push
- commit 文は Write でファイルに書いて `git commit -F <ファイル>` で流す。良い例: `fix(v102): close every product in a one-line list shime (rule 14, design shime-bundle-close oneline)`。最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push -u origin release/shime-oneline-bundle-impl` を単独で流す。
- PR は作らない。マージしない。

## 止まる条件（止まるのはこれだけ）
- push・commit がフックや見張りに止められた／作業場所が作れない／merge が衝突した／最初の grep で決めた5ファイルの外に出た／確かめ1で failed が出て、直し方が設計 §3-1 とこのカードの文の中に無い。
- 止まるときは言い換えて再試行しない。

## 守ること
- Bash に PostgreSQL の対話ツールの名前を書かない。sleep しない。ファイルの作成と編集は Write/Edit で行う（ヒアドキュメント禁止）。git は1命令ずつ流す。
- 本番・DB・外部の道具には触らない。

## 報告（最後の発言。1発言600字以内に分け、番号を付ける）
- 冒頭: 「本報告はカード shime-bundle-close oneline（規則14）の実行結果である」。
- 最初の grep の結果、確かめ1〜4の生出力（4 は長ければ前半と後半を分けて全文）。
- push した枝と HEAD。
- 止まったとき: 止まった手順／最後に流した命令／止まった理由の原文。
- 最後の行: `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。

（カードここまで）
