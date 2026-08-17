import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  downloadLearningReportExport,
  getAdminLearningVideos,
  getLearningReport,
} from "@/api/learning";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportToolbar } from "@/components/admin/ReportToolbar";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatLearningCompletion,
  formatLearningVideoStatus,
} from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type {
  LearningCompletionStatus,
  LearningReportRow,
  LearningVideo,
  LearningVideoStatus,
} from "@/types/learning";

type CompletionFilter = LearningCompletionStatus | "all";

function formatDateTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

function videoStatusVariant(status: LearningVideoStatus): StatusPillVariant {
  if (status === "published") return "success";
  if (status === "archived") return "warning";
  return "default";
}

function completionVariant(status: LearningCompletionStatus): StatusPillVariant {
  if (status === "completed") return "success";
  if (status === "in_progress") return "warning";
  return "default";
}

const accountStatusLabels: Record<string, string> = {
  pending: "待完成注册",
  active: "已启用",
  inactive: "已停用",
};

function accountStatusVariant(status: string): StatusPillVariant {
  if (status === "active") return "success";
  if (status === "inactive") return "error";
  return "warning";
}

function LearningReportFilters({
  videos,
  videoId,
  status,
  onVideoChange,
  onStatusChange,
}: {
  videos: LearningVideo[];
  videoId: string | null;
  status: CompletionFilter;
  onVideoChange: (value: string | null) => void;
  onStatusChange: (value: CompletionFilter) => void;
}) {
  return (
    <>
      <Field className="min-w-56">
        <FieldLabel htmlFor="learning-report-video">视频</FieldLabel>
        <Select
          id="learning-report-video"
          aria-label="视频"
          value={videoId ?? "all"}
          onChange={(event) =>
            onVideoChange(event.target.value === "all" ? null : event.target.value)
          }
        >
          <option value="all">全部视频</option>
          {videos.map((video) => (
            <option key={video.id} value={String(video.id)}>
              {video.title}
            </option>
          ))}
        </Select>
      </Field>
      <Field className="min-w-48">
        <FieldLabel htmlFor="learning-report-status">完成状态</FieldLabel>
        <Select
          id="learning-report-status"
          aria-label="完成状态"
          value={status}
          onChange={(event) => onStatusChange(event.target.value as CompletionFilter)}
        >
          <option value="all">全部状态</option>
          <option value="not_started">未开始</option>
          <option value="in_progress">学习中</option>
          <option value="completed">已完成</option>
        </Select>
      </Field>
    </>
  );
}

function LearningReportExportButton({
  videoId,
  status,
}: {
  videoId: string | null;
  status: CompletionFilter;
}) {
  const mutation = useMutation({
    mutationFn: () => downloadLearningReportExport({ videoId, status }),
  });

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        type="button"
        size="sm"
        variant="outline"
        pending={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        <Download data-icon="inline-start" />
        {mutation.isPending ? "导出中" : "导出学习报表"}
      </Button>
      {mutation.isSuccess ? (
        <Alert variant="success" className="py-2">
          <AlertDescription>学习报表已开始下载。</AlertDescription>
        </Alert>
      ) : null}
      {mutation.isError ? (
        <Alert variant="error" className="py-2">
          <AlertDescription>{getErrorMessage(mutation.error, "学习报表导出失败")}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

const columns: ColumnDef<LearningReportRow>[] = [
  {
    accessorKey: "display_name",
    header: "用户姓名",
    cell: ({ row }) => (
      <span className="min-w-0 break-words font-medium">
        {row.original.display_name || "未填写"}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "用户姓名" },
  },
  {
    accessorKey: "account_email",
    header: "用户邮箱",
    cell: ({ row }) => (
      <span className="min-w-0 break-words font-mono text-body-sm">
        {row.original.account_email}
      </span>
    ),
    meta: { mobileLabel: "用户邮箱" },
  },
  {
    accessorKey: "account_status",
    header: "账户状态",
    cell: ({ row }) => (
      <StatusPill variant={accountStatusVariant(row.original.account_status)}>
        {accountStatusLabels[row.original.account_status] ?? "未知状态"}
      </StatusPill>
    ),
    meta: { mobileLabel: "账户状态" },
  },
  {
    accessorKey: "video_title",
    header: adminTableCopy.video,
    cell: ({ row }) => (
      <span className="min-w-0 break-words font-medium">{row.original.video_title}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.video },
  },
  {
    accessorKey: "video_status",
    header: adminTableCopy.videoStatus,
    cell: ({ row }) => (
      <StatusPill variant={videoStatusVariant(row.original.video_status)}>
        {formatLearningVideoStatus(row.original.video_status)}
      </StatusPill>
    ),
    meta: { mobileLabel: adminTableCopy.videoStatus },
  },
  {
    accessorKey: "completion_percent",
    header: adminTableCopy.progress,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.completion_percent}%</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.progress },
  },
  {
    accessorKey: "completion_status",
    header: adminTableCopy.status,
    cell: ({ row }) => (
      <StatusPill variant={completionVariant(row.original.completion_status)}>
        {formatLearningCompletion(row.original.completion_status)}
      </StatusPill>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.status },
  },
  {
    accessorKey: "last_heartbeat_at",
    header: adminTableCopy.lastSeen,
    cell: ({ row }) => (
      <span className="text-body-sm">{formatDateTime(row.original.last_heartbeat_at)}</span>
    ),
    meta: { mobileLabel: adminTableCopy.lastSeen },
  },
  {
    accessorKey: "completed_at",
    header: adminTableCopy.completedAt,
    cell: ({ row }) => (
      <span className="text-body-sm">{formatDateTime(row.original.completed_at)}</span>
    ),
    meta: { mobileLabel: adminTableCopy.completedAt },
  },
];

export function AdminLearningReportPage() {
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<CompletionFilter>("all");
  const videos = useQuery({
    queryKey: adminKeys.learningVideos(),
    queryFn: getAdminLearningVideos,
  });
  const videosPending = videos.isLoading && !videos.data;
  const videosLoadError = videos.isError && !videos.data;

  return (
    <ReportPage
      title={adminPageText.learning.reportTitle}
      chapterLabel={adminPageCopy.learning}
      description="按视频和完成状态查看用户的学习进度；身份使用平台账号邮箱、显示名与状态。"
      queryKey={[
        ...adminKeys.learningReport(selectedVideoId, selectedStatus),
        videosLoadError ? "videos-error" : videosPending ? "videos-loading" : "videos-ready",
      ]}
      queryEnabled={!videosPending}
      isLoading={videosPending}
      onRetry={() => videos.refetch()}
      queryFn={() => {
        if (videosLoadError) {
          throw new Error("视频列表加载失败");
        }
        return getLearningReport({ videoId: selectedVideoId, status: selectedStatus });
      }}
      columns={columns}
      rowKey={(row) => `${row.video_id}-${row.candidate_id}`}
      toolbar={
        videosPending || videosLoadError ? null : (
          <ReportToolbar
            filters={
              <LearningReportFilters
                videos={videos.data ?? []}
                videoId={selectedVideoId}
                status={selectedStatus}
                onVideoChange={setSelectedVideoId}
                onStatusChange={setSelectedStatus}
              />
            }
            actions={
              <LearningReportExportButton videoId={selectedVideoId} status={selectedStatus} />
            }
          />
        )
      }
    />
  );
}
