import { Type } from "@sinclair/typebox";
import { loadAuthProfileStoreForSecretsRuntime } from "openclaw/plugin-sdk/agent-runtime";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import {
  extractCredentialValue,
  findCredential,
  listLabelsForService,
  normalizeService,
  parseProfileId,
} from "./shared.js";

type AgentToolResult = {
  content: Array<{ type: "text"; text: string }>;
  details: unknown;
};

function json(payload: unknown): AgentToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    details: payload,
  };
}

export function createGetCredentialTool(): AnyAgentTool {
  return {
    name: "get_credential",
    label: "Get Credential",
    description:
      "Retrieve a previously saved credential value for use in the current session. " +
      "The secret is returned securely (stripped from transcript persistence). " +
      "If multiple profiles exist for a service, specify a label or call " +
      "list_saved_credentials first.",
    parameters: Type.Object(
      {
        service: Type.String({
          description: "Provider/service name (e.g. 'github')",
        }),
        label: Type.Optional(
          Type.String({
            description:
              "Profile label (e.g. 'work-account'). If omitted, returns the " +
              "'default' profile or the sole profile for that service.",
          }),
        ),
      },
      { additionalProperties: false },
    ),
    async execute(_toolCallId: string, params: Record<string, unknown>) {
      try {
        const service = normalizeService(params.service);
        if (!service) throw new Error("service is required");

        const label =
          typeof params.label === "string" && params.label.trim() ? params.label.trim() : undefined;

        const store = loadAuthProfileStoreForSecretsRuntime();
        const match = findCredential(store, service, label);

        if (!match) {
          if (!label) {
            const labels = listLabelsForService(store, service);
            if (labels.length > 1) {
              return json({
                error:
                  `Multiple credentials found for ${service}: ${labels.join(", ")}. ` +
                  "Specify a label, or call list_saved_credentials to see all profiles.",
              });
            }
          }
          return json({
            error: label
              ? `No saved credential found for ${service} with label "${label}".`
              : `No saved credential found for ${service}.`,
          });
        }

        const { profileId, credential } = match;
        const value = extractCredentialValue(credential);
        if (!value) {
          return json({
            error: `Credential ${profileId} exists but has no inline secret value.`,
          });
        }

        const parsed = parseProfileId(profileId, credential.provider);
        return {
          content: [
            {
              type: "text" as const,
              text: `Retrieved saved credential "${profileId}" for ${service}.`,
            },
          ],
          details: {
            status: "ok",
            profileId,
            service: parsed.service,
            type: credential.type,
            label: parsed.label,
            value,
            ...(credential.type === "api_key" && credential.metadata
              ? { metadata: credential.metadata }
              : {}),
            ...(credential.email ? { email: credential.email } : {}),
          },
        };
      } catch (err) {
        return json({ error: err instanceof Error ? err.message : String(err) });
      }
    },
  };
}
