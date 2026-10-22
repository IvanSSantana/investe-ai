import { ApiError } from "../api/client";

export const errorMessage = (error: unknown, fallback: string): string =>
  error instanceof ApiError ? error.detail : fallback;