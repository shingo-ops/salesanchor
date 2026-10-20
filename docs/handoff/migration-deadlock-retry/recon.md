# recon: 本番 deploy が migration の deadlock で止まる件

- 調べた日: 2026-10-20（origin/main 基準・git fetch 済み）。調査は Sonnet、判断と記録は Claude Opus。
- 生出力はリポジトリ外（/tmp/CC報告ファイル/deadlock315/）。

## 既存 ADR の検索
- `git grep -i "deadlock\|run_all_migrations\|実行済み" docs/adr/` と docs/adr/FEATURE-INDEX.md で探した。
- deadlock を主題にした ADR は無い。
- docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:23 によると、migration は全件を毎回流し直す設計で、実行済みを飛ばす仕組みは無い。
- docs/adr/ADR-1005-migration-run-once-ledger.md（Accepted）は、実行済みの台帳を作る方向を決めたもの。段階2（未実行のものだけを1回流す）はまだ実装されていない。scripts/run_all_migrations.sh に台帳の仕組みは無い。
- docs/adr/ADR-1024 は ai_ro ビューの扱いを決めたもの。scripts/run_all_migrations.sh:78-106 で、migration が失敗するとビューを外したままにする（fail-closed）。
- docs/handoff/dryrun-2pass/design.md:37 では、CI が全 migration を2周流す。2周目で失敗する migration は本番で安全でないとしている。

## 観測した失敗（deploy run、2026-10-14 03:53Z 以降の 300 件）
| run | 時刻(UTC) | 位置 | deadlock の相手 |
|---|---|---|---|
| 38927277793 attempt 1 | 2026-10-16 | 20261002_170000_drop_discord_inventory_tables | 再実行で success（docs/handoff/inventory-row-drawer/design.md:523） |
| 39078834651 | 2026-10-17 23:32:03 | [315/354] 同上 | public.suppliers ↔ public.products |
| 39187148522 | 2026-10-19 01:58:51 | [348/356] 20261017_120000_line_conditions_value_rank | public.conditions（ビュー）↔ public.line_conditions |
| 39361249082 | 2026-10-20 02:57:43 | [315/357] 20261002_170000_drop_discord_inventory_tables | public.suppliers ↔ public.products |

- エラー文はどれも `ERROR:  deadlock detected` だった。例は run 39361249082 のログの 5211-5214 行。
- deadlock は1回目には失敗するが、再実行では通っている。38927277793 は attempt 2 で success、39187148522 の後の deploy も success だった。

## 仕組み（実物）
- .github/workflows/deploy.yml:403-453 でコンテナを作り直して起動する。backend・celery-worker・celery-beat・discord-gateway が、migration の前に起動している。
- その後、.github/workflows/deploy.yml:563-577 で `bash scripts/run_all_migrations.sh` を流す。
  - つまり migration の最中も、DB を触るアプリが動いている。
- scripts/run_all_migrations.sh:61-66 の run_sql は、`docker exec -i ... psql -v ON_ERROR_STOP=1 < file` を1回流すだけ。
  - :20 の `set -e` により、最初の失敗でスクリプト全体が止まる。
  - 再試行の仕組みと lock_timeout は無い（grep で timeout|retry が 0 件）。
- 本番 DB の設定は、deadlock_timeout=1000ms、lock_timeout=0。
- 20261002_170000 で毎回 lock を取る理由
  - 20260604_120000_create_parse_logs.sql（:319）と、Python 経由で作る 059 の表（:187 migrate_inventory_sprint1.py:55）が、毎回作り直されている。
  - それを :903 で毎回消している。
  - parse_logs は suppliers・products に外部キーを持つ（migrations/20260604_120000_create_parse_logs.sql:4,6,8）。そのため、消すたびに参照先の表に強い lock を取る。
- 失敗すると、ai_ro ビューは次に deploy が成功するまで外れたままになる（scripts/run_all_migrations.sh:87-93）。
