import fs from "node:fs";
import path from "node:path";
import { createAsyncLock, writeJsonAtomic } from "../../../src/infra/json-files.js";
import {
  getSlackThreadParticipationEntriesSnapshot,
  hydrateSlackThreadParticipationCache,
} from "../../../src/slack/sent-thread-cache.js";

const STORE_VERSION = 1;
const TTL_MS = 24 * 60 * 60 * 1000;
const POLL_INTERVAL_MS = 5_000;

type StoredSlackThreadCache = {
  version: 1;
  entries: Array<{ key: string; ts: number }>;
};

export type SlackThreadCachePersistenceManager = {
  flush: () => Promise<void>;
  stop: () => Promise<void>;
};

function loadFromDisk(filePath: string, logWarn?: (message: string) => void): void {
  let raw: string;
  try {
    raw = fs.readFileSync(filePath, "utf-8");
  } catch (err) {
    if (
      !(
        typeof err === "object" &&
        err != null &&
        "code" in err &&
        (err as { code?: unknown }).code === "ENOENT"
      )
    ) {
      logWarn?.(`pazi: failed reading persisted slack thread cache at ${filePath}: ${String(err)}`);
    }
    return;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    logWarn?.(`pazi: ignoring invalid slack thread cache JSON at ${filePath}`);
    return;
  }

  const obj = parsed as { version?: unknown; entries?: unknown };
  if (obj?.version !== STORE_VERSION || !Array.isArray(obj.entries)) {
    return;
  }

  const now = Date.now();
  const valid: Array<[string, number]> = [];
  for (const entry of obj.entries as Array<{ key?: unknown; ts?: unknown }>) {
    if (typeof entry?.key !== "string" || !entry.key) {
      continue;
    }
    if (typeof entry?.ts !== "number" || !Number.isFinite(entry.ts) || entry.ts <= 0) {
      continue;
    }
    if (now - entry.ts > TTL_MS) {
      continue;
    }
    valid.push([entry.key, entry.ts]);
  }
  if (valid.length > 0) {
    hydrateSlackThreadParticipationCache(valid);
  }
}

function snapshotToString(snapshot: ReadonlyMap<string, number>): string {
  // Cheap identity check: sorted keys + timestamps
  const parts: string[] = [];
  for (const [key, ts] of snapshot) {
    parts.push(`${key}:${ts}`);
  }
  return parts.sort().join("\n");
}

export async function startSlackThreadCachePersistence(params: {
  stateDir: string;
  logWarn?: (message: string) => void;
}): Promise<SlackThreadCachePersistenceManager> {
  const filePath = path.join(params.stateDir, "pazi", "slack", "sent-thread-cache.json");
  loadFromDisk(filePath, params.logWarn);

  const withWriteLock = createAsyncLock();
  let hasLoggedPersistError = false;
  let lastPersistedIdentity = snapshotToString(getSlackThreadParticipationEntriesSnapshot());

  async function persistIfChanged(): Promise<void> {
    const snapshot = getSlackThreadParticipationEntriesSnapshot();
    const identity = snapshotToString(snapshot);
    if (identity === lastPersistedIdentity) {
      return;
    }
    await withWriteLock(async () => {
      const payload: StoredSlackThreadCache = {
        version: STORE_VERSION,
        entries: [...snapshot.entries()].map(([key, ts]) => ({ key, ts })),
      };
      try {
        await writeJsonAtomic(filePath, payload, {
          mode: 0o600,
          ensureDirMode: 0o700,
          trailingNewline: true,
        });
        lastPersistedIdentity = identity;
        hasLoggedPersistError = false;
      } catch (err) {
        if (!hasLoggedPersistError) {
          hasLoggedPersistError = true;
          params.logWarn?.(
            `pazi: failed persisting slack thread cache at ${filePath}: ${String(err)}`,
          );
        }
      }
    });
  }

  const timer = setInterval(() => {
    void persistIfChanged();
  }, POLL_INTERVAL_MS);

  const flush = async (): Promise<void> => {
    await persistIfChanged();
    await withWriteLock(async () => {});
  };

  const stop = async (): Promise<void> => {
    clearInterval(timer);
    await flush();
  };

  return { flush, stop };
}
