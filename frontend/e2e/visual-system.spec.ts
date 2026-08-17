import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { Buffer } from "node:buffer";
import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";

import {
  CANDIDATE_URL,
  OPERATOR_URL,
  VISUAL_ATTEMPT_ID,
  VISUAL_EXAM_ID,
  VISUAL_LANDSCAPE_VIEWPORTS,
  VISUAL_LONG_IDENTIFIER,
  VISUAL_REPRESENTATIVE_GROUPS,
  VISUAL_REPRESENTATIVE_VIEWPORTS,
  VISUAL_VIEWPORTS,
  installVisualAuth,
  installVisualRoutes,
  setVisualOffline,
  type VisualAuthOptions,
  type VisualRouteHandle,
  type VisualRouteState,
  type VisualScenario,
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
  scenario: VisualScenario = "baseline",
  resultAnswersReleased?: boolean,
) {
  await installVisualAuth(page, {
    ...auth,
    longContent:
      auth.longContent ??
      (scenario === "long-content" ||
        scenario === "long-options" ||
        scenario === "question-form-open" ||
        scenario === "learning-video-controls"),
  });
  const fixture = await installVisualRoutes(page, {
    state,
    attemptStatus,
    scenario,
    resultAnswersReleased,
  });
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
    expect(headings).not.toContain(1);
    await expect(page.locator("[data-testid='exam-question-heading']:visible")).toHaveCount(1);
    await expect(page.locator("h2[data-testid='exam-question-heading']:visible")).toHaveCount(1);
    return;
  }
  expect(headings[0], `${family} must start its visible hierarchy at H1`).toBe(1);
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
    const overflowingContent: string[] = [];
    const hasHorizontalOverflowOwner = (element: HTMLElement) => {
      let ancestor = element.parentElement;
      while (ancestor && ancestor !== document.body) {
        const ancestorStyle = window.getComputedStyle(ancestor);
        if (
          ["auto", "scroll", "hidden", "clip"].includes(ancestorStyle.overflowX) &&
          ancestor.scrollWidth > ancestor.clientWidth + 1
        ) {
          return true;
        }
        ancestor = ancestor.parentElement;
      }
      return false;
    };
    document.querySelectorAll<HTMLElement>("body *").forEach((element) => {
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden") return;
      const rect = element.getBoundingClientRect();
      if (
        element.scrollWidth > element.clientWidth + 1 &&
        !["auto", "scroll", "hidden", "clip"].includes(style.overflowX)
      ) {
        overflowingContent.push(
          `${element.scrollWidth}/${element.clientWidth} ${element.tagName.toLowerCase()}.${element.className}`.slice(
            0,
            200,
          ),
        );
      }
      if (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.right > viewportRight &&
        !hasHorizontalOverflowOwner(element)
      ) {
        outOfBounds.push(
          `${style.position}:${Math.round(rect.left)}..${Math.round(rect.right)} ${element.tagName.toLowerCase()}.${element.className}`.slice(
            0,
            200,
          ),
        );
      }
    });
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      outOfBounds: outOfBounds.slice(0, 5),
      overflowingContent: overflowingContent.slice(-5),
    };
  });
  expect(
    result.scrollWidth,
    `root overflow: bounds=${JSON.stringify(result.outOfBounds)} content=${JSON.stringify(result.overflowingContent)}`,
  ).toBeLessThanOrEqual(result.clientWidth + 1);
  expect(result.outOfBounds, "visible content must stay within the viewport").toEqual([]);
}

async function assertFamilyChrome(page: Page, family: Family) {
  if (family === "auth") {
    await expect(page.locator("[data-auth-canvas]:visible")).toHaveCount(1);
    await expect(page.locator("[data-navigation-family]:visible")).toHaveCount(0);
    return;
  }

  if (family === "focus") {
    await expect(page.locator("[data-exam-workspace]:visible")).toHaveCount(1);
    await expect(page.locator("[data-navigation-family]:visible")).toHaveCount(0);
    return;
  }

  await expect(page.locator(`[data-navigation-family='${family}']:visible`)).toHaveCount(1);
}

