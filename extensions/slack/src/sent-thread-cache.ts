import { resolveGlobalDedupeCache } from "openclaw/plugin-sdk/infra-runtime";

/**
 * In-memory cache of Slack threads the bot has participated in.
 * Used to auto-respond in threads without requiring @mention after the first reply.
 * Follows a similar TTL pattern to the MS Teams and Telegram sent-message caches.
 */

const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const MAX_ENTRIES = 5000;

/**
 * Keep Slack thread participation shared across bundled chunks so thread
 * auto-reply gating does not diverge between prepare/dispatch call paths.
 */
const SLACK_THREAD_PARTICIPATION_KEY = Symbol.for("openclaw.slackThreadParticipation");
const threadParticipation = resolveGlobalDedupeCache(SLACK_THREAD_PARTICIPATION_KEY, {
  ttlMs: TTL_MS,
  maxSize: MAX_ENTRIES,
});

/**
 * Parallel timestamp map for persistence support (hydrate/snapshot).
 * DedupeCache doesn't expose iteration or direct set, so we keep a
 * synchronized Map alongside it for the persistence layer.
 */
const persistenceTimestamps = new Map<string, number>();

function makeKey(accountId: string, channelId: string, threadTs: string): string {
  return `${accountId}:${channelId}:${threadTs}`;
}

export function recordSlackThreadParticipation(
  accountId: string,
  channelId: string,
  threadTs: string,
): void {
  if (!accountId || !channelId || !threadTs) {
    return;
  }
  const key = makeKey(accountId, channelId, threadTs);
  threadParticipation.check(key);
  persistenceTimestamps.set(key, Date.now());
}

export function hasSlackThreadParticipation(
  accountId: string,
  channelId: string,
  threadTs: string,
): boolean {
  if (!accountId || !channelId || !threadTs) {
    return false;
  }
  return threadParticipation.peek(makeKey(accountId, channelId, threadTs));
}

/**
 * Bulk-load entries into the in-memory cache (e.g. from persisted storage).
 * Callers are responsible for filtering expired/invalid entries before calling.
 */
export function hydrateSlackThreadParticipationCache(
  entries: Iterable<[key: string, timestamp: number]>,
): void {
  for (const [key, ts] of entries) {
    threadParticipation.check(key);
    persistenceTimestamps.set(key, ts);
  }
}

/**
 * Snapshot current in-memory entries for external persistence layers.
 * Returns a copy — mutations do not affect the live cache.
 */
export function getSlackThreadParticipationEntriesSnapshot(): ReadonlyMap<string, number> {
  return new Map(persistenceTimestamps);
}

export function clearSlackThreadParticipationCache(): void {
  threadParticipation.clear();
  persistenceTimestamps.clear();
}
