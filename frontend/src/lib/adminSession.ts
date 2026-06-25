import { emitSessionChanged } from "@/lib/sessionEvents";

const STORAGE_KEY = "internal-exam-admin-token";

export function getAdminToken(): string | null {
  const sessionToken = window.sessionStorage.getItem(STORAGE_KEY);
  if (sessionToken) {
    return sessionToken;
  }
  const legacyToken = window.localStorage.getItem(STORAGE_KEY);
  if (legacyToken) {
    window.sessionStorage.setItem(STORAGE_KEY, legacyToken);
    window.localStorage.removeItem(STORAGE_KEY);
    return legacyToken;
  }
  return null;
}

export function setAdminToken(token: string): void {
  window.sessionStorage.setItem(STORAGE_KEY, token);
  window.localStorage.removeItem(STORAGE_KEY);
  emitSessionChanged({ reason: "admin-login" });
}

export function clearAdminToken(reason: "admin-logout" | "unauthorized" = "admin-logout"): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(STORAGE_KEY);
  emitSessionChanged({ reason });
}
