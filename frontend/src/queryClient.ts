import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api/client";

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => handleGlobalError(error, query.queryKey),
  }),
  mutationCache: new MutationCache({
    onError: (error) => handleGlobalError(error, null),
  }),
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, 
      retry: 2,                 
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 2,
    },
  },
});

function handleGlobalError(
  error: unknown,
  queryKey: readonly unknown[] | null,
): void {
  if (!(error instanceof ApiError) || error.status !== 401) return;

  if (queryKey && queryKey[0] === "me") return;

  queryClient.clear();

  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}