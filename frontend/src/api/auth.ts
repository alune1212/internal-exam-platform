import { apiRequest } from "@/api/client";
import type { Candidate, CandidateAccount, CandidateProfile } from "@/types/candidate";

export type CandidateLoginChallenge = {
  challenge_id: number;
  expires_at: string;
  resend_available_at: string;
};

export type CandidateAuthenticated = {
  outcome: "authenticated";
  account: CandidateAccount;
  token: string;
  token_expires_at: string;
};

export type CandidateRegistrationRequired = {
  outcome: "registration_required";
  registration_credential: string;
  email: string;
  suggested_display_name: string | null;
  registration_expires_at: string;
};

export type CandidateAccountUnavailable = {
  outcome: "account_unavailable";
  message: string;
};

export type CandidateLoginVerification =
  | CandidateAuthenticated
  | CandidateRegistrationRequired
  | CandidateAccountUnavailable;

export function requestCandidateLoginOtp(payload: { email: string }) {
  return apiRequest<CandidateLoginChallenge>("/api/candidates/login", {
    method: "POST",
    body: JSON.stringify({ email: payload.email.trim().toLowerCase() }),
  });
}

export function candidateFromAuthenticated(response: CandidateAuthenticated): Candidate {
  if (response.account.status !== "active") {
    throw new Error("账号暂不可用，请联系管理员重新激活后再登录。");
  }
  return {
    ...response.account,
    status: "active",
    token: response.token,
    token_expires_at: response.token_expires_at,
  };
}

export function verifyCandidateLoginOtp(payload: {
  challenge_id: number;
  otp: string;
}): Promise<CandidateLoginVerification> {
  return apiRequest<CandidateLoginVerification>("/api/candidates/login/verify", {
    method: "POST",
    body: JSON.stringify({ challenge_id: payload.challenge_id, otp: payload.otp.trim() }),
  });
}

export function completeCandidateRegistration(payload: {
  registration_credential: string;
  display_name: string;
}): Promise<Candidate> {
  return apiRequest<CandidateAuthenticated>("/api/candidates/register/complete", {
    method: "POST",
    body: JSON.stringify({
      registration_credential: payload.registration_credential,
      display_name: payload.display_name.trim(),
    }),
  }).then(candidateFromAuthenticated);
}

function normalizeProfile(profile: CandidateProfile): CandidateProfile {
  return {
    ...profile,
    id: Number(profile.id),
    email: profile.email.trim().toLowerCase(),
    display_name: profile.display_name?.trim() || null,
  };
}

export function getCandidateProfile(): Promise<CandidateProfile> {
  return apiRequest<CandidateProfile>("/api/account/profile").then(normalizeProfile);
}

export function updateCandidateProfile(payload: {
  display_name: string;
}): Promise<CandidateProfile> {
  return apiRequest<CandidateProfile>("/api/account/profile", {
    method: "PATCH",
    body: JSON.stringify({ display_name: payload.display_name.trim() }),
  }).then(normalizeProfile);
}

export function loginAdmin(payload: { username: string; password: string }) {
  return apiRequest<{ token: string; token_type: string }>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
