// PAZ-300: Extracted credit-exhaustion cache logic for testability and
// correct scoping — the cache resets when the userId changes so a stale
// 402 from one user never blocks a different user.

const CREDIT_EXHAUSTION_CACHE_MS = 5 * 60 * 1000;

let last402At: number | null = null;
let cachedUserId: string | null = null;

/**
 * Returns true when a recent 402 was recorded for this userId and the
 * cache window has not yet elapsed.  Automatically clears when the
 * userId changes (proxy context switch).
 */
export function shouldBlockDueToExhaustion(userId: string, nowMs = Date.now()): boolean {
  if (cachedUserId !== null && cachedUserId !== userId) {
    // Different user — stale cache, reset.
    last402At = null;
    cachedUserId = userId;
    return false;
  }
  cachedUserId = userId;
  if (last402At === null) return false;
  return nowMs - last402At < CREDIT_EXHAUSTION_CACHE_MS;
}

/** Record a 402 for the given userId. */
export function recordExhaustion(userId: string, nowMs = Date.now()): void {
  cachedUserId = userId;
  last402At = nowMs;
}

/** Explicitly clear the cache (called when proxy context is set). */
export function clearCreditExhaustionCache(): void {
  last402At = null;
  cachedUserId = null;
}

/** @internal — test-only reset */
export function _resetForTest(): void {
  last402At = null;
  cachedUserId = null;
}

export { CREDIT_EXHAUSTION_CACHE_MS };
