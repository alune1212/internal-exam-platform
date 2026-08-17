import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { requestCandidateLoginOtp, verifyCandidateLoginOtp } from "@/api/auth";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { clearRegistrationFlow, getRegistrationFlow } from "@/lib/candidateSession";
import { LoginPage } from "@/pages/LoginPage";
import type { Candidate } from "@/types/candidate";

vi.mock("@/api/auth", () => ({
  requestCandidateLoginOtp: vi.fn(),
  verifyCandidateLoginOtp: vi.fn(),
}));

const candidate: Candidate = {
  id: 7,
  email: "user@example.com",
  display_name: "测试用户",
  status: "active",
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
};

const challenge = {
  challenge_id: 12,
  expires_at: "2099-01-01T00:10:00.000Z",
  resend_available_at: "2000-01-01T00:00:00.000Z",
};

function renderPage({
  entry = "/login",
  contextCandidate = null,
  loginCandidate = vi.fn(),
}: {
  entry?: string;
  contextCandidate?: Candidate | null;
  loginCandidate?: CandidateSessionContext["loginCandidate"];
} = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const context: CandidateSessionContext = {
    candidate: contextCandidate,
    loginCandidate,
    logoutCandidate: vi.fn(),
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route element={<Outlet context={context} />}>
            <Route path="*" element={<LoginPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage V2 Auth Canvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
    clearRegistrationFlow();
    vi.mocked(requestCandidateLoginOtp).mockResolvedValue(challenge);
    vi.mocked(verifyCandidateLoginOtp).mockResolvedValue({
      outcome: "authenticated",
      account: {
        id: candidate.id,
        email: candidate.email,
        display_name: candidate.display_name,
        status: candidate.status,
      },
      token: candidate.token,
      token_expires_at: candidate.token_expires_at,
    });
  });

  it("renders Chinese-first hierarchy with one heading, surface, and primary action", () => {
    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "邮箱登录" })).toBeInTheDocument();
    expect(screen.getByTestId("candidate-login-header")).toHaveAttribute("data-page-header");
    expect(
      screen.getByTestId("candidate-login-header").querySelectorAll("[data-page-context]"),
    ).toHaveLength(1);
    expect(screen.getByRole("group", { name: "登录操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送验证码" })).toBeInTheDocument();
    expect(
      screen.getByTestId("candidate-login-header").closest("[data-auth-canvas]"),
    ).toHaveAttribute("data-auth-canvas", "candidate");
    expect(screen.getByTestId("candidate-login-header").closest("[data-auth-canvas]")).toHaveClass(
      "landscape:grid",
    );
    expect(screen.getByText("知试")).toBeInTheDocument();
    expect(
      screen.getByText("登录后可进行学习、练习和错题复习；正式考试仅对受邀的应考人员开放。"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("uses the existing email OTP request and resend timing behavior", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("邮箱"), " User@Example.com ");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));

    await waitFor(() => expect(requestCandidateLoginOtp).toHaveBeenCalled());
    expect(vi.mocked(requestCandidateLoginOtp).mock.calls[0]?.[0]).toEqual({
      email: "user@example.com",
    });
    expect(await screen.findByLabelText("验证码")).toBeInTheDocument();
    expect(screen.getByText(/验证码已发送至/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新发送验证码" })).toBeEnabled();
  });

  it("keeps OTP verification, candidate session callback, and safe return state", async () => {
    const user = userEvent.setup();
    const loginCandidate = vi.fn();
    renderPage({ entry: "/login?returnTo=%2Flearning%2F9", loginCandidate });

    await user.type(screen.getByLabelText("邮箱"), "user@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    await user.type(await screen.findByLabelText("验证码"), "123456");
    await user.click(screen.getByRole("button", { name: "验证并继续" }));

    await waitFor(() => expect(verifyCandidateLoginOtp).toHaveBeenCalled());
    expect(vi.mocked(verifyCandidateLoginOtp).mock.calls[0]?.[0]).toEqual({
      challenge_id: 12,
      otp: "123456",
    });
    expect(loginCandidate).toHaveBeenCalledWith(candidate);
  });

  it("preserves registration-required recovery without exposing API codes", async () => {
    const user = userEvent.setup();
    vi.mocked(verifyCandidateLoginOtp).mockResolvedValueOnce({
      outcome: "registration_required",
      registration_credential: "registration-credential",
      email: "new@example.com",
      suggested_display_name: "新用户",
      registration_expires_at: "2099-01-01T00:10:00.000Z",
    });
    renderPage({ entry: "/login?returnTo=%2Fexams%2F1%2Fstart" });

    await user.type(screen.getByLabelText("邮箱"), "new@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    await user.type(await screen.findByLabelText("验证码"), "123456");
    await user.click(screen.getByRole("button", { name: "验证并继续" }));

    await waitFor(() =>
      expect(getRegistrationFlow()).toMatchObject({
        registration_credential: "registration-credential",
        email: "new@example.com",
        returnTo: "/exams/1/start",
      }),
    );
    expect(screen.queryByText("registration_required")).not.toBeInTheDocument();
  });

  it("shows recoverable request and verification errors in the shared feedback region", async () => {
    const user = userEvent.setup();
    vi.mocked(requestCandidateLoginOtp).mockRejectedValueOnce(new Error("mail unavailable"));
    renderPage();

    await user.type(screen.getByLabelText("邮箱"), "user@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
  });
});
