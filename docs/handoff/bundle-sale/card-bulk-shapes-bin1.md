# 実装カード 追記便1: バルク系だけ まとめ売りの形 P1・P2 を足す（コード）

> 親: [design.md](./design.md) §12（とくに §12-3・§12-4・§12-6）／ADR: [ADR-1027](../../adr/ADR-1027-bundle-sale-reading.md)「バルク系だけの追加の形（2026-10-21 追記）」／手順書: [bundle-sale-new-wording.md](../../runbooks/bundle-sale-new-wording.md)
> 区分: ADR-1015 の A。`scripts/dev/bundle_replay.py` を含む（`scripts/` 配下）。マージ前の GO 記録は Opus が委任 GO として PR 本文に書く。migrations・deploy.yml・本番の scripts は含まない。
> 状態: カード作成済み（Opus 2026-10-22）。設計審査済み（Opus reviewer 3回目 APPROVE・Fable「高」）。PO 承認は「1」（2026-10-21、チャット。既存の延長として進め、8 行を在庫表・シート版に「商品名 100枚セット」で出す）。設計の文書は PR #4623。

## 読んだ節（Opus・照合結果）
- guards/00-common.md・05-pr.md・07-migration.md（migrations は触らないので 07 は「該当なし」を確認）を読み、下の冒頭・PR の段に反映した。
- design.md §12-3・§12-4・§12-6、ADR-1027 追記の節、runbook の :13・:22・:35 を origin/main dddf78570 で照合（審査役 2026-10-22、一字一句一致）。

## 冒頭（必読）
- 受領確認: 着手前に「追記便1 カード受領・作業場所・HEAD」を /tmp/CC報告ファイル/bundle-bulk/bin1/receipt.txt に書く。
- 最初に `./scripts/dev/executor-preflight.sh || exit 1`。作業場所は `bash scripts/new-worktree.sh release/bundle-bulk-shapes-bin1 --claude`（origin/main 起点。PR #4623 がマージ済みの origin/main であることを `git log origin/main --oneline -5` で確かめる。未マージなら止まる）。
- 全コマンドは `cd /Users/tanizawashingo/worktrees/salesanchor/release-bundle-bulk-shapes-bin1 &&` で始める。出力は head/tail で上限を付ける。生出力は /tmp/CC報告ファイル/bundle-bulk/bin1/ に保存する。
- 停止するときは、止まった項目・理由・生出力のパスを `BLOCKED:` か `NEEDS_DECISION:` で Opus に返す。このカードに無いことはしない。
- 本番 DB・secrets・GitHub の設定には触らない。本番データ（~/CC報告ファイル-keep/ の下）は社外秘。リポジトリ・PR・コミットに中身（仕入元の名前・本文）を載せない。テストの本文は下に書いた作り文だけを使う。
- commit・push・PR は段を分け、各段で `git log -1` を確かめる。PR を作った後は作業場所の `.pr-number` が在り、番号が PR と同じことを確かめる。PR は `bash scripts/gh-pr-create-safe.sh`（本文は /tmp/CC報告ファイル/bundle-bulk/bin1/pr-body.md に先に書く）。下書きにしない。GO 記録の欄は作らない（Opus が書く）。マージはしない。`--admin`・`--auto` は使わない。
- 行番号は origin/main 7560d8007 時点で読んだもの（PR #4623 のマージ後の origin/main は dddf78570。#4623 は文書だけでコードは変えていない）。ずれていれば実物に合わせる。中身が違えば止まる。

