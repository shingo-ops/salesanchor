# ADR-1037: 入れ替え時の migration はロック待ちを1秒で諦め、間を空けて流し直す

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-21） |
| 備考 | PO 2026-10-21「1」で次の成功条件を承認：「アプリの入れ替え中に在庫表を開いても、1回の表示が2秒を超えない（作り替えの作業がほかを待たせるのは最大1秒まで）」「待たせ合いで入れ替えが失敗する回数を0にする（今は週4回）」。設計は PO の委任に基づき Opus が決定。 |
| 起案日 | 2026-10-21 |
| 方針の決定者 | Shingo（PO）＝成功条件。実現方法＝Claude Opus（委任） |
| 関連 | ADR-1005（毎回全件を流す作り。段階2で変わる）、ADR-1003（DROP を含む migration は委任 GO 対象外）、ADR-135、ADR-136 |
| 設計 | `docs/handoff/migration-lock-timeout/design.md`、現状 `docs/handoff/migration-lock-timeout/recon.md` |

---

## What（何を決めたか）

1. `scripts/run_all_migrations.sh` の run_sql で流す SQL は、接続ごとに `lock_timeout=1s` を付けて流す（`docker exec -e PGOPTIONS`）。DB・ロール全体には付けない。
2. "deadlock detected" と "canceling statement due to lock timeout" で落ちたファイルは、3秒あけて流し直す。1ファイル初回含め最大10回、1回の実行全体で再試行は合計40回まで。上限に達したら今までどおり止める。ほかのエラーは即停止。
3. 値の正本は run_sql の直前の4行（`SQL_LOCK_TIMEOUT` など）だけ。環境変数での上書きは試験のためで、deploy.yml・.env には書かない。
4. 挙動は `tests/sandbox/migration-run-sql-retry.sh`（本物の run_sql を抜き出して使い捨て DB で試す）で確かめる。run_sql を変えたらこの試験を流す。

## Why（なぜ）

- 入れ替えのたびに全 migration を流し直し（ADR-1005）、その中の `DROP TABLE IF EXISTS public.parse_logs` が FK 先の products に最強のロックを取りに行く。今はロック待ちに上限が無く、待っている間は後から来た在庫表の読み取りも全部止まる。試験用 DB の再現で、後から来た読み取りが 8912ms 待たされた。lock_timeout=1s では 1085ms で諦め、読み取りは止まらず、流し直しで 84ms で通った（`docs/handoff/migration-lock-timeout/recon.md` §4）。
- 本番では 10/19 の入れ替え中に在庫表の平均が最大 13.5 秒になり、deadlock で在庫表が 500 を返した。直近300回の入れ替えで deadlock による失敗が4件あり、4件とも run_sql 側だった（同 §3）。
- 回数と間隔は、移行ステップの打ち切り10分（ssh-action v1 の既定）と通常の所要最大138秒から決めた。最悪でも約300秒（5秒待ちの8ファイルが毎回上限まで待っても458秒）に収まる。
- PostgreSQL 公式文書は lock_timeout のサーバー全体設定を勧めていない。アプリの接続の挙動を変えないため、移行の接続だけに付ける。

## 対象外（この ADR では決めない）

- `SET LOCAL lock_timeout = '5s'` を持つ 8 ファイル（そのトランザクションの中では5秒待つ）。2本は DROP を含み、変えるには PO 本人の GO が要る。
- run_py（Python の移行）の接続。
- parse_logs を毎回作って消すこと（ADR-1005 の段階2で扱う）。

## 結果

- （反映後に、移行ステップのある入れ替え3回分の結果を追記する：失敗回数、"lock conflict; retry" と "retry limit reached" の回数、移行中に在庫表が2秒を超えた件数）
