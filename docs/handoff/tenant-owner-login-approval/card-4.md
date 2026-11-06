# card: 便4 会社のオーナーが社員のログインを許可する画面（フロントエンド）

状態: カード発行（Opus、2026-11-06）。PO の実装承認は 2026-11-06「1」（このまま作り始める）。設計: docs/handoff/tenant-owner-login-approval/design.md 便4。便3（バックエンドの口）は #5182 で本番反映済み。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: origin/main `7e0bc67b1dd39f658fa37ca3da1ca39277dd3fb8`。行番号はこの時点のもの。ずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

設計からの小さな変更（Opus 判断・記録）: 新しい画面のファイル名は design.md の `LoginRequestsPage.tsx` ではなく `TenantLoginRequestsPage.tsx` にする（運営の画面と同じ名前の default import が App.tsx で2つになるのを避けるため）。2画面で共有する部品は `frontend/src/features/auth/AdminLoginRequestList.tsx`（一覧・確認の小窓・メモ欄をまとめて1か所に）。共有部品の文言は既存の `superAdmin.loginRequests.*` をそのまま使う（鍵の引っ越しはしない）。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin4 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin4-owner-approval-ui` を origin から取り、このカードが在ること。
- P2 `grep -c '"is_tenant_owner": is_tenant_owner(system_keys),' backend/app/routers/roles.py` が 1。
- P3 `grep -c '@router.post("/login-requests/ask-admin"' backend/app/routers/auth.py` が 1。`grep -c '@router.get("/tenant/login-requests"' backend/app/routers/tenant_login_requests.py` が 1。
- P4 `grep -rn "isTenantOwner\|ask-admin\|tenant/login-requests\|AdminLoginRequestList" frontend/src` が 0 件。
- P5 次がそれぞれちょうど 1 件:
  - `grep -c "const isTenantAdmin = data?.is_tenant_admin === true;" frontend/src/hooks/usePermissions.ts`
  - `grep -c '{!approval.hasTrustedDevice && !approval.hasRecoveryCodes && (' frontend/src/pages/login/LoginPage.tsx`
  - `grep -c 'const totalUnread = unread + requests.length;' frontend/src/components/NoticeBell.tsx`
  - `grep -c 'import LoginRequestsPage from "./pages/super-admin/LoginRequestsPage";' frontend/src/App.tsx`
  - `grep -c '{ to: "notifications",  labelKey: "nav.notifications",' frontend/src/pages/management-center/ManagementCenterPage.tsx`

## 1. 触るファイル
1. frontend/src/hooks/usePermissions.ts
2. frontend/src/lib/auth/selfAuth.ts
3. frontend/src/pages/login/LoginPage.tsx
4. frontend/src/pages/login/LoginPage.test.tsx
5. frontend/src/features/auth/AdminLoginRequestList.tsx（新規）
6. frontend/src/pages/super-admin/LoginRequestsPage.tsx
7. frontend/src/pages/management-center/TenantLoginRequestsPage.tsx（新規）
8. frontend/src/pages/management-center/TenantLoginRequestsPage.test.tsx（新規）
9. frontend/src/pages/management-center/ManagementCenterPage.tsx
10. frontend/src/App.tsx
11. frontend/src/components/NoticeBell.tsx
12. frontend/src/components/NoticeBell.test.tsx
13. frontend/src/locales/ja.json
14. frontend/src/locales/en.json

触らない: backend 全部・migrations・.github・frontend/src/pages/super-admin/LoginRequestsPage.test.tsx（動きが変わらないので通るはず。落ちたら BLOCKED）・CSS ファイル（新しい色・余白は作らない）・frontend/src/features/auth/LoginRequestDecision.tsx。

## 2. 変更

### 2-1 usePermissions.ts
- `interface PermissionsResponse` に `is_tenant_owner?: boolean;` を足す（`is_tenant_admin?: boolean;` の次の行）。
- `const isTenantAdmin = data?.is_tenant_admin === true;` の次の行に `const isTenantOwner = data?.is_tenant_owner === true;`。
- 返り値と依存の両方に `isTenantOwner` を足す:
  変更前 `() => ({ permissions, isTenantAdmin, loading, error, hasPermission, hasAny, reload: load }),`
  変更後 `() => ({ permissions, isTenantAdmin, isTenantOwner, loading, error, hasPermission, hasAny, reload: load }),`
  変更前 `[permissions, isTenantAdmin, loading, error, hasPermission, hasAny, load],`
  変更後 `[permissions, isTenantAdmin, isTenantOwner, loading, error, hasPermission, hasAny, load],`
- 変更履歴に1行: ` *   2026-11-06: is_tenant_owner を返す（会社のオーナーのログイン許可の画面と鈴・ADR-1063）。`

### 2-2 selfAuth.ts（`recoverLoginRequest` の関数の直後に足す）
```ts
export type AskAdminStatus = "requested" | "already_requested" | "no_owner" | "expired";

