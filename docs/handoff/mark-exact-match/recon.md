# recon: 型番が「型番-数字」（カード番号）に当たる件（EB-02 と EB02-003）

- 基準: origin/main 035b0145e（2026-10-18 JST。`git rev-parse HEAD` で確認）
- 調べた人: Sonnet（読み取り）。試算の数値は Opus 提示の `/tmp/CC報告ファイル/mark_exact_match_simulation.txt`（社外秘データは含まない集計）を引用
- 設計: docs/handoff/mark-exact-match/design.md
- 設計仕様書（あるべき姿）: 該当領域の索引は `docs/specs/line-analysis-tuning/README.md`（LINE解析の調整記録）。本件は §1.8 の「既存の延長・修正」に当たり、新しい仕様書は作らない（`docs/STANDARD-WORKFLOW.md` §1.8）

## 1. 既存 ADR・設計の検索結果（STANDARD-WORKFLOW §1 Phase 2）
実行したコマンドと生出力: `/tmp/CC報告ファイル/mark_exact_match_design/adr_search1.txt`・`adr_search2.txt`

| 検索 | 結果 |
|---|---|
| `git grep -il "strict_code\|_strict_code_pattern\|厳格.*品番\|品番らしい" docs/adr` | 該当なし（grep 済み）。厳格な品番の照合を定めた ADR は無い |
| `git grep -il "extraction_judgement" docs/adr` | `docs/adr/ADR-1006-product-code-pm5-and-mark-only-matching.md` のみ |
| `git grep -il "match_product" docs/adr` | 該当なし |
| `git grep -il "product_code" docs/adr` | ADR-1001・ADR-1002・ADR-1006 |
| `docs/adr/FEATURE-INDEX.md` を「照合・型番・mark・v102・書き写し・LINE解析・商品マスタ」で検索 | 18行目の在庫/商品マスタ（ADR-099・093・014）だけ。照合規則の行は無い |
| `git grep -il "品番らしい\|strict_codes\|_strict_code" -- docs` | ADR は 0 件。handoff の 6 文書: `docs/handoff/excl-cond-contain/`・`fix-exclude-keyword-boundary/`・`line-match-price-digit-boundary/`・`prototype-v102-product-first/`・`v102-followup-post-ref/`・`v102-shime-inventory-ref/` |

- 関係する ADR は ADR-1006 だけ。内容は「品番の照合は mark だけで行う（v7 は `_code_candidate_basis` から product_code を外す）」（`docs/adr/ADR-1006-product-code-pm5-and-mark-only-matching.md:14`・`:52-54`）。**何を照合に使うか**の決定であり、**当たりの境界の作り方**は扱っていない。本件の変更は ADR-1006 と食い違わない。
- 厳格な照合の導入と境界の細かい調整は、これまで ADR を起こさず handoff の設計で行われている（上の 6 文書。直近の先例: `docs/handoff/line-match-price-digit-boundary/design.md`、数字だけの値と金額の境界。関連 ADR として ADR-154・135・136 を引いた）。
- **結論（ADR の新規起案が必要な規模か）**: 不要。理由: ①変更は境界条件1つで、何を照合に使うかの方針（ADR-1006）は変えない、②先例（price-digit-boundary ほか）も handoff の設計＋既存 ADR 参照で通っている、③DB・migration を触らない。ADR-1006 の更新も不要（本文に境界の記述が無い）。ただし「照合規則の変更に ADR が必要か」の線引きは文書化されていない（design.md の未決 U3）。

## 2. 対象コード（実物。すべて origin/main 035b0145e）
パスはリポジトリ相対。フルパスは `/Users/tanizawashingo/worktrees/salesanchor/release-mark-exact-match/` を前につける。

