<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — v102 の決まりの直し（言葉の表・単位・見出し・〆・残り）

> この文書は何か：2026-10-24 の正答率の測り直しで、原文・Gemini の書き写し・システムの解析を 300 件突き合わせたところ、誤りはどれも Gemini ではなくシステム側の決まりの入れ忘れだった。その決まりがコードと表のどこにあるかを、行番号つきで並べた下調べです。
> 親: `docs/handoff/v102-rule-fixes/design.md`

**仕事名**: v102-rule-fixes  
**日付**: 2026-10-25  
**対象ADR**: ADR-1023 / ADR-1035 / ADR-1036 / ADR-1041（すべて既存。新しい ADR は作らない。理由は design.md「ADR」）  
**担当**: architect（Opus。同じ AI が設計と審査をする自己審査）  
**基準**: `git fetch` 後の origin/main d7924ae70。行番号は git show origin/main で読んだ行。

社外秘の扱い: 仕入元の名前・投稿の原文・投稿の id は書かない。件ごとの原文と生の出力は社外秘フォルダ（リポジトリの外。accuracy-20261024/new-posts/check3/ と design-prep/）に置き、ここでは件を「件1〜件9」と呼ぶ。対応表は社外秘フォルダの照合表にある。

---

## 0. 既存の ADR と設計の検索

- git grep で「見出し」「〆」「状態の語」「state_word」を docs/adr/ から探した結果 と `docs/adr/FEATURE-INDEX.md` を見た。FEATURE-INDEX には、状態・単位・〆・v102 の行が無い（見落としやすい。design.md「維持の仕組み」で 1 行足す）。
- 関係する ADR（社外秘フォルダ design-prep/R1.md 43-51 行に全表）:
  - ADR-1023（Accepted）状態の価値順。複数の状態が当たったら価値の低い方を採る。
  - ADR-1035（Proposed）状態ごとの単位。ADR-1036（Proposed）個・無記入の箱系は値段で単位を決める。
  - ADR-1041（Proposed 2026-10-23）区分ごとに取れる単位の表＋状態の見出し（What5。保留中）。
  - ADR-1031（Accepted）シングル系の状態。ADR-1032（Accepted）復活止め。ADR-158 is_current。ADR-1007 migration は構造だけ。
- 既存の設計:
  - `docs/handoff/v102-heading-and-unit/design.md` — 状態の見出し D2（便2）。15 行目で「規則の文章が試算の道具と食い違う点と、根拠 `R11:` が値段の処理の行き先を変える経路が残る」ため保留。244-246 行に審査 3 回目の必須 2 件。
  - `docs/handoff/v102-shime-same-post-stock/design.md` — 〆の規則 13（§3）。ADR は無い（§9）。

