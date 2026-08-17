import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileVideo, Pencil, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  archiveLearningVideo,
  getAdminLearningVideos,
  publishLearningVideo,
  updateAdminLearningVideo,
  uploadLearningVideo,
} from "@/api/learning";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import {
  PageActions,
  PageHeader,
  PageSection,
  PageShell,
  PageStaleNotice,
  PageState,
} from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatLearningVideoStatus,
} from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type { LearningVideo, LearningVideoStatus } from "@/types/learning";

type Notice = { tone: "success" | "error"; message: string };
type StatusAction = "publish" | "archive";

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function formatBytes(bytes: number) {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
  }
  return `${Math.max(1, Math.ceil(bytes / 1024))} KiB`;
}

function formatDateTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

function statusVariant(status: LearningVideoStatus): StatusPillVariant {
  if (status === "published") return "success";
  if (status === "archived") return "warning";
  return "neutral";
}

function statusActionPending(
  mutation: { isPending: boolean; variables?: { id: number; action: StatusAction } },
  videoId: number,
  action: StatusAction,
) {
  return (
    mutation.isPending && mutation.variables?.id === videoId && mutation.variables.action === action
  );
}

export function AdminLearningVideoPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [probeUrl, setProbeUrl] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [editingVideo, setEditingVideo] = useState<LearningVideo | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const editDialogReturnFocusRef = useRef<HTMLElement | null>(null);
  const editDialogReturnFocusIdRef = useRef<number | null>(null);

  const videos = useQuery({
    queryKey: adminKeys.learningVideos(),
    queryFn: getAdminLearningVideos,
  });

  useEffect(() => {
    if (!file) {
      setProbeUrl(null);
      return;
    }
    const nextUrl = URL.createObjectURL(file);
    setProbeUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);

  useEffect(() => {
    if (editDialogOpen || editDialogReturnFocusIdRef.current === null) return;

    const returnFocusId = editDialogReturnFocusIdRef.current;
    const timeoutId = window.setTimeout(() => {
      const returnFocus = editDialogReturnFocusRef.current;
      if (returnFocus?.isConnected) {
        returnFocus.focus();
        return;
      }
      document
        .querySelector<HTMLElement>(`[data-learning-video-edit-id="${returnFocusId}"]`)
        ?.focus();
    });

    return () => window.clearTimeout(timeoutId);
  }, [editDialogOpen]);

  const uploadMutation = useMutation({
    mutationFn: uploadLearningVideo,
    onSuccess: () => {
      setNotice({ tone: "success", message: "视频已上传为草稿。" });
      setTitle("");
      setDescription("");
      setFile(null);
      setDurationSeconds(null);
      setMetadataError(null);
      void queryClient.invalidateQueries({ queryKey: adminKeys.learningVideos() });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "视频上传失败") }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "publish" | "archive" }) =>
      action === "publish" ? publishLearningVideo(id) : archiveLearningVideo(id),
    onSuccess: () => {
      setNotice({ tone: "success", message: "视频状态已更新。" });
      void queryClient.invalidateQueries({ queryKey: adminKeys.learningVideos() });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "视频状态更新失败") }),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { id: number; title: string; description: string | null }) =>
      updateAdminLearningVideo(payload.id, {
        title: payload.title,
        description: payload.description,
      }),
    onSuccess: () => {
      setEditDialogOpen(false);
      setEditingVideo(null);
      setNotice({ tone: "success", message: "视频信息已保存。" });
      void queryClient.invalidateQueries({ queryKey: adminKeys.learningVideos() });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "视频信息保存失败") }),
  });

  function handleFileChange(nextFile: File | null) {
    setFile(nextFile);
    setDurationSeconds(null);
    setMetadataError(null);
    if (nextFile && !title.trim()) {
      setTitle(nextFile.name.replace(/\.[^.]+$/, ""));
    }
  }

  function handleUpload() {
    if (!file || !durationSeconds || !title.trim()) {
      return;
    }
    uploadMutation.mutate({
      title: title.trim(),
      description: description.trim() || null,
      duration_seconds: durationSeconds,
      file,
    });
  }

  function openEdit(video: LearningVideo) {
    editDialogReturnFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    editDialogReturnFocusIdRef.current = video.id;
    setNotice(null);
    updateMutation.reset();
    setEditingVideo(video);
    setEditTitle(video.title);
    setEditDescription(video.description ?? "");
    setEditDialogOpen(true);
  }

  const columns: ColumnDef<LearningVideo>[] = [
    {
      accessorKey: "title",
      header: adminTableCopy.title,
      cell: ({ row }) => (
        <div className="flex min-w-0 flex-col gap-1">
          <span className="min-w-0 break-words font-medium">{row.original.title}</span>
          <span className="min-w-0 break-words text-caption text-muted">
            {row.original.original_filename}
          </span>
        </div>
      ),
      meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.title },
    },
    {
      accessorKey: "duration_seconds",
      header: adminTableCopy.duration,
      cell: ({ row }) => (
        <span className="font-mono text-body-sm tabular-nums">
          {formatDuration(row.original.duration_seconds)}
        </span>
      ),
      meta: { mobileLabel: adminTableCopy.duration },
    },
    {
      accessorKey: "file_size_bytes",
      header: "文件大小",
      cell: ({ row }) => (
        <span className="font-mono text-body-sm">{formatBytes(row.original.file_size_bytes)}</span>
      ),
      meta: { mobileLabel: "文件大小" },
    },
    {
      accessorKey: "status",
      header: adminTableCopy.status,
      cell: ({ row }) => (
        <StatusPill variant={statusVariant(row.original.status)}>
          {formatLearningVideoStatus(row.original.status)}
        </StatusPill>
      ),
      meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.status },
    },
    {
      accessorKey: "uploaded_at",
      header: "上传时间",
      cell: ({ row }) => (
        <span className="text-body-sm">{formatDateTime(row.original.uploaded_at)}</span>
      ),
      meta: { mobileLabel: "上传时间" },
    },
    {
      id: "actions",
      header: adminTableCopy.action,
      cell: ({ row }) => (
        <PageActions placement="card" aria-label="视频操作">
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-learning-video-edit-id={row.original.id}
            onClick={() => openEdit(row.original)}
          >
            <Pencil data-icon="inline-start" />
            编辑
          </Button>
          {row.original.status !== "published" ? (
            <Button
              type="button"
              size="sm"
              pending={statusActionPending(statusMutation, row.original.id, "publish")}
              onClick={() => statusMutation.mutate({ id: row.original.id, action: "publish" })}
            >
              发布
            </Button>
          ) : null}
          {row.original.status !== "archived" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              pending={statusActionPending(statusMutation, row.original.id, "archive")}
              onClick={() => statusMutation.mutate({ id: row.original.id, action: "archive" })}
            >
              归档
            </Button>
          ) : null}
        </PageActions>
      ),
      meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.action },
    },
  ];

  const uploadDisabled = !file || !durationSeconds || !title.trim() || Boolean(metadataError);

  return (
    <PageShell data-testid="admin-learning-video-shell" density="workbench" width="full">
      <PageHeader
        eyebrow={adminPageCopy.learning}
        title={adminPageText.learning.title}
        description={adminPageText.learning.description}
      />

      <PageSection
        variant="panel"
        className="gap-section"
        aria-busy={uploadMutation.isPending || undefined}
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <Field>
            <FieldLabel htmlFor="learning-video-title">视频标题</FieldLabel>
            <Input
              id="learning-video-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：入职安全学习"
            />
          </Field>
          <Field invalid={Boolean(metadataError)} pending={uploadMutation.isPending}>
            <FieldLabel htmlFor="learning-video-file">视频文件</FieldLabel>
            <input
              ref={fileInputRef}
              id="learning-video-file"
              type="file"
              accept="video/mp4,video/webm"
              className="hidden"
              disabled={uploadMutation.isPending}
              aria-label="选择视频文件"
              aria-describedby={`learning-video-file-status${metadataError ? " learning-video-file-error" : ""}`}
              aria-invalid={metadataError ? true : undefined}
              onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
            />
            <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
              <PageActions placement="card" aria-label="视频文件操作">
                <Button
                  type="button"
                  variant="outline"
                  disabled={uploadMutation.isPending}
                  aria-controls="learning-video-file"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileVideo data-icon="inline-start" />
                  选择视频文件
                </Button>
              </PageActions>
              <FieldDescription
                id="learning-video-file-status"
                className="min-w-0 break-words"
                aria-live="polite"
              >
                {file ? `${file.name} · ${formatBytes(file.size)}` : "MP4 / WebM，最大 500 MiB"}
              </FieldDescription>
            </div>
            {metadataError ? (
              <FieldError id="learning-video-file-error">{metadataError}</FieldError>
            ) : null}
          </Field>
        </div>

        <Field>
          <FieldLabel htmlFor="learning-video-description">视频说明</FieldLabel>
          <Textarea
            id="learning-video-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="可选，用于说明学习目标或适用人群。"
          />
        </Field>

        {probeUrl ? (
          <video
            data-testid="learning-duration-probe"
            aria-hidden="true"
            className="hidden"
            src={probeUrl}
            preload="metadata"
            onLoadedMetadata={(event) => {
              const duration = Math.ceil(event.currentTarget.duration);
              if (Number.isFinite(duration) && duration > 0) {
                setDurationSeconds(duration);
                setMetadataError(null);
              } else {
                setMetadataError("无法读取视频时长，请确认文件可播放。");
              }
            }}
            onError={() => setMetadataError("无法读取视频元数据，请重新选择文件。")}
          />
        ) : null}

        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
          <PageActions placement="form" aria-label="视频上传操作">
            <Button
              type="button"
              disabled={uploadDisabled}
              pending={uploadMutation.isPending}
              onClick={handleUpload}
            >
              <UploadCloud data-icon="inline-start" />
              {uploadMutation.isPending ? "上传中" : "上传视频"}
            </Button>
          </PageActions>
          <span className="text-body-sm text-muted">
            {durationSeconds
              ? `已读取时长 ${formatDuration(durationSeconds)}`
              : "选择视频后自动读取时长。"}
          </span>
        </div>
      </PageSection>

      {notice && !editingVideo ? (
        <Alert variant={notice.tone === "success" ? "success" : "error"}>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      {videos.isError && videos.data ? (
        <PageStaleNotice
          lastSuccessfulAt={videos.dataUpdatedAt}
          onRetry={() => void videos.refetch()}
          retrying={videos.isFetching}
        />
      ) : null}

      <PageSection variant="data">
        {videos.isLoading ? (
          <PageState state="loading" surface="inherit" rows={3} skeletonVariant="table" />
        ) : videos.isError && !videos.data ? (
          <PageState
            state="error"
            surface="inherit"
            eyebrow={adminPageCopy.error}
            title="视频列表加载失败。"
            description="请稍后重试，或确认后台服务是否可用。"
            onRetry={() => void videos.refetch()}
          />
        ) : (
          <SimpleDataTable columns={columns} data={videos.data ?? []} emptyText="暂无学习视频" />
        )}
      </PageSection>

      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) {
            setEditingVideo(null);
          }
        }}
      >
        <DialogContent
          onCloseAutoFocus={(event) => {
            const returnFocus = editDialogReturnFocusRef.current;
            if (returnFocus?.isConnected) {
              event.preventDefault();
              returnFocus.focus();
            }
          }}
        >
          <DialogHeader chapter={adminPageCopy.learning}>
            <DialogTitle>编辑视频信息</DialogTitle>
            <DialogDescription>仅更新标题和说明，不替换已上传的视频文件。</DialogDescription>
          </DialogHeader>
          {updateMutation.isError && notice ? (
            <Alert variant="error">
              <AlertDescription>{notice.message}</AlertDescription>
            </Alert>
          ) : null}
          <form
            className="flex min-w-0 flex-col gap-4"
            aria-busy={updateMutation.isPending || undefined}
            onSubmit={(event) => {
              event.preventDefault();
              if (!editingVideo || !editTitle.trim()) return;
              updateMutation.mutate({
                id: editingVideo.id,
                title: editTitle.trim(),
                description: editDescription.trim() || null,
              });
            }}
          >
            <Field pending={updateMutation.isPending}>
              <FieldLabel htmlFor="learning-video-edit-title">视频标题</FieldLabel>
              <Input
                id="learning-video-edit-title"
                value={editTitle}
                onChange={(event) => setEditTitle(event.target.value)}
              />
            </Field>
            <Field pending={updateMutation.isPending}>
              <FieldLabel htmlFor="learning-video-edit-description">视频说明</FieldLabel>
              <Textarea
                id="learning-video-edit-description"
                value={editDescription}
                onChange={(event) => setEditDescription(event.target.value)}
              />
            </Field>
            <PageActions placement="form" aria-label="视频编辑操作">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditDialogOpen(false);
                  setEditingVideo(null);
                }}
              >
                取消
              </Button>
              <Button
                type="submit"
                pending={updateMutation.isPending}
                disabled={!editingVideo || !editTitle.trim()}
              >
                {updateMutation.isPending ? "保存中" : "保存"}
              </Button>
            </PageActions>
          </form>
        </DialogContent>
      </Dialog>
    </PageShell>
  );
}
