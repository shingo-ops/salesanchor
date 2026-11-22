# 実装カード 便2: Meta 審査用スイッチの画面（ADR-1055 What 11・設計 3-8）

- 設計: `docs/handoff/auth-new-device-approval/review-exempt-design.md` §3-8（Opus 審査済み: `review-exempt-review-opus.md`）
- 口（本番反映済み・#5683）: `backend/app/routers/super_admin_meta_review.py`
- ブランチ: `release/meta-review-switch-bin2`（origin/main 94a85aebf 起点）
- 区分: 画面だけ（backend・migrations・scripts は触らない）
- PO 承認: 「1」（2026-11-23、スイッチの画面を作る。マージ・反映まで委任）

## 1. 口の形（実物 `backend/app/routers/super_admin_meta_review.py`）

| 口 | 返す形 |
|---|---|
| `GET /super-admin/meta-review` (:59-81) | `{ tenant_name: string\|null, is_on: boolean, until: string\|null }`。印の会社が無ければ `tenant_name=null, is_on=false` |
| `PUT /super-admin/meta-review` body `{ on: boolean }` (:84-145) | 同じ形。印の会社が無いと 409 `meta_review_tenant_missing` |
| `GET /super-admin/meta-review/logins` (:148-184) | `{ items: [{ created_at, email, path, status_code, reason, device }] }`（新しい順・既定100件） |

- `until` が入っていて `is_on=false` ＝ 14日たって自動で切れた。手で OFF にすると `until=null`（:89）。
- `status_code`: 200 成功・202 許可待ち・それ以外は通らなかった。
- `reason` が入る値（`backend/app/routers/auth.py` の `_audit` 呼び出し。:415, :421, :428, :440, :458, :487, :1211, :1224, :1482, :1642, :1663）:
  `ok` `meta_review` `first_login` `device_approval_required` `bad_password` `inactive` `locked` `passkey_new_device` `recovery_code_wrong` `approved_recovery` `approved_admin` `approved_device`。これ以外・null は「その他」で記号をそのまま出す。

## 2. 触るファイル（これ以外は触らない）

### (1) `frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx`
変更前 :12-14
```tsx
interface Props {
  /** 閲覧者の画面で今選んでいる状態。ログインの画面では未指定。 */
  activeKey?: UserMenuStatus;
```
変更後
```tsx
interface Props {
  /** 今選んでいる項目。閲覧者の画面は状態、Meta 審査用の画面は "meta-review"。ログインの許可待ちの画面では未指定。 */
  activeKey?: UserMenuStatus | "meta-review";
```
変更前 :37-45（2つ目の組）に1項目足す:
```tsx
        {
          key: "login-requests",
          label: t("nav.superAdminLoginRequests"),
          to: "/super-admin/users/login-requests",
        },
        {
          key: "meta-review",
          label: t("nav.superAdminMetaReview"),
          to: "/super-admin/users/meta-review",
        },
```
変更前 :49 `if (key === "login-requests") return;` → 変更後 `if (key === "login-requests" || key === "meta-review") return;`
冒頭のコメント（:1-4）の「2つ目の組（題なし）: ログインの許可待ち」→「2つ目の組（題なし）: ログインの許可待ち・Meta 審査用」。

### (2) `frontend/src/App.tsx`
:100 の下に `import MetaReviewPage from "./pages/super-admin/MetaReviewPage";`
:343-347 の Route の直後に:
```tsx
                    {/* ADR-1055 What 11: Meta 審査用のスイッチ (is_super_admin 限定、Page 内で 403 の表示) */}
                    <Route
                      path="/super-admin/users/meta-review"
                      element={<MetaReviewPage />}
                    />
```

### (3) `frontend/src/config/routeTitles.ts`
:21 の下に `  "/super-admin/users/meta-review":           "nav.superAdminMetaReview",`（桁は周りに合わせる）

