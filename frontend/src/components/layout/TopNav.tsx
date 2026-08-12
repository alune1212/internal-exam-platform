import { ArrowLeft, LogIn, LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { NamePlate } from "@/components/editorial/NamePlate";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { candidateActionCopy } from "@/lib/pageCopy";
import { useScrolled } from "@/lib/useScrolled";
import { MD, useMediaQuery } from "@/lib/use-media-query";
import { candidateDisplayName, type Candidate } from "@/types/candidate";

type NavItem = {
  to: string;
  label: string;
  mark: string;
  end?: boolean;
  activePattern?: RegExp;
};

type TopNavProps = {
  candidate: Candidate | null;
  onLogout: () => void;
};

function NavLinkItem({ item, pathname }: { item: NavItem; pathname: string }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn(
          "relative inline-flex h-10 items-center gap-1.5 px-1 text-body-sm font-medium transition-colors",
          isActive || item.activePattern?.test(pathname) ? "text-ink" : "text-muted hover:text-ink",
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            aria-hidden="true"
            className={cn(
              "inline-block w-7 text-right font-mono text-[11px] uppercase tracking-[0.16em] transition-colors",
              isActive || item.activePattern?.test(pathname) ? "text-ink" : "text-muted",
            )}
          >
            {item.mark}
          </span>
          <span>{item.label}</span>
          <span
            aria-hidden="true"
            className={cn(
              "absolute inset-x-0 -bottom-px h-px transition-opacity",
              isActive || item.activePattern?.test(pathname) ? "bg-ink opacity-100" : "opacity-0",
            )}
          />
        </>
      )}
    </NavLink>
  );
}

export function TopNav({ candidate, onLogout }: TopNavProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrolled = useScrolled();
  const isDesktop = useMediaQuery(MD.lg);
  const location = useLocation();
  const isInExam = /^\/exams\/\d+\/taking/.test(location.pathname);
  const navItems: NavItem[] = [
    { to: "/learning", label: "学习", mark: "I.", activePattern: /^\/learning(?:\/|$)/ },
    { to: "/practice", label: "练习", mark: "II." },
    { to: "/exams", label: "考试", mark: "III.", end: true },
  ];

  return (
    <header
      data-scrolled={scrolled}
      className="sticky top-0 z-40 h-16 border-b border-hairline-soft bg-canvas"
    >
      <div className="mx-auto grid h-full max-w-6xl grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 md:px-8">
        <Link
          to="/exams"
          aria-label="返回考试列表首页"
          className="justify-self-start rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
        >
          <Wordmark size="sm" subtitle="internal exam platform" />
        </Link>

        {isDesktop ? (
          <nav className="flex items-center gap-8 justify-self-center">
            {navItems.map((item) => (
              <NavLinkItem key={item.mark} item={item} pathname={location.pathname} />
            ))}
          </nav>
        ) : null}

        <div className="flex items-center gap-2 justify-self-end">
          {isDesktop ? (
            candidate ? (
              <>
                <Link to="/profile" aria-label="打开账号资料">
                  <NamePlate name={candidateDisplayName(candidate)} subtitle="用户" />
                </Link>
                {isInExam ? (
                  <Button asChild variant="outline" size="sm">
                    <Link to="/exams" aria-label={candidateActionCopy.returnExamList}>
                      <ArrowLeft data-icon="inline-start" aria-hidden="true" />
                      {candidateActionCopy.returnExamList}
                    </Link>
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={onLogout}
                  aria-label="退出登录"
                  className="text-muted hover:text-ink"
                >
                  <LogOut aria-hidden="true" />
                </Button>
              </>
            ) : (
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">
                  <LogIn data-icon="inline-start" aria-hidden="true" />
                  登录
                </Link>
              </Button>
            )
          ) : (
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
                  <SheetDescription className="sr-only">用户导航菜单</SheetDescription>
                </SheetHeader>
                <nav className="flex flex-col gap-1 px-4 pb-6">
                  {navItems.map((item) => (
                    <NavLink
                      key={item.mark}
                      to={item.to}
                      end={item.end}
                      onClick={() => setMobileOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          "flex h-12 items-center rounded-md px-3 text-body font-medium transition-colors",
                          isActive || item.activePattern?.test(location.pathname)
                            ? "bg-surface-card text-ink"
                            : "text-body hover:bg-surface-card hover:text-ink",
                        )
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                  {candidate ? (
                    <div className="mt-4 flex flex-col gap-3 border-t border-hairline-soft pt-4">
                      <Link
                        to="/profile"
                        onClick={() => setMobileOpen(false)}
                        aria-label="打开账号资料"
                      >
                        <NamePlate name={candidateDisplayName(candidate)} subtitle="用户" />
                      </Link>
                      {isInExam ? (
                        <Button asChild variant="outline">
                          <Link to="/exams" onClick={() => setMobileOpen(false)}>
                            <ArrowLeft data-icon="inline-start" aria-hidden="true" />
                            {candidateActionCopy.returnExamList}
                          </Link>
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setMobileOpen(false);
                          onLogout();
                        }}
                      >
                        <LogOut data-icon="inline-start" aria-hidden="true" />
                        退出登录
                      </Button>
                    </div>
                  ) : (
                    <Button asChild className="mt-4">
                      <Link to="/login" onClick={() => setMobileOpen(false)}>
                        <LogIn data-icon="inline-start" aria-hidden="true" />
                        登录
                      </Link>
                    </Button>
                  )}
                </nav>
              </SheetContent>
            </Sheet>
          )}
        </div>
      </div>
    </header>
  );
}
