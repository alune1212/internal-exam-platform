import { BookOpenCheck, ClipboardList, LogIn, LogOut, Trophy, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  clearCurrentCandidate,
  getCurrentCandidate,
  setCurrentCandidate,
} from "@/lib/candidateSession";
import { navLinkClassName } from "@/lib/utils";
import type { Candidate } from "@/types/candidate";

const navItems = [
  { to: "/practice", label: "练习", icon: BookOpenCheck },
  { to: "/exams", label: "考试", icon: ClipboardList },
  { to: "/exams/1/ranking", label: "排名", icon: Trophy },
];

export type CandidateSessionContext = {
  candidate: Candidate | null;
  loginCandidate: (candidate: Candidate) => void;
  logoutCandidate: () => void;
};

export function CandidateLayout() {
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState<Candidate | null>(() => getCurrentCandidate());

  function loginCandidate(nextCandidate: Candidate) {
    setCurrentCandidate(nextCandidate);
    setCandidate(nextCandidate);
  }

  function logoutCandidate() {
    clearCurrentCandidate();
    setCandidate(null);
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-semibold">内部临时考试平台</h1>
            <p className="text-sm text-muted-foreground">练习、考试、成绩查询</p>
          </div>
          <div className="flex flex-col gap-3 md:items-end">
            <nav className="flex flex-wrap gap-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={(props) => navLinkClassName(props, "sm")}
                >
                  <item.icon data-icon="inline-start" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            {candidate ? (
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-sm">
                  <UserRound className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="font-medium">当前：{candidate.name}</p>
                    {candidate.employee_no || candidate.department ? (
                      <p className="text-xs text-muted-foreground">
                        {[candidate.employee_no, candidate.department].filter(Boolean).join(" · ")}
                      </p>
                    ) : null}
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={logoutCandidate}>
                  <LogOut data-icon="inline-start" />
                  退出登录
                </Button>
              </div>
            ) : (
              <Button asChild size="sm">
                <Link to="/login">
                  <LogIn data-icon="inline-start" />
                  进入考试
                </Link>
              </Button>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet
          context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
        />
      </main>
    </div>
  );
}
