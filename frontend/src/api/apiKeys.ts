import { apiClient } from "./client";
import type { ApiKeyCreateRequest, ApiKeyCreateResponse } from "../types";

export const createApiKey = (payload: ApiKeyCreateRequest) =>
  apiClient<ApiKeyCreateResponse>("/api/v1/auth/keys", {
    method: "POST",
    body: payload,
  });

export const revokeApiKey = (keyId: string) =>
  apiClient<void>(`/api/v1/auth/keys/${encodeURIComponent(keyId)}`, {
    method: "DELETE",
  });