import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Interview Agent",
  description: "AI-powered mock interview platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
