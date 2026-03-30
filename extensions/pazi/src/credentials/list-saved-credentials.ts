import { Type } from "@sinclair/typebox";
import { loadAuthProfileStoreForSecretsRuntime } from "openclaw/plugin-sdk/agent-runtime";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { listCredentialSummaries, normalizeService } from "./shared.js";

export function createListSavedCredentialsTool(): AnyAgentTool {
  return {
    name: "list_saved_credentials",
    label: "List Saved Credentials",
    description:
      "List saved credential profiles (service, type, label) without exposing " +
      "secret values. Use to check what credentials are already stored before " +
      "calling ask_for_credentials or get_credential.",
    parameters: Type.Object(
      {
        service: Type.Optional(
          Type.String({
            description: "Optional: filter by provider/service name (e.g. 'github')",
          }),
        ),
      },
      { additionalProperties: false },
    ),
    async execute(_toolCallId: string, params: Record<string, unknown>) {
      try {
        const serviceFilter =
          typeof params.service === "string" && params.service.trim()
            ? normalizeService(params.service)
            : undefined;

        const store = loadAuthProfileStoreForSecretsRuntime();
        const summaries = listCredentialSummaries(store, serviceFilter);

        return {
          content: [
            {
              type: "text" as const,
              text:
                summaries.length === 0
                  ? "No saved credentials found."
                  : `Found ${summaries.length} saved credential profile(s).`,
            },
          ],
          details: { credentials: summaries },
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ error: msg }, null, 2) }],
          details: { error: msg },
        };
      }
    },
  };
}
