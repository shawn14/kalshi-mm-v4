import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Kalshi MM v4",
  description: "Professional market-making dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg text-fg antialiased">
        <Providers>
          <div className="flex min-h-dvh">
            <Sidebar />
            {/* Main content — offset for sidebar */}
            <main className="ml-16 flex-1 overflow-auto md:ml-56">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
