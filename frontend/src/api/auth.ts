import { apiRequest } from "@/api/client";
import type { Candidate } from "@/types/candidate";

export type CandidateLoginChallenge = {
  challenge_id: number;
  expires_at: string;
  resend_available_at: string;
};

export function requestCandidateLoginOtp(payload: {
  name: string;
  employee_no?: string;
  email: string;
}) {
  return apiRequest<CandidateLoginChallenge>("/api/candidates/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyCandidateLoginOtp(payload: { challenge_id: number; otp: string }) {
  return apiRequest<Candidate>("/api/candidates/login/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginAdmin(payload: { username: string; password: string }) {
  return apiRequest<{ token: string; token_type: string }>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
