import fs from "node:fs";
import path from "node:path";
import { loadJsonFile } from "openclaw/plugin-sdk/json-store";

type ProxyContext = {
  userId: string;
  agentId: string;
  proxyToken: string;
  dashboardBaseUrl?: string;
  browserEnabled?: boolean;
  /** Set when a workspace migration is in progress. Agent should finish current work and stop. */
  migrationNotice?: {
    migrationId: string;
    newPlan: string;
    startedAt: string;
  };
};

export type { ProxyContext };

const STALE_BUSY_AFTER_MS = 20 * 60 * 1000;

let currentContext: ProxyContext | null = null;
let lastProxyActivityAtMs: number | null = null;

// Persistence configuration
let persistencePath: string | null = null;
let diskLoaded = false;
let persistenceWarnLogger: ((message: string) => void) | null = null;
let useDirectWrite = false; // sticky flag: skip atomic rename after EPERM

/**
 * Migration notice is runtime-only orchestration state.
 * Never persist it to disk, otherwise VM snapshots can carry stale "migrating"
 * state into the replacement instance.
 */
function stripTransientProxyContextFields(ctx: ProxyContext): ProxyContext {
  if (!ctx.migrationNotice) {
    return ctx;
  }
  const { migrationNotice: _migrationNotice, ...persistable } = ctx;
  return persistable;
}

function warnPersistence(message: string, err?: unknown): void {
  const formatErr = err instanceof Error ? err.message : String(err);
  const suffix = err === undefined ? "" : ` (${formatErr})`;
  const text = `pazi proxy context persistence: ${message}${suffix}`;
  if (persistenceWarnLogger) {
    persistenceWarnLogger(text);
    return;
  }
  // Fallback for contexts where plugin logger is not wired.
  console.warn(text);
}

function isEperm(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    (err as NodeJS.ErrnoException).code === "EPERM"
  );
}

/**
 * Configure the file path for persisting proxy context.
 * Called once from the pazi plugin's register() function.
 * Must be called before any get/set operations for persistence to work.
 */
export function configurePersistencePath(filePath: string): void {
  const normalized = filePath.trim();
  if (!normalized) {
    persistencePath = null;
    diskLoaded = false;
    useDirectWrite = false;
    warnPersistence("disabled because configured path was empty");
    return;
  }
  persistencePath = normalized;
  diskLoaded = false;
  useDirectWrite = false;
}

/**
 * Configure warning logger used for persistence failures.
 * Called from plugin register() to route warnings to gateway logger.
 */
export function configurePersistenceWarnLogger(logger: ((message: string) => void) | null): void {
  persistenceWarnLogger = logger;
}

/**
 * Validate that a parsed JSON value is a valid ProxyContext.
 * All fields must be non-empty strings.
 */
function isValidProxyContext(value: unknown): value is ProxyContext {
  if (!value || typeof value !== "object") {
    return false;
  }
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.userId === "string" &&
    typeof obj.agentId === "string" &&
    typeof obj.proxyToken === "string" &&
    obj.userId.length > 0 &&
    obj.agentId.length > 0 &&
    obj.proxyToken.length > 0 &&
    (obj.dashboardBaseUrl === undefined || typeof obj.dashboardBaseUrl === "string")
  );
}

/**
 * Get the current proxy context. Returns the in-memory cached value if set.
 * On first call after startup (when in-memory is null), lazy-loads from disk.
 */
export function getProxyContext(): ProxyContext | null {
  if (currentContext) {
    return currentContext;
  }

  // Lazy load from disk on first access when no in-memory context
  if (!diskLoaded && persistencePath) {
    diskLoaded = true;
    try {
      const loaded = loadJsonFile(persistencePath);
      if (isValidProxyContext(loaded)) {
        currentContext = stripTransientProxyContextFields(loaded);
      } else if (loaded !== undefined && loaded !== null) {
        warnPersistence(`ignored invalid persisted context at ${persistencePath}`);
      }
    } catch (err) {
      warnPersistence(`failed to load persisted context from ${persistencePath}`, err);
    }
  }

  return currentContext;
}

