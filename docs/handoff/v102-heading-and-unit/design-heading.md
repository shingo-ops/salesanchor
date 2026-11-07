---
mode: handoff
---
# design: 状態の見出しを、その下の品目に使う（v102・ADR-1041 便2 の改訂）

> この文書は何か：仕入元が見出しの行に状態（「未サーチ品」「傷あり」など）を書き、その下に品目を並べた投稿で、下の品目にその状態を付ける作り方です。D2（[design.md](./design.md) の便2）を置き換えます。

親: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)

状態: 設計案作成済み・設計審査済み（第3版〜第4.7版。クラウドの審査役 model opus。同じ製品の AI による自己審査で、人の第二者レビューではない。下の「審査」）。PO 承認: 方針「1」（2026-11-07。〆の失敗の回帰分析の結果、見出しの直しを先にする）と実装の承認「１」（2026-11-07）。**本番の切り替え（設定の行を入れる）は、PO の「切り替える」の返事の後**。実装は未着手（実装カード [card-H.md](./card-H.md)）。
- 決定の記録: [ADR-1041](../../adr/ADR-1041-kubun-allowed-units-and-condition-heading.md) What 5（この PR で直す）
- 試算の生出力・原文つきの表・審査の全文は社外秘フォルダ `~/CC報告ファイル-keep/shime-auto-check/heading-fix/unsearched-heading/`。この文書には件数・状態の名前・コードの位置だけを書く。投稿の原文・仕入元の名前は書かない。
- 行番号の基準: origin/main `37fa04f7b`（2026-11-07 fetch）。`170ff9612..37fa04f7b` で `gemini_raw_copy_v101.py`・`gemini_raw_copy_v102_product_first.py`・`line_analysis_v102_svc.py`・ADR-1041 の差は 0（審査役が `git diff --stat` で確認）。

## 目的（PO の言葉と、利用者に見える変化）

> 1（〆の失敗の回帰分析の結果、見出しの直しを先に。2026-11-07）

> １（作り始める。本番に出す前にもう一度報告する。2026-11-07）

- 今: 見出しに未サーチと書き、その下に空行で区切って品目を並べた投稿で、下の品目が「サーチ済みのパック」（いつもの値）として在庫表に並ぶ。未サーチは値打ちが高いので、仕入れの判断を誤らせる。毎朝の〆点検で 10/22・10/25・11/2・11/7 の 4 回、同じ形で再発した。〆の失敗 10 行のうち 4 行がこの型。
- 後: 品目の行に状態の語が無く、状態がいつもの値で決まった品目だけ、すぐ上の見出しの塊に状態マスタの語があり、いつもの値と同じ群の状態なら、その状態を付ける。

## 原因（コードの事実）

- 解析 AI の返事は件ごとに行の番号・値段・数量だけで、状態は返さない。状態はコードが件の行の文字だけを見て決める（`backend/app/services/gemini_raw_copy_v101.py:929` → `backend/app/services/gemini_raw_copy_v102_product_first.py:825` → `tcg_analyzer_svc.py` の `resolve_condition_v2`）。
- 見出しの行は件の行に入らないので、状態の語が見えない。語が無いパックは `R5:パック既定`（Searched pack）、箱は `R4:単位既定`（Sealed box）になる。
- 指示文で見出しの行を件に入れる形（f_dm）は、空行 1 つまでの形だけ扱い、件ごとに空行がある形は届かない。指示文で見出しを足す案は 10/22 の試算で正答率を下げた。

## KGI と KPI

| 区分 | 内容 | 測り方 |
|---|---|---|
| KGI | 見出しの下の品目の状態の誤り: 直近 30 日の試算で、変わる 42 件が全部正しく、誤り 0 のまま本番に入る | K2-2・K9 |
| KPI | K0〜K5（下の受入条件）がすべて合格 | 受入条件の表 |

## 対象と対象外

