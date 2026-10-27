# 使い道の分からない管理者2人を止めた記録

> この文書は何か：2段階の確認の対象を決める前に、使い道の分からない管理者2人を「止めた（消していない）」本番データ変更の記録です。

親: [../design.md](../design.md)

## 目的

- 2段階の確認を必須にする管理者を、使い道の分かる人だけにする（PO 決定 2026-10-27 原文「3」→「1」）。
- 対象: public.users の id 7（tenant 5 test-tenant-2 の管理者）と id 9（tenant 1 test-corp のオーナー）。docs に使い道の記載なし（../recon.md §4）。
- 中身: is_active を true から false にするだけ。行は消さない。止めた人はログインも既存トークンでの利用も 401（../recon.md §3）。

## 台本

| ファイル | 中身 | sha256 |
|---|---|---|
| read.sql | 読み取りだけ（前後の確認） | f94bba68b2b85ae40668251badb2a4c132cb89c3645e414598c14783f80267c9 |
| dryrun.sql | 本実行と同じ処理。最後が ROLLBACK | 1aba340368b051a210376e73a5a1a7b2174079a915f3d9be710775fb6b358e00 |
| deactivate.sql | 本実行。2行でなければ止まる（DO ブロックの件数ガード） | 5898371548f0c5734cdff9f5edcb08c7ca14f70c316337e30fa841c65337103f |
| rollback.sql | 戻し（2人を有効に戻す）。未実行 | 3f1567067ee78a6d87dc71cd6fdba2e85a0fd3a0f90db506f4bf45d52387e0f1 |

- users は FORCE RLS のため、`SET LOCAL app.is_operator = 'true'` を同じトランザクションで立てる。
- 道: 無制限鍵の ssh → `docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1`。実行の殻（apply.sh）はサーバーの宛先を含むため repo に置かない。殻は前後に read.sql を流し、全出力を run-log.txt に残す。

## 実行記録

| 項目 | 内容 |
|---|---|
| 許可 | PO の会話での決定（2026-10-27「1」）と、PO 本人の `!` 実行 |
| DRY-RUN | 2026-10-27T14:17:37Z・dryrun.sql（sha256 上表）・2行が false になり ROLLBACK・後の読み取りで true のまま |
| 本実行 | 2026-10-27T14:19:49Z・deactivate.sql（sha256 上表）・2行・COMMIT・NOTICE「OK: 2 rows set is_active=false」 |
| 事後の確認 | 同じ実行の後の読み取りで id 7・9 とも is_active=f、updated_at 2026-10-27 14:19:50.997229+00 |
| 有効な管理者の人数 | 5人 → 3人（2026-10-27 23:20 JST の読み取り。../recon.md §4） |
| ログ | [run-log.txt](run-log.txt)（全出力・68行） |
| 戻し | rollback.sql。未実行 |