async function assertTouchTargets(page: Page, viewport: Viewport, family: Family) {
  if (family !== "focus" || viewport.width > 768) return;
  const targets = await page
    .locator(
      "[data-exam-question-workspace] button[role='radio'], [data-exam-question-workspace] button[role='checkbox'], [data-exam-workspace] button",
    )
    .evaluateAll((nodes) =>
      nodes
        .filter((node) => {
          const style = window.getComputedStyle(node);
          const rect = (node as HTMLElement).getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0;
        })
        .map((node) => {
          const rect = (node as HTMLElement).getBoundingClientRect();
          return {
            label: (node as HTMLElement).getAttribute("aria-label") ?? node.textContent?.trim(),
            width: rect.width,
            height: rect.height,
          };
        }),
    );
  expect(targets.length, "Exam Focus should expose touch targets").toBeGreaterThan(0);
  expect(
    targets.filter(({ width, height }) => width < 44 || height < 44),
    `Exam Focus targets must be at least 44 CSS pixels: ${JSON.stringify(targets)}`,
  ).toEqual([]);
}

async function assertRadioAndCheckboxFlow(page: Page) {
  const radioGroup = page.getByRole("radiogroup");
  await expect(radioGroup).toBeVisible();
  const radios = page.getByRole("radio");
  expect(await radios.count()).toBeGreaterThanOrEqual(2);
  await radios.first().focus();
  const before = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  await page.keyboard.press("ArrowRight");
  const after = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(after).not.toBe(before);

  const next = page.getByRole("button", { name: "下一题" });
  if (await next.isVisible().catch(() => false)) {
    await next.click();
    const checkboxGroup = page.getByRole("group").filter({ has: page.getByRole("checkbox") });
    if (await checkboxGroup.isVisible().catch(() => false)) {
      const checkboxes = page.getByRole("checkbox");
      expect(await checkboxes.count()).toBeGreaterThanOrEqual(2);
      await checkboxes.first().focus();
      await page.keyboard.press("Space");
      await expect(checkboxes.first()).toHaveAttribute("aria-checked", "true");
    }
  }
}

async function assertOverlayReachability(
  page: Page,
  selector = "[role='dialog']",
  requireScroll = false,
) {
  const overlay = page.locator(selector).filter({ visible: true }).last();
  await expect(overlay).toBeVisible();
  const metrics = await overlay.evaluate((element) => {
    const style = window.getComputedStyle(element);
    const focusable = element.querySelectorAll<HTMLElement>(
      "button, a[href], input, textarea, select, [tabindex]:not([tabindex='-1'])",
    );
    return {
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
      overflowY: style.overflowY,
      maxHeight: style.maxHeight,
      focusable: focusable.length,
    };
  });
  expect(metrics.focusable, "overlay controls must remain keyboard reachable").toBeGreaterThan(0);
  expect(["auto", "scroll"], "overlay must own internal scrolling").toContain(metrics.overflowY);
  if (requireScroll) {
    expect(
      metrics.scrollHeight,
      "long overlay content must be internally scrollable",
    ).toBeGreaterThan(metrics.clientHeight);
  } else {
    expect(metrics.scrollHeight).toBeGreaterThanOrEqual(metrics.clientHeight);
  }
  return overlay;
}

async function assertMobileNavigation(page: Page, family: "candidate" | "admin") {
  const menu = page.getByRole("button", { name: "打开菜单" });
  await expect(menu).toBeVisible();
  await menu.click();
  const navigation = await assertOverlayReachability(page);
  await expect(navigation.getByRole("button", { name: "退出登录" })).toBeVisible();
  const navLinks = navigation.locator("a[href]");
  expect(
    await navLinks.count(),
    `${family} navigation should preserve destinations`,
  ).toBeGreaterThan(0);
  return navigation;
}

