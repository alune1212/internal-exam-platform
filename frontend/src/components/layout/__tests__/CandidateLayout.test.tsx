import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { LoginPage } from "@/pages/LoginPage";

vi.mock("@/api/auth", () => ({
  loginCandidate: vi.fn(),
}));

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
  it("renders the login route as a clean auth screen without candidate navigation or footer", () => {
    renderCandidateShell("/login");

    expect(screen.getByRole("heading", { name: "登录考试人" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "练习" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "考试" })).not.toBeInTheDocument();
    expect(screen.queryByText("CONTACT")).not.toBeInTheDocument();
  });
});
