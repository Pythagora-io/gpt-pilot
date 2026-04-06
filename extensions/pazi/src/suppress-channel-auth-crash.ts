import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { registerUnhandledRejectionHandler } from "openclaw/plugin-sdk/runtime-env";

/**
 * Regex matching non-recoverable channel auth errors that should NOT crash the gateway.
 * These errors indicate invalid/expired tokens — restarting won't fix them.
 */
const CHANNEL_AUTH_ERROR_RE =
  /\binvalid_auth\b|\btoken_revoked\b|\btoken_expired\b|\baccount_inactive\b|\bnot_authed\b|\borg_login_required\b|\bteam_access_not_granted\b|\bmissing_scope\b|\bcannot_find_service\b|\binvalid_token\b/i;

function collectReasonCandidates(reason: unknown): string[] {
  const queue: unknown[] = [reason];
  const seen = new Set<unknown>();
  const candidates: string[] = [];

  while (queue.length > 0) {
    const current = queue.shift();
    if (current == null || seen.has(current)) {
      continue;
    }
    seen.add(current);

    if (typeof current === "string") {
      candidates.push(current);
      continue;
    }

    if (current instanceof Error) {
      if (current.message) {
        candidates.push(current.message);
      }
      if (current.stack) {
        candidates.push(current.stack);
      }
    }

    if (!current || typeof current !== "object") {
      continue;
    }

    const record = current as Record<string, unknown>;
    for (const key of ["message", "error", "code", "name", "type"] as const) {
      const value = record[key];
      if (typeof value === "string" && value.trim()) {
        candidates.push(value);
      }
    }

    for (const key of ["cause", "reason", "original", "error", "data"] as const) {
      const nested = record[key];
      if (nested !== undefined) {
        queue.push(nested);
      }
    }

    if (Array.isArray(record.errors)) {
      queue.push(...record.errors);
    }
  }

  return candidates;
}

function formatReasonForLog(reason: unknown): string {
  if (reason instanceof Error) {
    return reason.message;
  }
  if (typeof reason === "string") {
    return reason;
  }
  const candidates = collectReasonCandidates(reason)
    .map((value) => value.trim())
    .filter(Boolean);
  if (candidates.length > 0) {
    return candidates[0] as string;
  }
  try {
    return JSON.stringify(reason);
  } catch {
    return String(reason);
  }
}

function isChannelAuthError(reason: unknown): boolean {
  if (!reason) {
    return false;
  }
  const candidates = collectReasonCandidates(reason);
  return candidates.some((value) => CHANNEL_AUTH_ERROR_RE.test(value));
}

/**
 * Register a global unhandled-rejection handler that suppresses channel auth
 * errors (e.g. Slack invalid_auth) instead of crashing the gateway process.
 *
 * Without this, an expired Slack token causes an unhandled promise rejection
 * on every startup, killing the process ~15s after launch and creating an
 * infinite supervisor restart loop.
 */
export function installChannelAuthCrashGuard(logger: OpenClawPluginApi["logger"]): () => void {
  return registerUnhandledRejectionHandler((reason) => {
    if (isChannelAuthError(reason)) {
      const message = formatReasonForLog(reason);
      logger.error(
        `Suppressed channel auth crash (token likely expired/revoked): ${message}. ` +
          `Reconfigure the channel credentials to restore functionality.`,
      );
      return true;
    }
    return false;
  });
}
