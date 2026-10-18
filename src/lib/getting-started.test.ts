import { describe, expect, it } from "vitest";
import {
  getUseCase,
  isUseCaseId,
  nextUndoneStep,
  USE_CASE_IDS,
  USE_CASES,
  useCaseProgress,
} from "./getting-started";

const smallBusiness = getUseCase("small_business");

describe("useCaseProgress percent", () => {
  it("is 0 when nothing is done", () => {
    const progress = useCaseProgress(smallBusiness, new Set());
    expect(progress.doneCount).toBe(0);
    expect(progress.percent).toBe(0);
  });

  it("is 100 when every step is done", () => {
    const all = new Set(smallBusiness.steps.map((step) => step.source));
    const progress = useCaseProgress(smallBusiness, all);
    expect(progress.doneCount).toBe(progress.total);
    expect(progress.percent).toBe(100);
  });

  it("counts done steps as a whole percent", () => {
    const first = new Set([smallBusiness.steps[0]!.source]);
    expect(useCaseProgress(smallBusiness, first).percent).toBe(25);

    const threeOfFour = new Set(smallBusiness.steps.slice(0, 3).map((step) => step.source));
    expect(useCaseProgress(smallBusiness, threeOfFour).percent).toBe(75);
  });

  it("rounds to the nearest whole percent", () => {
    const marketing = getUseCase("marketing");
    const oneOfThree = new Set([marketing.steps[0]!.source]);
    expect(useCaseProgress(marketing, oneOfThree).percent).toBe(33);
  });

  it("counts a step as done only when its own source key is completed", () => {
    const wrongKey = new Set(["knowledge_added_by_mistake"]);
    expect(useCaseProgress(smallBusiness, wrongKey).doneCount).toBe(0);
  });
});

describe("useCaseProgress unknown source keys", () => {
  it("ignores keys that match no step", () => {
    const withExtras = new Set([
      "not_a_real_source",
      "channel_connected:tiktok",
      "widget_installed_later",
    ]);
    const progress = useCaseProgress(smallBusiness, withExtras);
    expect(progress.doneCount).toBe(0);
    expect(progress.percent).toBe(0);
    expect(progress.total).toBe(smallBusiness.steps.length);
  });

  it("does not change the percent when unknown keys are added", () => {
    const real = [smallBusiness.steps[1]!.source];
    const plain = useCaseProgress(smallBusiness, new Set(real));
    const padded = useCaseProgress(smallBusiness, new Set([...real, "unknown:key", "other"]));
    expect(padded.percent).toBe(plain.percent);
    expect(padded.doneCount).toBe(plain.doneCount);
  });

  it("marks a step unknown, not done, when the caller did not check its source", () => {
    const progress = useCaseProgress(smallBusiness, new Set(), new Set());
    expect(progress.steps.every((item) => item.status === "unknown")).toBe(true);
    expect(progress.percent).toBe(0);
  });

  it("marks a checked step not done, and a done step done", () => {
    const checked = new Set(smallBusiness.steps.map((step) => step.source));
    const done = new Set([smallBusiness.steps[0]!.source]);
    const progress = useCaseProgress(smallBusiness, done, checked);
    expect(progress.steps[0]!.status).toBe("done");
    expect(progress.steps[1]!.status).toBe("not_done");
  });
});

describe("use case definitions", () => {
  it("lists six use cases, one per id", () => {
    expect(USE_CASES).toHaveLength(6);
    expect(new Set(USE_CASES.map((item) => item.id))).toEqual(new Set(USE_CASE_IDS));
  });

  it.each(USE_CASES.map((item) => [item.id, item] as const))(
    "%s has at least 3 steps with unique ids",
    (_id, useCase) => {
      expect(useCase.steps.length).toBeGreaterThanOrEqual(3);
      const ids = useCase.steps.map((step) => step.id);
      expect(new Set(ids).size).toBe(ids.length);
    },
  );

  it.each(USE_CASES.map((item) => [item.id, item] as const))(
    "%s has a plain title, a who-it-is-for line and an honest limits note",
    (_id, useCase) => {
      expect(useCase.title.trim().length).toBeGreaterThan(0);
      expect(useCase.forWho.trim().length).toBeGreaterThan(0);
      expect(useCase.limits.trim().length).toBeGreaterThan(20);
    },
  );

  it.each(USE_CASES.map((item) => [item.id, item] as const))(
    "%s has a source key and a route on every step",
    (_id, useCase) => {
      for (const step of useCase.steps) {
        expect(step.source.trim().length).toBeGreaterThan(0);
        expect(step.instruction.trim().length).toBeGreaterThan(0);
        expect(step.route).toBeDefined();
      }
    },
  );
});

describe("isUseCaseId", () => {
  it("accepts known ids and rejects anything else", () => {
    expect(isUseCaseId("call_centre")).toBe(true);
    expect(isUseCaseId("enterprise")).toBe(false);
    expect(isUseCaseId(null)).toBe(false);
    expect(isUseCaseId(42)).toBe(false);
  });
});

describe("nextUndoneStep", () => {
  it("returns the first step that is not done", () => {
    const progress = useCaseProgress(smallBusiness, new Set([smallBusiness.steps[0]!.source]));
    expect(nextUndoneStep(progress)?.id).toBe(smallBusiness.steps[1]!.id);
  });

  it("returns null when every step is done", () => {
    const all = new Set(smallBusiness.steps.map((step) => step.source));
    expect(nextUndoneStep(useCaseProgress(smallBusiness, all))).toBeNull();
  });
});
