import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function navLinkClassName({ isActive }: { isActive: boolean }, size: "sm" | "md" = "md") {
  return cn(
    "inline-flex items-center gap-2 rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground",
    size === "sm" ? "h-9" : "h-10",
    isActive && "bg-accent text-accent-foreground",
  );
}