/** 待つ機械で「会社の管理者に頼む」（ADR-1063）。依頼が終わっていれば 409 not_pending（SelfAuthError）。 */
export async function askAdminLoginRequest(): Promise<AskAdminStatus> {
  const res = await postAuth<{ status: AskAdminStatus }>("/login-requests/ask-admin");
  return res.status;
}
```

### 2-3 LoginPage.tsx
(a) import を変える:
変更前 `import { SelfAuthError, pollLoginRequest, recoverLoginRequest } from "../../lib/auth/selfAuth";`
変更後 `import { SelfAuthError, askAdminLoginRequest, pollLoginRequest, recoverLoginRequest } from "../../lib/auth/selfAuth";`
変更前 `import type { LoginApprovalRequired } from "../../lib/auth/selfAuth";`
変更後 `import type { AskAdminStatus, LoginApprovalRequired, LoginRequestPollStatus } from "../../lib/auth/selfAuth";`
1 行目 `import { useState, FormEvent, useEffect, useRef } from "react";` → `import { useState, FormEvent, useEffect, useRef, useCallback } from "react";`

(b) `const [recoveryError, setRecoveryError] = useState("");` の次に:
```ts
  // 「会社の管理者に頼む」（ADR-1063）。押した結果の文を出す
  const [askResult, setAskResult] = useState<Exclude<AskAdminStatus, "expired"> | null>(null);
  const [askBusy, setAskBusy] = useState(false);
```

(c) 待ちの終わり方を1か所にまとめる。`// 待ちの間: 残り時間を1秒ごとに更新し、` の行の直前に足す:
```ts
  // 待ちを終えてログイン画面に戻す（期限切れ・断られた）。poll と「管理者に頼む」の両方から使う
  const endApproval = useCallback((message: string) => {
    setApproval(null);
    setPollNotice("");
    setAskResult(null);
    setError(message);
  }, []);

  // poll の結果に従う。待ちを終えたら true
  const applyPollStatus = useCallback(
    (status: LoginRequestPollStatus): boolean => {
      if (status === "rejected") {
        endApproval(t("login.deviceApproval.rejected"));
        return true;
      }
      if (status === "expired") {
        endApproval(t("login.deviceApproval.expired"));
        return true;
      }
      // completed: トークンを受けた。user が立つので上の自動遷移が進む
      if (status === "completed") {
        clearRecoveryPromptMarksForCurrentUser();
        return true;
      }
      return false;
    },
    [endApproval, t],
  );
```

(d) poll の useEffect の中を置き換える。
変更前（この塊全体）:
```ts
    const stop = (message: string) => {
      setApproval(null);
      setPollNotice("");
      setError(message);
    };
    const run = async () => {
      try {
        const status = await pollLoginRequest();
        if (cancelled) return;
        pollDelayRef.current = POLL_INTERVAL_MS;
        setPollNotice("");
        if (status === "rejected") return stop(t("login.deviceApproval.rejected"));
        if (status === "expired") return stop(t("login.deviceApproval.expired"));
        // completed: トークンを受けた。user が立つので上の自動遷移が進む
        if (status === "completed") {
          clearRecoveryPromptMarksForCurrentUser();
          return;
        }
      } catch (err) {
```
変更後:
```ts
    const run = async () => {
      try {
        const status = await pollLoginRequest();
        if (cancelled) return;
        pollDelayRef.current = POLL_INTERVAL_MS;
        setPollNotice("");
        if (applyPollStatus(status)) return;
      } catch (err) {
```
同じ useEffect の中の `return stop(t("login.deviceApproval.expired"));` を `return void endApproval(t("login.deviceApproval.expired"));` に。依存 `}, [approval, t]);` を `}, [approval, applyPollStatus, endApproval, t]);` に。

