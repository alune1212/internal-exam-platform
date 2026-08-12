import { expect, test, type Page } from "@playwright/test";

const CANDIDATE_URL = process.env.E2E_CANDIDATE_URL ?? "http://127.0.0.1:18080";
const OPERATOR_URL = process.env.E2E_OPERATOR_URL ?? "http://127.0.0.1:18081";
const SMTP_CAPTURE_URL = process.env.E2E_SMTP_CAPTURE_URL ?? "http://127.0.0.1:18025";
const UPCOMING_EXAM_TITLE = "E2E 邀请考试（即将开放）";
const INVITATION_STATUS_EXAM_TITLE = "E2E 邀请投递状态";
const PENDING_EMAIL = "e2e.pending@example.com";
const SCOPED_EMAIL = "e2e.scoped@example.com";
const INACTIVE_EMAIL = "e2e.inactive@example.com";
const CANDIDATE_STORAGE_KEY = "internal-exam-candidate";
const ADMIN_STORAGE_KEY = "internal-exam-admin-token";
const ALLOWED_RUNTIME_HOSTS = new Set(
  [CANDIDATE_URL, OPERATOR_URL, SMTP_CAPTURE_URL].map((url) => new URL(url).hostname),
);

type ApiEnvelope<T> = { data: T };
type Exam = { id: number; title: string; available_from?: string | null };
type AdminAccount = { id: number; email: string; status: string };
type CandidateSession = { id: number; token: string };
type InvitationStatus = {
  total_count: number;
  not_sent_count: number;
  sent_count: number;
  failed_count: number;
};

function watchRuntime(page: Page, failures: string[]) {
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => failures.push(`page: ${error.message}`));
  page.on("request", (request) => {
    if (!ALLOWED_RUNTIME_HOSTS.has(new URL(request.url()).hostname)) {
      failures.push(`external-runtime-request: ${request.url()}`);
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 500)
      failures.push(`server-error: ${response.status()} ${response.url()}`);
  });
}

async function loginOperator(page: Page): Promise<string> {
  await page.goto(`${OPERATOR_URL}/admin/login`);
  await page.getByLabel("账号 · Username").fill("e2e-operator");
  await page.getByLabel("密码 · Password").fill("e2e-operator-password-not-for-formal-use");
  await page.getByRole("button", { name: "进入管理后台" }).click();
  await expect(page).toHaveURL(/\/admin\/dashboard$/);
  return page.evaluate((key) => sessionStorage.getItem(key) ?? "", ADMIN_STORAGE_KEY);
}

async function getAdminExams(page: Page, token: string): Promise<Exam[]> {
  const response = await page.request.get(`${OPERATOR_URL}/api/admin/exams`, {
    headers: { "X-Admin-Token": token },
  });
  expect(response.ok()).toBe(true);
  return ((await response.json()) as ApiEnvelope<Exam[]>).data;
}

async function getAdminAccount(page: Page, token: string, email: string): Promise<AdminAccount> {
  const response = await page.request.get(
    `${OPERATOR_URL}/api/admin/accounts?search=${encodeURIComponent(email)}`,
    { headers: { "X-Admin-Token": token } },
  );
  expect(response.ok()).toBe(true);
  const accounts = ((await response.json()) as ApiEnvelope<AdminAccount[]>).data;
  const account = accounts.find((item) => item.email === email);
  expect(account).toBeTruthy();
  return account!;
}

async function waitForCapturedOtp(page: Page, email: string): Promise<string> {
  let otp = "";
  await expect
    .poll(async () => {
      const response = await page.request.get(
        `${SMTP_CAPTURE_URL}/messages/latest?recipient=${encodeURIComponent(email)}&kind=otp`,
      );
      if (!response.ok()) return "";
      const message = (await response.json()) as { otp?: string; subject?: string };
      otp = message.otp ?? "";
      return `${message.subject}:${message.otp}`;
    })
    .toBe("考试平台登录验证码:246810");
  return otp;
}

async function loginOrCompleteRegistration(
  page: Page,
  email: string,
  returnTo: string,
  displayName?: string,
): Promise<CandidateSession> {
  await page.goto(`${CANDIDATE_URL}/login?returnTo=${encodeURIComponent(returnTo)}`);
  await expect(page.getByRole("heading", { name: "邮箱登录" })).toBeVisible();
  await expect(page.getByText("员工号")).toHaveCount(0);
  await page.getByLabel("邮箱").fill(email);
  await page.getByRole("button", { name: "发送验证码" }).click();
  await expect(page.getByLabel("验证码")).toBeVisible();
  const otp = await waitForCapturedOtp(page, email);
  await page.getByLabel("验证码").fill(otp);
  await page.getByRole("button", { name: "验证并继续" }).click();

  if (displayName) {
    await expect(page).toHaveURL(/\/register/);
    const displayNameInput = page.getByRole("textbox", { name: "姓名", exact: true });
    await expect(displayNameInput).toBeVisible();
    await displayNameInput.fill(displayName);
    await page.getByRole("button", { name: /创建账号并继续/ }).click();
  }
  await expect
    .poll(() => page.evaluate((key) => sessionStorage.getItem(key), CANDIDATE_STORAGE_KEY))
    .not.toBeNull();
  const payload = await page.evaluate((key) => sessionStorage.getItem(key), CANDIDATE_STORAGE_KEY);
  if (!payload) throw new Error("candidate session was not stored");
  return JSON.parse(payload) as CandidateSession;
}

