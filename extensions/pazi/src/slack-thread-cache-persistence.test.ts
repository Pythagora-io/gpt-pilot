import fs from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { withTempDir } from "../../../test/helpers/extensions/temp-dir.js";
import {
  clearSlackThreadParticipationCache,
  hasSlackThreadParticipation,
  recordSlackThreadParticipation,
} from "../../slack/src/sent-thread-cache.js";
import { startSlackThreadCachePersistence } from "./slack-thread-cache-persistence.js";

describe("pazi slack thread cache persistence", () => {
  afterEach(() => {
    clearSlackThreadParticipationCache();
  });

  it("persists cache entries to disk", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const manager = await startSlackThreadCachePersistence({ stateDir });
      try {
        recordSlackThreadParticipation("A1", "C123", "1700000000.000001");
        await manager.flush();

        const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
        expect(fs.existsSync(filePath)).toBe(true);

        const data = JSON.parse(fs.readFileSync(filePath, "utf-8")) as {
          version: number;
          entries: Array<{ key: string; ts: number }>;
        };
        expect(data.version).toBe(1);
        expect(data.entries.length).toBe(1);
        expect(data.entries[0]?.key).toBe("A1:C123:1700000000.000001");
      } finally {
        await manager.stop();
      }
    });
  });

  it("hydrates cache from persisted file on startup", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(
        filePath,
        JSON.stringify({
          version: 1,
          entries: [{ key: "A1:C123:1700000000.000001", ts: Date.now() - 1000 }],
        }),
        "utf-8",
      );

      const manager = await startSlackThreadCachePersistence({ stateDir });
      try {
        expect(hasSlackThreadParticipation("A1", "C123", "1700000000.000001")).toBe(true);
      } finally {
        await manager.stop();
      }
    });
  });

  it("flushes pending writes when stopped", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const manager = await startSlackThreadCachePersistence({ stateDir });
      recordSlackThreadParticipation("A1", "C123", "1700000000.000001");
      await manager.stop();

      const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
      expect(fs.existsSync(filePath)).toBe(true);
    });
  });

  it("does not write when cache is unchanged", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const manager = await startSlackThreadCachePersistence({ stateDir });
      try {
        await manager.flush();
        const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
        expect(fs.existsSync(filePath)).toBe(false);
      } finally {
        await manager.stop();
      }
    });
  });

  it("ignores corrupted cache file", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, "not valid json {{{{", "utf-8");

      const warnings: string[] = [];
      const manager = await startSlackThreadCachePersistence({
        stateDir,
        logWarn: (msg) => warnings.push(msg),
      });
      try {
        expect(hasSlackThreadParticipation("A1", "C123", "1700000000.000001")).toBe(false);
        expect(warnings.length).toBe(1);
      } finally {
        await manager.stop();
      }
    });
  });

  it("skips expired entries on load", async () => {
    await withTempDir("pazi-slack-cache-", async (stateDir) => {
      const filePath = path.join(stateDir, "pazi", "slack", "sent-thread-cache.json");
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(
        filePath,
        JSON.stringify({
          version: 1,
          entries: [
            { key: "A1:C123:1700000000.000001", ts: Date.now() - 25 * 60 * 60 * 1000 },
            { key: "A1:C456:1700000000.000002", ts: Date.now() - 1000 },
          ],
        }),
        "utf-8",
      );

      const manager = await startSlackThreadCachePersistence({ stateDir });
      try {
        expect(hasSlackThreadParticipation("A1", "C123", "1700000000.000001")).toBe(false);
        expect(hasSlackThreadParticipation("A1", "C456", "1700000000.000002")).toBe(true);
      } finally {
        await manager.stop();
      }
    });
  });
});