/**
 * Set the proxy context. Updates both in-memory cache and disk persistence.
 * Disk write is best-effort — failures are silently caught.
 */
/**
 * Check if browser access is enabled for the current workspace.
 * Returns false if context is missing or browserEnabled is not explicitly true.
 */
export function isBrowserEnabled(): boolean {
  return getProxyContext()?.browserEnabled === true;
}

export function setProxyContext(ctx: ProxyContext): void {
  currentContext = ctx;
  diskLoaded = true; // We have a known value, no need to load from disk
  persistToDisk(stripTransientProxyContextFields(ctx));
}

/**
 * Best-effort persist context to disk.
 * Primary path: atomic write-then-rename (safe against kill mid-write).
 * Fallback: direct write when rename fails with EPERM (overlay filesystem).
 */
function persistToDisk(ctx: ProxyContext): void {
  if (!persistencePath) {
    return;
  }
  const data = JSON.stringify(ctx, null, 2) + "\n";

  // Fast path: overlay filesystem detected, skip atomic rename
  if (useDirectWrite) {
    try {
      const dir = path.dirname(persistencePath);
      fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
      fs.writeFileSync(persistencePath, data, "utf8");
      fs.chmodSync(persistencePath, 0o600);
    } catch (err) {
      warnPersistence(`failed to persist context to ${persistencePath}`, err);
    }
    return;
  }

  // Atomic path: write to temp, then rename
  const tmpPath = `${persistencePath}.${process.pid}.tmp`;
  try {
    const dir = path.dirname(persistencePath);
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    fs.writeFileSync(tmpPath, data, "utf8");
    fs.chmodSync(tmpPath, 0o600);

    try {
      fs.renameSync(tmpPath, persistencePath);
    } catch (renameErr) {
      // Clean up temp file best-effort
      try {
        fs.rmSync(tmpPath, { force: true });
      } catch {
        /* ignore */
      }

      if (!isEperm(renameErr)) {
        throw renameErr; // re-throw non-EPERM to outer catch
      }

      // EPERM: overlay filesystem — switch to direct writes permanently
      useDirectWrite = true;
      warnPersistence(
        `rename failed with EPERM for ${persistencePath}; falling back to direct writes`,
        renameErr,
      );

      // Write directly this time
      fs.writeFileSync(persistencePath, data, "utf8");
      fs.chmodSync(persistencePath, 0o600);
    }
  } catch (err) {
    // Best-effort: disk write failed, in-memory is still authoritative.
    warnPersistence(`failed to persist context to ${persistencePath}`, err);
  }
}

export function markProxyActivity(atMs = Date.now()): void {
  lastProxyActivityAtMs = atMs;
}

export function getProxyLastActivityAt(): number | null {
  return lastProxyActivityAtMs;
}

export function isProxyBusyForStatus(nowMs = Date.now()): boolean {
  if (!currentContext || lastProxyActivityAtMs === null) {
    return false;
  }
  return nowMs - lastProxyActivityAtMs <= STALE_BUSY_AFTER_MS;
}

/**
 * Clear the proxy context from both memory and disk.
 * After clearing, getProxyContext() will return null even if the file existed.
 */
export function clearProxyContext(): void {
  currentContext = null;
  lastProxyActivityAtMs = null;
  diskLoaded = true; // Prevent re-loading cleared context from disk
  clearPersistedContext();
}

function clearPersistedContext(): void {
  if (!persistencePath) {
    return;
  }
  try {
    fs.rmSync(persistencePath, { force: true });
  } catch (err) {
    // Best-effort
    warnPersistence(`failed to clear persisted context at ${persistencePath}`, err);
  }
}

/* ── Test helpers (not for production use) ────────────────────── */

/**
 * Reset ALL module state. For use in tests only.
 * @internal
 */
export function _resetForTest(): void {
  currentContext = null;
  lastProxyActivityAtMs = null;
  persistencePath = null;
  diskLoaded = false;
  persistenceWarnLogger = null;
  useDirectWrite = false;
}