### 2-1. 区切り文字の集合と正規表現の部品
- `backend/app/services/extraction_judgement_svc.py:155-157`
```python
_CODE_SEPARATOR_CHARS = (
    " 　-‐‑–—―ー−・_.'’‘´́`"
)
_CODE_SEPARATOR_RE = "[" + "".join(re.escape(ch) for ch in _CODE_SEPARATOR_CHARS) + "]*"
```
  - ハイフン類は ASCII `-`、U+2010、U+2011、U+2013、U+2014、U+2015、U+2212、U+30FC（ー）。U+2012（フィギュアダッシュ）は含まれない。
- `backend/app/services/extraction_judgement_svc.py:160`: `_SYMBOL_GAP_RE`（値の中の記号の隙間に許す文字）。
- `backend/app/services/extraction_judgement_svc.py:22-28` `fold_for_match`: NFKC → 小文字 → カタカナをひらがな化（U+30A1〜U+30F6 のみ。U+30FC は変わらない）。全角の `－`（U+FF0D）・`ＯＰ０１` は NFKC で半角になる（`/tmp/CC報告ファイル/mark_exact_match_design/r1_check_out.txt` の `ＯＰ－０１` で確認）。U+2212 など NFKC で変わらない文字は残る。

### 2-2. 変更する関数（今の全文）
- `backend/app/services/extraction_judgement_svc.py:173-198`
```python
@lru_cache(maxsize=_CODE_PATTERN_CACHE_SIZE)
def _strict_code_pattern(raw: str) -> tuple[str, re.Pattern[str]] | None:
    """品番らしい値なら（英数字だけ並べた文字列, 区切りを許す正規表現）を返す。品番らしくなければ None。
    ...
    """
    folded = fold_for_match(raw)
    if not all(_is_code_char(ch) for ch in folded):
        return None
    alnum = "".join(ch for ch in folded if ch in _ALNUM_CHARS)
    if len(alnum) <= _SHORT_VALUE_MAX_LEN or alnum.isdigit() or not any(ch in _LETTER_CHARS for ch in alnum):
        return None
    parts: list[str] = []
    gap_has_symbol = False
    for ch in folded:
        if ch in _ALNUM_CHARS:
            if parts:
                parts.append(_SYMBOL_GAP_RE if gap_has_symbol else _CODE_SEPARATOR_RE)
            parts.append(re.escape(ch))
            gap_has_symbol = False
        elif ch not in _CODE_SEPARATOR_CHARS:
            gap_has_symbol = True
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])")
    return alnum, pattern
```
- **正規表現の組み立て行（変更する1行）**: `backend/app/services/extraction_judgement_svc.py:197`
  `    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])")`
  - 左は「直前が英数字でない」、右は「直後が英数字でない」。値の中の隙間（`_CODE_SEPARATOR_RE`）は文字の**間**にだけ入り、末尾には入らない（`parts` は英数字1文字ごとに「隙間→文字」の順で積む）。このため右側に先読みを足しても、値の内側の区切りの許容には影響しない。
  - 例: 値 `EB-02` → 英数字 `eb02` → パターンは `(?<![a-z0-9])e[区切り]*b[区切り]*0[区切り]*2(?![a-z0-9])`（実物）。原文 `EB02-003` の `EB02` の直後は `-`（英数字でない）ので今は当たる。これが取り違えの原因。
  - この関数が返す `alnum` は呼び出し元の事前絞り込み（`alnum not in nb` …）に使われる。変更しない。

### 2-3. 同じ関数を使う経路（呼び出し元の全走査）
`git grep -n "_strict_code_pattern\|_strict_code_hits" backend` の結果に基づく。

