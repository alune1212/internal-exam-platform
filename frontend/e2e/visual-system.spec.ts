import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";

import {
  CANDIDATE_URL,
  OPERATOR_URL,
  VISUAL_ATTEMPT_ID,
  VISUAL_EXAM_ID,
  VISUAL_LANDSCAPE_VIEWPORTS,
  VISUAL_VIEWPORTS,
  installVisualAuth,
  installVisualRoutes,
  setVisualOffline,
  type VisualAuthOptions,
  type VisualRouteHandle,
  type VisualRouteState,
} from "./fixtures/visual-system";

type Family = "auth" | "candidate" | "admin" | "focus";
type Viewport = (typeof VISUAL_VIEWPORTS)[number];

test.describe.configure({ mode: "serial" });

function portraitViewports() {
  return VISUAL_VIEWPORTS.filter(
    ({ name }) => name !== "landscape-phone" && name !== "landscape-tablet",
  );
}

function slug(pathname: string) {
  return pathname
    .replace(/^\//, "")
    .replace(/[/:?=&]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/-$/, "")
    .replace(/[^a-zA-Z0-9\u4e00-\u9fff-]/g, "-")
    .toLowerCase();
}

async function setDeterministicViewport(page: Page, viewport: Viewport, reducedMotion = false) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.emulateMedia({ reducedMotion: reducedMotion ? "reduce" : "no-preference" });
}

async function gotoVisualRoute(
  page: Page,
  host: string,
  pathname: string,
  auth: VisualAuthOptions,
  state: VisualRouteState = "ready",
  attemptStatus?: "in_progress" | "submitted" | "auto_submitted",
) {
  await installVisualAuth(page, auth);
  const fixture = await installVisualRoutes(page, { state, attemptStatus });
  await page.goto(`${host}${pathname}`, { waitUntil: "domcontentloaded" });
  await page.locator("h1:visible, h2:visible, h3:visible").first().waitFor({ state: "visible" });
  return fixture;
}

