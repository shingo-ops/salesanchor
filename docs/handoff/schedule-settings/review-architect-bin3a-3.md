# 設計の審査（architect 第3回）: schedule-settings 便3a

- 審査した物: `origin/release/schedule-settings-bin3`（be9849ec7）の `docs/handoff/schedule-settings/design-bin3a.md`（設計）と `card-bin3a.md`（カード）
- 第2回の結果: `origin/release/schedule-settings-bin3a-review2` の `docs/handoff/schedule-settings/review-architect-bin3a-2.md`（R1・L1〜L6）
- 照らした実物: `origin/main` 314eeef1e（第2回と同じ。この版で `origin/release/schedule-settings-bin3` の分岐元と一致し、main の先行は 0 件: `git rev-list --count origin/release/schedule-settings-bin3..origin/main` = 0）
- 範囲: 読むだけ。製品のコード・DB・本番・secrets には触っていない。試験・検査は 1 本も流していない（下の事実はファイルを読んで確かめた物）

## 判定: REVISE

1. 第2回の R1 と L1〜L5 は設計に正しく入っている（下の表）。設計の行番号・命令・ファイル名は実物と合う。設計に直す所は無い。
2. カードの「触るファイル」「各変更」「確かめ」は設計 §3〜§5 とほぼ一致する。ただし、カードの手順 2 点（main の取り込み・台帳の commit）が、クラウドの決まり `scripts/agent-hooks/cloud/rules.md` と正面から食い違う（R1）。実装役はクラウドで動くので、1 手目で止まるおそれがある。
3. それ以外はカードだけにある追加（`stage1-column-class.tsv`）と言い回しの差で、作れなくなる物ではない（L1〜L3）。REJECT の理由は無い。

## 第2回の指摘が設計に入ったかの対応表（実物で照らした）

| 指摘 | 設計の場所 | 実物との照合 | 結果 |
|---|---|---|---|
| R1 `_REVIEWED` に既存 2 項へも足す | F10（`design-bin3a.md:60-64`） | `/home/user/salesanchor/backend/tests/test_tenant_loop_migration_guard.py:53`（`rls_bootstrap.py` の集合に便2b の名前）・`:74`（`test_calendar_sync_tenant_reset_pg.py` の集合に便2b の名前）が実在し、設計は「その隣に足す」「`:83` は触らない」「新しい試験ごとに 1 項（移行を流す物は `scoped`・文字として読むだけの物は `text_only` と理由）」と書く。`rls_bootstrap.py:190`・`test_calendar_sync_tenant_reset_pg.py:56` の便2b の行も実在する | 入った |
| L1 A5 の拾う場所の一覧 | §2（`design-bin3a.md:90`） | `schedule-owner.ts` は「10-11, 34, 45-46」に直っている。前回の実物の一覧（10・11・34・45・46）と一致。「応答キーは完全一致で確かめ、画面の試験に名前を書かない」の付記も入っている | 入った |
| L2 移行後の CHECK をひな形側と照らす | §5（`design-bin3a.md:195`）・カード変更8 | 「`format_type` が `text`・`pg_get_constraintdef` の鍵の並びが同じ部屋の `calendar_events_color_key_check` と同じ」を移行の試験に足した。カードも同じ（`card-bin3a.md:95`）。前回の指摘（`tenant.py:1607` は `calendar_events` の CHECK）に対し、比べる相手は同じ部屋の `calendar_events_color_key_check`（`tenant.py:1607`）で正しい。ひな形の `calendar_owner_settings` 自身の CHECK との照合は、カードの `test_owner_color_key_map.py`（`card-bin3a.md:96`）が「移行とひな形の CHECK の鍵が `tenant.py:1607` と同じ並び」を見るので、両方埋まる | 入った |
| L3・L5 会社を選ぶ文は 1 か所・1 行 | §3-1（`design-bin3a.md:98`）・カード変更1（`card-bin3a.md:45`） | 前例 `migrations/20261127_100000_add_calendar_team_share.sql:18` の形。`rls_bootstrap.py:171-172`・`:200-207` が数える形に合う。最後の確かめを同じループの中でやると明記 | 入った |
| L4・L6 | 記録のみ | 変更不要 | — |

## 設計の行番号・命令の再照合（origin/main 314eeef1e）

