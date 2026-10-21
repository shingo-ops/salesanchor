# 実装カード: ADR-1031 シングル系の状態5つ と プロモパック系（v102）

発行 2026-10-19 Opus（PO の委任に基づく）。設計は [design.md](./design.md)（PO 承認済み 2026-10-19「y」）、判断は [ADR-1031](../../adr/ADR-1031-single-and-promo-pack-conditions.md)、現状は [recon.md](./recon.md)。
作業場所: `/Users/tanizawashingo/worktrees/salesanchor/release-single-promo-pack-conditions-design`（ブランチ `release/single-promo-pack-conditions-design`）。この中だけで作業する。

## 触る範囲

| # | ファイル | 中身 |
|---|---|---|
| C1 | `backend/app/services/tcg_analyzer_svc.py` `load_condition_entries`（:652-769） | 引数 `include_scoped_groups: bool = False` を足す。False のとき value_group が `single`・`promo_pack` の行を返さない。既定の呼び出し元は一切変えない |
| C2 | `backend/app/services/line_analysis_v102_svc.py` `load_v102_masters`（:201-217、呼び出し :206） | `include_scoped_groups=True` を渡す。v102 の中で群の行を `single` / `promo_pack` / それ以外に分けて持つ |
| C3 | `backend/app/services/gemini_raw_copy_v102_product_first.py` 定数（:46-50） | `PRODUCT_KUBUN_SINGLE = "シングル系"`、`PRODUCT_KUBUN_PROMO_PACK = "プロモパック系"`、既定の状態名 `"Single"`・`"未開封"`、basis `"R7:単品既定"`・`"R8:プロモパック既定"` |
| C4 | 同 `_resolve_condition`（:570-589） | 商品の kubun_type が シングル系 → `single` 群の行だけで `resolve_condition_v2(..., kubun="シングル系", prefer_lowest_value=True)`。結果が FLAG_SINGLE＋単位不明（＝語が当たらない）なら状態 Single・basis R7。プロモパック系 → `promo_pack` 群の行だけで判定し、当たらなければ 未開封・basis R8、2行以上当たったら既存の `REVIEW_MULTIPLE_CANDIDATES` を付ける。それ以外の区分は今と同じコード経路（1文字も挙動を変えない） |
| C5 | 同 `_other_kubun_hits`（:592-604） | `single`・`promo_pack` 群の行を対象にしない |
| C6 | `backend/app/services/line_analysis_v102_svc.py` `_condition_columns`（:630-641） | 状態名から code を引くとき、群の中で引く。「PSA10」は single と promo_pack の2行あるので、シングル系の結果は single 群の行、プロモパック系の結果は promo_pack 群の行の code になること。やり方は実物を読んで選び、報告に書く（例: _resolve_condition が群を返す・entry を直接返す）。群の行が DB に無いときは今と同じく FLAG_SINGLE に落ちてよい |
| C7 | `backend/app/services/tcg_result_order.py:11` | `VALUE_GROUP_ORDER = ("case","box","pack","promo_pack","single")` |
| C8 | migration 1本（既存の命名・形に合わせる） | `line_conditions_value_group_check` を作り直し、許す値に `promo_pack`・`single` を足す。データは入れない。downgrade は元の box/case/pack に戻す |
| C9 | テスト（既存の v102 / analyzer のテストの置き場所に合わせる） | 下の T1〜T8 |
| C10 | `docs/handoff/single-promo-pack-conditions/data/` | 記録 SQL（下の S1〜S5）。本番には流さない（流すのは Opus） |

v101 の `_state_words` は、C1 の既定 False で新しい行が渡らないので変更不要。実物で渡らないことを確かめて報告に書く。

## 触らない範囲

- v6・v10・v101・shadow・単位の復元・GAS・フロント（色を含む）・`condition_vocab.py`・`inventory_aggregation.py`。
- 既存の状態の行（CN0008 を含む 16 行）・箱系/セット系/バルク系/区分なしの判定経路。
- `deploy.yml`・本番 `scripts/`・secrets。

## 値（S1 で入れる 8 行。app_kubun は「シングル系」または「プロモパック系」）

PSA の正規表現（N は 10/9/8、7以下は `[1-7１-７]`。10 は `(10|１０)`、9 は `(9|９)`、8 は `(8|８)`）:
`(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?N(?![0-9０-９])`

