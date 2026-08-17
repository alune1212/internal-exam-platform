import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { CANDIDATE_PRESENTATION_HANDLE } from "@/components/layout/candidate-presentation-mode";
import { clearCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";
import { LoginPage } from "@/pages/LoginPage";

vi.mock("@/api/auth", () => ({
  loginCandidate: vi.fn(),
  requestCandidateLoginOtp: vi.fn(),
  verifyCandidateLoginOtp: vi.fn(),
}));

const mockCandidate = {
  id: 42,
  token: "expired-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active" as const,
};
const supportedUserAgent =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36";

function mockMediaQuery(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

function renderCandidateShell(initialEntry: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <CandidateLayout />,
        children: [
          { path: "login", element: <LoginPage /> },
          { path: "register", element: <div>注册页</div> },
          { path: "exams", element: <div>考试列表</div> },
          {
            path: "exams/:examId/taking",
            element: <div>正式考试</div>,
            handle: { [CANDIDATE_PRESENTATION_HANDLE]: "focus" },
          },
        ],
      },
    ],
    { initialEntries: [initialEntry] },
  );

  return Object.assign(
    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
          })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
    { router },
  );
}

describe("CandidateLayout", () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: supportedUserAgent,
      configurable: true,
    });
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("blocks legacy or embedded browsers before login and formal attempts", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (Linux; Android 15) MicroMessenger/8.0 Chrome/140.0.0.0 Mobile",
      configurable: true,
    });

    const loginRender = renderCandidateShell("/login");

    expect(screen.getByRole("heading", { name: "请更换受支持的系统浏览器。" })).toBeInTheDocument();
    expect(screen.getByTestId("unsupported-browser")).toHaveAttribute("data-browser", "embedded");
    expect(screen.queryByRole("button", { name: "发送验证码" })).not.toBeInTheDocument();

    loginRender.unmount();
    renderCandidateShell("/exams");

    expect(screen.getByRole("heading", { name: "请更换受支持的系统浏览器。" })).toBeInTheDocument();
  });

  it("lists macOS support and its minimum browser versions", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Firefox/140.0",
      configurable: true,
    });

    renderCandidateShell("/login");

    expect(screen.getByText(/macOS Chrome（120 及以上）\/Safari（17 及以上）/)).toBeInTheDocument();
  });

  it("renders the login route as a clean auth screen without candidate navigation or footer", () => {
    renderCandidateShell("/login");

    expect(screen.getByRole("heading", { name: "邮箱登录" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "学习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "练习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "考试" })).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("keeps the registration route in the same chrome-free auth canvas", () => {
    renderCandidateShell("/register");

    expect(screen.getByText("注册页")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("renders the authenticated candidate app shell without a global footer", () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByText("考试列表")).toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("locks Candidate Calm to candidate navigation without admin or focus chrome", () => {
    mockMediaQuery(true);
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "学习" })).toHaveAttribute("href", "/learning");
    expect(screen.getByRole("link", { name: "练习" })).toHaveAttribute("href", "/practice");
    expect(screen.getByRole("link", { name: "考试" })).toHaveAttribute("href", "/exams");
    expect(screen.queryByRole("link", { name: "仪表盘" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "题号导航" })).not.toBeInTheDocument();
    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "calm",
    );
    expect(screen.getByRole("main")).not.toHaveClass("max-w-6xl");
  });

  it("selects static Exam Focus chrome for the formal taking route", () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams/7/taking");

    expect(screen.getByText("正式考试")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "focus",
    );
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("logs out through the existing candidate session action", async () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    await userEvent.setup().click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByRole("heading", { name: "邮箱登录" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toBeNull();
  });

  it("returns to login when a candidate session is cleared after unauthorized API response", async () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByText("考试列表")).toBeInTheDocument();

    act(() => {
      clearCurrentCandidate("unauthorized");
    });

    expect(await screen.findByRole("heading", { name: "邮箱登录" })).toBeInTheDocument();
    expect(screen.queryByText("考试列表")).not.toBeInTheDocument();
  });

  it("preserves a safe same-origin return target when guarding a candidate route", async () => {
    const { router } = renderCandidateShell("/exams?source=invite#details");

    expect(await screen.findByRole("heading", { name: "邮箱登录" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
    expect(router.state.location.search).toBe("?returnTo=%2Fexams%3Fsource%3Dinvite%23details");
  });
});