(e) `const cancelApproval = () => {` の塊の `setError("");` の次の行に `setAskResult(null);` を足す。`handleSignIn` の `setApproval(result);` の次の行に `setAskResult(null);` を足す。

(f) `cancelApproval` の塊の直後に:
```ts
  const handleAskAdmin = async () => {
    if (askBusy) return;
    setError("");
    setAskBusy(true);
    try {
      const status = await askAdminLoginRequest();
      if (status === "expired") {
        endApproval(t("login.deviceApproval.expired"));
        return;
      }
      setAskResult(status);
    } catch (err) {
      if (err instanceof SelfAuthError && err.status === 409) {
        // 依頼がもう終わっている: 状態の判断は poll の1か所に任せる
        try {
          applyPollStatus(await pollLoginRequest());
        } catch {
          endApproval(t("login.deviceApproval.expired"));
        }
      } else {
        setError(authErrorMessage(err, t, "login"));
      }
    } finally {
      setAskBusy(false);
    }
  };
```

(g) 待ち画面の表示。
変更前:
```tsx
            {!approval.hasTrustedDevice && !approval.hasRecoveryCodes && (
              <p>{t("login.deviceApproval.noTrustedDevice")}</p>
            )}
```
変更後:
```tsx
            <Button
              variant="outline"
              size="auth"
              shape="pill"
              fullWidth
              type="button"
              loading={askBusy}
              disabled={askBusy || askResult !== null}
              onClick={() => void handleAskAdmin()}
            >
              {t("login.deviceApproval.askAdmin")}
            </Button>
            {askResult === "requested" && (
              <Callout variant="info" title={t("login.deviceApproval.askAdminRequested")} />
            )}
            {askResult === "already_requested" && (
              <Callout variant="info" title={t("login.deviceApproval.askAdminAlready")} />
            )}
            {askResult === "no_owner" && (
              <Callout variant="warning" title={t("login.deviceApproval.askAdminNoOwner")} />
            )}
            {!approval.hasTrustedDevice && !approval.hasRecoveryCodes && (
              <p>{t("login.deviceApproval.noTrustedDevice")}</p>
            )}
```
（Callout の title は必須（frontend/src/components/Callout.tsx の CalloutProps）。文は title に入れ、本文は付けない。Opus 2026-11-06 訂正: 初回のクラウド実行で tsc TS2741 が出たため）

### 2-4 LoginPage.test.tsx（既存の書き方・mock に合わせて足す。既存の試験は消さない・変えない）
既存の待ち画面の試験と同じやり方で 202 の待ち画面を出し、`fetch`（または既存が mock しているもの）で `/login-requests/ask-admin` に対し次を返す試験を 4 本:
- T1 `{"status":"requested"}` → ボタンを押すと `askAdminRequested` の文（en）が出て、ボタンが押せなくなる。
- T2 `{"status":"no_owner"}` → `askAdminNoOwner` の文が出る。
- T3 `{"status":"expired"}` → 待ち画面が消え、`login.deviceApproval.expired` の文（en）が出る。
- T4 409 `{"detail":"not_pending"}` の後、poll が `{"status":"rejected"}` → `login.deviceApproval.rejected` の文が出る。
既存試験の mock の形が分からない・この4本が既存の形で書けない → `BLOCKED: LoginPage.test の mock`。

