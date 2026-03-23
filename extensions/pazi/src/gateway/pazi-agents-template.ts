import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { ErrorCodes, errorShape } from "../../../../src/gateway/protocol/index.js";
import type { GatewayRequestHandler } from "../../../../src/gateway/server-methods/types.js";

const TEMPLATE_PATH = new URL("../../templates/AGENTS.pazi.md", import.meta.url);

export function createPaziAgentsTemplateGet(): GatewayRequestHandler {
  return async ({ respond }) => {
    try {
      const template = await fs.readFile(fileURLToPath(TEMPLATE_PATH), "utf-8");
      respond(true, { version: "pazi-actions-v1", sectionId: "pazi-frontend-actions", template });
    } catch {
      respond(false, undefined, errorShape(ErrorCodes.UNAVAILABLE, "pazi_agents_template_unavailable"));
    }
  };
}
