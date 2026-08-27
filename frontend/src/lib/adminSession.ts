import { emitSessionChange } from "@/app/queryClient";

const STORAGE_KEY = "internal-exam-admin-token";

function readSessionValue(key: string): string | null {
  const sessionValue = window.sessionStorage.getItem(key);
  if (sessionValue) {
    return sessionValue;
  }
  const legacyValue = window.localStorage.getItem(key);
  if (!legacyValue) {
    return null;
  }
  window.sessionStorage.setItem(key, legacyValue);
  window.localStorage.removeItem(key);
  return legacyValue;
}

function writeSessionValue(key: string, value: string): void {
  window.sessionStorage.setItem(key, value);
}

function clearSessionValue(key: string): void {
  window.sessionStorage.removeItem(key);
  window.localStorage.removeItem(key);
}

export function getAdminToken(): string | null {
  return readSessionValue(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  writeSessionValue(STORAGE_KEY, token);
  emitSessionChange("admin-login");
}

export function clearAdminToken(reason: "admin-logout" | "unauthorized" = "admin-logout"): void {
  clearSessionValue(STORAGE_KEY);
  emitSessionChange(reason);
}
