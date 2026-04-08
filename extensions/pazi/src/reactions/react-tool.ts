/**
 * Agent tool: react_to_message
 *
 * Allows the agent to react to a user message with an emoji.
 * Persists reaction via API and broadcasts to frontend via WebSocket.
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

export function createReactToMessageTool(deps: {
  pluginConfig: Record<string, unknown> | null;
}): AnyAgentTool {
  return {
    name: "react_to_message",
    label: "React to Message",
    description:
      "React to a user message with an emoji. Use this to express appreciation, acknowledgment, or other reactions to the user's messages. Available emojis: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷",
    parameters: Type.Object(
      {
        messageId: Type.String({
          description:
            "The stable ID of the user message to react to. This is typically the message ID from the conversation context.",
        }),
        emoji: Type.String({
          description:
            "The emoji to react with. Must be one of: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷",
        }),
      },
      { additionalProperties: false },
    ),
    async execute(
      _toolCallId: string,
      params: Record<string, unknown>,
    ): Promise<AgentToolResult> {
      const messageId = typeof params.messageId === "string" ? params.messageId : "";
      const emoji = typeof params.emoji === "string" ? params.emoji : "";

      if (!messageId || !emoji) {
        return json({ error: "messageId and emoji are required" });
      }

      if (!ALLOWED_EMOJIS.includes(emoji)) {
        return json({ error: `Invalid emoji. Allowed: ${ALLOWED_EMOJIS.join(" ")}` });
      }

      // Resolve API connection
      const context = getProxyContext();
      if (!context) {
        return json({ error: "No proxy context — workspace not initialized" });
      }

      const resolved = resolvePaziBillingConfig({ pluginConfig: deps.pluginConfig, env: process.env });
      const apiUrl = resolved.apiUrl?.trim();
      if (!apiUrl) {
        return json({ error: "PAZI_API_URL not configured" });
      }

      // Derive session key from agent ID (pattern: agent:{agentId}:main)
      const sessionKey = `agent:${context.agentId}:main`;
      if (!context.agentId) {
        return json({ error: "No active agent — cannot determine session key" });
      }

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
