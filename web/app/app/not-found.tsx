import Link from "next/link";

export default function AppNotFound() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-81px)] max-w-shell flex-col items-start justify-center px-6 py-16 lg:px-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">主系统路径不存在</div>
      <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text">这条主系统路径当前不存在</h1>
      <p className="mt-5 max-w-2xl text-sm leading-7 text-ink-muted">
        可以回到 Agent 控制台重新进入计划、知识库或检索页，继续你的当前工作流。
      </p>
      <Link href="/app" className="mt-8 rounded-sm bg-ink-primary px-5 py-3 text-sm font-semibold text-white">
        回到 Agent 控制台
      </Link>
    </main>
  );
}
