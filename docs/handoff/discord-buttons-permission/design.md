# design: リードのカルテの Discord ボタンの出し分けと、Discord 操作の別権限

- 状態: 段階A 設計合格・本番反映済み／段階B 設計合格（自己審査）・データの変更とコードは未着手
- 根拠: docs/handoff/discord-buttons-permission/recon.md、ADR-091、ADR-1007、docs/handoff/permission-keys-conditions-categories/design.md §11-6
- 作成: 2026-11-04 Claude Opus（設計担当）。同一 AI の自己審査であり、独立した第二者レビューではない。

## 1. 目的（PO の言葉）

> 別途権限として付与できるようにするまず見えないように1

- 段階A: 押しても断られる Discord のボタンを、その権限の無い人には見せない。
- 段階B: Discord の操作を、リードの編集・削除とは別の権限として、役割ごとに付けたり外したりできるようにする。

## 2. 段階A（画面だけ）

### 2-1. 変更前後

| ボタン | 変更前 | 変更後（見える条件） | サーバーの鍵（変えない） |
|---|---|---|---|
| チャンネル招待 | 誰にでも出る | leads.update を持つ人だけ | leads.update（recon §4） |
| ロール再同期 | 誰にでも出る | leads.update を持つ人だけ | leads.update |
| チャンネルから外す・キック・BAN | 誰にでも出る | leads.delete を持つ人だけ | leads.delete |
| ロール同期の状態の文字 | 誰にでも出る | 変えない（誰にでも出る） | — |

画面の条件はサーバーの鍵と同じ文字列。出し分けの正本はサーバーの鍵で、画面はそれを読むだけ（DB の写しを作らない）。

### 2-2. 実装（file:line は origin/main 7d56ab771）

`frontend/src/pages/inbox/InboxKartePanel.tsx` の 1 ファイルと、新しい試験 1 ファイル。

1. KarteTabContent（:464-475）の `const { t } = useTranslation();` の次の行に `const { hasPermission } = usePermissions();` を足す。usePermissions は :17 で読み込み済み。写しの置き場を共有するので通信は増えない。
2. :532-535 のチャンネル招待の条件の先頭に `hasPermission("leads.update") &&` を足す。
   - 前: `{leadDetail.discord_guild_channel_id && (... Small/Large ...) && (<ChannelInviteButton .../>)}`
   - 後: `{hasPermission("leads.update") && leadDetail.discord_guild_channel_id && (... Small/Large ...) && (<ChannelInviteButton .../>)}`
3. :537-539 の外す/キック/BAN の条件を `{hasPermission("leads.delete") && leadDetail.discord_user_id && (...)}` にする。
4. RoleSyncStatusRow（:875-877）に引数 `canResync: boolean` を足す。:920-926 の再同期ボタンを `{canResync && (<Button ...>...</Button>)}` で囲む。状態の文字（:908-918）と結果の文字（:927-928）は変えない。
5. :541-546 の呼び出しに `canResync={hasPermission("leads.update")}` を足す。
6. 試験 `frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx` を新しく作る。usePermissions の差し替えは `frontend/src/features/secretary/SecretaryChat.test.tsx:35-37` と同じ形。KarteTabContent が export されていない場合は、export を足さずに InboxKartePanel 経由で描く。それが重いときは、KarteTabContent に `export` を 1 語足すことを許す（他の変更はしない）。
   - T1: 権限なし → 招待・再同期・外す・キック・BAN の 5 つの文字が無い。状態の文字は在る。
   - T2: leads.update だけ → 招待・再同期は在る。外す・キック・BAN は無い。
   - T3: leads.update と leads.delete → 5 つとも在る。
   - ボタンの文字は ja.json の既存の鍵（leads.discordRoleResync など）を t() 経由で引く。試験の中に日本語を直書きしない。

### 2-3. 触らない範囲

- backend・DB・migration・i18n の辞書・CSS・部品（Button など）。新しい見た目は作らない（隠すだけ）。
- ChannelInviteButton・DiscordRemoveButtons の中身。
- :257 の canMerge など、ほかの出し分け。

### 2-4. 受入（○×）

