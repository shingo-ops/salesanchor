---
mode: handoff
---
# 実装カード 便2: 正答率の採点の道具（読み取り専用）

親: [design.md](./design.md) §7・§8 便2

- 状態: カード作成済み・設計審査済み（2026-10-20 Opus、同じ AI による自己審査）・改訂1（使う行を全行に変更、2026-10-20 Opus）・PO 実装承認（2026-10-20「1」＝「照らし合わせる道具を作る」）
- 担当: Sonnet（実装）。Opus は審査・マージ判断。
- 社外秘: 正解表・投稿の原文・システム結果の写しは、リポジトリの外の `~/CC報告ファイル-keep/accuracy-gold-20261020/` に置く。リポジトリには道具と、作り物のテスト用データだけを入れる。

## 1. 作るもの

- `scripts/accuracy/score_v102.py`（新規。Python 3.12・標準ライブラリだけ）
- `scripts/accuracy/test_score_v102.py`（新規。pytest。作り物のデータだけを使う）
- `scripts/accuracy/README.md`（新規。使い方を5行ほど）

触らないもの: `backend/`・`frontend/`・`migrations/`・`.github/`・本番の `scripts/`（deploy 系）。DB には接続しない。

## 2. 入力（引数）

```
python3 -I scripts/accuracy/score_v102.py \
  --gold <gold_v1.tsv> --snapshot-dir <snapshot/> --out-dir <出力先>
```

- `--gold`: 正解表。タブ区切りで1行目は見出し。列は `投稿id, price_line, lines, 許容する行, E2_price, E3_quantity, A1_product_id, A2_condition, A3_unit, A4_status, A5_ship, A4根拠, 迷い, 除外, 裁定根拠, PO確認`。
- `--snapshot-dir`: `<投稿id>.tsv` が投稿ごとに並ぶフォルダ。1行目は見出しで、システム結果の写しが入っている。使う列は `extraction_item_id, line_start, line_end, source_lines, raw_price, raw_quantity, product_id, condition_canonical, unit_canonical, status, ship_ja, price_normalized, quantity_normalized, exclusion`。見出しは名前で引く（列番号の直書きは禁止）。必要な列が無ければ、エラーで止める。
- `--out-dir`: 出力先。リポジトリの中のパス（`git rev-parse --show-toplevel` の配下）が指定された場合は、拒否して止める（社外秘の流出を防ぐため）。

## 3. 採点の決まり

1. **使う行**: snapshot の全行を使う。`is_current` では絞らない（改訂 2026-10-20 Opus）。
   - 理由: 写しは1件につき1行で、重複は0件。同じ件に別の世代は無い。`is_current` が false なのは、同じ仕入元の後の投稿に同じ商品と状態があり、古い方を外したという意味（backend/app/services/tcg_analyzer_svc.py:1627）。その投稿の解析としては最新。
   - 調べた記録: /tmp/CC報告ファイル/accuracy-design/prod-compare.txt。
2. **件の対応づけ**: 投稿ごとに、正解の件とシステムの件を対応づける。
   - システムの件が正解の件に当たるのは、正解の `price_line` がシステムの件の行の範囲（`line_start`〜`line_end`）に入るとき。
   - 当たる候補が2つ以上あるときは、行の重なり（正解の lines との共通の行数）が最大のものを選ぶ。同点なら `extraction_item_id` の小さい方。
   - 1つのシステムの件は、1つの正解の件にしか使わない。正解の件は投稿内の price_line の昇順で処理する。
   - 全欄除外の正解の件も、対応づけには加える（採点はしない）。こうすると、その件に当たるシステムの件を「余分」に数えない（Opus 確認 2026-10-20）。
3. **C1 読み落とし**: 当たるシステムの件が無い正解の件の数。ほかに、どの正解にも当たらなかったシステムの件の数を「余分」として別に数える。
4. **除外**: 正解の「除外」列が空でない件を次のように扱う。
   - 全欄除外の件は、採点に使わない。
   - 「A1」を含む件は、A1 を採点しない。
   - 「A2」を含む件は、A2・A3 を採点しない。
   - 値が `(除外)` か `対象外` の欄は、「答え無し」として数える。
   - 実際の値の書き方は gold_v1.tsv で確かめる。想定外の書き方があれば、止まって報告する。
