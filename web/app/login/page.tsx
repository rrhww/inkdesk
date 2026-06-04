import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { OwnerLoginForm } from "@/components/workbench/owner-login-form";
import { loginOwner } from "@/lib/owner-auth";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
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
  const resolved = searchParams ? await searchParams : undefined;

  if (hasOwnerSession(await getRequestOwnerSession())) {
    redirect("/app");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[28px] bg-white shadow-paper lg:grid-cols-[1.15fr_0.85fr]">
        <section className="bg-ink-low px-8 py-12 md:px-12">
          <div className="font-headline text-sm uppercase tracking-[0.22em] text-ink-muted">Inkdesk</div>
          <h1 className="mt-6 font-headline text-5xl font-extrabold tracking-tight">进入私有 LLM Wiki</h1>
          <p className="mt-6 max-w-xl font-body text-[1.3rem] leading-[1.8] text-[#313738]">
            这是单人私有入口。进入后会直接回到 Ask-first 工作区，先看当前缺什么证据，再决定继续追问、补 raw、审 ingest 或打开 wiki。
          </p>
          <p className="mt-4 max-w-xl text-sm leading-7 text-ink-muted">
            默认工作流是：Ask 暴露判断和缺口，raw 保存来源，ingest 提出补丁，然后由你确认哪些变化能写入 wiki。
          </p>
        </section>

        <section className="px-8 py-12 md:px-12">
          <OwnerLoginForm action={loginAction} hasError={Boolean(resolved?.error)} />
        </section>
      </div>
    </main>
  );
}
