import { describe, expect, test } from "vitest";
import {
  formatPaziBillingErrorMessage,
  PAZI_INSUFFICIENT_CREDITS_META,
  PAZI_OUT_OF_CREDITS_MESSAGE,
} from "./pazi-billing-message.js";

describe("pazi-billing-message", () => {
  describe("PAZI_OUT_OF_CREDITS_MESSAGE", () => {
    test("should not mention API keys", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE.toLowerCase()).not.toContain("api key");
      expect(PAZI_OUT_OF_CREDITS_MESSAGE.toLowerCase()).not.toContain("api-key");
      expect(PAZI_OUT_OF_CREDITS_MESSAGE.toLowerCase()).not.toContain("apikey");
    });

    test("should contain subscription URL", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE).toContain(
        "https://pazi.ai/dashboard/account/subscription",
      );
    });

    test("should mention credits", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE.toLowerCase()).toContain("credits");
    });

    test("should mention subscription", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE.toLowerCase()).toContain("subscription");
    });

    test("should start with warning emoji", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE).toMatch(/^⚠️/);
    });

    test("should end with [insufficient_credits] detection tag", () => {
      expect(PAZI_OUT_OF_CREDITS_MESSAGE).toMatch(/\[insufficient_credits\]$/);
    });
  });

  describe("PAZI_INSUFFICIENT_CREDITS_META", () => {
    test("should have correct code", () => {
      expect(PAZI_INSUFFICIENT_CREDITS_META.code).toBe("insufficient_credits");
    });

    test("should have subscription action URL", () => {
      expect(PAZI_INSUFFICIENT_CREDITS_META.actionUrl).toBe("/dashboard/account/subscription");
    });

    test("should have Upgrade label", () => {
      expect(PAZI_INSUFFICIENT_CREDITS_META.actionLabel).toBe("Upgrade");
    });
  });

  describe("formatPaziBillingErrorMessage", () => {
    test("should return Pazi message regardless of provider parameter", () => {
      expect(formatPaziBillingErrorMessage()).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
      expect(formatPaziBillingErrorMessage("anthropic")).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
      expect(formatPaziBillingErrorMessage("openai")).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
    });

    test("should return Pazi message regardless of model parameter", () => {
      expect(formatPaziBillingErrorMessage(undefined, "claude-3-sonnet")).toBe(
        PAZI_OUT_OF_CREDITS_MESSAGE,
      );
      expect(formatPaziBillingErrorMessage("anthropic", "claude-3-sonnet")).toBe(
        PAZI_OUT_OF_CREDITS_MESSAGE,
      );
      expect(formatPaziBillingErrorMessage("openai", "gpt-4")).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
    });

    test("should always return the same message", () => {
      const message1 = formatPaziBillingErrorMessage();
      const message2 = formatPaziBillingErrorMessage("some-provider", "some-model");
      expect(message1).toBe(message2);
      expect(message1).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
    });
  });
});
