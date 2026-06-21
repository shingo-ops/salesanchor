import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { Card } from "../../components/Card";
import { PageLayout } from "../../components/PageLayout";
import { CALENDARS, type CalendarId, cssVar } from "../../features/schedule/calendars.config";
import { SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";

type SectionKey = "display" | "sync" | "management" | "automation";
type ShareMode = "self" | "view" | "edit";
type ViewMode = "day" | "week" | "month";
type RowMode = "standard" | "compact";
type Timezone = "tokyo" | "utc" | "la" | "berlin";
type SyncDirection = "two" | "push" | "pull";
type SyncInterval = "5" | "15" | "30" | "manual";
type ReminderValue = "none" | "10" | "30" | "60" | "1440";
type DefaultLength = "30" | "60" | "120";

interface SettingsCalendar {
  name: string;
  colorVar: string;
  visible: boolean;
  share: ShareMode;
}

interface CustomCalendar extends SettingsCalendar {
  id: string;
}

interface SettingsState {
  display: {
    view: ViewMode;
    weekStart: "sun" | "mon";
    startHour: string;
    endHour: string;
    rowH: RowMode;
    tz: Timezone;
    workingHours: boolean;
  };
  sync: {
    dir: SyncDirection;
    interval: SyncInterval;
    targets: Record<CalendarId, boolean>;
  };
  management: Record<CalendarId, SettingsCalendar>;
  customCalendars: CustomCalendar[];
  automation: {
    autoShip: boolean;
    autoBill: boolean;
    autoBuy: boolean;
    reminder: ReminderValue;
    defaultLen: DefaultLength;
  };
}

interface CalendarEditorState {
  id: string;
  isNew: boolean;
  name: string;
  colorVar: string;
  share: ShareMode;
  visible: boolean;
}

interface CalendarRow {
  id: string;
  name: string;
  colorVar: string;
  visible: boolean;
  share: ShareMode;
  isBase: boolean;
}

const COLOR_PALETTE = [
  "--cal-personal",
  "--cal-meeting",
  "--cal-purchase",
  "--cal-shipping",
  "--cal-billing",
  "--cal-release",
  "--cal-holiday",
  "--accent",
  "--calendar-google-blue",
] as const;

const DISPLAY_TIMEZONES: Timezone[] = [
  "tokyo",
  "utc",
  "la",
  "berlin",
];

const SECTION_SUBTITLE_KEYS: Record<SectionKey, string> = {
  display: "schedule.settingsDisplaySubtitle",
  sync: "schedule.settingsSyncSubtitle",
  management: "schedule.settingsCalendarSubtitle",
  automation: "schedule.settingsAutomationSubtitle",
};

function cloneState(state: SettingsState): SettingsState {
  return {
    ...state,
    display: { ...state.display },
    sync: { ...state.sync, targets: { ...state.sync.targets } },
    management: Object.fromEntries(
      Object.entries(state.management).map(([key, value]) => [key, { ...value }]),
    ) as Record<CalendarId, SettingsCalendar>,
    customCalendars: state.customCalendars.map((calendar) => ({ ...calendar })),
    automation: { ...state.automation },
  };
}

function createInitialState(): SettingsState {
  const management = Object.fromEntries(
    CALENDARS.map((calendar) => [
      calendar.id,
      {
        name: calendar.label,
        colorVar: calendar.colorVar,
        visible: true,
        share: "self" as ShareMode,
      },
    ]),
  ) as Record<CalendarId, SettingsCalendar>;

  return {
    display: {
      view: "week",
      weekStart: "sun",
      startHour: "7",
      endHour: "22",
      rowH: "standard",
      tz: "tokyo",
      workingHours: true,
    },
    sync: {
      dir: "two",
      interval: "15",
      targets: {
        personal: true,
        meeting: true,
        purchase: true,
        shipping: true,
        billing: true,
        release: false,
        holiday: false,
      },
    },
    management,
    customCalendars: [],
    automation: {
      autoShip: true,
      autoBill: true,
      autoBuy: false,
      reminder: "10",
      defaultLen: "60",
    },
  };
}

function SettingsRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="schedule-settings__row">
      <div className="schedule-settings__row-copy">
        <span className="schedule-settings__label">{label}</span>
        {description && <span className="schedule-settings__description">{description}</span>}
      </div>
      <div className="schedule-settings__row-control">{children}</div>
    </div>
  );
}