async function assertSafeAreaHooks(page: Page, family: Family, viewport: Viewport) {
  if (family !== "focus" || viewport.width > 768) return async () => {};

  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Emulation.setSafeAreaInsetsOverride", {
    insets: { top: 0, right: 0, bottom: 34, left: 0 },
  });
  const metrics = await page
    .locator("[class*='safe-area-inset-bottom']:visible")
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const element = node as HTMLElement;
        const rect = element.getBoundingClientRect();
        return {
          paddingBottom: Number.parseFloat(window.getComputedStyle(element).paddingBottom),
          bottom: rect.bottom,
          viewportHeight: window.innerHeight,
        };
      }),
    );
  expect(metrics.length, "Exam Focus should expose a visible safe-area owner").toBeGreaterThan(0);
  expect(
    metrics.some(
      ({ paddingBottom, bottom, viewportHeight }) =>
        paddingBottom >= 34 && bottom <= viewportHeight + 1,
    ),
    `Exam Focus controls must clear the injected safe area: ${JSON.stringify(metrics)}`,
  ).toBeTruthy();

  return async () => {
    await cdp.send("Emulation.setSafeAreaInsetsOverride", { insets: {} });
    await cdp.detach();
  };
}

function resolveRepresentativeRoute(route: string) {
  return route
    .replace(":examId", String(VISUAL_EXAM_ID))
    .replace(":attemptId", String(VISUAL_ATTEMPT_ID));
}

async function assertResultReleaseState(page: Page, released: boolean) {
  if (released) {
    await expect(page.getByTestId("result-review")).toBeVisible();
    await expect(page.getByText("正确答案").first()).toBeVisible();
    await expect(page.getByText("答案与解析尚未发布。")).toHaveCount(0);
    return;
  }

  await expect(page.getByTestId("result-release-gate")).toBeVisible();
  await expect(page.getByText("答案与解析尚未发布。")).toBeVisible();
  await expect(page.getByText("正确答案")).toHaveCount(0);
  await expect(page.getByText("焦点、状态和操作都需要被看见。")).toHaveCount(0);
}

async function assertQuestionFormOpenState(page: Page, pending: boolean, requireScroll = false) {
  const form = page.locator("[data-question-form]");
  await expect(form).toBeVisible();
  const dialog = await assertOverlayReachability(page, "[role='dialog']", requireScroll);
  await expect(dialog.getByRole("heading", { name: /题目/ }).first()).toBeVisible();
  await expect(dialog.getByLabel("题干")).toBeVisible();
  if (pending) {
    await expect(form).toHaveAttribute("aria-busy", "true");
    await expect(dialog.getByRole("button", { name: /保存/ }).last()).toBeDisabled();
  }
}

async function assertLearningVideoControlState(page: Page, requireScroll: boolean) {
  const fileInput = page.locator("input[type='file'][aria-label='选择视频文件']");
  await expect(fileInput).toHaveCount(1);
  const fileTrigger = page.getByRole("button", { name: "选择视频文件" });
  await expect(fileTrigger).toBeVisible();
  await expect(fileTrigger).toBeEnabled();
  await fileTrigger.focus();
  await expect(fileTrigger).toBeFocused();
  const selectedFileName = `培训视频-${VISUAL_LONG_IDENTIFIER}.mp4`;
  await fileInput.setInputFiles({
    name: selectedFileName,
    mimeType: "video/mp4",
    buffer: Buffer.from("visual-system-video-fixture"),
  });
  await expect(page.locator("#learning-video-file-status")).toContainText(selectedFileName);

  const edit = page.getByRole("button", { name: "编辑" }).first();
  await expect(edit).toBeVisible();
  await edit.click();
  const dialog = await assertOverlayReachability(page, "[role='dialog']", requireScroll);
  await expect(dialog.getByRole("heading", { name: "编辑视频信息" })).toBeVisible();
  await expect(dialog.getByLabel("视频标题")).toBeVisible();
}

const representativeGroup = (id: (typeof VISUAL_REPRESENTATIVE_GROUPS)[number]["id"]) =>
  VISUAL_REPRESENTATIVE_GROUPS.find((group) => group.id === id)!;

