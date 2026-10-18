import { apiClient } from "./client";
import type { LoginRequest, RegisterRequest, UserResponse } from "../types";

export const login = (payload: LoginRequest) =>
  apiClient<UserResponse>("/api/v1/auth/login", { method: "POST", body: payload });

export const register = (payload: RegisterRequest) =>
  apiClient<UserResponse>("/api/v1/auth/register", { method: "POST", body: payload });

export const logout = () =>
  apiClient<void>("/api/v1/auth/logout", { method: "POST" });

export const getMe = () =>
  apiClient<UserResponse>("/api/v1/auth/me", { method: "GET" });