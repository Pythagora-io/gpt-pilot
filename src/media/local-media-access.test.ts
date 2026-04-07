import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { assertLocalMediaAllowed, LocalMediaAccessError } from "./local-media-access.js";
import { getAgentScopedMediaLocalRoots } from "./local-roots.js";

describe("assertLocalMediaAllowed", () => {
  let tmpDir: string;
  let stateDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "media-access-test-"));
    stateDir = path.join(tmpDir, "state");
    await fs.mkdir(path.join(stateDir, "media"), { recursive: true });
    await fs.mkdir(path.join(stateDir, "workspace"), { recursive: true });
    await fs.mkdir(path.join(stateDir, "sandboxes"), { recursive: true });
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);
  });

  afterEach(async () => {
    vi.unstubAllEnvs();
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it("blocks workspace-* paths when localRoots is undefined (default)", async () => {
    const wsDir = path.join(stateDir, "workspace-someagent");
    await fs.mkdir(wsDir, { recursive: true });
    const filePath = path.join(wsDir, "file.png");
    await fs.writeFile(filePath, "test");

    await expect(assertLocalMediaAllowed(filePath, undefined)).rejects.toThrow(
      LocalMediaAccessError,
    );
  });

  it("allows workspace-* paths when explicit roots include that directory", async () => {
    const wsDir = path.join(stateDir, "workspace-someagent");
    await fs.mkdir(wsDir, { recursive: true });
    const filePath = path.join(wsDir, "file.png");
    await fs.writeFile(filePath, "test");

    const roots = [
      path.join(stateDir, "media"),
      path.join(stateDir, "workspace"),
      path.join(stateDir, "sandboxes"),
      wsDir,
    ];

    await expect(assertLocalMediaAllowed(filePath, roots)).resolves.toBeUndefined();
  });

  it("cross-agent media access works with multi-agent scoped roots", async () => {
    // Agent B generates a file in its workspace
    const agentBWorkspace = path.join(stateDir, "workspace-agentb");
    await fs.mkdir(agentBWorkspace, { recursive: true });
    const mediaFile = path.join(agentBWorkspace, "generated-image.png");
    await fs.writeFile(mediaFile, "image-data");

    // Agent A needs to access Agent B's file — build roots from Agent A's perspective
    const cfg = {
      agents: {
        list: [{ id: "agenta" }, { id: "agentb" }],
      },
    };
    const roots = getAgentScopedMediaLocalRoots(cfg, "agenta");

    await expect(assertLocalMediaAllowed(mediaFile, roots)).resolves.toBeUndefined();
  });

  it("rejects paths not under any provided root", async () => {
    const outsidePath = path.join(tmpDir, "outside", "secret.txt");
    await fs.mkdir(path.dirname(outsidePath), { recursive: true });
    await fs.writeFile(outsidePath, "secret");

    const roots = [path.join(stateDir, "media"), path.join(stateDir, "workspace")];

    await expect(assertLocalMediaAllowed(outsidePath, roots)).rejects.toThrow(
      LocalMediaAccessError,
    );
  });
});
