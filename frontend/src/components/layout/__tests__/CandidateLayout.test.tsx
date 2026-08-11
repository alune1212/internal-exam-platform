import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateLayout } from "@/components/layout/CandidateLayout";
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
  name: "张三",
  employee_no: "YG0001",
  department: "综合管理部",
  status: "active",
  should_attend: true,
};
const supportedUserAgent =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36";

function renderCandidateShell(initialEntry: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <CandidateLayout />,
        children: [
          { path: "login", element: <LoginPage /> },
          { path: "exams", element: <div>考试列表</div> },
        ],
      },
    ],
    { initialEntries: [initialEntry] },
  );

  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <RouterProvider router={router} />
    </QueryClientProvider>,
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

    expect(
      screen.getByText(/macOS Chrome\/Safari（Chrome 120\+、Safari 17\+）/),
    ).toBeInTheDocument();
  });

  it("renders the login route as a clean auth screen without candidate navigation or footer", () => {
    renderCandidateShell("/login");

    expect(screen.getByRole("heading", { name: "入场核验" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "学习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "练习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "考试" })).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("renders the authenticated candidate app shell without a global footer", () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByText("考试列表")).toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("returns to login when a candidate session is cleared after unauthorized API response", async () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByText("考试列表")).toBeInTheDocument();

    act(() => {
      clearCurrentCandidate("unauthorized");
    });

    expect(await screen.findByRole("heading", { name: "入场核验" })).toBeInTheDocument();
    expect(screen.queryByText("考试列表")).not.toBeInTheDocument();
  });
});
