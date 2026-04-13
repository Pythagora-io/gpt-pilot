import type { SlackThreadReplyMode } from "./slack-thread-reply-mode.js";

type ChannelType = "slack" | "telegram" | "whatsapp";

type ReplyToMode = "off" | "first" | "all";

interface ChannelConfigureParams {
  channel: ChannelType;
  accountId?: string;
  timeoutMs?: number;
  config: {
    name?: string;
    botToken?: string;
    appToken?: string;
    appId?: string;
    accessMode?: "open" | "closed";
    groupAccessMode?: "open" | "closed";
    allowFrom?: string[];
    creatorSlackUserId?: string;
    slashCommandName?: string;
    token?: string;
    replyToMode?: ReplyToMode;
    ackReaction?: string;
    threadReplyMode?: SlackThreadReplyMode;
    ackMessage?: string;
  };
}

interface ProbeResult {
  ok: boolean;
  status?: number | null;
  error?: string | null;
  bot?: {
    id?: string | number | null;
    name?: string | null;
    username?: string | null;
  };
  team?: { id?: string | null; name?: string | null };
  elapsedMs?: number | null;
}

interface TelegramOnboardingResult {
  mode: "pairing";
  dmPolicy: "pairing";
  command: string;
  botUsername?: string | null;
  deepLink?: string;
  pollingIntervalMs?: number;
}

interface WhatsAppOnboardingResult {
  mode: "pairing";
  dmPolicy: "pairing";
  method: "qr";
}

interface ChannelConfigureResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  probe?: ProbeResult;
  appId?: string;
  teamId?: string;
  dmPolicy?: "open" | "allowlist";
  groupPolicy?: "open" | "allowlist";
  allowFrom?: string[];
  creatorSlackUserId?: string;
  replyToMode?: ReplyToMode;
  ackReaction?: string;
  threadReplyMode?: SlackThreadReplyMode;
  ackMessage?: string;
  onboarding?: TelegramOnboardingResult | WhatsAppOnboardingResult;
}

type GatewayErrorShape = {
  code: string;
  message: string;
};

