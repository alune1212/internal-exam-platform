import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));

vi.mock("@/api/client", () => ({ apiRequest }));

import { getWrongPracticeQuestions } from "@/api/questions";

describe("practice question API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiRequest.mockResolvedValue([]);
  });

  it("sends bounded pagination defaults", async () => {
    await getWrongPracticeQuestions();

    expect(apiRequest).toHaveBeenCalledWith(
      "/api/practice/wrong-questions?limit=50&offset=0&history_limit=20",
    );
  });

  it("clamps page and history sizes while preserving filters", async () => {
    await getWrongPracticeQuestions({
      category_1: "安全与账号",
      mastered: false,
      limit: 101,
      offset: -2,
      history_limit: 0,
    });

    expect(apiRequest).toHaveBeenCalledWith(
      "/api/practice/wrong-questions?category_1=%E5%AE%89%E5%85%A8%E4%B8%8E%E8%B4%A6%E5%8F%B7&mastered=false&limit=100&offset=0&history_limit=1",
    );
  });
});
