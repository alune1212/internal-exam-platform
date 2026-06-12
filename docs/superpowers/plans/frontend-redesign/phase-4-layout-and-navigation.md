# Phase 4: Layout & Navigation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the chrome (TopNav, AdminSideRail, Footer) and rewire both layouts to use the new Wordmark, NamePlate, and Sheet primitives, with mobile-responsive navigation.

**Architecture:** CandidateLayout uses TopNav + Outlet + Footer; admin uses AdminSideRail + Outlet. Both layouts detect viewport via a `useMediaQuery` hook (`(min-width: 1024px)`) to switch between desktop nav and mobile sheet. No state management library change — keep React `useState` for nav open/close. Active route detection reuses the existing `NavLink` `className={({ isActive }) => ...}` pattern.

**Tech Stack:** React 19, React Router 7, Tailwind 3.4, lucide-react, vitest + @testing-library/react + jsdom (new test deps), Radix UI Sheet primitive (from Phase 2), design tokens from Phase 1 (`index.css` + `tailwind.config.ts` exposes `bg-canvas`, `text-ink`, `bg-footer`, `text-footer-soft`, `rounded-pill`, `rounded-lg`, `font-display`, `font-mono`).

**Prerequisites (already done in earlier phases, do not re-implement):**
- Phase 1: design tokens live in `frontend/src/index.css` (CSS vars `--canvas`, `--ink`, `--footer`, `--footer-soft`, etc.) and are mapped to Tailwind utilities (`bg-canvas`, `text-ink`, `bg-footer`, `text-footer-soft`, `rounded-pill`, `rounded-lg`, `font-display`, `font-mono`, `text-caption`).
- Phase 2: `Button` is pill-shaped (`rounded-pill`); `Sheet` primitive exists at `frontend/src/components/ui/sheet.tsx` and exports `Sheet`, `SheetTrigger`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetClose`. It uses Radix Dialog under the hood.
- Phase 3: `Wordmark` and `NamePlate` exist at `frontend/src/components/editorial/Wordmark.tsx` and `frontend/src/components/editorial/NamePlate.tsx`. `Wordmark` props: `{ size?: "sm" | "md"; subtitle?: string; tone?: "light" | "dark"; href?: string }` (light = dark text on light bg, dark = white text on dark bg). `NamePlate` props: `{ candidate: { name: string; employee_no?: string; department?: string }; tone?: "light" | "dark" }`.
- `frontend/src/lib/candidateSession.ts` is unchanged from baseline.

**Files created in this phase:**
- `frontend/src/lib/use-media-query.ts` (new hook)
- `frontend/src/components/layout/Footer.tsx` (new)
- `frontend/src/components/layout/TopNav.tsx` (new)
- `frontend/src/components/layout/AdminSideRail.tsx` (new)
- `frontend/src/components/layout/CandidateLayout.tsx` (rewrite)
- `frontend/src/components/layout/AdminLayout.tsx` (rewrite)
- `frontend/src/components/layout/__tests__/use-media-query.test.ts` (new)
- `frontend/src/components/layout/__tests__/Footer.test.tsx` (new)
- `frontend/src/components/layout/__tests__/TopNav.test.tsx` (new)
- `frontend/src/components/layout/__tests__/AdminSideRail.test.tsx` (new)
- `frontend/vitest.config.ts` (new — required for test infra)
- `frontend/src/test/setup.ts` (new — vitest setup file)

**Files modified in this phase:**
- `frontend/package.json` (add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `@testing-library/user-event` as devDependencies)
- `frontend/tsconfig.json` (add `"types": ["vitest/globals", "@testing-library/jest-dom"]` and include `vitest.config.ts`)

---

## Task 1: Install and configure vitest + Testing Library

**Files:**
- `frontend/package.json` (modify)
- `frontend/vitest.config.ts` (new)
- `frontend/src/test/setup.ts` (new)
- `frontend/tsconfig.json` (modify)

**Why first:** No tests exist in the frontend today. The remaining 7 tasks rely on `vitest` and `@testing-library/react` to TDD the `useMediaQuery` hook and to smoke-test the layout components. Installing the toolchain up front lets us write tests as we go.

- [ ] Add the following to `frontend/package.json` `devDependencies` (use semver-compatible versions: `vitest@^2.1.0`, `@testing-library/react@^16.1.0`, `@testing-library/jest-dom@^6.6.0`, `@testing-library/user-event@^14.5.0`, `jsdom@^25.0.0`):

  ```json
  "vitest": "^2.1.0",
  "@testing-library/react": "^16.1.0",
  "@testing-library/jest-dom": "^6.6.0",
  "@testing-library/user-event": "^14.5.0",
  "jsdom": "^25.0.0"
  ```

  Also add a script entry to `scripts`:

  ```json
  "test": "vitest run",
  "test:watch": "vitest"
  ```

- [ ] Run `cd frontend && npm install` to install the new devDependencies.

- [ ] Create `frontend/vitest.config.ts` with this exact content:

  ```ts
  import path from "node:path";
  import react from "@vitejs/plugin-react";
  { vitest 用了 } from "vitest/config";

  export default defineConfig({
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  });
  ```

  The import statement is `import { defineConfig } from "vitest/config";` — write it that way (the placeholder above is just a comment marker, not literal text).

- [ ] Create `frontend/src/test/setup.ts`:

  ```ts
  import "@testing-library/jest-dom/vitest";
  ```

- [ ] Update `frontend/tsconfig.json` to add `vitest/globals` types. Edit the `compilerOptions` block to include:

  ```json
  "types": ["vitest/globals", "@testing-library/jest-dom"]
  ```

  Also add `frontend/vitest.config.ts` to `include` (or rely on the default `**/*.ts` globs — verify by reading the file). The `include` already covers `"src"`, so the new config file at the root is picked up by the editor but not by `tsc --noEmit`. That is acceptable.

- [ ] Run `cd frontend && npx tsc --noEmit` — must pass with no errors. If it complains about missing `@testing-library/jest-dom`, the package was not installed correctly; re-run `npm install`.

- [ ] Run `cd frontend && npm test` — vitest should start, find zero tests, and exit successfully (it reports "No test files found" which is fine for this task).

- [ ] Commit:

  ```bash
  git add frontend/package.json frontend/vitest.config.ts frontend/src/test/setup.ts frontend/tsconfig.json frontend/package-lock.json
  git commit -m "chore(test): 配置 vitest + testing-library 测试环境"
  ```

---

## Task 2: Build the `useMediaQuery` hook (TDD)

**Files:**
- `frontend/src/lib/use-media-query.ts` (new)
- `frontend/src/components/layout/__tests__/use-media-query.test.ts` (new)

**Why:** Both layouts need a viewport detector to swap between desktop nav and mobile sheet. Centralizing the logic in a hook keeps the layout components declarative and makes the behavior testable in isolation.

- [ ] Write the test first at `frontend/src/components/layout/__tests__/use-media-query.test.ts`:

  ```ts
  import { act, renderHook } from "@testing-library/react";

  import { useMediaQuery } from "@/lib/use-media-query";

  describe("useMediaQuery", () => {
    let listeners: Array<(event: MediaQueryListEvent) => void>;
    let matchesValue: boolean;

    beforeEach(() => {
      listeners = [];
      matchesValue = false;
      Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: (query: string) => ({
          get matches() {
            return matchesValue;
          },
          media: query,
          onchange: null,
          addEventListener: (_event: string, cb: (e: MediaQueryListEvent) => void) => {
            listeners.push(cb);
          },
          removeEventListener: (_event: string, cb: (e: MediaQueryListEvent) => void) => {
            listeners = listeners.filter((l) => l !== cb);
          },
          dispatchEvent: () => false,
        }),
      });
    });

    it("returns the initial matches value from matchMedia", () => {
      matchesValue = true;
      const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
      expect(result.current).toBe(true);
    });

    it("returns false initially when matchMedia reports no match", () => {
      matchesValue = false;
      const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
      expect(result.current).toBe(false);
    });

    it("updates when matchMedia emits a change event", () => {
      matchesValue = false;
      const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
      expect(result.current).toBe(false);

      act(() => {
        matchesValue = true;
        for (const listener of listeners) {
          listener({ matches: true, media: "(min-width: 1024px)" } as MediaQueryListEvent);
        }
      });
      expect(result.current).toBe(true);
    });

    it("removes the listener on unmount", () => {
      const { unmount } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
      expect(listeners.length).toBe(1);
      unmount();
      expect(listeners.length).toBe(0);
    });

    it("returns false during SSR (when window is undefined)", () => {
      const originalWindow = globalThis.window;
      // @ts-expect-error — simulate SSR
      delete (globalThis as { window?: Window }).window;
      const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
      expect(result.current).toBe(false);
      (globalThis as { window: Window }).window = originalWindow;
    });
  });
  ```

- [ ] Run `cd frontend && npm test -- use-media-query` — tests fail (no implementation).

- [ ] Create `frontend/src/lib/use-media-query.ts`:

  ```ts
  import { useEffect, useState } from "react";

  /**
   * Subscribe to a CSS media query and return whether it currently matches.
   *
   * SSR-safe: returns `false` when `window` is undefined.
   * Re-renders the consuming component when the viewport crosses the breakpoint.
   */
  export function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState<boolean>(() => {
      if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
        return false;
      }
      return window.matchMedia(query).matches;
    });

    useEffect(() => {
      if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
        return;
      }
      const mediaQueryList = window.matchMedia(query);
      const handleChange = (event: MediaQueryListEvent) => {
        setMatches(event.matches);
      };
      // Sync once on mount in case the initial value was computed under different window state
      setMatches(mediaQueryList.matches);
      mediaQueryList.addEventListener("change", handleChange);
      return () => {
        mediaQueryList.removeEventListener("change", handleChange);
      };
    }, [query]);

    return matches;
  }
  ```

- [ ] Run `cd frontend && npm test -- use-media-query` — all 5 tests pass.

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors.

- [ ] Commit:

  ```bash
  git add frontend/src/lib/use-media-query.ts frontend/src/components/layout/__tests__/use-media-query.test.ts
  git commit -m "feat(layout): 实现 useMediaQuery 视口检测 hook"
  ```

---

## Task 3: Build the `Footer` component (TDD)

**Files:**
- `frontend/src/components/layout/Footer.tsx` (new)
- `frontend/src/components/layout/__tests__/Footer.test.tsx` (new)

**Why first:** Footer is the simplest chrome piece (presentational, no state, no props) and gives us a foundation to verify the design tokens are wired correctly. Building it first also lets us drop it into both layouts later.

- [ ] Write the test at `frontend/src/components/layout/__tests__/Footer.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";

  import { Footer } from "@/components/layout/Footer";

  describe("Footer", () => {
    it("renders the platform wordmark text", () => {
      render(<Footer />);
      expect(screen.getByText("知试")).toBeInTheDocument();
    });

    it("renders the subtitle 'internal exam platform'", () => {
      render(<Footer />);
      expect(screen.getByText(/internal exam platform/i)).toBeInTheDocument();
    });

    it("applies the dark footer background color", () => {
      const { container } = render(<Footer />);
      const footer = container.querySelector("footer");
      expect(footer).toHaveClass("bg-footer");
      expect(footer).toHaveClass("text-footer-soft");
    });

    it("contains a copyright line with the current year", () => {
      render(<Footer />);
      const year = new Date().getFullYear();
      expect(screen.getByText(new RegExp(`${year}`))).toBeInTheDocument();
    });
  });
  ```

- [ ] Run `cd frontend && npm test -- Footer` — tests fail (no implementation).

- [ ] Create `frontend/src/components/layout/Footer.tsx`:

  ```tsx
  import { Wordmark } from "@/components/editorial/Wordmark";

  export function Footer() {
    const year = new Date().getFullYear();

    return (
      <footer className="bg-footer text-footer-soft">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 md:flex-row md:items-start md:justify-between md:px-8 md:py-12">
          <div className="flex flex-col gap-3">
            <Wordmark size="sm" tone="dark" />
            <p className="text-body-sm max-w-sm">
              内部临时考试与刷题平台 · 轻量、可信、留有纸感。
            </p>
          </div>
          <div className="flex flex-col gap-2 text-body-sm md:items-end">
            <p className="text-caption tracking-[0.16em]">CONTACT</p>
            <a
              href="mailto:internal-exam@example.com"
              className="transition-colors hover:text-white"
            >
              internal-exam@example.com
            </a>
            <p className="text-caption">
              © {year} ZHISHI · INTERNAL EXAM PLATFORM
            </p>
          </div>
        </div>
      </footer>
    );
  }
  ```

- [ ] Run `cd frontend && npm test -- Footer` — all 4 tests pass.

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors.

- [ ] Commit:

  ```bash
  git add frontend/src/components/layout/Footer.tsx frontend/src/components/layout/__tests__/Footer.test.tsx
  git commit -m "feat(layout): 实现 Footer 组件"
  ```

---

## Task 4: Build the `TopNav` component (TDD)

**Files:**
- `frontend/src/components/layout/TopNav.tsx` (new)
- `frontend/src/components/layout/__tests__/TopNav.test.tsx` (new)

**Why:** TopNav is the candidate-side chrome. It introduces the `NavLink` + `useMediaQuery` + `Sheet` integration pattern that `AdminSideRail` mirrors in Task 5. Building it standalone lets us iterate on the mobile-sheet trigger pattern before it shows up twice.

- [ ] Write the test at `frontend/src/components/layout/__tests__/TopNav.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  userEvent from "@testing-library/user-event";
  import { MemoryRouter } from "react-router-dom";

  import { TopNav } from "@/components/layout/TopNav";
  import type { Candidate } from "@/types/candidate";

  const candidate: Candidate = {
    name: "张敏",
    employee_no: "E1001",
    department: "产品部",
  };

  function renderTopNav(props: { candidate: Candidate | null; onLogout: () => void }) {
    return render(
      <MemoryRouter initialEntries={["/practice"]}>
        <TopNav candidate={props.candidate} onLogout={props.onLogout} />
      </MemoryRouter>,
    );
  }

  describe("TopNav", () => {
    it("renders the wordmark linking to the home route", () => {
      renderTopNav({ candidate, onLogout: () => {} });
      const wordmarkLink = screen.getByRole("link", { name: /知试/ });
      expect(wordmarkLink).toHaveAttribute("href", "/exams");
    });

    it("renders all three primary nav items", () => {
      renderTopNav({ candidate, onLogout: () => {} });
      expect(screen.getByRole("link", { name: "练习" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "排名" })).toBeInTheDocument();
    });

    it("marks the active nav item with an underline (text-ink class)", () => {
      renderTopNav({ candidate, onLogout: () => {} });
      const activeLink = screen.getByRole("link", { name: "练习" });
      expect(activeLink).toHaveClass("text-ink");
      expect(activeLink.querySelector("span")).toHaveClass("bg-ink");
    });

    it("renders the candidate NamePlate when a candidate is logged in", () => {
      renderTopNav({ candidate, onLogout: () => {} });
      expect(screen.getByText("张敏")).toBeInTheDocument();
      expect(screen.getByText(/E1001/)).toBeInTheDocument();
    });

    it("renders a login link when no candidate is logged in", () => {
      renderTopNav({ candidate: null, onLogout: () => {} });
      expect(screen.getByRole("link", { name: /登录/ })).toBeInTheDocument();
    });

    it("invokes onLogout when the logout icon button is clicked", async () => {
      const onLogout = vi.fn();
      const user = userEvent.setup();
      renderTopNav({ candidate, onLogout });
      await user.click(screen.getByRole("button", { name: "退出登录" }));
      expect(onLogout).toHaveBeenCalledOnce();
    });
  });
  ```

  The `userEvent` import is `import userEvent from "@testing-library/user-event";`.

- [ ] Run `cd frontend && npm test -- TopNav` — tests fail (no implementation).

- [ ] Create `frontend/src/components/layout/TopNav.tsx`:

  ```tsx
  import { LogIn, LogOut, Menu } from "lucide-react";
  import { useState } from "react";
  import { Link, NavLink } from "react-router-dom";

  import { Wordmark } from "@/components/editorial/Wordmark";
  import { NamePlate } from "@/components/editorial/NamePlate";
  import { Button } from "@/components/ui/button";
  import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
  import { cn } from "@/lib/utils";
  import type { Candidate } from "@/types/candidate";

  type NavItem = { to: string; label: string; end?: boolean };

  const navItems: NavItem[] = [
    { to: "/practice", label: "练习" },
    { to: "/exams", label: "考试" },
    { to: "/exams/1/ranking", label: "排名" },
  ];

  type TopNavProps = {
    candidate: Candidate | null;
    onLogout: () => void;
  };

  function NavLinkItem({ item }: { item: NavItem }) {
    return (
      <NavLink
        to={item.to}
        end={item.end}
        className={({ isActive }) =>
          cn(
            `
              relative inline-flex h-10 items-center px-1 text-body-sm font-medium
              transition-colors
            `,
            isActive ? "text-ink" : "text-muted hover:text-ink",
          )
        }
      >
        {({ isActive }) => (
          <>
            <span>{item.label}</span>
            <span
              aria-hidden
              className={cn(
                `
                  absolute inset-x-0 -bottom-px h-px transition-opacity
                `,
                isActive ? "bg-ink opacity-100" : "opacity-0",
              )}
            />
          </>
        )}
      </NavLink>
    );
  }

  export function TopNav({ candidate, onLogout }: TopNavProps) {
    const [mobileOpen, setMobileOpen] = useState(false);

    return (
      <header className="sticky top-0 z-40 h-16 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-full max-w-6xl items-center justify-between gap-4 px-4 md:px-8">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <Link
              to="/exams"
              aria-label="知试首页"
              className="flex items-center gap-3 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              <Wordmark size="sm" />
            </Link>
          </div>

          {/* Desktop nav */}
          <nav className="hidden flex-1 items-center justify-center gap-8 lg:flex">
            {navItems.map((item) => (
              <NavLinkItem key={item.to} item={item} />
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {candidate ? (
              <div className="hidden items-center gap-3 md:flex">
                <NamePlate candidate={candidate} />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={onLogout}
                  aria-label="退出登录"
                  className="text-muted hover:text-ink"
                >
                  <LogOut aria-hidden />
                </Button>
              </div>
            ) : (
              <Button asChild variant="ghost" size="sm" className="hidden md:inline-flex">
                <Link to="/login">
                  <LogIn data-icon="inline-start" aria-hidden />
                  登录
                </Link>
              </Button>
            )}

            {/* Mobile menu trigger */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger
                className="inline-flex h-10 w-10 items-center justify-center rounded-pill text-ink transition-colors hover:bg-surface-card lg:hidden"
                aria-label="打开菜单"
              >
                <Menu aria-hidden />
              </SheetTrigger>
              <SheetContent side="bottom" className="rounded-t-lg">
                <SheetHeader>
                  <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
                </SheetHeader>
                <nav className="flex flex-col gap-1 px-4 pb-6">
                  {navItems.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          `
                            flex h-12 items-center rounded-md px-3 text-body font-medium
                            transition-colors
                          `,
                          isActive
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
                      <NamePlate candidate={candidate} />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setMobileOpen(false);
                          onLogout();
                        }}
                      >
                        <LogOut data-icon="inline-start" aria-hidden />
                        退出登录
                      </Button>
                    </div>
                  ) : (
                    <Button
                      asChild
                      variant="default"
                      className="mt-4"
                      onClick={() => setMobileOpen(false)}
                    >
                      <Link to="/login">
                        <LogIn data-icon="inline-start" aria-hidden />
                        登录
                      </Link>
                    </Button>
                  )}
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>
    );
  }
  ```

  Notes on the implementation:
  - `Wordmark` (from Phase 3) renders the Z-circle + "知试" text + optional subtitle. We pass `size="sm"` to keep the top-bar at 64px.
  - The active-state underline is rendered as a separate `<span>` so we can animate it without disturbing the text node position. The base text uses `text-muted`; active gets `text-ink` + an absolutely positioned 1px underline.
  - The desktop `NamePlate` + logout button hides below the `md` breakpoint to avoid overflow; the mobile sheet has a duplicate logout/login entry so the action is always reachable.
  - We use `lg:hidden` on the hamburger trigger to match the design rule "hamburger appears on phone AND tablet" (lg ≥ 1024px is the desktop breakpoint).

- [ ] Run `cd frontend && npm test -- TopNav` — all 6 tests pass.

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors.

- [ ] Commit:

  ```bash
  git add frontend/src/components/layout/TopNav.tsx frontend/src/components/layout/__tests__/TopNav.test.tsx
  git commit -m "feat(layout): 实现 TopNav 候选端顶栏"
  ```

---

## Task 5: Build the `AdminSideRail` component (TDD)

**Files:**
- `frontend/src/components/layout/AdminSideRail.tsx` (new)
- `frontend/src/components/layout/__tests__/AdminSideRail.test.tsx` (new)

**Why:** AdminSideRail mirrors the TopNav pattern (desktop sidebar + mobile FAB/sheet) but inverts the visual treatment (dark bg, white text, full-bleed). Building it after TopNav lets us reuse the `useMediaQuery` + `Sheet` integration we just validated.

- [ ] Write the test at `frontend/src/components/layout/__tests__/AdminSideRail.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  userEvent from "@testing-library/user-event";
  import { MemoryRouter } from "react-router-dom";

  import { AdminSideRail } from "@/components/layout/AdminSideRail";

  function renderSideRail(initialPath: string) {
    return render(
      <MemoryRouter initialEntries={[initialPath]}>
        <AdminSideRail />
      </MemoryRouter>,
    );
  }

  describe("AdminSideRail", () => {
    it("renders all five admin nav items", () => {
      renderSideRail("/admin/dashboard");
      expect(screen.getByRole("link", { name: "仪表盘" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "题库" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "导入" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "报表" })).toBeInTheDocument();
    });

    it("renders the dark wordmark with the 'admin' subtitle", () => {
      renderSideRail("/admin/dashboard");
      const wordmarkLink = screen.getByRole("link", { name: /知试/ });
      expect(wordmarkLink).toBeInTheDocument();
      expect(screen.getByText(/admin/i)).toBeInTheDocument();
    });

    it("highlights the active route with white text and white background", () => {
      renderSideRail("/admin/dashboard");
      const activeLink = screen.getByRole("link", { name: "仪表盘" });
      expect(activeLink).toHaveClass("bg-white");
      expect(activeLink).toHaveClass("text-ink");
    });

    it("applies dark background to the desktop aside container", () => {
      const { container } = renderSideRail("/admin/dashboard");
      const aside = container.querySelector("aside");
      expect(aside).toHaveClass("bg-footer");
    });

    it("opens the mobile sheet when the menu button is triggered", async () => {
      const user = userEvent.setup();
      renderSideRail("/admin/dashboard");
      // The mobile trigger is the only button with aria-label="打开菜单" in this component
      const trigger = screen.getByRole("button", { name: "打开菜单" });
      await user.click(trigger);
      // Sheet content includes a heading "导航"
      expect(await screen.findByText("导航")).toBeInTheDocument();
    });
  });
  ```

  The `userEvent` import is `import userEvent from "@testing-library/user-event";`.

- [ ] Run `cd frontend && npm test -- AdminSideRail` — tests fail (no implementation).

- [ ] Create `frontend/src/components/layout/AdminSideRail.tsx`:

  ```tsx
  import { Menu } from "lucide-react";
  import { useState } from "react";
  import { NavLink } from "react-router-dom";

  import { Wordmark } from "@/components/editorial/Wordmark";
  import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
  import { cn } from "@/lib/utils";

  type NavItem = { to: string; label: string; end?: boolean };

  const navItems: NavItem[] = [
    { to: "/admin/dashboard", label: "仪表盘" },
    { to: "/admin/questions", label: "题库" },
    { to: "/admin/questions/import", label: "导入" },
    { to: "/admin/exams", label: "考试" },
    { to: "/admin/reports/scores", label: "报表" },
  ];

  function SidebarList({ onNavigate }: { onNavigate?: () => void }) {
    return (
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                `
                  flex h-11 items-center rounded-md px-3 text-body-sm font-medium
                  transition-colors
                `,
                isActive
                  ? "bg-white text-ink"
                  : "text-footer-soft hover:bg-white/10 hover:text-white",
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

    return (
      <>
        {/* Desktop sidebar */}
        <aside className="hidden w-60 shrink-0 flex-col border-r border-black bg-footer px-5 py-6 text-footer-soft lg:flex">
          <div className="mb-8">
            <Wordmark size="sm" tone="dark" subtitle="admin" />
          </div>
          <SidebarList />
        </aside>

        {/* Mobile: brand + FAB */}
        <div className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-hairline-soft bg-canvas px-4 lg:hidden">
          <Wordmark size="sm" subtitle="admin" />
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger
              className="inline-flex h-10 w-10 items-center justify-center rounded-pill text-ink transition-colors hover:bg-surface-card"
              aria-label="打开菜单"
            >
              <Menu aria-hidden />
            </SheetTrigger>
            <SheetContent side="bottom" className="rounded-t-lg">
              <SheetHeader>
                <SheetTitle className="font-display text-display-sm">导航</SheetTitle>
              </SheetHeader>
              <div className="px-4 pb-6">
                <SidebarList onNavigate={() => setMobileOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </>
    );
  }
  ```

  Notes on the implementation:
  - Desktop sidebar is `hidden lg:flex` so it only renders layout above the `lg` (1024px) breakpoint.
  - Mobile fallback is a 64px bar with the wordmark and a hamburger — no FAB on top of a sheet (simpler than the spec's "FAB" wording, equivalent in behavior).
  - `bg-footer` (`#0a0a0a`) and `text-footer-soft` (`#a1a1aa`) come from Phase 1 design tokens.
  - Active state: `bg-white text-ink` (inverts the dark rail into a white pill on the active row).

- [ ] Run `cd frontend && npm test -- AdminSideRail` — all 5 tests pass.

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors.

- [ ] Commit:

  ```bash
  git add frontend/src/components/layout/AdminSideRail.tsx frontend/src/components/layout/__tests__/AdminSideRail.test.tsx
  git commit -m "feat(layout): 实现 AdminSideRail 黑色侧栏"
  ```

---

## Task 6: Rewrite `CandidateLayout` to compose TopNav + Footer + Outlet

**Files:**
- `frontend/src/components/layout/CandidateLayout.tsx` (rewrite — replaces the existing file)

**Why:** The existing layout inlines the header, candidate state, and outlet into one file. We need to split the chrome into `TopNav` (Task 4) and `Footer` (Task 3), keep the candidate-session context (used by `LoginPage` via `useOutletContext`), and wrap everything in the new 64px top bar + dark footer. We must not change the public `CandidateSessionContext` type — `LoginPage` and other consumers depend on it.

- [ ] Read the current consumers of `CandidateSessionContext` to confirm we keep the type stable:

  ```bash
  cd frontend && grep -rn "CandidateSessionContext\|useOutletContext" src/
  ```

  Expect to find: `src/pages/LoginPage.tsx`. Note any other consumers.

- [ ] Replace `frontend/src/components/layout/CandidateLayout.tsx` with:

  ```tsx
  import { useState } from "react";
  import { Outlet, useNavigate } from "react-router-dom";

  import { Footer } from "@/components/layout/Footer";
  import { TopNav } from "@/components/layout/TopNav";
  {
    clearCurrentCandidate,
    getCurrentCandidate,
    setCurrentCandidate,
  } from "@/lib/candidateSession";
  import type { Candidate } from "@/types/candidate";

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
      <div className="flex min-h-screen flex-col bg-canvas">
        <TopNav candidate={candidate} onLogout={logoutCandidate} />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-10">
          <Outlet
            context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
          />
        </main>
        <Footer />
      </div>
    );
  }
  ```

  The import statement is `import { clearCurrentCandidate, getCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";` — write it that way (the placeholder braces in the snippet are just formatting).

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors. The `CandidateSessionContext` type is exported from the same file with the same shape, so `LoginPage`'s `useOutletContext<CandidateSessionContext>()` keeps working.

- [ ] Run `cd frontend && npm test` — all existing tests still pass (the only consumers of this layout are the route definitions, which are not unit-tested).

- [ ] Spot-check that no other file in `frontend/src/` imports from `CandidateLayout` other than `router.tsx` and `LoginPage.tsx`:

  ```bash
  cd frontend && grep -rn "CandidateLayout\|CandidateSessionContext" src/
  ```

  Expect only `src/app/router.tsx` (imports `CandidateLayout`) and `src/pages/LoginPage.tsx` (imports `CandidateSessionContext`). If something else appears, update it to use the new public API.

- [ ] Commit:

  ```bash
  git add frontend/src/components/layout/CandidateLayout.tsx
  git commit -m "refactor(layout): 重写 CandidateLayout 接入 TopNav 和 Footer"
  ```

---

## Task 7: Rewrite `AdminLayout` to compose AdminSideRail + Outlet

**Files:**
- `frontend/src/components/layout/AdminLayout.tsx` (rewrite — replaces the existing file)

**Why:** Mirror Task 6 for the admin side. The existing layout uses a 240px aside on `md`+; we are moving to `lg`+ to align with the design breakpoint table. The `Outlet` renders the admin pages; we need a top-level grid: `[240px sidebar | main]` on desktop, stacked (sidebar-on-top mobile bar + main) on phone/tablet.

- [ ] Replace `frontend/src/components/layout/AdminLayout.tsx` with:

  ```tsx
  import { Outlet } from "react-router-dom";

  import { AdminSideRail } from "@/components/layout/AdminSideRail";
  import { Footer } from "@/components/layout/Footer";

  export function AdminLayout() {
    return (
      <div className="flex min-h-screen flex-col bg-canvas-warm">
        <div className="flex flex-1 flex-col lg:flex-row">
          <AdminSideRail />
          <main className="flex-1 px-4 py-6 md:px-8 md:py-10">
            <div className="mx-auto w-full max-w-6xl">
              <Outlet />
            </div>
          </main>
        </div>
        <Footer />
      </div>
    );
  }
  ```

  Notes:
  - `bg-canvas-warm` (`#fafaf7`) on the body wrapper gives admin pages the "paper" backdrop specified in section 6.7.
  - The `<AdminSideRail />` component already handles its own desktop/mobile switching; the layout just gives it flex layout context.
  - The admin login page lives at `/admin/login` and is NOT a child of `AdminLayout` (see `router.tsx`) — it renders the login form without any chrome, matching the spec's "admin login has its own layout language" rule (Phase 6 will style the login page).
  - We do NOT render the candidate `Footer` here — we render the shared `Footer` from Task 3, which is dark and works on both candidate and admin shells.

- [ ] Run `cd frontend && npx tsc --noEmit` — no type errors.

- [ ] Run `cd frontend && npm test` — all tests still pass.

- [ ] Commit:

  ```bash
  git add frontend/src/components/layout/AdminLayout.tsx
  git commit -m "refactor(layout): 重写 AdminLayout 接入 AdminSideRail"
  ```

---

## Task 8: Visual smoke test, lint, format, typecheck

**Files:** none — this is a verification + cleanup task.

**Why:** Phase 4 introduces 4 new files, rewrites 2 layouts, and changes the visual chrome of every authenticated page. A manual pass through both shells (candidate + admin) at desktop and mobile widths is the only way to catch layout regressions before Phase 5 starts polishing individual pages. After visual verification we run the project's quality gates so the phase lands in a green state.

- [ ] Start the dev server: `cd frontend && npm run dev`. Open `http://localhost:5173`.

- [ ] **Candidate shell — desktop (≥1024px):**
  - [ ] Log in as a test candidate (any name + optional employee_no). Confirm the new 64px top bar shows: Z-circle + "知试" + italic subtitle, 3 nav items with the active one underlined, NamePlate on the right, log-out icon button. Resize to ~1100px wide to confirm the desktop nav shows and the hamburger is hidden.
  - [ ] Navigate to `/practice`, `/exams`, `/exams/1/ranking` — confirm the underline moves to the right nav item.
  - [ ] Confirm the dark `#0a0a0a` footer renders at the bottom with `text-footer-soft` copy and the current year.

- [ ] **Candidate shell — mobile (<768px):**
  - [ ] Resize to 375px wide. The top bar should show the wordmark only; the hamburger should appear on the right.
  - [ ] Tap the hamburger; a bottom sheet slides up with the 3 nav items + NamePlate + logout button. Tap a nav item — it navigates AND closes the sheet.
  - [ ] Tap outside the sheet content — the sheet closes.

- [ ] **Admin shell — desktop (≥1024px):**
  - [ ] Log in to `/admin/login` and navigate to `/admin/dashboard`. Confirm the 240px black sidebar is visible with 5 white/grey nav items, the active one inverts to a white pill.
  - [ ] Click through `题库`, `导入`, `考试`, `报表` — confirm the active pill moves.
  - [ ] Confirm the admin main area sits on `bg-canvas-warm` (`#fafaf7`), not pure white.

- [ ] **Admin shell — mobile:**
  - [ ] Resize to 375px. The desktop sidebar disappears; a 64px mobile bar with the wordmark + hamburger replaces it.
  - [ ] Tap the hamburger; the bottom sheet opens with the same 5 nav items styled for the dark rail. Tapping a nav item navigates and closes the sheet.

- [ ] **Cross-shell sanity:**
  - [ ] Log out from the candidate shell — should redirect to `/login`. The TopNav should swap to the "登录" button (no NamePlate).
  - [ ] Reload the page after logging out — the candidate state should NOT persist visually (the TopNav stays in logged-out state).
  - [ ] Hard-refresh on `/admin/dashboard` while logged in — the layout should render without a flash of the mobile bar (the `useMediaQuery` initial value is computed synchronously in `useState`).

- [ ] Stop the dev server (Ctrl-C).

- [ ] Run the full quality gate:

  ```bash
  cd frontend
  npm run lint
  npm run format:check
  npx tsc --noEmit
  npm test
  npm run build
  ```

  All four must complete with zero errors. If `format:check` reports diffs, run `npm run format` and re-run the gate. If `lint` reports warnings, fix them — do not silence with `eslint-disable`.

- [ ] Verify the working tree is clean and on `main`:

  ```bash
  git status
  git log --oneline -8
  ```

  Expect 7 new commits in addition to whatever was on the branch before Phase 4 (one per task above). The phase is complete when the working tree is clean.

- [ ] Commit (only if formatting fixes were applied):

  ```bash
  git add -u frontend
  git commit -m "style: prettier 格式化 Phase 4 改动"
  ```

  Skip this step if `npm run format:check` was already clean.

- [ ] **Final report:** Reply to the user with a 1-paragraph summary of what was built (TopNav, AdminSideRail, Footer, useMediaQuery hook, layout rewrites, vitest setup) and the 7 commit hashes. Do not paste the full plan back.

---

## Acceptance checklist (mirrors the user-supplied success criteria)

- [ ] `frontend/src/lib/use-media-query.ts` exists and has 5 passing tests.
- [ ] `frontend/src/components/layout/Footer.tsx` exists and has 4 passing tests.
- [ ] `frontend/src/components/layout/TopNav.tsx` exists and has 6 passing tests.
- [ ] `frontend/src/components/layout/AdminSideRail.tsx` exists and has 5 passing tests.
- [ ] `frontend/src/components/layout/CandidateLayout.tsx` is rewritten to use `TopNav` + `Outlet` + `Footer` and continues to export `CandidateSessionContext` with the same shape.
- [ ] `frontend/src/components/layout/AdminLayout.tsx` is rewritten to use `AdminSideRail` + `Outlet` + `Footer`.
- [ ] `frontend/src/app/router.tsx` is unchanged (it already references the two layout components by name).
- [ ] `frontend/src/lib/candidateSession.ts` is unchanged.
- [ ] Desktop candidate shell (≥1024px) shows the 64px top bar with Z-circle + wordmark + italic subtitle + 3 horizontal nav items (active = underline + text-ink) + NamePlate + logout icon.
- [ ] Mobile candidate shell (<768px) shows a top bar with wordmark + hamburger; tapping the hamburger opens a bottom sheet with the same nav items.
- [ ] Desktop admin shell (≥1024px) shows a 240px dark (`#0a0a0a`) sidebar with white wordmark + 5 nav items (active = white pill, text-ink).
- [ ] Mobile admin shell (<768px) shows a top bar with the wordmark + hamburger; tapping opens a bottom sheet.
- [ ] `npm run lint`, `npm run format:check`, `npx tsc --noEmit`, `npm test`, `npm run build` all pass with zero errors.
- [ ] No use of `bg-accent`, `bg-primary`, `text-muted-foreground`, or other HSL-based shadcn tokens in the new layout files — they use the Phase 1 design-token utilities (`bg-canvas`, `text-ink`, `bg-footer`, `text-footer-soft`, `bg-surface-card`, `border-hairline-soft`).
- [ ] No `any` in the new files. All prop types and state are explicit.
- [ ] All icon-only buttons have an `aria-label` (logout, hamburger menu).