interface GatewayMethodContext {
  params: unknown;
  respond: (ok: boolean, data?: unknown, error?: GatewayErrorShape) => void;
  context: {
    stopChannel: (channel: string, accountId?: string) => Promise<void>;
    startChannel: (channel: string, accountId?: string) => Promise<void>;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type OpenClawConfig = Record<string, any>;

interface ChannelConfigureDeps {
  loadConfig: () => OpenClawConfig;
  writeConfigFile: (cfg: OpenClawConfig) => void | Promise<void>;
  probeSlack: (token: string, timeoutMs: number) => Promise<ProbeResult>;
  probeTelegram: (
    token: string,
    timeoutMs: number,
    proxyUrl: string | undefined,
  ) => Promise<ProbeResult>;
  onConfigured?: (result: ChannelConfigureResult) => Promise<void> | void;
}

/** Validates a Slack user ID format: starts with U or W, alphanumeric, 9-11 chars. */
function isValidSlackUserId(id: string): boolean {
  return /^[UW][A-Z0-9]{8,10}$/i.test(id.trim());
}

const VALID_CHANNELS: ReadonlySet<string> = new Set(["slack", "telegram", "whatsapp"]);
const VALID_ACK_REACTIONS: ReadonlySet<string> = new Set([
  "eyes",
  "thumbsup",
  "rocket",
  "white_check_mark",
  "hourglass_flowing_sand",
]);
const ERROR_INVALID_REQUEST = "INVALID_REQUEST";
const ERROR_UNAVAILABLE = "UNAVAILABLE";
const TELEGRAM_PAIRING_POLL_INTERVAL_MS = 3000;
const DEFAULT_SLASH_COMMAND = "pazi-agent";
const MAX_SLASH_COMMAND_CHARS = 32;
const MAX_SLASH_COMMAND_NAME_CHARS = MAX_SLASH_COMMAND_CHARS - 1;

// Keep these rules in sync with `shared/utils/SlackCommand.ts` in the `pazi` repository.
function sanitizeSlashCommandName(
  raw: string | undefined,
  fallback = DEFAULT_SLASH_COMMAND,
): string {
  const normalized = (raw ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, MAX_SLASH_COMMAND_NAME_CHARS)
    .replace(/-+$/g, "");
  return normalized || fallback;
}

function respondError(
  respond: GatewayMethodContext["respond"],
  code: string,
  message: string,
  payload?: unknown,
): void {
  respond(false, payload, { code, message });
}

function isChannelType(value: unknown): value is ChannelType {
  return typeof value === "string" && VALID_CHANNELS.has(value);
}

function validateParams(raw: unknown): {
  ok: boolean;
  error?: string;
  params?: ChannelConfigureParams;
} {
  if (!raw || typeof raw !== "object") {
    return { ok: false, error: "params must be an object" };
  }
  const p = raw as Record<string, unknown>;

  if (!isChannelType(p.channel)) {
    return {
      ok: false,
      error: "channel must be 'slack', 'telegram', or 'whatsapp'",
    };
  }

  const config = p.config;
  if (!config || typeof config !== "object") {
    return { ok: false, error: "config must be an object" };
  }
  const cfg = config as Record<string, unknown>;

  if (p.channel === "slack") {
    const botToken = typeof cfg.botToken === "string" ? cfg.botToken.trim() : "";
    const appToken = typeof cfg.appToken === "string" ? cfg.appToken.trim() : "";
    // Only default to "closed" when accessMode is explicitly provided.
    // When omitted (undefined), skip closed-mode validation to allow
    // token-only reconfiguration from older clients.
    const accessMode =
      cfg.accessMode === "open" ? "open" : cfg.accessMode !== undefined ? "closed" : undefined;
    const creatorSlackUserId =
      typeof cfg.creatorSlackUserId === "string" ? cfg.creatorSlackUserId.trim() : "";
    const allowFrom = Array.isArray(cfg.allowFrom)
      ? cfg.allowFrom.filter(
          (entry): entry is string => typeof entry === "string" && entry.trim().length > 0,
        )
      : [];
    if (!botToken || !appToken) {
      return { ok: false, error: "Slack requires botToken and appToken" };
    }
    if (creatorSlackUserId && !isValidSlackUserId(creatorSlackUserId)) {
      return {
        ok: false,
        error:
          "Invalid Slack user ID format. IDs start with U or W followed by 8-10 alphanumeric characters.",
      };
    }
    // When closed, require either an explicit allowFrom list or a creator user ID.
    if (accessMode === "closed" && allowFrom.length === 0 && !creatorSlackUserId) {
      return {
        ok: false,
        error:
          "Closed Slack access requires at least one allowed Slack user ID or a creator Slack user ID",
      };
    }
  }

  if (p.channel === "telegram") {
    const token =
      typeof cfg.token === "string"
        ? cfg.token.trim()
        : typeof cfg.botToken === "string"
          ? cfg.botToken.trim()
          : "";
    if (!token) {
      return { ok: false, error: "Telegram requires token or botToken" };
    }
  }

  // WhatsApp uses QR-code pairing — no token required at configure time.

  return {
    ok: true,
    params: {
      channel: p.channel,
      accountId: typeof p.accountId === "string" ? p.accountId : undefined,
      timeoutMs: typeof p.timeoutMs === "number" ? p.timeoutMs : undefined,
      config: {
        name: typeof cfg.name === "string" ? cfg.name : undefined,
        botToken: typeof cfg.botToken === "string" ? cfg.botToken : undefined,
        appToken: typeof cfg.appToken === "string" ? cfg.appToken : undefined,
        appId: typeof cfg.appId === "string" ? cfg.appId : undefined,
        accessMode:
          cfg.accessMode === "open" ? "open" : cfg.accessMode !== undefined ? "closed" : undefined,
        groupAccessMode:
          cfg.groupAccessMode === "open"
            ? "open"
            : cfg.groupAccessMode === "closed"
              ? "closed"
              : undefined,
        allowFrom: Array.isArray(cfg.allowFrom)
          ? cfg.allowFrom.filter((entry): entry is string => typeof entry === "string")
          : undefined,
        creatorSlackUserId:
          typeof cfg.creatorSlackUserId === "string" && cfg.creatorSlackUserId.trim().length > 0
            ? cfg.creatorSlackUserId.trim().toUpperCase()
            : undefined,
        slashCommandName:
          typeof cfg.slashCommandName === "string" ? cfg.slashCommandName : undefined,
        token: typeof cfg.token === "string" ? cfg.token : undefined,
        replyToMode:
          cfg.replyToMode === "off" || cfg.replyToMode === "first" || cfg.replyToMode === "all"
            ? cfg.replyToMode
            : undefined,
        ackReaction:
          typeof cfg.ackReaction === "string" && VALID_ACK_REACTIONS.has(cfg.ackReaction.trim())
            ? cfg.ackReaction.trim()
            : undefined,
        threadReplyMode:
          cfg.threadReplyMode === "full" ||
          cfg.threadReplyMode === "summary-only" ||
          cfg.threadReplyMode === "quiet"
            ? cfg.threadReplyMode
            : undefined,
        ackMessage:
          typeof cfg.ackMessage === "string" && cfg.ackMessage.trim().length > 0
            ? cfg.ackMessage.trim()
            : undefined,
      },
    },
  };
}

function normalizeSlackAllowFrom(input: string[] | undefined): string[] {
  return (input ?? [])
    .map((entry) => entry.trim().toUpperCase())
    .filter((entry) => entry.length > 0);
}

function normalizeBindingChannel(channel: string): string {
  return channel.trim().toLowerCase();
}

function upsertChannelAgentBinding(
  cfg: OpenClawConfig,
  params: { channel: ChannelType; accountId: string; agentId: string },
): OpenClawConfig {
  const channel = normalizeBindingChannel(params.channel);
  const accountId = params.accountId.trim();
  const agentId = params.agentId.trim();
  if (!channel || !accountId || !agentId || accountId === "default") {
    return cfg;
  }

  const existing = Array.isArray(cfg.bindings) ? cfg.bindings : [];
  const filtered = existing.filter((binding) => {
    const match = binding?.match;
    return !(
      binding?.agentId &&
      typeof match?.channel === "string" &&
      typeof match?.accountId === "string" &&
      normalizeBindingChannel(match.channel) === channel &&
      match.accountId.trim() === accountId
    );
  });

  return {
    ...cfg,
    bindings: [
      ...filtered,
      {
        agentId,
        match: { channel, accountId },
      },
    ],
  };
}

function applySlackConfig(
  cfg: OpenClawConfig,
  accountId: string,
  input: ChannelConfigureParams["config"],
  _probe: ProbeResult,
): OpenClawConfig {
  const botToken = input.botToken?.trim() ?? "";
  const appToken = input.appToken?.trim() ?? "";

  const slashCommandName =
    input.slashCommandName !== undefined
      ? sanitizeSlashCommandName(input.slashCommandName)
      : undefined;
  const {
    streamMode: _legacyStreamMode,
    streaming: _rawStreaming,
    chunkMode: _legacyChunkMode,
    blockStreaming: _legacyBlockStreaming,
    blockStreamingCoalesce: _legacyBlockStreamingCoalesce,
    nativeStreaming: _legacyNativeStreaming,
    ...existingAccount
  } = (cfg.channels?.slack?.accounts?.[accountId] ?? {}) as Record<string, unknown>;
  // Preserve streaming only when it's already the new object shape; drop scalar legacy values.
  if (_rawStreaming && typeof _rawStreaming === "object" && !Array.isArray(_rawStreaming)) {
    existingAccount.streaming = _rawStreaming;
  }

  const hasExistingAccount = Object.keys(existingAccount).length > 0;
  const shouldWriteDmAccess =
    input.accessMode !== undefined ||
    input.allowFrom !== undefined ||
    input.creatorSlackUserId !== undefined ||
    !hasExistingAccount;
  const shouldWriteGroupAccess = input.groupAccessMode !== undefined || !hasExistingAccount;

  const existingDmPolicy = (existingAccount.dmPolicy as string | undefined) ?? undefined;
  const existingAllowFrom = Array.isArray(existingAccount.allowFrom)
    ? existingAccount.allowFrom.filter((entry): entry is string => typeof entry === "string")
    : undefined;
  const existingCreator =
    typeof existingAccount.creatorSlackUserId === "string"
      ? existingAccount.creatorSlackUserId.trim().toUpperCase()
      : "";
  const creatorSlackUserId = input.creatorSlackUserId?.trim().toUpperCase() ?? "";

  let dmPolicy: "open" | "allowlist" | undefined;
  let allowFrom: string[] | undefined;
  let dm: { policy: "open" | "allowlist"; allowFrom: string[] } | undefined;
  if (shouldWriteDmAccess) {
    // Preserve existing DM policy/allowlist on token-only edits for existing accounts.
    const accessMode =
      input.accessMode !== undefined
        ? input.accessMode === "open"
          ? "open"
          : "closed"
        : existingDmPolicy === "open"
          ? "open"
          : "closed";

    if (accessMode === "open") {
      allowFrom = ["*"];
    } else {
      const explicit = normalizeSlackAllowFrom(input.allowFrom);
      if (explicit.length > 0) {
        allowFrom = explicit;
      } else if (creatorSlackUserId) {
        allowFrom = [creatorSlackUserId];
      } else if (Array.isArray(existingAllowFrom) && existingAllowFrom.length > 0) {
        allowFrom = existingAllowFrom.filter((e) => e.trim().length > 0);
      } else {
        allowFrom = [];
      }
      // Ensure the creator is always in the allow list when in closed mode.
      const effectiveCreator = creatorSlackUserId || existingCreator;
      if (effectiveCreator && !allowFrom.includes(effectiveCreator)) {
        allowFrom = [effectiveCreator, ...allowFrom];
      }
    }

    dmPolicy = accessMode === "open" ? "open" : "allowlist";
    dm = { policy: dmPolicy, allowFrom };
  }

  let groupPolicy: "open" | "allowlist" | undefined;
  if (shouldWriteGroupAccess) {
    const groupAccessMode =
      input.groupAccessMode === "open"
        ? "open"
        : input.groupAccessMode === "closed"
          ? "closed"
          : existingAccount.groupPolicy === "allowlist"
            ? "closed"
            : "open";
    groupPolicy = groupAccessMode === "open" ? "open" : "allowlist";
  }

  return upsertChannelAgentBinding(
    {
      ...cfg,
      channels: {
        ...cfg.channels,
        slack: {
          ...cfg.channels?.slack,
          enabled: true,
          accounts: {
            ...cfg.channels?.slack?.accounts,
            [accountId]: {
              ...existingAccount,
              enabled: true,
              botToken,
              appToken,
              ...(dmPolicy ? { dmPolicy } : {}),
              ...(groupPolicy ? { groupPolicy } : {}),
              ...(allowFrom ? { allowFrom } : {}),
              ...(creatorSlackUserId ? { creatorSlackUserId } : {}),
              ...(dm ? { dm } : {}),
              // Disable block streaming so tool execution traces and intermediate
              // steps are not posted to Slack — only the final response is sent.
              streaming: {
                ...(existingAccount.streaming && typeof existingAccount.streaming === "object"
                  ? (existingAccount.streaming as Record<string, unknown>)
                  : {}),
                block: { enabled: false },
              },
              // Always reply inside threads so the bot doesn't spam the channel.
              replyToMode: "all",
              // Enable bot-to-bot communication by default so multi-agent setups
              // work out of the box. Safety is preserved by requireMention (agents
              // only respond when explicitly @mentioned, not on every bot message).
              // Only set the default when the account doesn't already have an
              // explicit value — avoids overriding a deliberate opt-out on reconfigure.
              ...((existingAccount as Record<string, unknown>)?.allowBots === undefined
                ? { allowBots: true }
                : {}),
              ...(input.name ? { name: input.name } : {}),
              ...(input.replyToMode ? { replyToMode: input.replyToMode } : {}),
              ...(input.ackReaction?.trim() ? { ackReaction: input.ackReaction.trim() } : {}),
              ...(input.threadReplyMode ? { threadReplyMode: input.threadReplyMode } : {}),
              ...(input.ackMessage?.trim() ? { ackMessage: input.ackMessage.trim() } : {}),
              ...(slashCommandName
                ? {
                    slashCommand: {
                      ...cfg.channels?.slack?.accounts?.[accountId]?.slashCommand,
                      enabled: true,
                      name: slashCommandName,
                    },
                  }
                : {}),
            },
          },
        },
      },
    },
    { channel: "slack", accountId, agentId: accountId },
  );
}

function applyTelegramConfig(
  cfg: OpenClawConfig,
  accountId: string,
  input: ChannelConfigureParams["config"],
): OpenClawConfig {
  const token = (input.token ?? input.botToken ?? "").trim();

  return upsertChannelAgentBinding(
    {
      ...cfg,
      channels: {
        ...cfg.channels,
        telegram: {
          ...cfg.channels?.telegram,
          enabled: true,
          accounts: {
            ...cfg.channels?.telegram?.accounts,
            [accountId]: {
              ...cfg.channels?.telegram?.accounts?.[accountId],
              enabled: true,
              botToken: token,
              dmPolicy: "pairing",
              ...(input.name ? { name: input.name } : {}),
            },
          },
        },
      },
    },
    { channel: "telegram", accountId, agentId: accountId },
  );
}

function applyWhatsAppConfig(
  cfg: OpenClawConfig,
  accountId: string,
  input: ChannelConfigureParams["config"],
): OpenClawConfig {
  // WhatsApp uses QR-code pairing — no token stored at configure time.
  // This prepares the account so the WhatsApp monitor can request QR auth on startup.
  return upsertChannelAgentBinding(
    {
      ...cfg,
      channels: {
        ...cfg.channels,
        whatsapp: {
          ...cfg.channels?.whatsapp,
          enabled: true,
          accounts: {
            ...cfg.channels?.whatsapp?.accounts,
            [accountId]: {
              ...cfg.channels?.whatsapp?.accounts?.[accountId],
              enabled: true,
              dmPolicy: "pairing",
              ...(input.name ? { name: input.name } : {}),
            },
          },
        },
      },
    },
    { channel: "whatsapp", accountId, agentId: accountId },
  );
}

export function createPaziChannelsConfigureHandler(
  deps: ChannelConfigureDeps,
): (ctx: GatewayMethodContext) => Promise<void> {
  return async ({ params, respond, context }: GatewayMethodContext) => {
    const validation = validateParams(params);
    if (!validation.ok || !validation.params) {
      respondError(respond, ERROR_INVALID_REQUEST, validation.error ?? "invalid params");
      return;
    }

    const { channel, config: inputConfig } = validation.params;
    const rawAccountId = validation.params.accountId?.trim();
    const accountId = rawAccountId || "default";
    const timeoutMs = validation.params.timeoutMs ?? 5000;

    // WhatsApp uses QR-code pairing — skip token probe.
    let probe: ProbeResult | undefined;
    if (channel !== "whatsapp") {
      try {
        if (channel === "slack") {
          const token = inputConfig.botToken?.trim() ?? "";
          // probeSlack validates botToken. appToken validity is verified on channel restart.
          probe = await deps.probeSlack(token, timeoutMs);
        } else {
          const token = (inputConfig.token ?? inputConfig.botToken ?? "").trim();
          probe = await deps.probeTelegram(token, timeoutMs, undefined);
        }
      } catch (err) {
        respondError(
          respond,
          ERROR_UNAVAILABLE,
          `probe failed: ${err instanceof Error ? err.message : String(err)}`,
        );
        return;
      }

      if (!probe.ok) {
        respondError(respond, ERROR_UNAVAILABLE, probe.error ?? "token probe failed", { probe });
        return;
      }
    }

    try {
      await context.stopChannel(channel, accountId);
    } catch (err) {
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `failed to stop channel: ${err instanceof Error ? err.message : String(err)}`,
      );
      return;
    }

    try {
      let cfg = deps.loadConfig();
      if (channel === "slack") {
        if (!probe) {
          respondError(respond, ERROR_UNAVAILABLE, "slack probe result missing");
          return;
        }
        const isNewSlackAccount = !cfg.channels?.slack?.accounts?.[accountId];
        cfg = applySlackConfig(cfg, accountId, inputConfig, probe);
        // Validate: new accounts with omitted accessMode must not end up with
        // an empty allowlist ("nobody can DM" config).
        if (isNewSlackAccount && inputConfig.accessMode === undefined) {
          const savedAccount = cfg.channels?.slack?.accounts?.[accountId];
          const savedAllowFrom = savedAccount?.allowFrom;
          const savedDmPolicy = savedAccount?.dmPolicy;
          if (
            savedDmPolicy === "allowlist" &&
            (!Array.isArray(savedAllowFrom) ||
              savedAllowFrom.filter((e) => typeof e === "string" && e.trim().length > 0).length ===
                0)
          ) {
            respondError(
              respond,
              ERROR_INVALID_REQUEST,
              "Closed Slack access requires at least one allowed Slack user ID or a creator Slack user ID",
            );
            try {
              await context.startChannel(channel, accountId);
            } catch {
              /* best-effort restart */
            }
            return;
          }
        }
      } else if (channel === "telegram") {
        cfg = applyTelegramConfig(cfg, accountId, inputConfig);
      } else if (channel === "whatsapp") {
        cfg = applyWhatsAppConfig(cfg, accountId, inputConfig);
      } else {
        const unsupportedChannel: never = channel;
        throw new Error(`unsupported channel: ${String(unsupportedChannel)}`);
      }
      await deps.writeConfigFile(cfg);
    } catch (err) {
      try {
        await context.startChannel(channel, accountId);
      } catch (restartErr) {
        respondError(
          respond,
          ERROR_UNAVAILABLE,
          `config write failed and restart failed: ${restartErr instanceof Error ? restartErr.message : String(restartErr)}`,
        );
        return;
      }
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `config write failed: ${err instanceof Error ? err.message : String(err)}`,
      );
      return;
    }

    try {
      await context.startChannel(channel, accountId);
    } catch (err) {
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `channel restart failed after config update: ${err instanceof Error ? err.message : String(err)}`,
      );
      return;
    }

