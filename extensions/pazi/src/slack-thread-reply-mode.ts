import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { sendMessageSlack } from "openclaw/plugin-sdk/slack";

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

/**
 * Global suppression registry shared via globalThis.
 *
 * Why globalThis instead of module scope?
 * ─────────────────────────────────────
 * The pazi extension is loaded as TypeScript via jiti with tryNative=false,
 * which creates a separate module graph from the gateway's native ESM modules.
 * Module-scoped closures (like the `suppressionChecks[]` array inside
 * `registerSlackReplySuppression`) are duplicated — the extension writes to
 * jiti's copy while the gateway's `shouldSuppressSlackReply` reads from the
 * native ESM copy, which is always empty.
 *
 * By storing the suppressed threads map on globalThis, all module instances
 * (jiti and native ESM) share the same state. The `message_sending` hook
 * (which runs in the gateway's own context) reads from the same map that
 * the `message_received` hook writes to.
 */
const GLOBAL_KEY = "__openclawPaziSlackSuppressedThreads";

function getGlobalSuppressedThreads(): Map<string, SuppressedThread> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any;
  if (!g[GLOBAL_KEY]) {
    g[GLOBAL_KEY] = new Map<string, SuppressedThread>();
  }
  return g[GLOBAL_KEY] as Map<string, SuppressedThread>;
}

// ── Config Resolution ──────────────────────────────────────────────────

export function resolveThreadReplyConfig(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  cfg: Record<string, any>,
  accountId: string,
): ResolvedThreadReplyConfig {
  const account = cfg?.channels?.slack?.accounts?.[accountId];
  if (!account || typeof account !== "object") {
    return { mode: "quiet", ackMessage: DEFAULT_ACK_MESSAGE };
  }
  const raw = account as Record<string, unknown>;
  const mode: SlackThreadReplyMode =
    raw.threadReplyMode === "summary-only" || raw.threadReplyMode === "quiet"
      ? raw.threadReplyMode
      : raw.threadReplyMode === "full"
        ? "full"
        : "quiet";
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
function threadKey(accountId: string, targetId: string, threadTs: string): string {
  return `${accountId}:${targetId}:${threadTs}`;
}

// ── Final Summary Builder ──────────────────────────────────────────────

export function buildFinalSummary(messages: unknown[], success: boolean, error?: string): string {
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
        if (part && typeof part === "object" && (part as Record<string, unknown>).type === "text") {
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
  const suppressedThreads = getGlobalSuppressedThreads();

  // ── Suppression via message_sending hook ────────────────────────────
  //
  // This hook runs in the gateway's own module context (not jiti's), so
  // it reliably reads from the shared globalThis map. It replaces the
  // previous `registerSlackReplySuppression` approach which was broken
  // by the jiti dual-module-instance issue.
  //
  // The hook fires for every outbound message. We only cancel messages
  // targeting a specific suppressed thread — NOT all messages for the
  // entire account. This prevents swallowing unrelated DMs, channel
  // messages, or other threads when one thread has active suppression.
  //
  api.on("message_sending", (event, ctx) => {
    if (ctx.channelId !== "slack") return;
    const accountId = ctx.accountId ?? "default";

    // Extract thread timestamp from the outbound message metadata.
    // The event payload carries the target thread info.
    const threadTs =
      typeof event?.metadata?.threadTs === "string"
        ? event.metadata.threadTs
        : typeof event?.metadata?.threadId === "string"
          ? event.metadata.threadId
          : undefined;

    if (!threadTs) return; // No thread context → not a thread reply → don't suppress

    // Extract target channel/user ID from the event
    const targetId =
      typeof event?.metadata?.targetId === "string"
        ? event.metadata.targetId
        : typeof ctx.conversationId === "string"
          ? (extractSlackTargetId(ctx.conversationId) ?? undefined)
          : undefined;

    // Check if this specific thread is suppressed
    if (targetId) {
      const key = threadKey(accountId, targetId, threadTs);
      if (suppressedThreads.has(key)) {
        return { cancel: true };
      }
    }

    // Fallback: check by accountId + threadTs (in case targetId isn't available).
    // This path is less precise — if two channels somehow share the same threadTs
    // (extremely unlikely with Slack's timestamp format), it could suppress the
    // wrong channel. Log a warning so it's observable.
    for (const thread of suppressedThreads.values()) {
      if (thread.accountId === accountId && thread.threadTs === threadTs) {
        api.logger.warn(
          `pazi: message_sending suppression matched via fallback (no targetId). ` +
            `accountId=${accountId} threadTs=${threadTs} — consider investigating why targetId was unavailable.`,
        );
        return { cancel: true };
      }
    }
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
      typeof event.metadata?.threadId === "string" ? event.metadata.threadId : undefined;
    if (!threadTs?.trim()) return;

    const cfg = api.runtime.config.loadConfig();
    const config = resolveThreadReplyConfig(cfg, accountId);
    if (config.mode === "full") return;

    // Resolve Slack target — conversationId has the proper format (channel:C123 or user:U123)
    const sendTarget = (ctx.conversationId ?? "").trim();
    const targetId = extractSlackTargetId(sendTarget) ?? extractSlackTargetId(event.from ?? "");
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

    // Resolve accountId from the session key.
    //
    // PluginHookAgentContext doesn't carry accountId directly, but the
    // sessionKey encodes it. Format: "agent:<accountId>:slack:channel:<channelId>:thread:<ts>"
    // We also extract channelId and threadTs to precisely match the suppressed thread
    // (prevents cross-thread leaks on multi-account gateways).
    const sessionKey = ctx.sessionKey ?? "";
    const skMatch = sessionKey.match(
      /^agent:([^:]+):slack:(?:channel|user):([^:]+)(?::thread:([^:]+))?/,
    );
    const accountId = skMatch?.[1] ?? "default";
    const skThreadTs = skMatch?.[3];

    // Find matching suppressed thread for THIS account and thread.
    //
    // Bug fix: previous implementation grabbed the first entry from the map
    // regardless of which account/agent the run belonged to. On multi-agent
    // gateways (multiple Slack bot accounts), agent A's completion could
    // match agent B's suppressed thread entry, causing cross-thread leaks.
    // Now we filter by accountId (and threadTs when available from session key)
    // to ensure each agent only resolves its own suppressed threads.
    let matchedKey: string | undefined;
    let matchedThread: SuppressedThread | undefined;

    for (const [key, thread] of suppressedThreads) {
      if (thread.accountId !== accountId) continue;
      // If we have thread timestamp from session key, require exact match
      if (skThreadTs && thread.threadTs !== skThreadTs) continue;
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
