"use client";

import { useState } from "react";
import type { PermissionRequestData } from "@/lib/coding-stream";

type PermissionDialogProps = {
  request: PermissionRequestData;
  onRespond: (allow: boolean, reason?: string) => Promise<void>;
};

export function PermissionDialog({ request, onRespond }: PermissionDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [reason, setReason] = useState("");

  const handleRespond = async (allow: boolean) => {
    setSubmitting(true);
    try {
      await onRespond(allow, allow ? undefined : reason || undefined);
    } finally {
      setSubmitting(false);
    }
  };

  const inputJson = (() => {
    try {
      return JSON.stringify(request.tool_input, null, 2);
    } catch {
      return String(request.tool_input);
    }
  })();

  const isDangerous = ["Write", "Edit", "MultiEdit", "Bash", "PowerShell", "NotebookEdit", "WebFetch"].includes(
    request.tool_name,
  ) || request.tool_name.startsWith("mcp__");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-2xl rounded-3xl bg-white shadow-2xl">
        {/* 头部 */}
        <div className="flex items-center gap-3 border-b border-ink-low px-6 py-4">
          <span className="material-symbols-outlined text-[24px] text-amber-500">
            {isDangerous ? "warning" : "help"}
          </span>
          <div className="flex-1">
            <div className="text-sm font-semibold text-ink-text">
              工具调用权限请求
            </div>
            <div className="text-xs text-ink-muted">
              Claude Code 想要执行以下操作，请确认是否放行
            </div>
          </div>
        </div>

        {/* 工具信息 */}
        <div className="space-y-4 px-6 py-5">
          <div>
            <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted mb-1">
              工具名称
            </div>
            <div className="flex items-center gap-2">
              <code className="rounded-lg bg-ink-low px-2 py-1 text-sm font-mono text-ink-text">
                {request.tool_name}
              </code>
              {isDangerous && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                  危险操作
                </span>
              )}
            </div>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted mb-1">
              调用参数
            </div>
            <pre className="max-h-64 overflow-auto rounded-2xl bg-ink-low p-4 text-xs font-mono text-ink-text">
{inputJson}
            </pre>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted mb-1">
              拒绝理由（可选）
            </div>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="拒绝时填写理由，会反馈给 Claude"
              className="w-full rounded-xl border border-ink-low bg-white px-3 py-2 text-sm text-ink-text placeholder:text-ink-muted focus:border-ink-primary focus:outline-none"
            />
          </div>
        </div>

        {/* 按钮 */}
        <div className="flex items-center justify-end gap-3 border-t border-ink-low px-6 py-4">
          <button
            onClick={() => handleRespond(false)}
            disabled={submitting}
            className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-ink-low/80 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? "提交中…" : "拒绝"}
          </button>
          <button
            onClick={() => handleRespond(true)}
            disabled={submitting}
            className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? "提交中…" : "允许执行"}
          </button>
        </div>
      </div>
    </div>
  );
}
