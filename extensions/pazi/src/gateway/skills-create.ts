import fs from "node:fs/promises";
import path from "node:path";
import {
  buildWorkspaceSkillStatus,
  listAgentIds,
  resolveAgentWorkspaceDir,
} from "openclaw/plugin-sdk/agent-runtime";
import type { OpenClawConfig } from "openclaw/plugin-sdk/core";
import {
  ErrorCodes,
  errorShape,
  type GatewayRequestHandler,
} from "openclaw/plugin-sdk/gateway-runtime";

/**
 * Strip a leading YAML frontmatter block from user-pasted content
 * to prevent double-frontmatter in the written SKILL.md.
 * Only strips if the block between `---` delimiters contains YAML-like
 * key-value pairs (e.g. `name: value`) to avoid mangling legitimate
 * markdown thematic breaks.
 */
function stripLeadingFrontmatter(text: string): string {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  if (!normalized.startsWith("---\n")) return normalized;
  const endIndex = normalized.indexOf("\n---", 4);
  if (endIndex === -1) return normalized;
  const block = normalized.slice(4, endIndex);
  // Only strip if it looks like YAML frontmatter (contains key: value lines)
  if (!/^[a-zA-Z_][a-zA-Z0-9_-]*\s*:/m.test(block)) return normalized;
  return normalized.slice(endIndex + 4).replace(/^\n+/, "");
}

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

    // Check ALL loaded skills (bundled, workspace, shared, plugin) for name collision.
    const status = buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg });
    const collision = status.skills.find(
      (s: { filePath: string }) =>
        path.basename(path.dirname(s.filePath)).toLowerCase() === normalizedName,
    );
    if (collision) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`),
      );
      return;
    }

    // Cross-workspace check: iterate ALL agent workspaces to catch collisions
    // that buildWorkspaceSkillStatus (scoped to one workspace) cannot see.
    const allAgentIds = listAgentIds(cfg);
    for (const agentIdEntry of allAgentIds) {
      if (agentIdEntry === resolved.agentId) continue; // already checked above
      const wsDir = resolveAgentWorkspaceDir(cfg, agentIdEntry);
      try {
        await fs.access(path.join(wsDir, "skills", normalizedName, "SKILL.md"));
        respond(
          false,
          undefined,
          errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`),
        );
        return;
      } catch {
        // No collision in this workspace — continue
      }
    }

    const skillDir =
      scope === "all"
        ? path.join(sharedDir, normalizedName)
        : path.join(resolved.workspaceDir, "skills", normalizedName);
    const skillFile = path.join(skillDir, "SKILL.md");

    // Strip any frontmatter from user-pasted content to prevent double-frontmatter.
    const sanitizedContent = stripLeadingFrontmatter(content.trim());

    // Build SKILL.md content with frontmatter.
    const skillContent =
      `---
name: ${normalizedName}
description: ${description}
---

${sanitizedContent}
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
