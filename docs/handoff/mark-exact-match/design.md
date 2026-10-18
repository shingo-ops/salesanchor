# design: 型番の照合で「型番の後ろに -数字 が続くとき」は当てない（案R1）

- 関連ADR: ADR-1006-product-code-pm5-and-mark-only-matching（ADR-1006。照合は mark だけで行う。本件はその**境界の作り方**であり、方針は変えない）、ADR-135・ADR-136（本番投入前のGO）。ADR の新規起案は不要（recon.md §1 結論）
- recon: docs/handoff/mark-exact-match/recon.md
- 先行設計（同じ共有関数の境界の調整）: docs/handoff/line-match-price-digit-boundary/design.md
- 設計仕様書（あるべき姿）: docs/specs/line-analysis-tuning/README.md（既存の延長・修正。STANDARD-WORKFLOW §1.8）
- 状態: 設計案作成済み・設計審査済み（Opus APPROVE、§12）・PO 決定済み（2026-10-18、Opus が提示した案R1への PO 原文「y」）

## 1. 目的（KGI）
商品マスタの型番（mark・product_code・型番らしい検索ワード・除外ワード）が、原文の別商品のカード番号（例 `EB02-003`）の先頭部分に当たって、別の商品に決まらない・候補が増えないようにする。
- 画面・出力で○×を判定できる形: 原文「EB02-003 …」の行が、型番 `EB-02` の商品（BOX）でなく、`EB02-003` を mark に持つ商品（カード）だけに決まる（K4）。
- 同時に、今まで正しく決まっていた行の結果を変えない（K3: v102 現行 1238行で変化 0）。

## 2. 方式（案R1）
`_strict_code_pattern` が作る正規表現の**右端**に否定先読み `(?![ハイフン類][0-9])` を1つ足す。型番の直後が「ハイフン類＋数字」なら当たらない。左側と、直後が他の文字のときは今のまま。

- ハイフン類は同ファイルの区切り文字の集合（extraction_judgement_svc.py:155-157 の `_CODE_SEPARATOR_CHARS`）に含まれるハイフン8種に合わせる: ASCII `-`、U+2010、U+2011、U+2013、U+2014、U+2015、U+2212、U+30FC（ー）。
  - 試算（recon §3-2）で使った集合は、上に U+2012 を加えた9種。U+2012 は同ファイルの集合に無いので本設計では入れない（同ファイルの扱いに揃える。U+2012 を原文に含む例は本番の写し・合成表のどちらにも無い、とは確認していない → 未確認。差は1文字であり、K3 の再計算で検出できる）。
- 「正規化後の文字に効くか」: 先読みは `fold_for_match` 済みの `folded` に適用される（`:208` `pattern.search(folded)`）。NFKC により全角 `－`（U+FF0D）・全角数字は半角になる。`ＯＰ－０１` が当たること、`OP01−001`（U+2212）・`OP01‐001`（U+2010）・`OP01ー001`（U+30FC）が当たらないことを実行で確認（recon §3-1、`/tmp/CC報告ファイル/mark_exact_match_design/r1_check_out.txt`）。
- 値の内側の区切りの許容（`OP-01` ↔ `OP01` ↔ `OP 01`）は変わらない。隙間の正規表現は文字の間にだけあり、末尾には無いため（recon §2-2）。

### 2-1. 変更前後のコード

**(a) 定数の追加**（`backend/app/services/extraction_judgement_svc.py`、`:158` の `_CODE_SEPARATOR_RE = …` の直後に空行なしで2行足す）