function CalendarSwatch({
  colorVar,
  selected,
  onClick,
}: {
  colorVar: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`schedule-color-swatch${selected ? " schedule-color-swatch--selected" : ""}`}
      style={{ background: cssVar(colorVar) }}
      onClick={onClick}
      aria-pressed={selected}
      aria-label={colorVar}
    />
  );
}

function CalendarEditDialog({
  open,
  title,
  state,
  onName,
  onColor,
  onShare,
  onVisible,
  onClose,
  onSave,
  onDelete,
}: {
  open: boolean;
  title: string;
  state: CalendarEditorState | null;
  onName: (value: string) => void;
  onColor: (value: string) => void;
  onShare: (value: ShareMode) => void;
  onVisible: (value: boolean) => void;
  onClose: () => void;
  onSave: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();

  if (!open || !state) return null;

  return (
    <>
      <div className="schedule-dialog__backdrop" onClick={onClose} />
      <div className="schedule-dialog">
        <div className="schedule-dialog__header">
          <div className="schedule-dialog__title">{title}</div>
          <Button variant="ghost" size="sm" iconOnly aria-label={t("common.close")} onClick={onClose}>
            <SCHEDULE_SETTINGS_ICONS.close size={18} aria-hidden="true" />
          </Button>
        </div>
        <div className="schedule-dialog__body">
          <label className="schedule-field">
            <span className="schedule-field__label">{t("schedule.settingsCalendarName")}</span>
            <input
              className="schedule-input"
              value={state.name}
              onChange={(event) => onName(event.target.value)}
            />
          </label>
          <div className="schedule-field">
            <span className="schedule-field__label">{t("schedule.settingsCalendarColor")}</span>
            <div className="schedule-color-grid">
              {COLOR_PALETTE.map((colorVar) => (
                <CalendarSwatch
                  key={colorVar}
                  colorVar={colorVar}
                  selected={state.colorVar === colorVar}
                  onClick={() => onColor(colorVar)}
                />
              ))}
            </div>
          </div>
          <label className="schedule-field">
            <span className="schedule-field__label">{t("schedule.settingsCalendarShare")}</span>
            <select
              className="schedule-select"
              value={state.share}
              onChange={(event) => onShare(event.target.value as ShareMode)}
            >
              <option value="self">{t("schedule.settingsShareSelf")}</option>
              <option value="view">{t("schedule.settingsShareView")}</option>
              <option value="edit">{t("schedule.settingsShareEdit")}</option>
            </select>
          </label>
          <SettingsRow
            label={t("schedule.settingsCalendarVisible")}
            description={t("schedule.settingsCalendarVisibleDesc")}
          >
            <label className="toggle-switch">
              <input type="checkbox" checked={state.visible} onChange={(event) => onVisible(event.target.checked)} />
              <span className="toggle-switch-slider" />
            </label>
          </SettingsRow>
        </div>
        <div className="schedule-dialog__footer">
          <Button variant="danger" onClick={onDelete}>
            {t("common.delete")}
          </Button>
          <div className="schedule-dialog__footer-spacer" />
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" onClick={onSave}>
            {t("common.save")}
          </Button>
        </div>
      </div>
    </>
  );
}

export default function ScheduleSettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const navRefs = useRef<Record<SectionKey, HTMLDivElement | null>>({
    display: null,
    sync: null,
    management: null,
    automation: null,
  });

  const [settings, setSettings] = useState<SettingsState>(() => createInitialState());
  const [savedSettings, setSavedSettings] = useState<SettingsState>(() => cloneState(createInitialState()));
  const [activeSection, setActiveSection] = useState<SectionKey>("display");
  const [dirty, setDirty] = useState(false);
  const [calendarEditor, setCalendarEditor] = useState<CalendarEditorState | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const focusSection = (section: SectionKey) => {
    setActiveSection(section);
    navRefs.current[section]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const markDirty = (next: SettingsState) => {
    setSettings(next);
    setDirty(true);
  };

  const updateManagement = (id: CalendarId, patch: Partial<SettingsCalendar>) => {
    markDirty({
      ...settings,
      management: {
        ...settings.management,
        [id]: {
          ...settings.management[id],
          ...patch,
        },
      },
    });
  };

  const updateCustomCalendar = (id: string, patch: Partial<SettingsCalendar>) => {
    markDirty({
      ...settings,
      customCalendars: settings.customCalendars.map((calendar) => (
        calendar.id === id ? { ...calendar, ...patch } : calendar
      )),
    });
  };

  const openEditor = (kind: "base" | "custom" | "new", id?: string) => {
    if (kind === "new") {
      setCalendarEditor({
        id: `custom-${Date.now()}`,
        isNew: true,
        name: t("schedule.settingsNewCalendarDefault"),
        colorVar: "--cal-personal",
        share: "self",
        visible: true,
      });
      return;
    }

    if (kind === "base" && id) {
      const calendar = settings.management[id as CalendarId];
      setCalendarEditor({
        id,
        isNew: false,
        name: calendar.name,
        colorVar: calendar.colorVar,
        share: calendar.share,
        visible: calendar.visible,
      });
      return;
    }

    if (kind === "custom" && id) {
      const calendar = settings.customCalendars.find((item) => item.id === id);
      if (!calendar) return;
      setCalendarEditor({
        id,
        isNew: false,
        name: calendar.name,
        colorVar: calendar.colorVar,
        share: calendar.share,
        visible: calendar.visible,
      });
    }
  };

  const saveEditor = () => {
    if (!calendarEditor) return;
    if (calendarEditor.isNew) {
      const nextCustom = {
        id: calendarEditor.id,
        name: calendarEditor.name.trim() || t("schedule.settingsNewCalendarDefault"),
        colorVar: calendarEditor.colorVar,
        visible: calendarEditor.visible,
        share: calendarEditor.share,
      };
      markDirty({
        ...settings,
        customCalendars: [...settings.customCalendars, nextCustom],
      });
    } else if (settings.management[calendarEditor.id as CalendarId]) {
      updateManagement(calendarEditor.id as CalendarId, {
        name: calendarEditor.name.trim() || settings.management[calendarEditor.id as CalendarId].name,
        colorVar: calendarEditor.colorVar,
        share: calendarEditor.share,
        visible: calendarEditor.visible,
      });
    } else {
      updateCustomCalendar(calendarEditor.id, {
        name: calendarEditor.name.trim() || calendarEditor.name,
        colorVar: calendarEditor.colorVar,
        share: calendarEditor.share,
        visible: calendarEditor.visible,
      });
    }
    setCalendarEditor(null);
    setBanner(t("schedule.settingsSavedLocal"));
  };

  const deleteEditor = () => {
    if (!calendarEditor) return;
    if (calendarEditor.isNew) {
      setCalendarEditor(null);
      return;
    }

    if (settings.management[calendarEditor.id as CalendarId]) {
      updateManagement(calendarEditor.id as CalendarId, { visible: false });
    } else {
      markDirty({
        ...settings,
        customCalendars: settings.customCalendars.filter((calendar) => calendar.id !== calendarEditor.id),
      });
    }
    setCalendarEditor(null);
    setBanner(t("schedule.settingsHiddenLocal"));
  };

  const cancelAll = () => {
    setSettings(cloneState(savedSettings));
    setDirty(false);
    setCalendarEditor(null);
    setBanner(t("schedule.settingsReverted"));
  };

  const saveAll = () => {
    setSavedSettings(cloneState(settings));
    setDirty(false);
    setBanner(t("schedule.settingsSavedLocal"));
  };

  const baseCalendarRows: CalendarRow[] = CALENDARS.map((calendar) => ({
    id: calendar.id,
    name: settings.management[calendar.id].name,
    colorVar: settings.management[calendar.id].colorVar,
    visible: settings.management[calendar.id].visible,
    share: settings.management[calendar.id].share,
    isBase: true,
  }));

  const customCalendarRows: CalendarRow[] = settings.customCalendars.map((calendar) => ({
    id: calendar.id,
    name: calendar.name,
    colorVar: calendar.colorVar,
    visible: calendar.visible,
    share: calendar.share,
    isBase: false,
  }));

  const calendarRows = [...baseCalendarRows, ...customCalendarRows];
  const activeSubtitleKey = SECTION_SUBTITLE_KEYS[activeSection];

  return (
    <PageLayout navKey="nav.schedule" subtitleKey="schedule.settingsSubtitle">
      <div className="schedule-settings">
        <div className="schedule-settings__shell">
          <nav className="schedule-settings__nav" aria-label={t("schedule.settingsNavigation")}>
            {([
              ["display", t("schedule.settingsDisplayTitle"), SCHEDULE_SETTINGS_ICONS.display],
              ["sync", t("schedule.settingsSyncTitle"), SCHEDULE_SETTINGS_ICONS.sync],
              ["management", t("schedule.settingsCalendarTitle"), SCHEDULE_SETTINGS_ICONS.calendar],
              ["automation", t("schedule.settingsAutomationTitle"), SCHEDULE_SETTINGS_ICONS.automation],
            ] as const).map(([key, label, Icon]) => (
              <button
                key={key}
                type="button"
                className={`schedule-settings__nav-item${activeSection === key ? " schedule-settings__nav-item--active" : ""}`}
                onClick={() => focusSection(key)}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </button>
            ))}
          </nav>

          <div className="schedule-settings__content">
            <header className="schedule-settings__header">
              <button className="schedule-back-button" onClick={() => navigate("/schedule")} type="button">
                <SCHEDULE_SETTINGS_ICONS.back size={18} aria-hidden="true" />
                <span>{t("schedule.settingsBack")}</span>
              </button>
              <div className="schedule-settings__header-copy">
                <p className="schedule-settings__eyebrow">{t("schedule.settingsTitle")}</p>
                <div className="schedule-settings__title-row">
                  <span className="schedule-settings__avatar">S</span>
                  <div>
                    <div className="schedule-settings__title">{t("schedule.settingsTitle")}</div>
                    <div className="schedule-settings__subtitle">{t(activeSubtitleKey)}</div>
                  </div>
                </div>
              </div>
            </header>

            {banner && <div className="schedule-settings__banner">{banner}</div>}

          <div ref={(node) => { navRefs.current.display = node; }} className="schedule-settings__section-anchor" />
          <Card variant="container" density="compact" className="schedule-settings__card">
            <div className="schedule-settings__card-title">{t("schedule.settingsDisplayTitle")}</div>
            <div className="schedule-settings__card-body">
              <SettingsRow label={t("schedule.settingsDefaultView")}>
                <select
                  className="schedule-select"
                  value={settings.display.view}
                  onChange={(event) => markDirty({ ...settings, display: { ...settings.display, view: event.target.value as ViewMode } })}
                >
                  <option value="day">{t("schedule.dayView")}</option>
                  <option value="week">{t("schedule.weekView")}</option>
                  <option value="month">{t("schedule.monthView")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsWeekStart")}>
                <select
                  className="schedule-select"
                  value={settings.display.weekStart}
                  onChange={(event) => markDirty({ ...settings, display: { ...settings.display, weekStart: event.target.value as "sun" | "mon" } })}
                >
                  <option value="sun">{t("schedule.settingsWeekStartSun")}</option>
                  <option value="mon">{t("schedule.settingsWeekStartMon")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsWorkingHours")}>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={settings.display.workingHours}
                    onChange={(event) => markDirty({ ...settings, display: { ...settings.display, workingHours: event.target.checked } })}
                  />
                  <span className="toggle-switch-slider" />
                </label>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsTimeRange")}>
                <div className="schedule-settings__range">
                  <select
                    className="schedule-select"
                    value={settings.display.startHour}
                    onChange={(event) => markDirty({ ...settings, display: { ...settings.display, startHour: event.target.value } })}
                  >
                    {Array.from({ length: 24 }, (_, hour) => hour).map((hour) => (
                      <option key={hour} value={String(hour)}>{`${hour}:00`}</option>
                    ))}
                  </select>
                  <span>〜</span>
                  <select
                    className="schedule-select"
                    value={settings.display.endHour}
                    onChange={(event) => markDirty({ ...settings, display: { ...settings.display, endHour: event.target.value } })}
                  >
                    {Array.from({ length: 24 }, (_, hour) => hour).map((hour) => (
                      <option key={hour} value={String(hour)}>{`${hour}:00`}</option>
                    ))}
                  </select>
                </div>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsRowHeight")}>
                <select
                  className="schedule-select"
                  value={settings.display.rowH}
                  onChange={(event) => markDirty({ ...settings, display: { ...settings.display, rowH: event.target.value as RowMode } })}
                >
                  <option value="standard">{t("schedule.settingsRowHeightStandard")}</option>
                  <option value="compact">{t("schedule.settingsRowHeightCompact")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsTimezone")}>
                <select
                  className="schedule-select"
                  value={settings.display.tz}
                  onChange={(event) => markDirty({ ...settings, display: { ...settings.display, tz: event.target.value as Timezone } })}
                >
                  {DISPLAY_TIMEZONES.map((timezone) => (
                    <option key={timezone} value={timezone}>
                      {timezone === "tokyo"
                        ? t("schedule.settingsTimezoneTokyo")
                        : timezone === "utc"
                          ? t("schedule.settingsTimezoneUtc")
                          : timezone === "la"
                            ? t("schedule.settingsTimezoneLa")
                            : t("schedule.settingsTimezoneBerlin")}
                    </option>
                  ))}
                </select>
              </SettingsRow>
            </div>
          </Card>

          <div ref={(node) => { navRefs.current.sync = node; }} className="schedule-settings__section-anchor" />
          <Card variant="container" density="compact" className="schedule-settings__card">
            <div className="schedule-settings__card-title">{t("schedule.settingsSyncTitle")}</div>
            <div className="schedule-settings__card-body">
              <SettingsRow label={t("schedule.settingsSyncAccount")}>
                <div className="schedule-settings__account">
                  <span className="schedule-settings__avatar schedule-settings__avatar--small">S</span>
                  <div>
                    <div className="schedule-settings__account-email">shingo@highlife.jp</div>
                    <Badge variant="success" appearance="soft" size="sm">
                      {t("schedule.settingsConnected")}
                    </Badge>
                  </div>
                </div>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsSyncMode")}>
                <select
                  className="schedule-select"
                  value={settings.sync.dir}
                  onChange={(event) => markDirty({ ...settings, sync: { ...settings.sync, dir: event.target.value as SyncDirection } })}
                >
                  <option value="two">{t("schedule.settingsSyncBidirectional")}</option>
                  <option value="push">{t("schedule.settingsSyncPush")}</option>
                  <option value="pull">{t("schedule.settingsSyncPull")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsSyncInterval")}>
                <select
                  className="schedule-select"
                  value={settings.sync.interval}
                  onChange={(event) => markDirty({ ...settings, sync: { ...settings.sync, interval: event.target.value as SyncInterval } })}
                >
                  <option value="5">{t("schedule.settingsEvery5")}</option>
                  <option value="15">{t("schedule.settingsEvery15")}</option>
                  <option value="30">{t("schedule.settingsEvery30")}</option>
                  <option value="manual">{t("schedule.settingsManual")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsLastSync")}>
                <span className="schedule-settings__timestamp">2026/06/20 11:02</span>
              </SettingsRow>
              <div className="schedule-settings__subsection-title">{t("schedule.settingsSyncTargets")}</div>
              <div className="schedule-settings__targets">
                {CALENDARS.filter((calendar) => calendar.id !== "holiday").map((calendar) => (
                  <div key={calendar.id} className="schedule-settings__target-row">
                    <div className="schedule-settings__target-copy">
                      <span className="schedule-settings__target-swatch" style={{ background: cssVar(calendar.colorVar) }} />
                      <span>{calendar.label}</span>
                    </div>
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={settings.sync.targets[calendar.id]}
                        onChange={(event) => markDirty({
                          ...settings,
                          sync: { ...settings.sync, targets: { ...settings.sync.targets, [calendar.id]: event.target.checked } },
                        })}
                      />
                      <span className="toggle-switch-slider" />
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <div ref={(node) => { navRefs.current.management = node; }} className="schedule-settings__section-anchor" />
          <Card variant="container" density="compact" className="schedule-settings__card">
            <div className="schedule-settings__card-title">{t("schedule.settingsCalendarTitle")}</div>
            <div className="schedule-settings__card-body">
              <div className="schedule-settings__calendar-list">
                {calendarRows.map((calendar) => (
                  <div key={calendar.id} className="schedule-settings__calendar-row">
                    <div className="schedule-settings__target-copy">
                      <span className="schedule-settings__target-swatch" style={{ background: cssVar(calendar.colorVar) }} />
                      <span>{calendar.name}</span>
                    </div>
                    <div className="schedule-settings__calendar-actions">
                      <Button variant="secondary" size="sm" onClick={() => openEditor(calendar.isBase ? "base" : "custom", calendar.id)}>
                        {t("schedule.settingsEdit")}
                      </Button>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={calendar.visible}
                          onChange={(event) => (
                            calendar.isBase
                              ? updateManagement(calendar.id as CalendarId, { visible: event.target.checked })
                              : updateCustomCalendar(calendar.id, { visible: event.target.checked })
                          )}
                        />
                        <span className="toggle-switch-slider" />
                      </label>
                    </div>
                  </div>
                ))}
              </div>
              <Button variant="outline" onClick={() => openEditor("new")}>
                {t("schedule.settingsCreateCalendar")}
              </Button>
            </div>
          </Card>

          <div ref={(node) => { navRefs.current.automation = node; }} className="schedule-settings__section-anchor" />
          <Card variant="container" density="compact" className="schedule-settings__card">
            <div className="schedule-settings__card-title">{t("schedule.settingsAutomationTitle")}</div>
            <div className="schedule-settings__card-body">
              <SettingsRow
                label={t("schedule.settingsAutoShip")}
                description={t("schedule.settingsAutoShipDesc")}
              >
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={settings.automation.autoShip}
                    onChange={(event) => markDirty({ ...settings, automation: { ...settings.automation, autoShip: event.target.checked } })}
                  />
                  <span className="toggle-switch-slider" />
                </label>
              </SettingsRow>
              <SettingsRow
                label={t("schedule.settingsAutoBill")}
                description={t("schedule.settingsAutoBillDesc")}
              >
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={settings.automation.autoBill}
                    onChange={(event) => markDirty({ ...settings, automation: { ...settings.automation, autoBill: event.target.checked } })}
                  />
                  <span className="toggle-switch-slider" />
                </label>
              </SettingsRow>
              <SettingsRow
                label={t("schedule.settingsAutoBuy")}
                description={t("schedule.settingsAutoBuyDesc")}
              >
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={settings.automation.autoBuy}
                    onChange={(event) => markDirty({ ...settings, automation: { ...settings.automation, autoBuy: event.target.checked } })}
                  />
                  <span className="toggle-switch-slider" />
                </label>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsReminder")}>
                <select
                  className="schedule-select"
                  value={settings.automation.reminder}
                  onChange={(event) => markDirty({ ...settings, automation: { ...settings.automation, reminder: event.target.value as ReminderValue } })}
                >
                  <option value="none">{t("schedule.settingsReminderNone")}</option>
                  <option value="10">{t("schedule.settingsReminder10")}</option>
                  <option value="30">{t("schedule.settingsReminder30")}</option>
                  <option value="60">{t("schedule.settingsReminder60")}</option>
                  <option value="1440">{t("schedule.settingsReminder1440")}</option>
                </select>
              </SettingsRow>
              <SettingsRow label={t("schedule.settingsDefaultLength")}>
                <select
                  className="schedule-select"
                  value={settings.automation.defaultLen}
                  onChange={(event) => markDirty({ ...settings, automation: { ...settings.automation, defaultLen: event.target.value as DefaultLength } })}
                >
                  <option value="30">{t("schedule.settingsLen30")}</option>
                  <option value="60">{t("schedule.settingsLen60")}</option>
                  <option value="120">{t("schedule.settingsLen120")}</option>
                </select>
              </SettingsRow>
            </div>
          </Card>

            <div className="schedule-settings__savebar">
              <div className="schedule-settings__savebar-note">
                {dirty ? t("schedule.settingsUnsaved") : t("schedule.settingsSaved")}
              </div>
              <div className="schedule-settings__savebar-actions">
                <Button variant="secondary" onClick={cancelAll}>
                  {t("common.cancel")}
                </Button>
                <Button variant="primary" onClick={saveAll}>
                  {t("schedule.settingsSave")}
                </Button>
              </div>
            </div>
          </div>
        </div>

        <CalendarEditDialog
          open={calendarEditor != null}
          title={calendarEditor?.isNew ? t("schedule.settingsCreateCalendar") : t("schedule.settingsEditCalendar")}
          state={calendarEditor}
          onName={(value) => setCalendarEditor((current) => current ? { ...current, name: value } : current)}
          onColor={(value) => setCalendarEditor((current) => current ? { ...current, colorVar: value } : current)}
          onShare={(value) => setCalendarEditor((current) => current ? { ...current, share: value } : current)}
          onVisible={(value) => setCalendarEditor((current) => current ? { ...current, visible: value } : current)}
          onClose={() => setCalendarEditor(null)}
          onSave={saveEditor}
          onDelete={deleteEditor}
        />
      </div>
    </PageLayout>
  );
}