for (const viewport of VISUAL_REPRESENTATIVE_VIEWPORTS) {
  const loginGroup = representativeGroup("candidate-login");
  test(`representative ${loginGroup.id} at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(loginGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      CANDIDATE_URL,
      route,
      {},
      "ready",
      undefined,
      "long-content",
    );
    await page.getByLabel("邮箱").fill(`${VISUAL_LONG_IDENTIFIER.toLowerCase()}@example.test`);
    await page.getByRole("button", { name: "发送验证码" }).click();
    await expect(page.getByLabel("验证码")).toBeVisible();
    await assertVisualContract(page, testInfo, "auth", route, viewport, fixture, problems);
  });

  const examListGroup = representativeGroup("exam-list");
  test(`representative ${examListGroup.id} at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(examListGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      CANDIDATE_URL,
      route,
      { candidate: true },
      "ready",
      undefined,
      "long-content",
    );
    if (viewport.width < 1024) {
      const navigation = await assertMobileNavigation(page, "candidate");
      await navigation.getByRole("button", { name: "关闭" }).click();
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    } else {
      await expect(page.getByRole("navigation", { name: "候选人导航" })).toBeVisible();
      await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
    }
    await assertVisualContract(page, testInfo, "candidate", route, viewport, fixture, problems);
  });

  const focusGroup = representativeGroup("active-formal-exam");
  test(`representative ${focusGroup.id} long options at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(focusGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      CANDIDATE_URL,
      route,
      { candidate: true, attempt: true },
      "ready",
      undefined,
      "long-options",
    );
    await expect(page.getByTestId("exam-save-status")).toHaveText("答案已保存");
    await expect(page.getByRole("radio").first()).toContainText(VISUAL_LONG_IDENTIFIER);
    await assertRadioAndCheckboxFlow(page);
    if (viewport.width < 1024) {
      const trigger = page.getByRole("button", { name: "打开题号导航" });
      await trigger.click();
      await assertOverlayReachability(page);
      await page.getByRole("button", { name: "关闭" }).click();
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    }
    await assertVisualContract(page, testInfo, "focus", route, viewport, fixture, problems);
  });

  const resultGroup = representativeGroup("result");
  for (const released of [true, false]) {
    test(`representative ${resultGroup.id} ${released ? "released" : "unreleased"} at ${viewport.name}`, async ({
      page,
    }, testInfo) => {
      await setDeterministicViewport(page, viewport);
      const problems = collectRuntimeProblems(page);
      const route = resolveRepresentativeRoute(resultGroup.route);
      const fixture = await gotoVisualRoute(
        page,
        CANDIDATE_URL,
        route,
        { candidate: true },
        "ready",
        undefined,
        released ? "long-content" : "result-unreleased",
        released,
      );
      await assertResultReleaseState(page, released);
      await assertVisualContract(page, testInfo, "candidate", route, viewport, fixture, problems);
    });
  }

  const dashboardGroup = representativeGroup("admin-dashboard");
  test(`representative ${dashboardGroup.id} at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(dashboardGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      OPERATOR_URL,
      route,
      { admin: true },
      "ready",
      undefined,
      "long-content",
    );
    if (viewport.width < 1024) {
      const navigation = await assertMobileNavigation(page, "admin");
      await navigation.getByRole("button", { name: "关闭" }).click();
      await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    } else {
      await expect(page.getByTestId("admin-desktop-rail")).toBeVisible();
      await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
    }
    await assertVisualContract(page, testInfo, "admin", route, viewport, fixture, problems);
  });

  const questionGroup = representativeGroup("question-form");
  test(`representative ${questionGroup.id} open pending state at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(questionGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      OPERATOR_URL,
      route,
      { admin: true },
      "saving",
      undefined,
      "question-form-open",
    );
    await page.getByRole("button", { name: "编辑" }).first().click();
    await assertQuestionFormOpenState(page, false, viewport.width < 1024);
    await page.getByLabel("题干").fill(`${VISUAL_LONG_IDENTIFIER}${VISUAL_LONG_IDENTIFIER}`);
    await page.getByRole("button", { name: "保存" }).last().click();
    await assertQuestionFormOpenState(page, true, viewport.width < 1024);
    if (viewport.width < 1024) {
      const dialog = page.getByRole("dialog");
      await dialog.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
      await expect(page.getByLabel("选项 F 内容")).toBeVisible();
    }
    await assertVisualContract(page, testInfo, "admin", route, viewport, fixture, problems);
  });

  const reportGroup = representativeGroup("score-report");
  test(`representative ${reportGroup.id} at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(reportGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      OPERATOR_URL,
      route,
      { admin: true },
      "ready",
      undefined,
      "long-content",
    );
    await expect(page.getByRole("button", { name: /导出/ })).toBeVisible();
    await expect(page.getByText(VISUAL_LONG_IDENTIFIER).first()).toBeVisible();
    await assertVisualContract(page, testInfo, "admin", route, viewport, fixture, problems);
  });
}

