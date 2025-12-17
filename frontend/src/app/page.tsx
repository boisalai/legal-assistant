"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { NewCaseModal } from "@/components/cases/new-course-modal";
import { LanguageSelector } from "@/components/ui/language-selector";

export default function Home() {
  const t = useTranslations();
  const [showNewCaseModal, setShowNewCaseModal] = useState(false);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold">
            {t("common.appName")}
          </Link>
          <LanguageSelector />
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-6 px-4">
          <h1 className="text-2xl font-semibold">
            {t("home.title")}
          </h1>
          <p className="text-muted-foreground max-w-md">
            {t("home.subtitle")}
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => setShowNewCaseModal(true)}>
              {t("home.newCourse")}
            </Button>
            <Link href="/courses">
              <Button variant="outline">{t("home.viewCourses")}</Button>
            </Link>
          </div>
        </div>
      </main>

      <NewCaseModal open={showNewCaseModal} onOpenChange={setShowNewCaseModal} />
    </div>
  );
}