function collectRuntimeProblems(page: Page) {
  const problems: string[] = [];
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().startsWith("Failed to load resource: the server responded with a status of")
    ) {
      problems.push(`console: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 400) problems.push(`http ${response.status()}: ${response.url()}`);
  });
  return problems;
}

async function assertHeadingOrder(page: Page, family: Family) {
  const headings = await page.locator("h1, h2, h3, h4, h5, h6").evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const style = window.getComputedStyle(node);
        const rect = (node as HTMLElement).getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0;
      })
      .map((node) => Number(node.tagName.slice(1))),
  );
  expect(headings.length, `${family} should expose a visible heading`).toBeGreaterThan(0);
  if (family === "focus") {
    expect(headings.some((level) => level === 2 || level === 3)).toBeTruthy();
    return;
  }
  expect(headings.filter((level) => level === 1).length).toBe(1);
  for (let index = 1; index < headings.length; index += 1) {
    expect(headings[index] - headings[index - 1]).toBeLessThanOrEqual(1);
  }
}

async function assertNoHorizontalOverflow(page: Page) {
  const result = await page.evaluate(() => {
    document.documentElement.style.overflowX = "visible";
    document.body.style.overflowX = "visible";
    const root = document.documentElement;
    const viewportRight = window.innerWidth + 1;
    const outOfBounds: string[] = [];
    document.querySelectorAll<HTMLElement>("body *").forEach((element) => {
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden") return;
      if (style.position === "absolute" || style.position === "fixed") return;
      const rect = element.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0 && rect.right > viewportRight) {
        outOfBounds.push(`${element.tagName.toLowerCase()}.${element.className}`.slice(0, 160));
      }
    });
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      outOfBounds: outOfBounds.slice(0, 5),
    };
  });
  expect(
    result.scrollWidth,
    `root overflow: ${JSON.stringify(result.outOfBounds)}`,
  ).toBeLessThanOrEqual(result.clientWidth + 1);
  expect(result.outOfBounds, "visible content must stay within the viewport").toEqual([]);
}

async function assertCompactLabels(page: Page) {
  const violations = await page
    .locator(
      "button:not([role='radio']):not([role='checkbox']), a, [role='tab'], [role='menuitem']",
    )
    .evaluateAll((nodes) => {
      const result: string[] = [];
      nodes.forEach((node) => {
        const element = node as HTMLElement;
        const text = element.innerText.trim();
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);
        if (!text || style.display === "none" || style.visibility === "hidden" || rect.width === 0)
          return;
        const lineHeight = Number.parseFloat(style.lineHeight);
        // Controls own a minimum hit area (often 40–48px) around a one-line
        // label, so compare the rendered label budget rather than treating the
        // hit area itself as a wrapped line. A second line increases scrollHeight
        // beyond this 2.5x allowance at the governed type sizes.
        if (Number.isFinite(lineHeight) && element.scrollHeight > lineHeight * 2.5) {
          result.push(`${text.slice(0, 40)} (${element.scrollHeight}/${lineHeight})`);
        }
      });
      return result;
    });
  expect(violations, "compact action labels must remain one line").toEqual([]);
}

async function assertRequiredActionAndFocus(page: Page) {
  const actions = page.locator("button:not([disabled]), a[href]");
  await expect(actions.first()).toBeVisible();
  const actionInsideViewport = await actions.evaluateAll((nodes) =>
    nodes.some((node) => {
      const element = node as HTMLElement;
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        rect.width > 0 &&
        rect.height > 0 &&
        rect.bottom >= 0 &&
        rect.top <= window.innerHeight
      );
    }),
  );
  expect(actionInsideViewport).toBeTruthy();
  const unobscured = await actions.first().evaluate((node) => {
    const rect = (node as HTMLElement).getBoundingClientRect();
    const target = document.elementFromPoint(
      rect.left + rect.width / 2,
      rect.top + rect.height / 2,
    );
    return Boolean(target && (target === node || (node as HTMLElement).contains(target)));
  });
  expect(unobscured, "the first required action must not be covered").toBeTruthy();

  let focusState = { focused: false, visibleRing: false };
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press("Tab");
    focusState = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      if (!active || active === document.body) return { focused: false, visibleRing: false };
      const style = window.getComputedStyle(active);
      const rect = active.getBoundingClientRect();
      const visibleRing =
        style.outlineStyle !== "none" ||
        Number.parseFloat(style.outlineWidth) > 0 ||
        style.boxShadow !== "none";
      return { focused: rect.width > 0 && rect.height > 0, visibleRing };
    });
    if (focusState.focused && focusState.visibleRing) break;
  }
  expect(focusState.focused).toBeTruthy();
  expect(focusState.visibleRing, "keyboard focus must expose a visible ring").toBeTruthy();
}

async function assertNoRuntimeProblems(page: Page, problems: string[], fixture: VisualRouteHandle) {
  const expectedFailures = new Set(fixture.failedRequests);
  const unexpectedHttp = problems.filter((problem) => {
    if (!problem.startsWith("http ")) return true;
    return ![...expectedFailures].some((request) =>
      problem.includes(request.split(" ").slice(1).join(" ")),
    );
  });
  expect(fixture.unexpectedApiRequests, "all API calls must be declared by the fixture").toEqual(
    [],
  );
  expect(unexpectedHttp, "unexpected console/page/runtime failures").toEqual([]);
  await fixture.dispose();
}

async function captureVisual(
  testInfo: TestInfo,
  page: Page,
  family: Family,
  route: string,
  viewport: Viewport,
) {
  const outputRoot = process.env.PLAYWRIGHT_OUTPUT_DIR ?? testInfo.outputDir;
  const outputPath = join(
    outputRoot,
    "visual-system",
    family,
    `${slug(route)}-${viewport.name}.png`,
  );
  await mkdir(dirname(outputPath), { recursive: true });
  await page.screenshot({ path: outputPath, fullPage: true });
}

async function assertVisualContract(
  page: Page,
  testInfo: TestInfo,
  family: Family,
  route: string,
  viewport: Viewport,
  fixture: VisualRouteHandle,
  problems: string[],
) {
  await assertHeadingOrder(page, family);
  await assertNoHorizontalOverflow(page);
  await assertCompactLabels(page);
  await assertRequiredActionAndFocus(page);
  await captureVisual(testInfo, page, family, route, viewport);
  await assertNoRuntimeProblems(page, problems, fixture);
}

async function assertExamFocusNavigation(page: Page, viewport: Viewport) {
  if (viewport.width < 1024) {
    const trigger = page.getByRole("button", { name: "打开题号导航" });
    await expect(trigger).toBeVisible();
    await trigger.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("button", { name: "交卷" })).toBeVisible();
    await page.getByRole("button", { name: "关闭" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    return;
  }

  await expect(page.getByRole("region", { name: "题号导航" })).toBeVisible();
  await expect(page.getByRole("button", { name: "交卷" })).toBeVisible();
}

const authRoutes = [
  { route: "/login", auth: {}, state: "ready" as const },
  { route: "/register", auth: { registration: true }, state: "ready" as const },
  { route: "/admin/login", auth: {}, state: "ready" as const, admin: true },
];

const candidateRoutes = [
  { route: "/learning", auth: { candidate: true } },
  { route: "/practice/wrong-questions", auth: { candidate: true } },
  { route: "/exams", auth: { candidate: true } },
  { route: `/exams/${VISUAL_EXAM_ID}/start`, auth: { candidate: true } },
  {
    route: `/exams/${VISUAL_EXAM_ID}/result?attemptId=${VISUAL_ATTEMPT_ID}`,
    auth: { candidate: true },
  },
  { route: "/profile", auth: { candidate: true } },
];

const adminRoutes = [
  { route: "/admin/dashboard", auth: { admin: true } },
  { route: "/admin/accounts", auth: { admin: true } },
  { route: "/admin/questions", auth: { admin: true } },
  { route: "/admin/questions/import", auth: { admin: true } },
  { route: "/admin/exams", auth: { admin: true } },
  { route: `/admin/exams/${VISUAL_EXAM_ID}/edit`, auth: { admin: true } },
  { route: `/admin/exams/${VISUAL_EXAM_ID}/candidates`, auth: { admin: true } },
  { route: `/admin/exams/${VISUAL_EXAM_ID}`, auth: { admin: true }, state: "stale" as const },
  { route: "/admin/learning", auth: { admin: true } },
  { route: "/admin/learning/reports", auth: { admin: true } },
  { route: "/admin/reports/scores", auth: { admin: true } },
  { route: "/admin/reports/questions", auth: { admin: true } },
  { route: "/admin/reports/wrong", auth: { admin: true } },
  { route: "/admin/reports/absent", auth: { admin: true } },
  { route: "/admin/operations", auth: { admin: true } },
];

for (const viewport of portraitViewports()) {
  for (const entry of authRoutes) {
    test(`auth canvas ${entry.route} at ${viewport.name}`, async ({ page }, testInfo) => {
      await setDeterministicViewport(page, viewport);
      const problems = collectRuntimeProblems(page);
      const fixture = await gotoVisualRoute(
        page,
        entry.admin ? OPERATOR_URL : CANDIDATE_URL,
        entry.route,
        entry.auth,
        entry.state,
      );
      if (entry.route === "/login") {
        await page.getByRole("button", { name: "发送验证码" }).click();
        await expect(page.getByText("请输入邮箱")).toBeVisible();
        await page.getByLabel("邮箱").fill("visual.candidate@example.test");
        await page.getByRole("button", { name: "发送验证码" }).click();
        await expect(page.getByLabel("邮箱")).toHaveAttribute("disabled", "");
      }
      await assertVisualContract(page, testInfo, "auth", entry.route, viewport, fixture, problems);
    });
  }

  for (const entry of candidateRoutes) {
    test(`candidate calm ${entry.route} at ${viewport.name}`, async ({ page }, testInfo) => {
      await setDeterministicViewport(page, viewport);
      const problems = collectRuntimeProblems(page);
      const fixture = await gotoVisualRoute(page, CANDIDATE_URL, entry.route, entry.auth);
      if (viewport.width < 1024) {
        const menu = page.getByRole("button", { name: "打开菜单" });
        await expect(menu).toBeVisible();
        await menu.click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
        await page.getByRole("button", { name: "关闭" }).click();
        await expect(page.getByRole("dialog")).toBeHidden();
      } else {
        await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
      }
      await assertVisualContract(
        page,
        testInfo,
        "candidate",
        entry.route,
        viewport,
        fixture,
        problems,
      );
    });
  }

  for (const entry of adminRoutes) {
    test(`admin workbench ${entry.route} at ${viewport.name}`, async ({ page }, testInfo) => {
      await setDeterministicViewport(page, viewport);
      const problems = collectRuntimeProblems(page);
      const fixture = await gotoVisualRoute(
        page,
        OPERATOR_URL,
        entry.route,
        entry.auth,
        entry.state ?? "ready",
      );
      if (entry.state === "stale") {
        await page.getByRole("button", { name: "刷新工作台" }).click();
        await expect(page.getByText("工作台刷新失败")).toBeVisible();
      }
      if (viewport.width < 1024) {
        const menu = page.getByRole("button", { name: "打开菜单" });
        if (await menu.isVisible().catch(() => false)) {
          await menu.click();
          await expect(page.getByRole("dialog")).toBeVisible();
          await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
          await page.getByRole("button", { name: "关闭" }).click();
          await expect(page.getByRole("dialog")).toBeHidden();
        }
      } else {
        await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
      }
      await assertVisualContract(page, testInfo, "admin", entry.route, viewport, fixture, problems);
    });
  }

  test(`exam focus ready at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = `/exams/${VISUAL_EXAM_ID}/taking?attemptId=${VISUAL_ATTEMPT_ID}`;
    const fixture = await gotoVisualRoute(page, CANDIDATE_URL, route, {
      candidate: true,
      attempt: true,
    });
    await expect(page.locator('[data-testid="exam-question-heading"]:visible')).toBeVisible();
    await expect(page.getByTestId("exam-save-status")).toContainText("已保存");
    await assertExamFocusNavigation(page, viewport);
    await assertVisualContract(page, testInfo, "focus", route, viewport, fixture, problems);
  });
}

