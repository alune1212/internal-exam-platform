const LEGACY_KEYS = new Set([
  "internal-exam-admin-token",
  "internal-exam-candidate",
  "internal-exam-registration-flow",
]);

const LEGACY_PREFIXES = ["internal-exam-attempt-session:", "internal-exam-attempt-draft:"];

export function clearLegacyProjectStorage(storage: Storage = window.localStorage): void {
  const keysToRemove: string[] = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key && (LEGACY_KEYS.has(key) || LEGACY_PREFIXES.some((prefix) => key.startsWith(prefix)))) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => storage.removeItem(key));
}
