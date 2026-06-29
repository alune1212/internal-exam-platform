import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { clearCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";
import { LoginPage } from "@/pages/LoginPage";

vi.mock("@/api/auth", () => ({
  loginCandidate: vi.fn(),
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
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("renders the login route as a clean auth screen without candidate navigation or footer", () => {
    renderCandidateShell("/login");

    expect(screen.getByRole("heading", { name: "登录考试人" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "练习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "考试" })).not.toBeInTheDocument();
    expect(screen.queryByText("CONTACT")).not.toBeInTheDocument();
  });

  it("returns to login when a candidate session is cleared after unauthorized API response", async () => {
    setCurrentCandidate(mockCandidate);
    renderCandidateShell("/exams");

    expect(screen.getByText("考试列表")).toBeInTheDocument();

    act(() => {
      clearCurrentCandidate("unauthorized");
    });

    expect(await screen.findByRole("heading", { name: "登录考试人" })).toBeInTheDocument();
    expect(screen.queryByText("考试列表")).not.toBeInTheDocument();
  });
});