### (4) 新規 `frontend/src/pages/super-admin/MetaReviewPage.tsx`
外枠は `LoginRequestsPage.tsx:22-53` と同じ（`useSuperAdmin`・`LoadingBlock`・非 super admin は `superAdmin.accessDenied` の alert・`PageLayout navKey="nav.superAdminMetaReview" subtitleKey="superAdmin.metaReview.subtitle"`・`hub-shell`・`<UserManagementSubMenu activeKey="meta-review" statusLabel={statusLabel} />`・`hub-content`）。statusLabel と STATUS_KEY も LoginRequestsPage と同じ書き方。

中身（`hub-content` の中に `Stack gap="4"` で2枚）:

**カード1 スイッチ**（`SectionCard title={t("superAdmin.metaReview.switchTitle")}`）
- 読む: 画面を開いたとき `api.get<MetaReviewStatus>("/super-admin/meta-review")`。
- 会社名: `t("superAdmin.metaReview.tenant", { name: status.tenant_name })`。
- `tenant_name === null` なら `t("superAdmin.metaReview.noTenant")` を出し、Toggle は `disabled`。
- `Toggle`（`components/Toggle.tsx`）: `checked={status.is_on}`、`aria-label={t("superAdmin.metaReview.toggleLabel")}`、`disabled={saving || status.tenant_name === null}`、`onCheckedChange={(next) => setPending(next)}`（すぐには送らない）。
- `Badge`: ON は `variant="success"` で `t("superAdmin.metaReview.badgeOn")`、OFF は `variant="neutral"` で `t("superAdmin.metaReview.badgeOff")`。
- ON のとき: `t("superAdmin.metaReview.autoOffAt", { when: formatDate(status.until, i18n.language) })`。
- OFF で `until` があるとき（14日たって自動で切れた）: `t("superAdmin.metaReview.autoOffDone", { when: formatDate(status.until, i18n.language) })`。OFF で `until === null` なら何も出さない。
- 日時は `features/tcg-analysis-review/formatDateTime.ts` の `formatDate`（日本時間）を使う。新しい日時の関数を作らない。
- `ConfirmModal`（`components/ConfirmModal.tsx`）: `open={pending !== null}`。
  - ON にするとき: `title=t("superAdmin.metaReview.confirmOnTitle")`、`message=t("superAdmin.metaReview.confirmOnMessage")`、`confirmLabel=t("superAdmin.metaReview.confirmOn")`。
  - OFF にするとき: `danger`、`title=t("superAdmin.metaReview.confirmOffTitle")`、`message=t("superAdmin.metaReview.confirmOffMessage")`、`confirmLabel=t("superAdmin.metaReview.confirmOff")`。
  - `confirmLoading={saving}`。確定で `api.put<MetaReviewStatus>("/super-admin/meta-review", { on: pending })` → 返った形で status を置き換え → 履歴を読み直す → `pending=null`。取り消しで `pending=null`（status は変えない）。
  - 失敗したら `pending=null` にして `t("superAdmin.metaReview.saveError")` を `error-message` の alert で出す。
- 読み込み失敗は `t("superAdmin.metaReview.loadError")` を alert。

**カード2 ログインの履歴**（`SectionCard title={t("superAdmin.metaReview.historyTitle")}`）
- 読む: `api.get<{ items: MetaReviewLoginItem[] }>("/super-admin/meta-review/logins")`。開いたときと、30秒ごと（`useEffect` の `setInterval(…, 30_000)`、離れたら `clearInterval`）。
- `DataTable`（`components/DataTable.tsx`、`mobileCards`、`rowKey` は `${created_at}-${index}` 相当で一意になればよい）。列:
  - `colWhen` 日時: `formatDate(row.created_at, i18n.language)`（null は空）
  - `colEmail` メール: `row.email ?? ""`
  - `colResult` 結果: `Badge` で 200 → `variant="success"` `t("superAdmin.metaReview.resultOk")`、202 → `variant="warning"` `t("superAdmin.metaReview.resultPending")`、ほか → `variant="danger"` `t("superAdmin.metaReview.resultNg")`
  - `colReason` 理由: 下の表で i18n へ。表に無い値・null は `t("superAdmin.metaReview.reason.other", { code: row.reason ?? "-" })`
  - `colDevice` 機械: `row.device`（口が日本語にして返す。そのまま）
