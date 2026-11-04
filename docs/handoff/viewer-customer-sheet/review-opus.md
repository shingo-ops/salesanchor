# 設計審査 — 閲覧者管理ページを在庫解析ツールの顧客管理にする

> この文書は何か：設計書が実装に渡せる形になっているかを、設計者と同じ AI（Opus）がクラウドで起動した審査役で確かめた記録です。審査役は設計者と同じ種類の AI なので、独立した第二者の審査ではありません。

親: [design.md](design.md)・現状の記録: [recon.md](recon.md)

**日付**: 2026-11-04
**審査した人**: クラウドで一回実行した Opus の審査役（Architect 役。設計者と同一種の AI）。依頼の仕組みは RemoteTrigger（2〜4回目は trig_01B6txwLrN8RPfsf3vwE9x77）
**判定**: 1回目 REVISE（指摘9件）→ 2回目 REVISE（MEDIUM 2・LOW 5）→ 3回目 REVISE（MEDIUM 2・LOW 4）→ 4回目 APPROVE（LOW 1）→ LOW 1 を反映（f3bfd1db3）。PO 承認は 2026-11-04 チャットの「1」。どの判定も PO の実装承認・GO を兼ねない。

## 1. 審査の回ごとの記録

| 回 | 実行の番号 | 審査した版（HEAD） | 時刻（UTC） | 判定 | 指摘と対処 |
|---|---|---|---|---|---|
| 1 | 未記録（記録を残し忘れた。確かめられない） | 未記録 | 2026-11-04 | REVISE | 9件。2回目の審査役が「9件すべて直った」と確認 |
| 2 | cse_01W47tdeGEkiK1TbNuQe1JAE | 0fbeab195 | 10:04〜10:07 | REVISE | MEDIUM：AI 読み取りから隠す2つの一覧（ops_case.deny_tables・ai_cloud_meta.column_class）の書き場所が無い／管理 API の URL と応答の形が無い。LOW：理由の優先順・書いた後に get_target で読み直す・409 と 422 の分け方・テンプレートが無いときの 503・ja.json の行（:2805・:2816）。すべて 3回目までに反映 |
| 3 | cse_01W47tdifqvXjyGn1JXmU8Jn | e07b21c8c | 10:14〜10:16 | REVISE | MEDIUM：差し込み項目 form_url・form_expires／名簿の削除時に配信先のつなぎを NULL にする。LOW：ViewerTemplatesPage.test.tsx の行・DistributionTarget の入出力の型・甲の表の参照を :41 に・§5 の古い記述。2回目の L5 は一部だけ直っていた。すべて 4回目までに反映 |
| 4 | cse_01W47tdej8GaueNhQvWWSd4c | 95d5b5f98 | 10:21〜10:23 | APPROVE | LOW：分類表の件数。unnest で1列1行に展開されるため 1068→1075（mask 6＋allow 1）、ai_cloud_views.sql:3 のコメントも直す。f3bfd1db3 で反映 |

## 2. 4回目の LOW を反映する前に照合した事実（origin/main 基準）

| 設計の記述 | 照合先 | 結果 |
|---|---|---|
| 分類表は1列ごとに1行 | migrations/20261024_100300_create_ai_cloud_views.sql:14〜:16・:48（INSERT … SELECT … CROSS JOIN LATERAL unnest(v.cols)） | 一致。足す7列で7行 |
| 件数の試験 | backend/tests/ops/test_ai_cloud_views.py:484（== 1068） | 1075 に変える |
| 件数のコメント | 同 SQL の :3（「1068 行」） | 1075 に変える |
| 名簿の行の位置 | 同 SQL の viewer_accounts の行（:298〜:299 付近） | その後ろに足す |

## 3. 審査で確かめていないこと（実装のときに確かめる）

- 1回目の審査の実行番号と審査した版（記録が残っていない）。
- 3回目：T10 の分類漏れ検査（test_ai_cloud_views.py:490〜:530）の中身を、審査役は読んでいない。
- 4回目：backend/tests/test_viewer_purge.py の試験用 DB（pg fixture）に tcg_distribution_targets があるか。この fixture は test_tcg_work_matching_integration の pg を使い、migration を流す（test_viewer_purge.py:3・:18）ので、表はある見込みだが、まだ確かめていない。
- 4回目：.github/workflows/migration-guard.yml:224 の PUBLIC_TABLES の行の全文。

上の3件は実装カードの「実物点検」に入れ、実装役が着手前に確かめる。

## 4. 観点ごとの判定（4回目時点）

| 観点 | 判定 | 根拠 |
|---|---|---|
| データと配線を分散させない | 合格 | 名簿は viewer_accounts、請求先は1対1の別表、配信先は名簿を指す列だけ。配信の判定は list_targets と get_target の CASE 1か所 |
| 金型とトークン | 合格 | 既存の金型だけを使い、要るときは先に金型に登録する（design.md の §3 の画面の項）。フォームは TextField・Radio・Button・EmptyState で、金型にない部品は要らない。B2B 登録画面の直値と自作部品は写さない |
| 目標が○×で測れる | 合格 | §7 の受入条件の表に、確かめ方（試験・DB の数え方）がある |
| 範囲がはっきりしている | 合格 | 対象と対象外（§2）、ツールの請求書は別テーマ |
| 個人情報の扱い | 合格 | 請求先を AI 読み取りから隠す2つの一覧と、試験の件数（10→11・1068→1075）まで書いてある |

審査役の生の応答: 手元の控え /tmp/CC報告ファイル/viewer-design-review/（run2.txt・run3.txt・run4.txt・run4-check.txt）。個人名を含みうるため PR には載せない。

## 5. 設計の PR（#5121）の審査の LOW と、便2 カードで補ったこと（2026-11-04）

- LOW-1: card-bin1.md の「§5 手順7」は「手順6」（API の形を作り直す手順）の誤り。直した。
- LOW-2: ADR-1019:9・docs/specs/inventory-management/inventory-viewer/README.md:22・docs/handoff/gas-viewer-fresh-fast/design.md:70 の改訂を、どの PR で行うかが書かれていなかった。便2 カードの文書 PR（文書だけ）で改訂し、design.md §3-7・§5 にそう書いた。
- LOW-3: PR 本文に「PO の実装承認はマージ・本番反映の GO を兼ねない」の一文が無かった。便1 の実装 PR の本文から入れる。
- 補ったこと: 管理画面に請求先を出すには読む口が要るが、design.md §3-5 に書いていなかった。GET /api/v1/super-admin/viewers/{viewer_id}/billing-profile（super admin だけ・行が無ければ null）を design.md §3-5 と card-bin2.md §3-3 に足した。新しい表・新しい正本は増えない（読むのは viewer_billing_profiles の1か所）。
- 便2 カードの手順3（対象ファイルが基準 d948cf9c7 から変わっていないか）を 2026-11-04 に origin/main で流し、差分は空だった。
