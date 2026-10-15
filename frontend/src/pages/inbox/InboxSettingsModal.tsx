import { useTranslation } from "react-i18next";
import type { StatusTabKey } from "./inbox.types";
import { Modal } from "../../components/Modal";
import { SelectControl } from "../../components/Select";
import { Toggle } from "../../components/Toggle";

interface InboxSettings {
  showRightPanel: boolean;
  defaultTab: StatusTabKey;
  defaultUnreadOnly: boolean;
  browserNotifications: boolean;
  soundEnabled: boolean;
}

interface Props {
  inboxSettings: InboxSettings;
  updateInboxSetting: <K extends keyof InboxSettings>(key: K, value: InboxSettings[K]) => void;
  onClose: () => void;
}

export function InboxSettingsModal({ inboxSettings, updateInboxSetting, onClose }: Props) {
  const { t } = useTranslation();

  return (
    <Modal open={true} onClose={onClose} title={t("inbox.settings.title")} size="sm">
        <div className="inbox-settings-section-title">{t("inbox.settings.display")}</div>

        <div className="inbox-settings-row">
          <span className="inbox-settings-label">{t("inbox.settings.showRightPanel")}</span>
          <Toggle checked={inboxSettings.showRightPanel}
            aria-label={t("inbox.settings.showRightPanel")}
            onCheckedChange={(next) => updateInboxSetting("showRightPanel", next)} />
        </div>

        <div className="inbox-settings-row">
          <span className="inbox-settings-label">{t("inbox.settings.defaultTab")}</span>
          <SelectControl size="sm"
            value={inboxSettings.defaultTab}
            onChange={(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}>
            <option value="all">{t("inbox.settings.defaultTabAll")}</option>
            <option value="lead">{t("inbox.settings.defaultTabLead")}</option>
            <option value="deal">{t("inbox.settings.defaultTabDeal")}</option>
            <option value="existing">{t("inbox.settings.defaultTabExisting")}</option>
            <option value="followup">{t("inbox.settings.defaultTabFollowUp")}</option>
            <option value="archive">{t("inbox.settings.defaultTabArchive")}</option>
          </SelectControl>
        </div>

        <div className="inbox-settings-row">
          <span className="inbox-settings-label">{t("inbox.settings.defaultUnreadOnly")}</span>
          <Toggle checked={inboxSettings.defaultUnreadOnly}
            aria-label={t("inbox.settings.defaultUnreadOnly")}
            onCheckedChange={(next) => updateInboxSetting("defaultUnreadOnly", next)} />
        </div>

        <div className="inbox-settings-section-title" style={{ marginTop: "var(--space-4)" }}>
          {t("inbox.settings.notifications")}
        </div>

        <div className="inbox-settings-row">
          <span className="inbox-settings-label">{t("inbox.settings.browserNotifications")}</span>
          <Toggle checked={inboxSettings.browserNotifications}
            aria-label={t("inbox.settings.browserNotifications")}
            onCheckedChange={async (next) => {
              if (next) {
                const perm = await Notification.requestPermission();
                if (perm === "denied") {
                  alert(t("inbox.settings.browserNotificationsDenied"));
                  return;
                }
              }
              updateInboxSetting("browserNotifications", next);
            }} />
        </div>

        <div className="inbox-settings-row">
          <span className="inbox-settings-label">{t("inbox.settings.soundEnabled")}</span>
          <Toggle checked={inboxSettings.soundEnabled}
            aria-label={t("inbox.settings.soundEnabled")}
            onCheckedChange={(next) => updateInboxSetting("soundEnabled", next)} />
        </div>

    </Modal>
  );
}
