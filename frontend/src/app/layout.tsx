import "katex/dist/katex.min.css";
import "@/styles/globals.css";

import { type Metadata } from "next";
import localFont from "next/font/local";

import { AccentProvider } from "@/components/accent-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { I18nProvider } from "@/core/i18n/context";
import { detectLocaleServer } from "@/core/i18n/server";

// aio-skin: Aio's brand font, feeds --font-code -> --font-sans/--font-mono in globals.css
const codeNewRoman = localFont({
  src: [
    { path: "./fonts/CodeNewRoman-Regular.otf", weight: "400", style: "normal" },
    { path: "./fonts/CodeNewRoman-Bold.otf", weight: "700", style: "normal" },
  ],
  variable: "--font-code",
  display: "swap",
});

// aio-skin: Aio's heading font, matches apps/web pairing (--font-heading)
const libreBaskerville = localFont({
  src: [
    { path: "./fonts/LibreBaskerville-Regular.ttf", weight: "400", style: "normal" },
    { path: "./fonts/LibreBaskerville-Bold.ttf", weight: "700", style: "normal" },
  ],
  variable: "--font-heading",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aio",
  description: "Your personal AI agent.",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await detectLocaleServer();
  return (
    <html
      lang={locale}
      className={`${codeNewRoman.variable} ${libreBaskerville.variable}`}
      suppressContentEditableWarning
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" enableSystem disableTransitionOnChange>
          <AccentProvider>
            <I18nProvider initialLocale={locale}>{children}</I18nProvider>
          </AccentProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
