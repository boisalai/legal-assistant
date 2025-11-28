"use client";

import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLocale, locales, localeNames, localeFlags, type Locale } from "@/i18n";

export function LanguageSelector() {
  const t = useTranslations("common");
  const { locale, changeLocale } = useLocale();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title={t("language")}>
          <Globe className="h-4 w-4" />
          <span className="sr-only">{t("language")}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => changeLocale(loc)}
            className={locale === loc ? "bg-accent" : ""}
          >
            <span className="mr-2">{localeFlags[loc]}</span>
            {localeNames[loc]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
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
