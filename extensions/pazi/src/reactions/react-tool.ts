/**
 * Agent tool: react_to_message
 *
 * Allows the agent to react to a user message with an emoji in webchat.
 * Persists reaction via API and broadcasts to frontend via WebSocket.
 *
 * When no messageId is provided, stores the reaction with a "latest-user"
 * sentinel that the frontend resolves to the most recent user message.
 */
import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { getPluginRuntimeGatewayRequestScope } from "openclaw/plugin-sdk/plugin-runtime";
import { resolvePaziBillingConfig } from "../config.js";
import { getProxyContext } from "../context.js";

const ALLOWED_EMOJIS = [
  "\u{1F64C}", // 🙌
  "\u{1F44D}", // 👍
  "\u{2764}\u{FE0F}", // ❤️
  "\u{1F389}", // 🎉
  "\u{1F525}", // 🔥
  "\u{1F440}", // 👀
  "\u{1F914}", // 🤔
  "\u{1F602}", // 😂
  "\u{1F937}", // 🤷
];

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

function broadcastReactionEvent(payload: Record<string, unknown>): void {
  const scope = getPluginRuntimeGatewayRequestScope();
  if (!scope?.context) {
    return; // Cannot broadcast outside gateway scope — non-fatal
  }
  scope.context.broadcast("integration", payload);
}

/**
 * Sentinel messageId used when the agent reacts without specifying a target.
 * The frontend resolves this to the most recent user message in the session.
 */
const LATEST_USER_SENTINEL = "latest-user";

export function createReactToMessageTool(deps: {
  pluginConfig: Record<string, unknown> | null;
}): AnyAgentTool {
  return {
    name: "react_to_message",
    label: "React to Message",
    description:
      "React to a user message in web chat with an emoji. Use this in webchat sessions (not Slack/Discord — those use the message tool with action=react). Call this to express appreciation, acknowledgment, or humor in response to the user's messages. The reaction appears as a badge below their message. You don't need to provide a messageId — it automatically reacts to the most recent user message. Available emojis: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷",
    parameters: Type.Object(
      {
        emoji: Type.String({
          description: "The emoji to react with. Must be one of: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷",
        }),
        messageId: Type.Optional(
          Type.String({
            description:
              "Optional: the stable ID of the user message to react to. If omitted, automatically reacts to the most recent user message.",
          }),
        ),
      },
      { additionalProperties: false },
    ),
    async execute(_toolCallId: string, params: Record<string, unknown>): Promise<AgentToolResult> {
      const explicitMessageId = typeof params.messageId === "string" ? params.messageId.trim() : "";
      const emoji = typeof params.emoji === "string" ? params.emoji : "";

      if (!emoji) {
        return json({ error: "emoji is required" });
      }

      if (!ALLOWED_EMOJIS.includes(emoji)) {
        return json({ error: `Invalid emoji. Allowed: ${ALLOWED_EMOJIS.join(" ")}` });
      }

      // Resolve API connection
      const context = getProxyContext();
      if (!context) {
        return json({ error: "No proxy context — workspace not initialized" });
      }

      const resolved = resolvePaziBillingConfig({
        pluginConfig: deps.pluginConfig,
        env: process.env,
      });
      const apiUrl = resolved.apiUrl?.trim();
      if (!apiUrl) {
        return json({ error: "PAZI_API_URL not configured" });
      }

      if (!context.agentId) {
        return json({ error: "No active agent — cannot determine session key" });
      }

      // Derive session key from agent ID (pattern: agent:{agentId}:main)
      const sessionKey = `agent:${context.agentId}:main`;

      // Use explicit messageId if provided, otherwise use the "latest-user" sentinel
      // The frontend resolves the sentinel to the most recent user message
      const messageId = explicitMessageId || LATEST_USER_SENTINEL;

      try {
        // Persist reaction via API
        const url = new URL("/chat/reactions/agent", apiUrl);
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-proxy-token": context.proxyToken,
          },
          body: JSON.stringify({
            sessionKey,
            messageId,
            messageRole: "user",
            emoji,
          }),
        });

        if (!response.ok) {
          const text = await response.text().catch(() => "");
          return json({ error: `API error (${response.status}): ${text}` });
        }

        // Broadcast to frontend via WebSocket
        broadcastReactionEvent({
          action: "reaction_added",
          messageId,
          emoji,
          actor: "agent",
        });

        return json({ success: true, messageId, emoji });
      } catch (err) {
        return json({ error: err instanceof Error ? err.message : String(err) });
      }
    },
  };
}
