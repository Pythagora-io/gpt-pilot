import fs from "node:fs/promises";
import path from "node:path";
import { isAgentBootstrapEvent, type InternalHookHandler } from "openclaw/plugin-sdk/hook-runtime";

function normalizeInjectedName(value: string): string {
  return value.replace(/[\r\n]+/g, " ").trim();
}

/**
 * Bootstrap hook that injects:
 * 1. The user's name into USER.md (from `.pazi/user-meta.json`)
 * 2. The agent's display name into IDENTITY.md (from config)
 *
 * The frontend writes `.pazi/user-meta.json` (via pazi.files.set) right
 * after agents.create with: { "name": "Zvonimir" }
 *
 * The agent's display name comes from the agents.list config entry.
 */
export const paziBootstrapUserHook: InternalHookHandler = async (event) => {
  if (!isAgentBootstrapEvent(event)) return;

  const context = event.context;

  // --- Inject agent name into IDENTITY.md ---
  const identityFile = context.bootstrapFiles.find((f) => f.name === "IDENTITY.md");
  if (identityFile && !identityFile.missing && identityFile.content) {
    // Only fill in if the name field is blank (template default)
    if (identityFile.content.match(/^- \*\*Name:\*\*\s*$/m)) {
      // Resolve agent display name from config
      const agentId = context.agentId;
      const agents = Array.isArray(context.cfg?.agents?.list) ? context.cfg!.agents!.list : [];
      const agentEntry = agents.find((a) => a?.id === agentId);
      const agentName =
        typeof agentEntry?.name === "string" ? normalizeInjectedName(agentEntry.name) : "";
      if (agentName) {
        identityFile.content = identityFile.content.replace(
          /^- \*\*Name:\*\*\s*$(\n\s+_\(set during agent creation\)_)?/m,
          () => `- **Name:** ${agentName}`,
        );
      }
    }
  }

  // --- Inject user name into USER.md ---
  const userFile = context.bootstrapFiles.find((f) => f.name === "USER.md");
  if (!userFile || userFile.missing || !userFile.content) return;

  // Check if USER.md already has a name filled in (not just the blank template)
  if (!userFile.content.match(/^- \*\*Name:\*\*\s*$/m)) return;

  // Read user metadata from the workspace
  const metaPath = path.join(context.workspaceDir, ".pazi", "user-meta.json");
  let userName: string | undefined;
  try {
    const raw = await fs.readFile(metaPath, "utf-8");
    const meta = JSON.parse(raw) as { name?: string };
    userName = typeof meta.name === "string" ? normalizeInjectedName(meta.name) : undefined;
  } catch {
    // File doesn't exist or is invalid — nothing to inject
    return;
  }

  if (!userName) return;

  userFile.content = userFile.content
    .replace(/^- \*\*Name:\*\*\s*$/m, () => `- **Name:** ${userName}`)
    .replace(/^- \*\*What to call them:\*\*\s*$/m, () => `- **What to call them:** ${userName}`);
};
