import { useMutation, useQueryClient } from "@tanstack/react-query";
import { login, logout, register } from "../api/auth";
import type { LoginRequest, RegisterRequest } from "../types";

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginRequest) => login(payload),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RegisterRequest) => {
      return register(payload).then(() => login(payload));
    },
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => queryClient.clear(),
  });
} 