- `backend/app/services/tenant.py:1632`（登録コメント）・`:1649-1660`（`calendar_owner_settings`）・`:1599`・`:1607`（`calendar_events` の `color_key text` と CHECK）: 合う。
- `scripts/run_all_migrations.sh:1494-1495`（便2b のコメントと `run_sql`）、`:1498` が `mr_report_summary`。「`:1495` の次・`mr_report_summary` の前」は正しい。
- `migrations/20261024_100300_create_ai_cloud_views.sql:3`（「1169 行」）・`:381-382`（`color` mask・`share_mode` allow）、`backend/tests/ops/test_ai_cloud_views.py:486`（`== n0 == 1170`）: 合う。1170 − 2 + 1 = 1169 で、コメントの 1169 も整合する。
- `backend/app/routers/calendar.py`: `OwnerSettingsBody`（`:81-84`）・`OwnerRosterItem`（`:87` から）・`no_fields_to_update`（`:475`）・`_check_color_key`（`:115-120`。空文字を許す）は設計の記述と合う。設計が「空文字は 422」と別扱いにする理由も明記されている。
- `frontend/src/pages/schedule/ScheduleSettingsPage.tsx`: `type="color"` は `:426` の 1 か所、`settingsConnectedAt` の使用は `:476`、`categoryColorOptions` は `:325-328`、`renderOwnerRow` は `:418`。設計 §4-2 の置き換え先と合う。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:346`（共有行の組み立て）・`SchedulePageImpl.test.tsx:1939`・`ScheduleSettingsPage.test.tsx:348`・`schedule-owner.ts:34-35`: 合う。
- `frontend/src/components/ColorSwatchPicker.tsx:14`（`value: string | null`・「null はデフォルト」）・`:25-26`: 設計 §4-2 の「先頭の選択肢が `value: null`」は金型の仕様どおりに作れる。カードの停止条件「null の選択肢が作れない」は起きない。
- `locales/ja.json`・`en.json` に `shareTeam`（`:3598`）・`settingsConnectedAt`（`:3640`）が在る。設計 §4-4 の「`settingsConnectedAt` を消し `shareTeam` を残す」は実物と合う。
- 台帳の前例 `.claude-pipeline/active-work.d/release-schedule-settings-bin2b.md` は main に在る。

## カードと設計の突き合わせ

| 見る点 | 結果 |
|---|---|
| 触るファイルの一覧 | 設計 §3〜§5・F10・F11 の全ファイルがカードの 1〜13 にある。逆にカードにあって設計に無い物は 2 つ: `docs/handoff/cloud-case-ai/stage1-column-class.tsv`（L1）と台帳（R1・設計 §3〜§5 に無いが前例の運用）。設計の F10・F11 の物（`rls_bootstrap.py`・`test_calendar_sync_tenant_reset_pg.py`・`test_tenant_loop_migration_guard.py`・`openapi.json`・allowlist・`test_ai_cloud_views.py`）は全部カードにある |
| 各変更 | 変更1〜6 は設計 §3-1〜§4-4 と同じ。差は言い回しだけ（L2） |
| 確かめ | 設計 §2 の A1・A5・A7 の `git grep` を生のまま残す・A4/A6/A8/A9 を試験で見る、と対応する。A8 の「本番で前後の件数」はデプロイ後の確認でカードの範囲外。設計 A8 の本番側の確認はカードに無いが、実装役の仕事ではない（Opus のデプロイ後）ので食い違いではない |
| 停止条件 | 設計 §4-4 末尾の「en の空白を削る検査があれば止める」・§5 は変更6 に入っている。ColorSwatchPicker・openapi 差分・既存試験・main 衝突の停止条件も設計の各所と合う |

## R（直さないと作れない・壊れる物）

### R1 カードの「main の取り込み」と「台帳の commit」が、クラウドの決まりと食い違う（カード `card-bin3a.md:9`・`:23`・`:87-88`・`:117` を直す）

- 事実: `/home/user/salesanchor/scripts/agent-hooks/cloud/rules.md:15` は「main は取り込まない（取り込むと、PR の必須の点検が main の新しいファイルをこの枝で足したものと数えて落ちる）」「reset・rebase・force・merge・pull は使わない」と書く。カード `card-bin3a.md:9` は「始める前に `git merge --no-edit origin/main` で main を取り込む」と書く。`card-bin3a.md:117` の停止条件も「main の取り込みで衝突した」。
- 事実: `rules.md:12` は「`.claude-pipeline/active-work.d/` の登録ファイルは commit しない」。カード `card-bin3a.md:23`（触るファイル 13）・`:87-88`（変更7 の台帳）は、台帳 `release-schedule-settings-bin3.md` を新規に作る指示で、commit に含める流れ。
- 事実: 実物は今 main の先行が 0 件（上の `rev-list`）。実装時に main が進んでいなければ、取り込みは「Already up to date」で何も起きないが、命令そのものが見張りに止められるかは**未確認**（この審査では流していない）。止められれば実装役は 1 手目で BLOCKED になる。main が進んでいれば、決まりが禁じる合流の commit が増え、PR の必須の点検が落ちるおそれがある。
- 影響: カードの手順どおりにやると、クラウドの実装役は決まりと食い違う 2 つの命令の間で迷う（「迷わず作れるか」の基準に当たる）。
- 直し（カードだけ。設計は直さない）:
  - `card-bin3a.md:9` の「始める前に `git merge --no-edit origin/main` で main を取り込む」を、「`git switch -C release/schedule-settings-bin3 origin/release/schedule-settings-bin3` の後、`git rev-list --count HEAD..origin/main` を流す。0 でなければ main は取り込まず `BLOCKED:`（main が進んだので Opus が枝を取り直す）で返す」に差し替える。
  - `card-bin3a.md:117` の停止条件「main の取り込みで衝突した」を「main が先に進んでいた（上の件数が 0 でない）」に差し替える。
  - 台帳（触るファイル 13・変更7 の 2 つ目の点）は、(a) カードから外して Opus が PR の時に足す、または (b) 「クラウドの決まり `rules.md:12` により commit しない。台帳は Opus が足す」と明記する、のどちらかにする。前例の便2b の台帳は main に在るので、Opus が足す運用なら (a) が自然。

## L（軽い指摘）

- **L1 `stage1-column-class.tsv` は設計に無く、カードだけにある**（`card-bin3a.md:17`・変更4 の 2 つ目の点）。
  - 事実: `/home/user/salesanchor/docs/handoff/cloud-case-ai/stage1-column-class.tsv:579-580` は `calendar_owner_settings` の `color`（mask）・`share_mode`（allow）の 2 行で実在する。便2a の前例として `calendar_categories` の `color_key` 行（`:562`）がこの表に在る。
  - 事実: `git grep -n 'stage1-column-class' origin/main` が当たるのは `docs/` の文書だけで、`backend/`・`scripts/`・`.github/` からこの表を読む検査は見つからなかった。表は SQL の元の記録で、検査は無い。
  - 直し: 設計 §3-4 に「`docs/handoff/cloud-case-ai/stage1-column-class.tsv:579-580` の 2 行を消し、`color_key` の 1 行を同じ 6 列の形（型は `text`）で足す。検査は無いが、元の表を SQL に合わせる前例（便2a）に従う」と 1 行足す。設計とカードを揃えるための物で、足さなくても実装は壊れない。
- **L2 分類の説明文の言語が設計とカードで違う**。設計 §3-4（`design-bin3a.md:138`）は英語の `'values are limited by calendar_owner_settings_color_key_check'`、カード（`card-bin3a.md:69`）は日本語の `'値の決まり calendar_owner_settings_color_key_check で値が限られる'`。実物の `calendar_categories` の行（`stage1-column-class.tsv:562`）・`share_mode` の行（`create_ai_cloud_views.sql:382`）は日本語。カードが実物に合う。設計 §3-4 を日本語に揃えると、実装役は迷わない。
- **L3 理由の表の確認が「要るなら止めて報告」だけで、答えが書いていない**（`card-bin3a.md:60`）。実物では `backend/tests/test_api_error_reason_sync.py:73-76`（`test_table_codes_are_used_in_app`）は「表にあるコードがサーバーで使われているか」だけを見て、サーバーの新しい `detail` が表に無くても落ちない。したがって `invalid_color_key` を表に足さなくても試験は通る（読んだだけで未実行）。カードに「表への追加は要らない（逆向きの検査が無い）。画面の理由の文面を足したいなら別の便」と 1 行書くと、実装役が止まらずに済む。
- **L4 A8 の本番側の確認**（記録）。設計 A8 の「本番で t1・t4 の予定の件数を前後で数える」は、カードの範囲外（実装役ではなく Opus のデプロイ後）。カードに書く必要は無いが、設計 §11 かデプロイ後の手順に残すこと。

## 付記（事実と未確認）

- 試験・検査は 1 本も流していない。R1 の「見張りが `git merge` を止める」かは未確認（`rules.md:15` の文面と、`origin/main` が分岐元と一致していることだけが事実）。
- 本番の列の形・行数は、読む窓口を使っていないので未確認（設計 F2・A4 の記載のまま）。
