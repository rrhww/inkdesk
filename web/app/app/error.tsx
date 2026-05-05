"use client";

import Link from "next/link";

export default function AppError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto max-w-shell px-6 py-16 lg:px-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">LLM Wiki 错误</div>
      <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text">当前页面没有正常载入</h1>
      <p className="mt-5 max-w-2xl text-sm leading-7 text-ink-muted">
        {error.message || "可以先重试一次，或者回到 Today Vault Panel 继续工作。"}
      </p>
      <div className="mt-8 flex gap-3">
        <button className="rounded-sm bg-ink-primary px-5 py-3 text-sm font-semibold text-white" onClick={reset} type="button">
          重试
        </button>
        <Link href="/app" className="rounded-sm bg-white px-5 py-3 text-sm font-semibold text-ink-text shadow-paper">
          回到 Today Vault Panel
        </Link>
      </div>
    </main>
  );
}
