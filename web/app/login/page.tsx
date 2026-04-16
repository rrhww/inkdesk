import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { OwnerLoginForm } from "@/components/workbench/owner-login-form";
import { loginOwner } from "@/lib/owner-auth";
import { InkdeskApiError } from "@/lib/server-api";
import { OWNER_SESSION_COOKIE, hasOwnerSession } from "@/lib/owner-session";

async function loginAction(formData: FormData) {
  "use server";

  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  try {
    const result = await loginOwner(email, password);

    if (!result) {
      redirect("/login?error=1");
    }

    const cookieStore = await cookies();
    cookieStore.set(OWNER_SESSION_COOKIE, result.sessionToken, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 8
    });
    redirect("/app");
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 401) {
      redirect("/login?error=1");
    }

    throw error;
  }
}

type LoginPageProps = {
  searchParams?: Promise<{
    error?: string;
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const cookieStore = await cookies();
  const resolved = searchParams ? await searchParams : undefined;

  if (hasOwnerSession(cookieStore.get(OWNER_SESSION_COOKIE)?.value)) {
    redirect("/app");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[28px] bg-white shadow-paper lg:grid-cols-[1.15fr_0.85fr]">
        <section className="bg-ink-low px-8 py-12 md:px-12">
          <div className="font-headline text-sm uppercase tracking-[0.22em] text-ink-muted">Inkdesk</div>
          <h1 className="mt-6 font-headline text-5xl font-extrabold tracking-tight">进入主系统</h1>
          <p className="mt-6 max-w-xl font-body text-[1.3rem] leading-[1.8] text-[#313738]">
            这是主人专用入口。进入后会直接进入 Agent 控制台，并继续处理笔记、任务计划与公开内容输出。
          </p>
        </section>

        <section className="px-8 py-12 md:px-12">
          <OwnerLoginForm action={loginAction} hasError={Boolean(resolved?.error)} />
        </section>
      </div>
    </main>
  );
}
