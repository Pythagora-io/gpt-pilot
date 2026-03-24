import fs from "node:fs/promises";
import path from "node:path";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";
import type { OpenClawConfig } from "../../../../src/config/config.js";
import { loadWorkspaceSkillEntries } from "../../../../src/agents/skills.js";

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

/**
 * Sources that represent user-managed skills which can be deleted.
 * Bundled and extra skills cannot be deleted — only disabled.
 */
const DELETABLE_SOURCES = new Set([
  "openclaw-workspace",
  "openclaw-managed",
  "agents-skills-project",
  "agents-skills-personal",
]);

export function createPaziSkillsDeleteHandler(deps: {
  loadConfig: () => OpenClawConfig;
  writeConfigFile: (cfg: OpenClawConfig) => void | Promise<void>;
  resolveWorkspace: ResolveWorkspace;
}): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const skillKey =
      typeof params.skillKey === "string" ? params.skillKey.trim() : "";

    if (!skillKey) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, "skillKey is required"),
      );
      return;
    }

    const agentId =
      params && typeof params === "object"
        ? (params as { agentId?: unknown }).agentId
        : undefined;
    const resolved = deps.resolveWorkspace(agentId);
    if (!resolved) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"),
      );
      return;
    }

    const cfg = deps.loadConfig();
    const entries = loadWorkspaceSkillEntries(resolved.workspaceDir, {
      config: cfg,
    });

    // Find the skill entry matching the given skillKey.
    const entry = entries.find((e) => {
      const key = e.metadata?.skillKey ?? e.skill.name;
      return key === skillKey;
    });

    if (!entry) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.INVALID_REQUEST,
          `skill "${skillKey}" not found`,
        ),
      );
      return;
    }

    if (!DELETABLE_SOURCES.has(entry.skill.source)) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.INVALID_REQUEST,
          `cannot delete ${entry.skill.source} skill — only user-managed skills can be removed`,
        ),
      );
      return;
    }

    // The skill directory is the parent directory of SKILL.md.
    const skillDir = path.dirname(entry.skill.filePath);

    try {
      await fs.rm(skillDir, { recursive: true, force: true });
    } catch (err) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.UNAVAILABLE,
          `failed to delete skill directory: ${err instanceof Error ? err.message : String(err)}`,
        ),
      );
      return;
    }

    // Remove any config override for this skill key.
    const skills = cfg.skills ? { ...cfg.skills } : {};
    const configEntries = skills.entries ? { ...skills.entries } : {};
    if (skillKey in configEntries) {
      delete configEntries[skillKey];
      skills.entries = configEntries;
      const nextConfig: OpenClawConfig = { ...cfg, skills };
      try {
        await deps.writeConfigFile(nextConfig);
      } catch {
        // Best effort — the directory is already gone.
      }
    }

    respond(true, { ok: true, skillKey, deleted: true });
  };
}
