import fs from "node:fs/promises";
import path from "node:path";
import { listAgentIds, resolveAgentWorkspaceDir } from "../../../../src/agents/agent-scope.js";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

interface PaziSkillsDeps {
  resolveWorkspace: ResolveWorkspace;
  loadConfig: () => Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resolveRequestWorkspace(
  params: unknown,
  resolveWorkspace: ResolveWorkspace,
): ResolvedWorkspace | null {
  const agentId =
    params && typeof params === "object" ? (params as { agentId?: unknown }).agentId : undefined;
  return resolveWorkspace(agentId);
}

/**
 * Split a SKILL.md file into frontmatter block and body.
 * Returns `null` frontmatter when the file doesn't start with `---`.
 */
function splitSkillDocument(raw: string): { frontmatter: string | null; body: string } {
  const normalized = raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  if (!normalized.startsWith("---")) {
    return { frontmatter: null, body: normalized };
  }
  const endIndex = normalized.indexOf("\n---", 3);
  if (endIndex === -1) {
    return { frontmatter: null, body: normalized };
  }
  return {
    frontmatter: normalized.slice(4, endIndex),
    body: normalized.slice(endIndex + 4).replace(/^\n+/, ""),
  };
}

/**
 * Patch a single top-level scalar in frontmatter text.
 * Uses `JSON.stringify` for the value to handle colons / quotes / newlines safely.
 */
function upsertFrontmatterScalar(
  frontmatter: string,
  key: "name" | "description",
  value: string,
): string {
  const safeValue = JSON.stringify(value);
  const lines = frontmatter.split("\n");
  const regex = new RegExp(`^${key}:\\s`);
  const idx = lines.findIndex((l) => regex.test(l) || l === `${key}:`);

  if (idx !== -1) {
    lines[idx] = `${key}: ${safeValue}`;
  } else if (key === "name") {
    lines.unshift(`${key}: ${safeValue}`);
  } else {
    const nameIdx = lines.findIndex((l) => /^name:\s/.test(l) || l === "name:");
    lines.splice(nameIdx !== -1 ? nameIdx + 1 : 0, 0, `${key}: ${safeValue}`);
  }
  return lines.join("\n");
}

/**
 * Build the final SKILL.md content.
 *
 * The `content` parameter is body text only (no frontmatter) — the user edits
 * body in the content field, while name/description come from separate inputs.
 * We read the existing file to preserve any extra frontmatter fields (metadata,
 * etc.) and patch only name/description.
 */
function buildUpdatedDocument(params: {
  existingRaw: string | null;
  name: string;
  description: string;
  content: string;
}): string {
  const { existingRaw, content, name, description } = params;

  // Get existing frontmatter to preserve extra fields (metadata, etc.)
  let baseFm: string;
  if (existingRaw) {
    const { frontmatter } = splitSkillDocument(existingRaw);
    baseFm = frontmatter ?? "";
  } else {
    baseFm = "";
  }

  let patchedFm = upsertFrontmatterScalar(baseFm || `name: ${JSON.stringify(name)}`, "name", name);
  patchedFm = upsertFrontmatterScalar(patchedFm, "description", description);

  const separator = content.startsWith("\n") ? "" : "\n";
  return `---\n${patchedFm}\n---\n${separator}${content}`;
}

function slugify(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "") || "skill"
  );
}

// ---------------------------------------------------------------------------
// pazi.skills.get
// ---------------------------------------------------------------------------

export function createPaziSkillsGet(deps: PaziSkillsDeps): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const resolved = resolveRequestWorkspace(params, deps.resolveWorkspace);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }

    const p = params as Record<string, unknown>;
    const skillKey = typeof p.skillKey === "string" ? p.skillKey.trim() : "";
    if (!skillKey) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "missing skillKey"));
      return;
    }

    // Dynamic import to avoid circular dependency at module level
    const { buildWorkspaceSkillStatus } = await import("../../../../src/agents/skills-status.js");

    const cfg = deps.loadConfig();
    const status = buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg });
    const entry = status.skills.find((s: { skillKey: string }) => s.skillKey === skillKey);

    if (!entry) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${skillKey}" not found`),
      );
      return;
    }

    try {
      const raw = await fs.readFile(entry.filePath, "utf-8");
      const { body } = splitSkillDocument(raw);
      respond(true, {
        skillKey,
        source: entry.source,
        description: entry.description ?? "",
        content: body,
        bundled: entry.source === "openclaw-bundled",
        scope: entry.source === "openclaw-extra" ? "all" : "agent",
      });
    } catch {
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "failed to read skill file"));
    }
  };
}

// ---------------------------------------------------------------------------
// pazi.skills.set
// ---------------------------------------------------------------------------

