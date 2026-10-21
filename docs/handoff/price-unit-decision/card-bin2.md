# 実装カード: 値段で単位を決める 便2（対象を広げる・Pack・状態の写し・理由の外し方）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md・11-lint.md

受領確認: 着手前に「カード受領・worktree release/price-unit-code-bin2」と 1 行返してから始める。

PO 実装承認: 2026-10-21「1」（便1・便2 を作る）。種類の正本: 2026-10-21 PO「1」（状態の種類は状態マスタの札 `line_conditions.condition_def_id` から読む。コードに対応表を持たない）。カートン=未開封・サーチ済み箱=サーチ済み も PO 合意済み（2026-10-21）。
設計: docs/handoff/price-unit-decision/design.md の「B」「B2」「C」「D」「コードの変え方 → 便2」「受入条件 便2 K1」（PR #4585・#4594 マージ済み）。決定: docs/adr/ADR-1036-price-decides-unit.md。
前提の事実: 札 8 行と組 2 行は本番に COMMIT 済み（2026-10-21 05:22:53Z、記録 PR #4599）。今の本番の状態マスタは `docs/handoff/price-unit-decision/data/bin2-defid/evidence/q2.out` に、札 8 行（design.md B2 の表）を足した形。

行番号は今の main（e3e1fd768）。ずれていたら名前で探す。

## 作業場所
- 既に作ってある worktree `/Users/tanizawashingo/worktrees/salesanchor/release-price-unit-code-bin2`（ブランチ release/price-unit-code-bin2、origin/main e3e1fd768 起点）の中だけで作業する。本店（~/salesanchor）で checkout・編集しない。
- 開始時に `./scripts/dev/executor-preflight.sh || exit 1`。
- このカード自身（card-bin2.md）は Opus がこのブランチに置く。消さない。

## やること

### 1. `backend/app/services/v102_buyback_unit_svc.py`
1. 設定（:27-31・`BuybackSettings` :75-80・`parse_settings` :92-105・`load_settings` :149-154）
   - `SETTING_PACK_MAX = "unit_buyback_pack_max"` を足す。必須の 4 key（`_SETTING_KEYS`）には入れず、読む SQL の key には足す（無くてもよい key）。
   - `BuybackSettings` に `pack_max: Decimal | None` を足す。
   - `parse_settings`: key が無い → `pack_max=None`（Pack を決めない＝今と同じ）。key があって数でない・有限でない・`0 < pack_max < box_min` でない → 設定全体を不正として None。
2. 判定 `decide_code`（:108-117）: 返り値を「単位の種類（`"Box"`・`"Case"`・`"Pack"` の 3 つ。単位→群の対応 Box→box・Case→case・Pack→pack はコードの小さな定数でよい）と r」にする。`pack_max` があって `r <= pack_max` なら Pack。Box・Case の帯は今と同じ。
3. 対象 `is_candidate`（:136-146）に**必須**引数 `unit_alias_to_info` を足す。今の条件 `has_no_unit_and_condition_word(item)`（:120-133）に **or** で次を足す（ほかの条件 pid・価格・bundle・excluded・セット系は今のまま全体にかかる）:
   - `item["product_category"] == PRODUCT_KUBUN_BOX`（`backend/app/services/gemini_raw_copy_v102_product_first.py:48`）
   - かつ `condition_basis` が `_FLAG_NOTE_PREFIX` で始まらない
   - かつ 単位の語で決まっていない: `unit_basis` が Mapping で、`alias` が None、または `resolve_unit_v2(alias, unit_alias_to_info)[1]`（`backend/app/services/tcg_analyzer_svc.py:817`）が `BOX_RECHECK_UNIT_KUBUNS`（`backend/app/services/gemini_raw_copy_v102_product_first.py:65-67`）に入る。
