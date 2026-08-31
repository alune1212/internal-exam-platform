import { emitSessionChange } from "@/app/queryClient";
import { clearLegacyProjectStorage } from "@/lib/legacyStorageCleanup";

const STORAGE_KEY = "internal-exam-admin-token";

export function getAdminToken(): string | null {
  return window.sessionStorage.getItem(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  window.sessionStorage.setItem(STORAGE_KEY, token);
  emitSessionChange("admin-login");
}

export function clearAdminToken(reason: "admin-logout" | "unauthorized" = "admin-logout"): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
  clearLegacyProjectStorage();
  emitSessionChange(reason);
}
