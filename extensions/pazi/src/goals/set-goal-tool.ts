import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { getPluginRuntimeGatewayRequestScope } from "openclaw/plugin-sdk/plugin-runtime";
import { resolvePaziBillingConfig } from "../config.js";
import { getProxyContext } from "../context.js";

export type SetGoalToolDeps = {
  pluginConfig: Record<string, unknown> | null;
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

function emitIntegrationEvent(payload: Record<string, unknown>): void {
  const scope = getPluginRuntimeGatewayRequestScope();
  if (!scope?.context) {
    throw new Error("Cannot emit outside a gateway request.");
  }
  scope.context.broadcast("integration", payload);
}

interface GoalApiResult {
  ok: true;
  data: { goal: { id: string; [key: string]: unknown } };
}

interface GoalApiError {
  ok: false;
  error: string;
}

async function createGoalViaApi(
  pluginConfig: Record<string, unknown> | null,
  body: Record<string, unknown>,
): Promise<GoalApiResult | GoalApiError> {
  const context = getProxyContext();
  if (!context) {
    return { ok: false, error: "No billing context set — workspace may not be initialized yet" };
  }

  const resolved = resolvePaziBillingConfig({ pluginConfig, env: process.env });
  const apiUrl = resolved.apiUrl?.trim();
  if (!apiUrl) {
    return { ok: false, error: "PAZI_API_URL not configured" };
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(apiUrl);
  } catch {
    return { ok: false, error: `Invalid PAZI_API_URL: ${apiUrl}` };
  }

  const url = new URL("/goals", baseUrl);
  const headers = new Headers();
  headers.set("x-proxy-token", context.proxyToken);
  headers.set("Content-Type", "application/json");

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  const text = await res.text();
  const payload = text.trim() ? (JSON.parse(text) as Record<string, unknown>) : null;

  if (res.ok && payload) {
    return { ok: true, data: payload as GoalApiResult["data"] };
  }

  const record = payload as { error?: string; message?: string } | null;
  const errMsg = record?.error ?? record?.message ?? res.statusText ?? "Request failed";
  return { ok: false, error: `Pazi API error (${res.status}): ${errMsg}` };
}

export function createSetGoalTool(deps: SetGoalToolDeps): AnyAgentTool {
  return {
    name: "set_goal",
    label: "Set Goal",
    description:
      "Create a goal for the user with a tracking plan. The goal is created immediately and a display card " +
      "appears in the user's dashboard showing the goal details and scheduled check-ins. " +
      "Use this when the user asks you to set, create, or track a goal. " +
      "IMPORTANT: Before calling this tool, ask the user questions to understand the goal deeply — " +
      "what metrics to track, what integrations they use (Twitter, Google Analytics, etc.), " +
      "how often they want check-ins (daily, weekly, monthly). Then create a comprehensive plan " +
      "with specific scheduled tasks that will proactively track progress and determine next steps. " +
      "Each scheduled check-in should be actionable — not just 'check progress' but 'analyze metrics, " +
      "compare to target, and suggest specific actions to stay on track'. " +
      "Returns the created goal ID and details.",
    parameters: Type.Object(
      {
        title: Type.String({ description: "Short goal title (max 500 chars)" }),
        description: Type.Optional(
          Type.String({ description: "Detailed goal description (max 5000 chars)" }),
        ),
        targetDate: Type.Optional(
          Type.String({ description: "Target completion date (ISO 8601, e.g. '2026-05-01')" }),
        ),
        startingValue: Type.Optional(
          Type.Number({ description: "Starting metric value (e.g. 0, 100)" }),
        ),
        targetValue: Type.Optional(
          Type.Number({ description: "Target metric value (e.g. 1000, 50)" }),
        ),
        metricLabel: Type.Optional(
          Type.String({ description: "Metric label (e.g. 'followers', 'users', 'posts')" }),
        ),
        scheduledCheckIns: Type.Optional(
          Type.Array(
            Type.Object({
              name: Type.String({ description: "Check-in task name" }),
              schedule: Type.String({ description: "Cron expression for check-in schedule" }),
              description: Type.Optional(Type.String({ description: "Check-in description" })),
            }),
            { description: "Proposed scheduled check-ins for tracking this goal" },
          ),
        ),
      },
      { additionalProperties: false },
    ),
    // oxlint-disable-next-line typescript/no-explicit-any
    async execute(_toolCallId: string, params: any, _signal?: AbortSignal) {
      try {
        const title = typeof params.title === "string" ? params.title.trim() : "";
        const description =
          typeof params.description === "string" ? params.description.trim() : undefined;
        const targetDate =
          typeof params.targetDate === "string" ? params.targetDate.trim() : undefined;
        const startingValue =
          typeof params.startingValue === "number" ? params.startingValue : undefined;
        const targetValue = typeof params.targetValue === "number" ? params.targetValue : undefined;
        const metricLabel =
          typeof params.metricLabel === "string" ? params.metricLabel.trim() : undefined;
        const scheduledCheckIns = Array.isArray(params.scheduledCheckIns)
          ? params.scheduledCheckIns
          : undefined;

        if (!title) {
          throw new Error("title is required");
        }

        const context = getProxyContext();
        if (!context) {
          throw new Error("No proxy context available — workspace may not be initialized yet");
        }

        // Create the goal directly via Pazi API — no user confirmation needed
        const result = await createGoalViaApi(deps.pluginConfig, {
          agentId: context.agentId,
          title,
          description: description || undefined,
          targetDate: targetDate || undefined,
          startingValue,
          targetValue,
          currentValue: startingValue, // Start at the starting value
          metricLabel: metricLabel || undefined,
          scheduledTaskIds: [], // Frontend creates cron jobs and updates this
        });

        if (!result.ok) {
          return json({ error: result.error });
        }

        const goal = result.data.goal;

        // Emit integration event so frontend shows the goal card and creates cron jobs
        emitIntegrationEvent({
          action: "goal_created",
          goalId: goal.id,
          title,
          description: description || undefined,
          targetDate: targetDate || undefined,
          startingValue,
          targetValue,
          currentValue: startingValue,
          metricLabel: metricLabel || undefined,
          scheduledCheckIns: scheduledCheckIns || undefined,
        });

        return json({
          status: "created",
          goalId: goal.id,
          title,
          message: `Goal "${title}" has been created successfully.`,
        });
      } catch (err) {
        return json({ error: err instanceof Error ? err.message : String(err) });
      }
    },
  };
}