4. 状態の読み方（B2）: `CONDITION_CODE_BOX`・`CONDITION_CODE_CASE`（:34-35）・`_TARGETS_SQL`（:68-72）・`load_targets`（:166-175）を置き換える。
   - SQL: `public.line_conditions` の `is_active = TRUE AND tenant_id IS NULL AND value_group = ANY(['box','case','pack'])` の行を全部、`code・id・canonical・value_group・unit_id・condition_def_id` と、`line_units`（有効）を LEFT JOIN した単位の canonical 付きで読む（1 回の SQL）。
   - 群ごとに: `unit_id` の種類数、既定（札 2 か 7）の行数、札ごとの行数を数える。
   - 止める範囲: box・case の群は「`unit_id` が 1 種類（NULL を除いて 1 種類で、NULL の行が無い）かつ 既定の行がちょうど 1 行」のときだけ使える。どちらかが使えなければ None（便全体で何もしない。今の「CN0003・CN0001 が引けない」と同じ扱い）。pack の群は `unit_id` が 1 種類でなければ pack だけ使えない（Box・Case は決める）。
   - warning（design.md B2「ログ」）: (a) 群に同じ札の行が 2 行以上 (b) 群（box・case・pack どれも）で既定の行がちょうど 1 行でない（pack は warning だけで止めない）(c) 群の `unit_id` が 2 種類以上。群・札・件数・code を出す。今の :172 と同じ `logger.warning("[buyback_unit] …")` の書き方。
   - 返すもの: 群ごとの「札 → 写し先の行（id・canonical・単位の canonical）」（札ごとに**ちょうど 1 行**のものだけ。2 行以上の札は入れない）、群が使えるか、`condition_id → 札`（読んだ全行。札が空の行は None）、`code → 札`。既定の同一視 {2, 7} だけはコードの定数で持つ。種類×単位の対応表をコードに持たない。
5. 種類の決め方（design.md「コードの変え方 → 便2」の「状態の種類」の (1)(2) の順のまま）
   - (1) `condition_decided_by_word(basis)` が False の行は、今の状態（Error・FLAG_SINGLE を含む）に関係なく「既定」。
   - (2) True の行は、今の `condition_id` を逆引きして札を出す。2・7 なら「既定」、それ以外はその札。逆引きに無い・札が None なら何もしない。
   - `item["review"]` の要素で `kind == "condition_multiple_candidates"` のものの `codes` も、`code → 札` で種類にする（2・7 は既定）。1 つでも引けない（読んだ行に無い・札が None）なら何もしない。
   - 今の状態の種類と codes の種類を合わせて、種類が 2 つ以上なら何もしない。1 つならその種類。
   - 写し先: 値段で決まった単位の群で、その種類（既定なら札 2 か 7）の行がちょうど 1 行ならその行。無ければ何もしない。群が使えなければ何もしない。
   - Pack は `item["product_category"] == PRODUCT_KUBUN_BOX` の行だけ。それ以外の行で Pack と出たら何もしない。
6. 理由: `REASONS_DROPPED_WHEN_DECIDED`（:44）に `"condition_multiple_candidates"` を足す。
7. `apply_buyback_units`（:196-226）に**必須**引数 `unit_alias_to_info` を足し（`posted_at` の前でも後でもよいが、呼び出し側と揃える）、`is_candidate` に渡す。
   - 同じ値（:221-222）: 今の (状態, 単位) と写し先が同じでも、`review_reasons` に外す理由があれば理由だけ外す。外す理由が無ければ今どおり何もしない。
   - basis（`with_decision` :182-193）は design.md D の表どおり:
     - 語で決まった行（`condition_decided_by_word` が真）: 値が変わる → 状態は写し先、basis は今の basis の後ろに `|PRICE:①r=` と比（小数 2 桁） を足す（先頭は変えない）。値は同じで理由だけ外す → 同じく後ろに足す。
     - 語なしの行: 値が変わる → 今と同じ `BUYBACK:` の形（今の with_decision の書き方）。値は同じで理由だけ外す → basis は変えない。
     - どれも 100 字で切る（今の `_CONDITION_BASIS_MAX`）。
   - 単位 id が引けなければ何もしない（今と同じ）。入力は変えない（新しい dict を返す）。

