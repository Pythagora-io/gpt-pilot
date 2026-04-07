import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { getProxyContext, setProxyContext } from "../context.js";

/**
 * Keep proxy context agentId aligned with the active tool-call agent.
 *
 * Chat connections can be long-lived and span multiple agent sessions.
 * Without this sync, integrations can be scoped to a stale/default agent.
 */
export function registerProxyAgentSyncHook(api: OpenClawPluginApi): void {
  api.on(
    "before_tool_call",
    (_event, ctx) => {
      const nextAgentId = typeof ctx.agentId === "string" ? ctx.agentId.trim() : "";
      if (!nextAgentId) {
        return;
      }

      const current = getProxyContext();
      if (!current || current.agentId === nextAgentId) {
        return;
      }

      setProxyContext({ ...current, agentId: nextAgentId });
    },
    { priority: 20 },
  );
}
