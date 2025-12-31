"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { useLocale, locales, localeNames, localeFlags, defaultLocale } from "@/i18n";

export function LanguageSelector() {
  const t = useTranslations("common");
  const { locale, changeLocale } = useLocale();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  // Use default locale during SSR and before hydration
  const currentLocale = mounted ? locale : defaultLocale;

  // Get the other locale (not current one)
  const otherLocale = locales.find((loc) => loc !== currentLocale) || currentLocale;
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
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const currentLocale = mounted ? locale : defaultLocale;

  return (
    <div className="flex gap-2">
      {locales.map((loc) => (
        <Button
          key={loc}
          variant={currentLocale === loc ? "default" : "outline"}
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
