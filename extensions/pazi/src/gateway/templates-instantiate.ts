import fs from "node:fs/promises";
import path from "node:path";
import {
  ErrorCodes,
  errorShape,
  type GatewayRequestHandler,
} from "openclaw/plugin-sdk/gateway-runtime";
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
    const templateId = typeof params.templateId === "string" ? params.templateId.trim() : "";

    if (!templateId) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "templateId is required"));
      return;
    }

    const result = await loadTemplate(templateId);
    if (!result) {
      respond(
        false,
        undefined,
        errorShape(ErrorCodes.INVALID_REQUEST, `template "${templateId}" not found`),
      );
      return;
    }

    const agentId =
      params && typeof params === "object" ? (params as { agentId?: unknown }).agentId : undefined;
    const resolved = deps.resolveWorkspace(agentId);
    if (!resolved) {
      respond(false, undefined, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
      return;
    }

    const { manifest, files, errors: loadErrors } = result;
    const written: string[] = [];
    const errors: string[] = [...loadErrors];

    for (const file of files) {
      // Write each file at its relative path within the workspace.
      // Both top-level files (IDENTITY.md, SOUL.md) and skill files
      // (skills/devops-onboarding/SKILL.md, skills/devops-onboarding/references/credential-storage.md, etc.)
      // are placed at their relative path under the workspace root.
      const targetPath = path.join(resolved.workspaceDir, file.relativePath);

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
        errors.push(`${file.relativePath}: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    // If nothing was written and there are errors, treat as a failure
    if (written.length === 0 && errors.length > 0) {
      respond(
        false,
        undefined,
        errorShape(
          ErrorCodes.UNAVAILABLE,
          `failed to write any template files: ${errors.join("; ")}`,
        ),
      );
      return;
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
