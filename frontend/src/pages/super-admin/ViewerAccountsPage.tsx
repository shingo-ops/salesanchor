/**
 * /super-admin/viewers — 閲覧者（社外の在庫閲覧専用アカウント）の管理画面（ADR-1019 段4a-2）。
 *
 * - 一覧は LINE名・状態・登録日時・期限・操作の5列。行を押すと右から詳細（メール・Discord ID・部屋・目印）が出る（段7）
 * - 詳細スライドで LINE名だけ直せる（段8。メール・Discord ID・状態は直せない）
 * - 一覧・状態変更（本契約・延長〈日数または日付まで〉）。停止とログイン記録は画面から外した（段6。API と CLI は残置）
 * - 左メニューで状態ごとに絞る（?status=）／申込フォームURLのコピー／部屋の無い申込中・お試し中・本契約の人のコード・招待の作り直し（段5・段6）
 * - is_super_admin=true のみアクセス可（Page 内で 403 ガード）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Badge, type BadgeVariant } from "../../components/Badge";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { Modal } from "../../components/Modal";
import { TextField } from "../../components/TextField";
import { Radio } from "../../components/Radio";
import { Select } from "../../components/Select";
import { SubMenu, type SubMenuGroup } from "../../components/SubMenu";
import { LoadingBlock } from "../../components/loading";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";

interface ViewerItem {
  id: number;
  email: string;
  line_name: string;
  inventory_issue: string | null;
  status: string;
  trial_expires_at: string | null;
  created_at: string;
  discord_user_id: string | null;
  discord_channel_id: string | null;
  discord_channel_url: string | null;
  flag_many_ips: boolean;
  flag_shared_ip: boolean;
}

/** 配信先（シート）。配信先の画面と同じ表（/tcg/distribution/targets）を読み書きする。 */
interface SheetItem {
  id: string;
  name: string;
  spreadsheet_id: string;
  sheet_name: string;
  is_active: boolean;
  viewer_account_id: number | null;
  last_distributed_at: string | null;
  last_distributed_count: number | null;
  last_result: string | null;
  deliverable: boolean;
  reason: "manual_off" | "suspended" | "not_contracted" | null;
}

const SHEET_REASON_VARIANT: Record<string, BadgeVariant> = {
  manual_off: "warning",
  suspended: "danger",
  not_contracted: "neutral",
};

const SHEET_REASON_KEY: Record<string, string> = {
  manual_off: "sheetReasonManualOff",
  suspended: "sheetReasonSuspended",
  not_contracted: "sheetReasonNotContracted",
};

type Action = "activate" | "extend";
type ExtendMode = "days" | "date";

const STATUS_VARIANT: Record<string, BadgeVariant> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  pending: "neutral",
  verified: "neutral",
};

const STATUS_KEY: Record<string, string> = {
  pending: "statusPending",
  verified: "statusVerified",
  trial: "statusTrial",
  active: "statusActive",
  suspended: "statusSuspended",
};

/** 左メニューに出す状態（この順）。verified・suspended は出さない（「すべて」には含まれる） */
const MENU_STATUSES = ["pending", "trial", "active"] as const;
type MenuKey = "all" | (typeof MENU_STATUSES)[number];

interface ReissueResult {
  signup_code: string;
  expires_at: string;
  invite_url: string | null;
  message: string;
  viewer: ViewerItem;
}

/** 状態変更の応答のうち、部屋へのお知らせの結果（段10 便2）。 */
interface StatusChangeResult {
  room_notice?: "sent" | "failed" | "no_room" | "no_template" | null;
  room_notice_text?: string | null;
}

/** お客さんが書いた請求先（GET /super-admin/viewers/{id}/billing-profile。無ければ null）。 */
interface BillingProfile {
  party_type: "company" | "individual";
  bill_to_name: string;
  contact_name: string | null;
  postal_code: string;
  address: string;
  phone: string;
  invoice_email: string | null;
  updated_at: string;
}

/** 「請求先フォームを送る」の結果（POST /super-admin/viewers/{id}/send-billing-form）。 */
interface BillingFormSendResult {
  room_notice: "sent" | "failed" | "no_room";
  room_notice_text: string;
  mail_queued: boolean;
  expires_at: string;
}

