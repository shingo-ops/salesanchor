# 点検用（見るだけ）の役割から書き込みの権限を外す（1 回だけの画面操作）

本番の画面点検が使う役割を、設計どおり「見るだけ」に戻す手順と記録。

- 親の設計: [design.md](design.md) §5-2（:190「`*.view` だけを付ける」）・D3（:378「役割を見るだけに」）
- 見つけた経緯: docs/handoff/permission-keys-conditions-categories/design.md:50「点検用の役割が持つ書き込みの権限 20 件…別件として PO に聞く」
- 状態: PO 承認済み（2026-11-05 チャット「1」＝書き込みの権限を外す、同日チャット「1」＝SQL で外す）・本番反映済み（11:41 JST）・K1〜K3 合格（§8）

## 1. 目的と受入

| 基準 | 検証方法 |
|---|---|
| K1 テナント 001 の役割「点検用（見るだけ）」（role id 2611）が、下の §3 の 25 個を 1 つも持たない | 読み取りの道で role_permissions を数える。52 → 27、残りは §3 の「残す」27 個と一致 |
| K2 本番の画面点検（prod-ui-check）が全部通る | 操作から 300 秒以上あとに手で起動。S1〜S8 が passed、速さの記録で「測れなかった 0」 |
| K3 点検の 403 が増えない | 速さの記録の「403 が返った API」が操作前（2026-11-05 10:16 JST の回: 4 件）以下 |

## 2. 現在地（観測事実）

- 2026-11-05 10:45 JST 読み取りの道（AUDIT sha=660e389cad43 rows=52）: role 2611 は 52 個の権限を持つ。うち書き込み・出力・承認の権限が 25 個（§3）。
- 2026-11-05 10:46 JST 読み取りの道（AUDIT sha=1cb191d168be rows=1）: role 2611 を持つのは user 87 の 1 人だけ。user 87 はほかの役割を持たない。
- 点検は書き込みをしない:
  - tests/prod-check/page-speed.spec.ts:420-438: GET・HEAD・OPTIONS とログイン以外の送信は止める（abort または 409）。
  - tests/prod-check/prod-ui.spec.ts: 待つのは GET の返事とログインの POST だけ（:16・:82・:116）。
- 書き込みの権限だけで開ける読み取り（GET）の道は 0 本。origin/main ab8a6f725 の backend/app を構文で読み、require_permission を持つ GET 136 本を調べた。§3 の 25 個だけを求める GET は無い（reports.export を求める 2 本は reports.view でも通る: backend/app/routers/reports.py:77・:107）。

## 3. 外すもの・残すもの

外す（25 個）:
- 顧客: customers.create・customers.update・customers.delete
- 案件: deals.create・deals.update・deals.delete
- リード: leads.create・leads.update・leads.delete・leads.convert
- リードの Discord: leads.discord_invite・leads.discord_resync・leads.discord_remove_channel・leads.discord_kick・leads.discord_ban
- 注文: orders.create・orders.update・orders.delete
- レポート: reports.export・staff_reports.create・staff_reports.review
- チーム: teams.create・teams.update・teams.delete・teams.manage_members

残す（27 個）: archive.view・bots.view・channels.view・conditions.view・customers.view・dashboard.view・deals.view・erp.view・goals.view・invoices.view・leads.view・menu.dashboard・messaging.view・notifications.view・orders.view・product_categories.view・products.view・quotes.view・reports.view・roles.view・shifts.view・staff_reports.view_own・staff_reports.view_team・staff.view・suppliers.view・teams.view・tenant.profile.view

## 4. やり方

- 当初は役割の画面（https://app.salesanchor.jp/roles）で Opus が Chrome から外す案だった。2026-11-05 11:00 JST ごろ、25 個をまとめて外す画面の操作が自動の安全の判定に止められ、何も変わらなかった（直後の読み取りで 52 個のまま）。回り道はしていない。
- そこで PO が 2026-11-05 チャット「1」で「前夜と同じやり方（SQL・使い捨ての許可 2 回）」を選んだ。ADR-025 は開発段階のため手での書き換えを続けてよい（CLAUDE.md「データ手動 DB INSERT の原則禁止」）。
- 手順は前例 docs/handoff/discord-buttons-permission/data-change-1/README.md と同じ形:

| 段 | ファイル | 流す人 | 使う鍵 |
|---|---|---|---|
| 1 事前確認（読み取り） | role-view-only-fix/02_verify_read.sql | Opus | 読み取り専用の鍵 |
| 2 DRY-RUN（最後に巻き戻す） | role-view-only-fix/01_dryrun.sql | Opus（PO の使い捨て許可の後） | ssh 設定 prod1 の postgres コンテナの psql |
| 3 本実行 | role-view-only-fix/01_apply.sql | Opus（PO の 2 回目の使い捨て許可の後） | 同上 |
| 4 事後確認（読み取り） | role-view-only-fix/02_verify_read.sql | Opus | 読み取り専用の鍵 |