| 基準 | 検証方法 |
|---|---|
| A1 権限なしの人に 5 つの操作ボタンが出ない・状態の文字は出る | 試験 T1（CI の vitest） |
| A2 leads.update だけの人（営業）は招待・再同期だけ出る | 試験 T2（CI） |
| A3 両方を持つ人（所有者など）は 5 つとも出る | 試験 T3（CI）と、反映後に 001 の所有者で Chrome で開いて目で見る（Discord の設定があるリードが 001 に無ければ、試験だけで判定し、その旨を記録） |
| A4 変更が 2 ファイルだけ | `git diff origin/main...HEAD --name-only` |
| A5 CI が全部緑 | PR の checks |

### 2-5. リスクと対処

| リスク | 対処 |
|---|---|
| 権限の読み込み中（loading）に一瞬ボタンが消えている | 読み込み中は「無い」扱いで隠れる。押せないボタンを一瞬出すより安全。表示は 1 回の通信のあと出る |
| 営業が外す・キック・BAN を使えなくなったと感じる | 今も押すと断られている（recon §4）。できることは変わらない |
| 画面とサーバーの鍵がずれる | 段階Bで鍵を変えるときは、画面とサーバーを同じ PR で変える（§3-4） |

### 2-6. 戻し方

PR を revert する。DB は変えない。

## 3. 段階B（別の権限）

PO の決定: 2026-11-04 チャット「3」（5 つに分ける）。調べた事実は recon.md §7。

### 3-1. 新しい鍵（public.permissions に 5 行。category はすべて「リード」）

| 鍵 | ボタン | 今の鍵（付け替え前） | 役割の画面に出る文（description） |
|---|---|---|---|
| leads.discord_invite | チャンネル招待 | leads.update | Discord 専用チャンネルへの招待 |
| leads.discord_resync | ロール再同期 | leads.update | Discord ロールの再同期 |
| leads.discord_remove_channel | チャンネルから外す | leads.delete | Discord 専用チャンネルから外す |
| leads.discord_kick | Kick | leads.delete | Discord サーバーからの退出（Kick） |
| leads.discord_ban | BAN | leads.delete | Discord からの永久追放（BAN） |

- 役割の画面（frontend/src/pages/roles/RolesPage.tsx）は DB の category で束ね、description をそのまま出す（recon §7-4）。「リード」は既にあるので、画面のコード・アイコン・辞書は変えない。
- 所有者・システム管理者は、行を足すだけで 5 つとも届く（ADR-1007。最大 300 秒）。

### 3-2. 最初に誰に付けるか（今と同じに写す）

- 招待・再同期は、今 leads.update を持つ役割に付ける。外す・Kick・BAN は、今 leads.delete を持つ役割に付ける。
- 誰のできることも変わらない。だから PO に別の判断を求めない（§3-2 草案の推奨どおり）。分け直しは、反映後に PO が役割の画面で自由にできる。
- 001 の「点検用（見るだけ）」の役割（id 2611）も今 update・delete を持つので、そのまま写す（recon §7-6）。

### 3-3. データの変更（ADR-1007 に従う。migration にしない）

- 置き場: docs/handoff/discord-buttons-permission/data-change-1/（README・00〜02・09）。
- 1 つのトランザクションで、5 行を足し、5 社の役割へ写し、件数と写しのずれ 0 を DO ブロックで確かめる。違えば止まる。
- 想定: 一覧 130→135。付与 001 は 22、003・004・005・006 は 17 ずつ（合計 90）。写しのずれはすべて 0。
- 新しく作られる会社の役割は DEFAULT_ROLES（backend/app/services/tenant.py:50-185）で決まる。既存の会社には届かない（seed_system_roles は非システムの既存役割を上書きしない。tenant.py:1600-1655）ため、コードの PR で DEFAULT_ROLES にも足す。

### 3-4. コードの変更（card-impl-2.md）

- サーバー: 5 本の道の鍵を新しい鍵に付け替える（discord_channel_invite.py・discord_role_resync.py・discord_remove.py の 3 本）。
- 画面: カルテの出し分けを新しい鍵に変える。外す系の 3 つは 1 つの部品にまとまっているので、部品にボタンごとの可否を渡す。
- DEFAULT_ROLES: マネージャーに 5 つ、営業に招待・再同期の 2 つ（今の update・delete の持ち方と同じ）。
- 試験: 道の鍵（pytest C5 の書き換えと C6 の追加）、既定の役割（pytest）、ボタン（vitest T1〜T4）。

