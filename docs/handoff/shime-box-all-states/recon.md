# recon: 状態を書かない箱の〆で、箱の仲間の別の状態の在庫が残る件

状態: 調査済み（Opus・2026-11-10）。根拠のコードは origin/main 96a63df05a23c0250e7a0550ca7399e1ddb4b01a。社外秘の原文・仕入元名・件ごとの記録はリポジトリに置かない（Mac の記録フォルダ `shime-auto-check/multistate/`）。

## 1. 既存 ADR の検索

- `git grep -i "soldout\|〆\|取り残し" docs/adr/` と `docs/adr/FEATURE-INDEX.md` で探した。関係するもの:
  - ADR-1023（状態の価値順。状態マスタの `value_group`・`value_rank`）
  - ADR-1031（区分ごとの状態の群）
  - ADR-1032（〆の後に古い在庫を生き返らせない）
  - ADR-1041（区分ごとの単位の表・状態の見出し。語と記号をコードに書かず設定 `tcg_distribution_settings` に持つ前例）
  - ADR-1007（値は記録した SQL で入れる）
- 〆の規則12（商品名を書いた〆が前の在庫の取り残された状態を引き継ぐ）は ADR ではなく設計書 `docs/handoff/v102-shime-*` 系で決められている。規則12の「状態が語で決まっていない件だけ」を変える ADR は無い。

## 2. 今の動き（コードの事実）

### 2-1 〆の件が完売にする相手の決め方

- 規則12の入口: `backend/app/services/gemini_raw_copy_v101.py:1502`（`_apply_soldout_inherit` を呼ぶ）、本体 `backend/app/services/gemini_raw_copy_v101.py:1310-1325`。決めた相手は 1 つだけ `soldout_targets` に入れ、印は `SOLDOUT_INHERIT`。
- 判定: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:407-437`（`decide_soldout_inherit`）。
  - 候補（`:367-375`）: 完売・商品が直接決まった・相手がまだ無い・人の判断でない・**状態が語で決まっていない**（`:373`）・行に単位語が無い（`:374`、規則12f）。
  - 12g（`:425-426`）: 取り残しが 2 種類以上で、最新の在庫の投稿の状態が 1 種類なら、その状態に決める。
  - 12d（`:427-428`）: 〆と同じ状態の在庫が前の投稿にあれば決めない。
  - 12e（`:429-430`）: 取り残しがちょうど 1 種類のときだけ決める。
  - 取り残し（`:378-395`、`_stranded_stock`）: 状態ごとに最も新しい投稿を見て、そこが在庫なら取り残し。同じ投稿の同じ商品の他の件の状態は除く。
- 「語で決まったか」の判定: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:45-52`。`R4:単位既定`・`R5:パック既定` は語でない（`:42`）。`R\d+:` で始まる理由は語（`:41`）。
- 結果、状態を書かない「商品名＋〆」は、〆の状態（単位の既定＝Sealed box）の在庫が前にあると 12d で何もしない。Sealed box だけが完売になり、シュリンクなし等の在庫は残る。

### 2-2 相手が 2 つ以上のときの書き方（既にある仕組み）

- 先頭の相手で〆の件の状態を上書き: `backend/app/services/line_analysis_v102_svc.py:941-964`（`_apply_soldout_targets`）。
- 2 つ目以降の相手は `analysis_soldout_extra_targets` に書く: `backend/app/services/line_analysis_v102_svc.py:966-975`（`_extra_targets`）、`:1213`（書く所）。
- 在庫表の「今の行」の決め直しは、この表の相手も最新の投稿として数える: `backend/app/services/tcg_analyzer_svc.py:2044-2140`（仮の行 `:2089-2101`）。→ 相手を増やすだけで、その状態の古い在庫は今の行でなくなる。DB の形は変えなくてよい。

### 2-3 箱の仲間の状態

- 状態マスタの `value_group='box'` が箱の仲間（ADR-1023）。記録 SQL `docs/handoff/condition-value-rank/data/value_rank_commit.sql:11-15`: CN0003 Sealed box(1)・CN0004 Damaged sealed box(2)・CN0005 No shrink box(3)・CN0006 Opened box(4)・CN20261008072213(5)。
- 【未確認】本番の今の値。読み取り専用の鍵では `public.conditions`・`public.line_conditions` を読めない（2026-11-10 InsufficientPrivilege）。v102 は `load_condition_entries` で `value_group` を読む（`backend/app/services/tcg_analyzer_svc.py:698-708`）ので、実装では本番の表の値を使う。
- 【未確認】CN20261008072213 の名前。

### 2-4 設定の前例

- `backend/app/services/gemini_raw_copy_v102_product_first.py:172-174`: 設定の key を定数で持ち、値（JSON）を純粋関数で検査（`:410`・`:456`）。key が無いと働かない。
- やり直しの道具は設定を JSON ファイルで差し込める: `backend/app/tools/v102_replay_diff.py:182`（`--heading-setting`）。
- 語の試しで使った道具（`scripts/accuracy/condition_words/`）は試しのブランチ `release/condition-abbr-trial` にだけあり、origin/main には無い（`git ls-tree origin/main` で 0 件）。
- 状態の `value_group`・`value_rank` は `public.conditions` から読む（`backend/app/services/tcg_analyzer_svc.py:695-712`）。

## 3. 数（社外秘の記録から、数だけ）

- 2026-09-01〜11-09 の〆の行のうち、状態を書かない〆で前の投稿に別の状態の在庫が残る形で、原文で正解を決められた 21 件（全部の意味 14・特定の状態だけ 7）。
- 案ごとの当て（Opus の原文判定。PO の目視は未）:

| 案 | 直る | 壊す | 直らない |
|---|---|---|---|
| 1 全部消す | 14 | 7 | 0 |
| 1b 残りが箱の仲間だけのとき消す | 13 | 3 | 1 |
| 1c 1b＋略語を状態の語に | 13 | 1 | 1 |
| 1d 1c＋同じ投稿に在庫が残っていると書いてあれば消さない | 13 | 0 | 1 |

- 21 件の中に Opened box が残る形は 0 件（Opened box を含めた動きは未測定）。

## 4. 語の試し（2026-11-09・本番を変えず 134 投稿）

- 5 つの語（シュリあり／シュリンク有り／シュリンク有／有〆／有り〆）を記憶の中で CN0003 に足すと、状態の値・〆の相手・在庫は 1 件も変わらず、状態の理由だけ 176 件変わった（「単位既定」→語）。
- 例 9「商品名＋有〆」型は理由が `R4:有〆` になり「語で決まった」になる。今の規則12では候補外になるが、もともと 12d で何もしないので結果は同じ。
