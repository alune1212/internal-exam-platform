import { Badge } from "@/components/ui/badge";
import { getQuestionTypeLabel, type QuestionNavItem } from "@/lib/questionNavigation";
import { cn } from "@/lib/utils";

export type QuestionNavigatorProps = {
  items: QuestionNavItem[];
  activeId?: number | null;
  className?: string;
  onJump: (targetId: string, itemId: number) => void;
};

const QUESTION_TYPE_ORDER = ["single", "multiple", "judge"];

export function QuestionNavigator({ items, activeId, className, onJump }: QuestionNavigatorProps) {
  const groups = groupNavItems(items);
  const hasSubmittedResult = items.some((item) => item.submittedResult);

  if (!items.length) {
    return null;
  }

  return (
    <section
      className={cn(
        "flex h-[70vh] min-h-0 flex-col overflow-hidden rounded-md border bg-card lg:h-full",
        className,
      )}
    >
      <div className="shrink-0 border-b p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">题号导航</h3>
          <span className="text-xs text-muted-foreground">共 {items.length} 题</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full border" />
            未作答
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-primary" />
            已作答
          </span>
          {hasSubmittedResult ? (
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
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden">
        <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto overscroll-contain p-4 [scrollbar-color:var(--hairline)_transparent] [scrollbar-gutter:stable] [scrollbar-width:thin] [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:w-2">
          {groups.map((group) => (
            <div key={group.type} className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{getQuestionTypeLabel(group.type)}</Badge>
                <span className="text-xs text-muted-foreground">{group.items.length} 题</span>
              </div>
              <div className="grid grid-cols-7 gap-2 sm:grid-cols-10 lg:grid-cols-5">
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={cn(
                      "h-8 min-w-0 rounded-md border px-2 text-xs font-medium transition-colors",
                      "hover:border-primary hover:text-primary",
                      item.answered && "border-primary bg-surface-card text-primary",
                      item.submittedResult === "correct" &&
                        "border-emerald-600 bg-emerald-50 text-emerald-700",
                      item.submittedResult === "wrong" &&
                        "border-destructive bg-surface-card text-destructive",
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
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-card to-transparent" />
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
