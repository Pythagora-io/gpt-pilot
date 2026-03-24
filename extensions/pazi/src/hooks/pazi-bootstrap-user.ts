import fs from "node:fs/promises";
import path from "node:path";
import {
  isAgentBootstrapEvent,
  type InternalHookHandler,
} from "../../../../src/hooks/internal-hooks.js";

/**
 * Bootstrap hook that injects the user's name into USER.md if a
 * `.pazi/user-meta.json` file exists in the workspace.
 *
 * The frontend writes `.pazi/user-meta.json` (via pazi.files.set) right
 * after agents.create with: { "name": "Zvonimir" }
 *
 * This hook reads that file at bootstrap time and fills in the blank
 * Name / "What to call them" fields in USER.md.
 */
export const paziBootstrapUserHook: InternalHookHandler = async (event) => {
  if (!isAgentBootstrapEvent(event)) return;

  const context = event.context;
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
    userName = typeof meta.name === "string" ? meta.name.trim() : undefined;
  } catch {
    // File doesn't exist or is invalid — nothing to inject
    return;
  }

  if (!userName) return;

  userFile.content = userFile.content
    .replace(/^- \*\*Name:\*\*\s*$/m, `- **Name:** ${userName}`)
    .replace(/^- \*\*What to call them:\*\*\s*$/m, `- **What to call them:** ${userName}`);
};
