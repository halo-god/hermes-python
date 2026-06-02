import { createI18n } from "vue-i18n";
import zhCN from "./locales/zh-CN";
import en from "./locales/en";

const I18N_KEY = "hermes.locale";

function detectLocale(): string {
  const saved = localStorage.getItem(I18N_KEY);
  if (saved) return saved;
  const lang = navigator.language;
  if (lang.startsWith("zh")) return "zh-CN";
  return "en";
}

const i18n = createI18n({
  legacy: false, // use Composition API
  locale: detectLocale(),
  fallbackLocale: "zh-CN",
  messages: {
    "zh-CN": zhCN,
    en,
  },
});

export function setLocale(locale: string) {
  (i18n.global.locale as any).value = locale;
  localStorage.setItem(I18N_KEY, locale);
}

export default i18n;