const LINE_NAME_MAX = 100;

/** 詳細欄からコピーできる文（API の COPYABLE_KEYS と同じ順） */
const COPYABLE_TEMPLATE_KEYS = [
  "signup_request",
  "room_recreated",
  "notice_extended",
  "interview_request",
  "notice_activated",
  "notice_suspended",
] as const;
/** お試しの期限が無い人には作れない文 */
const NEEDS_EXPIRY = new Set<string>(["notice_extended", "interview_request"]);

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function ViewerAccountsPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const f = "superAdmin.viewers";
  const [items, setItems] = useState<ViewerItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [roomNoticeText, setRoomNoticeText] = useState<string | null>(null);
  const [roomNoticeNoTemplate, setRoomNoticeNoTemplate] = useState(false);
  const [pending, setPending] = useState<{ viewer: ViewerItem; action: Action } | null>(null);
  const [daysText, setDaysText] = useState("7");
  const [running, setRunning] = useState(false);
  const [extendMode, setExtendMode] = useState<ExtendMode>("days");
  const [dateText, setDateText] = useState("");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [reissueTarget, setReissueTarget] = useState<ViewerItem | null>(null);
  const [reissueResult, setReissueResult] = useState<ReissueResult | null>(null);
  const [detail, setDetail] = useState<ViewerItem | null>(null);
  const [lineNameDraft, setLineNameDraft] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [savedName, setSavedName] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [sheetModalOpen, setSheetModalOpen] = useState(false);
  const [sheetBookDraft, setSheetBookDraft] = useState("");
  const [sheetTabDraft, setSheetTabDraft] = useState("");
  const [sheetSaving, setSheetSaving] = useState(false);
  const [sheetFormError, setSheetFormError] = useState("");
  const [billingSendResult, setBillingSendResult] = useState<BillingFormSendResult | null>(null);
  const [billingSendError, setBillingSendError] = useState("");

  const statusParam = searchParams.get("status");
  const activeKey: MenuKey = (MENU_STATUSES as readonly string[]).includes(statusParam ?? "")
    ? (statusParam as MenuKey)
    : "all";

  const load = useCallback(async () => {
    setFetching(true);
    try {
      const data = await api.get<{ items: ViewerItem[] }>("/super-admin/viewers");
      setItems(data.items);
      // 開いている詳細は、読み込み直した最新の行に差し替える（操作のあとで古くならないように）
      setDetail(prev => (prev ? data.items.find(i => i.id === prev.id) ?? null : null));
    } catch {
      setError(t(`${f}.loadError`));
    } finally {
      setFetching(false);
    }
  }, [t]);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void load();
    }
  }, [authLoading, isSuperAdmin, load]);

  // 別の人を開いたときと保存が終わったとき（line_name が変わったとき）は、下書きを作り直す
  const detailId = detail?.id ?? null;
  const detailLineName = detail?.line_name ?? "";
  useEffect(() => {
    setLineNameDraft(detailLineName);
  }, [detailId, detailLineName]);
  useEffect(() => {
    setSavedName(false);
    setSaveError("");
    setTemplateKey("");
    setTemplateError(null);
    setBillingSendResult(null);
    setBillingSendError("");
  }, [detailId]);

  // 開いた人のシートを読む（配信先の表から viewer_account_id が一致する1件。1人1シートまで）
  const sheetQuery = useApiQuery<SheetItem[]>("/tcg/distribution/targets", { enabled: detailId !== null });
  const invalidateApi = useInvalidateApi();
  const sheet = detailId === null ? null : (sheetQuery.data?.find(r => r.viewer_account_id === detailId) ?? null);
  const sheetLoading = detailId !== null && sheetQuery.isPending;
  const sheetLoadError = sheetQuery.isError;

  // 開いた人の請求先を読む（行が無ければ null。お客さんが送信したときに変わるので、管理者が送っても取り直さない）
  const billingQuery = useApiQuery<BillingProfile | null>(
    `/super-admin/viewers/${detailId ?? 0}/billing-profile`,
    { enabled: detailId !== null },
  );
  // 行が無いときの null と、想定外の形の応答は「まだ無い」として扱う
  const billing = typeof billingQuery.data?.bill_to_name === "string" ? billingQuery.data : null;
  const billingLoading = detailId !== null && billingQuery.isPending;
  const billingLoadError = billingQuery.isError;

  useEffect(() => {
    setSheetModalOpen(false);
    setSheetFormError("");
  }, [detailId]);

  const openSheetModal = () => {
    setSheetBookDraft(sheet?.spreadsheet_id ?? "");
    setSheetTabDraft(sheet?.sheet_name ?? "");
    setSheetFormError("");
    setSheetModalOpen(true);
  };

  const sheetFormValid = sheetBookDraft.trim() !== "" && sheetTabDraft.trim() !== "";

  const saveSheet = async () => {
    if (!detail || !sheetFormValid) return;
    setSheetSaving(true);
    setSheetFormError("");
    try {
      if (sheet) {
        await api.put(`/tcg/distribution/targets/${sheet.id}`, {
          spreadsheet_id: sheetBookDraft.trim(),
          sheet_name: sheetTabDraft.trim(),
        });
      } else {
        await api.post("/tcg/distribution/targets", {
          name: detail.line_name,
          spreadsheet_id: sheetBookDraft.trim(),
          sheet_name: sheetTabDraft.trim(),
          viewer_account_id: detail.id,
        });
      }
      setSheetModalOpen(false);
      await invalidateApi(["tcg", "distribution", "targets"]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setSheetFormError(t(`${f}.sheetConflictError`));
      else if (e instanceof ApiError && e.status === 422) setSheetFormError(t(`${f}.sheetViewerNotFoundError`));
      else setSheetFormError(t(`${f}.sheetSaveError`));
    } finally {
      setSheetSaving(false);
    }
  };

  const draftTrimmed = lineNameDraft.trim();
  const draftLength = Array.from(draftTrimmed).length;
  const draftValid = draftLength >= 1 && draftLength <= LINE_NAME_MAX;
  const canSaveName =
    detail !== null && draftTrimmed !== detail.line_name && draftValid && !savingName;

  const saveLineName = async () => {
    if (!detail || !canSaveName) return;
    setSavingName(true);
    setSavedName(false);
    setSaveError("");
    try {
      const res = await api.patch<ViewerItem>(`/super-admin/viewers/${detail.id}`, {
        line_name: draftTrimmed,
      });
      setDetail(res);
      setItems(prev => prev.map(i => (i.id === res.id ? res : i)));
      setLineNameDraft(res.line_name);
      setSavedName(true);
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setSaveError(t(`${f}.lineNameInvalid`));
      else if (e instanceof ApiError && e.status === 404) setSaveError(t(`${f}.notFoundError`));
      else setSaveError(t(`${f}.saveError`));
    } finally {
      setSavingName(false);
    }
  };

  const errorMessage = (e: unknown): string => {
    if (e instanceof ApiError) {
      if (e.status === 409) {
        return e.message === "viewer_already_linked"
          ? t(`${f}.alreadyLinkedError`)
          : t(`${f}.conflictError`);
      }
      if (e.status === 404) return t(`${f}.notFoundError`);
    }
    return t(`${f}.genericError`);
  };

  const copyText = (key: string, value: string) => {
    navigator.clipboard.writeText(value).then(
      () => {
        setCopiedKey(key);
        setTimeout(() => setCopiedKey(null), 2000);
      },
      () => setError(t(`${f}.genericError`)),
    );
  };

  const copySignupRequest = async () => {
    setError("");
    try {
      const res = await api.get<{ text: string }>("/super-admin/viewers/signup-request");
      copyText("signupRequest", res.text);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const templateErrorMessage = (e: unknown): string => {
    if (e instanceof ApiError) {
      if (e.status === 409) return t(`${f}.templateNoExpiry`);
      if (e.status === 503) return t(`${f}.templateNotFound`);
      if (e.status === 404) return t(`${f}.notFoundError`);
    }
    return t(`${f}.genericError`);
  };

  const copyTemplate = async () => {
    if (!detail || !templateKey) return;
    setTemplateError(null);
    try {
      const res = await api.get<{ text: string }>(
        `/super-admin/viewers/${detail.id}/template-text?key=${encodeURIComponent(templateKey)}`,
      );
      copyText("template", res.text);
    } catch (e) {
      setTemplateError(templateErrorMessage(e));
    }
  };

  const sendBillingForm = async () => {
    if (!detail || detail.status !== "active") return;
    setRunning(true);
    setBillingSendResult(null);
    setBillingSendError("");
    try {
      const res = await api.post<BillingFormSendResult>(
        `/super-admin/viewers/${detail.id}/send-billing-form`,
        {},
      );
      setBillingSendResult(res);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setBillingSendError(t(`${f}.billingConflictError`));
      else if (e instanceof ApiError && e.status === 503) setBillingSendError(t(`${f}.templateNotFound`));
      else if (e instanceof ApiError && e.status === 404) setBillingSendError(t(`${f}.notFoundError`));
      else setBillingSendError(t(`${f}.genericError`));
    } finally {
      setRunning(false);
    }
  };

  const runReissue = async () => {
    if (!reissueTarget) return;
    setRunning(true);
    setError("");
    try {
      const res = await api.post<{
        signup_code: string;
        expires_at: string;
        invite_url: string | null;
        message: string;
      }>(
        `/super-admin/viewers/${reissueTarget.id}/reissue-signup-code`,
        {},
      );
      setReissueResult({ ...res, viewer: reissueTarget });
      setReissueTarget(null);
      await load();
    } catch (e) {
      setReissueTarget(null);
      setError(errorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  const openAction = (viewer: ViewerItem, action: Action) => {
    setError("");
    setRoomNoticeText(null);
    setRoomNoticeNoTemplate(false);
    setDaysText("7");
    setExtendMode("days");
    setDateText("");
    setPending({ viewer, action });
  };

  const days = Number(daysText);
  const daysValid = daysText.trim() !== "" && Number.isInteger(days) && days >= 1 && days <= 365;

  const todayText = new Date().toLocaleDateString("sv-SE"); // YYYY-MM-DD（端末の日付）
  const dateValid = dateText !== "" && dateText > todayText;
  const extendValid = extendMode === "days" ? daysValid : dateValid;

  const run = async () => {
    if (!pending) return;
    if (pending.action === "extend" && !extendValid) return;
    setRunning(true);
    setError("");
    try {
      const path = `/super-admin/viewers/${pending.viewer.id}/${pending.action}`;
      const res =
        pending.action === "extend"
          ? await api.post<StatusChangeResult>(path, extendMode === "days" ? { days } : { until_date: dateText })
          : await api.post<StatusChangeResult>(path, {});
      // 部屋に送れなかった（failed）か部屋が無い（no_room）ときだけ、送るはずだった文をコピーできるようにする
      const failed = res?.room_notice === "failed" || res?.room_notice === "no_room";
      setRoomNoticeText(failed && res?.room_notice_text ? res.room_notice_text : null);
      // テンプレートの行が無く、部屋に送れなかった（状態は変わっている）
      setRoomNoticeNoTemplate(res?.room_notice === "no_template");
      setPending(null);
      await load();
    } catch (e) {
      setPending(null);
      setError(errorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  if (authLoading) {
    return <LoadingBlock />;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminViewers">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const columns: DataTableColumn<ViewerItem>[] = [
    { key: "line_name", header: t(`${f}.colLineName`) },
    {
      key: "status",
      header: t(`${f}.colStatus`),
      renderCell: row => (
        <Badge variant={STATUS_VARIANT[row.status] ?? "neutral"}>
          {STATUS_KEY[row.status] ? t(`${f}.${STATUS_KEY[row.status]}`) : row.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: t(`${f}.colCreated`),
      renderCell: row => formatDate(row.created_at) ?? t(`${f}.empty`),
    },
    {
      key: "trial_expires_at",
      header: t(`${f}.colExpires`),
      renderCell: row => formatDate(row.trial_expires_at) ?? t(`${f}.empty`),
    },
    {
      key: "actions",
      header: t(`${f}.colActions`),
      renderCell: row => (
        <Stack direction="row" gap="2">
          {row.status === "trial" && (
            <>
              <Button size="sm" variant="primary" onClick={() => openAction(row, "activate")}>
                {t(`${f}.activate`)}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => openAction(row, "extend")}>
                {t(`${f}.extend`)}
              </Button>
            </>
          )}
          {["pending", "trial", "active"].includes(row.status) && !row.discord_channel_url && (
            <Button size="sm" variant="secondary" onClick={() => { setError(""); setReissueTarget(row); }}>
              {t(`${f}.reissue`)}
            </Button>
          )}
        </Stack>
      ),
    },
  ];

  const confirmKey: Record<Action, string> = {
    activate: "confirmActivate",
    extend: "extendTarget",
  };
  const pendingTitle = pending
    ? pending.action === "extend"
      ? t(`${f}.extendTitle`)
      : t(`${f}.activate`)
    : "";

  const countOf = (key: MenuKey) =>
    key === "all" ? items.length : items.filter(i => i.status === key).length;
  const menuLabel = (key: MenuKey) => (key === "all" ? t(`${f}.menuAll`) : t(`${f}.${STATUS_KEY[key]}`));
  const menuGroups: SubMenuGroup<MenuKey>[] = [
    {
      items: (["all", ...MENU_STATUSES] as MenuKey[]).map(key => ({
        key,
        label: menuLabel(key),
        badge: countOf(key),
      })),
    },
  ];
  const handleMenuChange = (key: MenuKey) => {
    if (key === "all") setSearchParams({}, { replace: true });
    else setSearchParams({ status: key }, { replace: true });
  };
  const visibleItems = activeKey === "all" ? items : items.filter(i => i.status === activeKey);

  const copyButton = (key: string, value: string) => (
    <Button size="sm" variant="secondary" onClick={() => copyText(key, value)}>
      {copiedKey === key ? t(`${f}.copied`) : t(`${f}.copy`)}
    </Button>
  );

  return (
    <PageLayout
      navKey="nav.superAdminViewers"
      subtitleKey="superAdmin.viewers.subtitle"
      noScroll
      headerAction={
        <>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => copyText("signupUrl", `${window.location.origin}/viewer/#signup`)}
          >
            {copiedKey === "signupUrl" ? t(`${f}.copied`) : t(`${f}.copySignupUrl`)}
          </Button>
          <Button variant="secondary" size="sm" onClick={copySignupRequest}>
            {copiedKey === "signupRequest" ? t(`${f}.copied`) : t(`${f}.copySignupRequest`)}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => navigate("/super-admin/viewer-templates")}>
            {t(`${f}.templates`)}
          </Button>
        </>
      }
    >
      <div className="hub-shell">
        <SubMenu
          variant="flat"
          className="hub-subnav"
          groups={menuGroups}
          activeKey={activeKey}
          onChange={handleMenuChange}
        />
        <div className="hub-content">
      {error && (
        <div className="error-message" role="alert" data-testid="viewers-error">
          {error}
        </div>
      )}
      {roomNoticeNoTemplate && (
        <div className="error-message" role="alert" data-testid="viewers-room-notice-no-template">
          {t(`${f}.roomNoticeNoTemplate`)}
        </div>
      )}
      {roomNoticeText && (
        <div className="error-message" role="alert" data-testid="viewers-room-notice-failed">
          <p>{t(`${f}.roomNoticeFailed`)}</p>
          <p data-testid="viewers-room-notice-text">{roomNoticeText}</p>
          {copyButton("roomNotice", roomNoticeText)}
        </div>
      )}
      {fetching && items.length === 0 ? (
        <LoadingBlock />
      ) : (
        <DataTable
          columns={columns}
          data={visibleItems}
          rowKey={row => String(row.id)}
          onRowClick={row => setDetail(row)}
          emptyState={<EmptyState title={t("common.noData")} size="compact" />}
        />
      )}
        </div>
      </div>

      <Drawer
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={t(`${f}.detailTitle`)}
        footer={
          detail && (
            <Stack direction="column" gap="2">
              <Select
                size="sm"
                fullWidth
                label={t(`${f}.templatePick`)}
                placeholder={t(`${f}.templatePlaceholder`)}
                options={COPYABLE_TEMPLATE_KEYS.map(k => ({
                  value: k,
                  label: t(`superAdmin.viewerTemplates.names.${k}`),
                  disabled: NEEDS_EXPIRY.has(k) && !detail.trial_expires_at,
                }))}
                value={templateKey}
                onChange={e => {
                  setTemplateKey(e.target.value);
                  setTemplateError(null);
                }}
                error={templateError ?? undefined}
                data-testid="viewers-detail-template"
              />
              <Stack direction="row" gap="2">
                <Button
                  variant="secondary"
                  disabled={!templateKey}
                  onClick={() => { void copyTemplate(); }}
                  data-testid="viewers-detail-template-copy"
                >
                  {copiedKey === "template" ? t(`${f}.copied`) : t(`${f}.copy`)}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => { void saveLineName(); }}
                  disabled={!canSaveName}
                  data-testid="viewers-detail-save"
                >
                  {t("common.save")}
                </Button>
              </Stack>
            </Stack>
          )
        }
      >
        {detail && (
          <div className="form-grid" data-testid="viewers-detail">
            <div className="form-row">
              <TextField
                label={t(`${f}.colLineName`)}
                value={lineNameDraft}
                onChange={e => {
                  setLineNameDraft(e.target.value);
                  setSavedName(false);
                }}
                error={lineNameDraft !== detail.line_name && !draftValid ? t(`${f}.lineNameInvalid`) : undefined}
                data-testid="viewers-detail-line-name"
              />
              {savedName && (
                <div role="status" data-testid="viewers-detail-saved">
                  {t(`${f}.saved`)}
                </div>
              )}
              {saveError && (
                <div className="error-message" role="alert" data-testid="viewers-detail-save-error">
                  {saveError}
                </div>
              )}
            </div>
            <div className="form-row">
              <label>{t(`${f}.colEmail`)}</label>
              <div>{detail.email}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colStatus`)}</label>
              <div>
                <Badge variant={STATUS_VARIANT[detail.status] ?? "neutral"}>
                  {STATUS_KEY[detail.status] ? t(`${f}.${STATUS_KEY[detail.status]}`) : detail.status}
                </Badge>
              </div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colCreated`)}</label>
              <div>{formatDate(detail.created_at) ?? t(`${f}.empty`)}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colExpires`)}</label>
              <div>{formatDate(detail.trial_expires_at) ?? t(`${f}.empty`)}</div>
            </div>
            <div className="form-row">
              <label>{t(`${f}.colDiscord`)}</label>
              <div>{detail.discord_user_id ?? t(`${f}.empty`)}</div>
            </div>
            {detail.discord_channel_url && (
              <div className="form-row">
                <ButtonLink
                  href={detail.discord_channel_url}
                  variant="ghost"
                  size="sm"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t(`${f}.openRoom`)}
                </ButtonLink>
              </div>
            )}
            <div className="form-row">
              <label>{t(`${f}.colFlags`)}</label>
              <Stack direction="row" gap="2">
                {detail.flag_many_ips && <Badge variant="warning">{t(`${f}.flagManyIps`)}</Badge>}
                {detail.flag_shared_ip && <Badge variant="warning">{t(`${f}.flagSharedIp`)}</Badge>}
                {!detail.flag_many_ips && !detail.flag_shared_ip && t(`${f}.flagsNone`)}
              </Stack>
            </div>
            <div className="form-row" data-testid="viewers-detail-sheet">
              <label>{t(`${f}.sheetTitle`)}</label>
              {sheetLoading ? (
                <LoadingBlock />
              ) : sheetLoadError ? (
                <div className="error-message" role="alert" data-testid="viewers-detail-sheet-error">
                  {t(`${f}.sheetLoadError`)}
                </div>
              ) : sheet ? (
                <Stack direction="column" gap="2">
                  <div data-testid="viewers-detail-sheet-name">{sheet.name}</div>
                  <div data-testid="viewers-detail-sheet-last">
                    {t(`${f}.sheetLastDistributed`)}: {formatDate(sheet.last_distributed_at) ?? t(`${f}.empty`)}
                  </div>
                  <div data-testid="viewers-detail-sheet-result">
                    {t(`${f}.sheetLastResult`)}: {sheet.last_result ?? t(`${f}.empty`)}
                  </div>
                  <div>
                    {sheet.reason ? (
                      <Badge variant={SHEET_REASON_VARIANT[sheet.reason] ?? "neutral"}>
                        {t(`${f}.${SHEET_REASON_KEY[sheet.reason] ?? "sheetReasonManualOff"}`)}
                      </Badge>
                    ) : (
                      <Badge variant="success">{t(`${f}.sheetDelivering`)}</Badge>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={openSheetModal}
                    data-testid="viewers-detail-sheet-edit"
                  >
                    {t(`${f}.sheetEdit`)}
                  </Button>
                </Stack>
              ) : (
                <EmptyState
                  title={t(`${f}.sheetEmpty`)}
                  size="compact"
                  action={
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={openSheetModal}
                      data-testid="viewers-detail-sheet-add"
                    >
                      {t(`${f}.sheetAdd`)}
                    </Button>
                  }
                />
              )}
            </div>
            <div className="form-row" data-testid="viewers-detail-billing">
              <label>{t(`${f}.billingTitle`)}</label>
              {billingLoading ? (
                <LoadingBlock />
              ) : billingLoadError ? (
                <div className="error-message" role="alert" data-testid="viewers-detail-billing-error">
                  {t(`${f}.billingLoadError`)}
                </div>
              ) : billing ? (
                <Stack direction="column" gap="2">
                  <div data-testid="viewers-detail-billing-party">
                    {t(`${f}.billingPartyType`)}: {t(`${f}.${billing.party_type === "company" ? "billingCompany" : "billingIndividual"}`)}
                  </div>
                  <div data-testid="viewers-detail-billing-name">
                    {t(`${f}.billingName`)}: {billing.bill_to_name}
                  </div>
                  {billing.contact_name && (
                    <div data-testid="viewers-detail-billing-contact">
                      {t(`${f}.billingContact`)}: {billing.contact_name}
                    </div>
                  )}
                  <div data-testid="viewers-detail-billing-postal">
                    {t(`${f}.billingPostal`)}: {billing.postal_code.slice(0, 3)}-{billing.postal_code.slice(3)}
                  </div>
                  <div data-testid="viewers-detail-billing-address">
                    {t(`${f}.billingAddress`)}: {billing.address}
                  </div>
                  <div data-testid="viewers-detail-billing-phone">
                    {t(`${f}.billingPhone`)}: {billing.phone}
                  </div>
                  <div data-testid="viewers-detail-billing-email">
                    {t(`${f}.billingEmail`)}: {billing.invoice_email ?? t(`${f}.empty`)}
                  </div>
                </Stack>
              ) : (
                <EmptyState title={t(`${f}.billingEmpty`)} size="compact" />
              )}
              {detail.status === "active" && (
                <Stack direction="column" gap="2">
                  <div>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={running}
                      onClick={() => { void sendBillingForm(); }}
                      data-testid="viewers-detail-billing-send"
                    >
                      {t(`${f}.billingSend`)}
                    </Button>
                  </div>
                  {billingSendError && (
                    <div className="error-message" role="alert" data-testid="viewers-detail-billing-send-error">
                      {billingSendError}
                    </div>
                  )}
                  {billingSendResult && (
                    <div data-testid="viewers-detail-billing-send-result">
                      <p data-testid="viewers-detail-billing-room">
                        {t(`${f}.billingRoom_${billingSendResult.room_notice}`)}
                      </p>
                      {billingSendResult.mail_queued && <p>{t(`${f}.billingMailQueued`)}</p>}
                      <p>
                        {t(`${f}.billingExpires`)}: {formatDate(billingSendResult.expires_at)}
                      </p>
                      {billingSendResult.room_notice !== "sent" && (
                        <>
                          <p data-testid="viewers-detail-billing-text">{billingSendResult.room_notice_text}</p>
                          {copyButton("billingForm", billingSendResult.room_notice_text)}
                        </>
                      )}
                    </div>
                  )}
                </Stack>
              )}
            </div>
          </div>
        )}
      </Drawer>

      <Modal
        open={sheetModalOpen}
        onClose={() => setSheetModalOpen(false)}
        title={sheet ? t(`${f}.sheetEdit`) : t(`${f}.sheetAdd`)}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setSheetModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="primary"
              onClick={() => { void saveSheet(); }}
              disabled={sheetSaving || !sheetFormValid}
              data-testid="viewers-sheet-save"
            >
              {t("common.save")}
            </Button>
          </>
        }
      >
        <Stack direction="column" gap="2">
          <TextField
            label={t(`${f}.sheetBookId`)}
            value={sheetBookDraft}
            onChange={e => setSheetBookDraft(e.target.value)}
            data-testid="viewers-sheet-book"
          />
          <TextField
            label={t(`${f}.sheetTabName`)}
            value={sheetTabDraft}
            onChange={e => setSheetTabDraft(e.target.value)}
            data-testid="viewers-sheet-tab"
          />
          {sheetFormError && (
            <div className="error-message" role="alert" data-testid="viewers-sheet-form-error">
              {sheetFormError}
            </div>
          )}
        </Stack>
      </Modal>

      <Modal
        open={reissueTarget !== null}
        onClose={() => setReissueTarget(null)}
        title={t(`${f}.reissue`)}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setReissueTarget(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="primary"
              onClick={() => { void runReissue(); }}
              disabled={running}
              data-testid="viewers-reissue-run"
            >
              {t(`${f}.run`)}
            </Button>
          </>
        }
      >
        {reissueTarget && (
          <p>
            {t(`${f}.confirmReissue`, { name: reissueTarget.line_name, email: reissueTarget.email })}
          </p>
        )}
      </Modal>

      <Modal
        open={reissueResult !== null}
        onClose={() => setReissueResult(null)}
        title={t(`${f}.reissueTitle`)}
        size="sm"
        footer={
          <Button variant="secondary" onClick={() => setReissueResult(null)}>
            {t("common.close")}
          </Button>
        }
      >
        {reissueResult && (
          <>
            <p>{t(`${f}.reissueOnlyOnce`)}</p>
            <p>
              {t(`${f}.reissueCode`)}: <span data-testid="viewers-reissue-code">{reissueResult.signup_code}</span>
              {copyButton("code", reissueResult.signup_code)}
            </p>
            <p>
              {t(`${f}.reissueExpires`)}: {formatDate(reissueResult.expires_at)}
            </p>
            <p>
              {t(`${f}.reissueMessage`)}: {copyButton("reissueMessage", reissueResult.message)}
            </p>
            <p>
              {t(`${f}.reissueInvite`)}:{" "}
              {reissueResult.invite_url ? (
                <>
                  <span data-testid="viewers-reissue-invite">{reissueResult.invite_url}</span>
                  {copyButton("invite", reissueResult.invite_url)}
                </>
              ) : (
                <span data-testid="viewers-reissue-invite-failed">{t(`${f}.reissueInviteFailed`)}</span>
              )}
            </p>
          </>
        )}
      </Modal>

      <Modal
        open={pending !== null}
        onClose={() => setPending(null)}
        title={pendingTitle}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setPending(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="primary"
              onClick={() => { void run(); }}
              disabled={running || (pending?.action === "extend" && !extendValid)}
              data-testid="viewers-run"
            >
              {t(`${f}.run`)}
            </Button>
          </>
        }
      >
        {pending && (
          <>
            <p>
              {t(`${f}.${confirmKey[pending.action]}`, {
                name: pending.viewer.line_name,
                email: pending.viewer.email,
              })}
            </p>
            {pending.action === "extend" && (
              <>
                <Radio
                  name="viewers-extend-mode"
                  label={t(`${f}.extendByDays`)}
                  checked={extendMode === "days"}
                  onChange={() => setExtendMode("days")}
                  data-testid="viewers-extend-mode-days"
                />
                <Radio
                  name="viewers-extend-mode"
                  label={t(`${f}.extendByDate`)}
                  checked={extendMode === "date"}
                  onChange={() => setExtendMode("date")}
                  data-testid="viewers-extend-mode-date"
                />
                {extendMode === "days" ? (
                  <TextField
                    label={t(`${f}.extendDays`)}
                    type="number"
                    min={1}
                    max={365}
                    step={1}
                    value={daysText}
                    onChange={e => setDaysText(e.target.value)}
                    data-testid="viewers-extend-days"
                  />
                ) : (
                  <TextField
                    label={t(`${f}.extendDateLabel`)}
                    type="date"
                    min={todayText}
                    value={dateText}
                    onChange={e => setDateText(e.target.value)}
                    data-testid="viewers-extend-date"
                  />
                )}
              </>
            )}
          </>
        )}
      </Modal>

    </PageLayout>
  );
}