- 01 のガード: 役割 2611 が 1 つ・事前 52 個・25 組の id と名前が一致・消えたのがちょうど 25 行・事後 27 個で「残す」27 個と名前で一致・ほかの役割の行数は不変。1 つでも違えば止まり、何も残らない。
- 権限のキャッシュは最大 300 秒（ADR-1007）。K2 はそのあとに見る。

## 5. 代わりの案

| 案 | 採らない理由 |
|---|---|
| 役割の画面で外す（当初案） | 自動の安全の判定に止められた（§4）。PO が SQL を選んだ |
| PO が画面で外す | PO の手が 25 回要る。PO が選ばなかった |
| 役割を作り直す | user 87 の付け替えが要り、手順が増える |
| 今のままにする | 設計（design.md:190・:378）とずれ、点検の人の合言葉が漏れたときに書き換えられる |

## 6. リスクと戻し方

| リスク | 対処 |
|---|---|
| 点検が書き込みの権限に頼っていて落ちる | §2 で点検は書き込みをせず、書き込みの権限だけで開ける GET も 0 本。K2・K3 で確かめる |
| 外し漏れ・外しすぎ | K1 で残りの 27 個を名前で照合する |

戻し方: role-view-only-fix/09_rollback_apply.sql（事前 27 個・25 行を付け直し・事後 52 個のガード）。PO の使い捨て許可の後に流す。または同じ画面で 25 個のチェックを付け直して保存する。

## 外部・過去事例の参照と我々への応用

- 外部事例: 使わない。理由: 親の設計で決めた「見るだけ」に戻すだけで、新しいやり方を選ぶ判断を含まないため。
- 過去事例: 2026-11-04 の docs/handoff/discord-buttons-permission/data-change-1/README.md（同じ形の SQL・件数ガード・使い捨ての許可 2 回・前後の読み取り）。応用: 同じ順序と記録の形をそのまま使った。

## 維持の仕組み

- 今の守り: 点検は書き込みをしない（tests/prod-check/page-speed.spec.ts:420-438 が GET 以外を止める）。役割から書き込みの権限が無くなったので、点検の人の合言葉が漏れても書き換えはできない。
- まだ無いもの: 役割 2611 に書き込みの権限が再び付いたことを見つける機械の見張りは無い。新しい権限を足す作業（例: 2026-11-04 の Discord の 5 つ）で、既存の権限の持ち主へ写すと再び付きうる。
- 対処: 権限を写すデータ変更では、写す元から役割 2611 を外す。機械の見張りを作るかは PO に別に聞く（未決）。

## 7. 設計審査（自己審査・2026-11-05・同一 AI）

- 判定: APPROVE（設計合格）。
- 根拠: 親の設計の決定（見るだけ）に戻すだけで、新しい決定を含まない。影響する人は 1 人（点検の人）。点検の送信の全数（§2）と GET の全数（§2）を実物で確かめた。
- 未解決: なし。

## 8. 実行結果（実施後に記入）

| 項目 | 内容 |
|---|---|
| 画面操作（当初案） | 2026-11-05 11:00 JST ごろ 自動の安全の判定に止められ未実施。11:09 JST の読み取り（AUDIT ts=2026-11-05T02:09:18Z sha=660e389cad43 rows=52）で変化なし |
| DRY-RUN | 2026-11-05 11:40 JST 合格。PO の使い捨て許可（psql write・02:39:55Z 発行）の後に Opus が実行。01_dryrun.sql shasum 69193ec38fd4321e51ab7dfbe32d81372e0a4ca7。出力: `DO`、`NOTICE: before=52 deleted=25 after=27 other=365`、「残す」27 個を表示、`ROLLBACK`、`DRYRUN_OK`。直後の読み取り（AUDIT ts=2026-11-05T02:40:20Z sha=660e389cad43 rows=52）で 52 個のまま＝何も残っていない |
| 本実行 | 2026-11-05 11:41 JST（02:41:46Z）合格。PO の 2 回目の使い捨て許可（psql write・02:41:32Z 発行）の後に Opus が実行。01_apply.sql shasum 9ca4ae44f22a61077236ac4342434a67d04ea226。出力は DRY-RUN と同じ（`NOTICE: before=52 deleted=25 after=27 other=365`・27 個表示）、`COMMIT_NEXT`、`COMMIT`、`COMMIT_DONE` |
| K1 | 合格。11:42 JST の読み取り（AUDIT ts=2026-11-05T02:42:05Z sha=660e389cad43 rows=27）で 27 個。名前は §3 の「残す」27 個と全部一致 |
| K2・K3 | 合格。本実行から 380 秒あと（02:48:06Z）に prod-ui-check を手で起動（run 41957535303・main 63cadad・success）。S1〜S8 が 8 passed。速さの記録（11:51:14 JST）: 画面 135・測れなかった 0・「403 が返った API」4 件（inventory-visibility/matrix 2・buyback-prices/by-product 1・shipping/etd/images 1）＝操作前の 4 件と同数 |
