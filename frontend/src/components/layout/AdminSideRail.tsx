import { LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { Wordmark } from "@/components/editorial/Wordmark";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { isNavItemActive } from "@/lib/navigation";
import { cn } from "@/lib/utils";
import { useScrolled } from "@/lib/useScrolled";
import { MD, useMediaQuery } from "@/lib/use-media-query";

export type AdminNavigationItem = {
  id: string;
  to: string;
  label: string;
  end?: boolean;
  activePattern?: RegExp;
};

export type AdminNavigationGroup = {
  id: string;
  label: "概览" | "内容" | "考试" | "复盘" | "系统";
  items: readonly AdminNavigationItem[];
};

/**
 * The single source for primary admin destinations. Keep this model ordered:
 * the same data renders in the desktop rail and the mobile sheet.
 */
// eslint-disable-next-line react-refresh/only-export-components
export const ADMIN_NAVIGATION_GROUPS: readonly AdminNavigationGroup[] = [
  {
    id: "overview",
    label: "概览",
    items: [{ id: "dashboard", to: "/admin/dashboard", label: "仪表盘", end: true }],
  },
  {
    id: "content",
    label: "内容",
    items: [
      { id: "questions", to: "/admin/questions", label: "题库", end: true },
      { id: "question-import", to: "/admin/questions/import", label: "题库导入", end: true },
      {
        id: "learning",
        to: "/admin/learning",
        label: "学习",
        activePattern: /^\/admin\/learning(?:\/|$)/,
      },
    ],
  },
  {
    id: "exams",
    label: "考试",
    items: [
      {
        id: "exams",
        to: "/admin/exams",
        label: "考试编排",
        activePattern: /^\/admin\/exams(?:\/|$)/,
      },
    ],
  },
  {
    id: "review",
    label: "复盘",
    items: [
      {
        id: "reports",
        to: "/admin/reports/scores",
        label: "报表",
        activePattern: /^\/admin\/reports(?:\/|$)/,
      },
    ],
  },
  {
    id: "system",
    label: "系统",
    items: [
      {
        id: "accounts",
        to: "/admin/accounts",
        label: "用户账户",
        activePattern: /^\/admin\/accounts(?:\/|$)/,
      },
      { id: "operations", to: "/admin/operations", label: "运维", end: true },
    ],
  },
];

function itemIsActive(item: AdminNavigationItem, pathname: string) {
  return isNavItemActive(item, pathname);
}

function SidebarList({
  onNavigate,
  tone = "dark",
}: {
  onNavigate?: () => void;
  tone?: "dark" | "light";
}) {
  const { pathname } = useLocation();

  return (
    <nav aria-label="管理后台导航" data-navigation-tone={tone} className="flex flex-col gap-1">
      {ADMIN_NAVIGATION_GROUPS.map((group, groupIndex) => {
        const itemsWithActive = group.items.map((item) => ({
          item,
          active: itemIsActive(item, pathname),
        }));
        const groupIsActive = itemsWithActive.some(({ active }) => active);
        const showGroupLabel = group.items.length > 1;
        const previousGroupShowsLabel =
          groupIndex > 0 && ADMIN_NAVIGATION_GROUPS[groupIndex - 1].items.length > 1;
        const startsVisualBlock = groupIndex > 0 && (showGroupLabel || previousGroupShowsLabel);
        const groupTitleId = `admin-nav-group-${group.id}`;

        return (
          <section
            key={group.id}
            aria-labelledby={groupTitleId}
            data-nav-group-id={group.id}
            data-active-group={groupIsActive ? "true" : "false"}
            data-visible-group-label={showGroupLabel ? "true" : "false"}
            data-visual-break-before={startsVisualBlock ? "true" : "false"}
            className={cn("flex flex-col gap-2", startsVisualBlock && "mt-5")}
          >
            <p
              id={groupTitleId}
              className={
                showGroupLabel
                  ? cn(
                      "flex items-center gap-2 px-3 text-caption font-semibold uppercase tracking-caption",
                      tone === "dark" ? "text-footer-soft" : "text-muted",
                    )
                  : "sr-only"
              }
            >
              <span className="shrink-0">
                {group.label}
                {groupIsActive ? <span className="sr-only"> · 当前分组</span> : null}
              </span>
              {showGroupLabel ? (
                <span
                  aria-hidden="true"
                  data-nav-group-divider
                  className={cn(
                    "h-px min-w-0 flex-1",
                    tone === "dark" ? "bg-footer-soft opacity-40" : "bg-hairline",
                  )}
                />
              ) : null}
            </p>
            <div className="flex flex-col gap-1">
              {itemsWithActive.map(({ item, active }) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  data-active={active ? "true" : "false"}
                  data-nav-item-id={item.id}
                  className={({ isActive }) => {
                    const resolvedActive = isActive || active;

                    return cn(
                      "flex min-h-12 w-full min-w-0 items-center break-words rounded-md px-3 py-3 text-left text-body-sm font-medium leading-tight transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
                      tone === "dark"
                        ? cn(
                            "focus-visible:ring-canvas focus-visible:ring-offset-footer",
                            resolvedActive ? "bg-canvas text-ink" : "text-canvas hover:bg-white/10",
                          )
                        : cn(
                            "focus-visible:ring-ink focus-visible:ring-offset-canvas",
                            resolvedActive
                              ? "bg-surface-card text-ink"
                              : "text-body hover:bg-surface-card hover:text-ink",
                          ),
                    );
                  }}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </section>
        );
      })}
    </nav>
  );
}

function LogoutButton({
  onLogout,
  tone = "dark",
}: {
  onLogout: () => void;
  tone?: "dark" | "light";
}) {
  return (
    <button
      type="button"
      onClick={onLogout}
      className={cn(
        "flex h-12 w-full items-center gap-2 rounded-md px-3 text-body-sm font-medium transition-colors",
        tone === "dark"
          ? "text-footer-soft hover:bg-white/10 hover:text-canvas"
          : "text-muted hover:bg-surface-card hover:text-ink",
      )}
    >
      <LogOut className="size-4" aria-hidden="true" />
      退出登录
    </button>
  );
}

export function AdminSideRail({ onLogout }: { onLogout: () => void }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrolled = useScrolled();
  const isDesktop = useMediaQuery(MD.lg);

  if (isDesktop) {
    return (
      <aside
        data-testid="admin-desktop-rail"
        data-navigation-family="admin"
        className="sticky top-0 flex h-dvh w-60 shrink-0 flex-col overflow-hidden border-r border-footer-soft bg-footer px-5 py-6 text-footer-soft"
      >
        <Link
          to="/admin/dashboard"
          aria-label="返回管理后台首页"
          className="mb-8 inline-flex rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-canvas focus-visible:ring-offset-2 focus-visible:ring-offset-footer"
        >
          <Wordmark size="sm" tone="dark" subtitle="admin" />
        </Link>
        <div
          data-testid="admin-desktop-navigation-scroll"
          className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
        >
          <SidebarList />
        </div>
        <div className="mt-4 shrink-0 border-t border-footer-soft pt-4">
          <LogoutButton onLogout={onLogout} />
        </div>
      </aside>
    );
  }

  return (
    <div
      data-scrolled={scrolled}
      data-testid="admin-mobile-header"
      data-navigation-family="admin"
      className="sticky top-0 z-overlay flex min-h-16 items-center justify-between border-b border-hairline-soft bg-canvas px-page-inline"
    >
      <Link
        to="/admin/dashboard"
        aria-label="返回管理后台首页"
        className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
      >
        <Wordmark size="sm" subtitle="admin" />
      </Link>
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <button
            type="button"
            className="inline-flex size-10 items-center justify-center rounded-pill text-ink transition-colors hover:bg-surface-card"
            aria-label="打开菜单"
          >
            <Menu aria-hidden="true" />
          </button>
        </SheetTrigger>
        <SheetContent
          side="bottom"
          data-testid="admin-mobile-navigation"
          className="max-h-[calc(100dvh-1rem)] overflow-y-auto overscroll-contain rounded-t-lg pb-[calc(1.5rem+env(safe-area-inset-bottom))]"
        >
          <SheetHeader>
            <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
            <SheetDescription className="sr-only">管理后台导航菜单</SheetDescription>
          </SheetHeader>
          <div className="min-h-0 px-4 pb-6">
            <SidebarList tone="light" onNavigate={() => setMobileOpen(false)} />
            <div className="mt-4 border-t border-hairline pt-3">
              <LogoutButton
                tone="light"
                onLogout={() => {
                  setMobileOpen(false);
                  onLogout();
                }}
              />
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