- 対象: v102 の流れ（`_extract_one` で `v102=True`・`product_first` が None でない・`status_context` が None でない）で、件の状態がいつもの値で決まった件だけ。式: `not condition_decided_by_word(basis) and basis.endswith(("R4:単位既定", "R5:パック既定"))`（`condition_decided_by_word` は `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:46-52` を import）。末尾一致なので `R4:単位既定:単位不明`・`R4:<語>`（R4a）・群の既定・売り切れの引き継ぎは対象にならない。
- 対象外: 件の行に状態の語がある件（今のまま）。件より下の注記。値段から状態を推す決まり。売り切れの引き継ぎ。指示文。DB の形。v10.2 以前の流れ（`product_first is None` の枝）。

## 決め方（変更後）

### H1. 見出しの塊（純粋な関数 `_heading_block`・`gemini_raw_copy_v101.py` に新設）

件の最初の行（`min(item["lines"])`。行番号は 1 始まり、文字は `lines[n - 1]`）の 1 つ上から上へたどる。
1. 空行と、どれかの件の行（`status_context.owned_lines`。採った件と落とした件の lines の和。`backend/app/services/v102_status_context.py:41`、作るのは `gemini_raw_copy_v101.py:1364`、渡すのは :1399）は飛ばす。
2. 最初に当たった「件に入っていない・空でない行」から、上へ続く行を最大 `rule.max_lines` 行集める。空行・件の行に当たったら止める。
3. （c）集めた行に値段の形の行が 1 つでもあれば None。値段の形は既存の `_is_price_shaped`（`gemini_raw_copy_v101.py:986`。:1003 の値段の見落としの判定と同じ定義）を使う。
4. （b）集める手を止めた行が「空でない・件の行」なら None（別の件にくっついた言い分けの行）。
5. （a）文で終わる行を除く（`rule.sentence_end_re`。お店の方針・断り書き・お願いの文）。
6. 残った行を上から下の順に改行でつないだ文字と、残った行の最も小さい行番号を返す。残りが無ければ None。

正本のコード（実装はこれと同じ動きにする。文字の正規化はしない。`str.strip()` は全角の空白も除く。語・記号はコードに書かない）:

```python
def _heading_block(lines, first_line, owned, rule):
    n = first_line - 1
    while n >= 1 and (not lines[n - 1].strip() or n in owned):   # 1. 空行と件の行を飛ばす
        n -= 1
    got = []
    while n >= 1 and len(got) < rule.max_lines and lines[n - 1].strip() and n not in owned:   # 2.
        got.append(n); n -= 1
    if any(_is_price_shaped(lines[g - 1]) for g in got):          # c
        return None
    if n >= 1 and lines[n - 1].strip() and n in owned:            # b
        return None
    got = [g for g in sorted(got) if not rule.sentence_end_re.search(lines[g - 1].strip())]   # a
    if not got:
        return None
    return "\n".join(lines[g - 1] for g in got), min(got)
```

| 集める手が止まった理由 | 返り値 |
|---|---|
| 空行に当たった | a へ進む |
| 空でない件の行に当たった | None（b） |
| `max_lines` 行集めた | 次の行が空でない件の行なら None（b）。それ以外は a へ |
| 投稿の先頭に達した | a へ進む |
| 1 行も集まらなかった | None |

- 既存のステータス用の見出し探し（`v102_status_context.py:109` `_heading`）は投稿の先頭までたどる。状態の語は件の行の中にも普通に書かれ、遠い見出しまでたどると別の区分の注記を拾うので、状態では「最も近い、件に入っていない行の塊」だけを見る。
- 知っている限界: 絵文字で終わる文は a で除けない。採るのは R2・R3 の語だけで群の一致も要るので、30 日の試算でこの形の誤りは 0。毎朝の〆点検で見る。

### H2. 状態の決め直し（`_heading_condition`・`gemini_raw_copy_v101.py` に新設）

