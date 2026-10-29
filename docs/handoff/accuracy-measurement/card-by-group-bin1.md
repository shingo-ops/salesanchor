---
mode: handoff
---
# 実装カード 段1: 正答率を仕入元ごと・中分類ごとに分けて数える道具

親: [design-by-supplier.md](./design-by-supplier.md) §4〜§8

- 状態: カード作成済み・設計審査済み（2026-10-29 Opus、同じ AI による自己審査・下の §8）・PO 実装承認（2026-10-29 チャット、選択肢「1. 道具を作り、10/25 の300件を仕入元ごと・種類ごとに分けて弱いところを洗い出す」に「1」と回答）
- 担当: Sonnet（クラウドで実装〜push）。PR は手元で shingo-cc 名義。Opus は審査・マージ判断。
- 社外秘: 仕入元の名前・投稿の原文・投稿 id・判定表は、リポジトリにも PR にも入れない。試験は作り物のデータだけを使う。

## 0. 設計からの変更点（PO の選択による）

設計 §4 は score_v102 の出力を分ける形だった。PO が「10/25 の300件を分ける」を選んだため、分ける道具を **入力の形に依存しない1本**にする。入力は「1件×1項目＝1行の判定表」。10/25 の照合表も、後の score_v102 も、この形に直してから渡す。score_v102.py は変えない（設計 §5 V5 の「全体の表が変わらない」は、触らないことで守る）。

## 1. 作るもの

- `scripts/accuracy/by_group.py`（新規。Python 3.12・標準ライブラリだけ）
- `scripts/accuracy/test_by_group.py`（新規。pytest。作り物のデータだけ）
- `scripts/accuracy/fetch_groups.py`（新規。読むだけの窓口から対応表を作る。標準ライブラリだけ。窓口への送り方は `fetch_gold.py` の `post()` を読み込んで使う。新しく書かない）
- `scripts/accuracy/test_fetch_groups.py`（新規。窓口は差し替えて試験する。本番には繋がない）
- `scripts/accuracy/README.md`（追記。使い方を数行）

触らないもの: `score_v102.py`・`fetch_gold.py`・`fetch_snapshot.py`・`gold_to_sql.py` とその試験、`backend/`・`frontend/`・`migrations/`・`.github/`。DB への書き込みは無し。

## 2. by_group.py

```
python3 -I scripts/accuracy/by_group.py --verdicts <判定表.tsv> --groups <対応表.tsv> --out-dir <出力先>
```

- `--verdicts`: タブ区切り・1行目は見出し `key	項目	判定`。判定は `OK` / `NG` / `NOWORD` のどれか。ほかの値があれば、その行番号を出して終了コード2。同じ key と項目の組が2回あれば終了コード2。
- `--groups`: タブ区切り・1行目は見出し `key	仕入元	中分類`。値は文字列。空は `不明` として扱う。同じ key が2回あれば終了コード2。判定表にあって対応表に無い key は、両方の分け方で `不明` に入れ、件数を標準エラーに1行出す（止めない）。
- `--out-dir`: リポジトリの中（`git rev-parse --show-toplevel` の配下。git が無ければこの検査は飛ばす）なら拒否して終了コード2。score_v102.py の同じ検査の書き方に揃える。
- 出力（3つ。文字コード UTF-8・改行 `\n`・最後の行にも改行）:
  - `overall.tsv`・`by_supplier.tsv`・`by_category.tsv`
  - 列: `区分	項目	正しい	違う	答え無し	正答率	幅の下	幅の上	参考`（overall の区分は `全体`）
  - 項目の並び: 判定表に最初に出た順。その後に `全項目` を1行。`全項目` は key ごとに「NG が1つでもあれば違う、無ければ正しい」。答え無しは 0。
  - 区分の並び: 文字列の昇順。`不明` は最後。
  - 正答率 = 正しい ÷（正しい＋違う）を百分率で小数1桁（`%.1f`）。分母が0なら `-`。
  - 幅: Wilson の95%区間（z = 1.959964）。百分率で小数1桁。分母が0なら `-`。
  - 参考: 正しい＋違うが20未満なら `参考`、それ以外は空。
- 合計の照合（設計 §5 V2）: 項目ごとに、各区分の 正しい・違う・答え無し の合計が overall と一致することを、by_supplier と by_category の両方で書く前に確かめる。合わなければ何も書かずに `STOP: 合計が合いません <項目>` を出して終了コード3。
- 同じ入力なら出力は1バイトも変わらない（日時・乱数・辞書の順に頼らない）。

## 3. fetch_groups.py

