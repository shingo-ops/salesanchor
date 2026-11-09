# 実装カード 便M: 受信箱の「手で会話を書き足す欄」を外す

> What this document is, in one line:
> Remove the manual conversation record feature (inbox input panel, the 4 lead conv-logs API routes, their tests and texts) while keeping the channel roster API and the company conversation tab. No table or data change.

- 親: design.md §便M（PO 2026-11-09「手動記録は廃止なのでK3不要」「便1.5 を先、手動記録の廃止の設計はその後」）。設計審査は design.md §10「便M」
- 基準: origin/main d1580a38b。行番号はすべて、この版で Opus が読んで確かめた（生の記録 /tmp/CC報告ファイル/conv/manual/card-facts.txt・revise-check.txt・cl-keep2.py）
- 本番の手の記録は5社とも 0 行（recon §8-8）。データの移し替えは無い
- ブランチ: このカードと同じ `release/conversation-unify-manual-removal`。クラウドで commit する前に `bash scripts/new-worktree.sh release/conversation-unify-manual-removal` で作業場所を作るか、既にある枝を checkout する
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする
  - Draft、`--base main`、`shingo-cc` 名義で起票する
  - `migrations/`・`deploy.yml`・本番 `scripts/` を含まないので、危険 PR ではない
  - マージと本番反映は担当が行わない

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- origin/main の次の行が、下の表の「基準の中身」と同じであること
  - 確かめ方の例: `git show origin/main:backend/app/routers/conv_logs.py | sed -n '192,202p'`
  - 1つでも違えば、BLOCKED: で差を返す

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `backend/app/routers/conv_logs.py:49` | `class ConvLogCreate(BaseModel):` |
| `backend/app/routers/conv_logs.py:83` | `async def _fetch_conv_log(` |
| `backend/app/routers/conv_logs.py:116` | `async def _fire_translation(` |
| `backend/app/routers/conv_logs.py:178` | `async def list_channel_masters(` |
| `backend/app/routers/conv_logs.py:202` | `async def create_conv_log(` |
| `backend/app/routers/conv_logs.py:450` | `async def delete_conv_log(` |
| `backend/app/realtime/topics.py:237` | `("POST", "/api/v1/leads/{lead_id}/conv-logs"): _PENDING,` |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:10` | `import { ManualRecordSection } from "./ManualRecordSection";` |
| `frontend/src/pages/inbox/InboxPage.tsx:235` | `onManualRecordSaved={state.reloadMessages}` |
| `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:114` | `{log.recorded_by_user_id && (` |
| `scripts/check-dangling-routes.js:44` | `'frontend/src/pages/inbox/ManualRecordSection.tsx',` |
| `frontend/scripts/error-text-next-action-baseline.json:107` | `"inbox.manualRecord.saveError",` |
| `backend/tests/error_detail_baseline.json:18` | `"app/routers/conv_logs.py": 10,` |

## 1. 事実（Opus が確かめたこと。担当は確かめ直さなくてよい）

- 手の記録の入口は受信箱の ManualRecordSection だけ。名簿で manual の窓口（今は WhatsApp だけ）を開いたときに出る。
- conv_logs.py は2つの役目を持つ:
  - 手の記録の API 4つ（作成 :192-326・一覧 :328-370・変更 :372-446・削除 :448-490）→ 外す。
  - 名簿の API（一覧 :165-190・追加・隠す・無効にする :492-614）→ 残す。
- 残す部分（名簿の API）で使う読み込み（Opus が数えた。cl-keep2.py）:
  - 使う: `Any`・`APIRouter`・`Depends`・`HTTPException`・`Query`・`status`・`BaseModel`・`Field`・`text`・`AsyncSession`・`get_current_tenant`・`get_current_user`・`require_permission`・`reset_tenant_context`・`set_tenant_context`・`get_db`・`User`・`channel_masters`・`record_audit_log`。
  - 使わない → 外す: `import logging`（:17）と `logger = logging.getLogger(__name__)`（:40。使うのは外す `_fire_translation` だけ）・`uuid`・`datetime`/`timedelta`/`timezone`（:19 の行ごと）・`field_validator`・`from app.services.conv_log_writer import ...`（:38 の行ごと）。
- `backend/tests/test_channel_masters_shared.py:31` は `app.routers.conv_logs.record_audit_log` を差し替える。`record_audit_log` は名簿の API が使うので残る。この試験は変えない。
- 文の数の見張り（test_error_detail_guard.py）が数える conv_logs.py の文は、外した後 4（:514・:558・:598・:603 の4か所。`not_found:` で始まる理由コードは数えない）。基準 10 を 4 に下げる。
- 会社の会話タブの「手動記録」の印は `log.recorded_by_user_id` があるときだけ出る。手の記録が無くなるので、印は出ない。

## 2. やること（この順）

1. クラウドの事前確認として、`git config user.name shingo-cc` と `git rev-parse --verify origin/main` を流す。どちらかが失敗したら BLOCKED: で返す。
2. §3 画面を外す
3. §4 API を外す
4. §5 試験を直す・足す
5. API の形の写しを作り直す: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`
   - 4つの道が消える差だけが出る見込み。ほかの道の差が出たら NEEDS_DECISION: で返す。
6. 型の写しを作り直す: `cd frontend && npm run generate:api-types`。差が出たら commit に含める。
7. §6 の検索を流す
8. commit して push する（`git -C <作業場所> push -u origin release/conversation-unify-manual-removal` を単独で）

## 3. 画面を外す

- `frontend/src/pages/inbox/ManualRecordSection.tsx` を消す（`git rm`）。
- `frontend/src/pages/inbox/InboxMessageThread.tsx`:
  - :10 の import を消す。
  - :71 の `onManualRecordSaved?: () => void;` を消す。
  - :103 の分割代入から `onManualRecordSaved` を消す（同じ行のほかの名前は残す）。
  - :864-871 の8行（:864 の注釈 `{/* SA-02 Stage 3: 手動記録入力（manual チャネルのみ表示） */}` と、`{selectedLeadId != null && ( <ManualRecordSection ... /> )}` の7行）を消す。前後の要素は変えない。
- `frontend/src/pages/inbox/InboxPage.tsx:235` の `onManualRecordSaved={state.reloadMessages}` の1行を消す。`state.reloadMessages` がほかで使われなくなっても、フックの側は変えない。
- `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:114-118` の手動記録の印（`{log.recorded_by_user_id && ( <span className="conv-log-manual-badge"> ... )}`）の5行を消す。
  - `.conv-log-manual-badge` の CSS がどこかにあれば、それも消す（`git grep -n conv-log-manual-badge -- frontend/src` で探す）。
  - 型の `recorded_by_user_id` は API が返し続けるので、型は変えない。
- 文言:
  - `frontend/src/locales/ja.json` と `en.json` の `inbox.manualRecord`（:1422-1434 の塊）を消す。
  - 同じ2つの `companies.convHistory.manual`（:1258）を消す。前の行の末尾のカンマを JSON として正しく直す。
  - ほかの `"manual"`（:2892 の sendMode・:3212 の source）は**別物。触らない。**
- `frontend/scripts/error-text-next-action-baseline.json:107` の `"inbox.manualRecord.saveError",` の行を消す。
- `scripts/check-dangling-routes.js:44` の `'frontend/src/pages/inbox/ManualRecordSection.tsx',` の行を消す（:43 の ChannelMastersPage は残す）。

## 4. API を外す（`backend/app/routers/conv_logs.py` ほか）

- conv_logs.py:
  - :1-14 の説明を「連絡手段の名簿の API」に書き直す。残すエンドポイント（GET /channel-masters、POST /admin/channel-masters、PATCH 隠す、DELETE 無効にする）を並べる。`手動会話ログ` の語は残さない。
  - §1 の「使わない」読み込みを外す。
  - :49-66 の `ConvLogCreate`・`ConvLogUpdate` を消す。`ChannelMasterCreate`・`ChannelVisibilityUpdate` は残す。外した後の Models の見出し（:44-46）は残す。
  - :78-166（Helpers の見出しと `_fetch_conv_log`・`_fire_translation`）を消す。:168 からの名簿の一覧の見出しは残す。
  - :191-490（作成・一覧・変更・削除の4つと、それぞれの見出しの注釈）を消す。:168-190 の `list_channel_masters` と :491- の名簿の API（`create_channel_master`・`update_channel_master_visibility`・`deactivate_channel_master`）は1文字も変えない。
- `backend/app/main.py:43`（`    conv_logs,  # SA-02 Stage 3: 手動会話ログ CRUD`）の注釈を `# 連絡手段の名簿 API` に替える。:730 の `include_router` は残す（名簿の API が載っている）。
- `backend/app/realtime/topics.py:237-239` の conv-logs の3行を消す。
- `backend/tests/error_detail_baseline.json:18` の値を `10` から `4` にする。

## 5. 試験（手元で回さない。CI の結果を読む）

### 5-1. 消す

- `backend/tests/test_conv_logs_fire_translation.py` を丸ごと消す（`_fire_translation` を直接読み込む）。
- `backend/tests/test_conv_logs_router.py` から、手の記録の試験を消す:
  - :35・:71・:99・:137・:181・:221・:253・:293・:330・:502・:545・:589 から始まる12本（:501 より後ろの3本も消す）（`create_conv_log`・`update_conv_log`・`delete_conv_log` を読み込むもの）。
  - :372・:401・:427・:452・:477 から始まる名簿の5本は**残す**。
  - :21 の `_make_mock_result` は、残す5本が使っていなければ消す（使っていれば残す）。使わなくなった import も外す。
  - 冒頭の説明を名簿の試験に合わせて直す。

### 5-2. 書き換える `backend/tests/test_conversation_unify_bin1.py`

- 準備 `env`（:53-97）:
  - :76-87（`from app.routers import conv_logs as conv_logs_router`・`real_fetch`・`fetch_with_datetimes`）を消す。
  - :90-92 の conv_logs の差し替え3つを消す。:93 の `get_avatar_urls_batch` の差し替えは残す。
  - 説明を「meta_messages の試験の準備」に替える。
- 消す: `_record_manual`（:125）と、手の記録の API を使う6本（:143・:165・:181・:206・:224・:266 から始まる試験）。
- 残す: :286 `test_phone_manual_record_is_not_counted_for_language`（直接 INSERT で、言語判定の除外 is_manual を確かめる）。
- 書き換えて残す: :312 `test_priority_scoring_label_skips_manual_record`。
  - `_record_manual(client, ...)` の行を、:290-296 と同じ形の直接 INSERT（`is_manual` = 1、`platform='phone'`、`message_id='manual_label_1'`、`message_text='電話で価格を確認'`、`occurred_at` と `created_at` を同じ `'2026-06-02 10:00:00'`。priority_scoring.py:274 が created_at で並べるため）に替え、`await env.commit()` を足す。期待（ラベルが自動の行だけ）は変えない。
- :330 以降（webhook・Discord・migration の試験）は変えない。
- 冒頭の説明（:1-16）の 1〜6 と :45 の注記を残る試験に合わせて直し、7・8 の説明を「手の記録の行（直接入れたもの）が言語判定・ラベル付けに入らない」に直す。
- 使わなくなった import（`timedelta`・`timezone`・`datetime` など）は ruff の指摘どおり外す。`# noqa` は付けない。

### 5-3. 足す（新しい `backend/tests/test_conversation_unify_binM.py`）

| # | 試すこと | 期待 | 基準 |
|---|---|---|---|
| 1 | `POST /api/v1/leads/1/conv-logs` | 404 か 405 | M2 |
| 2 | `GET /api/v1/leads/1/conv-logs` | 404 か 405 | M2 |
| 3 | `PATCH /api/v1/leads/1/conv-logs/1` | 404 か 405 | M2 |
| 4 | `DELETE /api/v1/leads/1/conv-logs/1` | 404 か 405 | M2 |
| 5 | アプリの道の一覧（`app.routes`）に `/conv-logs` を含む道が無い | 0 件 | M2 |
| 6 | `GET /api/v1/channel-masters` が今までどおり道の一覧にある | 1 件 | 残すもの |

- 1〜4 は conftest の `client`（ログイン済み）で投げる。認証で 401/403 になる場合は、ログイン済みの client を使っているか確かめる。それでも 401/403 なら NEEDS_DECISION: で返す。
- 新しい試験の関数名・説明に、§6 の M5 で探す語（create_conv_log など）を入れない（入れると M5 が0件にならない）。
- 新しい試験ファイルが登録を要る見張り（`test_tenant_loop_migration_guard` 等）に当たったら、その指示どおり登録する。

## 6. 終わったときの検索（PR の枝で流し、結果を PR 本文に貼る）

```bash
# M5: 外したものの名前（0件）
git grep -n -E "ManualRecord|manualRecord|create_conv_log|list_conv_logs|update_conv_log|delete_conv_log|ConvLogCreate|ConvLogUpdate|_fire_translation|_fetch_conv_log" -- backend/app backend/tests frontend/src frontend/scripts scripts
# 手の記録の道（0件。openapi.json も含む）
git grep -n "/conv-logs" -- backend/app frontend/src frontend/api-contract scripts
# 名簿の API の4関数が残っている（4件）
git grep -n -E "def (list_channel_masters|create_channel_master|update_channel_master_visibility|deactivate_channel_master)\(" -- backend/app/routers/conv_logs.py
# 会社の会話タブの印（0件）
git grep -n "conv-log-manual-badge" -- frontend/src
```

- 4件にならないときは BLOCKED: で `git grep -n "^async def " -- backend/app/routers/conv_logs.py` の生の出力を返す。

## 7. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | BLOCKED: で差を返す |
| ruff が「使われていない」と言う import が §1 の外にある | 本当に使っていなければ外す。名簿の API が使うものなら残し、PR 本文に書く |
| test_error_detail_guard が「減った」「増えた」で落ちる | 出た数に合わせて baseline の conv_logs.py の行だけを直す。ほかの行が出たら BLOCKED: |
| i18n の検査（ja/en のキーの一致・使われていないキー）が落ちる | 出た指示どおり両方の JSON を直す。ほかの塊に及ぶなら BLOCKED: |
| api-contract-check が赤 | §2 の 5・6 の命令で作り直したか確かめる。手で openapi.json を直さない |
| 名簿の画面（ChannelMastersPage・ChannelTypeCombobox）の試験が落ちる | 名簿の API を変えていないか確かめる。変えていないのに落ちるなら BLOCKED: で生の出力 |
| e2e・画面の試験が手の記録の欄を探して落ちる | その試験の手の記録の部分だけを消す。ほかの期待は変えない。PR 本文に書く |
| §3〜§5 の外で手の記録を使う所が見つかった | 足さずに、NEEDS_DECISION: で場所を返す |
| 手元で試験を回したくなる | 回さない。CI の結果を読む |

## 8. 触らない

- `conversation_logs` の表と行、`meta_messages` の `is_manual` 列、既存の migration（便2・便3 の担当）
- 読む所の `is_manual` の除外（leads.py・meta_inbox.py・priority_scoring.py・translation_monitor.py・lang_judge）
- 名簿の API・名簿の画面（ChannelMastersPage）・窓口の選び箱（ChannelTypeCombobox）・`public.channel_masters` の行
- 会社の会話タブの API（companies.py:1065-1140）とタブそのもの
- `backend/app/services/conv_log_writer.py`（便3 で片付ける）
- `.github/workflows/`、`migrations/`、`deploy.yml`

## 9. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したときは、その場で手を止める。`BLOCKED:` で始めて、止まった手順・命令・生の出力を返す。自分で回り道を作らない
- 報告に入れるもの:
  - push した HEAD（40桁）
  - §6 の4つの検索の生の出力
  - 消した試験・書き換えた試験・足した試験の一覧
  - `git diff origin/main...HEAD --name-only` の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 10. 反映の後（Opus と PO が行う。担当はしない）

- M3: 反映の前と後に、Opus が読み取り専用の鍵で5社の `meta_messages` の `is_manual = true` を数える。どちらも 0 なら合格。
- M2: 反映の後、Opus が本番 API に作成を1回投げ、404 か 405 なら合格。
- M4: 反映の後の自動の動作確認（配備後点検）の結果を読む。
- M1: PO が最後の確かめで、受信箱の WhatsApp の相手を開き、手で書き足す欄が出ないことを目で見る（○×）。

END OF CARD
