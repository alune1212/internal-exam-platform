import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileVideo, Pencil, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";

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
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  return "default";
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
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

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
    setEditingVideo(video);
    setEditTitle(video.title);
    setEditDescription(video.description ?? "");
  }

  const columns: ColumnDef<LearningVideo>[] = [
    {
      accessorKey: "title",
      header: adminTableCopy.title,
      cell: ({ row }) => (
        <div className="flex flex-col gap-1">
          <span className="font-medium">{row.original.title}</span>
          <span className="text-caption text-muted">{row.original.original_filename}</span>
        </div>
      ),
      meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.title },
    },
    {
      accessorKey: "duration_seconds",
      header: adminTableCopy.duration,
      cell: ({ row }) => (
        <span className="font-mono text-sm tabular-nums">
          {formatDuration(row.original.duration_seconds)}
        </span>
      ),
      meta: { mobileLabel: adminTableCopy.duration },
    },
    {
      accessorKey: "file_size_bytes",
      header: "SIZE · 文件",
      cell: ({ row }) => (
        <span className="font-mono text-sm">{formatBytes(row.original.file_size_bytes)}</span>
      ),
      meta: { mobileLabel: "SIZE · 文件" },
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
      header: "UPLOADED · 上传时间",
      cell: ({ row }) => (
        <span className="text-body-sm">{formatDateTime(row.original.uploaded_at)}</span>
      ),
      meta: { mobileLabel: "UPLOADED · 上传时间" },
    },
    {
      id: "actions",
      header: adminTableCopy.action,
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => openEdit(row.original)}>
            <Pencil data-icon="inline-start" />
            编辑
          </Button>
          {row.original.status !== "published" ? (
            <Button
              type="button"
              size="sm"
              disabled={statusActionPending(statusMutation, row.original.id, "publish")}
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
              disabled={statusActionPending(statusMutation, row.original.id, "archive")}
              onClick={() => statusMutation.mutate({ id: row.original.id, action: "archive" })}
            >
              归档
            </Button>
          ) : null}
        </div>
      ),
      meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.action },
    },
  ];

  const uploadDisabled =
    uploadMutation.isPending ||
    !file ||
    !durationSeconds ||
    !title.trim() ||
    Boolean(metadataError);

  return (
    <PageShell data-testid="admin-learning-video-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.learning}
        title={adminPageText.learning.title}
        description={adminPageText.learning.description}
      />

      <PageSection variant="card" className="gap-5 p-6">
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="flex flex-col gap-2">
            <Label htmlFor="learning-video-title">视频标题</Label>
            <Input
              id="learning-video-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：入职安全学习"
            />
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-ink">视频文件</span>
            <input
              id="learning-video-file"
              type="file"
              accept="video/mp4,video/webm"
              className="sr-only"
              onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button asChild type="button" variant="outline">
                <label htmlFor="learning-video-file" className="cursor-pointer">
                  <FileVideo data-icon="inline-start" />
                  选择视频文件
                </label>
              </Button>
              <span className="text-body-sm text-muted">
                {file ? `${file.name} · ${formatBytes(file.size)}` : "MP4 / WebM，最大 500 MiB"}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="learning-video-description">视频说明</Label>
          <Textarea
            id="learning-video-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="可选，用于说明学习目标或适用人群。"
          />
        </div>

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

        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" disabled={uploadDisabled} onClick={handleUpload}>
            <UploadCloud data-icon="inline-start" />
            {uploadMutation.isPending ? "上传中" : "上传视频"}
          </Button>
          <span className="text-body-sm text-muted">
            {durationSeconds
              ? `已读取时长 ${formatDuration(durationSeconds)}`
              : "选择视频后自动读取时长。"}
          </span>
        </div>
        {metadataError ? (
          <Alert variant="error">
            <AlertDescription>{metadataError}</AlertDescription>
          </Alert>
        ) : null}
      </PageSection>

      {notice ? (
        <Alert variant={notice.tone === "success" ? "success" : "error"}>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      <PageSection variant="table">
        {videos.isLoading ? (
          <PageState state="loading" surface="inherit" rows={3} />
        ) : videos.isError && !videos.data ? (
          <PageState
            state="error"
            surface="inherit"
            eyebrow={adminPageCopy.error}
            title="视频列表加载失败。"
            description="请稍后重试，或确认后台服务是否可用。"
            className="py-10"
          />
        ) : (
          <SimpleDataTable columns={columns} data={videos.data ?? []} emptyText="暂无学习视频" />
        )}
      </PageSection>

      <Dialog
        open={Boolean(editingVideo)}
        onOpenChange={(open) => {
          if (!open) {
            setEditingVideo(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader chapter={adminPageCopy.learning}>
            <DialogTitle>编辑视频信息</DialogTitle>
            <DialogDescription>仅更新标题和说明，不替换已上传的视频文件。</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="learning-video-edit-title">视频标题</Label>
              <Input
                id="learning-video-edit-title"
                value={editTitle}
                onChange={(event) => setEditTitle(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="learning-video-edit-description">视频说明</Label>
              <Textarea
                id="learning-video-edit-description"
                value={editDescription}
                onChange={(event) => setEditDescription(event.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditingVideo(null)}>
              取消
            </Button>
            <Button
              type="button"
              disabled={updateMutation.isPending || !editingVideo || !editTitle.trim()}
              onClick={() =>
                editingVideo &&
                updateMutation.mutate({
                  id: editingVideo.id,
                  title: editTitle.trim(),
                  description: editDescription.trim() || null,
                })
              }
            >
              {updateMutation.isPending ? "保存中" : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  );
}
