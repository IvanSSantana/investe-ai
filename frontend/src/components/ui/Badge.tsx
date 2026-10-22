import type { CSSProperties, ReactNode } from "react";

export type BadgeVariant = "success" | "info" | "warning" | "danger" | "neutral";

const variants: Record<BadgeVariant, CSSProperties> = {
  success: { backgroundColor: "#d1fae5", color: "#065f46" },
  info:    { backgroundColor: "#dbeafe", color: "#1e40af" },
  warning: { backgroundColor: "#fef3c7", color: "#92400e" },
  danger:  { backgroundColor: "#fee2e2", color: "#991b1b" },
  neutral: { backgroundColor: "#e5e7eb", color: "#374151" },
};

const base: CSSProperties = {
  display: "inline-block",
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 600,
};

interface BadgeProps {
  children: ReactNode;
  variant: BadgeVariant;
  size?: "sm" | "md";
}

export function Badge({ children, variant, size = "sm" }: BadgeProps) {
  return (
    <span
      style={{
        ...base,
        ...variants[variant],
        ...(size === "md" && { fontSize: 14, padding: "8px 16px" }),
      }}
    >
      {children}
    </span>
  );
}