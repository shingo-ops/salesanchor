import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";
import { CALENDARS, cssVar } from "../../features/schedule/calendars.config";

type ShareMode = "self" | "view" | "edit";

export interface SettingsCalendar {
  name: string;
  colorVar: string;
  visible: boolean;
  share: ShareMode;
}

export interface CalendarEditorState {
  id: string;
  isNew: boolean;
  name: string;
  colorVar: string;
  share: ShareMode;
  visible: boolean;
}

export function SettingsRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: ReactNode;
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

export function ScheduleSettingsDialog({
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
              {CALENDARS.map((calendar) => (
                <CalendarSwatch
                  key={calendar.id}
                  colorVar={calendar.colorVar}
                  selected={state.colorVar === calendar.colorVar}
                  onClick={() => onColor(calendar.colorVar)}
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
