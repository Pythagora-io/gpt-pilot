import { afterEach, describe, expect, it } from "vitest";
import {
  CREDIT_EXHAUSTION_CACHE_MS,
  _resetForTest,
  clearCreditExhaustionCache,
  recordExhaustion,
  shouldBlockDueToExhaustion,
} from "./credit-exhaustion-cache.js";

afterEach(() => {
  _resetForTest();
});

describe("credit-exhaustion-cache", () => {
  describe("shouldBlockDueToExhaustion", () => {
    it("returns false when no exhaustion has been recorded", () => {
      expect(shouldBlockDueToExhaustion("user-1")).toBe(false);
    });

    it("returns true within the cache window after recording", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      expect(shouldBlockDueToExhaustion("user-1", now + 1000)).toBe(true);
    });

    it("returns false after the cache window expires", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      expect(shouldBlockDueToExhaustion("user-1", now + CREDIT_EXHAUSTION_CACHE_MS + 1)).toBe(
        false,
      );
    });

    it("returns true at exactly the cache boundary", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      expect(shouldBlockDueToExhaustion("user-1", now + CREDIT_EXHAUSTION_CACHE_MS - 1)).toBe(true);
    });

    it("resets cache when userId changes", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      // Same user is still blocked
      expect(shouldBlockDueToExhaustion("user-1", now + 1000)).toBe(true);
      // Different user clears the stale cache
      expect(shouldBlockDueToExhaustion("user-2", now + 1000)).toBe(false);
    });

    it("allows recording for new user after context switch", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      // Switch to user-2 (clears via shouldBlock)
      shouldBlockDueToExhaustion("user-2", now + 1000);
      // Record for user-2
      recordExhaustion("user-2", now + 2000);
      expect(shouldBlockDueToExhaustion("user-2", now + 3000)).toBe(true);
    });
  });

  describe("clearCreditExhaustionCache", () => {
    it("clears an active cache so requests are no longer blocked", () => {
      const now = 1_000_000;
      recordExhaustion("user-1", now);
      expect(shouldBlockDueToExhaustion("user-1", now + 1000)).toBe(true);

      clearCreditExhaustionCache();
      expect(shouldBlockDueToExhaustion("user-1", now + 1000)).toBe(false);
    });
  });

  describe("recordExhaustion", () => {
    it("records for the given user", () => {
      recordExhaustion("user-1");
      expect(shouldBlockDueToExhaustion("user-1")).toBe(true);
    });
  });
});
