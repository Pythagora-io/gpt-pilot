import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { isAgentBootstrapEvent, type InternalHookHandler } from "openclaw/plugin-sdk/hook-runtime";

const TEMPLATE_PATH = new URL("../../templates/AGENTS.pazi.md", import.meta.url);

let cachedTemplate: string | null = null;

async function loadTemplate(): Promise<string | null> {
  if (cachedTemplate !== null) return cachedTemplate;
  try {
    cachedTemplate = await fs.readFile(fileURLToPath(TEMPLATE_PATH), "utf-8");
    return cachedTemplate;
  } catch {
    return null;
  }
}

/**
 * Bootstrap hook that appends Pazi frontend-action docs to AGENTS.md
 * so the agent knows how to use voice client tools and PAZI_COMMAND text markers.
 */
export const paziBootstrapActionsHook: InternalHookHandler = async (event) => {
  if (!isAgentBootstrapEvent(event)) return;

  const template = await loadTemplate();
  if (!template) return;

  const context = event.context;
  const agentsFile = context.bootstrapFiles.find((f) => f.name === "AGENTS.md");
  if (!agentsFile || agentsFile.missing) return;

  // Avoid double-injection if the section is already present
  if (agentsFile.content && agentsFile.content.includes("## Pazi Frontend Actions")) return;

  agentsFile.content = (agentsFile.content ?? "") + "\n\n" + template;
};
