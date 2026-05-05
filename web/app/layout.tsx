/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Inkvault",
  description: "单人私有、raw / ingest / wiki 的 Vault-first LLM Wiki",
  metadataBase: new URL("https://inkvault.local"),
  openGraph: {
    title: "Inkvault",
    description: "一个把 raw 导入、ingest 编译和 wiki 沉淀整合进同一研究工作流的私有系统。",
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