- 対象の件で、見出しの塊の文字を `_resolve_condition(heading_text, product_first["product_category"], product_first["unit_kubun"], ctx.cond_entries, ctx.cond_canonical_to_uuid, ctx.product_first.scoped_cond_entries)` に通す（`gemini_raw_copy_v102_product_first.py:676`。:825 と同じ引数の並び。単位の区分は単位を直した後の値＝画面に出る単位に合わせる）。3 つ目の返り値（要確認の理由）は捨てる。
- 採る条件（3 つ全部）:
  1. 返った印 `hb` が `単品語あり・要確認(` で始まらない。
  2. `hb` から `R4c:商品分類既定>` を除いた残りが `^R[23]:` に当たる（`R3:MEMO:<語>` を含む）。R1・`R4:<語>`・既定・`EMPTY_BOX:explicit` は採らない。
  3. 群が同じ: `groups(c) = {e["value_group"] for e in ctx.cond_entries if e["canonical"] == c}`。新しい状態と件の既定の状態の両方が要素 1 つで、None でなく、等しいときだけ。群の列が無い環境（`tcg_analyzer_svc.py:778` で None）では採らない。
- 採ったときの印: `<hb>@見出し:L<見出しの塊の最も小さい行番号>`（例 `R3:未サーチ@見出し:L12`）。先頭が `R[23]:` なので、売り切れの引き継ぎ・値段からの推定は「語で決まった」として上書きしない。保存時に 100 字で切られても（`line_analysis_v102_svc.py:141`）先頭は残る。
- 差し込み位置: `gemini_raw_copy_v101.py:931-935` の `if product_first is not None:` の中、:933 で condition と basis を取り出した直後。差し替えるのは condition と basis の 2 つだけ。商品・単位・単位の区分・値段・数量・ステータス・要確認は触らない。単位は決め直さない（群が同じ状態だけ採るので、状態の単位は今の単位と同じ群。K3-2 で単位の差 0 を確かめる）。
- `ctx.product_first.condition_heading` が None なら何もしない（今と同じ）。

### H3. 設定（ADR-1041 What 5「コードに語や記号を書かない」）

- 置き場: `public.tcg_distribution_settings` の key `v102_condition_heading`。区分ごとの単位の表 `v102_kubun_allowed_units` と同じ表・同じ読み方。DB の形は変えない。
- 入れる値（試算と同じ）:

```json
{"max_lines": 3, "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"], "trailing_chars": "!！。"}
```

- コードは値から式を作る: `(` + `|`.join(re.escape(語)) + `)[` + re.escape(trailing_chars) + `\s]*$`。設定に正規表現は書かない（D2 の便2 の正規表現の設定 3 つは使わない）。
- 形: `ConditionHeadingRule`（frozen dataclass。`max_lines: int`・`sentence_end_re: re.Pattern[str]`）。`ProductFirstMasters`（`gemini_raw_copy_v102_product_first.py:126-149`）の最後に欄 `condition_heading: ConditionHeadingRule | None = None` を足し、`load_product_first_masters`（:368-392）で `_load_condition_heading(session)` を呼んで入れる（`kubun_allowed_units` と同じ道。:388・:430-436）。位置で作る所（:387・`backend/tests/test_v102_human_decisions_pg.py:41`）・`**__dict__`・`dataclasses.replace`（:231・`line_analysis_v102_svc.py:1505`）は、最後に既定 None の欄を足しても壊れない（第4.7版の審査で確認）。
- 検査（純粋な関数 `validate_condition_heading(raw: str | None) -> ConditionHeadingRule | None`）:

