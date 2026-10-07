# 設計：値を書く migration の無効化 PR-3a（ADR-1007 段3）【雛形・設計担当（Opus）が記入】

この文書は何か（1行）: 毎デプロイで値を書き戻していた migration のうち、先に無効化できる 18 本を、構造だけ残して値の書き込みを止める変更の設計。

親: ADR-1007（PR #3985）。事実: docs/handoff/neutralize-value-migrations-3a/recon.md（実装の担当が記入済み）
状態: 実装済み（Draft PR）。この雛形のうち「（設計担当が記入）」の欄は設計担当が埋める。

## 1. 目的
（設計担当が記入）
参考の事実: 2026-10-05 02:38Z に、seed_product_marks が MEGAドリームex の mark を M3 に戻した。同じ種類の再実行が、上書き型 8 本・補充型 20 本で毎デプロイ届いている。

## 2. 現在地
docs/handoff/neutralize-value-migrations-3a/recon.md の §1・§2 を参照。ADR-155（migration で値を操作しない）に、既存の migration を寄せる変更である。

## 3. 変更（実装の担当が事実として記入）
- migrations/ の 18 本: 値を書く文だけを外し、DDL と存在確認は残した（recon.md §2 に、ファイル・行番号・外した文・残した構造を列挙）。
- backend/tests/test_value_migrations_neutralized.py（新規）: 静的な試験（18 本に値を書く文が無い）と、PG の試験（値を戻さない・消した行を再挿入しない）。
- 土台: 段2（PR #4015）を merge。#4015 より先にマージしない。後続: PR-3b（080・023・075・025・018・024・20260604_180000。#4012 のデプロイ後）。

## 4. 代替案と選んだ理由
（設計担当が記入）

## 5. リスクと対処
（設計担当が記入）
参考の事実: migrations/ を触る危険な PR（ADR-136）。マージには PO の「GO #番号」が要る。本番のデータは変わらない（外した文は、今の本番の値と同じ値を書いていた。value の比較は recon の元の記録による。上書き型 8 本は差 0）。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 無効化した 18 本に、値を書く文（INSERT・UPDATE … SET・DELETE FROM・ON CONFLICT）が残っていない | backend/tests/test_value_migrations_neutralized.py の静的な試験 |
| migration を流しても、国・集計ルールの値が元に戻らない | 同ファイルの PG 試験（CI の RLS_ADMIN_DATABASE_URL で動く） |
| 085・086 が、消した種別を再挿入しない。表は残る | 同ファイルの PG 試験 |
| 20260611_100000 のセレクタ行が変わっていない | 同ファイルの静的な試験、backend/tests/test_rls_bootstrap_ordering.py |
| 変更した migration が、CI で 2 回流れて通る | CI の Migration SQL Test と全件ドライラン（結果は未確認） |
| デプロイ後に、本番の updated_at が一斉に動かない | デプロイ後に、本番で max(updated_at)（countries、inventory_aggregation_rules）を読み取りで前後比較（未実施） |

## 7. 外部・過去事例の参照と我々への応用
（設計担当が記入）
参考の事実: 前例は PR #3544（2026-09-18。データだけの 13 本を無効化）。構造と値が混ざったファイルの前例は無い。

## 維持の仕組み
- 守り手: backend/tests/test_value_migrations_neutralized.py（無効化した 18 本に値を書く文が戻らないことを検出）と .github/workflows/migration-guard.yml（新しい migration による値の書き込みを検出。既存ファイルの書き換えは段4 で対象に広げる）。設計担当（Opus）が、PR-3b と段4 で確かめる。
- 対象: 値を書く文が、無効化した migration に戻ること。
