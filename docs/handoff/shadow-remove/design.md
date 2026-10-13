# design: 試運転（shadow）の画面・仕組み・データを外す（段1a：コード／段1b：表）

- 状態: 設計案（Opus 作成・自己審査。コード審査は Fable）
- PO の決定（原文 2026-10-13）:
  - 依頼「要確認ページの試運転の確認待ちはもう使わないのでページも配線もDBも削除してくれ、詰まりと投稿のタブの使い方が不明」
  - 範囲の選択：「A（おすすめ）：『試運転の確認待ち』と『詰まり』のタブと、その裏の仕組みと、データの表と、『解析精度管理（新方式）』の画面を、まとめて消します。表を消すため、準備ができたら『GO #番号』をお願いします。」に対して「y」
  - 「完了したら２，３，４の順で対応を進めていく」
- 現在地: [recon.md](recon.md)（docs/handoff/shadow-remove/recon.md）
- 対象ADR: ADR-1004（llm_usage_events の line_extraction_shadow）、ADR-1007、ADR-1003（表を消す migration は PO 本人の GO が必要）、ADR-135・ADR-136

## 1. 目的
- 2026-09-30 に止めた試運転（shadow）の画面・API・書き込みの経路・データの表を外し、使われない配線を残さない。
- 「投稿」タブ（v102 の書き写しの直し）は残す。

## 2. 対象（外すもの）
- 画面：
  - 要確認のページの「試運転の確認待ち」タブ・「詰まり」タブと、そのキーワードの Modal（NeedsReviewTabsPanel.tsx）。
  - 「解析精度管理（新方式）」の画面と、サイドバーの項目（accuracy-management-v7）。
- API と service：
  - routers/tcg_shadow_review.py・services/tcg_shadow_review_svc.py
  - routers/tcg_shadow_accuracy.py・services/tcg_shadow_accuracy_svc.py・shadow_accuracy_signals.py
- 書き込みの経路：
  - tasks/tcg_extraction.py の shadow の呼び出し（EXTRACTION_SHADOW_ENABLED。本番は 0）
  - extraction_shadow_svc の shadow の実行部分
  - tools/shadow_backfill.py
- i18n の鍵・試験・CI の参照のうち、上の機能だけのもの。
- 段1b（GO の後）：表 extraction_shadow_results・extraction_shadow_runs。

## 3. 残すもの（壊さない）
- `load_product_entries`：本番の v102 が使う（gemini_raw_copy_v102_product_first.py:34,306）。
  - 関数の中身は変えずに、shadow と関係の無い置き場へ移す。候補は gemini_raw_copy_v102_product_first.py の中、または商品の照合の既存の service。
  - 呼び出し元を全部直し、元の場所に重複を残さない。
- llm_usage_events の行と、列 extraction_shadow_run_id：費用の台帳の履歴（345 行）。
- purpose 'line_extraction_shadow'：試験の道具の費用の記録で使っている。
- tools/prompt_ab.py：試験の道具で、指示書の試験（2026-10-12 の f_cv 等）に使う。
  - shadow の表に書く部分（:104-108）がある場合は、表を使わない形にする。台帳の記録は残す。
  - 判断に迷えば、止めて報告する。
- 「投稿」タブと、その API（tcg_v102_posts）。

## 4. 進め方
- 段1a（コードのみの PR）：上の §2 のうち、表以外を外す。表はまだ残す（読み書きする者が無くなる）。
- 段1b（migration の PR。PO の「GO #番号」が要る）：
  - 表を消す。
  - 毎回のデプロイで表が作り直されないように、scripts/run_all_migrations.sh の作成の登録（:843 付近）の扱いを、前例どおりに決める。
  - CI の参照（migration-test.yml・migration-guard.yml・dryrun-exclusions.tsv）を直す。
  - 前例（表を消す migration と、その登録の扱い・ADR-1002 の振り返り）を調べてから設計し、マージ前に PO の GO をいただく。
- そのあと、PO の指定どおりの順に進める。
  1. 2（読み込みの速さ）
  2. 3（表の1行）
  3. 4（スライド画面）

## 5. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 1. 要確認のページのタブが「本番の確認待ち」「投稿」だけになる | vitest・本番の bundle |
| 2. 「解析精度管理（新方式）」がサイドバーと経路から消える | vitest・grep |
| 3. v102 の解析が今までどおり（load_product_entries の移動で結果が変わらない） | 既存の v102 の試験が無修正で通る・本番の新しい投稿が done |
| 4. 外した API・関数への参照が残っていない | grep・tsc・pytest・CI |
| 5. 段1b：表が無くなり、デプロイで作り直されない | 本番の information_schema |

## 6. 危険と対処
- v102 を壊す：load_product_entries は中身を変えずに移し、v102 の試験で守る。
- 表を消すのは取り消せない：段1b は PO 本人の GO の後だけ。直前のバックアップを確かめる。
- 戻し方：段1a は revert。段1b はバックアップから戻す。

## 7. 維持の仕組み
- 守り手: v102 の既存の試験、CI（tsc・pytest・UI governance・migration 検査）。

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例：#4134（発注管理ページの削除。画面だけを先に外し、API・DB は残した）。今回は PO の指定により、段1b で表まで外す。
- 外部事例：該当なし。
