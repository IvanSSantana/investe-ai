import type { CSSProperties, ReactNode } from "react";

const cardStyle: CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  padding: 16,
  marginBottom: 16,
};

interface CardProps {
  title: string;
  children: ReactNode;
}

export function Card({ title, children }: CardProps) {
  return (
    <section style={cardStyle}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {children}
    </section>
  );
}