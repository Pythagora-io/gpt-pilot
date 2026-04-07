import { Type } from "@sinclair/typebox";
import { upsertAuthProfileWithLock } from "openclaw/plugin-sdk/agent-runtime";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import {
  buildCredential,
  buildProfileId,
  normalizeLabel,
  normalizeSecretValue,
  normalizeService,
  parseProfileId,
  type SavedCredentialType,
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

export function createSaveCredentialTool(): AnyAgentTool {
  return {
    name: "save_credential",
    label: "Save Credential",
    description:
      "Persist a user-provided API key or token into the agent's secure credential store " +
      "(auth-profiles.json). Use after ask_for_credentials so the user does not need to " +
      "re-enter credentials next session. Check list_saved_credentials first to avoid duplicates.",
    parameters: Type.Object(
      {
        service: Type.String({
          description: "Provider/service name, e.g. 'github' or 'openai'",
        }),
        type: Type.Unsafe<SavedCredentialType>({
          type: "string",
          enum: ["api_key", "token"],
          description: 'Credential type: "api_key" or "token"',
        }),
        key: Type.String({
          description: "The credential value (API key or token)",
        }),
        label: Type.Optional(
          Type.String({
            description:
              "Optional profile label for disambiguation (e.g. 'work-account'). Defaults to 'default'.",
          }),
        ),
        metadata: Type.Optional(
          Type.Record(Type.String(), Type.String(), {
            description: "Optional key-value metadata (e.g. { email: 'user@example.com' })",
          }),
        ),
      },
      { additionalProperties: false },
    ),
    async execute(_toolCallId: string, params: Record<string, unknown>) {
      try {
        const service = normalizeService(params.service);
        if (!service) throw new Error("service is required");

        const type = params.type as string;
        if (type !== "api_key" && type !== "token") {
          throw new Error('type must be "api_key" or "token"');
        }

        const key = normalizeSecretValue(params.key);
        if (!key) throw new Error("key must be a non-empty string");

        const label = normalizeLabel(params.label);
        const metadata =
          params.metadata && typeof params.metadata === "object"
            ? (params.metadata as Record<string, string>)
            : undefined;

        const profileId = buildProfileId(service, label);
        const credential = buildCredential({ service, type, key, metadata });

        const updated = await upsertAuthProfileWithLock({
          profileId,
          credential,
        });

        if (!updated) {
          throw new Error("Failed to write to auth-profiles.json");
        }

        const parsed = parseProfileId(profileId, service);
        return {
          content: [
            {
              type: "text" as const,
              text: `Saved ${type} credential for ${service} as profile "${profileId}".`,
            },
          ],
          details: {
            status: "saved",
            profileId,
            service,
            type,
            label: parsed.label,
          },
        };
      } catch (err) {
        return json({ error: err instanceof Error ? err.message : String(err) });
      }
    },
  };
}
