import fs from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { AgentBootstrapHookContext } from "../../../../src/hooks/internal-hooks.js";
import { createInternalHookEvent } from "../../../../src/hooks/internal-hooks.js";
import { withTempDir } from "../../../../src/test-utils/temp-dir.js";
import { paziBootstrapUserHook } from "./pazi-bootstrap-user.js";

describe("pazi bootstrap user hook", () => {
  it("injects agent and user names as literal single-line values", async () => {
    await withTempDir("pazi-bootstrap-user-", async (workspaceDir) => {
      const agentId = "agent-1";
      await fs.mkdir(path.join(workspaceDir, ".pazi"), { recursive: true });
      await fs.writeFile(
        path.join(workspaceDir, ".pazi", "user-meta.json"),
        JSON.stringify({ name: "$&\nUser Name" }),
        "utf-8",
      );

      const context: AgentBootstrapHookContext = {
        workspaceDir,
        agentId,
        cfg: {
          agents: {
            list: [{ id: agentId, name: "$&\nAgent Name" }],
          },
        },
        bootstrapFiles: [
          {
            name: "IDENTITY.md",
            path: path.join(workspaceDir, "IDENTITY.md"),
            missing: false,
            content: "- **Name:**\n  _(set during agent creation)_\n- **Creature:** AI assistant\n",
          },
          {
            name: "USER.md",
            path: path.join(workspaceDir, "USER.md"),
            missing: false,
            content: "- **Name:**\n- **What to call them:**\n- **Timezone:**\n",
          },
        ],
      };

      const event = createInternalHookEvent("agent", "bootstrap", "agent:main:main", context);
      await paziBootstrapUserHook(event);

      const identity = context.bootstrapFiles.find((f) => f.name === "IDENTITY.md");
      const user = context.bootstrapFiles.find((f) => f.name === "USER.md");

      expect(identity?.content).toContain("- **Name:** $& Agent Name");
      expect(identity?.content).not.toContain("\nAgent Name");
      expect(user?.content).toContain("- **Name:** $& User Name");
      expect(user?.content).toContain("- **What to call them:** $& User Name");
      expect(user?.content).not.toContain("\nUser Name");
    });
  });
});