### 2. `backend/app/services/line_analysis_v102_svc.py`
- `_buyback_units`（:962-982）に**必須**引数 `unit_alias_to_info` を足し、:966 の `is_buyback_candidate(item, values, unit_alias_to_info)` と :978 の `apply_buyback_units(...)` に渡す。
- 呼び出し（:1150）: `_write_results` の中で `masters.get("unit_alias_to_info") or {}` を渡す（:1137 と同じ書き方）。
- ほかは変えない。

### 3. 既存テストの直し（壊れるので合わせる。中身の期待は変えない）
- `backend/tests/test_v102_value_overrides.py:207` `fake_apply` の引数・:212 `is_buyback_candidate` の差し替え（引数 3 つ）・:220 `svc._buyback_units(...)` の呼び出し。
- `backend/tests/test_v102_buyback_unit.py`: :76 `_apply`・:162・:177 の `apply_buyback_units`、:272-273 の `is_candidate`、:291・:300・:315 の `_buyback_units`、:196 `test_parse_settings_requires_four_valid_keys`（pack の key は無くてもよい key として足す）、`_Session.execute`（:38-）・`_WriteSession`（:208-）が `_TARGETS_SQL` に返す行（下の 4. の 11 行の形に替える）。
- `backend/tests/test_gemini_raw_copy_v102_unit_state_set.py:185`・`:189`（`bb.is_candidate` を引数 3 つで）。
- 今のテストが期待している結果（Box・Case の決め方・basis）が変わる場合は直さずに止める（下の想定分岐）。

### 4. 足すテスト（`backend/tests/test_v102_buyback_unit.py`）
状態マスタのテスト用の行は、本番と同じ 11 行の形で作る（`docs/handoff/price-unit-decision/data/bin2-defid/evidence/q2.out` の box・case・pack の行に、design.md B2 の札を入れたもの）:

| code | canonical | 群 | 単位 | 札 |
|---|---|---|---|---|
| CN0003 | Sealed box | box | Box | 2 |
| CN0004 | Damaged sealed box | box | Box | 3 |
| CN0005 | No shrink box | box | Box | 4 |
| CN0006 | Opened box | box | Box | 5 |
| CN20261008072213 | Searched box | box | Box | 8 |
| CN0001 | Case | case | Case | 2 |
| CN0002 | Damaged case | case | Case | 3 |
| CN0009 | Opened case | case | Case | 5 |
| CN0007 | Unsearched pack | pack | Pack | 7 |
| CN0010 | Searched pack | pack | Pack | 8 |
| CN0013 | AR confirmed pack | pack | Pack | なし |

1. B の表の 15 組（design.md「B. 状態の決め方」の表。種類 5 × 単位 3）を、期待値をテストに直書きして 1 組ずつ確かめる（parametrize）。「決めない」の組は values が変わらない。
2. K1 の組（design.md 受入条件 便2 K1 をそのまま）: 語なし／「個」（unit_basis の alias が「個」で区分が条件つき）／ダメージ語／サーチ済語／シュリンクなし語／「未開封」「未サーチ」の語（既定と同じ）／別の区分の語だけ（`item["review"]` に `{"kind": "condition_multiple_candidates", "codes": [...]}`。例: Opened box の語＋codes に CN0006 → Case の帯で Opened case。種類が 2 つ以上 → 何もしない。codes が引けない → 何もしない）× 比（Box・Case・Pack・帯の間）。
3. 主例: ダメージ語で今すでに Damaged sealed box・Box・`condition_multiple_candidates` の行が、Box の帯で理由だけ外れ、basis の後ろに `|PRICE:①r=` が付く。語なしで値が同じ・理由ありの行は basis が変わらず理由だけ外れる。
4. 変わらない行: 単位の語がある行（alias「パック」「BOX」で区分が条件つき等でない）・単品語の印の行・セット系・人が直した行（skip）・箱系でない分類で Pack と出た行。`unit_buyback_pack_max` が無ければ Pack を決めない。`pack_max` が `box_min` 以上・0 以下なら設定全体が None。
5. 止める範囲とログ: 札を入れる前の形（CN0003・CN0001 に札が無い）→ 便全体で何もしない。札が空の行・群に同じ札が 2 行の組 → その組は何もしない＋warning (a)。pack の群だけ `unit_id` が 2 種類 → Box・Case は今どおり決まり Pack だけ決めない＋warning (c)。pack に既定の行が無い → warning (b) だけで Box・Case は決まる。
6. 原文に単位の語が書いてあれば原文が優先される（PO 2026-10-21）: 価格の行が「サーチ済みパック @300」のように状態の語と単位の語がくっついた書き方でも、`find_unit_product_first`（`backend/app/services/gemini_raw_copy_v102_product_first.py:511`）が単位の語「パック」を見つけ、その行は `is_candidate` が False になる（値段では決めない）ことを確かめる。`find_unit_product_first` を呼んでいる既存のテスト（`grep -rn find_unit_product_first backend/tests`）の作り方に合わせる。「サーチ済みBOX」「未開封カートン」も同じ形で 1 件ずつ。

