"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { useLocale, locales, localeNames, localeFlags, type Locale } from "@/i18n";

export function LanguageSelector() {
  const t = useTranslations("common");
  const { locale, changeLocale } = useLocale();

  // Get the other locale (not current one)
  const otherLocale = locales.find((loc) => loc !== locale) || locale;
  const otherLocaleName = localeNames[otherLocale];

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => changeLocale(otherLocale)}
      title={t("language")}
      className="text-sm"
    >
      {otherLocaleName}
    </Button>
  );
}

// Alternative: Inline selector for settings page
export function LanguageSelectorInline() {
  const t = useTranslations("common");
  const { locale, changeLocale } = useLocale();

  return (
    <div className="flex gap-2">
      {locales.map((loc) => (
        <Button
          key={loc}
          variant={locale === loc ? "default" : "outline"}
          size="sm"
          onClick={() => changeLocale(loc)}
        >
          <span className="mr-2">{localeFlags[loc]}</span>
          {localeNames[loc]}
        </Button>
      ))}
    </div>
  );
}
