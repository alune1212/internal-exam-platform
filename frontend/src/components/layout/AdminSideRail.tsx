import { Menu } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

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
import { useMediaQuery } from "@/lib/use-media-query";

type NavItem = {
  to: string;
  label: string;
};

const navItems: NavItem[] = [
  { to: "/admin/dashboard", label: "仪表盘" },
  { to: "/admin/questions", label: "题库" },
  { to: "/admin/questions/import", label: "导入" },
  { to: "/admin/exams", label: "考试" },
  { to: "/admin/reports/scores", label: "报表" },
];

function SidebarList({
  onNavigate,
  tone = "dark",
}: {
  onNavigate?: () => void;
  tone?: "dark" | "light";
}) {
  return (
    <nav className="flex flex-col gap-1">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex h-11 items-center rounded-md px-3 text-body-sm font-medium transition-colors",
              tone === "dark"
                ? isActive
                  ? "bg-white text-ink"
                  : "text-footer-soft hover:bg-white/10 hover:text-white"
                : isActive
                  ? "bg-surface-card text-ink"
                  : "text-body hover:bg-surface-card hover:text-ink",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AdminSideRail() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  if (isDesktop) {
    return (
      <aside className="w-60 shrink-0 border-r border-black bg-footer px-5 py-6 text-footer-soft">
        <Link
          to="/admin/dashboard"
          aria-label="返回管理后台首页"
          className="mb-8 inline-flex rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-canvas focus-visible:ring-offset-2 focus-visible:ring-offset-footer"
        >
          <Wordmark size="sm" tone="dark" subtitle="admin" />
        </Link>
        <SidebarList />
      </aside>
    );
  }

  return (
    <div className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-hairline-soft bg-canvas px-4">
      <Link
        to="/admin/dashboard"
        aria-label="返回管理后台首页"
        className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
      >
        <Wordmark size="sm" subtitle="admin" />
      </Link>
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger
          className="inline-flex size-10 items-center justify-center rounded-pill text-ink transition-colors hover:bg-surface-card"
          aria-label="打开菜单"
        >
          <Menu aria-hidden="true" />
        </SheetTrigger>
        <SheetContent side="bottom" className="rounded-t-lg">
          <SheetHeader>
            <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
            <SheetDescription className="sr-only">管理后台导航菜单</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-6">
            <SidebarList tone="light" onNavigate={() => setMobileOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
