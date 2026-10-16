/**
 * 閲覧ページ専用の i18n（ADR-027）。
 * 本体の frontend/src/i18n.ts と本体の辞書（約254KB）は読み込まない。viewer の辞書2つだけを読む。
 * 言語は本体と同じ cookie `locale=` を共有する（無ければ ja）。
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "../../locales/viewer/en.json";
import ja from "../../locales/viewer/ja.json";

export type ViewerLang = "ja" | "en";

function readLocaleCookie(): ViewerLang {
  try {
    const m = document.cookie.match(/(?:^|;\s*)locale=([^;]+)/);
    return m && m[1] === "en" ? "en" : "ja";
  } catch {
    return "ja";
  }
}

export function saveLocaleCookie(lang: ViewerLang): void {
  try {
    document.cookie = `locale=${lang};path=/;max-age=31536000;SameSite=Lax`;
  } catch {
    /* cookie が使えなくても切り替え自体は動く */
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ja: { translation: ja },
  },
  lng: readLocaleCookie(),
  fallbackLng: "ja",
  interpolation: { escapeValue: false },
});

export default i18n;
