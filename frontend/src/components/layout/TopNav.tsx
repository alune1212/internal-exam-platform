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
  end?: boolean;
  activePattern?: RegExp;
};

/**
 * Candidate navigation is intentionally one ordered model for desktop and
 * mobile. Presentation can change between the two layouts, but destinations
 * and their active matching must not drift.
 */
// eslint-disable-next-line react-refresh/only-export-components
export const CANDIDATE_NAVIGATION_ITEMS: readonly NavItem[] = [
  { to: "/learning", label: "学习", activePattern: /^\/learning(?:\/|$)/ },
  { to: "/practice", label: "练习", activePattern: /^\/practice(?:\/|$)/ },
  { to: "/exams", label: "考试", end: true },
];

function candidateNavigationItemIsActive(item: NavItem, pathname: string) {
  if (item.activePattern?.test(pathname)) return true;
  return item.end ? pathname === item.to : pathname.startsWith(`${item.to}/`);
}

type TopNavProps = {
  candidate: Candidate | null;
  onLogout: () => void;
};

function NavLinkItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = candidateNavigationItemIsActive(item, pathname);

  return (
    <NavLink
      to={item.to}
      end={item.end}
      aria-current={active ? "page" : undefined}
      data-active={active ? "true" : "false"}
      className={({ isActive }) =>
        cn(
          "inline-flex min-h-10 items-center rounded-pill px-3 text-body-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
          isActive || active
            ? "bg-surface-card text-ink"
            : "text-muted hover:bg-surface-card hover:text-ink",
        )
      }
    >
      <span>{item.label}</span>
    </NavLink>
  );
}

function MobileNavLink({
  item,
  pathname,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  onNavigate: () => void;
}) {
  const active = candidateNavigationItemIsActive(item, pathname);

  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      data-active={active ? "true" : "false"}
      className={({ isActive }) =>
        cn(
          "flex min-h-12 items-center rounded-md px-3 text-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
          isActive || active
            ? "bg-ink text-canvas"
            : "text-muted hover:bg-surface-card hover:text-ink",
        )
      }
    >
      {item.label}
    </NavLink>
  );
}

export function TopNav({ candidate, onLogout }: TopNavProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrolled = useScrolled();
  const isDesktop = useMediaQuery(MD.lg);
  const location = useLocation();
  const isInExam = /^\/exams\/\d+\/taking/.test(location.pathname);

  return (
    <header
      data-scrolled={scrolled}
      data-navigation-family="candidate"
      className="sticky top-0 z-overlay border-b border-hairline-soft bg-canvas"
    >
      <div className="mx-auto flex min-h-16 w-full min-w-0 items-center gap-4 px-page-inline lg:px-page-inline-lg">
        <Link
          to="/exams"
          aria-label="返回考试列表首页"
          className="min-w-0 shrink rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
        >
          <Wordmark size="sm" subtitle="internal exam platform" />
        </Link>

        {isDesktop ? (
          <nav
            aria-label="候选人导航"
            data-testid="candidate-desktop-nav"
            className="flex min-w-0 flex-1 items-center justify-center gap-1"
          >
            {CANDIDATE_NAVIGATION_ITEMS.map((item) => (
              <NavLinkItem key={item.to} item={item} pathname={location.pathname} />
            ))}
          </nav>
        ) : null}

        <div className={cn("flex min-w-0 shrink-0 items-center gap-2", !isDesktop && "ml-auto")}>
          {isDesktop ? (
            candidate ? (
              <>
                <Link
                  to="/profile"
                  aria-label="打开账号资料"
                  className="min-w-0 max-w-48 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
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
              <SheetContent
                side="bottom"
                data-testid="candidate-mobile-navigation"
                className="max-h-[calc(100dvh-1rem)] overflow-y-auto overscroll-contain rounded-t-lg pb-[calc(1.5rem+env(safe-area-inset-bottom))]"
              >
                <SheetHeader>
                  <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
                  <SheetDescription className="sr-only">用户导航菜单</SheetDescription>
                </SheetHeader>
                <nav
                  aria-label="候选人导航"
                  data-testid="candidate-mobile-nav"
                  className="flex flex-col gap-1 px-4 pb-6"
                >
                  {CANDIDATE_NAVIGATION_ITEMS.map((item) => (
                    <MobileNavLink
                      key={item.to}
                      item={item}
                      pathname={location.pathname}
                      onNavigate={() => setMobileOpen(false)}
                    />
                  ))}
                  {candidate ? (
                    <div className="mt-4 flex flex-col gap-3 border-t border-hairline-soft pt-4">
                      <Link
                        to="/profile"
                        onClick={() => setMobileOpen(false)}
                        aria-label="打开账号资料"
                        className="min-w-0 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
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
