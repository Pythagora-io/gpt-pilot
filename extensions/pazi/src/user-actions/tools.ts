import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { getPluginRuntimeGatewayRequestScope } from "openclaw/plugin-sdk/plugin-runtime";
import { getProxyContext } from "../context.js";
import { buildBrowserPermissionUrl } from "../dashboard-url.js";
import { createUserAction, getUserAction } from "./api.js";

export type UserActionToolsDeps = {
  pluginConfig: Record<string, unknown> | null;
  onBrowserPermissionGranted?: () => Promise<void>;
};

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

function emitIntegrationEvent(payload: Record<string, unknown>): void {
  const scope = getPluginRuntimeGatewayRequestScope();
  if (!scope?.context) {
    throw new Error("Cannot emit outside a gateway request.");
  }
  scope.context.broadcast("integration", payload);
}

async function pollUntilResolved(
  pluginConfig: Record<string, unknown> | null,
  requestId: string,
  service: string,
  kind: "credentials" | "browser_login" | "browser_permission",
  timeoutMs: number,
  pollIntervalMs: number,
  signal?: AbortSignal,
): Promise<AgentToolResult> {
  const deadline = Date.now() + timeoutMs;

  while (true) {
    if (signal?.aborted) {
      return json({ status: "aborted", requestId });
    }

    const result = await getUserAction(pluginConfig, requestId);
    if (!result.ok) {
      return json({ error: result.error });
    }

    const { status } = result.data.request;
    if (status === "completed") {
      const req = result.data.request;
      if (kind === "credentials") {
        const values = req.result?.values ?? {};
        // Safe summary in content (visible in UI/transcripts); raw values in details (model-only)
        return {
          content: [
            {
              type: "text",
              text:
                `Credentials received securely for ${service}. Fields: ${Object.keys(values).join(", ")}\n` +
                "Tip: use save_credential to persist these for future sessions.",
            },
          ],
          details: { status: "completed", requestId, service, values },
        };
      }
      if (kind === "browser_permission") {
        return json({
          status: "completed",
          requestId,
          enabled: true,
          message: "Browser permission granted. Browsing tools are now available.",
        });
      }
      return json({
        status: "completed",
        requestId,
        service,
        confirmed: true,
      });
    }
    if (status === "cancelled") {
      return json({ status: "cancelled", requestId, service });
    }
    if (status === "expired") {
      return json({ status: "expired", requestId });
    }

    if (Date.now() >= deadline) {
      return json({ status: "timeout", requestId });
    }

    const waitMs = Math.min(pollIntervalMs, deadline - Date.now());
    if (waitMs > 0) {
      const slept = await sleep(waitMs, signal);
      if (slept === "aborted") {
        return json({ status: "aborted", requestId });
      }
    }
  }
}

