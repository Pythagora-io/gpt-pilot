import fs from "node:fs/promises";
import path from "node:path";
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
    body: normalized.slice(endIndex + 4).replace(/^\n/, ""),
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
 * The `content` parameter is the raw text the user submitted from the editor.
 * We patch (or prepend) frontmatter so `name` / `description` from the
 * separate input fields always win.
 */
function buildUpdatedDocument(params: {
  name: string;
  description: string;
  content: string;
}): string {
  const { content, name, description } = params;
  const { frontmatter, body } = splitSkillDocument(content);

  if (frontmatter === null) {
    // No frontmatter in submitted content — prepend one.
    const fm = `---\nname: ${JSON.stringify(name)}\ndescription: ${JSON.stringify(description)}\n---\n\n`;
    return fm + content;
  }

  let patchedFm = upsertFrontmatterScalar(frontmatter, "name", name);
  patchedFm = upsertFrontmatterScalar(patchedFm, "description", description);

  return `---\n${patchedFm}\n---\n${body ? "\n" + body : "\n"}`;
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
      const content = await fs.readFile(entry.filePath, "utf-8");
      respond(true, {
        skillKey,
        filePath: entry.filePath,
        source: entry.source,
        content,
        bundled: entry.source === "openclaw-bundled",
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

    const finalContent = buildUpdatedDocument({ name, description, content });

    // Determine write path
    let writePath: string;
    let createdOverride = false;

    if (entry) {
      const isWorkspaceSkill =
        entry.source === "openclaw-workspace" || entry.source === "agents-skills-project";

      if (isWorkspaceSkill) {
        writePath = entry.filePath;
      } else {
        // Bundled/managed — create workspace override
        const dirName = slugify(name);
        const overrideDir = path.join(resolved.workspaceDir, "skills", dirName);
        writePath = path.join(overrideDir, "SKILL.md");
        createdOverride = true;
      }
    } else {
      // New skill (shouldn't normally happen via edit, but handle gracefully)
      const dirName = slugify(name);
      const overrideDir = path.join(resolved.workspaceDir, "skills", dirName);
      writePath = path.join(overrideDir, "SKILL.md");
      createdOverride = true;
    }

    try {
      await fs.mkdir(path.dirname(writePath), { recursive: true });
      await fs.writeFile(writePath, finalContent, "utf-8");
    } catch {
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "failed to write skill file"));
      return;
    }

    respond(true, {
      ok: true,
      skillKey,
      writtenTo: writePath,
      createdOverride,
    });
  };
}