- 0件: `emptyState={<EmptyState size="compact" title={t("superAdmin.metaReview.empty")} />}`
- 履歴の読み込み失敗は `t("superAdmin.metaReview.historyLoadError")` を alert。

理由→キーの表は **このファイルの中の1か所だけ**に置く（`const REASON_KEYS: Record<string, string> = { ok: "superAdmin.metaReview.reason.ok", … }`）。

- 色・大きさ・余白の直値を書かない。CSS ファイルを新しく作らない（部品の見た目だけで組む）。
- 生の `<input>`・`<select>`・`<button>` を書かない。

### (5) `frontend/src/locales/ja.json` と `en.json`（同じキーを両方に）
- `nav` に `superAdminMetaReview`（:318 `superAdminLoginRequests` の下）: ja「Meta審査用」／en「Meta Review」
- `superAdmin.loginRequests` の後ろに `superAdmin.metaReview`:

| キー | ja | en |
|---|---|---|
| subtitle | Meta の審査員が登録していない機械から入れるようにする、審査の間だけのスイッチです。ほかの会社では使えません。 | A switch, only for the review period, that lets the Meta reviewer sign in from an unregistered device. It does not work for any other company. |
| switchTitle | スイッチ | Switch |
| tenant | 対象の会社: {{name}} | Company: {{name}} |
| noTenant | 審査用の印が付いた会社がありません。スイッチは使えません。 | No company is marked for the review. The switch is not available. |
| toggleLabel | Meta 審査用のスイッチ | Meta review switch |
| badgeOn | ON（審査員はログインできます） | ON (the reviewer can sign in) |
| badgeOff | OFF（ふだんの確認に戻っています） | OFF (normal device checks are back) |
| autoOffAt | {{when}} に自動で OFF になります | Turns OFF automatically at {{when}} |
| autoOffDone | {{when}} に、14日たったので自動で OFF になりました | Turned OFF automatically at {{when}} after 14 days |
| confirmOnTitle | スイッチを ON にしますか | Turn the switch ON? |
| confirmOnMessage | 今から14日のあいだ、審査用の会社の人は登録していない機械からログインできます。14日たつと自動で OFF になります。 | For the next 14 days, people in the review company can sign in from unregistered devices. It turns OFF automatically after 14 days. |
| confirmOn | ON にする | Turn ON |
| confirmOffTitle | スイッチを OFF にしますか | Turn the switch OFF? |
| confirmOffMessage | OFF にすると、審査員は登録していない機械から入れなくなり、いま入っている分もすぐ切れます。 | When OFF, the reviewer can no longer sign in from unregistered devices, and current sessions end right away. |
| confirmOff | OFF にする | Turn OFF |
| saveError | スイッチを切り替えられませんでした。画面を読み込み直して、もう一度お試しください。 | Could not change the switch. Reload the page and try again. |
| loadError | スイッチの状態を読み込めませんでした。画面を読み込み直してください。 | Could not load the switch. Reload the page. |
| historyTitle | ログインの履歴 | Sign-in history |
| historyLoadError | ログインの履歴を読み込めませんでした。少し待ってから画面を読み込み直してください。 | Could not load the sign-in history. Wait a moment and reload the page. |
| empty | まだログインの試行はありません | No sign-in attempts yet |
| colWhen | 日時 | Time |
| colEmail | メール | Email |
| colResult | 結果 | Result |
| colReason | 理由 | Reason |
| colDevice | 機械 | Device |
| resultOk | 成功 | Signed in |
| resultPending | 許可待ち | Waiting for approval |
| resultNg | 通らなかった | Not signed in |
| reason.ok | いつもの機械でログイン | Signed in on a trusted device |
| reason.meta_review | スイッチ ON でログイン（登録していない機械） | Signed in with the switch ON (unregistered device) |
| reason.first_login | 最初のログイン（この機械を登録） | First sign-in (device registered) |
| reason.device_approval_required | 知らない機械のため許可待ち | Unknown device, waiting for approval |
| reason.bad_password | パスワード違い | Wrong password |
| reason.inactive | 使えないアカウント | Account not active |
| reason.locked | 回数の上限で一時停止 | Temporarily locked after too many attempts |
| reason.passkey_new_device | パスキーで新しい機械からログイン | Signed in with a passkey on a new device |
| reason.recovery_code_wrong | 予備の合言葉が違う | Wrong recovery code |
| reason.approved_recovery | 予備の合言葉で許可 | Approved with a recovery code |
| reason.approved_admin | 管理者が許可 | Approved by an admin |
| reason.approved_device | いつもの機械で許可 | Approved on a trusted device |
| reason.other | その他（{{code}}） | Other ({{code}}) |