for (const viewport of VISUAL_LANDSCAPE_VIEWPORTS) {
  test(`exam focus landscape ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = `/exams/${VISUAL_EXAM_ID}/taking?attemptId=${VISUAL_ATTEMPT_ID}`;
    const fixture = await gotoVisualRoute(page, CANDIDATE_URL, route, {
      candidate: true,
      attempt: true,
    });
    await expect(page.locator('[data-testid="exam-question-heading"]:visible')).toBeVisible();
    await assertExamFocusNavigation(page, viewport);
    await assertVisualContract(page, testInfo, "focus", route, viewport, fixture, problems);
  });
}

test("exam focus exposes saving, saved, offline, conflict, and submitted states", async ({
  page,
}, testInfo) => {
  const viewport = VISUAL_VIEWPORTS[1];
  await setDeterministicViewport(page, viewport);
  const route = `/exams/${VISUAL_EXAM_ID}/taking?attemptId=${VISUAL_ATTEMPT_ID}`;
  const stateChecks: Array<{
    state: VisualRouteState;
    text: RegExp | string;
    offline?: boolean;
    attemptStatus?: "in_progress" | "submitted" | "auto_submitted";
  }> = [
    { state: "saved", text: "答案已保存" },
    { state: "saving", text: "正在保存" },
    { state: "conflict", text: "答案版本冲突" },
    { state: "offline", text: "网络中断，答案待同步", offline: true },
    { state: "submitted", text: "考试已交卷", attemptStatus: "submitted" },
    { state: "auto-submitted", text: "考试已交卷", attemptStatus: "auto_submitted" },
  ];
  for (const check of stateChecks) {
    await page.goto("about:blank");
    const problems = collectRuntimeProblems(page);
    const fixture = await gotoVisualRoute(
      page,
      CANDIDATE_URL,
      route,
      { candidate: true, attempt: true },
      check.state,
      check.attemptStatus,
    );
    if (check.offline) {
      await setVisualOffline(page);
    }
    if (check.state === "saving" || check.state === "conflict") {
      const option = page.getByRole("radio").first();
      await option.click();
      await page.waitForTimeout(200);
    }
    await expect(page.getByText(check.text).first()).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await assertCompactLabels(page);
    await assertRequiredActionAndFocus(page);
    await captureVisual(testInfo, page, "focus", `${route}-${check.state}`, viewport);
    await assertNoRuntimeProblems(page, problems, fixture);
    if (check.offline) await setVisualOffline(page, false);
  }
});

test("visual-system reduced-motion and 200-percent zoom spot checks keep focus visible", async ({
  page,
}, testInfo) => {
  const viewport = VISUAL_VIEWPORTS[1];
  await setDeterministicViewport(page, viewport, true);
  const problems = collectRuntimeProblems(page);
  const route = `/exams/${VISUAL_EXAM_ID}/taking?attemptId=${VISUAL_ATTEMPT_ID}`;
  const fixture = await gotoVisualRoute(page, CANDIDATE_URL, route, {
    candidate: true,
    attempt: true,
  });
  await expect(page.locator("[aria-label^='剩余时间']:visible")).toBeVisible();
  const reducedMotion = await page.evaluate(() => {
    const timer = [...document.querySelectorAll<HTMLElement>("[aria-label^='剩余时间']")].find(
      (candidate) => {
        const rect = candidate.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      },
    );
    return timer ? getComputedStyle(timer).animationDuration : "";
  });
  expect(reducedMotion === "0s" || reducedMotion === "").toBeTruthy();
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Emulation.setPageScaleFactor", { pageScaleFactor: 2 });
  await assertNoHorizontalOverflow(page);
  await assertCompactLabels(page);
  await assertRequiredActionAndFocus(page);
  await captureVisual(testInfo, page, "focus", `${route}-zoom-200-reduced-motion`, viewport);
  await assertNoRuntimeProblems(page, problems, fixture);
});
