import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { Toggle } from "../../components/Toggle";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { usePermissions } from "../../hooks/usePermissions";
import { api } from "../../lib/api";
import {
  normalizeOwner,
  type ApiCalendarOwnersResponse,
  type CalendarOwner,
} from "./schedule-owner";
import { LoadingBlock } from "../../components/loading";

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

export default function ScheduleSettingsPage() {
  const { t } = useTranslation();
  const { hasPermission, loading: permsLoading } = usePermissions();
  const [owners, setOwners] = useState<CalendarOwner[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingStaffId, setSavingStaffId] = useState<number | null>(null);
  const [savedStaffId, setSavedStaffId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selfOwner = useMemo(() => owners.find((owner) => owner.isSelf) ?? null, [owners]);
  const otherOwners = useMemo(() => owners.filter((owner) => !owner.isSelf), [owners]);

  const jumpToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    if (permsLoading) return;
    if (!hasPermission("staff.view")) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get<ApiCalendarOwnersResponse>("/calendar/owners");
        if (cancelled) return;
        setOwners(data.owners.map(normalizeOwner));
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : t("common.fetchError"));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [hasPermission, permsLoading, t]);

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
      await api.patch(`/calendar/owners/${owner.userId}`, {
        color: owner.color,
        is_visible: owner.visible,
        share_mode: owner.shareMode,
      });
      setSavedStaffId(owner.staffId);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSavingStaffId(null);
    }
  };

  if (permsLoading) {
    return <div className="page"><LoadingBlock /></div>;
  }

  if (!hasPermission("staff.view")) {
    return (
      <PageLayout navKey="nav.scheduleSettings" subtitleKey="schedule.settingsSubtitle" noScroll>
        <div className="error-message" role="alert">
          {t("schedule.settingsPermissionRequired")}
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.scheduleSettings" subtitleKey="schedule.settingsSubtitle" noScroll>
      <div className="schedule-settings">
        {error && <div className="error-message">{error}</div>}
        {loading ? (
          <LoadingBlock />
        ) : (
          <div className="schedule-settings__shell">
            <nav className="schedule-settings__nav" aria-label={t("schedule.settingsNavigation")}>
              <button
                type="button"
                className="schedule-settings__nav-item"
                onClick={() => jumpToSection("schedule-settings-self")}
              >
                {t("schedule.myCalendars")}
              </button>
              {otherOwners.length > 0 && (
                <button
                  type="button"
                  className="schedule-settings__nav-item"
                  onClick={() => jumpToSection("schedule-settings-others")}
                >
                  {t("schedule.otherCalendars")}
                </button>
              )}
            </nav>

            <div className="schedule-settings__content">
              {selfOwner && (
                <section id="schedule-settings-self" className="schedule-settings__card schedule-settings__section-anchor">
                  <div className="schedule-settings__card-title">{t("schedule.myCalendars")}</div>
                  <div className="schedule-settings__card-body">
                    <div className="schedule-settings__calendar-row">
                      <div className="schedule-settings__row-copy">
                        <OwnerBadge owner={selfOwner} />
                        <span className="schedule-settings__description">{t("schedule.settingsCalendarVisibleDesc")}</span>
                      </div>
                      <div className="schedule-settings__calendar-actions">
                        <input
                          type="color"
                          aria-label={t("schedule.settingsCalendarColor")}
                          value={selfOwner.color}
                          onChange={(event) => updateOwner(selfOwner.staffId, { color: event.target.value })}
                        />
                        <Toggle
                          checked={selfOwner.visible}
                          aria-label={t("schedule.settingsCalendarVisible")}
                          onCheckedChange={(next) => updateOwner(selfOwner.staffId, { visible: next })}
                        />
                        <SelectControl
                          size="sm"
                          fullWidth
                          value={selfOwner.shareMode}
                          onChange={(event) => updateOwner(selfOwner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}
                        >
                          <option value="self">{t("schedule.settingsShareSelf")}</option>
                          <option value="view">{t("schedule.settingsShareView")}</option>
                          <option value="edit">{t("schedule.settingsShareEdit")}</option>
                        </SelectControl>
                        <Button
                          variant="secondary"
                          onClick={() => saveOwner(selfOwner)}
                          disabled={selfOwner.userId == null}
                          loading={savingStaffId === selfOwner.staffId}
                          loadingText={t("common.saving")}
                        >
                          {t("schedule.settingsSave")}
                        </Button>
                        {savedStaffId === selfOwner.staffId && (
                          <span className="schedule-settings__timestamp">
                            <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" /> {t("schedule.settingsSaved")}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {otherOwners.length > 0 && (
                <section id="schedule-settings-others" className="schedule-settings__card schedule-settings__section-anchor">
                  <div className="schedule-settings__card-title">{t("schedule.otherCalendars")}</div>
                  <div className="schedule-settings__card-body">
                    {otherOwners.map((owner) => (
                      <div key={owner.staffId} className="schedule-settings__calendar-row">
                        <div className="schedule-settings__row-copy">
                          <OwnerBadge owner={owner} />
                          <span className="schedule-settings__description">
                            {owner.staffCode}
                          </span>
                        </div>
                        <div className="schedule-settings__calendar-actions">
                          <input
                            type="color"
                            aria-label={t("schedule.settingsCalendarColor")}
                            value={owner.color}
                            onChange={(event) => updateOwner(owner.staffId, { color: event.target.value })}
                          />
                          <Toggle
                            checked={owner.visible}
                            aria-label={t("schedule.settingsCalendarVisible")}
                            onCheckedChange={(next) => updateOwner(owner.staffId, { visible: next })}
                          />
                          <SelectControl
                            size="sm"
                            fullWidth
                            value={owner.shareMode}
                            onChange={(event) => updateOwner(owner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}
                          >
                            <option value="self">{t("schedule.settingsShareSelf")}</option>
                            <option value="view">{t("schedule.settingsShareView")}</option>
                            <option value="edit">{t("schedule.settingsShareEdit")}</option>
                          </SelectControl>
                          <Button
                            variant="secondary"
                            onClick={() => saveOwner(owner)}
                            disabled={owner.userId == null}
                            loading={savingStaffId === owner.staffId}
                            loadingText={t("common.saving")}
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
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
