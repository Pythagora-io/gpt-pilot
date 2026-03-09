type ChannelType = "slack" | "telegram";

interface ChannelConfigureParams {
  channel: ChannelType;
  accountId?: string;
  timeoutMs?: number;
  config: {
    name?: string;
    botToken?: string;
    appToken?: string;
    token?: string;
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

interface ChannelConfigureResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  probe?: ProbeResult;
  onboarding?: TelegramOnboardingResult;
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
}

const VALID_CHANNELS: ReadonlySet<string> = new Set(["slack", "telegram"]);
const ERROR_INVALID_REQUEST = "INVALID_REQUEST";
const ERROR_UNAVAILABLE = "UNAVAILABLE";

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
    return { ok: false, error: "channel must be 'slack' or 'telegram'" };
  }

  const config = p.config;
  if (!config || typeof config !== "object") {
    return { ok: false, error: "config must be an object" };
  }
  const cfg = config as Record<string, unknown>;

  if (p.channel === "slack") {
    const botToken = typeof cfg.botToken === "string" ? cfg.botToken.trim() : "";
    const appToken = typeof cfg.appToken === "string" ? cfg.appToken.trim() : "";
    if (!botToken || !appToken) {
      return { ok: false, error: "Slack requires botToken and appToken" };
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
        token: typeof cfg.token === "string" ? cfg.token : undefined,
      },
    },
  };
}

function applySlackConfig(
  cfg: OpenClawConfig,
  accountId: string,
  input: ChannelConfigureParams["config"],
): OpenClawConfig {
  const botToken = input.botToken?.trim() ?? "";
  const appToken = input.appToken?.trim() ?? "";

  if (accountId === "default") {
    return {
      ...cfg,
      channels: {
        ...cfg.channels,
        slack: {
          ...cfg.channels?.slack,
          enabled: true,
          botToken,
          appToken,
          dmPolicy: "open",
          ...(input.name ? { name: input.name } : {}),
        },
      },
    };
  }

  return {
    ...cfg,
    channels: {
      ...cfg.channels,
      slack: {
        ...cfg.channels?.slack,
        enabled: true,
        accounts: {
          ...cfg.channels?.slack?.accounts,
          [accountId]: {
            ...cfg.channels?.slack?.accounts?.[accountId],
            enabled: true,
            botToken,
            appToken,
            dmPolicy: "open",
            ...(input.name ? { name: input.name } : {}),
          },
        },
      },
    },
  };
}

function applyTelegramConfig(
  cfg: OpenClawConfig,
  accountId: string,
  input: ChannelConfigureParams["config"],
): OpenClawConfig {
  const token = (input.token ?? input.botToken ?? "").trim();

  if (accountId === "default") {
    return {
      ...cfg,
      channels: {
        ...cfg.channels,
        telegram: {
          ...cfg.channels?.telegram,
          enabled: true,
          botToken: token,
          dmPolicy: "pairing",
          ...(input.name ? { name: input.name } : {}),
        },
      },
    };
  }

  return {
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
  };
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

    let probe: ProbeResult;
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
        cfg = applySlackConfig(cfg, accountId, inputConfig);
      } else {
        cfg = applyTelegramConfig(cfg, accountId, inputConfig);
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

    const result: ChannelConfigureResult = {
      ok: true,
      channel,
      accountId,
      probe,
    };
    if (channel === "telegram") {
      const botUsername = probe.bot?.username?.trim() ?? "";
      result.onboarding = {
        mode: "pairing",
        dmPolicy: "pairing",
        command: "/start",
        botUsername: botUsername || undefined,
        pollingIntervalMs: 3000,
        ...(botUsername
          ? {
              deepLink: `https://t.me/${encodeURIComponent(botUsername)}`,
            }
          : {}),
      };
    }
    respond(true, result);
  };
}