| 値 | 返り値 | ログ |
|---|---|---|
| key が無い（切り替え前の普通の状態） | None | debug だけ。マスタは仕事ごとに読み直す（`line_analysis_v102_svc.py:1556`）ので、info・warning だと切り替え前に毎回出る。区分ごとの単位の表は「無い＝入れ忘れ」なので warning、こちらは「無い＝切り替え前の正常」なので分ける |
| `{}`（取り消しの値） | None | なし |
| JSON として読めない | None | warning |
| `max_lines` が int でない・bool・1〜5 の外 | None | warning |
| `sentence_end` が空でない文字列の配列でない・空の配列・空の文字列を含む | None | warning |
| `trailing_chars` が文字列でない（空の文字列は可） | None | warning |
| 知らない key がある・必要な key が欠ける | None | warning |
| 上を全部通る | `ConditionHeadingRule` | なし |

- 切り替えは設定の行を入れること、戻しは値を `{}` に上書きすること（区分ごとの単位の表と同じ。data SQL の precheck・dryrun・commit・rollback・verify を `data/heading-*.sql` に置く）。
- 値段の形を設定に持たない理由: 値段の形は件の値段の見落とし（`_possible_missing_lines`）と同じ定義であるべきで、設定に二つ目の定義を作ると食い違う。ADR-1041 What 5 の「値段の形などは設定で持ち」と違うので、この PR で What 5 を直す。

## コードの変え方（file:line は origin/main `37fa04f7b`）

