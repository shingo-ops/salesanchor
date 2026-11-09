# 実装カード: 値段で単位を決める 便C（状態の語が無いパックはサーチ済み・既定の code を 1 か所に）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md・11-lint.md

受領確認: 着手前に「カード受領・worktree release/pack-default-searched-code」と 1 行返してから始める。

PO 実装承認: 2026-11-09「1」（この設計で実装まで進める）。目的の PO の言葉: 2026-11-09「状態が書いていないパックは全てサーチ済みに倒す、安全側に倒すため」。プロモパックは今のまま（2026-11-09「1」）。
設計: docs/handoff/price-unit-decision/design.md の「追補 C（2026-11-09）」。決定: docs/adr/ADR-1036-price-decides-unit.md What 4。

行番号は origin/main ded6cbe3e。ずれていたら名前で探す。

## 作業場所
- origin/main から `bash scripts/new-worktree.sh release/pack-default-searched-code` で worktree を作り、その中だけで作業する。
- 開始時に `./scripts/dev/executor-preflight.sh || exit 1`。

## やること

### 1. `backend/app/services/tcg_analyzer_svc.py`（値は変えない。置き場所を 1 か所にするだけ）
- 定数（`ENGINE_VERSION` :60 の近く）を足す:
  ```python
  # 状態の語が無い行の、状態マスタの群（line_conditions.value_group）ごとの既定の状態の code。
  # R4・R5（resolve_condition_v2）と値段で単位を決める規則（v102_buyback_unit_svc）の両方がここを読む（正本はここ 1 か所）
  DEFAULT_CONDITION_CODE_BY_GROUP = {"box": "CN0003", "case": "CN0001", "pack": "CN0010"}
  ```
- :953 `_find_cond_id(cond_entries, "CN0001")` → `_find_cond_id(cond_entries, DEFAULT_CONDITION_CODE_BY_GROUP["case"])`。
- :956 `"CN0003"` → `DEFAULT_CONDITION_CODE_BY_GROUP["box"]`。
- :974 `"CN0010"` → `DEFAULT_CONDITION_CODE_BY_GROUP["pack"]`。
- :965 の `"CN0007"`（メモの語を見る行）・canonical の文字（`"Case"`・`"Sealed box"`・`"Searched pack"`）・返す basis は変えない。

### 2. `backend/app/services/v102_buyback_unit_svc.py`
1. import（:29）に `DEFAULT_CONDITION_CODE_BY_GROUP` を足す。
2. :44-45 を置き換える:
   ```python
   # 語で決まった状態の札のうち、値段で決まった群にその札の行が無ければ、その群の既定（DEFAULT_CONDITION_CODE_BY_GROUP）に写すもの（2=未開封・7=未サーチ）
   _FALLBACK_TO_DEFAULT_LABELS = frozenset({2, 7})
   ```
   `_KIND_DEFAULT`（:46）は「語で決まっていない行」の印として残す。
3. `_kind`（:223-224）は消す。使っている所（:268・:316・:329）は札をそのまま使う。
4. `ConditionMap`（:107-117）: 形は変えない（`targets` = 群 → 種類 → 写し先）。docstring を「種類は札（int）と `_KIND_DEFAULT`。`_KIND_DEFAULT` はその群の既定の code の行」に直す。
5. `load_targets`（:227-275）:
   - :255-257 の既定の数え方を「その群で code が `DEFAULT_CONDITION_CODE_BY_GROUP[group]` の行」にする。warning (b) は「その行がちょうど 1 行でない、またはその行の札が空」のとき。文面は `"[buyback_unit] 状態マスタの群 %s の既定（code %s）の行が %d 行です、または札が空です（札の入った 1 行であるべき）"` の形（群・code・件数）。
   - :263 の `usable`: box・case は「`single_unit` かつ 上の既定の行が札の入った 1 行」。pack は今どおり `single_unit` だけ。
   - :265-269: 札ごとに 1 行のものは `targets[group][札]`（札が None の行は入れない。今と同じ）。それに加えて、既定の行が札の入った 1 行なら `targets[group][_KIND_DEFAULT]` = その行。
6. `_current_kind`（:310-316）: 語で決まった行は札をそのまま返す（`_kind` を通さない）。
7. `_review_code_kinds`（:319-330）: 札をそのまま集める（`_kind` を通さない）。
8. `decide_kind`（:333-349）を次の `decide_target` に置き換える（名前を変える。呼び出しは :381-382 と下の 3. のテストだけ。`git grep -n decide_kind` で 0 件になることを確かめる）:
   ```python
   def _target_of(rows: Mapping[Any, Target], kind: Any) -> Target | None:
       if kind in _FALLBACK_TO_DEFAULT_LABELS:
           return rows.get(kind) or rows.get(_KIND_DEFAULT)
       return rows.get(kind)


   def decide_target(item, values, cmap, group) -> Target | None:
       """値段で決まった群 group での写し先。決められなければ None（何もしない）。
       今の状態の種類と codes の種類を合わせ、それぞれの写し先が 1 つにそろうときだけ（種類ではなく写し先で比べる。design.md 追補 C）。
       今の状態が既定で codes があるときは、既定を数えず codes だけを使う（今と同じ）。"""
       rows = cmap.targets.get(group)
       current = _current_kind(values, cmap)
       if rows is None or current is None:
           return None
       code_kinds = _review_code_kinds(item, cmap)
       if code_kinds is None:
           return None
       if not code_kinds:
           if _REASON_MULTIPLE in (values.get("review_reasons") or "").split(REASON_SEPARATOR):
               return None
           kinds = {current}
       else:
           kinds = code_kinds if current == _KIND_DEFAULT else {*code_kinds, current}
       found = {_target_of(rows, k) for k in kinds}
       return next(iter(found)) if len(found) == 1 and None not in found else None
   ```
