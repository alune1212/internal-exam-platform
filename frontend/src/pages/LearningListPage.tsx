import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, Film } from "lucide-react";
import { Link, useOutletContext } from "react-router-dom";

import { getLearningVideos } from "@/api/learning";
import { ContextLabel } from "@/components/editorial/ContextLabel";
import { StatusPill } from "@/components/editorial/StatusPill";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import {
  PageActions,
  PageHeader,
  PageSection,
  PageShell,
  PageStaleNotice,
  PageState,
} from "@/components/page";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { candidateKeys } from "@/lib/queryKeys";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";
import type { CandidateLearningVideo } from "@/types/learning";

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function completionLabel(video: CandidateLearningVideo) {
  if (video.progress.completed_at) return candidatePageText.learning.completed;
  if (video.progress.watched_seconds > 0) return candidatePageText.learning.inProgress;
  return candidatePageText.learning.notStarted;
}

function LearningVideoCard({ video }: { video: CandidateLearningVideo }) {
  const completed = Boolean(video.progress.completed_at);

  return (
    <Card
      surface="data"
      data-video-id={video.id}
      className="flex min-w-0 flex-col gap-5 p-5 lg:p-7"
    >
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-2">
          <ContextLabel>学习视频</ContextLabel>
          <CardTitle as="h2">{video.title}</CardTitle>
        </div>
        <StatusPill className="shrink-0" variant={completed ? "success" : "warning"}>
          {completionLabel(video)}
        </StatusPill>
      </div>
      {video.description ? (
        <CardDescription className="break-words text-body text-muted">
          {video.description}
        </CardDescription>
      ) : null}
      <dl className="grid grid-cols-2 gap-3 border-y border-hairline-soft py-3 text-table-label text-muted">
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1">
            <Clock className="size-3" /> 时长
          </dt>
          <dd className="font-mono text-body text-ink">{formatDuration(video.duration_seconds)}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1">
            <Film className="size-3" /> 完成度
          </dt>
          <dd className="font-mono text-body text-ink">{video.progress.completion_percent}%</dd>
        </div>
      </dl>
      <div
        className="h-2 overflow-hidden rounded-pill bg-surface-card"
        role="progressbar"
        aria-label={`${video.title} 完成度`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.min(100, video.progress.completion_percent)}
      >
        <div
          className="h-full rounded-pill bg-success"
          style={{ width: `${Math.min(100, video.progress.completion_percent)}%` }}
        />
      </div>
      <PageActions placement="card" aria-label="视频操作">
        <Button asChild size="sm">
          <Link to={`/learning/${video.id}`}>
            {completed ? "回看视频" : "继续学习"}
            <ArrowUpRight data-icon="inline-end" aria-hidden="true" />
          </Link>
        </Button>
      </PageActions>
    </Card>
  );
}

export function LearningListPage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const { data, dataUpdatedAt, isError, isLoading, isFetching, refetch } = useQuery({
    queryKey: candidateKeys.learningVideos(),
    queryFn: getLearningVideos,
    enabled: Boolean(candidate),
    retry: false,
  });
  const hasLoadError = isError && !data;
  const hasStaleError = isError && Boolean(data);
  const videos = data ?? [];

  return (
    <PageShell density="calm" width="wide" stagger data-testid="candidate-learning-list-shell">
      <PageHeader
        title={candidatePageText.learning.title}
        description={candidatePageText.learning.description}
      />

      {hasStaleError ? (
        <PageStaleNotice
          lastSuccessfulAt={dataUpdatedAt}
          onRetry={() => refetch()}
          retrying={isFetching}
        />
      ) : null}

      {isLoading ? (
        <PageSection variant="plain">
          <PageState state="loading" rows={3} surface="inherit" />
        </PageSection>
      ) : hasLoadError ? (
        <PageSection variant="plain">
          <PageState
            state="error"
            surface="inherit"
            eyebrow={candidatePageCopy.error}
            title={candidatePageText.learning.errorTitle}
            description={candidatePageText.learning.errorDescription}
            onRetry={() => void refetch()}
          />
        </PageSection>
      ) : videos.length ? (
        <PageSection variant="plain" aria-label="学习视频列表">
          <div className="grid gap-5 md:grid-cols-2">
            {videos.map((video) => (
              <LearningVideoCard key={video.id} video={video} />
            ))}
          </div>
        </PageSection>
      ) : (
        <PageSection variant="plain">
          <PageState
            state="empty"
            surface="inherit"
            eyebrow={candidatePageCopy.empty}
            title={candidatePageText.learning.emptyTitle}
            description={candidatePageText.learning.emptyDescription}
          />
        </PageSection>
      )}
    </PageShell>
  );
}
