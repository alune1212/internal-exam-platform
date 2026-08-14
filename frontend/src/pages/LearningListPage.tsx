import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, Film } from "lucide-react";
import { Link, useOutletContext } from "react-router-dom";

import { getLearningVideos } from "@/api/learning";
import { StatusPill } from "@/components/editorial/StatusPill";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
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
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-2">
          <p className="font-body text-caption font-medium tracking-[0.12em] text-muted">
            学习视频
          </p>
          <h2 className="min-w-0 break-words font-display text-display-sm font-semibold text-ink lg:text-display-md">
            {video.title}
          </h2>
        </div>
        <StatusPill variant={completed ? "success" : "warning"}>
          {completionLabel(video)}
        </StatusPill>
      </div>
      {video.description ? <p className="text-body text-muted">{video.description}</p> : null}
      <dl className="grid grid-cols-2 gap-3 border-y border-hairline-soft py-3 text-caption text-muted">
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Clock className="size-3" /> 时长
          </dt>
          <dd className="font-mono text-body text-ink">{formatDuration(video.duration_seconds)}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Film className="size-3" /> 完成度
          </dt>
          <dd className="font-mono text-body text-ink">{video.progress.completion_percent}%</dd>
        </div>
      </dl>
      <div className="h-2 overflow-hidden rounded-pill bg-surface-card">
        <div
          className="h-full rounded-pill bg-success"
          style={{ width: `${Math.min(100, video.progress.completion_percent)}%` }}
        />
      </div>
      <Button asChild size="sm" className="self-start">
        <Link to={`/learning/${video.id}`}>
          {completed ? "回看视频" : "继续学习"}
          <ArrowUpRight data-icon="inline-end" />
        </Link>
      </Button>
    </article>
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
    <PageShell density="calm" stagger data-testid="candidate-learning-list-shell">
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
