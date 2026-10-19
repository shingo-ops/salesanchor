# ADR-1031 記録 SQL（本番未適用）

本番に流すのは Opus（担当は流さない）。順番は次のとおり。

| 順 | 作業 | 期待 |
|---|---|---|
| 0 | コード反映（PR マージ → デプロイ → migration `20261019_100000_line_conditions_value_group_add_promo_single.sql` 適用） | 行が無い間の判定は今と同じ |
| 1 | `01_precheck.sql` | PRECHECK_OK が 5 行（コード未使用 0・canonical 重なり 0・状態 16 行・区分なし 0・3 商品が区分 2 で 3） |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | INSERTED conditions 8・INSERTED category 1・UPDATED products 3・CHECK_OK conditions 24・CHECK_OK products 3。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 7 行 |
| 5 | 対象 job の再解析 | 設計 K1〜K5 を測る |

戻し: `04_rollback.sql`（ROLLBACK conditions 8・ROLLBACK products 3）→ 再解析。コードは PR を revert。

採番の根拠: 状態の code は CN0014 の次から CN0015〜CN0022（本番 16 行・最大 CN0014。CN2026… 形式の 2 行は別系列）。区分は code `PC_PROMO_PACK`、id は identity に任せる（現在の最大は 9）。読み取り結果は `/tmp/CC報告ファイル/adr1031/ro_conditions.tsv`・`ro_categories.tsv`・`ro_products.tsv`。
