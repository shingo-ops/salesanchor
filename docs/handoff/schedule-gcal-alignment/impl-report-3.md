# impl-report-3: 便3 Google Meet（K12〜K14）

枝: `release/schedule-gcal-bin3`（土台 origin/main `1f017118d`）。コードの commit: `5500829de`。
指示書: `origin/release/schedule-gcal-bin2-design` の design.md（HEAD 3b31aa127）§11-3・§5-7。便1・便2 の範囲には触っていない。

## 変えたもの（§11-3 の 17 項目すべて）

- 移行 `migrations/20261104_161223_add_calendar_events_meet_url.sql`（今ある会社を回して `meet_url TEXT` を足す・`ADD COLUMN IF NOT EXISTS`）と `scripts/run_all_migrations.sh` の 1 行
- `backend/app/services/calendar_service.py`: `can_add_meet`（送る条件の式もこの関数に置き換え）・作る／直す／取り込み／一覧の `meet_url`・返事 `{id, meet_url}`・`pending` は `asyncio.sleep(1)` で 2 回まで読み直し・`add_meet` だけの直しは `conferenceData` だけを patch（R4-1）
- `backend/app/services/google_calendar.py`: `create_event`・`update_event` の `conference`、`get_event`
- `backend/app/routers/calendar.py`: `add_meet`、422 を `try` の前で返す（作る＝`can_add_meet`、直す＝`can_add_meet`・`google_event_id`・持ち主が本人）、直す前の SELECT に `google_event_id, meet_url`、Meet 済みなら `add_meet` を外して渡す
- `backend/app/routers/google_calendar.py`: `connection_status` が `meet_available`（`can_add_meet`）を返す
- 画面: 型（`meet_url`／`meetUrl`）・「Google Meet を付ける」（`meet_available` が真で、新規か自分の予定で Meet 未設定のときだけ）・「Google Meet で参加」（`ButtonLink`・新しい窓・`rel="noopener noreferrer"`・`https://meet.google.com/` で始まるときだけ）・返事の `meet_url` が null なら既存の知らせの帯に `schedule.meetFailed`
- 文字: `schedule.addMeet`・`joinMeet`・`meetFailed`（ja・en 同じキー）
- ADR-1060（Proposed）・`docs/adr/README.md`（`generate-adr-index.js` で作り直し）・`FEATURE-INDEX.md` の 1 行

## 確かめ（生出力は /tmp/bin3-check-*.txt）

| 確かめ | 結果 |
|---|---|
| backend `pytest tests/test_calendar_owner_api.py tests/test_calendar_service.py tests/test_google_calendar.py` | 153 合格（もとは 121。新しい試験 32 件）。Python 3.12.3 |
| frontend `npm run test:unit -- src/pages/schedule` | 3 ファイル 75 合格（新しい試験 7 件） |
| `npx tsc --noEmit` | 0 件 |
| `npm run check:all` | 終了コード 0（`pages/schedule` への警告 0。他ファイルの既存の警告のみ） |
| `npm run check:new-tokens` | 合格（トークンは足していない） |
| `npm run build` | 成功 |
| `generate-adr-index.js` のあと `git diff --exit-code docs/adr/README.md` | 差分なし |
| `git diff --name-only origin/main...HEAD` | 17 ファイル。すべて §11-3 の範囲 |

新しい試験の内訳: 口（作る 422 など）3＋直す 422 の 3 通り＋既存 Meet 1＋許可 1、`can_add_meet` 5、作る（`conferenceDataVersion`／`createRequest`／`requestId` が毎回違う／`pending` 読み直し／2 回でも無ければ null／Meet 無しは何も付けない）5、直す 3、取り込み 2、一覧 1、`google_calendar` の `conference`・`get_event` 4、状態の口 4、画面 7。

## 既存の試験の合わせ込み（期待は変えていない・消していない）

- `test_calendar_owner_api.py` の `_event_db` に `google_event_id=None, meet_url=None` の既定つき引数を足し、5 列を返す形にした（今の 4 件の呼び方は同じ）。
- `test_calendar_service.py::test_returns_events` の行に `meet_url` の 19 列目を足した。
- `test_google_calendar.py` の `connection_status` 呼び出し 2 件に `user=` を渡すようにした（口が `user` を受けるため）。

## 分かれ道の確認（当たらなかった）

- `create_event`・`update_event`・`connection_status` の呼び元: 口と試験のほか、`routers/google_calendar.py:313,346` が `google_calendar.create_event/update_event` を呼ぶが、`conference` は既定 False の追加引数なので影響なし。
- 秘書の下書き（`SecretaryDraftEvent.tsx`）は作る口の返事を使っていない（`await api.post(...)` のみ）。
- `ButtonLink` は `target`・`rel` を通す。移行は 078 と同じく今ある会社を回せた。

## 注意・未確認

- ADR 番号 1060 は origin/main の最大＋1。開いている PR（約 50 本）の全部の中身までは確かめていない。同じ番号の PR があれば番号の付け替えが要る。
- 状態の口 `/google-calendar/status` を画面が読むのは今も「会社の管理者」だけ（`enabled: isTenantAdmin`・変えていない）。管理者でない人がつないだ本人でも Meet の Toggle は出ない。
- `api-contract/openapi.json`（触ってよい項目に無い）は更新していない。`add_meet`・`meet_available` の反映が要るかは CI の判定待ち。
- Workspace 管理者が Meet を止めているときの挙動、本番での K12・K14 は未確認（PO が本番で見る）。
- 本番へ入れる前に PO の「GO #PR番号」が要る（migrations を含む）。PR は作っていない。
