/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Inkdesk",
  description: "单人私有、Dev Run-first 的 AI 研发自动化控制台",
  metadataBase: new URL("https://inkdesk.local"),
  openGraph: {
    title: "Inkdesk",
    description: "一个把 Dev Run 任务驱动、raw 导入、ingest 编译和 wiki 沉淀整合进同一研发控制台的私有系统。",
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
