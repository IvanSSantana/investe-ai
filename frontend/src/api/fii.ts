import { apiClient, apiDownload } from "./client";
import type {
  RealStateFundResponse,
  ScheduleReportRequest,
  SendReportEmailRequest,
  ValuationPredictionResponse,
} from "../types/index.ts";

export const getIndicators = (ticker: string, forceRefresh = false) =>
  apiClient<RealStateFundResponse>(
    `/api/v1/fiis/${ticker}/indicators?force_refresh=${forceRefresh}`,
    { method: "GET" }
  );

export const getValuation = (ticker: string, forceRefresh = false) =>
  apiClient<ValuationPredictionResponse>(
    `/api/v1/fiis/${ticker}/valuation-prediction?force_refresh=${forceRefresh}`,
    { method: "GET" }
  );

export const downloadReport = (ticker: string) =>
  apiDownload(`/api/v1/fiis/${ticker}/report`);

export const sendReportEmail = (payload: SendReportEmailRequest) =>
  apiClient<{ message: string }>("/api/v1/fiis/send-email", {
    method: "POST",
    body: payload,
  });

export const scheduleEmail = (payload: ScheduleReportRequest) =>
  apiClient<{ message: string }>("/api/v1/fiis/schedule-email", {
    method: "POST",
    body: payload,
  });