## 実物点検（最初に。推測で進めない）
1. `backend/app/services/v102_bundle_svc.py` の :4（説明文）、:69-77（`_patterns`）、:92-101（`_find_candidates`）、:104-109（`_has_set_after_quantity`）、:112-143（`detect_bundle`）を読み、:128 が `found = _find_candidates(_strip_parens(full), pattern, word_to_canonical)` であることを確かめる。
2. `backend/app/services/line_analysis_v102_svc.py` の `_apply_bundle`（:1028 付近。:1034 で detect_bundle）と `_write_results` の :1140（`base_values = [_apply_bundle(...) for values, block in zip(base_values, blocks)]`）と :1141-1143（`PRODUCT_KUBUN_BULK` の分岐）を読み、:1140 の時点で `pairs` が `(item, row)` の並びで base_values・blocks と同じ長さ・同じ順であることを報告に書く。違えば止まる。
3. `PRODUCT_KUBUN_BULK` が `backend/app/services/gemini_raw_copy_v102_product_first.py:49` で `"バルク系"` であること、line_analysis_v102_svc.py が既にそれを import していることを確かめる。
4. `scripts/dev/bundle_replay.py` の :1-13（説明文）、:26-33（import）、:50-58（read_quantity）、:82-114（main）を読む。
5. `backend/tests/test_v102_bundle.py` の :90-95（単位名の直書き検査）、`backend/tests/test_v102_bulk_price.py` の :145-169（`ALIASES_MASTERS`・`_write`・`_item`）を読む。
6. 再現の入力を用意する: 第一は、ADR-1024 の読み取りの道（`~/.ssh/salesanchor-reader`・SELECT のみ）で、bundle_replay.py の説明文の列どおりに ALL_ROWS.tsv・UNITS_Q3.tsv・ALIASES_Q4.tsv を取り直す（q2・q3 の下にこの 3 つは無い。審査役が find で確認済み）。`~/.ssh/manual-only` は使わない。取れないときだけ、代わりに ~/CC報告ファイル-keep/accuracy-20261014/review-reasons/learn/widen/q2/all.jsonl（35,846 行。キーは arid・eid・cur・pid・pcat・ls・le・src・price・qty・unit・bs・rr・text。job_id・md5_8・price_basis は無く、pcat を kubun_type に読み替える）から変換し、その旨を報告に書く。どちらもできなければ止まる。固定一覧は同 q3/fixed.tsv（15 行）。
7. 基準の数を残す: 変更前（origin/main のまま）の bundle_replay.py を、6 の入力で `python3 -I` で回し、出力を ~/CC報告ファイル-keep/accuracy-20261014/review-reasons/learn/widen/bin1/replay/baseline/ に保存する。B3 はこの summary.txt と比べる。回せなければ止まる。変換の台本は ~/CC報告ファイル-keep/accuracy-20261014/review-reasons/learn/widen/bin1/ に置く（リポジトリに入れない）。

## 項目 1: `backend/app/services/v102_bundle_svc.py`
- `detect_bundle` に、最後の引数として `bulk_shapes: bool = False` を足す（既定 False。今の呼び出しは全て今と同じ結果）。
- 変更前 :128
  ```python
  found = _find_candidates(_strip_parens(full), pattern, word_to_canonical)
  ```
  変更後
  ```python
  found = _find_candidates(_strip_parens(full), pattern, word_to_canonical)
  if bulk_shapes:  # バルク系だけ（設計 bundle-sale §12: P1・P2）
      found += _find_bulk_candidates(full, word_to_canonical, set_words, quantity)
  ```
  :129 以降（空なら None・違う大きさ 2 つ以上・値段なし・割り切れ）は 1 字も変えない。
- 新しい関数 `_bulk_patterns(words: tuple[tuple[str, str], ...]) -> tuple[re.Pattern[str], re.Pattern[str]] | None`（`@lru_cache(maxsize=8)`）。unit_part・bundle_part は `_patterns`（:74-75）と同じ式で作る（語の表を新しく持たない。共通の小関数に切り出してもよいが、`_patterns` の結果は変えない）。
  - P1: `rf"({bundle_part}){_SP}*\((\d{{1,{_MAX_DIGITS}}}){_SP}*({unit_part})\)"`（固定一覧を作った写し q3/v2.py と同じ式。N と単位の間の空白は許し、括弧のすぐ内側の空白は許さない）
  - P2: `rf"({bundle_part}){_SP}*(?<!\d)(\d{{1,{_MAX_DIGITS}}}){_SP}*({unit_part})"`
  - 単位の語が空なら None。
- 新しい関数 `_find_bulk_candidates(full: str, word_to_canonical: Mapping[str, str], set_words: Iterable[str], quantity: object) -> list[tuple[int, str]]`:
  - P1 は **括弧を除く前の** `full` に当てる。P2 は `_strip_parens(full)` に当てる。
  - 両方とも、当たりの終わりの次の 1 字が `_AFTER_EXCLUDED`（入）なら使わない・N<2 は使わない（`_find_candidates` と同じ）。N は group(2)、単位は `word_to_canonical[group(3)]`。
  - P2 は、quantity が None でも空文字でもなく、`Decimal(str(quantity))` が整数（`q == q.to_integral_value()`。:137-139 と同じ読み方）で、かつ `_has_set_after_quantity(full, int(q), set_words)` が真のときだけ候補に入れる。それ以外は P2 を当てない（P1 は数量に関係なく当てる）。
  - コードに単位名を書かない（:90-95 の検査が通ること）。