### 3-5. 順番（逆にしない）

1. データの変更（DRY-RUN → 本実行 → 事後確認）。
2. コードの PR を main へ合流し、本番に反映する。
3. 001 で Chrome の目視（B1・B6）。

逆にすると、行の無い鍵をコードが求め、営業などが一時的に押せなくなり、見張り（salesanchor_permission_keys_missing）が 0 でなくなる。

### 3-6. 受入（○×）

| 基準 | 検証方法 |
|---|---|
| B1 役割の画面の「リード」に 5 つの文が出る | 001 で役割の画面を開いて目で見る |
| B2 各鍵が自分のボタンだけを出し、鍵の無い道は 403 | vitest T4（5 通り）と pytest C6（道ごとの鍵） |
| B3 移行の前後で各役割のできることが同じ | 02_verify_read.sql の写しのずれがすべて 0、付与 22/17/17/17/17 |
| B4 見張りが反映後も 0 | Grafana の salesanchor_permission_keys_missing |
| B5 CI が全部緑 | PR の checks |
| B6 001 の所有者には 5 つとも出る | 反映後に Chrome で 001 のリードのカルテを開く（Discord のあるリードが無ければ試験 T3 で判定し、その旨を記録） |

### 3-7. リスクと対処

| リスク | 対処 |
|---|---|
| データとコードの順番を逆にする | §3-5。カードに「データの事後確認が合格するまで合流しない」と書く |
| 写し漏れで誰かが押せなくなる | DO ブロックが会社ごとに件数とずれ 0 を確かめ、違えば巻き戻る |
| 役割の画面が長くなる | 5 行増えるだけ。PO の選んだ分け方 |

### 3-8. 戻し方

コードの PR を revert して反映 → その後で data-change-1/09_rollback_*.sql で 5 行を消す（付与は ON DELETE CASCADE で一緒に消える。tenant.py:514）。逆にしない。

## 4. 外部・過去事例の参照と我々への応用

不要。理由: 権限が無い操作のボタンを隠すのは、この製品の既存の型（InboxKartePanel.tsx:257 の canMerge）と同じで、外の事例で決める点が無い。段階Bの分け方は PO の事業判断。

## 5. 維持の仕組み

- 守り手: frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx（CI の vitest・試験 T1〜T3）と backend/app/auth/permission_catalog.py（権限キーの見張り・Grafana の値）。人の担当は設計担当の Claude Opus。
- 段階Aの出し分けは試験 T1〜T3 が CI で毎回確かめる。
- 段階Bの鍵は、既存の見張り（backend/app/auth/permission_catalog.py と CI の試験 C2、本番の Grafana の値）が、コードの鍵と DB の行のずれを見つける。

## 6. 設計審査（自己審査・2026-11-04・同一 AI）

- 段階A 判定: APPROVE（設計合格）。
  - 確かめたこと: 5 つのボタンの行と、サーバーの 5 本の道の鍵を 7d56ab771 の実物で読んだ。5 社の役割の保有を本番の読み取りで確かめた。usePermissions が写しの置き場を共有し、通信が増えないことを実物で読んだ。i18n・部品・色の新設が無い（隠すだけ）。データの写しを作らない。
  - 未解決: なし。
- 段階B 判定: APPROVE（設計合格）。
  - 確かめたこと: PO の決定「3」。5 本の道の鍵と画面の 3 か所を 89d3320ed の実物で読んだ。本番の読み取りで、一覧 130 行・新しい鍵 0 行・5 社の update/delete の保有を数えた（recon §7-2、事前確認 AUDIT 0da6dd665f2d）。02_verify_read.sql を変更前に流し、想定どおり付与 0・ずれ＝役割の数となることを確かめた（AUDIT c80c0e888af8）。役割の画面が category と description をそのまま出すこと、CI の見張り（C2）が DB と照らさず本番の Grafana だけが照らすこと（よって順番はデータが先）を実物で読んだ。
  - 未確認: DRY-RUN はまだ流していない（PO の使い捨て許可が要る）。DRY-RUN の結果が想定と違えば、本実行もコードも止める。
  - 未解決: なし。
