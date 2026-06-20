"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type InkSelectOption = {
  value: string;
  label: string;
};

type InkSelectProps = {
  id: string;
  name: string;
  value: string;
  options: InkSelectOption[];
  onChange?: (value: string) => void;
};

export function InkSelect({ id, name, value, options, onChange }: InkSelectProps) {
  const [open, setOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find((o) => o.value === selectedValue)?.label ?? selectedValue;

  useEffect(() => {
    setSelectedValue(value);
  }, [value]);

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, handleClickOutside]);

  const select = (v: string) => {
    setSelectedValue(v);
    setOpen(false);
    onChange?.(v);
  };

  return (
    <div ref={containerRef} className="relative">
      <input name={name} type="hidden" value={selectedValue} />
      <button
        id={id}
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20 text-left"
      >
        <span className={selectedValue ? "text-ink-text" : "text-ink-muted"}>{selectedLabel}</span>
        <span className={`material-symbols-outlined text-[18px] text-ink-muted transition-transform ${open ? "rotate-180" : ""}`}>
          keyboard_arrow_down
        </span>
      </button>
      {open && (
        <ul className="absolute z-50 mt-1 w-full rounded-[18px] bg-white shadow-paper border border-black/5 py-1 max-h-64 overflow-auto">
          {options.map((opt) => {
            const active = opt.value === selectedValue;
            return (
              <li key={opt.value}>
                <button
                  type="button"
                  onClick={() => select(opt.value)}
                  className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                    active
                      ? "bg-ink-primarySoft text-ink-text font-medium"
                      : "text-ink-text hover:bg-ink-low"
                  }`}
                >
                  {opt.label}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
