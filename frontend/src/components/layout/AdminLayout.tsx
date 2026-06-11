import { BarChart3, FileUp, Gauge, ListChecks, UsersRound } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

const navItems = [
  { to: "/admin/dashboard", label: "仪表盘", icon: Gauge },
  { to: "/admin/questions", label: "题库", icon: ListChecks },
  { to: "/admin/questions/import", label: "导入", icon: FileUp },
  { to: "/admin/exams", label: "考试", icon: UsersRound },
  { to: "/admin/reports/scores", label: "报表", icon: BarChart3 },
];

export function AdminLayout() {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="border-b bg-card md:min-h-screen md:border-b-0 md:border-r">
        <div className="flex flex-col gap-5 p-4">
          <div>
            <h1 className="text-lg font-semibold">考试管理</h1>
            <p className="text-sm text-muted-foreground">题库、人员、成绩</p>
          </div>
          <nav className="flex flex-wrap gap-2 md:flex-col">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isActive && "bg-accent text-accent-foreground",
                  )
                }
              >
                <item.icon data-icon="inline-start" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>
      <main className="px-4 py-6 md:px-8">
        <Outlet />
      </main>
    </div>
  );
}