### 2-5 AdminLoginRequestList.tsx（新規・全文）
```tsx
/**
 * ログインの許可待ちの一覧と許可の小窓（ADR-1055 K7・ADR-1063）。
 * 運営の画面（/super-admin/login-requests）と会社のオーナーの画面（/management-center/login-requests）で共有する。
 * - 許可には本人確認の方法（note）が必須
 * - 読む先・許可する先だけを props で受ける（見た目と動きは1か所）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";
import { LoadingBlock } from "../../components/loading";

export interface AdminLoginRequestRow {
  id: string;
  user_id: number;
  email: string | null;
  full_name: string | null;
  status: string;
  label: string | null;
  location: string | null;
  created_at: string | null;
  expires_at: string | null;
}

export interface AdminLoginRequestListProps {
  /** 一覧を読む先（api の相対パス） */
  listPath: string;
  /** 許可する先（api の相対パス） */
  approvePath: (id: string) => string;
}

const NOTE_MAX_LENGTH = 200;

export default function AdminLoginRequestList({ listPath, approvePath }: AdminLoginRequestListProps) {
  const { t, i18n } = useTranslation();
  const [rows, setRows] = useState<AdminLoginRequestRow[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [target, setTarget] = useState<AdminLoginRequestRow | null>(null);
  const [note, setNote] = useState("");
  const [approving, setApproving] = useState(false);

  const load = useCallback(async () => {
    setFetching(true);
    setError("");
    try {
      const res = await api.get<{ items: AdminLoginRequestRow[] }>(listPath);
      setRows(res.items);
    } catch {
      setError(t("superAdmin.loginRequests.loadError"));
    } finally {
      setFetching(false);
    }
  }, [listPath, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const closeConfirm = () => {
    setTarget(null);
    setNote("");
  };

  const handleApprove = async () => {
    if (!target || note.trim() === "") return;
    setError("");
    setSuccess("");
    setApproving(true);
    try {
      await api.post(approvePath(target.id), { note: note.trim() });
      setSuccess(t("superAdmin.loginRequests.approved"));
      closeConfirm();
      await load();
    } catch {
      closeConfirm();
      setError(t("superAdmin.loginRequests.approveError"));
    } finally {
      setApproving(false);
    }
  };

  const formatDate = (value: string | null) => (value ? new Date(value).toLocaleString(i18n.language) : "");

  const columns: DataTableColumn<AdminLoginRequestRow>[] = [
    {
      key: "user",
      header: t("superAdmin.loginRequests.colUser"),
      renderCell: (row) => row.full_name || row.email || String(row.user_id),
    },
    { key: "email", header: t("superAdmin.loginRequests.colEmail"), renderCell: (row) => row.email ?? "" },
    {
      key: "label",
      header: t("superAdmin.loginRequests.colDevice"),
      renderCell: (row) => row.label ?? t("superAdmin.loginRequests.unknown"),
    },
    {
      key: "location",
      header: t("superAdmin.loginRequests.colLocation"),
      renderCell: (row) => row.location ?? t("superAdmin.loginRequests.unknown"),
    },
    {
      key: "created_at",
      header: t("superAdmin.loginRequests.colRequested"),
      renderCell: (row) => formatDate(row.created_at),
    },
    {
      key: "expires_at",
      header: t("superAdmin.loginRequests.colExpires"),
      renderCell: (row) => formatDate(row.expires_at),
    },
    {
      key: "actions",
      header: "",
      renderCell: (row) => (
        <Button type="button" variant="primary" size="sm" onClick={() => setTarget(row)}>
          {t("superAdmin.loginRequests.approve")}
        </Button>
      ),
    },
  ];

  return (
    <>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="status">
          {success}
        </div>
      )}
      {fetching ? (
        <LoadingBlock />
      ) : (
        <DataTable<AdminLoginRequestRow>
          columns={columns}
          data={rows}
          rowKey={(row) => row.id}
          emptyState={t("superAdmin.loginRequests.empty")}
          mobileCards
        />
      )}
      <ConfirmModal
        open={target !== null}
        title={t("superAdmin.loginRequests.approveTitle")}
        message={
          <Stack gap="3">
            <p>{t("superAdmin.loginRequests.approveMessage")}</p>
            <label htmlFor="login-request-note">{t("superAdmin.loginRequests.noteLabel")}</label>
            <TextFieldControl
              id="login-request-note"
              type="text"
              maxLength={NOTE_MAX_LENGTH}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              required
            />
            <p>{t("superAdmin.loginRequests.noteHelp")}</p>
          </Stack>
        }
        confirmLabel={t("superAdmin.loginRequests.approve")}
        confirmDisabled={note.trim() === ""}
        confirmLoading={approving}
        onConfirm={() => void handleApprove()}
        onCancel={closeConfirm}
      />
    </>
  );
}
```