    const slackTeamId = channel === "slack" ? (probe?.team?.id?.trim() ?? "") : "";
    const result: ChannelConfigureResult = {
      ok: true,
      channel,
      accountId,
      ...(probe ? { probe } : {}),
      ...(channel === "slack" && inputConfig.appId?.trim()
        ? { appId: inputConfig.appId.trim().toUpperCase() }
        : {}),
      ...(slackTeamId ? { teamId: slackTeamId } : {}),
    };

    // For Slack, read response fields from the SAVED config (post-apply) to ensure
    // the response matches what was actually persisted — not raw input.
    if (channel === "slack") {
      const savedCfg = deps.loadConfig();
      const savedAccount = savedCfg.channels?.slack?.accounts?.[accountId];
      const savedDmPolicyRaw =
        (savedAccount?.dmPolicy as string | undefined) ??
        ((savedAccount?.dm as Record<string, unknown> | undefined)?.policy as string | undefined);
      if (savedDmPolicyRaw === "open" || savedDmPolicyRaw === "allowlist") {
        result.dmPolicy = savedDmPolicyRaw;
      }
      const savedGroupPolicyRaw = savedAccount?.groupPolicy as string | undefined;
      if (savedGroupPolicyRaw === "open" || savedGroupPolicyRaw === "allowlist") {
        result.groupPolicy = savedGroupPolicyRaw;
      }
      const savedAllowFrom = (savedAccount?.allowFrom as string[] | undefined) ?? [];
      result.allowFrom = savedAllowFrom.filter((entry) => typeof entry === "string");
      const savedCreator = (savedAccount as Record<string, unknown> | undefined)
        ?.creatorSlackUserId as string | undefined;
      if (savedCreator) {
        result.creatorSlackUserId = savedCreator;
      }
      result.replyToMode =
        ((savedAccount as Record<string, unknown> | undefined)?.replyToMode as
          | ReplyToMode
          | undefined) ??
        inputConfig.replyToMode ??
        "all";
      result.ackReaction =
        ((savedAccount as Record<string, unknown> | undefined)?.ackReaction as
          | string
          | undefined) ??
        (inputConfig.ackReaction?.trim() || "eyes");
      result.threadReplyMode =
        ((savedAccount as Record<string, unknown> | undefined)?.threadReplyMode as
          | SlackThreadReplyMode
          | undefined) ??
        inputConfig.threadReplyMode ??
        "quiet";
      result.ackMessage =
        ((savedAccount as Record<string, unknown> | undefined)?.ackMessage as string | undefined) ??
        (inputConfig.ackMessage?.trim() || undefined);
    }
    if (channel === "telegram") {
      const botUsername = probe?.bot?.username?.trim() ?? "";
      result.onboarding = {
        mode: "pairing",
        dmPolicy: "pairing",
        command: "/start",
        botUsername: botUsername || undefined,
        pollingIntervalMs: TELEGRAM_PAIRING_POLL_INTERVAL_MS,
        ...(botUsername
          ? {
              deepLink: `https://t.me/${encodeURIComponent(botUsername)}`,
            }
          : {}),
      };
    } else if (channel === "whatsapp") {
      result.onboarding = {
        mode: "pairing",
        dmPolicy: "pairing",
        method: "qr",
      };
    }
    await deps.onConfigured?.(result);
    respond(true, result);
  };
}