for (const viewport of VISUAL_REPRESENTATIVE_VIEWPORTS) {
  const focusGroup = representativeGroup("active-formal-exam");
  test(`representative ${focusGroup.id} guarded exit at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(focusGroup.route);
    const fixture = await gotoVisualRoute(
      page,
      CANDIDATE_URL,
      route,
      { candidate: true, attempt: true },
      "saving",
      undefined,
      "attempt-exit",
    );
    const option = page.getByRole("radio").first();
    await option.click();
    await expect(page.getByTestId("exam-save-status")).toHaveText(/^(待保存|正在保存答案)$/);
    await page.getByRole("button", { name: "返回考试列表" }).click();
    const warning = page.getByRole("alertdialog");
    await expect(warning).toBeVisible();
    await expect(warning).toContainText("答案尚未同步");
    await expect(page.getByRole("button", { name: "留在考试" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(warning).toBeHidden();
    await expect(page.getByRole("button", { name: "返回考试列表" })).toBeFocused();
    await assertVisualContract(page, testInfo, "focus", route, viewport, fixture, problems);
  });
}

for (const viewport of VISUAL_REPRESENTATIVE_VIEWPORTS) {
  test(`representative learning-video controls at ${viewport.name}`, async ({ page }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = "/admin/learning";
    const fixture = await gotoVisualRoute(
      page,
      OPERATOR_URL,
      route,
      { admin: true },
      "ready",
      undefined,
      "learning-video-controls",
    );
    await assertLearningVideoControlState(page, false);
    await assertVisualContract(page, testInfo, "admin", route, viewport, fixture, problems);
  });
}

for (const viewport of VISUAL_LANDSCAPE_VIEWPORTS) {
  test(`representative learning-video controls landscape ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await setDeterministicViewport(page, viewport);
    const problems = collectRuntimeProblems(page);
    const route = "/admin/learning";
    const fixture = await gotoVisualRoute(
      page,
      OPERATOR_URL,
      route,
      { admin: true },
      "ready",
      undefined,
      "learning-video-controls",
    );
    await assertLearningVideoControlState(page, true);
    await assertVisualContract(page, testInfo, "admin", route, viewport, fixture, problems);
  });
}

