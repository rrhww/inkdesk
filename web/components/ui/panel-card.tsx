import type { ReactNode } from "react";

type PanelCardProps = {
  children: ReactNode;
  className?: string;
};

export function PanelCard({ children, className = "" }: PanelCardProps) {
  return <div className={`paper-card ${className}`.trim()}>{children}</div>;
}
