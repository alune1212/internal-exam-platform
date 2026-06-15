import { describe, expect, it } from "vitest";

import {
  QUESTION_TYPE_ORDER,
  buildQuestionNavItems,
  perTypeIndexOf,
  sortByType,
} from "./questionNavigation";

type TestQuestion = { id: number; question_type: string };

describe("QUESTION_TYPE_ORDER", () => {
  it("is 单选 → 多选 → 判断", () => {
    expect(QUESTION_TYPE_ORDER).toEqual(["single", "multiple", "judge"]);
  });
});

describe("sortByType", () => {
  it("orders questions as 单选 → 多选 → 判断 regardless of input order", () => {
    const input: TestQuestion[] = [
      { id: 1, question_type: "multiple" },
      { id: 2, question_type: "judge" },
      { id: 3, question_type: "single" },
      { id: 4, question_type: "multiple" },
      { id: 5, question_type: "judge" },
      { id: 6, question_type: "single" },
    ];
    const sorted = sortByType(input);
    expect(sorted.map((q) => q.question_type)).toEqual([
      "single",
      "single",
      "multiple",
      "multiple",
      "judge",
      "judge",
    ]);
    expect(sorted.map((q) => q.id)).toEqual([3, 6, 1, 4, 2, 5]);
  });

  it("does not mutate the input array", () => {
    const input: TestQuestion[] = [
      { id: 1, question_type: "multiple" },
      { id: 2, question_type: "single" },
    ];
    const before = input.map((q) => q.id);
    sortByType(input);
    expect(input.map((q) => q.id)).toEqual(before);
  });

  it("pushes unknown question types to the end", () => {
    const input: TestQuestion[] = [
      { id: 1, question_type: "essay" },
      { id: 2, question_type: "single" },
      { id: 3, question_type: "judge" },
    ];
    const sorted = sortByType(input);
    expect(sorted.map((q) => q.question_type)).toEqual(["single", "judge", "essay"]);
  });

  it("returns an empty array unchanged", () => {
    expect(sortByType<TestQuestion>([])).toEqual([]);
  });
});

describe("perTypeIndexOf", () => {
  const sorted: TestQuestion[] = [
    { id: 10, question_type: "single" },
    { id: 11, question_type: "single" },
    { id: 20, question_type: "multiple" },
    { id: 21, question_type: "multiple" },
    { id: 30, question_type: "judge" },
  ];

  it("returns the 1-based index within the same type group", () => {
    expect(perTypeIndexOf(sorted, 10)).toBe(1);
    expect(perTypeIndexOf(sorted, 11)).toBe(2);
    expect(perTypeIndexOf(sorted, 20)).toBe(1);
    expect(perTypeIndexOf(sorted, 21)).toBe(2);
    expect(perTypeIndexOf(sorted, 30)).toBe(1);
  });

  it("returns 0 for an unknown question id", () => {
    expect(perTypeIndexOf(sorted, 999)).toBe(0);
  });
});

describe("buildQuestionNavItems", () => {
  it("assigns per-type displayIndex (1, 2, ...) regardless of array order", () => {
    const questions: TestQuestion[] = [
      { id: 1, question_type: "multiple" },
      { id: 2, question_type: "judge" },
      { id: 3, question_type: "single" },
    ];
    const items = buildQuestionNavItems({
      questions,
      answers: { 1: "A", 3: "D" },
      getTargetId: () => "x",
    });
    expect(items.map((i) => ({ id: i.id, displayIndex: i.displayIndex, type: i.type }))).toEqual([
      { id: 1, displayIndex: 1, type: "multiple" },
      { id: 2, displayIndex: 1, type: "judge" },
      { id: 3, displayIndex: 1, type: "single" },
    ]);
    expect(items[0].answered).toBe(true);
    expect(items[1].answered).toBe(false);
    expect(items[2].answered).toBe(true);
  });
});