| 群 | canonical | app_kubun | match_type | 語 | value_rank | effect |
|---|---|---|---|---|---|---|
| single | PSA10 | シングル系 | REGEX | PSA10 の式 | 1 | OUTPUT |
| single | PSA9 | シングル系 | REGEX | PSA9 の式 | 2 | OUTPUT |
| single | PSA8 | シングル系 | REGEX | PSA8 の式 | 3 | OUTPUT |
| single | PSA7以下 | シングル系 | REGEX | PSA1〜7 の式 | 4 | OUTPUT |
| single | Single | シングル系 | KEYWORD | search_kw 空（CN0014 Bulk と同じ形） | 5 | OUTPUT |
| promo_pack | 未開封 | プロモパック系 | KEYWORD | search_kw 空 | 1 | OUTPUT |
| promo_pack | 開封済み | プロモパック系 | REGEX | `(?<!未)開封(?!前\|していない\|なし\|不可)` | 2 | OUTPUT |
| promo_pack | PSA10 | プロモパック系 | REGEX | PSA10 の式 | 3 | OUTPUT |

列名・code の採番・その他の必須列は、本番の実物（AI 用読み取り専用の道 ADR-1024: `ssh -F /dev/null -i ~/.ssh/salesanchor-reader ...`。無制限鍵は使わない）と CN0014 の行に合わせる。code は無効行も含めた最大値の次から連番。

## 記録 SQL（C10。全部1つのトランザクション、件数を assert して違えば ROLLBACK）

- S1 `01_precheck.sql`: 新しい code が未使用・canonical「Single」「未開封」「開封済み」「PSA9」「PSA8」「PSA7以下」が既存に無い・区分「プロモパック系」が無い・3 商品（440525・466083・466077）の今の区分が 2、を数える。
- S2 `02_apply.sql`: 8 行の INSERT、区分「プロモパック系」の INSERT（前例: バルク系 id 9 の作成。列は実物の tcg_product_categories に合わせる。kubun_type は「プロモパック系」）、3 商品の区分の UPDATE（WHERE id と今の区分 2 の両方。更新 3 行を assert）。DRY-RUN 用に末尾 ROLLBACK 版と COMMIT 版の2つを置くか、変数で切り替える。
- S3 `03_verify.sql`: 8 行・1 区分・3 商品が期待どおりかを数える。
- S4 `04_rollback.sql`: 8 行を is_active=false、3 商品を区分 2 に戻す（区分の行は残す）。
- S5 `README.md`: 流す順番（コード反映 → S1 → S2 → S3 → 再解析）と、それぞれの期待件数。

## テスト

- T1 シングル系の商品で「PSA10」「psa10ar」「ＰＳＡ１０」「PSA 10」→ PSA10。
- T2 「PSA9」→PSA9、「PSA8」→PSA8、「PSA7」「PSA1」→PSA7以下、「PSA100」は PSA10 に当たらない。
- T3 シングル系で語なし → Single・basis「R7:単品既定」（R4 で始まらない）。
- T4 プロモパック系で語なし → 未開封・basis「R8:プロモパック既定」。
- T5 プロモパック系で「開封済み」→開封済み、「PSA10」→PSA10。
- T6 プロモパック系で「未開封」「開封前」「新品未開封」「開封していない」「開封なし」→ 開封済みにならない（＝未開封）。
- T7 プロモパック系で「開封済み PSA10」→ 要確認（REVIEW_MULTIPLE_CANDIDATES）が付く。
- T8 `load_condition_entries()` を引数なしで呼ぶと single/promo_pack 群の行が返らない。箱系の商品の判定結果が群の行を足す前後で同じ。
- 既存テスト（v6・v10・v101・v102・analyzer）を全部流して通ること。

## 手順

1. `./scripts/dev/executor-preflight.sh || exit 1`、`docs/ai-agents/executor-checklist.md` に従う。
2. C1〜C10 を実装、テストをローカルで流す（backend の既存の流し方に合わせる）。生出力は `/tmp/CC報告ファイル/adr1031/` に保存。
3. commit（`feat:` 1本でよい。recon/design/card は既にコミット済み）→ push → `gh auth status` で shingo-cc を確かめ、`gh pr create --base main --draft`。
4. PR 本文: 概要、`### 標準ワークフロー確認`（recon/design/ADR-1031 のパス）、触ったファイルの全列挙（`git diff origin/main...HEAD --name-only`）、migration を含む＝危険パスであること、テスト結果、記録 SQL は本番未適用であること。

## 停止条件（迷ったら止めて報告）

- 設計にない挙動の変更が必要になった・既存テストが落ちて原因が本件のコードでない・本番の列が設計と合わない・C6 の引き当てが群の中でできない。
- 報告は DONE / BLOCKED: / NEEDS_DECISION: で始め、PR URL・HEAD・テストの生出力のパス・C6 で選んだ方法・`_state_words` の確認結果を書く。