| ファイル | 変える所 | 触らない所 |
|---|---|---|
| `backend/app/services/gemini_raw_copy_v102_product_first.py` | `ConditionHeadingRule`・欄 `condition_heading`・`validate_condition_heading`・`_load_condition_heading`・:388 の呼び出しに 1 引数 | ほかの関数・`check_product_first_masters` |
| `backend/app/services/gemini_raw_copy_v101.py` | `_heading_block`・`_heading_condition` の新設、:931-935 の中で condition と basis を差し替える | `product_first is None` の枝、`_is_price_shaped` |
| `backend/app/tools/v102_replay_diff.py`（新設） | やり直しの台本（下の「試験」） | 本番の書き込みの段 |
| `backend/tests/`（新設のテストファイル） | 単体・境目・K0・K5・台本の試験 | 既存のテストの期待値 |
| `docs/handoff/v102-heading-and-unit/data/heading-*.sql`（新設） | 設定の data SQL 5 つ | 既存の data/*.sql |

触らないもの: `tcg_analyzer_svc.py`・`gemini_raw_copy_v102_soldout_ref.py`・`v102_buyback_unit_svc.py`・`v102_status_context.py`・`line_analysis_v102_svc.py`・指示文・migrations・deploy.yml・画面。

## 試験（実装の範囲）

- やり直しの台本 `backend/app/tools/v102_replay_diff.py`: 本番の `run_v102_analysis`（`line_analysis_v102_svc.py:1528`）の読み取りの部分だけを同じ順で行う。
  1. 投稿 id の一覧（ファイル）を受け取る。
  2. 投稿ごとに `load_extraction_context`、extraction_items の行（:1546 と同じ問い合わせ）、`_response_from_rows`（:1560）、`load_v102_decisions` と `_fixed_products`（:1561-1562）。
  3. マスタは `load_v102_masters`（:217）を 1 回だけ読み、`masters_with_followup(...)`（:1566-1569）で投稿ごとの引数を作る。
  4. `run_v102_pipeline(...)`（定義 :355・呼び出し :1570）を呼ぶ。`_write_results` 以降・`pg_advisory_xact_lock`・`commit` は呼ばない。
  5. 件ごとに 投稿 id・件の位置・lines・商品・単位・単位の区分・状態・condition_basis（100 字で切った値も）・値段・数量・ステータス・soldout_targets・soldout_target_basis を JSONL で `/tmp` に書く。
  6. 引数 `--heading-setting <JSON ファイル>` があれば、マスタの `condition_heading` を `dataclasses.replace` で差し替える（設定の表は読まない・書かない）。無ければ本番と同じく設定の表から読む。
  7. 差の道具: 2 つの JSONL を 投稿 id＋件の位置 で突き合わせ、列ごとの差の件数と、状態が変わった件の一覧を出す。
- AI を呼ばないこと: `_call_gemini`（`line_analysis_v102_svc.py:475`）を「呼ばれたら例外」に差し替えて流す試験を CI で回す。
- 流す場所: 本番の DB を読むだけ。重い処理は別コンテナ。台本と単体の試験は CI。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| K0: 設定が無いとき・`{}` のとき、変更後の出力は origin/main と全列・全件で差 0 | 単体の試験（検査の表の各行の返り値・None のとき `_extract_one` の結果が変わらない）。本番の読み取りで、直近 30 日を変更前（origin/main を固定した別の作業場所）と変更後（設定を渡さない）で流し、差の道具で全列 0 |
| K1: 見出しの下の未サーチのパック（〆の失敗の件）が全部 Unsearched pack・印が `R3:未サーチ@見出し:L<n>` の形 | 台本に `--heading-setting` を渡して流した表で数える（後処理の出力。書き込みの段は通らない） |
| K2: 基準の 17 件が 17/17（未サーチ 7 件が変わり、投稿の末尾の注記で状態が決まる投稿の 10 件は今のまま） | 同じ台本の結果を社外秘フォルダの基準の表と 1 件ずつ突き合わせる |
| K2-2: 直近 30 日の全投稿で、状態が変わった件を全部並べ、原文に照らして × 0 | 台本の差の一覧。Opus が 1 件ずつ ○× |
| K3: 見本 190 件が 190/190 のまま、正答率 A1〜A5 の平均が今以上 | 前回の採点の道具に、やり直しの結果を通す |
| K3-2: 状態以外の列（商品・単位・値段・数量・ステータス・soldout_targets・soldout_target_basis）が全件で差 0 | 差の道具が列ごとに数える。売り切れの相手が変わった件は K2-2 の一覧に入れる |
| K4: 本番の切り替え（設定の行を入れる）は PO の「切り替える」の後。マージだけでは本番の動きは変わらない（K0）。試験の費用 0 円 | 記録の時刻。`_call_gemini` を例外に差し替えた試験が通る |
| K5: 見出しで決めた件は、同じ語を件の行に書いた件と、値段からの推定・売り切れの適用の結果が同じ | 単体の試験: 印 `R3:未サーチ@見出し:L12` と `R3:未サーチ` の組（ほかは同じ）を、札 7・3・4 × 値段の帯（パック／箱／ケース／どれでもない）で、`v102_buyback_unit_svc` の候補の判定・`decide_kind`・`with_decision` と、`gemini_raw_copy_v102_soldout_ref` の `_narrow_by_condition`・`_is_inherit_candidate` に通す。状態・単位・`_is_inherit_candidate` の真偽が同じ、印は `@見出し:L<n>` を除いた先頭が同じ |
| 単体: 見出しの関数が、見出しの下の形・投稿の末尾の注記の形・件の行に状態がある形・見出しが無い形で期待どおり。境目: 止まり方 5 つ、絵文字で終わる文（除けない＝限界の固定）、半角の「!」で終わる文（除く）、「。」だけで終わる行（除く）、3 行で止まり 4 行目が件の行（None）／件でない行（a へ）、値段の形の行が混じる（None）、全角の空白だけの行（空行扱い）、値段の形でない「数と単位だけの行」が塊に入っても採れる | 単体の試験（原文は架空の文。社外の名前を入れない） |
| 設定の式: 入れる値から作った式と、第4.6版のコードの式（`(。|ます|ません|ございます|おります|です|下さい|ください)[!！。\s]*$`）が、境目の行で同じに当たる | 単体の試験 |
| K9: 切り替えの後 7 日間、毎朝の〆点検で、印に `@見出し:` を含む件を原文で判定し、誤り 0 | 毎朝の点検の判定記録 |

## 証拠（試算。社外秘フォルダ。v102）

- 入力: 本番の直近 30 日の v102 の全件 34,568 件（1,407 投稿）。本線の関数（`_resolve_condition`・`_is_price_shaped`・`condition_decided_by_word`）をそのまま呼ぶ。読み取りだけ。

| | 第4.1版（a・b・c なし） | 第4.2版以降（a・b・c あり。第4.7版の設定の値と同じ） |
|---|---|---|
| 状態が変わる件 | 48 | 42 |
| うち原文で正しい | 42 | 42 |
| うち誤り | 6 | **0** |
| 状態は同じで印だけ変わる | 7 | 1 |

- 42 件の内訳: 未サーチのパック 7 件・傷ありの箱 24 件・ダメージ品 7 件・シュリンク無し 4 件。Opus が原文で全件 ○。第4.1版の正しい 42 件は全部残る。
- 値段の段（K5b）: 値段からの推定で結果が変わり得る道 6 つ（候補に入る・外れる／札が無い状態／複数の候補の理由／値段の帯と札が合わない／札 8／印の末尾）について、30 日の対象 43 件で全部 0 件。値段の比そのものは読み取りの鍵で見えず未確認（過去 30 日の結果からの論証。今後は K5 で守る）。
- 売り切れの段・書き込みの段（K5c）: 道 6 つ（S1 直した件が〆の件／S2 参照の在庫になる／S3 同じ投稿の〆が在庫を売り切れにする・:1199／S4 同じ投稿の〆の引き継ぎ／S5 値段の引き継ぎ・:1207／S6 2 つ目以降の売り切れの相手・:1213）で、30 日の件数は全部 0。
- 限界: (1) 書き込みの段（`line_analysis_v102_svc.py:1198`・:1199・:1203・:1207・:1213）と人の判断の適用は台本で通らない（K5 で固定）。(2) 保存済みの件の行だけを見るので、AI が落とした件の行は「件の行」に入らない（本番は入る＝本番の方が止まりやすい側）。(3) 見落とし（直すべきなのに直らない件）は数えていない。

## 代替案

| 案 | 判定と理由 |
|---|---|
| A 指示文をさらに広げる | 採らない。10/22 に同系統の案が正答率を下げた。AI の返事は毎回揺れ、試験に費用がかかる |
| **B コードで見出しを見る（この設計）** | 採る。毎回同じ結果。保存済みの AI の返事で過去の投稿をやり直せ、試験の費用 0 円。件の行の語が常に優先 |
| C 仕入元ごとの設定に書く | 採らない。その仕入元だけで、欄が AI への指示に入るので A と同じ揺れ |
| D2 の便2（正規表現の設定 3 つ） | 採らない。規則の文が試算の道具と食い違い、審査 3 回目で保留のまま。この設計は試算が本線の関数をそのまま呼ぶ |
| 値段の形も設定に持つ | 採らない。値段の見落としの判定と二つ目の定義になり食い違う |

## リスクと対処

| リスク | 対処 |
|---|---|
| 前の件の続きの行を見出しと取り違え、下の件に状態が移る | c・b。採るのは R2・R3 の語だけ。K2-2 で 30 日の変わった件を全部目で見る（×0）。×が 1 件でも出たら設計に戻る |
| お店の方針・断り書きの文を見出しにする | a。第4.1版の誤り 5 件 → 第4.2版で 0 |
| 文で終わる見出しを落とす | 落ちても今と同じ（直らないだけ）。毎朝の〆点検で見逃しを見る |
| 見出しの範囲が広すぎる | 最も近い塊だけ。群の一致でパックの語は箱に効かない |
| 後の段が直した状態を上書きする | 印の先頭を `R[23]:` にする。K5 で固定 |
| マージしただけで本番の動きが変わる | 設定が無ければ働かない。K0 で全列・全件差 0 を確かめる |
| 設定の値の打ち間違い | 検査が None にして warning（今と同じ動きに戻る）。verify.sql で一字一句を確かめる |

## 戻し方

- 切り替えの後: data SQL の rollback（値を `{}` に上書き）。次の解析から今と同じ動き（解析は設定を仕事の最初に読むので、上書きの直前に始まった解析を除く）。
- コード: revert の PR（設定が `{}` か無ければ、コードが残っても動きは今と同じ）。

## 維持の仕組み

- 守り手: 新設のテストファイル（見出しの関数・設定の検査・K0・K5・台本）。CI で回る。
- 印 `@見出し:` で、毎朝の〆点検と読み取りで件数を数えられる。
- ADR-1041 の守り方に、key が無いときは debug だけの理由と、印の数え方を書く。
- 担当: 毎朝の〆点検（定期の仕事）と Opus。

## 接触面分析（6 面）

| 面 | 影響 | 確かめ方 |
|---|---|---|
| ①画面 | 状態の値と「決まり方」の印が変わる件がある（切り替えの後）。画面のコードは変えない | K2-2 |
| ②API | なし | — |
| ③処理 | v102 の後処理の状態の決め方。切り替えの前は変化なし | K0・K3-2 |
| ④データ | 設定の表に key 1 つ（切り替えのとき）。DB の形は変えない | data SQL の verify |
| ⑤外部 | AI を呼ばない | K4 の試験 |
| ⑥運用 | 毎朝の〆点検で `@見出し:` の件を見る | K9 |

## 外部・過去事例の参照と我々への応用

- 外部の事例は使わない。理由: 仕入元の独自の書き方を読む決まりで、外部の数値事例は判断の根拠にならない。根拠は本番の 30 日分の実測と、保存済みの返事でのやり直しの結果。
- 過去の事例: 同じ ADR の区分ごとの単位の表（便1）で、設定に置き、`{}` で戻し、data SQL で入れる形が本番で働いている。この設計はその道に揃える。

## 未決

- PO が決めるもの: 本番の切り替え（設定の行を入れる）の時期。実装・本番の読み取りの試算・審査の後に報告して「切り替える」の返事を待つ。
- 実装カードで確定するもの: 変更前として固定する HEAD、30 日の投稿の一覧の問い合わせ文。
- ADR-1041 を Accepted にする時期: K9 の 7 日の合格の後、PO 承認の手順で決める。

## 審査（同じ製品の AI。クラウドの審査役 model opus。人の第二者レビューではない）

- 第3版（2026-11-07）: REVISE。既定の印の種類・群の引き方・単位の決め直し・単位の区分・印の形と長さ・件の最初の行・台本の 7 点 → 第4版で直した。
- 第4版: APPROVE（推奨 3 点: 台本は書き込みの段を通らない・行番号・AI を呼ばない形 → 第4.1版で直した）。
- 第4.1版の試算で誤り 6 件 → 第4.2版で見分けの決まり a・b・c を足して 0 件。
- 第4.2版: REVISE（正本のコード・K5 の言い方・値段の段の道）→ 第4.3版で直した。
- 第4.3版: REVISE（売り切れの段の道）→ 第4.4版で直した。
- 第4.4版: 推奨 3 点（規則 12 の道ほか）→ 第4.5版で直した。
- 第4.5版: APPROVE（推奨: 値段の引き継ぎの道 S5 → 第4.6版で足した）。
- 第4.6版: APPROVE（推奨: 2 つ目以降の売り切れの相手の道 S6 → 足した。再審査なし）。
- 第4.7版（本線 `37fa04f7b`）: APPROVE。PO の実装承認の後、ADR-1041 What 5 と照合し、文の終わりの語と最大の行数をコードから設定へ移した版。推奨 2 点（key が無いときのログを debug に／ADR の index と備考）は反映済み（再審査なし。ログの格と ADR の文の追記のみ）。
