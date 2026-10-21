# 引継ぎ: 見つけたが手を付けていない件（2026-10-17 のセッションから）

このセッション（SMTP の文字欠け #4461・試し実行の失敗0本化 #4466・試し実行の強制化 #4476）の途中で見つけた件です。どれも未着手で、別のセッションに任せます。1件ずつ別の便として扱い、標準フロー（KGI→recon→design）から始めてください。

## 1. secrets の `$` 展開がほかの値にも起きていないか
- 事実: 本番 .env の SMTP_PASSWORD（途中に `$` を含む）が docker compose の変数展開で欠けていた。#4461 で deploy.yml の該当行だけ単一引用符にした。
- 未確認: deploy.yml が .env に書き出すほかの secrets に、引用符なし・二重引用符の行が残っているか。値に `$` を含むものがあるか（値は見ずに、`$` の有無と長さだけを数える）。
- 関連: 本番 .env:931 で変数 `s` が未定義という docker compose の警告（side4/REPORT.md「P5 本番反映」観測②）。同じ原因かは未確認。
- 注意: deploy.yml は危険パスなので、PO の「GO #番号」が要る。
- 便: docs/handoff/deploy-secrets-dollar-quote/design.md（完了: #4498 本番反映済み、K1〜K4 ○）

## 2. test_migration_value_writes.py を CI で動かす
- 事実: scripts/tests/test_migration_value_writes.py は、どの workflow からも呼ばれていない（docs/handoff/migration-dryrun-enforce/design.md:58）。
- 先に直すもの: test_protected_tables_include_the_four_added_masters が 28 != 27 で失敗している（#4476 より前の main の時点から）。
- 便: docs/handoff/migration-value-writes-test-ci/design.md

## 3. 試し実行の除外27行を実測で確かめる
- 事実: scripts/migration-guard/dryrun-exclusions.tsv にはデータ行が27行ある（コメント行を除く）。
- やること: #4466 と同じ方法で1本ずつ外して実測する。戻せるものは除外から外し、戻せないものは実測の ERROR を reason に書く（tsv:2-3 の規則）。
- 便: docs/handoff/dryrun-exclusions-remeasure/design.md

## 4. 20260919_030000 で、表がビューのとき外部キーが作られない
- 事実: 存在の確認が relkind を見ていない（VIEW でも真になる）。表がビューになっている環境では ALTER が飛ばされ、外部キーが作られない（side4/REPORT.md「P5」の欠陥②、design.md:60）。
- 今の本番には影響なし（素通りしている）。新しい環境を空から作るときに効いてくる。
- 注意: migrations/ を触るので危険パスになる。PO の「GO #番号」が要る。
- 便: docs/handoff/migration-fk-view-relkind/design.md（完了: 変更不要。relkind は #4446 で修正済み、空から作る環境でも本番でも外部キーあり）

## 根拠の置き場所
- ~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/REPORT.md
- docs/handoff/migration-dryrun-enforce/design.md「残り（別便）」
- docs/handoff/migration-dryrun-baseline/design.md

## このセッションに残したもの（引継ぎの対象外）
起きるのを待って確かめる4件は、agent-console の予約に登録した（purpose: measure）。
- P6 K1・K5（docs だけの反映）: 10/18 10:00
- SMTP の長さ（backend）: 10/18 10:30
- P6 K2（失敗の直後の反映）: 10/20 10:00
- P2（解析失敗の自動やり直し）: 10/20 10:30

## 維持の仕組み
守り手: この引継ぎ書を受け取ったセッション。1件を便として始めたら、その便の design.md にこの文書のパスを書く。4件すべてが便になったら、この文書は役目を終える。

## 外部・過去事例の参照と我々への応用
- 過去事例 #4466（docs/handoff/migration-dryrun-baseline/design.md）: 見込みだけで除外した migration が、後続を連鎖して落としていた。3 の除外27行も、見込みではなく実測で確かめる。
- 外部事例は使わない（理由: 引継ぎだけの文書で、設計判断を含まないため）。