async function getInvitationStatus(page: Page, token: string, examId: number) {
  const response = await page.request.get(`${OPERATOR_URL}/api/admin/exams/${examId}/invitations`, {
    headers: { "X-Admin-Token": token },
  });
  expect(response.ok()).toBe(true);
  return ((await response.json()) as ApiEnvelope<InvitationStatus>).data;
}

test("email registration preserves invitation return and enforces the opening boundary", async ({
  browser,
}) => {
  test.setTimeout(120_000);
  const failures: string[] = [];
  const operatorContext = await browser.newContext();
  const operatorPage = await operatorContext.newPage();
  watchRuntime(operatorPage, failures);
  const adminToken = await loginOperator(operatorPage);
  const exams = await getAdminExams(operatorPage, adminToken);
  const upcoming = exams.find((exam) => exam.title === UPCOMING_EXAM_TITLE);
  expect(upcoming).toBeTruthy();

  const candidateContext = await browser.newContext();
  const candidatePage = await candidateContext.newPage();
  watchRuntime(candidatePage, failures);
  const returnTo = `/exams/${upcoming!.id}/start`;
  await loginOrCompleteRegistration(candidatePage, PENDING_EMAIL, returnTo, "注册后用户");
  await expect(candidatePage).toHaveURL(new RegExp(`/exams/${upcoming!.id}/start$`));
  await expect(candidatePage.getByRole("button", { name: "尚未开放" })).toBeDisabled();
  await expect(candidatePage.getByText("应考人员可在")).toBeVisible();

  const session = JSON.parse(
    (await candidatePage.evaluate((key) => sessionStorage.getItem(key), CANDIDATE_STORAGE_KEY)) ??
      "{}",
  ) as CandidateSession;
  const startResponse = await candidatePage.request.post(
    `${CANDIDATE_URL}/api/exams/${upcoming!.id}/start`,
    { headers: { "X-Candidate-Token": session.token } },
  );
  expect(startResponse.ok()).toBe(false);

  await candidatePage.goto(`${CANDIDATE_URL}/practice`);
  await expect(candidatePage.getByRole("heading", { name: "日常练习" })).toBeVisible();
  await candidatePage.getByRole("radio").first().click();
  await candidatePage.getByRole("button", { name: "提交本题" }).click();
  await expect(
    candidatePage.locator("#practice-question-focus").getByText(/回答正确|回答错误/),
  ).toBeVisible();

  const absentResponse = await operatorPage.request.get(
    `${OPERATOR_URL}/api/admin/reports/absent-candidates?exam_id=${upcoming!.id}&status=not_started`,
    { headers: { "X-Admin-Token": adminToken } },
  );
  expect(absentResponse.ok()).toBe(true);
  const absentRows = (
    (await absentResponse.json()) as ApiEnvelope<
      Array<{ roster_email: string; roster_name: string }>
    >
  ).data;
  expect(absentRows).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        roster_email: SCOPED_EMAIL,
        roster_name: "冻结名单姓名",
      }),
    ]),
  );
  expect(failures).toEqual([]);

  await candidateContext.close();
  await operatorContext.close();
});

test("invitation delivery is explicit, isolated, and failed-only resendable", async ({
  browser,
}) => {
  test.setTimeout(90_000);
  const failures: string[] = [];
  const operatorContext = await browser.newContext();
  const operatorPage = await operatorContext.newPage();
  watchRuntime(operatorPage, failures);
  const adminToken = await loginOperator(operatorPage);
  const exams = await getAdminExams(operatorPage, adminToken);
  const upcoming = exams.find((exam) => exam.title === UPCOMING_EXAM_TITLE);
  const statusExam = exams.find((exam) => exam.title === INVITATION_STATUS_EXAM_TITLE);
  expect(upcoming).toBeTruthy();
  expect(statusExam).toBeTruthy();

  const initial = await getInvitationStatus(operatorPage, adminToken, upcoming!.id);
  expect(initial.not_sent_count).toBeGreaterThan(0);
  expect(initial.sent_count).toBe(0);
  expect(initial.failed_count).toBe(0);

  const sendResponse = await operatorPage.request.post(
    `${OPERATOR_URL}/api/admin/exams/${upcoming!.id}/invitations/send`,
    { headers: { "X-Admin-Token": adminToken } },
  );
  expect(sendResponse.ok()).toBe(true);
  await expect
    .poll(
      async () => (await getInvitationStatus(operatorPage, adminToken, upcoming!.id)).sent_count,
    )
    .toBe(initial.total_count);

  const failedBeforeResend = await getInvitationStatus(operatorPage, adminToken, statusExam!.id);
  expect(failedBeforeResend.failed_count).toBeGreaterThan(0);
  const resendResponse = await operatorPage.request.post(
    `${OPERATOR_URL}/api/admin/exams/${statusExam!.id}/invitations/resend`,
    { headers: { "X-Admin-Token": adminToken } },
  );
  expect(resendResponse.ok()).toBe(true);
  await expect
    .poll(
      async () =>
        (await getInvitationStatus(operatorPage, adminToken, statusExam!.id)).failed_count,
    )
    .toBe(0);
  const final = await getInvitationStatus(operatorPage, adminToken, statusExam!.id);
  expect(final.sent_count).toBe(failedBeforeResend.sent_count + failedBeforeResend.failed_count);
  expect(failures).toEqual([]);
  await operatorContext.close();
});

