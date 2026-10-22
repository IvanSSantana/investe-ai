export const fmtBRL = (v: number | null | undefined) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const fmtPct = (v: number | null | undefined, decimals = 2) =>
  v === null || v === undefined ? "—" : `${Number(v).toFixed(decimals)}%`;

export const fmtNum = (v: number | null | undefined, decimals = 2) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("pt-BR", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });