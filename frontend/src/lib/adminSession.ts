const STORAGE_KEY = "internal-exam-admin-token";

export function getAdminToken(): string | null {
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setAdminToken(token: string): void {
  window.localStorage.setItem(STORAGE_KEY, token);
}

export function clearAdminToken(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}
