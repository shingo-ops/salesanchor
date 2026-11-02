# 実装カード — 予定の画面に Google カレンダーのつなぐボタンを戻す

親: docs/handoff/schedule-gcal-connect/design.md ／ recon: docs/handoff/schedule-gcal-connect/recon.md ／ ADR-027・ADR-144・ADR-067・ADR-1018
状態: 設計担当（Opus）作成。実装は Sonnet。PO 決定 2026-11-02「1」（ボタンを戻す・本番まで）・「1」（PO が入れた予定だけ送る）。
作業場所: origin/main から新しいブランチ `release/schedule-gcal-connect-impl` を作る（クラウドでも同じ名前）。設計の書類（docs/handoff/schedule-gcal-connect/）は触らない。

## 0. 始める前に
- `./scripts/dev/executor-preflight.sh || exit 1`（クラウドで動かないときは、その出力を報告に貼って続ける）。`frontend/CLAUDE.md`・`docs/CC_UI_GOVERNANCE.md` を読む。
- 下の行番号と引用が実物と合うか確かめる。合わなければ始めずに `BLOCKED:` で止める。

## 1. 変えるファイル（これ以外は触らない）
| ファイル | 変えること |
|---|---|
| `backend/app/services/calendar_service.py` | 2-1 |
| `backend/tests/test_calendar_service.py` | 3-1 |
| `backend/app/routers/google_calendar.py` | 2-2 |
| `backend/tests/test_google_calendar.py` | 3-2 |
| `frontend/src/hooks/usePermissions.ts` | 2-3 |
| `frontend/src/hooks/usePermissions.test.ts` | 3-3 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 2-4 |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`（新規） | 3-4 |

文言は足さない。使うキーは ja.json / en.json に既にある `schedule.connectBtn`・`schedule.connectBtnConnected`・`schedule.connectError`。CSS も足さない。

## 2. 中身
### 2-1 calendar_service.py
- `_get_sync_mode`（:45-54）は変えない（update・delete・通知の登録でも使う）。その直後に足す:
```python
async def _get_sync_target(db: AsyncSession, tenant_id: int) -> tuple[str, Optional[int]]:
    """同期モードと、Google をつないだ人の user_id を返す。未接続は ('none', None)。"""
    row = await db.execute(
        text(
            "SELECT sync_mode, connected_by_user_id FROM tenant_google_calendar_config"
            " WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    return (record[0], record[1]) if record else ("none", None)
```
- `create_event` の :199-200 を次に置き換える:
```python
    sync_mode, connected_by = await _get_sync_target(db, tenant_id)
    # 接続は会社で1つ。つないだ人が作った予定だけ送り、ほかの人の予定はその人の Google に入れない（PO 2026-11-02）
    if sync_mode in ("bidirectional", "write_only") and connected_by == user_id:
```
- docstring（:165-168）の「同期モードが…場合のみ Google に送信する。」を「同期モードが 'bidirectional' または 'write_only' で、Google をつないだ本人が作った予定だけ Google に送信する。」にする。
- update_event・delete_event は変えない。

### 2-2 google_calendar.py
- :30-35 の import に `get_current_user` を足す（並びはアルファベット順）。
- `connect_start` の前（「Authenticated: 接続開始」の区切りの前）に足す:
```python
async def require_calendar_owner(
    tenant_id: int = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Google カレンダーをつないだ本人だけ通す。

    接続は会社で1つで、中身はつないだ人の Google カレンダー。
    ほかの人（管理者を含む）がその予定を読み書きできないようにする。未接続も通さない。
    """
    row = await db.execute(
        text(
            "SELECT connected_by_user_id FROM tenant_google_calendar_config"
            " WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    if record is None or record[0] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google カレンダーをつないだ本人だけが使えます",
        )
    return user
```
- 4 つの口 `list_events`（:249）・`create_event`（:276）・`update_event`（:302）・`delete_event`（:335）に、`tenant_id` の次の引数として `user: User = Depends(require_calendar_owner),` を足す。本体は変えない。
- callback・webhook・status・connect_start・disconnect は変えない。

### 2-3 usePermissions.ts
- `PermissionsResponse`（:13-15）に `is_tenant_admin?: boolean;` を足す。
- `const isTenantAdmin = data?.is_tenant_admin === true;` を足し、戻り値の useMemo（:43-46）の中身と依存に `isTenantAdmin` を足す。
- 変更履歴（:5-7）に `2026-11-03: is_tenant_admin を返す（予定の画面の Google カレンダー連携ボタン用）。` を 1 行足す。

### 2-4 SchedulePageImpl.tsx
- import に `import { useApiQuery } from "../../lib/query/apiQuery";` を足す（:23 の `usePermissions` の次）。
- :829 を `const { hasPermission, isTenantAdmin } = usePermissions();` にする。
- :831 の次に足す:
```tsx
  const gcalStatusQ = useApiQuery<{ connected: boolean }>("/google-calendar/status", { enabled: isTenantAdmin });
  const gcalConnected = gcalStatusQ.data?.connected === true;
  const [gcalConnecting, setGcalConnecting] = useState(false);
```
- `?connected` を見る useEffect（:864-874）の後に足す:
```tsx
  const handleGoogleConnect = async () => {
    setGcalConnecting(true);
    try {
      const { auth_url } = await api.get<{ auth_url: string }>("/google-calendar/connect/start");
      window.location.href = auth_url;
    } catch {
      setBanner({ type: "error", message: t("schedule.connectError") });
      setGcalConnecting(false);
    }
  };
```
- headerAction の `<div className="schedule-shell__toolbar">`（:1119）の直後、検索ボタンの前に足す:
```tsx
            {isTenantAdmin && (
              <Button
                variant="ghost"
                size="md"
                loading={gcalConnecting}
                disabled={gcalConnected || gcalConnecting}
                onClick={handleGoogleConnect}
              >
                {gcalConnected ? t("schedule.connectBtnConnected") : t("schedule.connectBtn")}
              </Button>
            )}
```
- 生の `<button>`・`style={{}}`・className の追加・色の直書きは入れない。

## 3. 試験
### 3-1 test_calendar_service.py
- 今の 3 つの試験（:213・:239・:263）の `sync_result.first` の戻り値を 2 つ組にする: `("none",)` → `("none", None)`、`("bidirectional",)` → `("bidirectional", 1)`（:263 の試験は user_id=1 なので Google を呼び、失敗の道を通るまま）。
- 足す試験:
  - つないだ人と別の人: `("bidirectional", 1)`・`user_id=2` → `app.services.google_calendar.create_event` を AsyncMock で差し替え、呼ばれないこと。`db.execute` の呼び出しが 2 回（INSERT と接続の読み取り）であること。
  - つないだ本人: `("bidirectional", 3)`・`user_id=3`・Google の戻り `{"id": "g1"}` → 1 回呼ばれ、3 回目の `db.execute` の引数に `gid == "g1"` と `oid == "app:1:<id>"` があること。

### 3-2 test_google_calendar.py
- `test_both_routes_depend_on_require_tenant_admin`（:310-317）と同じ形で、4 つの口の `user` の既定値が `require_calendar_owner` であることを確かめる試験を足す。
- `require_calendar_owner` を直接呼ぶ試験を 3 つ足す（db は `_make_db` のような AsyncMock。`first()` の戻りを変える）:
  - 行なし → 403
  - 行 `(1,)`・user.id=5 → 403
  - 行 `(5,)`・user.id=5 → user が返る
- 今の `test_list_events_db_error_502`（:325）・`test_create_event_not_connected_502`（:349）は関数を直接呼んでいるので、そのまま通るはず。通らなければ直さずに `BLOCKED:` で止める。

### 3-3 usePermissions.test.ts
- `{ permissions: [], is_tenant_admin: true }` → `isTenantAdmin === true`。
- `{ permissions: [] }`（欄なし）→ `isTenantAdmin === false`。

### 3-4 SchedulePageImpl.test.tsx（新規）
- 既存の画面の試験の書き方（`frontend/src/pages/` 配下の `*.test.tsx`）に合わせ、`api.get` を差し替えて描く。
- 管理者（`is_tenant_admin: true`・status `{connected:false}`）→ 「Googleカレンダー連携」のボタンがあり押せる。押すと `/google-calendar/connect/start` を呼ぶ。
- 管理者・status `{connected:true}` → 「✔︎連携済」で押せない。
- 管理者でない（`is_tenant_admin: false`）→ ボタンが無く、`/google-calendar/status` を呼ばない。
- 描くのに要る周りの呼び出し（予定一覧・持ち主一覧など）は空の答えで差し替える。描けないときは `BLOCKED:` で止めて、何が足りないかを書く。

## 4. 終わる前に
- backend: `pytest backend/tests/test_calendar_service.py backend/tests/test_google_calendar.py -q`
- frontend: `npm run lint`・`npx tsc --noEmit`・`npx vitest run src/hooks/usePermissions.test.ts src/pages/schedule`
- UI の決まりの検査: リポジトリ直下で、CI の ui-governance-gate と同じ `node scripts/check-ui-governance.js` を、BASE_SHA に origin/main との分かれ目、HEAD_SHA に HEAD を入れて動かす
- 生出力は省かずに報告へ貼る。
- PR は `--base main`・Draft にしない。本文に `### 標準ワークフロー確認` を入れ、design.md と recon.md の場所を書く。危険なパス（migrations/・deploy.yml・本番 scripts/）は触らない。

## 5. 想定分岐
- 行番号がずれている → 引用の文字列で場所を探し、合えば進める。文字列も無ければ `BLOCKED:`。
- `Button` に `loading` が無い → `BLOCKED:`（`GoogleCalendarStatusBar.tsx` では使っているので、あるはず）。
- UI の決まりの検査（scripts/check-ui-governance.js）が赤になる → 直さずに `BLOCKED:` で止め、出力を貼る。
