import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { createGetCredentialTool } from "./get-credential.js";
import { createListSavedCredentialsTool } from "./list-saved-credentials.js";
import { createSaveCredentialTool } from "./save-credential.js";

export function createCredentialTools(): AnyAgentTool[] {
  return [createSaveCredentialTool(), createListSavedCredentialsTool(), createGetCredentialTool()];
}