- 説明文 :4 の「形は「数 N（1〜5桁）＋単位の語＋まとめの語」だけ。」の後ろに「バルク系の行だけ（引数 bulk_shapes）、「まとめの語＋(N＋単位の語)」と、本文に数量の直後のセットがあるときの「まとめの語＋N＋単位の語」も見る（design.md §12）。」を足す。:22 のコメントは変えない。

## 項目 2: `backend/app/services/line_analysis_v102_svc.py`
- `_apply_bundle` に最後の引数 `bulk_shapes: bool = False` を足し、中の `detect_bundle(...)` に `bulk_shapes=bulk_shapes` を渡す。ほかは変えない。
- 変更前 :1140
  ```python
  base_values = [_apply_bundle(values, block, unit_words, set_words, unit_ids) for values, block in zip(base_values, blocks)]
  ```
  変更後（今の行末コメントがあれば残す）
  ```python
  base_values = [
      _apply_bundle(values, block, unit_words, set_words, unit_ids, bulk_shapes=item.get("product_category") == PRODUCT_KUBUN_BULK)
      for values, (item, _row), block in zip(base_values, pairs, blocks)
  ]  # ADR-1027：全ての行。バルク系だけ P1・P2 も見る
  ```

## 項目 3: `scripts/dev/bundle_replay.py`
- import の後に定数を置く: `_BULK_KUBUN = "バルク系"  # = gemini_raw_copy_v102_product_first.PRODUCT_KUBUN_BULK（:49）。台本は純関数だけを import するので写し、一致は test_v102_bundle.py で固定`。product_first は import しない（`python3 -I` で動かなくなるため）。
- 変更前 :94
  ```python
  res = detect_bundle(block, unit_words, set_words, (r["price_normalized"] or "").strip() or None, read_quantity(r) or None)
  ```
  変更後: 同じ引数で bulk_shapes=False（今の規則）と `bulk_shapes=(r.get("kubun_type") or "") == _BULK_KUBUN`（新しい規則）の 2 回呼ぶ。結果は新しい規則の方を `res` として今の出力に使う。2 回の結果（kind・n・unit）が違う行を「増えた行」として数える。
- read_quantity（:50-58）は変えない。
- 出力:
  - rows.tsv に列 `kubun_type` と `bulk_shapes_changed`（0/1）を足す（既存の列の順は変えず、末尾に足す）。
  - summary.txt の「## 判定ごとの件数」を「## 判定ごとの件数（バルク系）」と「## 判定ごとの件数（それ以外）」の 2 表にする（表の形は今と同じ）。さらに「## バルク系だけの追加の形で変わった行: N 行（うちバルク系以外 M 行）」を 1 行出す。
  - 最後の print に `bulk_shapes_changed=%d` を足す。
- 説明文（:1-14 の docstring）に「kubun_type がバルク系の行は detect_bundle を bulk_shapes=True で読む（design.md §12）。summary.txt はバルク系とそれ以外に分け、追加の形で変わった行を数える。」を 1 行足す。

