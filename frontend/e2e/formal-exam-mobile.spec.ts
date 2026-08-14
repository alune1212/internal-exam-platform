import { expect, test } from "@playwright/test";

const CANDIDATE_STORAGE_KEY = "internal-exam-candidate";
const ATTEMPT_SESSION_KEY = "internal-exam-attempt-session:1:10";
const ATTEMPT_ID = 10;

const candidateSession = {
  id: 1,
  token: "mobile-candidate-fixture",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "mobile-fixture@example.com",
  display_name: "移动端测试",
  status: "active",
};

function buildAttempt() {
  const now = Date.now();
  return {
    id: ATTEMPT_ID,
    exam_id: 1,
    candidate_id: 1,
    status: "in_progress",
    started_at: new Date(now - 60_000).toISOString(),
    duration_minutes: 30,
    ends_at: new Date(now + 29 * 60_000).toISOString(),
    server_now: new Date(now).toISOString(),
    score: 0,
    total_score: 2,
    correct_count: 0,
    wrong_count: 0,
    attempt_session_generation: 1,
    answer_revision: 0,
    questions: [
      {
        id: 101,
        question_type: "single",
        stem_snapshot: "首都是哪里？",
        options_snapshot: [
          { label: "A", content: "北京", sort_order: 1 },
          { label: "B", content: "上海", sort_order: 2 },
        ],
        score: 2,
        sort_order: 1,
        selected_answer: null,
      },
    ],
  };
}

test("mobile Chromium keeps formal exam actions reachable", async ({ page }) => {
  const failures: string[] = [];
  const attempt = buildAttempt();

  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => failures.push(`page: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 500)
      failures.push(`server-error: ${response.status()} ${response.url()}`);
  });

  await page.addInitScript(
    ({ candidate, attemptSession, candidateStorageKey, attemptSessionKey }) => {
      window.sessionStorage.setItem(candidateStorageKey, JSON.stringify(candidate));
      window.sessionStorage.setItem(attemptSessionKey, JSON.stringify(attemptSession));
    },
    {
      candidate: candidateSession,
      candidateStorageKey: CANDIDATE_STORAGE_KEY,
      attemptSessionKey: ATTEMPT_SESSION_KEY,
      attemptSession: {
        candidateId: 1,
        attemptId: ATTEMPT_ID,
        credential: "mobile-attempt-fixture",
        generation: 1,
        answerRevision: 0,
      },
    },
  );

  await page.route("**/api/attempts/10", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: attempt, message: "ok" }),
    });
  });
  await page.route("**/api/attempts/10/answers/save", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          saved_count: 1,
          saved_at: new Date().toISOString(),
          answer_revision: 1,
        },
        message: "ok",
      }),
    });
  });

  await page.goto(`/exams/1/taking?attemptId=${ATTEMPT_ID}`);
  const questionHeading = page.getByRole("heading", { name: "首都是哪里？" });
  await expect(questionHeading).toBeVisible();
  await expect(questionHeading).toBeFocused();

  const saveButton = page.getByRole("button", { name: "保存答案" });
  await expect(saveButton).toBeVisible();
  await page.getByRole("radio", { name: /选项 A：北京/ }).click();
  await saveButton.click();
  await expect(page.getByTestId("exam-save-status")).toContainText(/保存|同步/);

  const navigatorTrigger = page.getByRole("button", { name: "打开题号导航" });
  await expect(navigatorTrigger).toBeVisible();
  const triggerBox = await navigatorTrigger.boundingBox();
  expect(triggerBox).not.toBeNull();
  expect(triggerBox!.x).toBeGreaterThanOrEqual(0);
  expect(triggerBox!.y).toBeGreaterThanOrEqual(0);
  expect(triggerBox!.x + triggerBox!.width).toBeLessThanOrEqual(page.viewportSize()!.width);

  const viewport = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth + 1);

  await navigatorTrigger.click();
  const sheet = page.getByRole("dialog");
  await expect(sheet).toBeVisible();
  await expect(sheet.getByRole("region", { name: "题号导航" })).toBeVisible();
  await expect(sheet.getByRole("button", { name: "跳转到第 1 题" })).toBeVisible();
  await expect(sheet.getByRole("button", { name: "交卷" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  expect(failures).toEqual([]);
});