- 失敗を伝える文には次にすること（読み込み直し・もう一度）を必ず入れる（見張りの語の一覧は `frontend/scripts/check-error-text-next-action.js:28-29`）。上の表はそれを満たす形。結果の語は「通らなかった」にする。

### (6) 試験
- 新規 `frontend/src/pages/super-admin/MetaReviewPage.test.tsx`（書き方は `LoginRequestsPage.test.tsx` と同じ。`vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() } }))`）:
  1. super admin でない人には alert が出て、`api.get` を呼ばない
  2. OFF（until null）: Badge が badgeOff、autoOffDone が出ない、履歴0件で empty が出る
  3. OFF（until が過去）: autoOffDone が出る
  4. Toggle を押すと確認の小窓が出て、取り消すと `api.put` を呼ばない。確定すると `api.put("/super-admin/meta-review", { on: true })` を1回呼び、Badge が badgeOn になる
  5. 履歴: status_code 200/202/401 が resultOk/resultPending/resultNg、reason `meta_review` が訳され、表に無い reason が `reason.other` になる
- `frontend/src/pages/super-admin/users/UserManagementSubMenu.test.tsx`: Meta 審査用のリンクが `/super-admin/users/meta-review` を指す、`activeKey="meta-review"` でその項目が active、の2点を足す（既存の試験は変えない）。

## 3. 想定分岐（カードに無いことが起きたら止まる）

| 起きたこと | どうする |
|---|---|
| 部品の props が上の通りでない（例: ConfirmModal に danger が無い） | 止まって BLOCKED: で報告。部品を直さない |
| `formatDate` の import で lint／循環の赤 | 止まって報告。自作の日時関数を作らない |
| i18n の見張りや check:error-text-next-action が赤 | 文言を表の意味のまま直してよい。基準ファイル（baseline）は書き換えない |
| 既存の試験（ViewerAccountsPage.test 等）が赤 | 原因の行を報告。既存の試験は書き換えない |
| backend・openapi.json・migrations を触りたくなった | 触らない。止まって報告 |

## 4. 検証（実装役が流して生出力をファイルに残す）

```
cd frontend
npx tsc --noEmit
npx eslint src/pages/super-admin/MetaReviewPage.tsx src/pages/super-admin/MetaReviewPage.test.tsx src/pages/super-admin/users src/App.tsx src/config/routeTitles.ts
npx vitest run src/pages/super-admin/MetaReviewPage.test.tsx src/pages/super-admin/users/UserManagementSubMenu.test.tsx src/pages/super-admin/LoginRequestsPage.test.tsx src/pages/super-admin/ViewerAccountsPage.test.tsx
npm run check:i18n-missing-keys
npm run check:error-text-next-action
npm run check:css-colors && npm run check:css-values
```

## 5. 受入条件

| 基準 | 検証方法 |
|---|---|
| 利用者管理の小メニューで「ログインの許可待ち」の下に「Meta審査用」が出て、押すと /super-admin/users/meta-review が開く | SubMenu 試験・本番の画面 |
| 開くと会社名・ON/OFF の札・切替が出る。OFF のとき「OFF（ふだんの確認に戻っています）」 | 試験2・本番の画面 |
| 切替を押すと確認の小窓が出て、確定するまで口を呼ばない | 試験4 |
| ON のとき自動で OFF になる日時が日本時間で出る | 試験4・本番の画面 |
| 履歴が 日時・メール・結果・理由・機械 の5列で、打ち間違いのメールは出ない（口が出さない） | 試験5・本番の画面 |
| ja.json と en.json のキーが同じ | check:i18n-missing-keys |
| 色・大きさの直値 0・新しい CSS 0 | check:css-colors / check:css-values・差分 |
