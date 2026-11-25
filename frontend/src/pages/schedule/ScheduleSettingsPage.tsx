import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { SectionCard } from "../../components/SectionCard";
import { SubMenu } from "../../components/SubMenu";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { usePermissions } from "../../hooks/usePermissions";
import { api } from "../../lib/api";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import { useSeededForm } from "../../lib/query/useSeededForm";
import {
  normalizeOwner,
  type ApiCalendarOwnersResponse,
  type CalendarOwner,
} from "./schedule-owner";
import { LoadingBlock } from "../../components/loading";
import { formatDateInput } from "./schedule-utils";

const EMPTY_OWNERS: CalendarOwner[] = [];

function OwnerBadge({ owner }: { owner: CalendarOwner }) {
  return (
    <span className="schedule-settings__account">
      <span
        className="schedule-settings__avatar schedule-settings__avatar--small"
        style={{ background: owner.color }}
        aria-hidden="true"
      >
        {owner.name.slice(0, 1) || "?"}
      </span>
      <span className="schedule-settings__account-email">
        {owner.name}
      </span>
    </span>
  );
}

type SectionKey = "google" | "self" | "others";

interface GoogleStatus {
  connected: boolean;
  connected_at?: string | null;
}

export default function ScheduleSettingsPage() {
  const { t } = useTranslation();
  const { hasPermission, isTenantAdmin, loading: permsLoading } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const ownersEnabled = !permsLoading && hasPermission("staff.view");
  const ownersQ = useApiQuery<ApiCalendarOwnersResponse>("/calendar/owners", {
    enabled: ownersEnabled,
  });
  const { form: owners, setForm: setOwners, ready } = useSeededForm(
    "calendar/owners",
    ownersQ.data,
    (d) => d.owners.map(normalizeOwner),
    EMPTY_OWNERS,
  );
  const loading = ownersEnabled && !ready && !ownersQ.isError;
  const invalidate = useInvalidateApi();
  const [savingStaffId, setSavingStaffId] = useState<number | null>(null);
  const [savedStaffId, setSavedStaffId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const shownError = error ?? (ownersQ.error ? (ownersQ.error instanceof Error ? ownersQ.error.message : t("common.fetchError")) : null);

  // Google 連携の区画（管理者だけ）
  const gcalStatusQ = useApiQuery<GoogleStatus>("/google-calendar/status", {
    enabled: isTenantAdmin === true,
  });
  const gcalConnected = gcalStatusQ.data?.connected === true;
  const gcalConnectedAt = gcalStatusQ.data?.connected_at ?? null;
  const [connectNoticeOpen, setConnectNoticeOpen] = useState(false);
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [activeSection, setActiveSection] = useState<SectionKey>("google");

  // つないだ後・失敗した後の戻り（?connected=true|false&error=）を帯にする
  useEffect(() => {
    const connected = searchParams.get("connected");
    if (connected === "true") {
      setBanner({ type: "success", message: t("schedule.connectSuccess") });
    } else if (connected === "false") {
      const errorCode = searchParams.get("error");
      setBanner({
        type: "error",
        message: errorCode === "scope_missing" ? t("schedule.connectScopeMissing") : t("schedule.connectError"),
      });
    }
    if (connected) {
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selfOwner = useMemo(() => owners.find((owner) => owner.isSelf) ?? null, [owners]);
  const otherOwners = useMemo(() => owners.filter((owner) => !owner.isSelf), [owners]);

  const jumpToSection = (key: SectionKey) => {
    setActiveSection(key);
    document.getElementById(`schedule-settings-${key}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const startConnect = async () => {
    setConnectNoticeOpen(false);
    try {
      const { auth_url } = await api.get<{ auth_url: string }>("/google-calendar/connect/start");
      window.location.href = auth_url;
    } catch {
      setBanner({ type: "error", message: t("schedule.connectError") });
    }
  };

  const confirmDisconnect = async () => {
    setDisconnecting(true);
    try {
      await api.delete("/google-calendar/connect");
      setDisconnectOpen(false);
      await gcalStatusQ.refetch();
      setBanner({ type: "success", message: t("schedule.disconnectSuccess") });
    } catch {
      setDisconnectOpen(false);
      setBanner({ type: "error", message: t("schedule.disconnectError") });
    } finally {
      setDisconnecting(false);
    }
  };

  const updateOwner = (staffId: number, patch: Partial<CalendarOwner>) => {
    setOwners((current) => current.map((owner) => (
      owner.staffId === staffId ? { ...owner, ...patch } : owner
    )));
  };

  const saveOwner = async (owner: CalendarOwner) => {
    // PATCH のパスは users.id（ADR-1008）。user_id が無い名簿行は保存できない
    if (owner.userId == null) return;
    setSavingStaffId(owner.staffId);
    setSavedStaffId(null);
    setError(null);
    try {
      await api.patch(`/calendar/owners/${owner.userId}`, { color: owner.color });
      setSavedStaffId(owner.staffId);
      void invalidate(["calendar", "owners"]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSavingStaffId(null);
    }
  };

  if (permsLoading) {
    return <div className="page"><LoadingBlock /></div>;
  }

  if (!hasPermission("staff.view") && !isTenantAdmin) {
    return (
      <PageLayout navKey="nav.scheduleSettings" subtitleKey="schedule.settingsSubtitle" noScroll>
        <div className="error-message" role="alert">
          {t("schedule.settingsPermissionRequired")}
        </div>
      </PageLayout>
    );
  }

  const menuItems = [
    ...(isTenantAdmin ? [{ key: "google" as SectionKey, label: t("schedule.settingsGoogleTitle") }] : []),
    ...(ownersEnabled ? [{ key: "self" as SectionKey, label: t("schedule.myCalendars") }] : []),
    ...(ownersEnabled && otherOwners.length > 0
      ? [{ key: "others" as SectionKey, label: t("schedule.otherCalendars") }]
      : []),
  ];

  const renderOwnerRow = (owner: CalendarOwner, description: string | null) => (
    <div key={owner.staffId} className="schedule-settings__calendar-row">
      <div className="schedule-settings__row-copy">
        <OwnerBadge owner={owner} />
        {description && <span className="schedule-settings__description">{description}</span>}
      </div>
      <div className="schedule-settings__calendar-actions">
        <input
          type="color"
          aria-label={t("schedule.settingsCalendarColor")}
          value={owner.color}
          onChange={(event) => updateOwner(owner.staffId, { color: event.target.value })}
        />
        <Button
          variant="secondary"
          onClick={() => saveOwner(owner)}
          disabled={owner.userId == null}
          loading={savingStaffId === owner.staffId}
        >
          {t("schedule.settingsSave")}
        </Button>
        {savedStaffId === owner.staffId && (
          <span className="schedule-settings__timestamp">
            <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> {t("schedule.settingsSaved")}
          </span>
        )}
      </div>
    </div>
  );

  return (
    <PageLayout navKey="nav.scheduleSettings" subtitleKey="schedule.settingsSubtitle" noScroll>
      <div className="schedule-settings">
        {banner && (
          <div className={banner.type === "success" ? "success-message" : "error-message"} role="status">
            {banner.message}
          </div>
        )}
        {shownError && <div className="error-message">{shownError}</div>}
        <div className="schedule-settings__shell">
          <SubMenu
            variant="flat"
            groups={[{ items: menuItems }]}
            activeKey={activeSection}
            onChange={(key) => jumpToSection(key as SectionKey)}
            className="schedule-settings__nav"
          />

          <div className="schedule-settings__content">
            {isTenantAdmin && (
              <section id="schedule-settings-google" className="schedule-settings__section-anchor">
                <SectionCard title={t("schedule.settingsGoogleTitle")}>
                  {gcalConnected ? (
                    <div className="schedule-settings__calendar-row">
                      <div className="schedule-settings__row-copy">
                        <span>{t("schedule.statusConnected")}</span>
                        {gcalConnectedAt && !Number.isNaN(new Date(gcalConnectedAt).getTime()) && (
                          <span className="schedule-settings__description">
                            {t("schedule.settingsConnectedAt")}: {formatDateInput(new Date(gcalConnectedAt))}
                          </span>
                        )}
                      </div>
                      <div className="schedule-settings__calendar-actions">
                        <Button variant="danger" onClick={() => setDisconnectOpen(true)}>
                          {t("schedule.disconnect")}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="schedule-settings__calendar-row">
                      <div className="schedule-settings__row-copy">
                        <span className="schedule-settings__description">{t("schedule.settingsGoogleDesc")}</span>
                      </div>
                      <div className="schedule-settings__calendar-actions">
                        <Button variant="primary" onClick={() => setConnectNoticeOpen(true)}>
                          {t("schedule.connect")}
                        </Button>
                      </div>
                    </div>
                  )}
                </SectionCard>
              </section>
            )}

            {ownersEnabled && (loading ? (
              <LoadingBlock />
            ) : (
              <>
                {selfOwner && (
                  <section id="schedule-settings-self" className="schedule-settings__card schedule-settings__section-anchor">
                    <div className="schedule-settings__card-title">{t("schedule.myCalendars")}</div>
                    <div className="schedule-settings__card-body">
                      {renderOwnerRow(selfOwner, null)}
                    </div>
                  </section>
                )}

                {otherOwners.length > 0 && (
                  <section id="schedule-settings-others" className="schedule-settings__card schedule-settings__section-anchor">
                    <div className="schedule-settings__card-title">{t("schedule.otherCalendars")}</div>
                    <div className="schedule-settings__card-body">
                      {otherOwners.map((owner) => renderOwnerRow(owner, owner.staffCode))}
                    </div>
                  </section>
                )}
              </>
            ))}
          </div>
        </div>
      </div>

      <ConfirmModal
        open={connectNoticeOpen}
        title={t("schedule.connectNoticeTitle")}
        message={
          <>
            <p style={{ margin: 0 }}>{t("schedule.connectNoticeBody")}</p>
            <ul style={{ marginTop: "var(--space-2)", marginBottom: 0, paddingLeft: "var(--space-5)" }}>
              <li>{t("schedule.connectNoticeItemEvents")}</li>
              <li>{t("schedule.connectNoticeItemColors")}</li>
            </ul>
            <p style={{ marginTop: "var(--space-2)", marginBottom: 0 }}>{t("schedule.connectNoticeStop")}</p>
          </>
        }
        confirmLabel={t("schedule.connectNoticeConfirm")}
        onConfirm={() => void startConnect()}
        onCancel={() => setConnectNoticeOpen(false)}
      />
      <ConfirmModal
        open={disconnectOpen}
        danger
        title={t("schedule.disconnectConfirm")}
        message={t("schedule.disconnectNotice")}
        confirmLabel={t("schedule.disconnect")}
        confirmLoading={disconnecting}
        onConfirm={() => void confirmDisconnect()}
        onCancel={() => setDisconnectOpen(false)}
      />
    </PageLayout>
  );
}
