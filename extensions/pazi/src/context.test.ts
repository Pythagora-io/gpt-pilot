import fs from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { withTempDir } from "../../../test/helpers/extensions/temp-dir.js";
import {
  _resetForTest,
  clearProxyContext,
  configurePersistencePath,
  configurePersistenceWarnLogger,
  getProxyContext,
  getProxyLastActivityAt,
  isProxyBusyForStatus,
  markProxyActivity,
  setProxyContext,
} from "./context.js";

describe("pazi context busy status", () => {
  beforeEach(() => {
    clearProxyContext();
  });

  it("returns not busy when no context has been set", () => {
    expect(isProxyBusyForStatus(1_000_000)).toBe(false);
    expect(getProxyLastActivityAt()).toBeNull();
  });

  it("returns not busy when context exists but there is no activity yet", () => {
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    expect(isProxyBusyForStatus(1_000_000)).toBe(false);
  });

  it("returns busy when activity is within the 30-minute window", () => {
    const nowMs = 1_000_000;
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    markProxyActivity(nowMs - 29 * 60 * 1000);
    expect(isProxyBusyForStatus(nowMs)).toBe(true);
  });

  it("returns not busy when activity is older than 30 minutes", () => {
    const nowMs = 1_000_000;
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    markProxyActivity(nowMs - 31 * 60 * 1000);
    expect(isProxyBusyForStatus(nowMs)).toBe(false);
  });
});