| # | 場所 | 使い方 | 変更の効き方 |
|---|---|---|---|
| 1 | `backend/app/services/extraction_judgement_svc.py:201-209` `_strict_code_hits` | `_strict_code_pattern(raw)` を呼び、事前絞り込み（`:206`）の後 `pattern.search(folded)`（`:208`）。品番らしくない値は None | 変更が直接効く |
| 2 | 同 `:212-226` `_value_hits`（`:217-220` で #1 を呼ぶ） | 値が品番らしければ #1 の結果を返す。そうでなければ従来の規則 | 同じく効く |
| 3 | 同 `:229-239` `_code_candidate_basis` | `product.product_code`・`product.mark` を `_value_hits` に渡す（`:236-237`） | **mark・product_code の照合**。今回の本命 |
| 4 | 同 `:242-255` `_keyword_matches` | 検索ワードを空白で分けた各トークンを `_value_hits` に渡す（`:253`） | 型番らしい検索ワード（例 `EB02`）にも効く |
| 5 | 同 `:320-331` `_exclude_hit` | 除外ワードを #1 で判定（`:322-324`） | 型番らしい除外ワードにも効く（除外が**外れる**側に動きうる） |
| 6 | 同 `:372-` `match_product` | `:390` `_code_candidate_basis`、`:391` `_keyword_matches`、`:400` `_value_hits`（`code_hit_values`）、`:405` `_excluded_keywords` | 上の合成 |
| 7 | `backend/app/services/gemini_raw_copy_v102_product_first.py:233` `_g2_hits` → `:239-241`・`:249`、`:267-275` `match_product_g2`（`:275` で `match_product(strict_codes=True)`）、`:295-298` `match_text_g2` | v102 の本線の照合 | #3〜#6 を共有 |
| 8 | `match_text_g2` の呼び出し元: gemini_raw_copy_v102_product_first.py:664（本線 resolve_product_first 内）、`backend/app/services/v102_gap_lines.py:175`・`:202`、gemini_raw_copy_v102_followup.py:48、gemini_raw_copy_v102_soldout_ref.py:169 | 行から商品を決める | #7 を共有 |
| 9 | `backend/app/services/gemini_raw_copy_v102_followup.py:14`（import）・`:56` `extract_tokens`・`:81` `_hits` | 原文の語（`_CODE_TOKEN_RE`、`:20`）のうち `_strict_code_pattern(w) is not None` のものを「型番の語」とし（`:56`）、参照行の `folded` に `pattern[1].search`（`:81-82`）で当てる。**照合結果ではなく原文の探索** | 変更が効く。品番らしさの判定（`is not None`）は変わらない。当て方だけ変わる |
| 10 | `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:17`（import）・`:187-193` `_texts_hit_all`・`:196-197` `_row_hits_all`・`:227`・`:243` | 語が全て1つの参照行に当たるか（型番は `_strict_code_pattern(code)`、`:190-192`） | 変更が効く（#9 と同じ） |

- `backend/app/services/gemini_raw_copy_v102_product_first.py:17` ほかの `_strict_code_pattern` の再公開は無い（#9・#10 は `extraction_judgement_svc` から直接 import しているため、`_strict_code_pattern` を直せば自動で同じものを使う。名前を差し替える必要はない）。
- 本件で扱わない別経路（疎通の確認のみ）:
  - v6: `backend/app/services/tcg_analyzer_svc.py:305` `match_keyword`（純 ASCII 語は `(?<![a-z])…(?![a-z])` の境界）。`_strict_code_pattern` を呼ばない。
  - 登録時の衝突検知: `backend/app/services/tcg_product_code_collision_svc.py:56`・`:98`。`normalize_for_match` 後の「含む」判定で、同じ関数を使わない。
  - frontend: 照合関数を持たない（シミュレーション記録 手順1 の記載。frontend は表示のみ）。
  - 上記3点は `/tmp/CC報告ファイル/mark_exact_match_simulation.txt` 手順1 の記載をそのまま引用。**本 recon では tcg_analyzer_svc.py・collision_svc の中身を再読していない**（未確認の範囲として明記）。

