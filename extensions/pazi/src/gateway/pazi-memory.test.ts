import fs from "node:fs/promises";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { withTempDir } from "../../../../test/helpers/extensions/temp-dir.js";
import { createPaziMemoryGet } from "./pazi-memory.js";

type HandlerResponse = {
  ok: boolean;
  result?: {
    files?: Array<{ name: string; kind: string; content: string }>;
  };
  error?: unknown;
};

async function invokeMemoryGet(workspaceDir: string): Promise<HandlerResponse> {
  const handler = createPaziMemoryGet(() => ({ agentId: "agent-1", workspaceDir }));
  let response: HandlerResponse | null = null;
  await handler({
    req: {} as never,
    params: { agentId: "agent-1" },
    client: null,
    isWebchatConnect: () => false,
    respond: (ok, result, error) => {
      response = { ok, result: result as HandlerResponse["result"], error };
    },
    context: {} as never,
  });
  if (!response) {
    throw new Error("expected one response");
  }
  return response;
}

describe("createPaziMemoryGet", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("skips root memory symlinks", async () => {
    if (process.platform === "win32") {
      // Symlink permissions are environment-dependent on Windows CI.
      return;
    }

    await withTempDir("pazi-memory-", async (workspaceDir) => {
      await withTempDir("pazi-memory-target-", async (targetDir) => {
        const secretTarget = path.join(targetDir, "secret.md");
        await fs.writeFile(secretTarget, "secret");
        await fs.symlink(secretTarget, path.join(workspaceDir, "MEMORY.md"));

        const response = await invokeMemoryGet(workspaceDir);
        expect(response.ok).toBe(true);
        expect(response.result?.files).toEqual([]);
      });
    });
  });

  it("normalizes backslash memory paths before classification", async () => {
    await withTempDir("pazi-memory-", async (workspaceDir) => {
      await fs.mkdir(path.join(workspaceDir, "memory"), { recursive: true });
      await fs.writeFile(path.join(workspaceDir, "memory", "2026-03-26.md"), "daily");

      vi.spyOn(path, "relative").mockReturnValue("memory\\2026-03-26.md");

      const response = await invokeMemoryGet(workspaceDir);
      expect(response.ok).toBe(true);
      expect(response.result?.files).toHaveLength(1);
      expect(response.result?.files?.[0]?.name).toBe("memory/2026-03-26.md");
      expect(response.result?.files?.[0]?.kind).toBe("daily");
    });
  });
});
