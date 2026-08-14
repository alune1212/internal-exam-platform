import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ExamContextNav, getExamContextDestinations } from "@/components/admin/ExamContextNav";

function renderNav(initialPath = "/admin/exams/1") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ExamContextNav examId="1" examTitle="安全知识竞赛" />
    </MemoryRouter>,
  );
}

describe("ExamContextNav", () => {
  it("exposes only existing exam-scoped destinations", () => {
    renderNav();

    expect(screen.getByTestId("exam-context-identity")).toHaveTextContent("安全知识竞赛");
    expect(screen.getByRole("link", { name: "考试工作台" })).toHaveAttribute(
      "href",
      "/admin/exams/1",
    );
    expect(screen.getByRole("link", { name: "考试编排" })).toHaveAttribute(
      "href",
      "/admin/exams/1/edit",
    );
    expect(screen.getByRole("link", { name: "名单与授权" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates",
    );
    expect(screen.getByRole("link", { name: "邀请投递" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates#invitation-actions",
    );
    expect(screen.getByRole("link", { name: "成绩册" })).toHaveAttribute(
      "href",
      "/admin/reports/scores?exam_id=1",
    );
    expect(screen.getByRole("link", { name: "错题回看" })).toHaveAttribute(
      "href",
      "/admin/reports/wrong?exam_id=1",
    );

    const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    expect(hrefs).not.toContainEqual(expect.stringContaining("monitor"));
    expect(hrefs).not.toContainEqual(expect.stringContaining("/admin/exams/1/monitor"));
  });

  it("marks exactly one current destination and changes roster state for invitations", () => {
    const { unmount } = renderNav("/admin/exams/1/candidates");
    expect(screen.getByRole("link", { name: "名单与授权" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "邀请投递" })).not.toHaveAttribute("aria-current");

    unmount();
    renderNav("/admin/exams/1/candidates#invitation-actions");
    expect(screen.getByRole("link", { name: "邀请投递" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "名单与授权" })).not.toHaveAttribute("aria-current");
  });

  it("keeps the destination model typed and ordered", () => {
    expect(getExamContextDestinations("exam/1").map(({ id }) => id)).toEqual([
      "workspace",
      "configuration",
      "roster",
      "invitations",
      "results",
      "review",
    ]);
  });

  it("keeps context links keyboard focusable", async () => {
    const user = userEvent.setup();
    renderNav();

    const configuration = screen.getByRole("link", { name: "考试编排" });
    configuration.focus();
    expect(document.activeElement).toBe(configuration);
    await user.keyboard("{Enter}");
    expect(configuration).toHaveAttribute("aria-current", "page");
  });
});
