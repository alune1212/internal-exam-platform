import { Link, useLocation } from "react-router-dom";

import { cn } from "@/lib/utils";

export type ExamContextDestinationId =
  | "workspace"
  | "configuration"
  | "roster"
  | "invitations"
  | "results"
  | "review";

export type ExamContextDestination = {
  id: ExamContextDestinationId;
  label: string;
  to: string;
};

/**
 * Exam context links intentionally point at existing pages. Anchors are used
 * only for sections already present on the roster/configuration pages.
 */
// Exported for route-coverage tests; keep the component and its typed model co-located.
// eslint-disable-next-line react-refresh/only-export-components
export function getExamContextDestinations(examId: string): readonly ExamContextDestination[] {
  const encodedExamId = encodeURIComponent(examId);

  return [
    { id: "workspace", label: "考试工作台", to: `/admin/exams/${examId}` },
    { id: "configuration", label: "考试编排", to: `/admin/exams/${examId}/edit` },
    { id: "roster", label: "名单与授权", to: `/admin/exams/${examId}/candidates` },
    {
      id: "invitations",
      label: "邀请投递",
      to: `/admin/exams/${examId}/candidates#invitation-actions`,
    },
    { id: "results", label: "成绩册", to: `/admin/reports/scores?exam_id=${encodedExamId}` },
    { id: "review", label: "错题回看", to: `/admin/reports/wrong?exam_id=${encodedExamId}` },
  ];
}

function isDestinationActive(
  destination: ExamContextDestination,
  pathname: string,
  hash: string,
  examId: string,
) {
  switch (destination.id) {
    case "workspace":
      return pathname === `/admin/exams/${examId}`;
    case "configuration":
      return pathname === `/admin/exams/${examId}/edit`;
    case "roster":
      return pathname === `/admin/exams/${examId}/candidates` && hash !== "#invitation-actions";
    case "invitations":
      return pathname === `/admin/exams/${examId}/candidates` && hash === "#invitation-actions";
    case "results":
      return pathname === "/admin/reports/scores";
    case "review":
      return pathname === "/admin/reports/wrong";
  }
}

export interface ExamContextNavProps {
  examId: string;
  examTitle?: string | null;
}

export function ExamContextNav({ examId, examTitle }: ExamContextNavProps) {
  const { hash, pathname } = useLocation();
  const destinations = getExamContextDestinations(examId);
  const identity = examTitle?.trim() || `考试 #${examId}`;

  return (
    <section
      data-testid="exam-context-nav"
      aria-labelledby="exam-context-nav-title"
      className="flex flex-col gap-3 rounded-md border border-hairline bg-surface-card p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p
          id="exam-context-nav-title"
          className="text-caption font-semibold uppercase tracking-[0.14em] text-muted"
        >
          当前考试
        </p>
        <p className="text-body-sm font-medium text-ink" data-testid="exam-context-identity">
          {identity}
        </p>
      </div>
      <nav aria-label="考试上下文导航">
        <ul className="flex flex-wrap gap-2">
          {destinations.map((destination) => {
            const active = isDestinationActive(destination, pathname, hash, examId);

            return (
              <li key={destination.id}>
                <Link
                  to={destination.to}
                  aria-current={active ? "page" : undefined}
                  data-active={active ? "true" : "false"}
                  className={cn(
                    "inline-flex h-10 items-center whitespace-nowrap rounded-md border px-3 text-body-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                    active
                      ? "border-ink bg-ink text-canvas"
                      : "border-hairline bg-canvas text-muted hover:border-ink hover:text-ink",
                  )}
                >
                  {destination.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </section>
  );
}
