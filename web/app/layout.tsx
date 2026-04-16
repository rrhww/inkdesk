/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";
import { Inter, Manrope, Newsreader } from "next/font/google";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter"
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope"
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader"
});

export const metadata: Metadata = {
  title: "Inkdesk",
  description: "围绕长期项目运转的个人主系统，附带公开输出与分享能力",
  metadataBase: new URL("https://inkdesk.local"),
  openGraph: {
    title: "Inkdesk",
    description: "一个把个人笔记系统、Agent 与任务计划整合进同一工作流的超级个人工作台。",
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
      <body className={`${inter.variable} ${manrope.variable} ${newsreader.variable} overflow-x-hidden`}>{children}</body>
    </html>
  );
}
