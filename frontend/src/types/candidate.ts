/** The lifecycle states exposed by the platform-account API. */
export type CandidateStatus = "pending" | "active" | "inactive";

/** Account data returned by the auth/profile APIs before session credentials are added. */
export type CandidateAccount = {
  id: number;
  email: string;
  display_name: string | null;
  status: CandidateStatus;
};

export type ActiveCandidateAccount = Omit<CandidateAccount, "status"> & {
  status: "active";
};

/** Candidate account plus the short-lived credential kept in sessionStorage. */
export type Candidate = ActiveCandidateAccount & {
  token: string;
  token_expires_at: string;
};

export type CandidateProfile = CandidateAccount;

export function candidateDisplayName(candidate: Pick<CandidateAccount, "display_name">) {
  return candidate.display_name?.trim() || "用户";
}
