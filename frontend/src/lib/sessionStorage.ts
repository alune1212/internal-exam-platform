// Shared sessionStorage adapter with a one-time legacy localStorage migration.
// Both admin-token and candidate-payload storage share the same dance, so it
// lives here in one place.

export function readSessionValue(key: string): string | null {
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

export function writeSessionValue(key: string, value: string): void {
  window.sessionStorage.setItem(key, value);
  window.localStorage.removeItem(key);
}

export function clearSessionValue(key: string): void {
  window.sessionStorage.removeItem(key);
  window.localStorage.removeItem(key);
}
