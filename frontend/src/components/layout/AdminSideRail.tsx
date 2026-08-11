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
import { cn } from "@/lib/utils";
import { useScrolled } from "@/lib/useScrolled";
import { MD, useMediaQuery } from "@/lib/use-media-query";

type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  activePattern?: RegExp;
};

const navItems: NavItem[] = [
  { to: "/admin/dashboard", label: "仪表盘", end: true },
  { to: "/admin/exams", label: "考试", activePattern: /^\/admin\/exams(?:\/|$)/ },
  { to: "/admin/questions", label: "题库", end: true },
  { to: "/admin/questions/import", label: "题库导入", end: true },
  { to: "/admin/learning", label: "学习", activePattern: /^\/admin\/learning(?:\/|$)/ },
  { to: "/admin/reports/scores", label: "报表", activePattern: /^\/admin\/reports(?:\/|$)/ },
  { to: "/admin/operations", label: "运维", end: true },
];

function SidebarList({
  onNavigate,
  tone = "dark",
}: {
  onNavigate?: () => void;
  tone?: "dark" | "light";
}) {
  const { pathname } = useLocation();

  return (
    <nav className="flex flex-col gap-1">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) => {
            const active = isActive || Boolean(item.activePattern?.test(pathname));

            return cn(
              "flex h-12 items-center rounded-md px-3 text-body-sm font-medium transition-colors",
              tone === "dark"
                ? active
                  ? "bg-canvas text-ink"
                  : "text-footer-soft hover:bg-white/10 hover:text-canvas"
                : active
                  ? "bg-surface-card text-ink"
                  : "text-muted hover:bg-surface-card hover:text-ink",
            );
          }}
        >
          {item.label}
        </NavLink>
      ))}
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
      <aside className="sticky top-0 flex h-dvh w-60 shrink-0 flex-col overflow-hidden border-r border-footer-soft bg-footer px-5 py-6 text-footer-soft">
        <Link
          to="/admin/dashboard"
          aria-label="返回管理后台首页"
          className="mb-8 inline-flex rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-canvas focus-visible:ring-offset-2 focus-visible:ring-offset-footer"
        >
          <Wordmark size="sm" tone="dark" subtitle="admin" />
        </Link>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <SidebarList />
        </div>
        <div className="mt-4 border-t border-footer-soft pt-4">
          <LogoutButton onLogout={onLogout} />
        </div>
      </aside>
    );
  }

  return (
    <div
      data-scrolled={scrolled}
      className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-hairline-soft bg-canvas px-4"
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
        <SheetContent side="bottom" className="rounded-t-lg">
          <SheetHeader>
            <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
            <SheetDescription className="sr-only">管理后台导航菜单</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
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
