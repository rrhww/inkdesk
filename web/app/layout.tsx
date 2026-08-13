/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Inkdesk",
  description: "面向研发人员的可信知识看板与上下文工作台",
  metadataBase: new URL("https://inkdesk.local"),
  openGraph: {
    title: "Inkdesk",
    description: "围绕项目主题呈现当前理解、关键决策、来源和知识缺口。",
    type: "website"
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="overflow-x-hidden">{children}</body>
    </html>
  );
}
