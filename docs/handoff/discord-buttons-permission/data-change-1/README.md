# 段階B-データ: Discord の 5 つの権限を足し、今と同じ役割に付ける（1 回だけのデータ変更）

本番の権限の一覧へ 5 行を足し、各社の役割へ写す手順と記録。設計は [../design.md](../design.md) §3。

## 目的
Discord の 5 つの操作（招待・再同期・チャンネルから外す・Kick・BAN）を、役割の画面で 1 つずつ付け外しできるようにする。
最初は「今と同じ人が同じボタンを使える」ように写す。誰のできることも変えない。
ADR-1007 の「1回だけのデータの変更」で行う。migration には書かない。

## PO 承認
- 分け方: PO 2026-11-04 チャット「3」（5 つに分ける）。
- 最初の付け方: 今と同じに写す（design.md §3-2。誰のできることも変えない）。
- 本実行: PO 本人が DRY-RUN と本実行のそれぞれについて `bash scripts/permit-danger.sh "psql write"` を実行する（未実施）。

## 実行の前提（順番を守る）
1. このデータの変更が先。コードの付け替え（../card-impl-2.md）はその後に main へ合流する。逆にすると、行の無い鍵をコードが求め、営業などが一時的に押せなくなる。
2. 事前確認が下の「想定」と一致すること。

## 順序
| 段 | ファイル | 流す人 | 使う鍵 |
|---|---|---|---|
| 1 事前確認（読み取り） | `00_precheck_read.sql` | Opus | 読み取り専用の鍵 `~/.ssh/salesanchor-reader` |
| 2 DRY-RUN（最後に巻き戻す） | `01_dryrun.sql` | Opus のみ（PO の使い捨て許可の後） | 無制限鍵（ssh 設定 `prod1`） |
| 3 本実行 | `01_apply.sql` | Opus のみ（PO の使い捨て許可の後） | 同上 |
| 4 事後確認（読み取り） | `02_verify_read.sql` | Opus | 読み取り専用の鍵 |

- 読み取りの道は ssh で `ubuntu@49.212.137.46` へファイルを標準入力で渡す。文字列 `'leads.update'`・`'leads.delete'` を書き込みの語として断るため、00・02 は id 14・15 で絞る（recon.md §7-2）。
- 書き込みは `prod1` の `astro-webapp-postgres-1` コンテナの psql（`-X -U jarvis -d jarvis_db -v ON_ERROR_STOP=1`）へファイルを標準入力で渡す。
- 流すのは、このコミットの中身そのまま。流す前に shasum を取り、下の記録に残す。
- `SET LOCAL app.is_operator = 'true'` を同じトランザクションで張る（permissions の RLS）。各社の行の前に `set_config('app.tenant_id', …, true)` も張る（role_permissions の RLS: migrations/003_add_phase1_tenant_tables.sql:199-205）。

## 想定
| 項目 | 事前（2026-11-04 22:19 JST 実測・AUDIT sha=0da6dd665f2d） | 事後の想定 |
|---|---|---|
| 一覧の件数 TOTAL | 130 | 135 |
| `leads.discord%` の行 | 0 | 5 |
| 001 の Discord の付与 | 0 | 22（更新 5 役割 × 2 ＋ 削除 4 役割 × 3） |
| 003・004・005・006 の Discord の付与 | 各 0 | 各 17（更新 4 × 2 ＋ 削除 3 × 3） |
| 写しのずれ（02 の `*_NE_*`） | 更新・削除を持つ役割の数（001: 5・4、他: 4・3） | すべて 0 |

違えば止めて、数え直してからファイルを直す。

事前確認の出力（00 の生出力）:
```
TOTAL	130
NEW_EXISTING	0
MAX_ID	53613
T001_UPD	5
T001_DEL	4
T003_UPD	4
T003_DEL	3
T004_UPD	4
T004_DEL	3
T005_UPD	4
T005_DEL	3
T006_UPD	4
T006_DEL	3
TENANTS	1:test-corp:true 3:perm-check-zzz:true 4:highlife-jpn:true 5:test-tenant-2:true 6:tenant-review:true
AUDIT ts=2026-11-04T13:19:09Z sha=0da6dd665f2d rows=14 ms=77 result=ok
```

## 戻し方
コードの付け替えを先に戻す（PR を revert して本番に反映）。その後で 5 行を消す。逆にすると、コードが求める鍵が無くなり、全員がボタンを押せなくなる。

| 段 | ファイル | 中身 |
|---|---|---|
| 戻し DRY-RUN | `09_rollback_dryrun.sql` | 5 行を消し、件数ガード（消した数 5・残り 0・全体 130）を通してから必ず ROLLBACK |
| 戻し本実行 | `09_rollback_apply.sql` | 同じ件数ガードが通ったときだけ COMMIT |

- 各社の付与の行は外部キーの ON DELETE CASCADE（backend/app/services/tenant.py:514）で一緒に消える。
- 削除にあたるため、PO の確認と使い捨ての許可が要る（DRY-RUN と本実行でそれぞれ 1 回）。
- 消したあとしばらくは、キャッシュに残った権限が使われる（最大 300 秒・ADR-1007）。

## 実行結果（実施後に記入）
| 項目 | 内容 |
|---|---|
| DRY-RUN | 未実施 |
| 本実行 | 未実施 |
| 事後確認 | 未実施 |