変更前（`:155-158`）:
```python
_CODE_SEPARATOR_CHARS = (
    " 　-‐‑–—―ー−・_.'’‘´́`"
)
_CODE_SEPARATOR_RE = "[" + "".join(re.escape(ch) for ch in _CODE_SEPARATOR_CHARS) + "]*"
```
変更後（`:158` の次に2行追加）:
```python
_CODE_SEPARATOR_CHARS = (
    " 　-‐‑–—―ー−・_.'’‘´́`"
)
_CODE_SEPARATOR_RE = "[" + "".join(re.escape(ch) for ch in _CODE_SEPARATOR_CHARS) + "]*"
# 型番の直後が「ハイフン類＋数字」（例 EB02-003 の -003＝カード番号）のときは、その型番には当てない。
_CODE_HYPHEN_CHARS = "-‐‑–—―−ー"
_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE = "(?![" + "".join(re.escape(ch) for ch in _CODE_HYPHEN_CHARS) + "][0-9])"
```

**(b) 正規表現の組み立て**（同ファイル、組み立て行。変更前 `:197`）

変更前:
```python
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])")
```
変更後（定数追加で行番号が2つ下がり `:199`）:
```python
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])" + _CODE_NOT_BEFORE_HYPHEN_DIGIT_RE)
```

**(c) docstring に1行**（`_strict_code_pattern` の docstring 末尾、`値の中で記号があった隙間だけ…` の段落の後）
```
    値の直後が「ハイフン類＋数字」（カード番号の形。例 EB02-003）のときは当たらない（_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE）。