describe("pazi context persistence", () => {
  beforeEach(() => {
    configurePersistenceWarnLogger(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    _resetForTest();
  });

  const sampleContext = {
    userId: "user-123",
    agentId: "agent-456",
    proxyToken: "tok_abc",
  };

  it("persists context to disk on set and loads after reset", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "pazi", "proxy-context.json");
      configurePersistencePath(filePath);

      setProxyContext(sampleContext);

      // File should exist with correct content
      const raw = fs.readFileSync(filePath, "utf-8");
      const parsed = JSON.parse(raw);
      expect(parsed).toEqual(sampleContext);

      // File permissions should be 0o600
      if (process.platform !== "win32") {
        const mode = fs.statSync(filePath).mode & 0o777;
        expect(mode).toBe(0o600);
      }

      // Simulate restart: reset module state, reconfigure path
      _resetForTest();
      configurePersistencePath(filePath);

      // getProxyContext should lazy-load from disk
      const loaded = getProxyContext();
      expect(loaded).toEqual(sampleContext);
    });
  });

  it("returns null when persistence file does not exist", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      configurePersistencePath(path.join(dir, "nonexistent", "proxy-context.json"));

      expect(getProxyContext()).toBeNull();
    });
  });

  it("returns null when persistence file contains invalid JSON", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      fs.writeFileSync(filePath, "{invalid json!!!", "utf-8");
      configurePersistencePath(filePath);

      expect(getProxyContext()).toBeNull();
    });
  });

  it("returns null when persistence file contains valid JSON but wrong shape", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      fs.writeFileSync(filePath, JSON.stringify({ userId: 42 }), "utf-8");
      configurePersistencePath(filePath);

      expect(getProxyContext()).toBeNull();
    });
  });

  it("returns null when fields are empty strings", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      fs.writeFileSync(
        filePath,
        JSON.stringify({ userId: "", agentId: "a", proxyToken: "t" }),
        "utf-8",
      );
      configurePersistencePath(filePath);

      expect(getProxyContext()).toBeNull();
    });
  });

  it("clearProxyContext removes the persisted file", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "pazi", "proxy-context.json");
      configurePersistencePath(filePath);

      setProxyContext(sampleContext);
      expect(getProxyContext()).toEqual(sampleContext);

      clearProxyContext();

      // After clear, getProxyContext should return null
      expect(getProxyContext()).toBeNull();

      // File should be deleted
      expect(fs.existsSync(filePath)).toBe(false);

      // Simulate restart: even loading from disk should give null
      _resetForTest();
      configurePersistencePath(filePath);
      expect(getProxyContext()).toBeNull();
    });
  });

  it("in-memory cache is used after first disk load", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, JSON.stringify(sampleContext), "utf-8");
      configurePersistencePath(filePath);

      // First call loads from disk
      expect(getProxyContext()).toEqual(sampleContext);

      // Mutate file behind the scenes
      fs.writeFileSync(
        filePath,
        JSON.stringify({ userId: "changed", agentId: "changed", proxyToken: "changed" }),
        "utf-8",
      );

      // Second call returns cached value, not re-read from disk
      expect(getProxyContext()).toEqual(sampleContext);
    });
  });

  it("setProxyContext overwrites previous persisted context", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      configurePersistencePath(filePath);

      setProxyContext(sampleContext);
      const newContext = { userId: "user-999", agentId: "agent-999", proxyToken: "tok_new" };
      setProxyContext(newContext);

      const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(raw).toEqual(newContext);

      // Simulate restart
      _resetForTest();
      configurePersistencePath(filePath);
      expect(getProxyContext()).toEqual(newContext);
    });
  });

  it("works without persistence path configured", () => {
    // No configurePersistencePath call — defaults to null
    setProxyContext(sampleContext);
    expect(getProxyContext()).toEqual(sampleContext);
    clearProxyContext();
    expect(getProxyContext()).toBeNull();
  });

  it("creates parent directories when they do not exist", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "deep", "nested", "proxy-context.json");
      configurePersistencePath(filePath);

      setProxyContext(sampleContext);

      expect(fs.existsSync(filePath)).toBe(true);
      if (process.platform !== "win32") {
        const dirMode = fs.statSync(path.join(dir, "deep")).mode & 0o777;
        expect(dirMode).toBe(0o700);
      }
    });
  });

  it("emits warning when persisting context fails", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const warnings: string[] = [];
      configurePersistenceWarnLogger((message) => {
        warnings.push(message);
      });

      // Use a directory path as a file path so writeFileSync fails with EISDIR.
      configurePersistencePath(dir);
      setProxyContext(sampleContext);

      expect(warnings.some((message) => message.includes("failed to persist context"))).toBe(true);
    });
  });

  it("emits warning when configuring an empty persistence path", () => {
    const warnings: string[] = [];
    configurePersistenceWarnLogger((message) => {
      warnings.push(message);
    });

    configurePersistencePath("   ");

    expect(
      warnings.some((message) => message.includes("disabled because configured path was empty")),
    ).toBe(true);
  });

  it("persists atomically — file is valid even if stale temp exists from prior crash", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "pazi", "proxy-context.json");
      configurePersistencePath(filePath);

      // Simulate stale temp from a previous crash
      const staleTemp = `${filePath}.99999.tmp`;
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(staleTemp, "corrupted partial write", "utf-8");

      setProxyContext(sampleContext);

      const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(raw).toEqual(sampleContext);

      // Simulate restart: reset in-memory, reload from disk
      _resetForTest();
      configurePersistencePath(filePath);
      expect(getProxyContext()).toEqual(sampleContext);
    });
  });

  it("survives a truncated file gracefully (loads null, next set overwrites)", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, '{"userId":"u1","age', "utf-8");
      configurePersistencePath(filePath);

      expect(getProxyContext()).toBeNull();

      setProxyContext(sampleContext);
      _resetForTest();
      configurePersistencePath(filePath);
      expect(getProxyContext()).toEqual(sampleContext);
    });
  });

  it("prefers atomic rename when renameSync succeeds", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "pazi", "proxy-context.json");
      configurePersistencePath(filePath);

      const renameSpy = vi.spyOn(fs, "renameSync");

      setProxyContext(sampleContext);

      expect(renameSpy).toHaveBeenCalledTimes(1);
      expect(JSON.parse(fs.readFileSync(filePath, "utf-8"))).toEqual(sampleContext);
    });
  });

  it("falls back to direct write when renameSync throws EPERM", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "pazi", "proxy-context.json");
      configurePersistencePath(filePath);

      vi.spyOn(fs, "renameSync").mockImplementation(() => {
        const err: NodeJS.ErrnoException = new Error("EPERM: operation not permitted");
        err.code = "EPERM";
        throw err;
      });

      setProxyContext(sampleContext);

      const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(raw).toEqual(sampleContext);

      // Temp file should be cleaned up
      const tmpPath = `${filePath}.${process.pid}.tmp`;
      expect(fs.existsSync(tmpPath)).toBe(false);

      // File permissions should still be 0o600
      if (process.platform !== "win32") {
        const mode = fs.statSync(filePath).mode & 0o777;
        expect(mode).toBe(0o600);
      }
    });
  });

  it("warns once and skips rename on subsequent writes after EPERM fallback", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath = path.join(dir, "proxy-context.json");
      const warnings: string[] = [];
      configurePersistenceWarnLogger((msg) => warnings.push(msg));
      configurePersistencePath(filePath);

      const renameSpy = vi.spyOn(fs, "renameSync").mockImplementation(() => {
        const err: NodeJS.ErrnoException = new Error("EPERM: operation not permitted");
        err.code = "EPERM";
        throw err;
      });

      // First call triggers fallback + warning
      setProxyContext(sampleContext);
      expect(renameSpy).toHaveBeenCalledTimes(1);

      // Second call should skip rename entirely
      renameSpy.mockClear();
      const ctx2 = { userId: "u2", agentId: "a2", proxyToken: "t2" };
      setProxyContext(ctx2);
      expect(renameSpy).not.toHaveBeenCalled();

      // Fallback warning emitted exactly once
      const fallbackWarnings = warnings.filter((m) =>
        m.includes("falling back to direct writes"),
      );
      expect(fallbackWarnings).toHaveLength(1);

      // Second context was persisted correctly
      const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
      expect(raw).toEqual(ctx2);
    });
  });

  it("re-enables atomic rename after configuring a new path", async () => {
    await withTempDir("pazi-ctx-", async (dir) => {
      const filePath1 = path.join(dir, "path1", "proxy-context.json");
      configurePersistencePath(filePath1);

      // Force EPERM on first path
      const renameSpy = vi.spyOn(fs, "renameSync").mockImplementation(() => {
        const err: NodeJS.ErrnoException = new Error("EPERM");
        err.code = "EPERM";
        throw err;
      });
      setProxyContext(sampleContext);

      // Reconfigure to a new path — should reset fallback
      renameSpy.mockRestore();
      const filePath2 = path.join(dir, "path2", "proxy-context.json");
      configurePersistencePath(filePath2);

      const renameSpy2 = vi.spyOn(fs, "renameSync");
      setProxyContext(sampleContext);

      // Atomic rename should be attempted again on the new path
      expect(renameSpy2).toHaveBeenCalledTimes(1);
      expect(JSON.parse(fs.readFileSync(filePath2, "utf-8"))).toEqual(sampleContext);
    });
  });
});
