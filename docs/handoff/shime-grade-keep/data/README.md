# 便1 状態の辞書に「切れ込み」を足す SQL（本番未適用）

カートンの傷みの状態（line_conditions id 13・code CN0002・Damaged case）の search_kw の末尾に `,切れ込み` を1語足す。コードは変えない。本番に流すのは Opus（担当は流さない）。足す先は PO の選択（2026-11-14「1」＝傷みのあるカートン）。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql`（読み取り専用の道で1文として流す） | PRECHECK 行が1行: id 13・CN0002・Damaged case・app_kubun 箱系大・「切れ込み」を含む行が0。KIREKOMI_LINES が 2（直近180日の原文で「切れ込み」を含む行。設計 K2） |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | UPDATED 1・CHECK_OK 1、最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ、COMMIT |
| 4 | `03_verify.sql`（読み取り専用の道） | VERIFY 行が1行: 「切れ込み」を含む行は id 13 だけ。search_kw の末尾が `,切れ込み` |

戻し: `04_rollback.sql`（ROLLBACK 1）。状態の辞書は解析のたびに読み直される（`backend/app/services/tcg_analyzer_svc.py` の `load_condition_entries` は毎回 `public.conditions` を読む。`public.conditions` は `public.line_conditions` の VIEW：`migrations/20261017_120000_line_conditions_value_rank.sql:47`）ので、再起動は要らない。過去の解析結果は変えない（再解析しない）。
