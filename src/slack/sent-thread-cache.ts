import { resolveGlobalMap } from "../shared/global-singleton.js";

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

const threadParticipation = resolveGlobalMap<string, number>(SLACK_THREAD_PARTICIPATION_KEY);

function makeKey(accountId: string, channelId: string, threadTs: string): string {
  return `${accountId}:${channelId}:${threadTs}`;
}

function evictExpired(): void {
  const now = Date.now();
  for (const [key, timestamp] of threadParticipation) {
    if (now - timestamp > TTL_MS) {
      threadParticipation.delete(key);
    }
  }
}

function evictOldest(): void {
  const oldest = threadParticipation.keys().next().value;
  if (oldest) {
    threadParticipation.delete(oldest);
  }
}

export function recordSlackThreadParticipation(
  accountId: string,
  channelId: string,
  threadTs: string,
): void {
  if (!accountId || !channelId || !threadTs) {
    return;
  }
  if (threadParticipation.size >= MAX_ENTRIES) {
    evictExpired();
  }
  if (threadParticipation.size >= MAX_ENTRIES) {
    evictOldest();
  }
  threadParticipation.set(makeKey(accountId, channelId, threadTs), Date.now());
}

export function hasSlackThreadParticipation(
  accountId: string,
  channelId: string,
  threadTs: string,
): boolean {
  if (!accountId || !channelId || !threadTs) {
    return false;
  }
  const key = makeKey(accountId, channelId, threadTs);
  const timestamp = threadParticipation.get(key);
  if (timestamp == null) {
    return false;
  }
  if (Date.now() - timestamp > TTL_MS) {
    threadParticipation.delete(key);
    return false;
  }
  return true;
}

/**
 * Bulk-load entries into the in-memory cache (e.g. from persisted storage).
 * Callers are responsible for filtering expired/invalid entries before calling.
 */
export function hydrateSlackThreadParticipationCache(
  entries: Iterable<[key: string, timestamp: number]>,
): void {
  for (const [key, ts] of entries) {
    threadParticipation.set(key, ts);
  }
  if (threadParticipation.size > MAX_ENTRIES) {
    evictExpired();
  }
  while (threadParticipation.size > MAX_ENTRIES) {
    evictOldest();
  }
}

/**
 * Snapshot current in-memory entries for external persistence layers.
 * Returns a copy — mutations do not affect the live cache.
 */
export function getSlackThreadParticipationEntriesSnapshot(): ReadonlyMap<string, number> {
  return new Map(threadParticipation);
}

export function clearSlackThreadParticipationCache(): void {
  threadParticipation.clear();
}
