import { ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getQuestionTypeLabel, type QuestionNavItem } from "@/lib/questionNavigation";
import { cn } from "@/lib/utils";

const QUESTION_TYPE_ORDER = ["single", "multiple", "judge"];

export type ExamNavigatorProps = {
  items: QuestionNavItem[];
  activeId?: number | null;
  className?: string;
  desktopLayout?: boolean;
  sheetLayout?: boolean;
  onJump: (targetId: string, itemId: number) => void;
  onSubmit?: () => void;
  submitLabel?: string;
  submitDisabled?: boolean;
};

function groupNavItems(items: QuestionNavItem[]) {
  const sortedTypes = Array.from(new Set(items.map((item) => item.type))).sort((a, b) => {
    const indexA = QUESTION_TYPE_ORDER.indexOf(a);
    const indexB = QUESTION_TYPE_ORDER.indexOf(b);
    if (indexA === -1 && indexB === -1) {
      return a.localeCompare(b);
    }
    if (indexA === -1) {
      return 1;
    }
    if (indexB === -1) {
      return -1;
    }
    return indexA - indexB;
  });

  return sortedTypes.map((type) => ({
    type,
    items: items.filter((item) => item.type === type),
  }));
}

export function ExamNavigator({
  items,
  activeId,
  className,
  desktopLayout = true,
  sheetLayout = false,
  onJump,
  onSubmit,
  submitLabel = "提前交卷",
  submitDisabled = false,
}: ExamNavigatorProps) {
  const groups = groupNavItems(items);
  const hasSubmittedResult = items.some((item) => item.submittedResult);

  if (!items.length) {
    return null;
  }

  return (
    <section
      aria-label="题号导航"
      className={cn(
        "flex flex-col gap-4",
        desktopLayout &&
          "max-h-[calc(100vh-7rem)] rounded-lg border border-hairline bg-surface-card p-5 shadow-card",
        sheetLayout && "bg-canvas p-5",
        className,
      )}
    >
      <header className="flex items-baseline justify-between border-b border-hairline pb-3">
        <h3 className="font-display text-display-sm font-semibold text-ink">题号导航</h3>
        <span className="text-caption uppercase tracking-[0.16em] text-muted">
          共 {items.length} 题
        </span>
      </header>

      <div
        data-testid="exam-navigator-list"
        className="flex min-h-0 flex-col gap-4 overflow-y-auto overscroll-contain p-1"
      >
        {groups.map((group) => (
          <div key={group.type} className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <span className="font-display text-caption uppercase italic tracking-[0.18em] text-muted">
                CHAPTER&nbsp;{String(group.items[0]?.displayIndex ?? "").padStart(2, "0")}
                &nbsp;·&nbsp;{getQuestionTypeLabel(group.type)}
              </span>
              <span className="text-body-sm text-muted">{group.items.length} 题</span>
            </div>
            <ul className="grid grid-cols-5 gap-2">
              {group.items.map((item) => (
                <li key={item.id} className="contents">
                  <button
                    type="button"
                    onClick={() => onJump(item.targetId, item.id)}
                    aria-label={`跳转到第 ${item.displayIndex} 题`}
                    aria-current={activeId === item.id ? "true" : undefined}
                    className={cn(
                      "flex h-10 items-center justify-center rounded-md border font-mono text-base tabular-nums transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                      !item.answered && "border-hairline bg-canvas text-ink",
                      item.answered && !item.submittedResult && "border-ink bg-ink text-canvas",
                      item.submittedResult === "correct" && "border-success bg-success text-canvas",
                      item.submittedResult === "wrong" && "border-error bg-error text-canvas",
                      activeId === item.id && "outline outline-2 outline-offset-[-3px] outline-ink",
                    )}
                  >
                    {item.displayIndex}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {hasSubmittedResult ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-hairline pt-3 text-body-sm text-muted">
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full border border-hairline" />
            未作答
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-ink" />
            已作答
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-success" />
            正确
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-error" />
            错误
          </span>
        </div>
      ) : null}

      {onSubmit ? (
        <Button type="button" onClick={onSubmit} disabled={submitDisabled} className="w-full">
          {submitLabel}
          <ChevronRight data-icon="inline-end" />
        </Button>
      ) : null}
    </section>
  );
}