### 2-6 super-admin/LoginRequestsPage.tsx（全文を置き換え・動きは同じ）
```tsx
/**
 * /super-admin/login-requests — ログインの許可待ち一覧（ADR-1055 段A・K7）。
 *
 * - いつもの機械も予備の合言葉も無い人の依頼を、super admin が本人確認のうえ許可する
 * - 一覧と許可の小窓は会社のオーナーの画面と共有（features/auth/AdminLoginRequestList）
 * - is_super_admin=true のみアクセス可（Page 内で 403 の表示）
 */
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { LoadingBlock } from "../../components/loading";
import AdminLoginRequestList from "../../features/auth/AdminLoginRequestList";

export default function LoginRequestsPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();

  if (authLoading) return <LoadingBlock />;

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminLoginRequests">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.superAdminLoginRequests" subtitleKey="superAdmin.loginRequests.subtitle">
      <AdminLoginRequestList
        listPath="/super-admin/login-requests?status=pending"
        approvePath={(id) => `/super-admin/login-requests/${id}/approve`}
      />
    </PageLayout>
  );
}
```

### 2-7 management-center/TenantLoginRequestsPage.tsx（新規・全文）
```tsx
/**
 * /management-center/login-requests — 社員のログインの許可待ち（ADR-1063）。
 *
 * - 社員が新しい機械で「会社の管理者に頼む」を押した、同じ会社の依頼だけが並ぶ（会社の絞り込みは API 側）
 * - 会社のオーナー（is_tenant_owner）だけが開ける。それ以外は案内の文だけ
 * - 一覧と許可の小窓は運営の画面と共有（features/auth/AdminLoginRequestList）
 */
import { useTranslation } from "react-i18next";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { LoadingBlock } from "../../components/loading";
import AdminLoginRequestList from "../../features/auth/AdminLoginRequestList";

export default function TenantLoginRequestsPage() {
  const { t } = useTranslation();
  const { isTenantOwner, loading } = usePermissions();

  if (loading) return <LoadingBlock />;

  if (!isTenantOwner) {
    return (
      <PageLayout navKey="nav.tenantLoginRequests">
        <div className="error-message" role="alert">
          {t("managementCenter.loginRequests.ownerOnly")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.tenantLoginRequests" subtitleKey="managementCenter.loginRequests.subtitle">
      <AdminLoginRequestList
        listPath="/tenant/login-requests"
        approvePath={(id) => `/tenant/login-requests/${id}/approve`}
      />
    </PageLayout>
  );
}
```

### 2-8 TenantLoginRequestsPage.test.tsx（新規）
`frontend/src/pages/super-admin/LoginRequestsPage.test.tsx` と同じ書き方（`vi.mock("../../lib/api")`・MemoryRouter・`i18n.changeLanguage("en")`）。`vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }))`。試験 3 本:
- U1 `isTenantOwner: false, loading: false` → ownerOnly の文（en）が出て、`api.get` が呼ばれない。
- U2 `isTenantOwner: true` → `api.get` が `"/tenant/login-requests"` で呼ばれ、行の名前（ROW.full_name）が出る。
- U3 許可ボタン → メモ欄に `phone` を入れて確定 → `api.post` が `("/tenant/login-requests/req-9/approve", { note: "phone" })` で呼ばれる。（確定ボタンの探し方は super-admin の試験と同じにする）

### 2-9 ManagementCenterPage.tsx
- 30 行目 `const { hasPermission, hasAny } = usePermissions();` → `const { hasPermission, hasAny, isTenantOwner } = usePermissions();`
- business の items の `{ to: "notifications",  labelKey: "nav.notifications",  visible: hasPermission("notifications.manage") },` の次の行に:
  `        { to: "login-requests", labelKey: "nav.tenantLoginRequests", visible: isTenantOwner },`

### 2-10 App.tsx
- 93 行目 `import LoginRequestsPage from "./pages/super-admin/LoginRequestsPage";` の次の行に `import TenantLoginRequestsPage from "./pages/management-center/TenantLoginRequestsPage";`
- `/management-center` の入れ子の中、`<Route path="bots"                element={<BotsPage />} />` の次の行に:
  `                      <Route path="login-requests"      element={<TenantLoginRequestsPage />} />`
  （`<Route path="bots"` が 2 か所以上あれば、`/management-center` の入れ子の中のほうに足す。判断できなければ BLOCKED: App.tsx）

