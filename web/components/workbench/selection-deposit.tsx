"use client";

import { useCallback, useRef, useState, useEffect } from "react";

type SelectionDepositProps = {
  answerId: string;
  runId?: string;
  children: React.ReactNode;
};

export function SelectionDeposit({ answerId, runId, children }: SelectionDepositProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selection, setSelection] = useState<{ text: string; top: number; left: number } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleMouseUp = useCallback(() => {
    // Small delay to let the selection settle
    setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.toString().trim()) {
        setSelection(null);
        return;
      }

      const text = sel.toString().trim();
      if (text.length < 10) {
        setSelection(null);
        return;
      }

      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setSelection({
        text,
        top: rect.bottom + window.scrollY + 8,
        left: rect.left + window.scrollX + rect.width / 2,
      });
    }, 50);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("mouseup", handleMouseUp);
    return () => el.removeEventListener("mouseup", handleMouseUp);
  }, [handleMouseUp]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setSelection(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleDeposit = async () => {
    if (!selection) return;
    setSubmitting(true);
    try {
      await fetch("/api/deposits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "selection",
          askTurnId: answerId,
          runId: runId || undefined,
          payload: {
            selectedText: selection.text,
            selectionReason: "用户手动选中片段沉淀",
          },
        }),
      });
      setDone(true);
      setSelection(null);
    } catch {
      // silently fail, user can retry
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      {children}
      {selection && (
        <div
          className="fixed z-50 -translate-x-1/2"
          style={{ top: selection.top, left: selection.left }}
        >
          <div className="bg-ink-text text-white rounded-2xl px-4 py-2 shadow-lg flex items-center gap-2">
            <span className="text-xs truncate max-w-[200px]">
              {done ? "已提交沉淀" : `"${selection.text.slice(0, 40)}…"`}
            </span>
            {!done && (
              <button
                onClick={handleDeposit}
                disabled={submitting}
                className="shrink-0 rounded-full bg-white/20 px-3 py-1 text-xs font-semibold text-white hover:bg-white/30 disabled:opacity-50"
              >
                {submitting ? "提交中…" : "沉淀选中片段"}
              </button>
            )}
            <button
              onClick={() => { setSelection(null); setDone(false); }}
              className="shrink-0 material-symbols-outlined text-[16px] text-white/60 hover:text-white"
            >
              close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
