# 実装報告: 配信シート15列（card.md の実行結果）

## 受領確認

- カード docs/handoff/dist-columns-product-id/card.md を受領。「やること」1〜10・「触らない」・「想定される分かれ道」のとおりに実行した。
- 作業場所: /root/worktrees/salesanchor/release-dist-columns-impl、枝 release/dist-columns-product-id（開始時の先頭 `8139477b1 docs: add ADR-1066 and implementation card for 15-column delivery sheet`）。
- 台帳: `bash scripts/ledger-lookup.sh release/dist-columns-product-id` の出力
  `| release/dist-columns-product-id | 配信シートの列を15列（PO指定の並び＋商品ID）に変える設計 | 2026-11-06 | IN_PROGRESS | | | PO実装承認済み(11/6「2」)。クラウドSonnetで実装 |`

## 変更

- backend/app/services/tcg_distribution_svc.py: `_SHEET_LAYOUT`・`DIST_HEADERS`・`_SHEET_COLUMNS`、`_cell`、`fetch_output_rows(columns=)`、`build_distribution_rows(columns=)`、`run_distribution` は `columns=_SHEET_COLUMNS`、`_GAS_COLUMNS` の注釈。
- 試験3ファイル: card の7・8のとおり。
- カードに書かれていない 1 点の修正: `backend/tests/test_distribution_rows_builder.py` の `test_builder_ok_returns_fetch_rows_as_is` が `fetch.assert_awaited_once_with(db, include_flag_single=False, max_age_hours=48)` だった。`build_distribution_rows` が `fetch_output_rows` に `columns=columns` を常に渡すようになるため、`columns=svc._GAS_COLUMNS` を足した（card 8 の指示どおり `fetch_output_rows` に渡す形。写し側の既定は 14列のまま）。

## 試験

- pytest は手元に入っておらず（`/usr/local/bin/python3: No module named pytest`）、pytest は流せていない。DB も無い。pytest の結果は無い（CI で確かめる）。
- 構文確認のみ: `python3 -m py_compile`（本体＋試験3ファイル）→ `COMPILE_OK`。
- commit 時の ruff: `All checks passed!`

## check-before-submit（生出力 /tmp/.../scratchpad/cbs.txt、終了コード 0）

```
== 提出前の検査（check-before-submit）==
比べる元: 2 点で比べる検査 = origin/main c481f5e7d66ca4f44e9619f47d397bf56371ac73 / 変更ファイルの一覧・3 点で比べる検査 = 分岐点 c481f5e7d66ca4f44e9619f47d397bf56371ac73
HEAD: 783738ecae70eb794a9bab4052a327731afb4a6d
変更ファイル: 11 件 / ログ置き場: /tmp/check-before-submit.Wb3Ov1

-- 速い組（毎回）--
  ○ check_doc_index --strict                            0.7 秒
  ○ check_rule_registry                                 0.2 秒
  ○ lint_tenant_schema (strict)                         1.7 秒
  ○ check-claude-size                                   0.1 秒
  ○ generate-adr-index --check                          0.2 秒
  ○ test-ui-governance                                  0.1 秒
  ○ check-ui-governance                                 0.0 秒
  ○ check-dangling-routes                               0.9 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.1 秒
  ○ migration-value-writes diff --check 8               0.0 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         4.5 秒
  - check-migration-column-churn                     関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            0.9 秒

-- 違反の見本（変更に関係するものだけ）--
  ○ 見本の選別（case.json）                      0.0 秒
  - 変更に関係する見本はありません（全件は --full で流せます）

-- 重い組（--full のときだけ）--
  - test-guard-evaluations (node --test)             CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    CI で確かめる（約 375 秒。--full で流せます）

（必須チェック一覧・流した検査一覧は省略せず同じ内容が出力されたが、上と重複のため末尾の行のみ転記）
合計 10.0 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.Wb3Ov1（消さずに残します）
結果: ○ 流した検査は全部通りました（終了コード 0）
```
