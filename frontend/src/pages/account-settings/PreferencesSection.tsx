import { useTranslation } from "react-i18next";
import { useTheme } from "../../contexts/ThemeContext";
import { useLocale } from "../../contexts/LocaleContext";
import { SelectControl } from "../../components/Select";
import { Toggle } from "../../components/Toggle";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";

export default function PreferencesSection() {
  const { t } = useTranslation();
  const { theme, changeTheme } = useTheme();
  const { locale, changeLanguage } = useLocale();

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
    </section>
  );
}