## 3. 観測した事実
### 3-1. 実装の手元検証（リポジトリは変更せず、スクラッチのプラグインで関数を差し替えて実行）
- ファイル: /tmp/CC報告ファイル/mark_exact_match_design/r1_check.py（検証本体）・`r1_check_out.txt`（生出力）・plug/r1_plugin.py（pytest 用差し替え）
- 先読みに使うハイフン類の集合: `\-` U+2010 U+2011 U+2012 U+2013 U+2014 U+2015 U+2212 U+30FC（シミュレーションの variants.py と同じ。U+2012 を含む点だけ `_CODE_SEPARATOR_CHARS` と違う）
- 生出力（`r1_check_out.txt`）の要点（値 → 原文 → 現行 / R1）:
  - `EB-02` → `EB02-003 チョッパーズ`: True → **False**
  - `EB-02` → `EB02-003 / 20個@1000`: True → **False**
  - `EB-02` → `EB02`: True → True
  - `OP-01` → `OP01`・`OP-01`・`【OP-01】`・`OP01×2`・`ＯＰ－０１`・`OP-01 BOX`・`OP01-BOX`・`OP-01-BOX`: すべて True → True
  - `OP-01` → `OP01-001`・`OP01−001`（U+2212）・`OP01ー001`（U+30FC）・`OP01‐001`（U+2010）: True → **False**
  - `OP-01` → `OP01-001 と OP-01 BOX`（同じ行に両方）: True → True（`re.search` は全出現を見るので、区切られた方に当たる）
- 既存テストへの影響（同じ差し替えで実行）:
  - 実行: `cd backend && PYTHONPATH=.:/tmp/CC報告ファイル/mark_exact_match_design/plug python3 -m pytest <10ファイル> -q -n0 --no-cov [-p r1_plugin]`
  - 10ファイル: test_extraction_judgement_svc / test_extraction_judgement_cond_terms / test_gemini_raw_copy_v102_followup / _score_select / _match_g2 / _soldout_ref / _name_only / test_line_analysis_v102_svc / test_v102_buyback_unit / test_tcg_keyword_matching
  - 現行: `1154 passed, 1 warning, 12 errors`（`pytest_baseline.txt`）。R1 適用: `1154 passed, 1 warning, 12 errors`（`pytest_with_R1.txt`）。**passed の数は同じ、failed は 0**。
  - 12 errors はいずれも test_gemini_raw_copy_v102_soldout_ref.py の DB 付き試験で、原因は `AssertionError: Disposable CI service required … GITHUB_ACTIONS`（手元では DB を使う試験が走らない仕様。CI では走る）。R1 の有無と無関係。**この 12 件が R1 で緑のままかは手元では未確認 → CI で確認（K2）**。
  - 作業ツリーに変更が無いこと: `git status --short` が空（確認済み）。

### 3-2. 試算（Opus 提示・引用のみ。再実行はしていない）
`/tmp/CC報告ファイル/mark_exact_match_simulation.txt`（コード origin/main 165e316a7 時点、本番 ai_ro 読み取り）:
- v102 現行 1238行・原文 95通で、R1 により結果が変わった行 = 0。
- EB02-003 の取り違え: 424591 の mark を `EB02-003` に差し替えた想定で、現行は `ambiguous (57, 424591)`、R1 は `matched (424591,)`。他の4文は変化なし。
- 書かれ方の合成表（値 `OP-01`・`OP01`）: R1 で当たらなくなるのは `OP01-001`・`OP01-001 リーダー` の2形のみ。ほか（`OP01`・`OP-01`・`【OP-01】`・`ＯＰ－０１`・`OP-01 BOX`・`OP01-BOX`・`OP01×2` など）は現行と同じ。
- 本番原文での型番の書かれ方（360 出現）: 「後ろに -数字（カード番号）」は 3 出現（`[ST21-014]`・`[OP13-001]`・`OP13-001`）で、R1 で当たらなくなるが、**3 件とも行の結果は不変**。
- 起点コミットが 165e316a7 → 035b0145e と進んでいる。この間に extraction_judgement_svc.py の `_strict_code_pattern` 周辺が変わったかを確認: 下記コマンドの結果が空なら変更なし。
```
git log --oneline 165e316a7..035b0145e -- backend/app/services/extraction_judgement_svc.py
```
  実行結果は §6 に記載。

