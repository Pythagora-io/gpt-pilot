/**
 * Reply suppression registry for the Slack monitor dispatch path.
 *
 * This module provides `shouldSuppressSlackReply` which is called from
 * the Slack dispatch hot path (native ESM context). It reads from a
 * globalThis-shared map populated by the pazi extension (loaded via jiti).
 *
 * Why globalThis?
 * ─────────────────
 * The pazi extension runs in jiti's module graph (separate from native ESM).
 * Module-scoped state is not shared between the two graphs. globalThis is
 * the only reliable bridge. The pazi extension writes suppressed thread
 * entries to `globalThis.__openclawPaziSlackSuppressedThreads`, and this
 * module reads from it.
 *
 * Legacy callback API (`registerSlackReplySuppression`) is preserved for
 * backward compatibility but the primary suppression path now uses the
 * globalThis map.
 */

export type SlackReplySuppressCheck = (params: {
  accountId: string;
  target: string;
  threadTs?: string;
}) => boolean;

const suppressionChecks: SlackReplySuppressCheck[] = [];

/**
 * Register a suppression check. Returns a cleanup function.
 * @deprecated Use the globalThis shared map via the pazi extension instead.
 */
export function registerSlackReplySuppression(check: SlackReplySuppressCheck): () => void {
  suppressionChecks.push(check);
  return () => {
    const idx = suppressionChecks.indexOf(check);
    if (idx >= 0) suppressionChecks.splice(idx, 1);
  };
}

/**
 * Read the globalThis suppressed threads map (written by pazi extension).
 * Returns the map if it exists, or null.
 */
function getGlobalSuppressedThreads(): Map<
  string,
  { accountId: string; targetId: string; threadTs: string }
> | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any;
  return g.__openclawPaziSlackSuppressedThreads ?? null;
}

/**
 * Check if a reply should be suppressed.
 *
 * Checks two sources:
 * 1. The globalThis shared map (primary — populated by pazi extension)
 * 2. Legacy callback array (fallback — for any other extensions)
 *
 * Returns true if ANY source says suppress.
 */
export function shouldSuppressSlackReply(params: {
  accountId: string;
  target: string;
  threadTs?: string;
}): boolean {
  // ── Primary: check globalThis map ──
  const globalMap = getGlobalSuppressedThreads();
  if (globalMap && params.threadTs) {
    for (const thread of globalMap.values()) {
      if (
        thread.accountId === params.accountId &&
        thread.threadTs === params.threadTs &&
        // Also verify the target matches (prevent false positives if two
        // channels happen to share the same threadTs, which is rare but possible
        // in cross-workspace setups). The `target` param is a full target string
        // like "channel:C123" while `thread.targetId` is just the ID ("C123").
        // Use endsWith to avoid substring false-matches (e.g. C123 inside C1234).
        params.target.endsWith(thread.targetId)
      ) {
        return true;
      }
    }
  }

  // ── Fallback: legacy callback array ──
  for (const check of suppressionChecks) {
    try {
      if (check(params)) return true;
    } catch {
      // Suppress errors from callbacks
    }
  }
  return false;
}