5. **各項目の判定**: 「正しい／違う／答え無し」の3つで判定する。正答率は 正しい ÷（正しい＋違う）。
   - システムの値が `Error`・`FLAG_SINGLE`・空など正解の値に無いものなら「違う」とする。答え無しにはしない（Opus 確認 2026-10-20）。
   - **E1 行**: システムの行（`source_lines` があればそれを、無ければ line_start〜line_end の全行）が、必須の行（正解の lines）を全部含み、必須の行と許容する行の和からはみ出さなければ、正しい。
   - **E2 価格（Gemini 段）**: `raw_price` の数字だけを抜き出したものが、正解の E2 の数字だけと一致すれば、正しい。正解が `none` のときは、raw_price が空なら正しい。
   - **E2 価格（システム段）**: `price_normalized` を整数にしたものが、正解の E2 の数字と一致すれば、正しい。
   - **E3 数量**: E2 と同じ考え方で判定する。Gemini 段は `raw_quantity`、システム段は `quantity_normalized` を使う。
   - **A1 商品**: `product_id` が正解と一致すれば、正しい。
     - 正解が `未登録` のときは、product_id が空なら正しい。
     - 正解が `商品でない` のときは、システムの件の `exclusion` が空でなければ正しい。
   - **A2 状態**: `condition_canonical` が正解と完全に一致すれば、正しい。
   - **A3 単位**: `unit_canonical` が正解と完全に一致すれば、正しい。
   - **A4**: 正解を `在庫あり / 予約 / 売り切れ` から、システムの `status` の値に読み替えて比べる。
     - 読み替え表は、snapshot に実際に出てくる status の値を全部数えて作る（例: `In Stock / Pre-order / Sold out`）。
     - 表に無い値が1つでもあれば、止まって報告する。
   - **A5 発送日**: 両方を次のように整えてから、一致を比べる。
     - 前後の空白と、全角と半角の空白をすべて除く。
     - 括弧（【】()（））を除く。
     - 正解の `無し` は、ship_ja が空なら正しい。
6. **段ごとの数え方**
   - Gemini 段: 対応づけられた全件で、E1・E2(G)・E3(G) を採点する。
   - システム段: E1 が正しかった件だけで、A1〜A5・E2(S)・E3(S) を採点する。
   - 通し: 対応づけられた全件で、A1〜A5 を採点する。
   - 予約だけの行も別に出す。正解が「予約」の件で、A4 の正答率を求める。

## 4. 出力（--out-dir の中）

出力は全部、決まった並び順で書く。時刻・乱数・絶対パスは書かない。同じ入力なら sha256 が一致するようにする（KGI-3）。

- `result.tsv`: 列は `項目, 段, 正しい, 違う, 答え無し, 正答率`。正答率は小数第1位までの %。行は次のとおり。
  - E1・E2・E3 の Gemini 段（3行）
  - A1〜A5・E2・E3 のシステム段（7行）
  - A1〜A5 の通し（5行）
  - 予約の A4（1行）
  - C1 読み落とし（1行。件数）
  - 余分（1行。件数）
- `errors.tsv`: 違うと判定した件の一覧。列は `投稿id, price_line, 項目, 段, 正解, システム`。並びは投稿id・price_line・項目の順。社外秘なので、出力先は手元だけ。
- `inputs.sha256`: gold と snapshot の各ファイルの sha256。並びはファイル名順で、パスは --snapshot-dir からの相対にする。

## 5. テスト（test_score_v102.py、作り物データ）

最低限、次のテストを入れる。
1. E1 の判定（必須の行の不足／許容の行／はみ出し）
2. 対応づけ（同点・重なりの最大・1件は1回だけ）
3. 読み落としと余分の数
4. 除外の3種類
5. A4 の読み替え表に無い値で止まる
6. 必要な列が無いと止まる
7. out-dir がリポジトリの中なら止まる
8. 同じ入力を2回流すと、出力の sha256 が一致する

## 6. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| テストが全部通る | `python3 -m pytest scripts/accuracy -q` の出力（生ログはファイルに保存） |
| 本番の写しで2回流すと、result.tsv と errors.tsv の sha256 が一致する（KGI-3） | 2回の実行の後で `shasum -a 256` を2組取って比べる |
| result.tsv に9項目×段の行と、予約の行と、読み落としの行がある（KGI-4・5） | result.tsv の行を数える（18行＋見出し） |
| リポジトリに社外秘が混ざらない | `git diff origin/main...HEAD` に、gold・snapshot・投稿 id・仕入元名が0件であること（grep） |

## 7. 想定される分岐（止まる条件）

- （削除 2026-10-20: `is_current` で絞らないことにしたため不要）
- `source_lines` の書式が分からない → 実物の値を3つ示して止まる。
- 正解の除外列や A4 の値に、想定外の書き方がある → 止まる。
- 単位・状態の値の綴りが、正解と snapshot で揃わない（例: `Sealed box` と `Sealed Box`）→ 揃わない値の組を全部示して止まる。勝手に読み替えない。

## 8. 進め方

1. `bash scripts/new-worktree.sh` は使わない。今の作業場所 `release/accuracy-measurement-design` で、先に `git merge origin/main` を行う（`git -C` で。cd 禁止）。
2. 実装 → テスト → 本番の写しで1回目の測定（2回流す）を行う。出力先は `~/CC報告ファイル-keep/accuracy-gold-20261020/score/run1/` と `run2/`。
3. コミットは `git -C`。push と PR は Opus が行う。
4. 報告は DONE または BLOCKED: で行う。テストの生ログのパス、2回の sha256、result.tsv の中身（集計の数だけ。原文は書かない）を添える。