## 4. 既存の試験（実物）
`backend/tests/test_extraction_judgement_svc.py`
- `:167` `class TestMatchProductCode`（`test_matches_by_product_code` は product_code="OP-01"・原文 "OP-01 新品未開封 BOX" で当たる。strict_codes なし）
- `:662` `class TestMatchProductStrictCodes`（`_hits(text, products, **kwargs)` は `match_product(...).candidates` を返す。`:665-667`）
  - `:669` test_ex10_does_not_hit_inside_100_price
  - `:674` test_ex12_does_not_hit_across_line_break
  - `:680` test_sv7_does_not_hit_sv7a_but_sv7a_does
  - `:687` test_ard_does_not_hit_inside_card
  - `:693` test_rb01_does_not_hit_prb01_but_prb01_forms_do
  - `:700-704` test_hyphen_and_no_hyphen_both_hit_either_form（`EB-01`/`EB01` が `◆EB-01`・`EB01 メモリアル` に当たる。R1 でも成立）
  - `:706` test_apostrophe_variants_hit
  - `:710` test_acute_accent_separator_hits
  - ほか（`:715` kana・`:720` 短い値・`:726` SM5S・`:731` SM5+・`:736-748` 記号・`:750-772` 改行など・`:774` default_output_is_identical）
- `:785` `class TestExcludeKeywordsStrictCodes`、`:826` `class TestExcludeKeywordsLeftBoundary`
- `_product` ヘルパー: `:109-124`（引数 id_, product_code, mark, work_id, search_keywords, exclude_keywords）
- ファイル先頭の import: `:5-14`（`match_product` と `ProductEntry` などは import 済み。追加の import は不要）
- 追加位置: `:704`（`test_hyphen_and_no_hyphen_both_hit_either_form` の最後の行）の直後、`:706` `test_apostrophe_variants_hit` の前。
- 他の関連試験: `backend/tests/test_gemini_raw_copy_v102_name_only.py:76`（"OP-14 未開封" が strict_codes で当たる）、`backend/tests/test_gemini_raw_copy_v102_followup.py`・test_gemini_raw_copy_v102_soldout_ref.py（型番の語の探索）。R1 差し替えで赤は出ていない（§3-1）。

## 5. 呼び出し元ごとの「意図どおりか」の確認
| 呼び出し元 | 「型番-数字」を当てなくなることの是非 | 判定 |
|---|---|---|
| #3 mark・product_code（本命） | `EB-02` の商品が `EB02-003` の行（別商品のカード番号）に当たるのは取り違え。試算で変化 0 行 | 意図どおり（事実） |
| #4 検索ワード（型番らしいもの） | 同じ理由。検索ワードが型番だけ（例 `EB02`）の商品が、同型番のカード番号の行に当たらなくなる。試算（全体適用の R1）で変化 0 行 | 意図どおり（事実: 試算で不変。実害の有無は 0 行のため未観測） |
| #5 除外ワード（型番らしいもの） | 除外ワード `EB02` が `EB02-003` の行で効かなくなる（＝除外が外れる）。試算（全体適用の R1）で変化 0 行。ただし**除外が外れる方向の変化で、候補が増える可能性がある** | 試算 0 行のため実害は未観測。方向は注意（design.md の未決 U1） |
| #9 followup（`:56`・`:81`） | 型番の語（例 `op01`）を参照行（例 `op01-001 …`）で探す用途。R1 で「`op01` が `op01-001` の行に当たる」ことがなくなる。**全体適用の R1 の試算は `match_product` 系のみで、followup / soldout_ref の探索は試算していない（シミュレーション記録に該当の記載なし。grep で確認）** | **判断できない → 未決 U2（Opus 判断）** |
| #10 soldout_ref（`:190`） | 同上（参照行の探索） | **判断できない → 未決 U2** |

## 6. 起点コミットの差の確認
- `git cat-file -t 165e316a7` = commit。`git merge-base --is-ancestor 165e316a7 HEAD` の終了値は 0（祖先である）。
- `git log --oneline 165e316a7..035b0145e -- backend/app/services/extraction_judgement_svc.py` の出力は空（生出力: `/tmp/CC報告ファイル/mark_exact_match_design/git_log_since_sim.txt`、0 バイト）。試算時点から対象ファイルは変わっていない。試算の数値は現在の origin/main にも当てはまる（事実）。
- 本件の recon の基準コミット: 035b0145e。