for (const viewport of VISUAL_LANDSCAPE_VIEWPORTS) {
  for (const group of VISUAL_REPRESENTATIVE_GROUPS) {
    test(`representative ${group.id} landscape ${viewport.name}`, async ({ page }, testInfo) => {
      await setDeterministicViewport(page, viewport);
      const problems = collectRuntimeProblems(page);
      const route = resolveRepresentativeRoute(group.route);
      const host = group.family === "admin" ? OPERATOR_URL : CANDIDATE_URL;
      const auth: VisualAuthOptions =
        group.family === "admin"
          ? { admin: true }
          : group.family === "focus"
            ? { candidate: true, attempt: true }
            : group.family === "candidate"
              ? { candidate: true }
              : {};
      const scenario: VisualScenario =
        group.id === "active-formal-exam"
          ? "long-options"
          : group.id === "question-form"
            ? "question-form-open"
            : group.id === "result"
              ? "result-released"
              : "long-content";
      const fixture = await gotoVisualRoute(
        page,
        host,
        route,
        auth,
        "ready",
        undefined,
        scenario,
        true,
      );

      if (group.id === "candidate-login") {
        await expect(page.locator("[data-auth-canvas]:visible")).toHaveCount(1);
      } else if (group.id === "exam-list") {
        const navigation = await assertMobileNavigation(page, "candidate");
        await navigation.getByRole("button", { name: "关闭" }).click();
        await expect(page.locator('[role="dialog"]')).toHaveCount(0);
      } else if (group.id === "active-formal-exam") {
        await expect(page.getByRole("radio").first()).toContainText(VISUAL_LONG_IDENTIFIER);
        await assertRadioAndCheckboxFlow(page);
      } else if (group.id === "result") {
        await assertResultReleaseState(page, true);
      } else if (group.id === "admin-dashboard") {
        const navigation = await assertMobileNavigation(page, "admin");
        await navigation.getByRole("button", { name: "关闭" }).click();
        await expect(page.locator('[role="dialog"]')).toHaveCount(0);
      } else if (group.id === "question-form") {
        await page.getByRole("button", { name: "编辑" }).first().click();
        await assertQuestionFormOpenState(page, false, viewport.width < 1024);
      } else if (group.id === "score-report") {
        await expect(page.getByRole("button", { name: /导出/ })).toBeVisible();
      }
      await assertVisualContract(page, testInfo, group.family, route, viewport, fixture, problems);
    });
  }
}

for (const group of VISUAL_REPRESENTATIVE_GROUPS) {
  test(`representative ${group.id} reduced motion and 200 percent zoom`, async ({
    page,
  }, testInfo) => {
    const viewport = VISUAL_REPRESENTATIVE_VIEWPORTS[1];
    await setDeterministicViewport(page, viewport, true);
    const problems = collectRuntimeProblems(page);
    const route = resolveRepresentativeRoute(group.route);
    const host = group.family === "admin" ? OPERATOR_URL : CANDIDATE_URL;
    const auth: VisualAuthOptions =
      group.family === "admin"
        ? { admin: true }
        : group.family === "focus" || group.family === "candidate"
          ? { candidate: true, ...(group.family === "focus" ? { attempt: true } : {}) }
          : {};
    const scenario: VisualScenario =
      group.id === "active-formal-exam"
        ? "long-options"
        : group.id === "result"
          ? "result-unreleased"
          : group.id === "question-form"
            ? "question-form-open"
            : "long-content";
    const fixture = await gotoVisualRoute(
      page,
      host,
      route,
      auth,
      "ready",
      undefined,
      scenario,
      false,
    );

    if (group.id === "exam-list" || group.id === "admin-dashboard" || group.id === "score-report") {
      const navigation =
        group.family === "admin"
          ? await assertMobileNavigation(page, "admin")
          : group.id === "exam-list"
            ? await assertMobileNavigation(page, "candidate")
            : null;
      if (navigation) await navigation.getByRole("button", { name: "关闭" }).click();
      if (navigation) await expect(page.locator('[role="dialog"]')).toHaveCount(0);
    } else if (group.id === "active-formal-exam") {
      await expect(page.getByRole("radio").first()).toBeVisible();
    } else if (group.id === "question-form") {
      await page.getByRole("button", { name: "编辑" }).first().click();
      await assertQuestionFormOpenState(page, false, viewport.width < 1024);
    } else if (group.id === "result") {
      await assertResultReleaseState(page, false);
    } else if (group.id === "candidate-login") {
      await expect(page.getByRole("button", { name: "发送验证码" })).toBeVisible();
    }

    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setPageScaleFactor", { pageScaleFactor: 2 });
    const motion = await page.evaluate(
      () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    );
    expect(motion).toBeTruthy();
    await assertVisualContract(page, testInfo, group.family, route, viewport, fixture, problems);
  });
}

