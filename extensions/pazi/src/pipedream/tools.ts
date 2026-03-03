import { Type } from "@sinclair/typebox";
import type { AnyAgentTool, OpenClawConfig } from "openclaw/plugin-sdk";
import { callGateway } from "../../../../src/gateway/call.js";
import {
  checkIntegration,
  listActions,
  runAction,
  searchApps,
  type PipedreamApiResult,
} from "./api.js";

export type PipedreamToolsDeps = {
  pluginConfig: Record<string, unknown> | null;
  config: OpenClawConfig;
};

type AgentToolResult = {
  content: Array<{ type: "text"; text: string }>;
  details?: unknown;
};

function json(payload: unknown): AgentToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    details: payload,
  };
}

function readRequiredString(params: Record<string, unknown>, key: string): string {
  const value = params[key];
  if (typeof value !== "string") {
    throw new Error(`${key} required`);
  }
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${key} required`);
  }
  return trimmed;
}

function readOptionalString(params: Record<string, unknown>, key: string): string | undefined {
  const value = params[key];
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function readOptionalNumber(params: Record<string, unknown>, key: string): number | undefined {
  const value = params[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return undefined;
  }
  return value;
}

function coerceLimit(value: number | undefined): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return undefined;
  }
  return Math.floor(value);
}

function unwrapResult(result: PipedreamApiResult<unknown>): AgentToolResult {
  if (result.ok) {
    return json(result.data);
  }
  return json({ error: result.error });
}

async function sleep(ms: number, signal?: AbortSignal): Promise<"ok" | "aborted"> {
  if (signal?.aborted) {
    return "aborted";
  }
  return await new Promise<"ok" | "aborted">((resolve) => {
    const timer = setTimeout(() => {
      resolve("ok");
    }, ms);
    if (!signal) {
      return;
    }
    const onAbort = () => {
      clearTimeout(timer);
      resolve("aborted");
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

export function createPipedreamTools(deps: PipedreamToolsDeps): AnyAgentTool[] {
  return [
    {
      name: "mcp__pipedream__find_integrations",
      label: "Pipedream: Find Integrations",
      description: "Search Pipedream integrations/apps by name.",
      parameters: Type.Object(
        {
          query: Type.String({ description: "Search query." }),
          limit: Type.Optional(Type.Number({ description: "Maximum results to return." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const query = readRequiredString(params, "query");
          const limit = coerceLimit(readOptionalNumber(params, "limit"));
          const result = await searchApps({ pluginConfig: deps.pluginConfig }, query, limit);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "mcp__pipedream__list_actions",
      label: "Pipedream: List Actions",
      description: "List available actions for a Pipedream app.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          limit: Type.Optional(Type.Number({ description: "Maximum results to return." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const limit = coerceLimit(readOptionalNumber(params, "limit"));
          const result = await listActions({ pluginConfig: deps.pluginConfig }, app, limit);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "mcp__pipedream__check_integration",
      label: "Pipedream: Check Integration",
      description: "Check whether a Pipedream integration is connected.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const result = await checkIntegration({ pluginConfig: deps.pluginConfig }, app);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "mcp__pipedream__use_integration",
      label: "Pipedream: Use Integration",
      description: "Run a Pipedream action for a connected integration.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          actionId: Type.String({ description: "Action id to invoke." }),
          configuredProps: Type.Optional(
            Type.Record(Type.String(), Type.Unknown(), {
              description: "Configured properties for the action.",
            }),
          ),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const actionId = readRequiredString(params, "actionId");
          const configuredProps = params.configuredProps;
          if (
            configuredProps !== undefined &&
            (typeof configuredProps !== "object" ||
              configuredProps === null ||
              Array.isArray(configuredProps))
          ) {
            throw new Error("configuredProps must be an object");
          }
          const result = await runAction(
            { pluginConfig: deps.pluginConfig },
            app,
            actionId,
            configuredProps as Record<string, unknown> | undefined,
          );
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "mcp__pipedream__request_integration",
      label: "Pipedream: Request Integration",
      description: "Prompt the UI to connect a Pipedream integration.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          message: Type.Optional(Type.String({ description: "Optional message to display." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const message = readOptionalString(params, "message");
          const result = await callGateway({
            method: "pazi.integration.emit",
            params: { action: "required", app, message },
            config: deps.config,
          });
          return json(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "mcp__pipedream__wait_for_connection",
      label: "Pipedream: Wait For Connection",
      description: "Poll until a Pipedream integration is connected.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          timeoutMs: Type.Optional(
            Type.Number({ description: "Total time to wait before timing out." }),
          ),
          pollIntervalMs: Type.Optional(Type.Number({ description: "Delay between polls." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>, signal?: AbortSignal) {
        try {
          const app = readRequiredString(params, "app");
          const timeoutMs = readOptionalNumber(params, "timeoutMs");
          const pollIntervalMs = readOptionalNumber(params, "pollIntervalMs");
          const resolvedTimeoutMs =
            typeof timeoutMs === "number" && timeoutMs > 0 ? timeoutMs : 120_000;
          const resolvedPollMs =
            typeof pollIntervalMs === "number" && pollIntervalMs > 0 ? pollIntervalMs : 3_000;
          const deadline = Date.now() + resolvedTimeoutMs;

          while (true) {
            if (signal?.aborted) {
              return json({ status: "aborted" });
            }

            const result = await checkIntegration({ pluginConfig: deps.pluginConfig }, app);
            if (!result.ok) {
              return json({ error: result.error });
            }

            const payload =
              result.data && typeof result.data === "object"
                ? (result.data as { connected?: unknown; accountId?: unknown })
                : undefined;
            if (payload?.connected === true) {
              const accountId =
                typeof payload.accountId === "string" ? payload.accountId : undefined;
              return json({ status: "connected", accountId });
            }

            const now = Date.now();
            if (now >= deadline) {
              return json({ status: "timeout" });
            }

            const waitMs = Math.min(resolvedPollMs, deadline - now);
            const slept = await sleep(waitMs, signal);
            if (slept === "aborted") {
              return json({ status: "aborted" });
            }
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
  ];
}
