import { emitSessionChanged } from "@/lib/sessionEvents";
import { clearSessionValue, readSessionValue, writeSessionValue } from "@/lib/sessionStorage";

const STORAGE_KEY = "internal-exam-admin-token";

export function getAdminToken(): string | null {
  return readSessionValue(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  writeSessionValue(STORAGE_KEY, token);
  emitSessionChanged({ reason: "admin-login" });
}

export function clearAdminToken(reason: "admin-logout" | "unauthorized" = "admin-logout"): void {
  clearSessionValue(STORAGE_KEY);
  emitSessionChanged({ reason });
}
