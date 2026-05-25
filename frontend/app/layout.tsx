import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SidebarNav } from "@/components/sidebar-nav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Silvercurrent",
  description: "Personal cockpit for evaluating small-business acquisitions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <div className="flex min-h-screen">
          <aside className="flex w-56 shrink-0 flex-col gap-6 border-r border-border bg-sidebar px-4 py-6 text-sidebar-foreground">
            <div className="px-2">
              <span className="text-base font-semibold tracking-tight">
                Silvercurrent
              </span>
              <p className="mt-1 text-xs text-muted-foreground">
                Acquisition cockpit
              </p>
            </div>
            <SidebarNav />
          </aside>
          <main className="flex-1 px-8 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
