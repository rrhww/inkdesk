<<<<<<< HEAD
import React from 'react';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // 强制全屏无滚动条，透明纯净底色
    <div className="w-screen h-screen overflow-hidden bg-[#F8FAFC]">
      {children}
    </div>
  );
=======
import type { ReactNode } from "react";

export default function AppLayout({ children }: { children: ReactNode }) {
  return children;
>>>>>>> origin/main
}
