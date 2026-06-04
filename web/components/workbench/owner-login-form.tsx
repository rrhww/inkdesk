"use client";

import { useFormStatus } from "react-dom";

type OwnerLoginFormProps = {
  action: (formData: FormData) => void | Promise<void>;
  hasError: boolean;
};

export function OwnerLoginForm({ action, hasError }: OwnerLoginFormProps) {
  return (
    <form action={action} className="space-y-5">
      <div className="rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">
        主人身份：只有通过隐藏入口的本人才能进入私有研究工作区。
      </div>
      <div>
        <label className="mb-2 block text-sm text-ink-muted" htmlFor="owner-email">
          邮箱
        </label>
        <input
          autoComplete="username"
          className="w-full rounded-sm border-none bg-ink-low px-4 py-3 focus:ring-2 focus:ring-ink-primary/20"
          id="owner-email"
          name="email"
          placeholder="owner@inkdesk.local"
          required
          type="email"
        />
      </div>
      <div>
        <label className="mb-2 block text-sm text-ink-muted" htmlFor="owner-password">
          密码
        </label>
        <input
          autoComplete="current-password"
          className="w-full rounded-sm border-none bg-ink-low px-4 py-3 focus:ring-2 focus:ring-ink-primary/20"
          id="owner-password"
          name="password"
          placeholder="请输入密码"
          required
          type="password"
        />
      </div>
      {hasError ? (
        <p aria-live="polite" className="text-sm text-ink-errorText">
          凭证无效，请重新确认主人身份。
        </p>
      ) : null}
      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button className="w-full rounded-sm bg-ink-primary px-4 py-3 font-headline text-sm font-semibold text-white" type="submit">
      {pending ? "验证主人身份中..." : "进入工作区"}
    </button>
  );
}
