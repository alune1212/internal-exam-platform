import { BookOpenCheck, ClipboardList, LogIn, Trophy } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

const navItems = [
  { to: "/login", label: "进入考试", icon: LogIn },
  { to: "/practice", label: "练习", icon: BookOpenCheck },
  { to: "/exams", label: "考试", icon: ClipboardList },
  { to: "/exams/1/ranking", label: "排名", icon: Trophy },
];

export function CandidateLayout() {
  return (
    <div className="min-h-screen">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-semibold">内部临时考试平台</h1>
            <p className="text-sm text-muted-foreground">练习、考试、成绩查询</p>
          </div>
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground",
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
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
