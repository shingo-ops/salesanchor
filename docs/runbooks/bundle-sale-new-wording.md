# まとめ売りの新しい書き方を見つけたとき 運用 Runbook

対象: まとめ売り（N単位セット）の読み取り（ADR-1027）
関連コード: `backend/app/services/v102_bundle_svc.py`（`detect_bundle`）、`backend/app/services/line_analysis_v102_svc.py`（`_write_results` の `_apply_bundle`）
関連台本: `scripts/dev/bundle_replay.py`（本番データが要るため CI では走らない）
設計: `docs/handoff/bundle-sale/design.md`（§5-2・§12）

---

## 概要

仕入元の本文に「まとめで売っている」と書いてあるのに、まとめ売り（bundle_size）として読めず、要確認（例: bulk_price_basis_unknown）で止まる行を見つけたときの直し方。
規則は 1 か所（`detect_bundle`）だけで直す。画面ごとに別の読み方を作らない。区分で形を分けるときも、`detect_bundle` の引数（例: `bulk_shapes`）で分け、別の関数や別のファイルを作らない。

---

## やってはいけないこと

- 単位の語をコードに書く（単位の語は単位の別名マスタ line_unit_aliases が正本。`backend/tests/test_v102_bundle.py` が直書きを赤にする）。
- 新しいまとめの語の表を別のファイルに作る（まとめの語の置き場は `v102_bundle_svc.py` の `BUNDLE_WORDS`）。
- 仕入元の名前・本文をリポジトリ・PR に書く（生データは `~/CC報告ファイル-keep/` の下だけ）。テストには同じ形の作り文を使う。
- 区分で絞らずに新しい形を足す（2026-10-21 の試算では、「N種＋まとめの語」も含めて区分で絞らずに当てると全 35,846 行のうち 303 行が動いた。主に「N種」の形）。

---

## 手順

### 1. 数える（読み取りだけ）

1. 本番の行・単位マスタ・単位の別名マスタを、ADR-1024 の読み取りの道（`~/.ssh/salesanchor-reader`・SELECT のみ）で TSV に取る（列は台本の説明文のとおり）。置き場は `~/CC報告ファイル-keep/` の下。
2. 今の規則で当て直す:
   ```bash
   python3 -I scripts/dev/bundle_replay.py ALL_ROWS.tsv UNITS_Q3.tsv ALIASES_Q4.tsv OUT_DIR
   ```
3. 出力の summary.txt で、決まる・決まらない・当たらないの数を見る（設計 §12 の便1 の後は、バルク系／それ以外に分けた数も出る）。止まっている行の本文の形を、当たらない行から拾う。rows.tsv には本文が無いので、本文は ALL_ROWS.tsv と item_id で突き合わせて見る。

### 2. 設計の追記

1. `docs/handoff/bundle-sale/design.md` に追記の節を足す（形・候補にする条件・当てる区分・触るファイル・受入基準・維持の仕組み）。
2. 判定の写しを作り、全行に当てて「変わる行の固定一覧」を作る（変わる行・既存の bundle_size の行の変化・対象外の区分の変化を数える）。既存の行や対象外の区分が 1 行でも変わるなら、形を狭める。
3. 決まりを変えるときは ADR-1027 に追記の節を足し、`node scripts/generate-adr-index.js` を実行する。
4. 設計審査（Opus reviewer）と PO の承認を取る。

### 3. テスト

`backend/tests/test_v102_bundle.py` に、新しい形が決まる作り文・決まらない作り文・対象外の区分では当たらない作り文・過去の誤りの形（#9・#81・#42）が当たらない作り文を足す。`_write_results` を通す確認は `backend/tests/test_v102_bulk_price.py` に足す。

### 4. PR 本文に数を書く

PR の前に手順 1 の台本を新しい規則で当て直し、次の数を PR 本文に書く（ADR-1027「維持の仕組み」の決まり）:

- 決まる・決まらない・当たらない（バルク系／それ以外）
- 新しい規則で変わった行の数（固定一覧と同じか）
- 対象外の区分で変わった行の数（0 であること）

固定一覧と 1 行でも違えば止めて設計に戻る。

### 5. 本番の行を読み直す

コードが本番に出た後、変わる行を含む投稿だけを再解析する。前の値を全列保存し、必ず戻す試しで受入基準を照合し、書き戻しの SQL を先に用意する。実行の前に同意票で PO に確認する（ADR-1033）。再解析の最後に配信の予約が走るので、変わった行が次の配信で在庫表・シート版に出る。

---

## 見張り

2026-10-21 時点の基準値: 現行のバルク系 55 行のうち bulk_price_basis_unknown 21 行・bundle_unverified 0 行。
件数は毎週月曜 09:05 に管理者用 Discord へ自動で届く（backend/app/tasks/bundle_bulk_monitor.py、design §12-5 便3）。⚠️ のときや届かないときは手順1を人が回す。
