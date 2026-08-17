import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { completeCandidateRegistration } from "@/api/auth";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { clearRegistrationFlow, setRegistrationFlow } from "@/lib/candidateSession";
import { RegistrationPage } from "@/pages/RegistrationPage";
import type { Candidate } from "@/types/candidate";

vi.mock("@/api/auth", () => ({
  completeCandidateRegistration: vi.fn(),
}));

const candidate: Candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

function renderRegistration({ returnTo = "/exams/7/start", suggestedDisplayName = "张三" } = {}) {
  const loginCandidate = vi.fn();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  setRegistrationFlow({
    registration_credential: "registration-credential",
    email: candidate.email,
    suggested_display_name: suggestedDisplayName,
    returnTo,
    expires_at: "2099-01-01T00:10:00.000Z",
  });

  return {
    loginCandidate,
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/register?returnTo=${encodeURIComponent(returnTo)}`]}>
          <Routes>
            <Route element={<RegistrationRoute loginCandidate={loginCandidate} />}>
              <Route path="/register" element={<RegistrationPage />} />
              <Route path="/exams/:examId/start" element={<div>考试说明</div>} />
              <Route path="/exams" element={<div>考试列表</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

function RegistrationRoute({
  loginCandidate,
}: {
  loginCandidate: CandidateSessionContext["loginCandidate"];
}) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const context: CandidateSessionContext = {
    candidate,
    loginCandidate: (nextCandidate) => {
      loginCandidate(nextCandidate);
      setCandidate(nextCandidate);
    },
    logoutCandidate: vi.fn(),
  };

  return <Outlet context={context} />;
}

describe("RegistrationPage V2 Auth Canvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
    clearRegistrationFlow();
  });

  it("uses the semantic reading frame and shared auth action group", () => {
    renderRegistration();

    expect(screen.getByRole("heading", { level: 1, name: "完成账号注册" })).toBeInTheDocument();
    expect(screen.getByTestId("candidate-registration-shell")).toHaveAttribute(
      "data-width",
      "reading",
    );
    expect(screen.getByTestId("candidate-registration-shell")).toHaveAttribute(
      "data-auth-canvas",
      "candidate",
    );
    expect(screen.getByTestId("candidate-registration-shell")).toHaveClass("landscape:grid");
    expect(screen.getByTestId("candidate-registration-form-section")).toHaveAttribute(
      "data-surface-role",
      "panel",
    );
    expect(screen.getByRole("group", { name: "注册操作" })).toBeInTheDocument();
  });

  it("requires confirmation, supports keyboard submit, and preserves long names", async () => {
    const user = userEvent.setup();
    const longName = "这是一个用于验证长文本换行与输入保留的应考人员姓名";
    vi.mocked(completeCandidateRegistration).mockResolvedValue(candidate);
    renderRegistration({ suggestedDisplayName: longName });

    const nameInput = screen.getByRole("textbox", { name: "姓名" });
    expect(nameInput).toHaveValue(longName);
    expect(nameInput).toHaveFocus();

    await user.tab();
    await user.keyboard(" ");
    await user.tab();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(completeCandidateRegistration).toHaveBeenCalled());
    expect(vi.mocked(completeCandidateRegistration).mock.calls[0]?.[0]).toEqual({
      registration_credential: "registration-credential",
      display_name: longName,
    });
    expect(await screen.findByText("考试说明")).toBeInTheDocument();
  });

  it("exposes pending and recoverable error states without changing the registration contract", async () => {
    const user = userEvent.setup();
    let rejectRegistration: (error: Error) => void = () => undefined;
    const pendingRegistration = new Promise<Candidate>((_, reject) => {
      rejectRegistration = reject;
    });
    vi.mocked(completeCandidateRegistration).mockReturnValueOnce(pendingRegistration);
    renderRegistration();

    await user.click(screen.getByRole("checkbox", { name: "确认此姓名用于用户账号" }));
    await user.click(screen.getByRole("button", { name: "创建账号并继续" }));

    expect(screen.getByRole("button", { name: /创建账号并继续/ })).toBeDisabled();
    expect(
      screen.getByTestId("candidate-registration-form-section").querySelector("form"),
    ).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("textbox", { name: "姓名" })).toBeDisabled();

    rejectRegistration(new Error("registration unavailable"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "注册信息暂不可用，请重新验证邮箱后再试。",
    );
  });
});
