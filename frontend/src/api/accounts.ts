import { apiRequest } from "@/api/client";
import type { AdminAccount, AccountStatus } from "@/types/account";

export type AccountSearchFilters = {
  query?: string;
  status?: AccountStatus | "all" | null;
};

function withAccountFilters(filters?: AccountSearchFilters) {
  const params = new URLSearchParams();
  if (filters?.query?.trim()) params.set("search", filters.query.trim());
  if (filters?.status && filters.status !== "all") params.set("status", filters.status);
  const query = params.toString();
  return query ? `/api/admin/accounts?${query}` : "/api/admin/accounts";
}

export function getAdminAccounts(filters?: AccountSearchFilters) {
  return apiRequest<AdminAccount[]>(withAccountFilters(filters));
}

export function updateAdminAccountStatus(
  accountId: number,
  status: Exclude<AccountStatus, "pending">,
) {
  return apiRequest<AdminAccount>(`/api/admin/accounts/${accountId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