## 項目 4: `backend/tests/test_v102_bundle.py`（既存のテストは変えない。足す）
作り文だけを使う（仕入元の本文を使わない）。単位の別名は既存テストの作り方（split_unit_words に `{"枚": "Piece", "セット": "Set", ...}` を渡す形）に合わせる。
- P1: `bulk_shapes=True`、本文「✅RR バルク(100枚)\n@10000 在庫数 12セット」・値段 10000・数量 12 → KIND_DECIDED・n=100・unit "Piece"。同じ本文で `bulk_shapes=False` → None。
- P1 の括弧の内側の空白: 「バルク( 100枚 )」→ None。
- P2: `bulk_shapes=True`、本文「まとめ 100枚\n@24000 在庫数18セット」・値段 24000・数量 18 → KIND_DECIDED・n=100・"Piece"。同じ形で「在庫 20」・数量 20 → None。数量 None → None。`bulk_shapes=False` → None。
- 入: 「バルク(100枚入)」は括弧が閉じないので P1 に当たらない → None。「まとめ 100枚入 / @3000 在庫 5セット」・数量 5 → None。
- 混ぜる: `bulk_shapes=True`、本文「50枚セット\nバルク(100枚)\n@5000 在庫 3セット」・数量 3 → KIND_UNVERIFIED（違う大きさ 2 つ）。
- 過去の誤りの形: 本文「シングル 10000円(合計34枚セット)」・数量 1 と、本文「BULK 200枚 ¥4300」・数量 None → `bulk_shapes=True`・`False` とも None。
- 定数の一致: `importlib.util.spec_from_file_location` で `scripts/dev/bundle_replay.py` を読み込み、`_BULK_KUBUN == PRODUCT_KUBUN_BULK`（`from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_BULK`）。読み込みで main は走らない（`if __name__ == "__main__"` のため）ことを確かめる。
- 期待と違う結果が出たら、テストを期待に合わせて書き換えずに止まる（`NEEDS_DECISION:`）。

## 項目 5: `backend/tests/test_v102_bulk_price.py`（既存は変えない。2 本足す）
- `_write([_item(price_normalized=3000, quantity_normalized=26)], raw_text="【見出し】\n✅RR バルク(100枚)\n@3000 在庫数 26セット", lines=(2, 3), masters=ALIASES_MASTERS)[0]` → `bundle_size == 100`・`unit_canonical == "Piece"`・`price_normalized == 3000`・`quantity_normalized == 26`・`review_reasons is None`・`needs_review is False`。
- 同じ本文で `_item(price_normalized=3000, quantity_normalized=26, product_category="箱系")`（`_item` の BULK を上書きする形。上書きできなければその方法を報告してから足す）→ `bundle_size is None`。

## 項目 6: 文書の手直し（審査の低い指摘 1〜4。文字はこのとおり）
- `docs/runbooks/bundle-sale-new-wording.md`
  - 「規則は 1 か所（`detect_bundle`）だけで直す。画面ごと・区分ごとに別の読み方を作らない。」→「規則は 1 か所（`detect_bundle`）だけで直す。画面ごとに別の読み方を作らない。区分で形を分けるときも、`detect_bundle` の引数（例: `bulk_shapes`）で分け、別の関数や別のファイルを作らない。」
  - 「- 区分で絞らずに新しい形を足す（2026-10-21 の試算では、区分で絞らないと全 35,846 行のうち 303 行が動いた）。」→「- 区分で絞らずに新しい形を足す（2026-10-21 の試算では、「N種＋まとめの語」も含めて区分で絞らずに当てると全 35,846 行のうち 303 行が動いた。主に「N種」の形）。」
  - 手順 1 の 3 の文の後ろに「rows.tsv には本文が無いので、本文は ALL_ROWS.tsv と item_id で突き合わせて見る。」を足す。
- `docs/handoff/bundle-sale/design.md` の状態の行（:14 付近）の「便1 実装未着手」を「便1 実装済み（この PR）・便2 未着手」に直す。
- `docs/handoff/bundle-sale/design.md` §12-4 の `scripts/dev/bundle_replay.py:` の箇条の末尾に「説明文 :1-13 に、バルク系は bulk_shapes=True で読むことを 1 行足す。」を足す。
- このカードを `docs/handoff/bundle-sale/card-bulk-shapes-bin1.md` として置く（この内容のまま）。

## 項目 7: 再現（PR の前・リポジトリの外）
- 実物点検 6 の入力で、新しい `scripts/dev/bundle_replay.py` を `python3 -I` で回す。出力は ~/CC報告ファイル-keep/accuracy-20261014/review-reasons/learn/widen/bin1/replay/。
- 照合: 「増えた行」（bulk_shapes_changed=1）の item_id の集まりが q3/fixed.tsv の 15 行の extraction_item_id の集まりとちょうど同じで、15 行とも新しい判定が decided・N=100・Piece。バルク系以外の増えた行 0。照合の台本と結果も同じフォルダに置く。
- 1 行でも違えば止まる（違う行の一覧を付けて `NEEDS_DECISION:`）。