## 1. file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/gemini_raw_copy_v101.py:921` | `block = "\n".join(lines[n - 1] for n in item["lines"])`。システムは Gemini が件に入れた行（lines）だけから、商品・単位・状態・販売状況を決める。件の外の行は見ない |
| `backend/app/services/gemini_raw_copy_v101.py:71` | 行の役割 `ROLE_PRICE, ROLE_SHIP, ROLE_CONDITION, ROLE_STOCK, ROLE_NAME = "price", "ship", "condition", "stock", "name"` |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:563` | `find_unit_product_first`。単位の語を見つけた行の番号と役割を `unit_basis` の `line`・`role` に残す（:549・:559） |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:57` | `PRODUCT_KUBUN_UNKNOWN = "不明"`。商品が決まらないときの区分（:596-600 `_match_summary`） |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:77` | `_STATE_WORD_BASIS_RE = re.compile(r"^R[123]:")`。状態が原文の語で決まった印 |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:735` | `_resolve_unit_from_state`。764-766 行で、状態が原文の語（R1〜R3）で決まり、状態の単位が今の単位と違えば、書かれた単位を状態の単位に置き換える（理由 `state_word`）。書かれた単位がどの行の語か・区分が「不明」かを見ていない |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:775` | `_fix_unit_by_kubun`（ADR-1041 の表）。:764 の置き換えの後に動くので、置き換えを止められない |
| `backend/app/services/gemini_raw_copy_v102_product_first.py:822-834` | 呼ぶ順: 単位を見つける → 状態を決める（`_resolve_condition`）→ `_resolve_unit_from_state` → `_fix_unit_by_kubun` |
| `backend/app/services/v102_status_context.py:109` | `_heading`。件の最初の行から上へ、件でない行を探し、表の語に当たる行を見出しにする。販売状況だけに使う |
| `backend/app/services/v102_status_context.py:120` | `context_status`。販売状況が既定で決まったときだけ見出しで決め直す。状態（Damaged など）には同じ仕組みが無い |
| `backend/app/services/line_analysis_v102_svc.py:1085` | 規則 13 `_sell_out_stock_closed_in_the_same_post`。〆の件（自分の値段・数量が無く、商品と状態が決まった件）が範囲に含む在庫の件を Sold out にする |
| `backend/app/services/line_analysis_v102_svc.py:1157` | 規則 13 の呼び出し。値段で単位を決める処理（:1156）の後 |
| `backend/app/services/line_analysis_v102_svc.py:97` | 指示書のキー `V102_PROMPT_KEY = "raw_copy_v101_f_ct"`。本文は DB の extraction_prompt_config |

## 2. 誤りごとの原因（どれもシステム側。Gemini の書き写しの誤りは 0 件）

照合 300 件のうち、8 項目すべてに誤りが無いものは 271 件。誤りは 30 か所（29 件）。Gemini の 3 項目（行の範囲・数量・値段）はすべて書き写しのとおり（299/300。残る 1 件は件5、下）。

| 件 | 誤りの形 | 原因の場所 | 群 |
|---|---|---|---|
| 件1 | 「傷あり」と書かれた箱が、未開封の箱（Sealed box）になった | 状態の表で「傷」を含む語は「傷み」だけ（社外秘 cause/B.md §1c）。「傷あり」「傷有」「キズあり」が無い | F1 |
| 件2 | 「50パック@130円」の行の単位が Box になった | `backend/app/services/gemini_raw_copy_v102_product_first.py:764-766`。同じ件の「シュリンク無し」で状態が No shrink box に決まり、値段の行に書かれた「パック」を状態の単位 Box で上書きした | F2 |
| 件3 | 商品が決まらない行の「セット/¥…」の単位が Box になった | 同じ :764-766。区分「不明」でも上書きする | F2 |
| 件4・件5 | まとめ見出し「ダメージ品在庫」と、その下の説明「箱破れや潰れあり」の下の品目が Sealed box になった | 見出しの行が件の lines に入らない（`backend/app/services/gemini_raw_copy_v101.py:921`）。状態には見出しを受け継ぐ仕組みが無い（`backend/app/services/v102_status_context.py:109` は販売状況だけ） | F3 |
| 件6 | 見出し「【シュリンク無し】」の下の品目が Sealed box になった | 同上 | F3 |
| 件7 | 1 行目「下記商品　〆」の下の在庫が In Stock のまま | 〆の行が件にならず、どの件の block にも入らない。規則 13（`backend/app/services/line_analysis_v102_svc.py:1085`）は商品が決まった〆の件が前提 | F4 |
| 件8 | 「↑↑↑ 〆させていただきます」の上の在庫が In Stock のまま | 同上 | F4 |
| 件9 | 「8BOX」の下の「こちら残り 3BOX」が別の在庫として 2 行とも In Stock で残った | Gemini は 2 件に分けた（指示書の「値段の行ごとに 1 件」のとおり）。ただし Gemini の写しは「3BOX」で「残り」が落ちた（指示書は「残り」を写すよう求めている）。システムには「残り」が前の数量を置き換える決まりが無い | F5 |

今回の範囲の外（design.md「対象外」）: 商品が決まらない 16 件（検索語・除外語の不足 9・未登録 7）、雑誌付きの 2 件、状態が 2 つ書かれた 1 件、一部だけ傷んだ 1 件。

## 3. 本番での件数（v102-f_ct の現行行 4,927 件・1,196 投稿。社外秘 design-prep/R2.md 19-23 行）

| 群 | 本番の件数 | 読み方 |
|---|---|---|
| F1 傷あり系の語 | 本番の投稿全体（3,762 投稿）で 6 投稿。シングル系の行に入る語は 0 件 | 少なく、誤爆の先も無い |
| F2 状態の語で単位が置き換わった行 | 数量や値段の行に Pack・Set と書かれているのに Box・Case になった行 2 件。逆に、単位の語が数量に無く置き換えが正しく効いている行（推定）236 件 | 2 件だけを止め、236 件は変えない条件が要る |
| F3 件の外の行に状態の語 | 見出しの形 2,097 行（529 投稿）。まとめ見出しのダメージ語 24 行（下の件 83 件・状態の不一致 42 件）。「シュリンク無し」46 行（161 件・不一致 66 件）。注意書きで下に件があるもの 10 行（不一致 2 件） | 「下の件」の範囲は近似（R2.md 29 行）。見出しが本当に全部にかかるかは行ごとに読まないと決まらない |
| F4 〆が件の外にある投稿 | 28 投稿。時刻の案内でないもの 15（行末の〆 9・〆だけの行 2・「〆させていただきます」2・「下記商品 〆」1・「〆切」1）、時刻の案内 13 | 15 投稿の意味（完売か案内か）は文面を読まないと決まらない |
| F5 同じ投稿・商品・状態で In Stock 2 行以上 | 58 組。後ろの行が「残り」で始まる組 0。件9 の形は 1 組だけ | 誤りの形は 1 組で、決まりを足すほどの数が無い |

## 4. 表と指示書の変え方（前例）

- 状態の表（line_conditions）は migration で入れない。docs/handoff/<名>/data/ に記録 SQL（precheck → dryrun（ROLLBACK）→ commit → verify → rollback）を置き、PO が `!` で流す（ADR-1023 35 行、ADR-1007）。前例: `docs/handoff/v102-heading-and-unit/data/`。
- 管理画面は無い（ADR-1023 41 行「別便」）。
- 指示書を変えるときは新しいキーを足して切り替え PR を出し、過去の投稿を直すには Gemini の取り直しが要る（`backend/app/tools/reextract_v6_with_v102.py`）。コード・表だけの変更なら、システム段のやり直し（`backend/app/tasks/tcg_extraction.py:736` `reanalyze_v102_job`）で足りる。

## 5. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 件2・件3 の単位の語は、どの役割の行で見つかったか | 再試算で `unit_basis.role` を出す（便2 の K2-1）。原文では件2 は値段の行「50パック@130円」、件3 は値段の行「セット/¥…」 | 便2 のカードの最初に確かめる（不一致なら便2 は止める） |
| 2 | F2 の 236 件で、単位の語が数量・値段の行にあるものは何件か | 便2 の再試算（K2-2）で全件を数える | 便2 の受入条件にした |
| 3 | 件4〜件6 が、保留中の見出しの規則 D2 で直るか | 件4 の見出しは「在庫」を含み、D2 の「見出しでない印」（在庫）に当たる。件5・件6 も D2 の範囲（空行 2 連続で止める）に入るかは試していない | 便3（D2 の再設計）の受入条件にした |
| 4 | F4 の 15 投稿の〆が、どの品目の完売を意味するか | 15 投稿の原文を Opus が読んで分ける（便4 の最初） | 便4 の設計の続きで解消する。それまで便4 は実装しない |
| 5 | 「シュリンク無し」と「ダメージ有り」が両方書かれた箱の正解、雑誌付きの正解 | PO の判断 | 今回の範囲の外。別に聞く |

**未解決ゼロ確認**: 便1・便2 の前提は解消済み（#1・#2 は便2 の受入条件で確かめ、外れたら止める）。#3・#4 は便3・便4 を「設計の続き」とすることで扱い、実装可能とはしない。#5 は対象外。