```
python3 -I scripts/accuracy/fetch_groups.py --keys <keys.tsv> --out <対応表.tsv> [--url U]
```

- `--keys`: 見出し `key	msg_id	product_id`。product_id は空でもよい。
- 窓口に送る問い合わせ（読むだけ。ai_ro のビュー名は設計 §8 の確認結果による）:
  - 仕入元: `ai_ro.public__source_messages` の `id = msg_id` から `supplier_channel_id`、`ai_ro.public__supplier_channels` の `id` から `supplier_id`。出力の仕入元列には **supplier_id の数字だけ**を書く（名前は引かない）。
  - 中分類: `ai_ro.public__products` から `work_id`、`ai_ro.public__type_master` の `id = work_id` の `name_ja`。products の商品番号の列名は、最初に `information_schema.columns`（窓口で引く）で確かめる。product_id が空、または見つからないときは `商品なし`。
  - msg_id と product_id は、問い合わせに入れる前に形を確かめる（UUID か数字の形だけ通す。それ以外は終了コード2）。文字列をそのまま SQL に継ぎ足さない。
- 最初の実行で、上の列が窓口に無ければ、何も書かずに `BLOCKED: 窓口に <列> が無い` で終了コード1。推測で別の列を使わない。
- 窓口の行数の上限（fetch_gold.py の ROW_LIMIT）を超える問い合わせは、分けて送る。

## 4. 試験（作り物のデータだけ）

- by_group:
  - T1 2区分×3項目の小さな表で、正しい・違う・答え無し・正答率・幅・参考が手計算どおり（幅は 9/10 → 59.6〜98.2、18/20 → 69.9〜97.2 を含める）。
  - T2 合計がずれる入力（作り物で対応表を細工する）で終了コード3・何も書かない。
  - T3 同じ入力を2回流して、3つの出力の sha256 が一致。
  - T4 判定の値が不正・key の重複・出力先がリポジトリの中、でそれぞれ終了コード2。
  - T5 対応表に無い key が `不明` に入り、`不明` が最後に並ぶ。
  - T6 `全項目` の行が key ごとの判定どおり。
- fetch_groups: 窓口の返事を差し替えて、対応表の形・`商品なし`・列が無いときの BLOCKED・不正な id での終了コード2。
- 流し方: `python3 -m pytest scripts/accuracy -q`。CI では集められない（設計「維持の仕組み」）。結果の全文を PR 本文に貼る。

## 5. 本番での確かめ（クラウドで1回だけ・読むだけ）

- 窓口で `information_schema.columns` を引き、§3 の列（source_messages の id・supplier_channel_id、supplier_channels の id・supplier_id、products の商品番号の列と work_id、type_master の id・name_ja）が出ているかを確かめる。出力は表名と列名だけ。行の中身は読まない。
- 結果を報告に書く。外れていたら §3 の実装を進めずに BLOCKED で返す。

## 6. 段2（このカードの外。Opus が手元で行う）

10/25 の照合表 `check_final.tsv` の8項目（g_lines・g_qty・g_price・s_qty・s_price・s_unit・s_cond・s_status。値の `:` や `(` より前を判定とする）を判定表に直し、`detail.json` の a・msg_id・s_product_id から keys.tsv を作る。照合の基準値は、全項目正しい 271/300・s_cond 48/24/228（2026-10-29 Opus が数え直して一致）。中分類はシステムが付けた商品で分ける（10/25 の表に正解の商品が無いため。設計 §4 の「正解の商品で分ける」からの変更点として、結果の表に注記する）。

## 7. 終わりの条件

- `python3 -m pytest scripts/accuracy -q` が全部通る（既存の試験も含む）。
- §5 の確かめの結果が報告にある。
- リポジトリの差分は §1 の5ファイルだけ（`git diff --name-only origin/main...HEAD`）。
- 報告の最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <内容>` のどれか。

## 8. カードの自己審査（2026-10-29 Opus）

- 判定: APPROVE
- 設計との整合: KGI-1〜5 は §2 の出力・参考・合計の照合・同じ出力で満たす。V1=§4 T1〜T6、V2=§2 合計の照合、V3=T3 と段2 の2回実行、V4=段2 で Opus と Sonnet が1仕入元を手で数える、V5=score_v102.py を触らない＋既存の試験が通る。
- 設計からの変更点は §0 と §6 の2つ。どちらも PO の選択（10/25 の300件を分ける）から来ていて、KGI は変わらない。
- 残る未確認: 窓口の列（§5 で確かめる）。外れたら止まる道を §3・§5 に書いた。
