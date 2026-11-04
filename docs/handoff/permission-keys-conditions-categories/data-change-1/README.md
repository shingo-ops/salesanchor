# 便1-データ: 権限の一覧に状態マスタ・商品カテゴリの 7 キーを足す（1 回だけのデータ変更）

この文書は、本番の権限の一覧へ 7 行を 1 回だけ足す手順と記録です。設計は [../design.md](../design.md) §4-2。

## 目的
コードが求めているのに権限の一覧（public.permissions）に無い 7 キーを足す。足すと、所有者・管理者が状態マスタと商品カテゴリの画面を開けるようになる（計算で届く。ADR-1007:48-51）。
ADR-1007:36 の「1回だけのデータの変更」で行う。migration には書かない。

## PO 承認
- 設計の作成: PO 2026-11-04 チャット「1」（2 つの鍵を権限の一覧に足す設計を作る）。
- 本実行の合意: 未（設計の審査のあと、PO に聞く）。

## 実行の前提（順番を守る）
1. 便1-コード（design.md §4-1）が main にマージされ、本番に反映されていること。取り込みの確定が閲覧キーで通る穴（recon.md §4）を先に塞ぐため。
2. 事前確認が下の「想定」と一致すること。

## 順序と実際のコマンド
SQL ファイルはどれもこのフォルダの中にある。リポジトリのルートで流す。

| 段 | ファイル | 流す人 | 使う鍵 |
|---|---|---|---|
| 1 事前確認（読み取り） | `00_precheck_read.sql` | Opus か担当（Sonnet） | `~/.ssh/salesanchor-reader`（読み取り専用の鍵） |
| 2 DRY-RUN（書き込みの形・最後に巻き戻す） | `01_dryrun.sql` | Opus のみ | `~/.ssh/manual-only/id_ed25519`（無制限鍵） |
| 3 本実行（書き込み） | `01_apply.sql` | Opus のみ | 同上 |
| 4 事後確認（読み取り） | `02_verify_read.sql` | Opus か担当（Sonnet） | `~/.ssh/salesanchor-reader` |

読み取り（00・02）:
```
ssh -F /dev/null -i ~/.ssh/salesanchor-reader -o IdentitiesOnly=yes -o BatchMode=yes ubuntu@49.212.137.46 < docs/handoff/permission-keys-conditions-categories/data-change-1/00_precheck_read.sql
```
- 02 も同じ形で、ファイル名だけが違う。
- 読み取りの道は SELECT を 1 文しか受けない。書き込みの語（create・update・delete）が文字列の中にあっても断られる（2026-11-04 実測「rejected: write keyword is not allowed」）。
- そのため 00 は resource と category で絞っている。

書き込み（01_dryrun・01_apply）:
```
ssh -o BatchMode=yes prod1 'docker exec -i astro-webapp-postgres-1 psql -X -U jarvis -d jarvis_db -v ON_ERROR_STOP=1' < docs/handoff/permission-keys-conditions-categories/data-change-1/01_dryrun.sql
```
apply も同じ形で、ファイル名だけが違う。
- 書き込みは Opus が流す。前提は、PO 本人が出した使い捨ての許可（`bash scripts/permit-danger.sh "psql write"`。1 回ごと・30 分で失効）。DRY-RUN と本実行で、それぞれ許可が要る。
- 流すのは、このコミットの中身そのまま。流す前後で shasum を取り、記録に残す。
- `SET LOCAL app.is_operator = 'true'` を同じトランザクションで張る（permissions の RLS: migrations/20261015_130000_add_permissions_rls.sql）。

## 想定
| 項目 | 事前（2026-11-04 09:18 JST 実測） | 事後の想定 |
|---|---|---|
| 一覧の件数 TOTAL | 123 | 130 |
| resource が conditions・product_categories の行 | 0 | 7 |
| category が 状態マスタ・商品カテゴリ の行 | 0 | 7 |
| id の最大 | 17859 | 17860 以上（DRY-RUN で連番が進むため、ちょうどの値は決めない） |

違えば止めて Opus に報告する。

事前確認の出力（00 を読み取りの道で流した生出力）:
```
k	v
TOTAL	123
NEW_EXISTING	0
CAT_EXISTING	0
MAX_ID	17859
AUDIT ts=2026-11-04T00:18:05Z sha=0594b6bae4cd rows=4 ms=127 result=ok
```

## 戻し方
7 行を消す。各社の role_permissions の行は外部キーの ON DELETE CASCADE（backend/app/services/tenant.py:514）で一緒に消える。点検用の役割に付けた 2 キーも消える。
| 段 | ファイル | 中身 |
|---|---|---|
| 戻し DRY-RUN | `09_rollback_dryrun.sql` | 7 行を消し、件数ガード（消した数 7・残り 0・全体 123）を通してから必ず ROLLBACK |
| 戻し本実行 | `09_rollback_apply.sql` | 同じ件数ガードが通ったときだけ COMMIT |
- 流し方は上の 01_dryrun・01_apply と同じ形で、ファイル名だけが違う。DRY-RUN の結果が ROLLBACK_DONE で終わってから本実行へ進む。
- 削除にあたるため、PO の確認と使い捨ての許可が要る（DRY-RUN と本実行でそれぞれ 1 回）。
- 全体 123 は便1-データの前の実測値。戻すまでに別の権限が足されていたら、ガードで止まる。そのときは数え直してからファイルを直す。
- 消したあと最大 300 秒は、キャッシュに残った権限で画面が開ける（backend/app/cache.py:19）。

## 実行結果（実施後に記入）
| 項目 | 内容 |
|---|---|
| DRY-RUN | |
| 本実行 | |
| 事後確認 | |
