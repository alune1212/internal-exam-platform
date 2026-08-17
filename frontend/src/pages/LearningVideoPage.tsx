import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { getLearningVideo, updateLearningProgress } from "@/api/learning";
import { StatusPill } from "@/components/editorial/StatusPill";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";
import { candidateKeys } from "@/lib/queryKeys";
import type { LearningProgressPayload, LearningVideoProgress } from "@/types/learning";

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

export function LearningVideoPage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const { videoId } = useParams();
  const navigate = useNavigate();
  const numericVideoId = Number(videoId);
  const queryClient = useQueryClient();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const watchedStartRef = useRef<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progressOverride, setProgressOverride] = useState<LearningVideoProgress | null>(null);

  const { data, dataUpdatedAt, isError, isLoading, isFetching, refetch } = useQuery({
    queryKey: candidateKeys.learningVideo(numericVideoId),
    queryFn: () => getLearningVideo(String(numericVideoId)),
    enabled: Boolean(candidate) && Number.isFinite(numericVideoId),
    retry: false,
  });

  useEffect(() => {
    setProgressOverride(null);
    watchedStartRef.current = null;
  }, [numericVideoId]);

  const mutation = useMutation({
    mutationFn: (payload: LearningProgressPayload) =>
      updateLearningProgress(numericVideoId, payload),
    onSuccess: (progress) => {
      setProgressOverride(progress);
      void queryClient.invalidateQueries({ queryKey: candidateKeys.learningVideos() });
    },
  });

  const progress = progressOverride ?? data?.progress;

  const sendHeartbeat = useCallback(() => {
    const video = videoRef.current;
    if (!video || !data || !Number.isFinite(video.currentTime)) {
      return;
    }
    const currentPosition = Math.floor(video.currentTime);
    const watchedStart = watchedStartRef.current ?? currentPosition;
    watchedStartRef.current = currentPosition;
    if (currentPosition <= watchedStart) {
      return;
    }
    mutation.mutate({
      current_position_seconds: currentPosition,
      watched_start_seconds: watchedStart,
      watched_end_seconds: currentPosition,
    });
  }, [data, mutation]);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    const interval = window.setInterval(sendHeartbeat, 10_000);
    return () => window.clearInterval(interval);
  }, [isPlaying, sendHeartbeat]);

  if (isLoading) {
    return (
      <PageShell density="calm" width="wide">
        <PageHeader
          title={candidatePageText.learning.title}
          description={candidatePageText.learning.description}
        />
        <PageSection variant="plain">
          <PageState state="loading" rows={4} surface="inherit" />
        </PageSection>
      </PageShell>
    );
  }

  if (!data || !progress) {
    return (
      <PageShell density="calm" width="wide">
        <PageHeader
          title={candidatePageText.learning.title}
          description={candidatePageText.learning.description}
        />
        <PageSection variant="plain">
          <PageState
            state="error"
            surface="inherit"
            eyebrow={candidatePageCopy.error}
            title={candidatePageText.learning.detailErrorTitle}
            description={candidatePageText.learning.detailErrorDescription}
            onRetry={() => void refetch()}
            secondaryAction={{ label: "返回学习列表", onClick: () => navigate("/learning") }}
          />
        </PageSection>
      </PageShell>
    );
  }

  const completed = Boolean(progress.completed_at);

  return (
    <PageShell density="calm" width="wide" data-testid="learning-video-shell">
      {isError ? (
        <PageStaleNotice
          lastSuccessfulAt={dataUpdatedAt}
          onRetry={() => refetch()}
          retrying={isFetching}
        />
      ) : null}
      <PageHeader
        title={data.title}
        description={data.description ?? "完成度达到 90% 后，系统会标记为已完成。"}
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/learning">
              <ArrowLeft data-icon="inline-start" />
              返回学习列表
            </Link>
          </Button>
        }
      />

      <PageSection variant="plain" aria-label="视频播放">
        <Card surface="focus" className="flex min-w-0 flex-col gap-5 p-5 lg:p-7">
          <video
            ref={videoRef}
            className="aspect-video w-full rounded-md bg-black"
            src={data.playback_url}
            controls
            preload="metadata"
            playsInline
            onLoadedMetadata={(event) => {
              const element = event.currentTarget;
              if (progress.last_position_seconds > 0 && element.currentTime === 0) {
                element.currentTime = Math.min(
                  progress.last_position_seconds,
                  data.duration_seconds,
                );
              }
            }}
            onPlay={(event) => {
              setIsPlaying(true);
              watchedStartRef.current = Math.floor(event.currentTarget.currentTime);
            }}
            onSeeking={() => {
              watchedStartRef.current = null;
            }}
            onSeeked={(event) => {
              watchedStartRef.current = Math.floor(event.currentTarget.currentTime);
            }}
            onPause={() => {
              setIsPlaying(false);
              sendHeartbeat();
            }}
            onEnded={() => {
              setIsPlaying(false);
              sendHeartbeat();
            }}
          />

          <div
            className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center"
            aria-busy={mutation.isPending}
          >
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-3">
                <StatusPill variant={completed ? "success" : "warning"}>
                  {completed
                    ? candidatePageText.learning.completed
                    : candidatePageText.learning.inProgress}
                </StatusPill>
                <span className="font-mono text-body-sm text-muted">
                  {progress.completion_percent}% / 90%
                </span>
                <span className="text-body-sm text-muted">
                  时长 {formatDuration(data.duration_seconds)}
                </span>
                {mutation.isPending ? (
                  <span role="status" aria-live="polite" className="text-body-sm text-muted">
                    正在保存进度
                  </span>
                ) : null}
              </div>
              <div
                className="h-2 overflow-hidden rounded-pill bg-surface-card"
                role="progressbar"
                aria-label={`${data.title} 完成度`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.min(100, progress.completion_percent)}
              >
                <div
                  className="h-full rounded-pill bg-success"
                  style={{ width: `${Math.min(100, progress.completion_percent)}%` }}
                />
              </div>
            </div>
            {completed ? (
              <span className="inline-flex items-center gap-2 text-body text-success">
                <CheckCircle2 className="size-4" aria-hidden="true" />
                已达到完成标准
              </span>
            ) : null}
          </div>

          {mutation.isError ? (
            <Alert variant="error">
              <AlertDescription>
                {getErrorMessage(mutation.error, "学习进度保存失败，请稍后重试。")}
              </AlertDescription>
            </Alert>
          ) : null}
        </Card>
      </PageSection>
    </PageShell>
  );
}