9. `apply_buyback_units` :381-384 を `target = decide_target(items[i], values, cmap, _UNIT_GROUP[unit])` ＋ `if target is None: continue` にする。ほかは変えない。

### 3. 既存テストの直し（設計の追補 C「変えること 4」の最後の項に書いた分だけ）
- `backend/tests/test_v102_buyback_unit.py`
  - :347 `("default", "Pack"): "Unsearched pack"` → `"Searched pack"`。
  - :407 期待を `("Searched pack", "Pack")` に、注記を「未開封 @箱の 1/10 → パックの群に札 2 の行が無いので既定の Searched pack」に。
  - :531-539: 消す行を `CN0007` から `CN0010` に替え、期待を次にする: 語なし @1000 → 変わらない（Pack の既定が無い）／語なし @10000 → Box／「未サーチ」の語（:408 の `unsearched` と同じ形）@1000 → Unsearched pack・Pack／warning に「群 pack」と「既定」。
  - :542-547: `two_box_defaults` を「CN0003 を消した形」に替え、何もしない（便全体）ことを確かめる。`no_case_default` はそのまま。
- `backend/tests/test_v102_condition_heading.py:355-362`: `bb.decide_kind(...)` と `cmap.targets[...].get(kind)` を `target = bb.decide_target(item, values, cmap, bb._UNIT_GROUP[unit]) if decided is not None else None` に替え、返す 2 つ目を `target` にする（:370 の `marked[1] == plain[1]` は Target 同士の比較になる）。:365-378 の期待は変えない。

### 4. 足すテスト
- `backend/tests/test_v102_buyback_unit.py`:
  1. C3: 「未サーチ」の語（今の状態 Unsearched pack・basis `R2:未サーチ`）＋ `item["review"]` に `{"kind": "condition_multiple_candidates", "codes": ["CN0003"]}` の行 → 箱の帯（@10000）で Sealed box・Box。
  2. C3b (i): 同じ行 → パックの帯（@1000）で何もしない（values が変わらない）。
  3. C3b (ii): 「サーチ済」の語（`_kvalues("searched", ...)`・basis `R2:サーチ済`）＋ codes `["CN0003"]` → パックの帯で Searched pack・Pack・理由が外れる。同じ行の箱の帯（@10000）は何もしない（Searched box と Sealed box が食い違う）。
  4. 箱の群に札 7 の行 `("CN9002", 91, "Unsearched box", "box", 10, 7, "Box")` を足した形: 「未サーチ」の語 @10000 → Unsearched box、語なし @10000 → Sealed box、warning (b) は出ない。
  5. 既定の行に札が無い形（CN0010 の札を None）: 語なし @1000 → 変わらない、warning (b)。
- `backend/tests/test_tcg_keyword_matching.py` か R4・R5 を試している既存のファイル（`git grep -ln "R5:パック既定" backend/tests`）の作り方に合わせて 1 件: `DEFAULT_CONDITION_CODE_BY_GROUP == {"box": "CN0003", "case": "CN0001", "pack": "CN0010"}`。

## 触らない範囲
- 上記以外の製品コード・既存テスト・frontend・migrations・deploy.yml・本番 scripts・DB・設定値。
- `gemini_raw_copy_v102_product_first.py`（プロモパックの R8 を含む）、`gemini_raw_copy_v101.py`、単位の語の探し方、値段の帯の数字（`decide_code`）、`is_candidate`、`with_decision` と basis の書き方、`REASONS_DROPPED_WHEN_DECIDED`、`_write_results` の順序、`tcg_supplier_quality_svc.py`。

## 想定分岐（迷ったら停止し、Opus へ NEEDS_DECISION: で返す）
- B の表の Box・Case 列（`test_b_table_15_combinations` の Box・Case の 10 組）が 1 組でも落ちる → 直さずに止める（便C は箱・カートンの結果を変えない設計）。
- 上の 3. に書いていない既存テストが落ちる → 直さずに止める（落ちたテスト名と生出力を返す）。
- `tcg_analyzer_svc.py` を `v102_buyback_unit_svc.py` から import すると循環 import になる → 止める（定数の置き場所は Opus が決める）。
- :953・:956・:974 の中身が上と違う（code が違う等）→ 止める。
- `git grep -n '"CN0001"\|"CN0003"\|"CN0010"' backend/app` が、直した後に :965 以外で 1 件でも残る → 止めて場所を返す。

## 完了の条件
- ローカルで `backend/tests/test_v102_buyback_unit.py`・`backend/tests/test_v102_condition_heading.py`・`backend/tests/test_v102_value_overrides.py`・`backend/tests/test_gemini_raw_copy_v102_unit_state_set.py`・`backend/tests/test_tcg_keyword_matching.py`・`backend/tests/test_gemini_raw_copy_v102_product_first.py`・`backend/tests/test_tcg_supplier_quality.py` が通る（生出力をファイルへ）。
- `gh auth status` で shingo-cc を確認し、worktree 内から PR を起票（base main。migration を含まないので Draft にしない）。本文はテンプレ起点で「### 標準ワークフロー確認」（recon/design は docs/handoff/price-unit-decision/、対象 ADR-1036、触るファイルを 1 行カンマ区切り、削除するファイル なし、PO 承認 2026-11-09「1」）。社外秘の原文・仕入元名・投稿番号は入れない。
- 報告は DONE / BLOCKED: / NEEDS_DECISION: で、PR URL・HEAD・テスト生出力のパス。

END OF CARD
