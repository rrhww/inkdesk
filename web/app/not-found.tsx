import Link from "next/link";

export default function RootNotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-reading flex-col items-start justify-center px-6 py-16">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">Not Found</div>
      <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text">这个页面没有被公开出来</h1>
      <p className="mt-5 max-w-2xl text-sm leading-7 text-ink-muted">
        你访问的内容当前不存在，或者还没有被发布到公开输出。可以先回到公开输出首页继续浏览已经分享的内容。
      </p>
      <Link href="/" className="mt-8 rounded-sm bg-ink-primary px-5 py-3 text-sm font-semibold text-white">
        返回公开输出首页
      </Link>
    </main>
  );
}