async function assertCompactLabels(page: Page) {
  const violations = await page
    .locator(
      "button:not([role='radio']):not([role='checkbox']), [data-action-group] a, [data-navigation-family] a:not([aria-label='打开账号资料']):not([aria-label*='首页']), [data-testid='exam-context-links'] a, [role='tab'], [role='menuitem']",
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
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        const lineTops: number[] = [];
        let textNode = walker.nextNode();
        while (textNode) {
          if (textNode.textContent?.trim()) {
            const range = document.createRange();
            range.selectNodeContents(textNode);
            for (const textRect of range.getClientRects()) {
              if (textRect.width > 0 && textRect.height > 0) lineTops.push(textRect.top);
            }
          }
          textNode = walker.nextNode();
        }
        const distinctLines = lineTops
          .sort((left, right) => left - right)
          .filter((top, index, values) => index === 0 || Math.abs(top - values[index - 1]) > 1);
        if (distinctLines.length > 1) {
          result.push(`${text.slice(0, 40)} (${distinctLines.length} lines)`);
        }
      });
      return result;
    });
  expect(violations, "compact action labels must remain one line").toEqual([]);

  const reflowViolations = await page.locator("[data-action-group]").evaluateAll((groups) => {
    const result: string[] = [];
    groups.forEach((group) => {
      const element = group as HTMLElement;
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden" || rect.width === 0) return;
      const reflow = element.dataset.actionReflow;
      if (reflow === "wrap" && style.flexWrap !== "wrap") {
        result.push(`${element.getAttribute("aria-label") ?? "action group"}: no wrap`);
      }
      if (reflow === "stack" && window.innerWidth < 640 && style.flexDirection !== "column") {
        result.push(`${element.getAttribute("aria-label") ?? "action group"}: no stack`);
      }
      const childRects = [...element.children]
        .map((child) => (child as HTMLElement).getBoundingClientRect())
        .filter((childRect) => childRect.width > 0 && childRect.height > 0);
      childRects.forEach((childRect) => {
        if (childRect.left < rect.left - 1 || childRect.right > rect.right + 1) {
          result.push(`${element.getAttribute("aria-label") ?? "action group"}: child overflow`);
        }
      });
      for (let left = 0; left < childRects.length; left += 1) {
        for (let right = left + 1; right < childRects.length; right += 1) {
          const first = childRects[left];
          const second = childRects[right];
          const overlaps =
            Math.min(first.right, second.right) - Math.max(first.left, second.left) > 1 &&
            Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top) > 1;
          if (overlaps) {
            result.push(`${element.getAttribute("aria-label") ?? "action group"}: overlap`);
          }
        }
      }
    });
    return result;
  });
  expect(reflowViolations, "action groups must reflow without overflow or overlap").toEqual([]);
}