test("inactive verification and account deactivation clear candidate sessions", async ({
  browser,
}) => {
  test.setTimeout(120_000);
  const failures: string[] = [];
  const operatorContext = await browser.newContext();
  const operatorPage = await operatorContext.newPage();
  watchRuntime(operatorPage, failures);
  const adminToken = await loginOperator(operatorPage);
  const exams = await getAdminExams(operatorPage, adminToken);
  const upcoming = exams.find((exam) => exam.title === UPCOMING_EXAM_TITLE);
  expect(upcoming).toBeTruthy();

  const inactiveContext = await browser.newContext();
  const inactivePage = await inactiveContext.newPage();
  watchRuntime(inactivePage, failures);
  await inactivePage.goto(`${CANDIDATE_URL}/login`);
  await inactivePage.getByLabel("邮箱").fill(INACTIVE_EMAIL);
  await inactivePage.getByRole("button", { name: "发送验证码" }).click();
  const inactiveOtp = await waitForCapturedOtp(inactivePage, INACTIVE_EMAIL);
  await inactivePage.getByLabel("验证码").fill(inactiveOtp);
  const inactiveVerifyResponsePromise = inactivePage.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/candidates/login/verify"),
  );
  await inactivePage.getByRole("button", { name: "验证并继续" }).click();
  const inactiveVerifyResponse = await inactiveVerifyResponsePromise;
  expect(inactiveVerifyResponse.ok()).toBe(true);
  const inactiveVerifyData = (
    (await inactiveVerifyResponse.json()) as ApiEnvelope<{
      outcome: string;
      message?: string;
      token?: string;
    }>
  ).data;
  expect(inactiveVerifyData.outcome).toBe("account_unavailable");
  expect(inactiveVerifyData.message).toBe("账号暂不可用，请联系管理员重新激活。");
  expect(inactiveVerifyData).not.toHaveProperty("token");
  await expect(inactivePage.getByText("账号暂不可用，请联系管理员重新激活。")).toBeVisible();
  await expect(
    inactivePage.evaluate((key) => sessionStorage.getItem(key), CANDIDATE_STORAGE_KEY),
  ).resolves.toBeNull();

  const scopedContext = await browser.newContext();
  const scopedPage = await scopedContext.newPage();
  watchRuntime(scopedPage, failures);
  await loginOrCompleteRegistration(scopedPage, SCOPED_EMAIL, `/exams/${upcoming!.id}/start`);
  const scopedAccount = await getAdminAccount(operatorPage, adminToken, SCOPED_EMAIL);
  const deactivate = await operatorPage.request.patch(
    `${OPERATOR_URL}/api/admin/accounts/${scopedAccount.id}/status`,
    {
      headers: { "X-Admin-Token": adminToken },
      data: { status: "inactive" },
    },
  );
  expect(deactivate.ok()).toBe(true);
  await scopedPage.goto(`${CANDIDATE_URL}/exams`);
  await expect(scopedPage).toHaveURL(/\/login\?/);
  await expect(
    scopedPage.evaluate((key) => sessionStorage.getItem(key), CANDIDATE_STORAGE_KEY),
  ).resolves.toBeNull();

  // The deactivated session's first active-exam refresh is intentionally rejected by the
  // API. Chromium reports that expected 401 as a console error, so consume exactly that
  // signal before asserting that no unexpected runtime failures were observed.
  const expectedUnauthorizedConsole =
    "console: Failed to load resource: the server responded with a status of 401 (Unauthorized)";
  const unauthorizedIndex = failures.indexOf(expectedUnauthorizedConsole);
  expect(unauthorizedIndex).toBeGreaterThanOrEqual(0);
  failures.splice(unauthorizedIndex, 1);

  const reactivate = await operatorPage.request.patch(
    `${OPERATOR_URL}/api/admin/accounts/${scopedAccount.id}/status`,
    {
      headers: { "X-Admin-Token": adminToken },
      data: { status: "active" },
    },
  );
  expect(reactivate.ok()).toBe(true);
  expect(failures).toEqual([]);
  await scopedContext.close();
  await inactiveContext.close();
  await operatorContext.close();
});
