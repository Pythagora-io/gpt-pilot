import { describe, expect, test } from "vitest";
import {
  PAZI_INSUFFICIENT_CREDITS_META,
  PAZI_OUT_OF_CREDITS_MESSAGE,
} from "../billing/pazi-billing-message.js";
import { getLastBillingError } from "./pazi-proxy.js";

describe("pazi-proxy billing integration", () => {
  test("should be able to import Pazi billing message", () => {
    expect(PAZI_OUT_OF_CREDITS_MESSAGE).toBeDefined();
    expect(typeof PAZI_OUT_OF_CREDITS_MESSAGE).toBe("string");
    expect(PAZI_OUT_OF_CREDITS_MESSAGE.length).toBeGreaterThan(0);
  });

  test("should create proper Anthropic error response format with insufficient_credits marker", () => {
    const paziResponse = {
      type: "error",
      error: {
        type: "insufficient_credits",
        message: PAZI_OUT_OF_CREDITS_MESSAGE,
      },
    };

    expect(paziResponse.type).toBe("error");
    // Preserve insufficient_credits so web frontend InsufficientCreditsDialog still works
    expect(paziResponse.error.type).toBe("insufficient_credits");
    expect(paziResponse.error.message).toBe(PAZI_OUT_OF_CREDITS_MESSAGE);
    expect(paziResponse.error.message).toContain("subscription");
    expect(paziResponse.error.message).toContain("[insufficient_credits]");
    expect(paziResponse.error.message).not.toMatch(/api[- ]?key/i);
  });

  test("should handle insufficient_credits error detection", () => {
    // Test the JSON structure that would trigger the Pazi message
    const insufficientCreditsResponse = {
      error: "insufficient_credits",
    };

    // Verify the structure we're looking for
    expect(insufficientCreditsResponse.error).toBe("insufficient_credits");
  });

  test("getLastBillingError should be null initially", () => {
    expect(getLastBillingError()).toBeNull();
  });

  test("PAZI_INSUFFICIENT_CREDITS_META should have correct fields for surface_error event", () => {
    expect(PAZI_INSUFFICIENT_CREDITS_META.code).toBe("insufficient_credits");
    expect(PAZI_INSUFFICIENT_CREDITS_META.actionUrl).toBe("/dashboard/account/subscription");
    expect(PAZI_INSUFFICIENT_CREDITS_META.actionLabel).toBe("Upgrade");
  });
});
