import { describe, expect, it } from "vitest";

import { controlBaseClasses, controlClasses, controlVariantClasses } from "../control-base";

describe("control base", () => {
  it("shares state and focus treatment across native controls", () => {
    for (const variant of ["input", "select", "textarea"] as const) {
      const classes = controlClasses(variant);
      expect(classes).toContain("border-hairline");
      expect(classes).toContain("focus-visible:ring-ink");
      expect(classes).toContain("aria-[invalid=true]:border-error");
      expect(classes).toContain(controlVariantClasses[variant]);
    }
  });

  it("keeps multiline sizing as the only intentional surface difference", () => {
    expect(controlVariantClasses.textarea).toContain("resize-y");
    expect(controlVariantClasses.textarea).toContain("bg-canvas-warm");
    expect(controlBaseClasses).not.toContain("bg-canvas-warm");
  });
});
