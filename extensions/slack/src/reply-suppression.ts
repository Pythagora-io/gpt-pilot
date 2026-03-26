/**
 * Reply suppression registry for the Slack monitor dispatch path.
 *
 * Extensions can register a callback that decides whether a specific
 * reply should be suppressed before it's sent to Slack.
 */

export type SlackReplySuppressCheck = (params: {
  accountId: string;
  target: string;
  threadTs?: string;
}) => boolean;

const suppressionChecks: SlackReplySuppressCheck[] = [];

/**
 * Register a suppression check. Returns a cleanup function.
 */
export function registerSlackReplySuppression(check: SlackReplySuppressCheck): () => void {
  suppressionChecks.push(check);
  return () => {
    const idx = suppressionChecks.indexOf(check);
    if (idx >= 0) suppressionChecks.splice(idx, 1);
  };
}

/**
 * Check if a reply should be suppressed.
 * Returns true if ANY registered check says suppress.
 */
export function shouldSuppressSlackReply(params: {
  accountId: string;
  target: string;
  threadTs?: string;
}): boolean {
  for (const check of suppressionChecks) {
    try {
      if (check(params)) return true;
    } catch {
      // Suppress errors from callbacks
    }
  }
  return false;
}
