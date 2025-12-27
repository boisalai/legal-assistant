import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { defaultLocale, locales, type Locale } from "./config";

// Import messages explicitly to avoid Next.js bundling issues
import enMessages from "../../messages/en.json";
import frMessages from "../../messages/fr.json";

const messagesMap = {
  en: enMessages,
  fr: frMessages,
} as const;

export default getRequestConfig(async () => {
  // Get locale from cookie, fallback to default
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;

  // Validate locale
  const locale: Locale = locales.includes(localeCookie as Locale)
    ? (localeCookie as Locale)
    : defaultLocale;

  return {
    locale,
    messages: messagesMap[locale],
  };
});
