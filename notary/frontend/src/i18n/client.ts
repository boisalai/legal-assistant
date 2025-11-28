"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { type Locale, locales, defaultLocale } from "./config";

// Cookie name for storing locale preference
const LOCALE_COOKIE_NAME = "locale";

/**
 * Get the current locale from cookie (client-side)
 */
export function getLocale(): Locale {
  if (typeof window === "undefined") return defaultLocale;

  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${LOCALE_COOKIE_NAME}=`));

  const value = cookie?.split("=")[1];

  if (value && locales.includes(value as Locale)) {
    return value as Locale;
  }

  return defaultLocale;
}

/**
 * Set the locale in cookie and reload the page
 */
export function setLocale(locale: Locale): void {
  if (!locales.includes(locale)) return;

  // Set cookie for 1 year
  const maxAge = 60 * 60 * 24 * 365;
  document.cookie = `${LOCALE_COOKIE_NAME}=${locale}; path=/; max-age=${maxAge}; SameSite=Lax`;

  // Reload to apply new locale
  window.location.reload();
}

/**
 * Hook to manage locale
 */
export function useLocale() {
  const router = useRouter();

  const changeLocale = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
  }, []);

  return {
    locale: getLocale(),
    changeLocale,
    locales,
  };
}
