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
  bot?: { id?: string | number; name?: string | null; username?: string | null };
  team?: { id?: string; name?: string };
  elapsedMs?: number;
}

interface ChannelConfigureResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  probe?: ProbeResult;
}

interface GatewayMethodContext {
  params: unknown;
  respond: (ok: boolean, data: unknown) => void;
  context: {
    stopChannel: (channel: string, accountId?: string) => void;
    startChannel: (channel: string, accountId?: string) => void;
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
      respond(false, { error: validation.error ?? "invalid params" });
      return;
    }

    const { channel, config: inputConfig } = validation.params;
    const accountId = validation.params.accountId || "default";
    const timeoutMs = validation.params.timeoutMs ?? 5000;

    let probe: ProbeResult;
    try {
      if (channel === "slack") {
        const token = inputConfig.botToken?.trim() ?? "";
        probe = await deps.probeSlack(token, timeoutMs);
      } else {
        const token = (inputConfig.token ?? inputConfig.botToken ?? "").trim();
        probe = await deps.probeTelegram(token, timeoutMs, undefined);
      }
    } catch (err) {
      respond(false, {
        error: `probe failed: ${err instanceof Error ? err.message : String(err)}`,
      });
      return;
    }

    if (!probe.ok) {
      respond(false, {
        error: probe.error ?? "token probe failed",
        probe,
      });
      return;
    }

    context.stopChannel(channel, accountId);

    let cfg = deps.loadConfig();
    if (channel === "slack") {
      cfg = applySlackConfig(cfg, accountId, inputConfig);
    } else {
      cfg = applyTelegramConfig(cfg, accountId, inputConfig);
    }
    await deps.writeConfigFile(cfg);

    context.startChannel(channel, accountId);

    const result: ChannelConfigureResult = {
      ok: true,
      channel,
      accountId,
      probe,
    };
    respond(true, result);
  };
}