async function assertRequiredActionAndFocus(page: Page) {
  const actions = page.locator("button:not([disabled]):visible, a[href]:visible");
  await expect(actions.first()).toBeVisible();
  const actionInsideViewport = await actions.evaluateAll((nodes) =>
    nodes.some((node) => {
      const element = node as HTMLElement;
      if (element.closest('[aria-hidden="true"], [inert]')) return false;
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
  const initiallyCoveredActions = await actions.evaluateAll((nodes) =>
    nodes.flatMap((node, index) => {
      const element = node as HTMLElement;
      if (element.closest('[aria-hidden="true"], [inert]')) return [];
      const rect = element.getBoundingClientRect();
      const visibleLeft = Math.max(rect.left, 0);
      const visibleRight = Math.min(rect.right, window.innerWidth);
      const visibleTop = Math.max(rect.top, 0);
      const visibleBottom = Math.min(rect.bottom, window.innerHeight);
      const visibleWidth = visibleRight - visibleLeft;
      const visibleHeight = visibleBottom - visibleTop;
      const minimumVisibleWidth = Math.min(rect.width, 24);
      const minimumVisibleHeight = Math.min(rect.height, 24);
      if (visibleWidth < minimumVisibleWidth - 1 || visibleHeight < minimumVisibleHeight - 1) {
        return [];
      }

      const xRatios = [0.5, 0.25, 0.75];
      const yRatios = [0.5, 0.1, 0.3, 0.7, 0.9];
      const hasUncoveredPoint = xRatios.some((xRatio) =>
        yRatios.some((yRatio) => {
          const x = visibleLeft + (visibleRight - visibleLeft) * xRatio;
          const y = visibleTop + (visibleBottom - visibleTop) * yRatio;
          const target = document.elementFromPoint(x, y);
          return Boolean(target && (target === element || element.contains(target)));
        }),
      );
      if (hasUncoveredPoint) return [];
      return [
        {
          index,
          label:
            element.getAttribute("aria-label") ??
            element.textContent?.trim().slice(0, 40) ??
            "action",
        },
      ];
    }),
  );
  const coveredActions: string[] = [];
  for (const { index, label } of initiallyCoveredActions) {
    const reachableAfterScroll = await actions.nth(index).evaluate(async (node) => {
      const element = node as HTMLElement;
      const scrollingAncestors: Array<{ element: HTMLElement; left: number; top: number }> = [];
      let ancestor = element.parentElement;
      while (ancestor) {
        if (
          ancestor.scrollHeight > ancestor.clientHeight ||
          ancestor.scrollWidth > ancestor.clientWidth
        ) {
          scrollingAncestors.push({
            element: ancestor,
            left: ancestor.scrollLeft,
            top: ancestor.scrollTop,
          });
        }
        ancestor = ancestor.parentElement;
      }
      const windowScroll = { left: window.scrollX, top: window.scrollY };

      try {
        element.scrollIntoView({ block: "center", inline: "nearest" });
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        });
        const rect = element.getBoundingClientRect();
        const visibleLeft = Math.max(rect.left, 0);
        const visibleRight = Math.min(rect.right, window.innerWidth);
        const visibleTop = Math.max(rect.top, 0);
        const visibleBottom = Math.min(rect.bottom, window.innerHeight);
        const xRatios = [0.5, 0.25, 0.75];
        const yRatios = [0.5, 0.1, 0.3, 0.7, 0.9];
        return xRatios.some((xRatio) =>
          yRatios.some((yRatio) => {
            const x = visibleLeft + (visibleRight - visibleLeft) * xRatio;
            const y = visibleTop + (visibleBottom - visibleTop) * yRatio;
            const target = document.elementFromPoint(x, y);
            return Boolean(target && (target === element || element.contains(target)));
          }),
        );
      } finally {
        scrollingAncestors.forEach(({ element: scrollElement, left, top }) => {
          scrollElement.scrollTo({ left, top });
        });
        window.scrollTo(windowScroll);
      }
    });
    if (!reachableAfterScroll) coveredActions.push(label);
  }
  expect(coveredActions, "visible required actions must not be covered").toEqual([]);

  let focusState = { focused: false, visibleRing: false };
  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press("Tab");
    focusState = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      if (!active || active === document.body) return { focused: false, visibleRing: false };
      const style = window.getComputedStyle(active);
      const rect = active.getBoundingClientRect();
      const visibleRing =
        active.matches(":focus-visible") &&
        (style.outlineStyle !== "none" ||
          Number.parseFloat(style.outlineWidth) > 0 ||
          style.boxShadow !== "none");
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
  await assertFamilyChrome(page, family);
  await assertHeadingOrder(page, family);
  await assertNoHorizontalOverflow(page);
  await assertCompactLabels(page);
  await assertRequiredActionAndFocus(page);
  await assertTouchTargets(page, viewport, family);
  const resetSafeArea = await assertSafeAreaHooks(page, family, viewport);
  await captureVisual(testInfo, page, family, route, viewport);
  await resetSafeArea();
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
    await expect(page.locator('[role="dialog"]')).toHaveCount(0);
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
        await expect(page.locator('[role="dialog"]')).toHaveCount(0);
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
          await expect(page.locator('[role="dialog"]')).toHaveCount(0);
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
    { state: "saving", text: "正在保存答案" },
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
      { candidate: true, attempt: true, draft: false },
      check.state,
      check.attemptStatus,
    );
    if (check.offline) {
      await setVisualOffline(page);
    }
    if (check.state === "saving" || check.state === "conflict") {
      const option = page.getByRole("radio").first();
      await option.click();
      await page.getByRole("button", { name: "保存答案" }).click();
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
