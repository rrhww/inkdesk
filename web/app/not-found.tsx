import Link from "next/link";

export default function RootNotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col items-start justify-center px-6 py-16">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Not Found</div>
      <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text">这个页面当前不存在</h1>
      <p className="mt-5 max-w-2xl text-sm leading-7 text-ink-muted">
        你访问的内容当前不存在。Inkdesk 现在主要作为私有研究工作区运行，可以回到登录入口继续进入自己的研究流。
      </p>
      <Link href="/login" className="mt-8 rounded-sm bg-ink-primary px-5 py-3 text-sm font-semibold text-white">
        返回登录入口
      </Link>
    </main>
  );
}