```

### 2-2. 手元実装との対応
手元実装 scratchpad/mx/variants.py の R1 は `p.pattern + r"(?![" + HY + r"]\d)"` を再コンパイルする形。本設計は同じ式を組み立て時に直接入れる（等価）。差は ①U+2012 を入れない ②`\d` でなく `[0-9]`（`folded` は NFKC 後で全角数字は半角化されるため実質同じ。ASCII 以外の数字に反応しない分だけ厳密）。

## 3. 範囲
- 入れる: 上の定数2行・組み立て1行・docstring 1行（`backend/app/services/extraction_judgement_svc.py`）、`TestMatchProductStrictCodes` への試験の追加（`backend/tests/test_extraction_judgement_svc.py`）。
- 触らない: `_strict_code_hits`（`:201-209`）・`_value_hits`・`_code_candidate_basis`・`_keyword_matches`・`_exclude_hit`・`match_product`、`has_word_boundary`、followup / soldout_ref / gap_lines / product_first の各ファイル（`_strict_code_pattern` を直接 import しているため自動で追従する。名前の差し替えは不要）、v6 の tcg_analyzer_svc.py の `match_keyword` 系、登録時の衝突検知 tcg_product_code_collision_svc.py、frontend、マスタ、`migrations/`・`.github/workflows/`・`scripts/`。
- 本変更は危険パス（`migrations/`・deploy.yml・本番 `scripts/`）を含まない。ただし `backend/app/services/` はユーザーに影響する変更に当たり、本番反映前の GO 記録が要る（STANDARD-WORKFLOW「完了の定義」）。
- 再解析（既存行の取り直し）は本設計の範囲外。必要なら反映後に別途（K3/K4）。

## 4. 代替案と選んだ理由（試算: `/tmp/CC報告ファイル/mark_exact_match_simulation.txt`）
| 案 | 内容 | 採否 | 理由 |
|---|---|---|---|
| R1 | 型番の右が「ハイフン類＋数字」なら当たらない | **採用** | 変化 0 行（1238行）。実装は1行の正規表現。EB02-003 の取り違えが ambiguous → matched 424591 に直る。当たらなくなる書き方は「OP01-001」型のカード番号だけ |
| R2 | 前後が英数字**または**ハイフン類のとき当たらない | 不採用 | 装飾のハイフンに隣接する語（`-ONE PIECE DAY24-` 等）で 5 行が matched → unmatched に外れる |
| R3 | 原文から型番の塊を切り出し完全一致 | 不採用 | 変化 0 行だが実装が複雑。数字を含まない語（MEGA・VSTAR）の例外処理が要る（最初の版はそれを現行から外し 97 行が変わる欠陥があった） |
| mark・product_code だけに限る（R1m） | 検索ワード・除外ワードは現行のまま | 不採用 | 試算で R1 と R1m はどちらも変化 0。コードでも mark だけ直すには `_code_candidate_basis` の分岐が増える。全体に効く R1 の方が1か所で済み、検索ワード・除外ワードに残る同じ取り違えも防ぐ |

## 5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 単体テスト追加: 「EB-02」が「EB02-003」に当たらない／「OP-01」が OP01・OP-01・【OP-01】・OP01×2・ＯＰ－０１・OP-01 BOX・OP01-BOX に当たる／「OP01-001」に当たらない | `backend/tests/test_extraction_judgement_svc.py` の `TestMatchProductStrictCodes` に追加（card-implement.md §4-3）。手元で、現行コードでは追加試験 8 件が落ち（赤）、案R1 では 17 件全て緑になることを確認済み（`/tmp/CC報告ファイル/mark_exact_match_design/draft_tests_result.txt`） |
| K2 既存テスト全緑 | `cd backend && python -m pytest tests -q`（CI の backend テスト）。手元では DB を使う 12 件が走らない（GITHUB_ACTIONS 必須）ので、全緑の判定は CI の必須チェックで行う。手元の 10 ファイル 1154 件は R1 差し替えで現行と同じ結果（recon §3-1） |
| K3 本番反映後、v102 現行行の再計算で変化 0 件、または変化した行を全部列挙して PO が確認 | scratchpad/mx/run.py 相当（原文→行ブロック→`product_match_text`→`match_product_g2`）を反映後のコードで流し、反映前の結果（res_base.json）と全行比較。Opus が実行して結果ファイルを残す。変化があれば行 ID・現行→新の status・候補を全件列挙 |
| K4 本番反映後、原文「EB02-003」を含む想定文が 424591 単独になる（チョッパーズのマスタ登録が済んでいることが前提。未済なら `EB-02` が当たらないことだけ確認） | K3 と同じ手順で、想定文 `EB02-003 / 20個@1000` を通して候補が 424591 のみ。マスタ未登録なら `EB-02` の商品（57）が候補に出ないことだけを確認。前提の登録状況は反映時に Opus が本番の読み取りで確認 |
| K5 デプロイの4観測（デプロイされた・実行された時刻・結果の形・指標） | ①デプロイされたか: 反映後の deploy.yml 実行が success で、本番の backend コンテナのコミット（または配信物）が本 PR のマージコミットに一致 ②実行されたか: 反映後に解析が走った時刻（v102 の `analysis_results` の更新時刻が反映時刻より後の行がある）③結果が期待の形か: K4 の想定文の結果 ④指標が変わったか: K3 の変化行数（0 が期待）と `ambiguous` の件数（EB02-003 の行が 424591 に決まる以外は不変）。台本は Opus が書き PO が `!` で実行 |

## 6. 外部・過去事例の参照と我々への応用
- 該当なし。理由: 変更は「型番のカード番号を型番本体に当てない」という自前のマスタ・自前の原文に固有の境界条件1つで、外部の実装を取り込む対象ではない（先読みで直後を除外する書き方は正規表現の標準的な使い方）。
- 過去事例（社内）: 同じ共有関数の境界の調整は `docs/handoff/line-match-price-digit-boundary/design.md`（数字だけの値は金額の一部に当てない）が先例。進め方（共有関数1か所を直す→全経路に同じく効く→試算で変化行を数える→追加試験で固定）を踏襲した。
- 成功の根拠は自前の写しでの試算（K3 の元になった 1238行・変化 0）に置く。

## 7. 弊害と対処（リスク）
| リスク | 内容 | 対処 |
|---|---|---|
| 1 カード番号だけの行 | 原文に `OP01-001`（カード番号）しか無い行は、型番 `OP-01` の商品（BOX）に当たらなくなる。これは狙い（カードをBOXに決めない）。ただし**カードのマスタが無い**と、その行は unmatched になる | 試算（本番出現 3 件）で行の結果は不変。反映後 K3 で全行を再計算し、変化行を全件列挙 |
| 2 除外ワードが外れる | 型番らしい除外ワード（例 `EB02`）が `EB02-003` の行で効かなくなり、候補が増える可能性（recon §5 #5） | 試算で変化 0。K3 の変化行の列挙で見る。U1 参照 |
| 3 followup / soldout_ref の探索 | 参照行の探索で `op01` が `op01-001` の行に当たらなくなる（recon §5 #9・#10）。試算していない | U2（Opus 判断）。反映後 K3 に followup / soldout_ref の再計算も含めるかを決める |
| 4 ー（U+30FC）の副作用 | 長音記号 `ー` + 数字が直後に続く型番（例 `OP01ー2`）も「カード番号の形」と見なして当たらなくなる | 同ファイルの区切り文字の集合に ー が既に含まれ、`OP01ー001` の形を当てない方が一貫するため含める。試算 1238 行で変化 0。実害が出たら集合から外す（1 行の変更） |
| 5 lru_cache | `_strict_code_pattern` はキャッシュされる。デプロイでプロセスは入れ替わるため古いパターンは残らない | 対処不要（再起動でキャッシュは消える） |

## 8. 戻し方
本 PR を revert する（定数 2 行・組み立て 1 行・docstring 1 行・追加試験）。DB の変更なし。再解析で結果が変わった行は、revert 後にもう一度再解析すれば戻る。

## 9. 測り方
- 反映前の基準値: v102 現行 1238行の結果（scratchpad/mx/res_base.json、matched 1139 / unmatched 88 / ambiguous 11）。コミット差の確認で、試算時点（165e316a7）から対象ファイルに変更なし（recon §6）。反映時点で再取得して基準値を取り直すかは Opus が決める。
- 反映後: K3（変化行数・0 が期待）・K4（想定文が 424591 単独）。

## 10. 維持の仕組み
- 守り手: `backend/tests/test_extraction_judgement_svc.py` の追加試験（K1）が、CI の backend テストで毎回、「`EB-02` が `EB02-003` に当たらない」「`OP-01` の各書き方に当たる」「`OP01-001` に当たらない」を固定する。回帰すれば CI が赤になる。
- 対象: 型番の照合が、別商品のカード番号に当たる取り違え。

## 11. 未決事項（Opus 判断）
| # | 内容 | 設計側の暫定案 |
|---|---|---|
| U1 | 型番らしい除外ワードが `EB02-003` の行で効かなくなる（除外が外れる方向）ことの是非。試算 0 行なので実害は未観測 | 全体に効かせる（案R1）のまま進め、K3 の変化行の列挙で見る。問題が出たら除外ワードだけ現行に戻す分岐を別便で設計 |
| U2 | followup（`gemini_raw_copy_v102_followup.py:56,:81`）・soldout_ref（gemini_raw_copy_v102_soldout_ref.py:190）の参照行探索で「型番がカード番号付きの行に当たらなくなる」ことの是非。この2経路は試算していない | 判断材料が無い。Opus が ①そのまま追従（暫定）か ②この2経路だけ現行の当て方（先読みなし）に戻す（`_strict_code_pattern` の引数で切替）かを決める。②にする場合は設計・カードを改訂 |
| U3 | 照合規則の変更に ADR が必要かの線引きが文書化されていない（先例は handoff 設計のみ） | 本件は ADR 不要で進める。線引きの文書化は本件の範囲外 |
| U4 | U+2012 を含めるか（試算は含む9種、本設計は同ファイルに揃えて8種） | 8種のまま。K3 で差が出たら追加（1文字） |

### 11-1. 決定（Opus、2026-10-18）
- U1: 暫定案のまま全体に効かせる。理由: R1 の後は `EB02-003` の行が `EB-02` の商品に当たらなくなるので、その行で `EB02` を除外する必要もなくなる（除外が外れても候補は増えない）。照合と除外を同じ規則にそろえる。K3 の変化行で確かめる。
- U2: ①そのまま追従させる。理由: 本照合が「カード番号はBOXに当てない」なのに参照行の探索だけ当てると、同じ行が経路によって別の商品に結び付き、食い違いが出る。規則は1か所にそろえる。②（引数で切り替える）は分岐が増えるので採らない。実害が出たら別便で設計する。反映後の観測は K3 の再計算（本照合）で行い、followup・soldout_ref 経路の再計算は範囲外とする（未試算であることを PR 本文に書く）。
- U3: ADR は起こさない。ADR-1006 の方針（mark だけで照合する）は変えず、境界1つの調整だから。先例 line-match-price-digit-boundary と同じ扱いにする。
- U4: 8種のまま（同じファイルの区切り文字の集合にそろえる）。

## 12. 審査（Opus 記入欄）
- 判定: APPROVE（同一AIによる自己審査。第二者レビューではない）
- 根拠: ①変更の正本 §2-1 は変更前後のコードと場所（前後の一致）で決まっていて、実装の余地がない。②試算では 1238行の変化が0。追加試験は現行で 8件が赤、R1 で 17件全て緑（recon §3）。③受け入れ基準 K1〜K5 は全て、表の検証方法で○×を判定できる。④範囲の外（followup/soldout_ref/v6/migrations 等）を明記した。⑤戻し方は revert だけで済み、DB の変更はない。未決 U1〜U4 は 11-1 で決めた。
