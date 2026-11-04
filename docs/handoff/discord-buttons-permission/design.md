# design: リードのカルテの Discord ボタンの出し分けと、Discord 操作の別権限

- 状態: 段階A 設計合格（自己審査）／段階B 草案（PO の決定待ち）
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

## 3. 段階B（別の権限）草案

### 3-1. 形

- public.permissions に新しい行を足す（category「リード」、description は日本語の文）。役割の編集画面は DB の description をそのまま出すので、画面のコードは変えない（recon §5-3）。
- サーバーの 5 本の道の鍵を、新しい鍵に付け替える。画面の出し分け（§2）も同じ PR で新しい鍵に変える。
- 所有者・システム管理者には、行を足すだけで届く（ADR-1007:48-51。最大 300 秒）。

### 3-2. PO に決めてもらうこと（1 件ずつ聞く）

1. 権限の分け方
   - 案1: 2 つ。「Discord に招待・再同期」と「Discord から外す・キック・BAN」。【推奨】止める操作は取り返しがつかないため、案内とは分ける。今の更新・削除の分け方と同じなので、移行で誰の権限も変わらない。
   - 案2: 1 つ。「Discord の操作」で 5 つ全部。わかりやすいが、営業に招待だけ許す形が作れない。
   - 案3: 5 つ。細かいが、役割の画面が長くなる。
2. 最初に誰に付けるか（分け方が決まった後に聞く）
   - 推奨: 今と同じ。招待・再同期は leads.update を持つ役割、外す系は leads.delete を持つ役割に付ける。誰のできることも変わらない。

### 3-3. データの変更（ADR-1007 に従う）

- 新しい行の追加と、§3-2 の 2 の役割への付与は、migration ではなく 1 回だけのデータの変更。docs/handoff/discord-buttons-permission/data-change-1/ に DRY-RUN と COMMIT の SQL と記録を残し、PO が `!` で流す。
- 順番: データの変更（行と付与）→ 反映を確かめる → コードの PR（鍵の付け替え）。逆にすると、行の無い鍵をコードが求め、見張り（permission_keys_missing）が 0 でなくなり、営業などが一時的に押せなくなる。

### 3-4. 受入（草案）

| 基準 | 検証方法 |
|---|---|
| B1 役割の編集画面の「リード」に新しい権限が出る | 001 で役割の画面を開いて目で見る |
| B2 新しい権限を外した役割では、ボタンが出ず、道が 403 | 試験（pytest・vitest）と 001 の点検用の役割での確認 |
| B3 移行の前後で、各役割のできることが同じ | データの変更の DRY-RUN の件数を recon §5-2 と照らす |
| B4 見張りの値が反映後も 0 | Grafana の salesanchor_permission_keys_missing |

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
- 段階B 判定: REVISE（PO の決定 §3-2 が要る）。
