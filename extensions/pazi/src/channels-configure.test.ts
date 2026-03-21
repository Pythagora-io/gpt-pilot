import { describe, expect, it, vi } from "vitest";
import { createPaziChannelsConfigureHandler } from "./channels-configure.js";

interface SlackAccountConfig {
  enabled?: boolean;
  botToken?: string;
  appToken?: string;
  slashCommand?: {
    enabled?: boolean;
    name?: string;
    sessionPrefix?: string;
  };
}

interface TelegramAccountConfig {
  enabled?: boolean;
  botToken?: string;
  dmPolicy?: string;
}

interface TestConfig {
  channels?: {
    slack?: {
      enabled?: boolean;
      botToken?: string;
      appToken?: string;
      accounts?: Record<string, SlackAccountConfig>;
    };
    telegram?: {
      enabled?: boolean;
      botToken?: string;
      accounts?: Record<string, TelegramAccountConfig>;
    };
  };
  bindings?: Array<{
    agentId?: string;
    match?: { channel?: string; accountId?: string };
  }>;
}

type HandlerResponse = {
  ok: boolean;
  data?: unknown;
  error?: { code: string; message: string };
};

function createHarness(initialConfig: TestConfig = {}) {
  let cfg = structuredClone(initialConfig);

  const loadConfig = vi.fn(() => cfg as Record<string, unknown>);
  const writeConfigFile = vi.fn(async (next: Record<string, unknown>) => {
    cfg = next as TestConfig;
  });
  const probeSlack = vi.fn(async () => ({ ok: true, team: { id: "T123" } }));
  const probeTelegram = vi.fn(async () => ({ ok: true, bot: { username: "testbot" } }));
  const stopChannel = vi.fn(async () => {});
  const startChannel = vi.fn(async () => {});

  const handler = createPaziChannelsConfigureHandler({
    loadConfig,
    writeConfigFile,
    probeSlack,
    probeTelegram,
  });

  async function invoke(params: unknown): Promise<HandlerResponse> {
    const responses: HandlerResponse[] = [];
    await handler({
      params,
      respond: (ok, data, error) => {
        responses.push({ ok, data, error });
      },
      context: { stopChannel, startChannel },
    });
    expect(responses).toHaveLength(1);
    return responses[0]!;
  }

  return { invoke, getConfig: () => cfg, stopChannel, startChannel };
}

describe("createPaziChannelsConfigureHandler account config writes", () => {
  it("writes Slack default account to channels.slack.accounts.default", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-default-bot",
        appToken: "xapp-default-app",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    expect(cfg.channels?.slack?.accounts?.default?.botToken).toBe("xoxb-default-bot");
    expect(cfg.channels?.slack?.accounts?.default?.appToken).toBe("xapp-default-app");
    expect(cfg.channels?.slack?.botToken).toBeUndefined();
    expect(cfg.channels?.slack?.appToken).toBeUndefined();
    expect(harness.stopChannel).toHaveBeenCalledWith("slack", "default");
    expect(harness.startChannel).toHaveBeenCalledWith("slack", "default");
  });

  it("writes Telegram default account to channels.telegram.accounts.default", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "telegram",
      config: {
        token: "telegram-default-token",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    expect(cfg.channels?.telegram?.accounts?.default?.botToken).toBe("telegram-default-token");
    expect(cfg.channels?.telegram?.accounts?.default?.dmPolicy).toBe("pairing");
    expect(cfg.channels?.telegram?.botToken).toBeUndefined();
    expect(harness.stopChannel).toHaveBeenCalledWith("telegram", "default");
    expect(harness.startChannel).toHaveBeenCalledWith("telegram", "default");
  });
});

describe("createPaziChannelsConfigureHandler slash command config", () => {
  it("writes slash command into account config", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        slashCommandName: "My Agent",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand).toEqual({
      enabled: true,
      name: "my-agent",
    });
  });

  it("sanitizes bad slash command input", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        slashCommandName: "!!! QA Bot !!!",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand?.name).toBe("qa-bot");
  });

  it("preserves existing slashCommand sub-fields", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
              slashCommand: {
                enabled: true,
                name: "old-name",
                sessionPrefix: "custom-prefix",
              },
            },
          },
        },
      },
    });

    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-new",
        appToken: "xapp-new",
        slashCommandName: "new-name",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand).toEqual({
      enabled: true,
      name: "new-name",
      sessionPrefix: "custom-prefix",
    });
  });

  it("omits slashCommand when not provided", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand).toBeUndefined();
  });
});
