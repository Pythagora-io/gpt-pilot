import fs from "node:fs/promises";
import path from "node:path";
import { listAgentIds, resolveAgentWorkspaceDir } from "../../../../src/agents/agent-scope.js";
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

    if (!content.trim()) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "content is required"));
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

    // Normalize to lowercase for consistent directory naming across create/edit paths.
    const normalizedName = name.toLowerCase();

    const scope = typeof params.scope === "string" ? params.scope : "agent";

    const cfg = deps.loadConfig();
    const extraDirs = cfg.skills?.load?.extraDirs;
    const sharedDir =
      Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";

    const agentId =
      params && typeof params === "object" ? (params as { agentId?: unknown }).agentId : undefined;
    const resolved = deps.resolveWorkspace(agentId);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }

    if (scope === "all" && !sharedDir) {
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

    // Check ALL locations — no duplicate names allowed anywhere (shared or any agent).
    const exists = async (filePath: string): Promise<boolean> => {
      try {
        await fs.access(filePath);
        return true;
      } catch {
        return false;
      }
    };

    // Check shared dir
    if (sharedDir && (await exists(path.join(sharedDir, normalizedName, "SKILL.md")))) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`),
      );
      return;
    }

    // Check every agent workspace
    const allAgentIds = listAgentIds(cfg);
    for (const agentIdEntry of allAgentIds) {
      const wsDir = resolveAgentWorkspaceDir(cfg, agentIdEntry);
      if (await exists(path.join(wsDir, "skills", normalizedName, "SKILL.md"))) {
        respond(
          false,
          undefined,
          errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`),
        );
        return;
      }
    }

    const skillDir =
      scope === "all"
        ? path.join(sharedDir, normalizedName)
        : path.join(resolved.workspaceDir, "skills", normalizedName);
    const skillFile = path.join(skillDir, "SKILL.md");

    // Build SKILL.md content with frontmatter.
    const skillContent =
      `---
name: ${normalizedName}
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

    respond(true, { ok: true, name: normalizedName, created: true });
  };
}
