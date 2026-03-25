import fs from "node:fs/promises";
import path from "node:path";
import type { OpenClawConfig } from "../../../../src/config/config.js";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

export function createPaziSkillsCreateHandler(deps: {
  loadConfig: () => OpenClawConfig;
  resolveWorkspace: ResolveWorkspace;
}): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const name = typeof params.name === "string" ? params.name.trim() : "";
    const description = typeof params.description === "string" ? params.description.trim() : "";
    const content = typeof params.content === "string" ? params.content : "";

    if (!name) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "name is required"));
      return;
    }

    if (!description) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "description is required"));
      return;
    }

    // Validate name is a safe directory slug (no path traversal).
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.INVALID_REQUEST,
          "name must be alphanumeric with dashes/underscores only",
        ),
      );
      return;
    }

    const scope = typeof params.scope === "string" ? params.scope : "agent";

    let skillDir: string;

    if (scope === "all") {
      // Write to the shared skills directory so all agents can use it.
      const cfg = deps.loadConfig();
      const extraDirs = cfg.skills?.load?.extraDirs;
      const sharedDir =
        Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";
      if (!sharedDir) {
        respond(
          false,
          undefined,
          errorShape(
            ErrorCodes.INVALID_REQUEST,
            "no shared skills directory configured (skills.load.extraDirs)",
          ),
        );
        return;
      }
      skillDir = path.join(sharedDir, name);
    } else {
      const agentId =
        params && typeof params === "object"
          ? (params as { agentId?: unknown }).agentId
          : undefined;
      const resolved = deps.resolveWorkspace(agentId);
      if (!resolved) {
        respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
        return;
      }
      skillDir = path.join(resolved.workspaceDir, "skills", name);
    }
    const skillFile = path.join(skillDir, "SKILL.md");

    // Check if skill already exists.
    try {
      await fs.access(skillFile);
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${name}" already exists`),
      );
      return;
    } catch {
      // Expected — skill doesn't exist yet.
    }

    // Build SKILL.md content with frontmatter.
    const skillContent =
      `---
name: ${name}
description: ${description}
---

${content}
`.trimEnd() + "\n";

    try {
      await fs.mkdir(skillDir, { recursive: true });
      await fs.writeFile(skillFile, skillContent, "utf-8");
    } catch (err) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.UNAVAILABLE,
          `failed to create skill: ${err instanceof Error ? err.message : String(err)}`,
        ),
      );
      return;
    }

    respond(true, { ok: true, name, created: true });
  };
}
