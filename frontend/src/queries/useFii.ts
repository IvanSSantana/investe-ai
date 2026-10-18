import { useMutation, useQuery } from "@tanstack/react-query";
import {
  downloadReport,
  getIndicators,
  getValuation,
  scheduleEmail,
  sendReportEmail,
} from "../api/fii";
import type { ScheduleReportRequest, SendReportEmailRequest } from "../types";

export function useValuation(ticker: string, forceRefresh = false) {
  return useQuery({
    queryKey: ["valuation", ticker, forceRefresh],
    queryFn: () => getValuation(ticker, forceRefresh),
    enabled: !!ticker,
  });
}

export function useIndicators(ticker: string, forceRefresh = false) {
  return useQuery({
    queryKey: ["indicators", ticker, forceRefresh],
    queryFn: () => getIndicators(ticker, forceRefresh),
    enabled: !!ticker,
  });
}

export function useSendReportEmail() {
  return useMutation({
    mutationFn: (payload: SendReportEmailRequest) => sendReportEmail(payload),
  });
}

export function useScheduleEmail() {
  return useMutation({
    mutationFn: (payload: ScheduleReportRequest) => scheduleEmail(payload),
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: (ticker: string) => downloadReport(ticker),
    onSuccess: (blob, ticker) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${ticker.toUpperCase()}_relatorio.md`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
}