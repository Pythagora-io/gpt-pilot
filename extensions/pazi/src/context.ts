import path from "node:path";
import { loadJsonFile, saveJsonFile } from "../../../src/infra/json-file.js";

type ProxyContext = {
  userId: string;
  agentId: string;
  proxyToken: string;
};

export type { ProxyContext };

const STALE_BUSY_AFTER_MS = 30 * 60 * 1000;

let currentContext: ProxyContext | null = null;
let lastProxyActivityAtMs: number | null = null;

// Persistence configuration
let persistencePath: string | null = null;
let diskLoaded = false;

/**
 * Configure the file path for persisting proxy context.
 * Called once from the pazi plugin's register() function.
 * Must be called before any get/set operations for persistence to work.
 */
export function configurePersistencePath(filePath: string): void {
  persistencePath = filePath || null;
}

/**
 * Validate that a parsed JSON value is a valid ProxyContext.
 * All fields must be non-empty strings.
 */
function isValidProxyContext(value: unknown): value is ProxyContext {
  if (!value || typeof value !== "object") return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.userId === "string" &&
    typeof obj.agentId === "string" &&
    typeof obj.proxyToken === "string" &&
    obj.userId.length > 0 &&
    obj.agentId.length > 0 &&
    obj.proxyToken.length > 0
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
        currentContext = loaded;
      }
    } catch {
      // Disk read failed — fall through to null
    }
  }

  return currentContext;
}

/**
 * Set the proxy context. Updates both in-memory cache and disk persistence.
 * Disk write is best-effort — failures are silently caught.
 */
export function setProxyContext(ctx: ProxyContext): void {
  currentContext = ctx;
  diskLoaded = true; // We have a known value, no need to load from disk
  persistToDisk(ctx);
}

/**
 * Best-effort persist context to disk.
 * Uses saveJsonFile which handles: mkdir with 0o700, writeFileSync, chmod 0o600.
 */
function persistToDisk(ctx: ProxyContext): void {
  if (!persistencePath) return;
  try {
    saveJsonFile(persistencePath, ctx);
  } catch {
    // Best-effort: disk write failed, in-memory is still authoritative.
    // Don't crash, don't log — saveJsonFile handles its own safety.
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
  if (!persistencePath) return;
  try {
    saveJsonFile(persistencePath, null);
  } catch {
    // Best-effort
  }
}

/* ── Test helpers (not for production use) ────────────────────── */

/**
 * Reset ALL module state. For use in tests only.
 */
export function _resetForTest(): void {
  currentContext = null;
  lastProxyActivityAtMs = null;
  persistencePath = null;
  diskLoaded = false;
}
