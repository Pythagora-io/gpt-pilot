import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { sendMessageSlack } from "../../slack/runtime-api.js";

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

/**
 * Check whether a given Slack account has any active suppressed threads.
 */
function hasActiveSuppression(accountId: string): boolean {
  const suppressedThreads = getGlobalSuppressedThreads();
  for (const thread of suppressedThreads.values()) {
    if (thread.accountId === accountId) {
      return true;
    }
  }
  return false;
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
  // The hook fires for every outbound message. We prefer exact matching by
  // account + target + thread to avoid suppressing unrelated conversations.
  // The final reply is delivered by the normal pipeline after agent_end
  // clears suppression.
  //
  api.on("message_sending", (event, ctx) => {
    if (ctx.channelId !== "slack") {
      return;
    }
    const accountId = ctx.accountId ?? "default";

    const threadTs =
      typeof event?.metadata?.threadTs === "string"
        ? event.metadata.threadTs
        : typeof event?.metadata?.threadId === "string"
          ? event.metadata.threadId
          : undefined;

    // If outbound metadata lacks thread info, fall back to account-level
    // suppression to prevent leaking intermediate drafts.
    if (!threadTs) {
      if (hasActiveSuppression(accountId)) {
        return { cancel: true };
      }
      return;
    }

    const targetCandidates = [
      typeof event?.metadata?.targetId === "string" ? event.metadata.targetId : undefined,
      typeof event?.metadata?.channelId === "string" ? event.metadata.channelId : undefined,
      typeof event?.to === "string" ? event.to : undefined,
      typeof ctx.conversationId === "string" ? ctx.conversationId : undefined,
    ];

    let targetId: string | undefined;
    for (const candidate of targetCandidates) {
      const parsed = candidate ? extractSlackTargetId(candidate) : null;
      if (parsed) {
        targetId = parsed;
        break;
      }
    }

    if (targetId) {
      const key = threadKey(accountId, targetId, threadTs);
      if (suppressedThreads.has(key)) {
        return { cancel: true };
      }
      // message_received uses user-scoped conversation IDs for DMs (`user:U...`),
      // while live replies now route via the concrete DM channel (`channel:D...`).
      // Check wildcard thread suppression to keep DM suppression stable across
      // this target-id shape shift.
      const wildcardKey = threadKey(accountId, "", threadTs);
      if (suppressedThreads.has(wildcardKey)) {
        return { cancel: true };
      }
    }

    // Fallback when target cannot be derived but thread id is present.
    for (const thread of suppressedThreads.values()) {
      if (thread.accountId === accountId && thread.threadTs === threadTs) {
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
    if (ctx.channelId !== "slack") {
      return;
    }

    const accountId = ctx.accountId ?? "default";
    const threadTs =
      typeof event.metadata?.threadId === "string" ? event.metadata.threadId : undefined;
    if (!threadTs?.trim()) {
      return;
    }

    const cfg = api.runtime.config.loadConfig();
    const config = resolveThreadReplyConfig(cfg, accountId);
    if (config.mode === "full") {
      return;
    }

    // Resolve Slack target — conversationId has the proper format (channel:C123 or user:U123)
    const sendTarget = (ctx.conversationId ?? "").trim();
    const rawTargetId = extractSlackTargetId(sendTarget) ?? extractSlackTargetId(event.from ?? "");
    // DM inbound conversationId is usually `user:U...`, but downstream live
    // reply target is `channel:D...`; persist with wildcard target to suppress
    // both forms for the same account+thread.
    const targetId = sendTarget.startsWith("user:") ? "" : rawTargetId;
    if (targetId == null || !sendTarget) {
      return;
    }

    const key = threadKey(accountId, targetId, threadTs);

    // Deduplicate — don't re-register for the same thread
    if (suppressedThreads.has(key)) {
      return;
    }

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
  // Fires after agent run completes. Clears suppression so the normal
  // reply pipeline can deliver the final reply.
  //
  api.on("agent_end", async (event, ctx) => {
    if (ctx.channelId !== "slack") {
      return;
    }

    // Resolve account from sessionKey because agent_end context does not
    // include accountId.
    const sessionKey = ctx.sessionKey ?? "";
    const skMatch = sessionKey.match(
      /^agent:([^:]+):slack:(?:channel|user):([^:]+)(?::thread:([^:]+))?/,
    );
    const resolvedAccountId = skMatch?.[1] ?? "default";
    const skThreadTs = skMatch?.[3];

    // Find matching suppressed thread for THIS account and thread.
    //
    // Bug fix: previous implementation grabbed the first entry from the map
    // regardless of which account/agent the run belonged to. On multi-agent
    // gateways (multiple Slack bot accounts), agent A's completion could
    // match agent B's suppressed thread entry, causing cross-thread leaks.
    // We also require thread match when sessionKey encodes it.
    let matchedKey: string | undefined;
    let matchedThread: SuppressedThread | undefined;

    for (const [key, thread] of suppressedThreads) {
      if (thread.accountId !== resolvedAccountId) {
        continue;
      }
      if (skThreadTs && thread.threadTs !== skThreadTs) {
        continue;
      }
      matchedKey = key;
      matchedThread = thread;
      break;
    }

    if (!matchedThread || !matchedKey) {
      return;
    }

    // Clear suppression so the normal reply pipeline's final delivery
    // (which runs after agent_end) can go through. Do NOT send here —
    // the pipeline already has the final reply queued and will deliver
    // it once suppression is lifted.
    suppressedThreads.delete(matchedKey);
  });
}