### 2-11 NoticeBell.tsx
(a) import に足す: `import { useNavigate } from "react-router-dom";` と `import { usePermissions } from "../hooks/usePermissions";`
(b) `interface NoticeList {` の塊の直後に:
```ts
/** 社員の依頼（会社のオーナーだけ・GET /tenant/login-requests の行のうち使う所だけ） */
interface StaffLoginRequest {
  id: string;
  full_name: string | null;
  email: string | null;
  created_at: string | null;
}

/** 社員の依頼の行を押したときに開く画面 */
export const STAFF_LOGIN_REQUESTS_PATH = "/management-center/login-requests";
```
(c) `const [openRequestId, setOpenRequestId] = useState<string | null>(null);` の次に:
```ts
  const [staffRequests, setStaffRequests] = useState<StaffLoginRequest[]>([]);
  const { isTenantOwner } = usePermissions();
  const navigate = useNavigate();
```
(d) `fetchPending` の try の中を、自分の依頼と社員の依頼を両方読む形にする。
変更前:
```ts
    try {
      const res = await api.get<{ items: PendingLoginRequest[] }>("/login-approvals/pending");
      setRequests(res.items ?? []);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
  }, []);
```
変更後:
```ts
    try {
      const res = await api.get<{ items: PendingLoginRequest[] }>("/login-approvals/pending");
      setRequests(res.items ?? []);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
    if (!isTenantOwner) {
      setStaffRequests([]);
      return;
    }
    try {
      const res = await api.get<{ items: StaffLoginRequest[] }>("/tenant/login-requests");
      setStaffRequests(res.items ?? []);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
  }, [isTenantOwner]);
```
（会社のオーナーには、社員が頼んだときに同じ合図 authLoginRequest が届く（便3）ので、既存の useRealtimeRefresh がそのまま読み直す。新しい合図は足さない）
(e) `handleRequestClick` の塊の直後に:
```ts
  const handleStaffRequestClick = () => {
    setOpen(false);
    navigate(STAFF_LOGIN_REQUESTS_PATH);
  };
```
(f) `const totalUnread = unread + requests.length;` → `const totalUnread = unread + requests.length + staffRequests.length;`
(g) 一覧: `{items.length === 0 && requests.length === 0 ? (` → `{items.length === 0 && requests.length === 0 && staffRequests.length === 0 ? (`。`{requests.map((req) => (` の塊の閉じ `))}` の直後（`{items.map((item) => (` の前）に:
```tsx
          {staffRequests.map((req) => (
            <li key={`staff-login-request-${req.id}`}>
              <NoticeRow
                title={t("notices.kind.staff_login_request", {
                  name: req.full_name || req.email || "-",
                })}
                meta={relativeTime(req.created_at, t, i18n.language)}
                unread
                onClick={handleStaffRequestClick}
              />
            </li>
          ))}
```
(h) 冒頭の説明コメントの `- 本文・Discord の id は扱わない` の行の前に1行:
` * - 会社のオーナーのときは、社員が「会社の管理者に頼む」を押した依頼（GET /tenant/login-requests）も足し、押すと管理センターの許可待ちの画面へ移る（ADR-1063）。`

### 2-12 NoticeBell.test.tsx（既存の試験は変えない）
- `vi.mock("../hooks/usePermissions", () => ({ usePermissions: vi.fn(() => ({ isTenantOwner: false })) }))` を足す（既存の試験は今までどおり isTenantOwner=false で動く）。既存の試験が usePermissions の実物（useApiQuery）に頼っていて、この mock で落ちる → `BLOCKED: NoticeBell.test usePermissions`。
- 試験 2 本を足す:
  - B1 isTenantOwner=true、`/tenant/login-requests` が 1 行（full_name "Sato"）を返す → 鈴の数に 1 足され、行の文に "Sato" が出る。
  - B2 その行を押す → 場所が `/management-center/login-requests` になる（既存の試験の useLocation の見方に合わせる）。
- isTenantOwner=false のときに `/tenant/login-requests` を呼ばないことを 1 本（B3）。

