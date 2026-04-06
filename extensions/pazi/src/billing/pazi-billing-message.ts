/**
 * Pazi-specific billing error message for when users run out of credits.
 * Replaces the generic "API key" message with subscription-specific guidance.
 */

export const PAZI_OUT_OF_CREDITS_MESSAGE =
  "⚠️ You've run out of Pazi credits. Upgrade your subscription to continue: https://pazi.ai/dashboard/account/subscription";

/**
 * Replacement for the core formatBillingErrorMessage function.
 * Returns the Pazi-specific message regardless of provider/model params
 * since all LLM calls go through the Pazi API.
 */
export function formatPaziBillingErrorMessage(provider?: string, model?: string): string {
  return PAZI_OUT_OF_CREDITS_MESSAGE;
}
