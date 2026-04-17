/**
 * Pazi-specific billing error message for when users run out of credits.
 * Replaces the generic "API key" message with subscription-specific guidance.
 *
 * The `[insufficient_credits]` tag at the end is a reliable detection marker
 * for the frontend — it survives all agent formatting/sanitization steps.
 */

export const PAZI_OUT_OF_CREDITS_MESSAGE =
  "⚠️ You've run out of Pazi credits. Upgrade your subscription to continue: https://pazi.ai/dashboard/account/subscription [insufficient_credits]";

/**
 * Structured metadata for the insufficient credits error.
 * Canonical source of truth for error payloads used by the extension and frontend.
 */
export const PAZI_INSUFFICIENT_CREDITS_META = {
  code: "insufficient_credits",
  actionUrl: "/dashboard/account/subscription",
  actionLabel: "Upgrade",
} as const;

/**
 * Replacement for the core formatBillingErrorMessage function.
 * Returns the Pazi-specific message regardless of provider/model params
 * since all LLM calls go through the Pazi API.
 */
export function formatPaziBillingErrorMessage(_provider?: string, _model?: string): string {
  return PAZI_OUT_OF_CREDITS_MESSAGE;
}
