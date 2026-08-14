import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { getErrorMessage } from "@/api/client";
import { getAdminAccounts, updateAdminAccountStatus } from "@/api/accounts";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { AccountStatus, AdminAccount } from "@/types/account";

type AccountFilter = AccountStatus | "all";

const statusLabels: Record<string, string> = {
  pending: "待完成注册",
  active: "已启用",
  inactive: "已停用",
};

function statusVariant(status: string): StatusPillVariant {
  if (status === "active") return "success";
  if (status === "inactive") return "error";
  return "warning";
}

export function AccountDirectoryPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<AccountFilter>("all");
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const accounts = useQuery({
    queryKey: ["admin", "accounts", search, status],
    queryFn: () => getAdminAccounts({ query: search, status }),
    retry: false,
  });
  const statusMutation = useMutation({
    mutationFn: ({
      accountId,
      nextStatus,
    }: {
      accountId: number;
      nextStatus: Exclude<AccountStatus, "pending">;
    }) => updateAdminAccountStatus(accountId, nextStatus),
    onSuccess: (_account, variables) => {
      setNotice({
        tone: "success",
        message:
          variables.nextStatus === "active"
            ? "账户已重新启用。"
            : "账户已停用；其历史记录与名单快照仍保留。",
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "accounts"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "账户状态更新失败") }),
  });

  const columns = useMemo<ColumnDef<AdminAccount>[]>(
    () => [
      {
        accessorKey: "display_name",
        header: "ACCOUNT NAME · 用户姓名",
        cell: ({ row }) => (
          <span className="font-medium text-ink">{row.original.display_name || "未完成注册"}</span>
        ),
        meta: { mobilePriority: "primary", mobileLabel: "用户姓名" },
      },
      {
        accessorKey: "email",
        header: "EMAIL · 邮箱",
        cell: ({ row }) => <span className="font-mono text-sm">{row.original.email}</span>,
        meta: { mobileLabel: "邮箱" },
      },
      {
        accessorKey: "status",
        header: "STATUS · 账户状态",
        cell: ({ row }) => (
          <StatusPill variant={statusVariant(row.original.status)}>
            {statusLabels[row.original.status] ?? "未知状态"}
          </StatusPill>
        ),
        meta: { mobileLabel: "账户状态" },
      },
      {
        id: "action",
        header: "ACTION · 操作",
        meta: { mobileLabel: "操作" },
        cell: ({ row }) => {
          const accountStatus = row.original.status;
          if (accountStatus !== "active" && accountStatus !== "inactive") {
            return <span className="text-caption text-muted">完成注册后可管理</span>;
          }
          const nextStatus = accountStatus === "active" ? "inactive" : "active";
          return (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={statusMutation.isPending}
              onClick={() => statusMutation.mutate({ accountId: row.original.id, nextStatus })}
            >
              {nextStatus === "active" ? "重新启用" : "停用账户"}
            </Button>
          );
        },
      },
    ],
    [statusMutation],
  );

  const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSearch(query.trim());
  };

  return (
    <PageShell data-testid="account-directory-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow="ACCOUNTS · 用户账户"
        title="账户目录"
        description="按邮箱或显示名查找平台用户，只能管理已完成注册账户的启用状态；邮箱不可编辑，也不提供删除操作。"
      />

      <PageSection variant="panel" className="p-6 lg:p-8">
        <form className="flex flex-col gap-4 md:flex-row md:items-end" onSubmit={submitSearch}>
          <Field className="min-w-0 flex-1">
            <FieldLabel htmlFor="account-search">搜索邮箱或显示名</FieldLabel>
            <Input
              id="account-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如 user@example.com"
            />
          </Field>
          <Field className="md:w-48">
            <FieldLabel htmlFor="account-status-filter">账户状态</FieldLabel>
            <Select
              id="account-status-filter"
              aria-label="账户状态"
              value={status}
              onChange={(event) => setStatus(event.target.value as AccountFilter)}
            >
              <option value="all">全部状态</option>
              <option value="pending">待完成注册</option>
              <option value="active">已启用</option>
              <option value="inactive">已停用</option>
            </Select>
          </Field>
          <Button type="submit" className="md:mb-0">
            <Search data-icon="inline-start" />
            搜索账户
          </Button>
        </form>
      </PageSection>

      {notice ? (
        <Alert variant={notice.tone === "success" ? "success" : "error"}>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      {accounts.isError && accounts.data ? (
        <PageStaleNotice
          lastSuccessfulAt={accounts.dataUpdatedAt}
          onRetry={() => accounts.refetch()}
          retrying={accounts.isFetching}
        />
      ) : null}

      <PageSection variant="table">
        {accounts.isLoading ? (
          <PageState state="loading" rows={4} surface="inherit" className="py-10" />
        ) : accounts.isError && !accounts.data ? (
          <PageState
            state="error"
            eyebrow="STATE · 异常状态"
            title="账户目录加载失败。"
            description="请稍后重试，或检查管理员账户接口。"
            onRetry={() => void accounts.refetch()}
            surface="inherit"
            className="py-10"
          />
        ) : (
          <SimpleDataTable
            columns={columns}
            data={accounts.data ?? []}
            emptyText="没有符合条件的账户。"
            rowKey={(row) => row.id}
          />
        )}
      </PageSection>
    </PageShell>
  );
}