## 止まる条件
- 実物点検の中身がこのカードの前提と違う（とくに :128・:1140・pairs の並び）。
- 項目 4・5 のテストの結果が期待と違う。
- 項目 7 の照合が固定一覧と 1 行でも違う。バルク系以外で 1 行でも変わる。
- カードに無いファイルを触る必要が出た。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| B1 既存のテストが全部そのまま緑・項目 4・5 の新しいテストが緑 | CI 必須「pytest (SQLite + PostgreSQL RLS)」 |
| B2 bundle_replay.py の「増えた行」が固定一覧 15 行と item_id ごとに一致・全て decided 100 Piece・バルク系以外 0 | 項目 7 の照合結果（~/CC報告ファイル-keep/.../widen/bin1/replay/） |
| B3 detect_bundle の既定（bulk_shapes=False）の結果が今と同じ・バルク系以外の行の判定が今と同じ | B1 の既存テスト＋新しい台本のバルク系以外の判定ごとの数が、実物点検 7 の baseline/summary.txt の同じ行の数と一致（「バルク系以外の増えた行 0」は仕組み上いつも 0 なので、この比べ方で確かめる） |
| B4 単位名の直書きなし | test_v102_bundle.py :90-95 |
| B5 PR 本文に bundle_replay の数（バルク系／それ以外の判定ごとの数・増えた行数・うちバルク系以外の数）を書く | PR 本文（ADR-1027「維持の仕組み」） |

## 触るファイル（全部）
backend/app/services/v102_bundle_svc.py、backend/app/services/line_analysis_v102_svc.py、scripts/dev/bundle_replay.py、backend/tests/test_v102_bundle.py、backend/tests/test_v102_bulk_price.py、docs/runbooks/bundle-sale-new-wording.md、docs/handoff/bundle-sale/design.md、docs/handoff/bundle-sale/card-bulk-shapes-bin1.md（新規）

触らない: v102_bulk_price_svc.py・tcg_distribution_svc.py（配信 SQL）・マスタ・migrations・deploy.yml・frontend・ADR。

## PR 本文に書くこと
- `### 標準ワークフロー確認`: recon `docs/handoff/bundle-sale/recon.md`・設計 `docs/handoff/bundle-sale/design.md`・対象ADR `ADR-1027`・設計仕様書 `docs/specs/bundle-sale/README.md`・触るファイル（上の全部を 1 行カンマ区切り）・削除するファイル（1 行でも書き換えたファイルを全部）・区分 A・PO承認「1」（2026-10-21、チャット）。
- B5 の数。仕入元の名前・本文は書かない。

## 戻し方
PR を revert する（列もマスタも変えないので、コードを戻せば読み方は今に戻る）。本番の行は便2 で再解析するまで変わらない。便2 の後に戻すときは、便2 で用意する書き戻しの SQL を使う。

## カードチェック（Opus reviewer・2026-10-22）
- 審査役 APPROVE（高 0・中 3・低 5）。カード通りに複製へ実装し、テストの期待値は全て一致、全 35,846 行で変わる行 15 行が固定一覧と一致（/tmp/CC報告ファイル/bundle-bulk/bin1/cardcheck/）。
- 反映: 中1 P1 の式を v2.py に揃えた／中2 基準の数（実物点検 7）と B3 の比べ方／中3 入力は reader 鍵で取り直しが第一／低1 読んだ節／低2 `.pr-number`／低3 design.md の状態の行／低5 docstring :1-14。低4 は今の書き方（集合と decided の両方を照合）で足りる。
- 数量が数字でない文字列のとき P2 の入口で例外になる点（審査役 低）: 本番の `_apply_bundle` の数量は Decimal か None なので、カードは変えない。

## Opus の対応表
- design.md §12-3（形と条件）→ 項目 1、§12-4（触るファイル）→ 項目 1〜5、§12-6（K1〜K10）のうち便1 で確かめられる K3・K4・K5 → B2・B3・項目 4、審査の低い指摘 1〜4 → 項目 6。K1・K2・K6〜K10 は便2 で照合する（本番データの読み直しの後）。
- 正本の重複なし: 判定は v102_bundle_svc 1 か所（台本も import）・単位の語は別名マスタ・まとめの語は BUNDLE_WORDS・区分の語は PRODUCT_KUBUN_BULK（台本の写しはテストで一致を固定）。
- 画面のコードは触らない（デザイン部品の追加なし）。

END OF CARD
