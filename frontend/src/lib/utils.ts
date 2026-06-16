import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "display-2xl",
            "display-xl",
            "display-lg",
            "display-md",
            "display-sm",
            "body-lg",
            "body",
            "body-sm",
            "caption",
          ],
        },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 将逗号分隔的答案字符串拆分为标签数组。 */
export function splitAnswer(answer: string | undefined): string[] {
  return (answer ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/** 多选题切换选项：返回新的逗号分隔答案字符串。 */
export function toggleMultipleAnswer(
  current: string | undefined,
  label: string,
  checked: boolean,
): string {
  const selected = new Set(splitAnswer(current));
  if (checked) {
    selected.add(label);
  } else {
    selected.delete(label);
  }
  return Array.from(selected).sort().join(",");
}

export function navLinkClassName({ isActive }: { isActive: boolean }, size: "sm" | "md" = "md") {
  return cn(
    `
      inline-flex items-center gap-2 rounded-md px-3 text-sm font-medium
      text-muted-foreground
      hover:bg-accent hover:text-accent-foreground
    `,
    size === "sm" ? "h-9" : "h-10",
    isActive && "bg-accent text-accent-foreground",
  );
}
