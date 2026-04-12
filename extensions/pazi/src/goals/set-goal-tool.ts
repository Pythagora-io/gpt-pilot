import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { getPluginRuntimeGatewayRequestScope } from "openclaw/plugin-sdk/plugin-runtime";
import { createUserAction, getUserAction } from "../user-actions/api.js";

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

export function createSetGoalTool(deps: SetGoalToolDeps): AnyAgentTool {
  return {
    name: "set_goal",
    label: "Set Goal",
    description:
      "Propose a goal for the user with a tracking plan. Opens a confirmation card in the user's dashboard " +
      "showing the goal details and scheduled check-ins. The user can confirm or reject. " +
      "Use this when the user asks you to set, create, or track a goal. " +
      "IMPORTANT: Before calling this tool, ask the user questions to understand the goal deeply — " +
      "what metrics to track, what integrations they use (Twitter, Google Analytics, etc.), " +
      "how often they want check-ins (daily, weekly, monthly). Then create a comprehensive plan " +
      "with specific scheduled tasks that will proactively track progress and determine next steps. " +
      "Each scheduled check-in should be actionable — not just 'check progress' but 'analyze metrics, " +
      "compare to target, and suggest specific actions to stay on track'. " +
      "Returns the created goal ID on confirmation.",
    parameters: Type.Object(
      {
        title: Type.String({ description: "Short goal title (max 500 chars)" }),
        description: Type.Optional(
          Type.String({ description: "Detailed goal description (max 5000 chars)" }),
        ),
        targetDate: Type.Optional(
          Type.String({ description: "Target completion date (ISO 8601, e.g. '2026-05-01')" }),
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
        timeoutMs: Type.Optional(
          Type.Number({ description: "Max wait time in ms (default: 300000)" }),
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
        const title = typeof params.title === "string" ? params.title.trim() : "";
        const description =
          typeof params.description === "string" ? params.description.trim() : undefined;
        const targetDate =
          typeof params.targetDate === "string" ? params.targetDate.trim() : undefined;
        const scheduledCheckIns = Array.isArray(params.scheduledCheckIns)
          ? params.scheduledCheckIns
          : undefined;
        const timeoutMs =
          typeof params.timeoutMs === "number" && params.timeoutMs > 0 ? params.timeoutMs : 300_000;
        const pollIntervalMs =
          typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0
            ? params.pollIntervalMs
            : 3_000;

        if (!title) {
          throw new Error("title is required");
        }

        const proposal = {
          title,
          description: description || undefined,
          targetDate: targetDate || undefined,
          scheduledCheckIns: scheduledCheckIns || undefined,
        };

        // 1. Create user action request
        const created = await createUserAction(deps.pluginConfig, {
          kind: "goal_confirmation",
          service: "Goals",
          message: `Goal proposal: ${title}`,
          proposal,
        });
        if (!created.ok) {
          return json({ error: created.error });
        }
        const requestId = created.data.request.requestId;

        // 2. Emit integration event to frontend
        emitIntegrationEvent({
          action: "goal_proposed",
          requestId,
          ...proposal,
        });

        // 3. Poll until resolved
        const deadline = Date.now() + timeoutMs;
        while (true) {
          if (signal?.aborted) {
            return json({ status: "aborted", requestId });
          }

          const result = await getUserAction(deps.pluginConfig, requestId);
          if (!result.ok) {
            return json({ error: result.error });
          }

          const { status } = result.data.request;
          if (status === "completed") {
            const goalId = (result.data.request as Record<string, unknown>).result as
              | { goalId?: string }
              | undefined;
            return json({
              status: "completed",
              requestId,
              goalId: goalId?.goalId,
              message: `Goal "${title}" has been confirmed and created.`,
            });
          }
          if (status === "cancelled") {
            return json({
              status: "cancelled",
              requestId,
              message: `Goal "${title}" was rejected by the user.`,
            });
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
      } catch (err) {
        return json({ error: err instanceof Error ? err.message : String(err) });
      }
    },
  };
}
