import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { registerSlackReplySuppression } from "../../slack/src/reply-suppression.js";
import { sendMessageSlack } from "../../slack/src/send.js";

// ── Types ──────────────────────────────────────────────────────────────

export type SlackThreadReplyMode = "full" | "summary-only" | "quiet";

type ResolvedThreadReplyConfig = {
  mode: SlackThreadReplyMode;
  ackMessage: string;
};

type SuppressedThread = {
  accountId: string;
  /** Bare Slack target ID (e.g. "C123" or "U123") — used for tracking key. */
  targetId: string;
  /** Full target string for sendMessageSlack (e.g. "channel:C123" or "user:U123"). */
  sendTarget: string;
  threadTs: string;
  mode: SlackThreadReplyMode;
  ackMessage: string;
  ackSent: boolean;
};

// ── Constants ──────────────────────────────────────────────────────────

const DEFAULT_ACK_MESSAGE = "On it";

// ── Config Resolution ──────────────────────────────────────────────────

export function resolveThreadReplyConfig(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  cfg: Record<string, any>,
  accountId: string,
): ResolvedThreadReplyConfig {
  const account = cfg?.channels?.slack?.accounts?.[accountId];
  if (!account || typeof account !== "object") {
    return { mode: "full", ackMessage: DEFAULT_ACK_MESSAGE };
  }
  const raw = account as Record<string, unknown>;
  const mode: SlackThreadReplyMode =
    raw.threadReplyMode === "summary-only" || raw.threadReplyMode === "quiet"
      ? raw.threadReplyMode
      : "full";
  const ackMessage =
    typeof raw.ackMessage === "string" && raw.ackMessage.trim()
      ? raw.ackMessage.trim()
      : DEFAULT_ACK_MESSAGE;
  return { mode, ackMessage };
}

// ── Helpers ────────────────────────────────────────────────────────────

/**
 * Extract the Slack target ID from a `from` or `conversationId` string.
 * Observed formats: "channel:C123", "user:U123", "slack:C123", "C123"
 * Returns the bare ID (C/G/D/U prefix + alphanumeric).
 */
function extractSlackTargetId(from: string): string | null {
  const match = from.match(/(?:^|:)([CGDU][A-Z0-9]+)$/i);
  return match?.[1] ?? null;
}

/**
 * Build a composite key for thread tracking.
 */
function threadKey(
  accountId: string,
  targetId: string,
  threadTs: string,
): string {
  return `${accountId}:${targetId}:${threadTs}`;
}

// ── Final Summary Builder ──────────────────────────────────────────────

export function buildFinalSummary(
  messages: unknown[],
  success: boolean,
  error?: string,
): string {
  // Scan from end to find last assistant message with text content
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (!msg || typeof msg !== "object") continue;
    const record = msg as Record<string, unknown>;
    if (record.role !== "assistant") continue;

    // String content
    if (typeof record.content === "string" && record.content.trim()) {
      return record.content.trim();
    }

    // Array content (Claude API format: [{type:"text", text:"..."}])
    if (Array.isArray(record.content)) {
      const textParts: string[] = [];
      for (const part of record.content) {
        if (
          part &&
          typeof part === "object" &&
          (part as Record<string, unknown>).type === "text"
        ) {
          const text = (part as Record<string, unknown>).text;
          if (typeof text === "string" && text.trim()) {
            textParts.push(text.trim());
          }
        }
      }
      if (textParts.length > 0) return textParts.join("\n\n");
    }
  }

  if (error?.trim()) return `I ran into an error: ${error.trim()}`;
  return "Done.";
}

// ── Registration ───────────────────────────────────────────────────────

export function registerSlackThreadReplyMode(api: OpenClawPluginApi): void {
  /**
   * In-memory map of suppressed threads.
   * Key: `${accountId}:${channelId}:${threadTs}`
   */
  const suppressedThreads = new Map<string, SuppressedThread>();

  // ── Register reply suppression callback with Slack extension ─────
  //
  // This callback runs synchronously in the Slack dispatch hot path.
  // It must be fast (Map iteration only, no async).
  //
  registerSlackReplySuppression((params) => {
    if (!params.threadTs) return false;

    // Check all suppressed threads for this accountId + threadTs combo
    for (const thread of suppressedThreads.values()) {
      if (
        thread.accountId === params.accountId &&
        thread.threadTs === params.threadTs
      ) {
        return true;
      }
    }
    return false;
  });

  // ── Hook: message_received ─────────────────────────────────────────
  //
  // Fires fire-and-forget when an inbound message arrives.
  // Detects Slack messages, checks config, registers suppression, sends ack.
  //
  api.on("message_received", async (event, ctx) => {
    if (ctx.channelId !== "slack") return;

    const accountId = ctx.accountId ?? "default";
    const threadTs =
      typeof event.metadata?.threadId === "string"
        ? event.metadata.threadId
        : undefined;
    if (!threadTs?.trim()) return;

    const cfg = api.runtime.config.loadConfig();
    const config = resolveThreadReplyConfig(cfg, accountId);
    if (config.mode === "full") return;

    // Resolve Slack target — conversationId has the proper format (channel:C123 or user:U123)
    const sendTarget = (ctx.conversationId ?? "").trim();
    const targetId =
      extractSlackTargetId(sendTarget) ??
      extractSlackTargetId(event.from ?? "");
    if (!targetId || !sendTarget) return;

    const key = threadKey(accountId, targetId, threadTs);

    // Deduplicate — don't re-register for the same thread
    if (suppressedThreads.has(key)) return;

    const thread: SuppressedThread = {
      accountId,
      targetId,
      sendTarget,
      threadTs,
      mode: config.mode,
      ackMessage: config.ackMessage,
      ackSent: false,
    };

    suppressedThreads.set(key, thread);

    // Send ack in summary-only mode
    if (config.mode === "summary-only") {
      try {
        await sendMessageSlack(sendTarget, config.ackMessage, {
          cfg,
          accountId,
          threadTs,
        });
        thread.ackSent = true;
      } catch (err) {
        api.logger.warn(
          `pazi: failed to send Slack ack: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    }
  });

  // ── Hook: agent_end ────────────────────────────────────────────────
  //
  // Fires after agent run completes. Sends final summary and cleans up.
  //
  api.on("agent_end", async (event, ctx) => {
    if (ctx.channelId !== "slack") return;

    // Find matching suppressed thread.
    // Single-task per agent, so at most one entry matches.
    let matchedKey: string | undefined;
    let matchedThread: SuppressedThread | undefined;

    for (const [key, thread] of suppressedThreads) {
      matchedKey = key;
      matchedThread = thread;
      break;
    }

    if (!matchedThread || !matchedKey) return;

    // Clean up immediately to unblock future messages
    suppressedThreads.delete(matchedKey);

    // Build and send final summary
    const summary = buildFinalSummary(
      Array.isArray(event.messages) ? event.messages : [],
      event.success,
      event.error,
    );

    try {
      const cfg = api.runtime.config.loadConfig();
      await sendMessageSlack(matchedThread.sendTarget, summary, {
        cfg,
        accountId: matchedThread.accountId,
        threadTs: matchedThread.threadTs,
      });
    } catch (err) {
      api.logger.warn(
        `pazi: failed to send final Slack summary: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  });
}
