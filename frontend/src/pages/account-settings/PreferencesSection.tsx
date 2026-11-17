import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useTheme } from "../../contexts/ThemeContext";
import { useLocale } from "../../contexts/LocaleContext";
import { SelectControl } from "../../components/Select";
import { Toggle } from "../../components/Toggle";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { getSecretaryVoice, saveSecretaryVoice, type VoiceSettings } from "../../features/secretary/secretaryApi";
import { useSecretaryAccess } from "../../features/secretary/useSecretaryAccess";

export default function PreferencesSection() {
  const { t } = useTranslation();
  const { theme, changeTheme } = useTheme();
  const { locale, changeLanguage } = useLocale();
  const { allowed } = useSecretaryAccess();
  // 秘書の声（秘書の窓が出る人だけ。読めるまでは行を出さない）
  const [voice, setVoice] = useState<VoiceSettings | null>(null);
  const [voiceLoadFailed, setVoiceLoadFailed] = useState(false);
  const [voiceSaveFailed, setVoiceSaveFailed] = useState(false);
  const [voiceSaving, setVoiceSaving] = useState(false);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    getSecretaryVoice()
      .then((v) => {
        if (!cancelled) setVoice(v);
      })
      .catch(() => {
        if (!cancelled) setVoiceLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [allowed]);

  const onVoiceChange = async (next: string) => {
    if (!voice) return;
    const previous = voice;
    setVoiceSaveFailed(false);
    setVoiceSaving(true);
    try {
      setVoice(await saveSecretaryVoice(next));
    } catch {
      setVoice(previous);
      setVoiceSaveFailed(true);
    } finally {
      setVoiceSaving(false);
    }
  };

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.preferences size={ICON.md} aria-hidden="true" />
        {t("accountSettings.sectionPreferences")}
      </div>

      <div className="account-settings-pref-row">
        <label htmlFor="dark-mode-toggle" className="account-settings-pref-label">
          {t("accountSettings.darkModeLabel")}
        </label>
        <Toggle
          id="dark-mode-toggle"
          checked={theme === "dark"}
          onCheckedChange={(next) => changeTheme(next ? "dark" : "light")}
        />
      </div>

      <div className="account-settings-pref-row">
        <label htmlFor="language-select" className="account-settings-pref-label">
          {t("accountSettings.languageLabel")}
        </label>
        <SelectControl
          size="sm"
          id="language-select"
          value={locale}
          onChange={(e) => changeLanguage(e.target.value)}
          className="account-settings-lang-select"
        >
          <option value="ja">{t("language.ja")}</option>
          <option value="en">{t("language.en")}</option>
        </SelectControl>
      </div>

      {allowed && voice && (
        <div className="account-settings-pref-row">
          <label htmlFor="secretary-voice-select" className="account-settings-pref-label">
            {t("accountSettings.secretaryVoiceLabel")}
          </label>
          <SelectControl
            size="sm"
            id="secretary-voice-select"
            value={voice.selected}
            disabled={voiceSaving}
            onChange={(e) => void onVoiceChange(e.target.value)}
            className="account-settings-lang-select"
          >
            {voice.voices.map((v) => (
              <option key={v} value={v}>
                {t(`secretary.voice.name.${v}`)}
              </option>
            ))}
          </SelectControl>
        </div>
      )}
      {allowed && voiceLoadFailed && (
        <div className="error-message">{t("accountSettings.secretaryVoiceLoadFailed")}</div>
      )}
      {allowed && voiceSaveFailed && (
        <div className="error-message">{t("accountSettings.secretaryVoiceSaveFailed")}</div>
      )}
    </section>
  );
}
