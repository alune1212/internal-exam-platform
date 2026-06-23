import { apiRequest } from "@/api/client";
import type { Candidate } from "@/types/candidate";

export function loginCandidate(payload: {
  name: string;
  employee_no?: string;
  phone_suffix: string;
}) {
  return apiRequest<Candidate>("/api/candidates/login", {
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
