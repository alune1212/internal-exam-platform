import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type QuestionNavItem = {
  id: number;
  displayIndex: number;
  type: string;
  answered: boolean;
  submittedResult?: "correct" | "wrong";
  targetId: string;
};

export type QuestionNavigatorProps = {
  items: QuestionNavItem[];
  activeId?: number | null;
  className?: string;
  onJump: (targetId: string, itemId: number) => void;
};

type BuildQuestionNavItemsParams<TQuestion extends { id: number; question_type: string }> = {
  questions: TQuestion[];
  answers: Record<number, string>;
  getSubmittedResult?: (question: TQuestion) => QuestionNavItem["submittedResult"];
  getTargetId: (question: TQuestion) => string;
};

const QUESTION_TYPE_ORDER = ["single", "multiple", "judge"];

export function getQuestionTypeLabel(questionType: string): string {
  const labels: Record<string, string> = {
    single: "单选",
    multiple: "多选",
    judge: "判断",
  };
  return labels[questionType] ?? questionType;
}

export function buildQuestionNavItems<TQuestion extends { id: number; question_type: string }>({
  questions,
  answers,
  getSubmittedResult,
  getTargetId,
}: BuildQuestionNavItemsParams<TQuestion>): QuestionNavItem[] {
  return questions.map((question, index) => ({
    id: question.id,
    displayIndex: index + 1,
    type: question.question_type,
    answered: Boolean(answers[question.id]),
    submittedResult: getSubmittedResult?.(question),
    targetId: getTargetId(question),
  }));
}

export function QuestionNavigator({ items, activeId, className, onJump }: QuestionNavigatorProps) {
  const groups = groupNavItems(items);

  if (!items.length) {
    return null;
  }

  return (
    <section
      className={cn(
        "rounded-md border bg-card p-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto",
        className,
      )}
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">题号导航</h3>
        <span className="text-xs text-muted-foreground">共 {items.length} 题</span>
      </div>
      <div className="flex flex-col gap-4">
        {groups.map((group) => (
          <div key={group.type} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{getQuestionTypeLabel(group.type)}</Badge>
              <span className="text-xs text-muted-foreground">{group.items.length} 题</span>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1 lg:grid lg:grid-cols-5 lg:overflow-visible lg:pb-0">
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    "h-8 min-w-8 rounded-md border px-2 text-xs font-medium transition-colors",
                    "hover:border-primary hover:text-primary",
                    item.answered && "border-primary/60 bg-primary/10 text-primary",
                    item.submittedResult === "correct" &&
                      "border-emerald-600 bg-emerald-50 text-emerald-700",
                    item.submittedResult === "wrong" &&
                      "border-destructive bg-destructive/10 text-destructive",
                    activeId === item.id && "ring-2 ring-ring ring-offset-2",
                  )}
                  aria-label={`跳转到第 ${item.displayIndex} 题`}
                  aria-current={activeId === item.id ? "true" : undefined}
                  onClick={() => onJump(item.targetId, item.id)}
                >
                  {item.displayIndex}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="size-2 rounded-full border" />
          未作答
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="size-2 rounded-full bg-primary/60" />
          已作答
        </span>
        {items.some((item) => item.submittedResult) ? (
          <>
            <span className="inline-flex items-center gap-1">
              <span className="size-2 rounded-full bg-emerald-600" />
              正确
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="size-2 rounded-full bg-destructive" />
              错误
            </span>
          </>
        ) : null}
      </div>
    </section>
  );
}

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