export function createPaziSkillsSet(deps: PaziSkillsDeps): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const resolved = resolveRequestWorkspace(params, deps.resolveWorkspace);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }

    const p = params as Record<string, unknown>;
    const skillKey = typeof p.skillKey === "string" ? p.skillKey.trim() : "";
    const name = typeof p.name === "string" ? p.name.trim() : "";
    const description = typeof p.description === "string" ? p.description.trim() : "";
    const content = typeof p.content === "string" ? p.content : "";
    const scope = typeof p.scope === "string" ? p.scope : undefined;

    if (!skillKey) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "missing skillKey"));
      return;
    }
    if (!name) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "missing name"));
      return;
    }

    const { buildWorkspaceSkillStatus } = await import("../../../../src/agents/skills-status.js");

    const cfg = deps.loadConfig();
    const status = buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg });
    const entry = status.skills.find((s: { skillKey: string }) => s.skillKey === skillKey);

    if (!entry) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${skillKey}" not found`),
      );
      return;
    }

    // Read existing file to preserve extra frontmatter fields
    let existingRaw: string | null = null;
    try {
      existingRaw = await fs.readFile(entry.filePath, "utf-8");
    } catch {
      // File may not be readable; we'll build fresh frontmatter
    }

    const finalContent = buildUpdatedDocument({ existingRaw, name, description, content });

    // Determine if scope is changing
    const currentIsShared = entry.source === "openclaw-extra";
    const wantShared = scope === "all";
    const wantAgent = scope === "agent";
    const scopeChanging = (wantShared && !currentIsShared) || (wantAgent && currentIsShared);

    // Determine write path
    let writePath: string;
    let createdOverride = false;
    let oldDirToRemove: string | undefined;

    // Helper to check file existence
    const fileExists = async (filePath: string): Promise<boolean> => {
      try {
        await fs.access(filePath);
        return true;
      } catch {
        return false;
      }
    };

    // Check name collision across ALL locations (shared + every agent workspace).
    // Skip the current skill's own location.
    const checkGlobalCollision = async (
      dirName: string,
      currentFilePath: string,
    ): Promise<boolean> => {
      const extraDirs = cfg.skills?.load?.extraDirs;
      const sharedDir =
        Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";

      // Check shared dir
      if (sharedDir) {
        const sharedFile = path.join(sharedDir, dirName, "SKILL.md");
        if (sharedFile !== currentFilePath && (await fileExists(sharedFile))) return true;
      }

      // Check all agent workspaces
      const allAgentIds = listAgentIds(cfg);
      for (const id of allAgentIds) {
        const wsDir = resolveAgentWorkspaceDir(cfg, id);
        const agentFile = path.join(wsDir, "skills", dirName, "SKILL.md");
        if (agentFile !== currentFilePath && (await fileExists(agentFile))) return true;
      }

      return false;
    };

    // Always check for global name collision (covers renames, scope changes, everything).
    const targetDirName = slugify(name);
    if (await checkGlobalCollision(targetDirName, entry.filePath)) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `skill "${targetDirName}" already exists`),
      );
      return;
    }

    if (scopeChanging && wantShared) {
      // Move from agent workspace → shared dir
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
      writePath = path.join(sharedDir, slugify(name), "SKILL.md");
      oldDirToRemove = path.dirname(entry.filePath);
    } else if (scopeChanging && wantAgent) {
      // Move from shared dir → agent workspace
      writePath = path.join(resolved.workspaceDir, "skills", slugify(name), "SKILL.md");
      oldDirToRemove = path.dirname(entry.filePath);
    } else {
      const isWorkspaceSkill =
        entry.source === "openclaw-workspace" || entry.source === "agents-skills-project";
      const isExtraSkill = entry.source === "openclaw-extra";

      if (isWorkspaceSkill || isExtraSkill) {
        writePath = entry.filePath;
      } else {
        // Bundled/managed — create workspace override using skillKey for stable path
        const dirName = slugify(entry.skillKey);
        const overrideDir = path.join(resolved.workspaceDir, "skills", dirName);
        writePath = path.join(overrideDir, "SKILL.md");
        createdOverride = true;
      }
    }

    try {
      if (oldDirToRemove) {
        // Scope change: copy entire skill directory first to preserve sibling assets,
        // then overwrite SKILL.md with updated content, then remove old dir.
        const newDir = path.dirname(writePath);
        await fs.cp(oldDirToRemove, newDir, { recursive: true });
        await fs.writeFile(writePath, finalContent, "utf-8");
        await fs.rm(oldDirToRemove, { recursive: true }).catch(() => {});
      } else {
        await fs.mkdir(path.dirname(writePath), { recursive: true });
        await fs.writeFile(writePath, finalContent, "utf-8");
      }
    } catch {
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "failed to write skill file"));
      return;
    }

    respond(true, {
      ok: true,
      skillKey,
      createdOverride,
    });
  };
}