export function createUserActionTools(deps: UserActionToolsDeps): AnyAgentTool[] {
  return [
    {
      name: "ask_for_credentials",
      label: "Ask For Credentials",
      description:
        "Prompt the user to enter credentials (API keys, passwords, tokens). " +
        "Opens a secure form in the user's dashboard. Waits for the user to submit " +
        "and returns the entered values. Works in all session types (text, voice, web, Slack). " +
        "Use when you need credentials for a third-party service.",
      parameters: Type.Object(
        {
          service: Type.String({ description: "Name of the service (e.g., 'GitHub', 'AWS')" }),
          fields: Type.Array(Type.String(), {
            description: "Credential field names to request (e.g., ['api_key', 'secret'])",
          }),
          message: Type.Optional(
            Type.String({ description: "Explanation of why credentials are needed" }),
          ),
          timeoutMs: Type.Optional(
            Type.Number({ description: "Max wait time in ms (default: 120000)" }),
          ),
          pollIntervalMs: Type.Optional(
            Type.Number({ description: "Poll interval in ms (default: 3000)" }),
          ),
        },
        { additionalProperties: false },
      ),
      // oxlint-disable-next-line typescript/no-explicit-any
      async execute(_toolCallId: string, params: any, signal?: AbortSignal) {
        try {
          const service = typeof params.service === "string" ? params.service.trim() : "";
          const fields = params.fields as unknown;
          const message = typeof params.message === "string" ? params.message.trim() : undefined;
          const timeoutMs =
            typeof params.timeoutMs === "number" && params.timeoutMs > 0
              ? params.timeoutMs
              : 120_000;
          const pollIntervalMs =
            typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0
              ? params.pollIntervalMs
              : 3_000;

          if (!service) {
            throw new Error("service is required");
          }
          if (!Array.isArray(fields) || fields.length === 0) {
            throw new Error("fields must be a non-empty array of strings");
          }

          const fieldNames = fields.map((f) => (typeof f === "string" ? f.trim() : String(f)));

          // 1. Create API request
          const created = await createUserAction(deps.pluginConfig, {
            kind: "credentials",
            service,
            fields: fieldNames,
            message: message || undefined,
          });
          if (!created.ok) {
            return json({ error: created.error });
          }
          const requestId = created.data.request.requestId;

          // 2. Emit event to frontend
          emitIntegrationEvent({
            action: "credentials_required",
            requestId,
            service,
            fields: fieldNames,
            message: message || undefined,
          });

          // 3. Poll until resolved
          return await pollUntilResolved(
            deps.pluginConfig,
            requestId,
            service,
            "credentials",
            timeoutMs,
            pollIntervalMs,
            signal,
          );
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "ask_for_browser_login",
      label: "Ask For Browser Login",
      description:
        "Prompt the user to log into a website in their browser. " +
        "Opens a card in the dashboard with a link and confirmation button. " +
        "Waits for the user to confirm they've logged in. Works in all session types. " +
        "Use when the agent needs cookie-based authentication or the service has no API integration.",
      parameters: Type.Object(
        {
          service: Type.String({ description: "Name of the service (e.g., 'Google', 'Jira')" }),
          url: Type.String({ description: "URL to open for login" }),
          message: Type.Optional(Type.String({ description: "Instructions for the user" })),
          timeoutMs: Type.Optional(
            Type.Number({ description: "Max wait time in ms (default: 120000)" }),
          ),
          pollIntervalMs: Type.Optional(
            Type.Number({ description: "Poll interval in ms (default: 3000)" }),
          ),
        },
        { additionalProperties: false },
      ),
      // oxlint-disable-next-line typescript/no-explicit-any
      async execute(_toolCallId: string, params: any, signal?: AbortSignal) {
        try {
          const service = typeof params.service === "string" ? params.service.trim() : "";
          const url = typeof params.url === "string" ? params.url.trim() : "";
          const message = typeof params.message === "string" ? params.message.trim() : undefined;
          const timeoutMs =
            typeof params.timeoutMs === "number" && params.timeoutMs > 0
              ? params.timeoutMs
              : 120_000;
          const pollIntervalMs =
            typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0
              ? params.pollIntervalMs
              : 3_000;

          if (!service) {
            throw new Error("service is required");
          }
          if (!url) {
            throw new Error("url is required");
          }

          // 1. Create API request
          const created = await createUserAction(deps.pluginConfig, {
            kind: "browser_login",
            service,
            url,
            message: message || undefined,
          });
          if (!created.ok) {
            return json({ error: created.error });
          }
          const requestId = created.data.request.requestId;

          // 2. Emit event to frontend
          emitIntegrationEvent({
            action: "browser_login_required",
            requestId,
            service,
            url,
            message: message || undefined,
          });

          // 3. Poll until resolved
          return await pollUntilResolved(
            deps.pluginConfig,
            requestId,
            service,
            "browser_login",
            timeoutMs,
            pollIntervalMs,
            signal,
          );
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "request_browser_permission",
      label: "Request Browser Permission",
      description:
        "Ask the user to enable web browsing for this workspace. " +
        "Use this when you need to use browser, web_search, web_fetch, or browser_use tools " +
        "but they are currently disabled. Opens a permission dialog in the user's dashboard. " +
        "Returns immediately with a dashboard URL — share it with the user so they can enable browsing from any device or channel.",
      parameters: Type.Object(
        {
          message: Type.Optional(
            Type.String({ description: "Explain to the user why browsing is needed" }),
          ),
        },
        { additionalProperties: false },
      ),
      // oxlint-disable-next-line typescript/no-explicit-any
      async execute(_toolCallId: string, params: any) {
        try {
          const message = typeof params.message === "string" ? params.message.trim() : undefined;

          // 1. Create user action request
          const created = await createUserAction(deps.pluginConfig, {
            kind: "browser_permission",
            service: "Web Browsing",
            message: message || undefined,
          });
          if (!created.ok) {
            return json({ error: created.error });
          }
          const requestId = created.data.request.requestId;

          // 2. Emit event to frontend (shows dialog for web dashboard users)
          emitIntegrationEvent({
            action: "browser_permission_required",
            requestId,
            message: message || undefined,
          });

          // 3. Build dashboard URL for non-web sessions (e.g. Slack)
          const ctx = getProxyContext();
          const dashboardUrl = buildBrowserPermissionUrl(ctx?.dashboardBaseUrl, requestId);

          // 4. Return immediately (non-blocking) — the agent can share the URL
          const contentText = dashboardUrl
            ? `Browser permission requested. If the user is not on the web dashboard, share this link: ${dashboardUrl}`
            : "Browser permission requested. The user has been prompted on the web dashboard.";

          return {
            content: [{ type: "text" as const, text: contentText }],
            details: {
              status: "pending",
              requestId,
              dashboardUrl,
            },
          };
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
  ];
}