### 5. 記録 SQL（ADR-1007）を作る: `docs/handoff/price-unit-decision/data/bin2/`
- precheck.sql・dryrun.sql・commit.sql・rollback.sql・verify.sql。形は便1 の `docs/handoff/price-unit-decision/data/bin1/` をそのまま写す（`*.sql` は gitignore なので `git add -f`）。
- 中身: `tcg_distribution_settings` に key `unit_buyback_pack_max`・value `0.2`・note「買取価格による単位・状態の判定: 比がこの値以下ならパック」の 1 行を足す。
- precheck は「その key がまだ無い・`unit_buyback_box_min` が 0.5」を確かめ、違えば止まる形。dryrun は ROLLBACK で終わる。rollback はその 1 行を取り除き、取り除いた件数が 1 であることを確かめる。verify は 1 行・値 0.2。
- 本番では流さない（PO が後で `!` で流す）。

## 触らない範囲
- 上記以外の製品コード・既存テスト・frontend・migrations・deploy.yml・本番 scripts。
- `_write_results` の順序（人の直し → 便BB → 規則13 → 便UP → `_apply_decisions`）、便UP、規則13、〆の規則 11b、`gemini_raw_copy_v102_product_first.py` の状態・単位の決め方（`find_unit_product_first` を含む）、人が状態を直した行の skip、`unit_basis`、DB の形、便1 の物差し（`_MEDIAN_SQL`・`load_medians`・`posted_at`）。
- 本番 DB・設定値（記録 SQL を作るだけ）。

## 想定分岐（迷ったら停止し、Opus へ NEEDS_DECISION: で返す）
- 4.6 で `find_unit_product_first` が「サーチ済みパック」から「パック」を見つけない → 単位の決め方は直さずに止め、テストの入力と出力を返す（PO の「原文優先」が崩れるので、Opus が設計を決める）。
- 今の Box・Case のテスト（:83・:89・:97・:102・:108・:117・:124・:130 等）の期待が変わる → 直さずに止める（便2 は Box・Case の今の決め方を変えない設計）。
- 上の 3. 以外の既存テストが落ちる → 直さずに止める。
- 行番号の中身が設計と違う（例: `_write_results` の便BB の位置が人の直しの前にある、`item["review"]` に codes が無い形）→ 止める。
- `line_conditions` に `tenant_id`・`value_group`・`condition_def_id` の列が無い → 止める。

## 完了の条件
- ローカルで `backend/tests/test_v102_buyback_unit.py`・`backend/tests/test_v102_value_overrides.py`・`backend/tests/test_gemini_raw_copy_v102_unit_state_set.py` と、`line_analysis_v102`・`gemini_raw_copy_v102` を含むテストが通る（生出力をファイルへ）。
- `gh auth status` で shingo-cc を確認し、worktree 内から PR を起票（base main。migration を含まないので Draft にしない）。本文はテンプレ起点で「### 標準ワークフロー確認」（recon/design は docs/handoff/price-unit-decision/、対象 ADR-1036、触るファイルを 1 行カンマ区切り、削除するファイル なし、PO 承認 2026-10-21「1」）。社外秘の原文・投稿番号は入れない。
- 報告は DONE / BLOCKED: / NEEDS_DECISION: で、PR URL・HEAD・テスト生出力のパス。

END OF CARD
