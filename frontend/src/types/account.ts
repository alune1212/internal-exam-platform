export type AccountStatus = "pending" | "active" | "inactive";

export type AdminAccount = {
  id: number;
  email: string;
  display_name?: string | null;
  status: AccountStatus | string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AccountStatusUpdate = {
  status: Exclude<AccountStatus, "pending">;
};