### 2-13 ja.json / en.json（同じ鍵を両方に。既存の鍵の並びの中、近い場所に）
- `nav` に `"tenantLoginRequests"`: ja「ログインの許可待ち」/ en「Login Approvals」
- `managementCenter` に `"loginRequests": { "subtitle", "ownerOnly" }`:
  - subtitle ja「社員が新しい機械で「会社の管理者に頼む」を押した依頼です。本人であることを確かめてから許可してください。」 / en「Requests from staff who chose "Ask my company admin" on a new device. Confirm it is really them before approving.」
  - ownerOnly ja「この画面は会社のオーナーだけが開けます。」 / en「Only the company owner can open this page.」
- `login.deviceApproval` に:
  - askAdmin ja「会社の管理者に頼む」 / en「Ask my company admin」
  - askAdminRequested ja「会社の管理者に知らせました。許可されると、この画面は自動で進みます。」 / en「We let your company admin know. This screen will continue automatically once they approve.」
  - askAdminAlready ja「会社の管理者にはもう知らせています。許可を待ってください。」 / en「Your company admin has already been notified. Please wait for approval.」
  - askAdminNoOwner ja「知らせる先の管理者が会社にいません。運営に連絡してください。」 / en「Your company has no admin to notify. Please contact support.」
  - noTrustedDevice を書き換え: ja「会社の管理者に頼むか、運営に連絡してください。」 / en「Ask your company admin, or contact support.」
- `notices.kind` に `"staff_login_request"`: ja「{{name}} さんが新しい機械からのログインの許可を求めています」 / en「{{name}} is asking to sign in from a new device」

## 3. 手順（全部 `cd <作業場所>` から始める。出力は tail で上限）
1. P1〜P5。
2. §2 の変更。
3. `cd frontend && npm ci 2>&1 | tail -5`（入っていれば省いてよい）
4. `cd frontend && npx tsc --noEmit -p . 2>&1 | tail -20`
5. `cd frontend && npx eslint <§1 の frontend/src の .ts/.tsx を全部> 2>&1 | tail -30`
6. `cd frontend && npm run check:i18n-missing-keys 2>&1 | tail -10 && npm run check:nav-sync 2>&1 | tail -5 && npm run check:page-layout 2>&1 | tail -5 && npm run check:page-folder 2>&1 | tail -5 && npm run check:page-size 2>&1 | tail -5`
7. `cd frontend && npx vitest run src/pages/login/LoginPage.test.tsx src/pages/super-admin/LoginRequestsPage.test.tsx src/pages/management-center/TenantLoginRequestsPage.test.tsx src/components/NoticeBell.test.tsx src/components/DesktopShell.test.tsx src/components/MobileShell.test.tsx 2>&1 | tail -25`（設定ファイルの指定が要るなら package.json の test:unit と同じ `--config vitest.unit.config.ts --project unit` を付ける）
8. `git add` は §1 の 14 個と、このカード以外を入れない。commit 文: `feat(auth): owner approves staff login from management center and bell (ADR-1063 bin4)`（末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。
9. `git push origin release/tenant-owner-bin4-owner-approval-ui 2>&1 | tail -3`

## 4. 想定される分かれ道
BLOCKED: に入ったら、その場で停止し、それまでの出力と §5 の報告を返して終わる（別のやり方を試さない）。
- P1〜P5 が外れた → `BLOCKED: P番号 と見えたもの`。
- 変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
- tsc・eslint・check の何かが失敗 → 自分が足した行の書き写し間違い（字・import の並び・使っていない import）だけ直してよい。それ以外は出力を貼って `BLOCKED: 名前`。eslint の `local/no-japanese-literal` や色・余白の規則に当たったら、その行を報告して BLOCKED（例外のコメントで逃げない）。
- 試験が落ちた → 新しく足した試験の書き方（mock の形・ボタンの探し方）の間違いだけ直してよい。既存の試験が落ちたら直さずに最後の 25 行を貼って `BLOCKED: 試験名`。
- `git status` に §1 とこのカード以外が出た → add せず名前を報告。
- push 拒否 → 最後の 3 行を貼って `BLOCKED: push`（force しない）。

## 5. 報告の形
- 1 行目: `RECEIVED tenant-owner-bin4 HEAD=…`
- 手順 4・5・6・7・9 の出力（tail の範囲）をそのまま貼る。直したところがあれば何をどう直したか。
- 秘密の値は貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
