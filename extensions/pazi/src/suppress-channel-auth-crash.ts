import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { registerUnhandledRejectionHandler } from "openclaw/plugin-sdk/runtime-env";

/**
 * Regex matching non-recoverable channel auth errors that should NOT crash the gateway.
 * These errors indicate invalid/expired tokens — restarting won't fix them.
 */
const CHANNEL_AUTH_ERROR_RE =
  /\binvalid_auth\b|\btoken_revoked\b|\btoken_expired\b|\baccount_inactive\b|\bnot_authed\b/i;

function isChannelAuthError(reason: unknown): boolean {
  if (!reason) {
    return false;
  }
  const message =
    reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "";
  return CHANNEL_AUTH_ERROR_RE.test(message);
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
      const message = reason instanceof Error ? reason.message : String(reason);
      logger.error(
        `Suppressed channel auth crash (token likely expired/revoked): ${message}. ` +
          `Reconfigure the channel credentials to restore functionality.`,
      );
      return true;
    }
    return false;
  });
}
