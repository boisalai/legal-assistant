import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";

export const metadata: Metadata = {
  title: "Notary Assistant - Analyse de Dossiers Notariaux",
  description: "Systeme d'IA pour automatiser les verifications preliminaires dans les cabinets de notaires au Quebec",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning className={GeistSans.variable}>
      <body className="antialiased min-h-screen bg-background font-sans">
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
