import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

const CANDIDATE_URL = process.env.E2E_CANDIDATE_URL ?? "http://127.0.0.1:18080";
const OPERATOR_URL = process.env.E2E_OPERATOR_URL ?? "http://127.0.0.1:18081";
const SMTP_CAPTURE_URL = process.env.E2E_SMTP_CAPTURE_URL ?? "http://127.0.0.1:18025";
const EXAM_TITLE = "E2E 正式考试";
const CANDIDATE_EMAIL = "e2e.candidate@example.com";
const CANDIDATE_STORAGE_KEY = "internal-exam-candidate";
const ADMIN_STORAGE_KEY = "internal-exam-admin-token";
const ALLOWED_RUNTIME_HOSTS = new Set(
  [CANDIDATE_URL, OPERATOR_URL, SMTP_CAPTURE_URL].map((url) => new URL(url).hostname),
);

function watchRuntime(page: Page, failures: string[], offline: () => boolean) {
  page.on("console", (message) => {
    if (message.type() === "error" && !offline()) failures.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => failures.push(`page: ${error.message}`));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!ALLOWED_RUNTIME_HOSTS.has(url.hostname)) {
      failures.push(`external-runtime-request: ${request.url()}`);
    }
  });
  page.on("requestfailed", (request) => {
    if (!offline()) failures.push(`request-failed: ${request.method()} ${request.url()}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failures.push(`server-error: ${response.status()} ${response.url()}`);
    }
  });
}

async function loginOperator(page: Page) {
  await page.goto(`${OPERATOR_URL}/admin/login`);
  await page.getByLabel("账号 · Username").fill("e2e-operator");
  await page.getByLabel("密码 · Password").fill("e2e-operator-password-not-for-formal-use");
  await page.getByRole("button", { name: "进入管理后台" }).click();
  await expect(page).toHaveURL(/\/admin\/dashboard$/);
}

async function waitForCapturedOtp(page: Page) {
  let capturedOtp = "";
  await expect
    .poll(async () => {
      const response = await page.request.get(
        `${SMTP_CAPTURE_URL}/messages/latest?recipient=${encodeURIComponent(CANDIDATE_EMAIL)}`,
      );
      if (!response.ok()) return "";
      const message = (await response.json()) as { otp?: string; subject?: string };
      capturedOtp = message.otp ?? "";
      return `${message.subject}:${message.otp}`;
    })
    .toBe("考试平台登录验证码:246810");
  return capturedOtp;
}

function composeArguments() {
  const composeFile = process.env.E2E_COMPOSE_FILE;
  const composeOverride = process.env.E2E_COMPOSE_OVERRIDE;
  const envFile = process.env.E2E_ENV_FILE;
  const projectName = process.env.E2E_PROJECT_NAME;
  if (!composeFile || !composeOverride || !envFile || !projectName) {
    throw new Error("Close-session E2E requires the disposable Compose runner variables");
  }
  return {
    envFile,
    args: [
      "compose",
      "--project-name",
      projectName,
      "--env-file",
      envFile,
      "-f",
      composeFile,
      "-f",
      composeOverride,
    ],
  };
}

async function closeAllSessions() {
  const { args, envFile } = composeArguments();
  execFileSync(
    "docker",
    [
      ...args,
      "exec",
      "-T",
      "backend",
      "uv",
      "run",
      "--no-sync",
      "python",
      "-m",
      "app.ops.operator_control",
      "check-session-closure",
    ],
    { stdio: "pipe" },
  );
  const original = readFileSync(envFile, "utf8");
  const rotated = original.replace(
    /^TOKEN_SECRET=.*$/m,
    `TOKEN_SECRET=e2e-rotated-${randomUUID()}-${randomUUID()}`,
  );
  if (rotated === original) throw new Error("Disposable E2E TOKEN_SECRET was not found");
  writeFileSync(envFile, rotated, { encoding: "utf8", mode: 0o600 });
  execFileSync("docker", [...args, "up", "-d", "--no-deps", "--force-recreate", "backend"], {
    stdio: "pipe",
  });
  await expect
    .poll(
      async () => {
        try {
          const response = await fetch(`${OPERATOR_URL}/api/ready`);
          return response.status;
        } catch {
          return 0;
        }
      },
      { timeout: 30_000 },
    )
    .toBe(200);
}

test("formal exam workflow survives offline recovery and enforces session boundaries", async ({
  browser,
}) => {
  test.setTimeout(180_000);
  const runtimeFailures: string[] = [];
  let suppressExpectedRequestFailure = false;

  const operatorContext = await browser.newContext();
  const operatorPage = await operatorContext.newPage();
  watchRuntime(operatorPage, runtimeFailures, () => suppressExpectedRequestFailure);
  await loginOperator(operatorPage);

  const candidateRouteProbe = await operatorPage.request.get(`${CANDIDATE_URL}/api/admin/exams`);
  expect(candidateRouteProbe.status()).toBe(404);
  expect((await operatorPage.request.get(`${CANDIDATE_URL}/docs`)).status()).toBe(404);

  const examsResponse = await operatorPage.request.get(`${OPERATOR_URL}/api/admin/exams`, {
    headers: {
      "X-Admin-Token": await operatorPage.evaluate(
        (key) => sessionStorage.getItem(key) ?? "",
        ADMIN_STORAGE_KEY,
      ),
    },
  });
  expect(examsResponse.ok()).toBe(true);
  const examsBody = (await examsResponse.json()) as { data: Array<{ id: number; title: string }> };
  const examId = examsBody.data.find((exam) => exam.title === EXAM_TITLE)?.id;
  expect(examId).toBeTruthy();

  await operatorPage.goto(`${OPERATOR_URL}/admin/exams/${examId}/edit`);
  await expect(operatorPage.getByText(/预检通过/)).toBeVisible();
  await operatorPage
    .getByLabel(new RegExp(`输入完整考试名称确认发布.*${EXAM_TITLE}`))
    .fill(EXAM_TITLE);
  await operatorPage.getByRole("button", { name: "确认发布" }).click();
  await expect(operatorPage.getByText("考试已发布，题池与应考名单已冻结。")).toBeVisible();

  const candidateContext = await browser.newContext();
  const candidatePage = await candidateContext.newPage();
  watchRuntime(candidatePage, runtimeFailures, () => suppressExpectedRequestFailure);
  await candidatePage.goto(`${CANDIDATE_URL}/login`);
  await candidatePage.getByLabel("姓名").fill("端到端考生");
  await candidatePage.getByLabel("员工号（可选）").fill("E2E-001");
  await candidatePage.getByLabel("邮箱").fill(CANDIDATE_EMAIL);
  await candidatePage.getByRole("button", { name: "发送验证码" }).click();
  await expect(candidatePage.getByLabel("验证码")).toBeVisible();
  await expect(candidatePage.getByText(/如果您的信息已登记在应考名单中/)).toBeVisible();
  const otp = await waitForCapturedOtp(candidatePage);
  await candidatePage.getByLabel("验证码").fill(otp);
  await candidatePage.getByRole("button", { name: "进入平台" }).click();
  await expect(candidatePage).toHaveURL(/\/exams$/);

  await candidatePage.getByRole("link", { name: "开始考试" }).click();
  await candidatePage.getByRole("button", { name: "开始考试" }).click();
  await expect(candidatePage).toHaveURL(/\/taking\?attemptId=\d+$/);
  const attemptId = new URL(candidatePage.url()).searchParams.get("attemptId");
  expect(attemptId).toMatch(/^\d+$/);

  suppressExpectedRequestFailure = true;
  await candidatePage.route("**/api/attempts/*/answers/save", (route) =>
    route.abort("internetdisconnected"),
  );
  await candidatePage.getByRole("radio", { name: /选项 A：主操作员/ }).click();
  await expect(candidatePage.getByText("网络中断，答案待同步")).toBeVisible();
  await candidatePage.reload();
  await expect(candidatePage.getByRole("radio", { name: /选项 A：主操作员/ })).toBeChecked();
  await expect(candidatePage.getByText("网络中断，答案待同步")).toBeVisible();
  const revisionResponse = candidatePage.waitForResponse(
    (response) => response.url().includes("/answers/save") && response.status() === 200,
  );
  await candidatePage.unroute("**/api/attempts/*/answers/save");
  suppressExpectedRequestFailure = false;
  await candidatePage.evaluate(() => window.dispatchEvent(new Event("online")));
  const savedBody = (await (await revisionResponse).json()) as {
    data: { answer_revision: number };
  };
  expect(savedBody.data.answer_revision).toBeGreaterThan(0);
  await expect(candidatePage.getByText("已保存", { exact: true })).toBeVisible();

  const candidatePayload = await candidatePage.evaluate(
    (key) => sessionStorage.getItem(key),
    CANDIDATE_STORAGE_KEY,
  );
  expect(candidatePayload).toBeTruthy();
  const takeoverContext = await browser.newContext();
  await takeoverContext.addInitScript(({ key, payload }) => sessionStorage.setItem(key, payload), {
    key: CANDIDATE_STORAGE_KEY,
    payload: candidatePayload!,
  });
  const takeoverPage = await takeoverContext.newPage();
  watchRuntime(takeoverPage, runtimeFailures, () => false);
  await takeoverPage.goto(
    `${CANDIDATE_URL}/exams/${examId}/taking?attemptId=${attemptId}&takeover=1`,
  );
  await expect(takeoverPage.getByRole("radio", { name: /选项 A：主操作员/ })).toBeVisible();

  const conflictResponse = candidatePage.waitForResponse(
    (response) => response.url().includes("/answers/save") && response.status() === 409,
  );
  suppressExpectedRequestFailure = true;
  await candidatePage.getByRole("radio", { name: /选项 B：任意考生/ }).click();
  await conflictResponse;
  await expect(candidatePage.getByText("答案版本冲突，请重新接管")).toBeVisible();
  suppressExpectedRequestFailure = false;

  const takeoverSaveResponse = takeoverPage.waitForResponse(
    (response) => response.url().includes("/answers/save") && response.status() === 200,
  );
  await takeoverPage.getByRole("radio", { name: /选项 B：任意考生/ }).click();
  await takeoverPage.getByRole("radio", { name: /选项 A：主操作员/ }).click();
  await takeoverSaveResponse;
  await expect(takeoverPage.getByText("已保存", { exact: true })).toBeVisible();
  const submitResponse = takeoverPage.waitForResponse((response) =>
    response.url().endsWith(`/api/attempts/${attemptId}/submit`),
  );
  await takeoverPage.getByRole("button", { name: "交卷" }).last().click();
  expect((await submitResponse).status()).toBe(200);
  await expect(takeoverPage).toHaveURL(/\/result\?attemptId=\d+$/);
  await expect(takeoverPage.getByText("答案与解析尚未发布。")).toBeVisible();

  await operatorPage.reload();
  const releaseRegion = operatorPage.getByRole("region", { name: "答案与解析" });
  await releaseRegion.getByRole("textbox").fill(EXAM_TITLE);
  const releaseButton = releaseRegion.getByRole("button", { name: "发布答案与解析" });
  await expect(releaseButton).toBeEnabled();
  const releaseResponse = operatorPage.waitForResponse(
    (response) =>
      response.url().includes("/result-details/release") && response.request().method() === "POST",
  );
  await releaseButton.click();
  expect((await releaseResponse).status()).toBe(200);
  await expect(operatorPage.getByText("答案与解析已一次性发布。")).toBeVisible();
  await takeoverPage.reload();
  await expect(takeoverPage.getByText("正确答案")).toBeVisible();

  const oldAdminToken = await operatorPage.evaluate(
    (key) => sessionStorage.getItem(key) ?? "",
    ADMIN_STORAGE_KEY,
  );
  const oldCandidateToken = JSON.parse(candidatePayload!) as { token: string };
  await closeAllSessions();
  expect(
    (
      await operatorPage.request.get(`${OPERATOR_URL}/api/admin/exams`, {
        headers: { "X-Admin-Token": oldAdminToken },
      })
    ).status(),
  ).toBe(401);
  expect(
    (
      await candidatePage.request.get(`${CANDIDATE_URL}/api/exams/active`, {
        headers: { "X-Candidate-Token": oldCandidateToken.token },
      })
    ).status(),
  ).toBe(401);

  expect(runtimeFailures).toEqual([]);
  await takeoverContext.close();
  await candidateContext.close();
  await operatorContext.close();
});
