import fs from "node:fs/promises";
import path from "node:path";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";
import { loadTemplate, listTemplateIds } from "../templates/load-template.js";

type ResolvedWorkspace = {
  agentId: string;
  workspaceDir: string;
};

type ResolveWorkspace = (agentId: unknown) => ResolvedWorkspace | null;

/**
 * RPC handler: `pazi.templates.instantiate`
 *
 * Writes a template's files (IDENTITY.md, SOUL.md, skills) into the
 * target agent's workspace.
 *
 * Params:
 *   - templateId (string, required): ID of the template to instantiate
 *   - agentId    (string, optional): target gateway agent ID
 */
export function createPaziTemplatesInstantiateHandler(deps: {
  resolveWorkspace: ResolveWorkspace;
}): GatewayRequestHandler {
  return async ({ params, respond }) => {
    const templateId =
      typeof params.templateId === "string" ? params.templateId.trim() : "";

    if (!templateId) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, "templateId is required"),
      );
      return;
    }

    const result = await loadTemplate(templateId);
    if (!result) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.INVALID_REQUEST,
          `template "${templateId}" not found`,
        ),
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

    const { manifest, files } = result;
    const written: string[] = [];
    const errors: string[] = [];

    for (const file of files) {
      // Determine target path:
      // - Top-level agent files (IDENTITY.md, SOUL.md) → workspace root
      // - Skills → workspace/skills/{name}/SKILL.md
      let targetPath: string;

      if (manifest.skills.includes(file.relativePath)) {
        // Extract skill name from path: "skills/cicd-pipeline/SKILL.md" → "cicd-pipeline"
        const parts = file.relativePath.split("/");
        const skillName = parts.length >= 2 ? parts[parts.length - 2] : parts[0];
        targetPath = path.join(
          resolved.workspaceDir,
          "skills",
          skillName,
          "SKILL.md",
        );
      } else {
        // Top-level file (IDENTITY.md, SOUL.md, etc.)
        targetPath = path.join(resolved.workspaceDir, file.relativePath);
      }

      // Safety: ensure target is within the workspace
      const resolvedTarget = path.resolve(targetPath);
      const resolvedWorkspace = path.resolve(resolved.workspaceDir);
      if (
        !resolvedTarget.startsWith(resolvedWorkspace + path.sep) &&
        resolvedTarget !== resolvedWorkspace
      ) {
        errors.push(`${file.relativePath}: path traversal rejected`);
        continue;
      }

      try {
        await fs.mkdir(path.dirname(targetPath), { recursive: true });
        await fs.writeFile(targetPath, file.content, "utf-8");
        written.push(file.relativePath);
      } catch (err) {
        errors.push(
          `${file.relativePath}: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    }

    respond(true, {
      ok: true,
      templateId: manifest.id,
      agentId: resolved.agentId,
      written,
      errors,
    });
  };
}

/**
 * RPC handler: `pazi.templates.list`
 *
 * Returns the list of available template IDs.
 */
export function createPaziTemplatesListHandler(): GatewayRequestHandler {
  return async ({ respond }) => {
    const ids = await listTemplateIds();
    respond(true, { ok: true, templates: ids });
  };
}
