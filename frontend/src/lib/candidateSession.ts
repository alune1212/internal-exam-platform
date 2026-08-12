import { emitSessionChanged } from "@/lib/sessionEvents";
import type { Candidate } from "@/types/candidate";
import { clearAllAttemptSessions } from "@/lib/attemptSession";
import { clearAllAttemptDrafts } from "@/lib/attemptDraft";

const STORAGE_KEY = "internal-exam-candidate";
const REGISTRATION_KEY = "internal-exam-registration-flow";
export const DEFAULT_CANDIDATE_DESTINATION = "/exams";

/**
 * Return targets are navigation hints only.  Keep them as same-origin paths
 * and reject protocol-relative, encoded external, backslash, and malformed
 * values before putting them back into a URL.
 */
export function getSafeReturnTo(value: string | null | undefined): string {
  if (!value) return DEFAULT_CANDIDATE_DESTINATION;
  let candidate: string;
  try {
    candidate = decodeURIComponent(value);
  } catch {
    return DEFAULT_CANDIDATE_DESTINATION;
  }
  if (!candidate.startsWith("/") || candidate.startsWith("//") || candidate.includes("\\")) {
    return DEFAULT_CANDIDATE_DESTINATION;
  }
  try {
    const url = new URL(candidate, window.location.origin);
    if (url.origin !== window.location.origin || url.protocol !== window.location.protocol) {
      return DEFAULT_CANDIDATE_DESTINATION;
    }
    if (
      !url.pathname.startsWith("/") ||
      url.pathname.startsWith("//") ||
      url.pathname === "/" ||
      url.pathname === "/login" ||
      url.pathname === "/register"
    ) {
      return DEFAULT_CANDIDATE_DESTINATION;
    }
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return DEFAULT_CANDIDATE_DESTINATION;
  }
}

export function candidateLoginPath(returnTo?: string | null): string {
  const safe = getSafeReturnTo(returnTo);
  return `/login?returnTo=${encodeURIComponent(safe)}`;
}

export function maskEmail(email: string | null | undefined): string {
  const normalized = email?.trim() ?? "";
  const at = normalized.indexOf("@");
  if (at <= 0 || at === normalized.length - 1) return "***";
  const local = normalized.slice(0, at);
  const domain = normalized.slice(at + 1);
  if (local.length <= 1) return `*@${domain}`;
  if (local.length === 2) return `${local[0]}*@${domain}`;
  return `${local[0]}${"*".repeat(Math.min(4, local.length - 2))}${local.at(-1)}@${domain}`;
}

export function getCurrentCandidate(): Candidate | null {
  // Candidate credentials are intentionally session-only. A token in
  // localStorage must never be promoted into an authenticated browser session.
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  return parseCandidate(raw);
}

function parseCandidate(raw: string): Candidate | null {
  try {
    const parsed = JSON.parse(raw) as Partial<Candidate> | null;
    const tokenExpiresAt = parsed?.token_expires_at;
    if (
      !parsed ||
      typeof parsed !== "object" ||
      typeof parsed.id !== "number" ||
      !Number.isFinite(parsed.id) ||
      parsed.id <= 0 ||
      typeof parsed.token !== "string" ||
      !parsed.token ||
      typeof tokenExpiresAt !== "string" ||
      !Number.isFinite(Date.parse(tokenExpiresAt)) ||
      typeof parsed.email !== "string" ||
      !parsed.email ||
      (typeof parsed.display_name !== "string" && parsed.display_name !== null) ||
      parsed.status !== "active"
    ) {
      throw new Error("invalid candidate session");
    }
    if (isCandidateSessionExpired({ token_expires_at: tokenExpiresAt })) {
      clearCurrentCandidate("unauthorized");
      return null;
    }
    return {
      id: parsed.id,
      token: parsed.token,
      token_expires_at: tokenExpiresAt,
      email: parsed.email.trim().toLowerCase(),
      display_name: parsed.display_name?.trim() || null,
      status: "active",
    };
  } catch {
    clearCurrentCandidate("unauthorized");
    return null;
  }
}

export function isCandidateSessionExpired(candidate: Pick<Candidate, "token_expires_at">): boolean {
  if (!candidate.token_expires_at) return false;
  const expiresAt = Date.parse(candidate.token_expires_at);
  return Number.isFinite(expiresAt) && expiresAt <= Date.now();
}

export function setCurrentCandidate(candidate: Candidate) {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(candidate));
  // Remove any persistent copy without ever reading it.
  window.localStorage.removeItem(STORAGE_KEY);
  emitSessionChanged({ reason: "candidate-login" });
}

export function clearCurrentCandidate(
  reason: "candidate-logout" | "unauthorized" = "candidate-logout",
) {
  window.sessionStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(STORAGE_KEY);
  clearRegistrationFlow();
  clearAllAttemptSessions();
  clearAllAttemptDrafts();
  emitSessionChanged({ reason });
}

export type RegistrationFlow = {
  registration_credential: string;
  email: string;
  suggested_display_name?: string | null;
  returnTo: string;
  expires_at: string;
};

export function setRegistrationFlow(flow: RegistrationFlow): void {
  const safeFlow = { ...flow, returnTo: getSafeReturnTo(flow.returnTo) };
  window.sessionStorage.setItem(REGISTRATION_KEY, JSON.stringify(safeFlow));
  window.localStorage.removeItem(REGISTRATION_KEY);
}

export function getRegistrationFlow(): RegistrationFlow | null {
  const raw = window.sessionStorage.getItem(REGISTRATION_KEY);
  if (!raw) return null;
  try {
    const flow = JSON.parse(raw) as RegistrationFlow;
    if (
      !flow.registration_credential ||
      typeof flow.email !== "string" ||
      !flow.email ||
      typeof flow.expires_at !== "string" ||
      isRegistrationFlowExpired(flow)
    ) {
      clearRegistrationFlow();
      return null;
    }
    return { ...flow, returnTo: getSafeReturnTo(flow.returnTo) };
  } catch {
    clearRegistrationFlow();
    return null;
  }
}

export function clearRegistrationFlow(): void {
  window.sessionStorage.removeItem(REGISTRATION_KEY);
  window.localStorage.removeItem(REGISTRATION_KEY);
}

function isRegistrationFlowExpired(flow: RegistrationFlow): boolean {
  if (!flow.expires_at) return false;
  const expiresAt = Date.parse(flow.expires_at);
  return Number.isFinite(expiresAt) && expiresAt <= Date.now();
}
