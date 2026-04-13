import { describe, expect, it, vi } from "vitest";
import { createPaziChannelsConfigureHandler } from "./channels-configure.js";

interface SlackAccountConfig {
  enabled?: boolean;
  botToken?: string;
  appToken?: string;
  dmPolicy?: "open" | "allowlist";
  groupPolicy?: "open" | "allowlist";
  allowFrom?: string[];
  creatorSlackUserId?: string;
  dm?: {
    policy?: "open" | "allowlist";
    allowFrom?: string[];
  };
  allowBots?: boolean;
  replyToMode?: "off" | "first" | "all";
  ackReaction?: string;
  threadReplyMode?: "full" | "summary-only" | "quiet";
  ackMessage?: string;
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
    return responses[0];
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
        accessMode: "open",
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

  it("defaults allowBots to true for new Slack accounts", async () => {
    const harness = createHarness();
    await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bots-test",
        appToken: "xapp-bots-test",
        accessMode: "open",
      },
    });

    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.allowBots).toBe(true);
  });

  it("preserves explicit allowBots: false on reconfigure", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
              allowBots: false,
            },
          },
        },
      },
    });
    await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-new",
        appToken: "xapp-new",
        accessMode: "open",
      },
    });

    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.allowBots).toBe(false);
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
        accessMode: "open",
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
        accessMode: "open",
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
        accessMode: "open",
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
        accessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand).toBeUndefined();
  });

  it("enforces Slack length cap and trims trailing hyphen after truncation", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        slashCommandName: `${"a".repeat(30)}-b`,
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.slashCommand?.name).toBe("a".repeat(30));
    expect(account?.slashCommand?.name?.length).toBeLessThanOrEqual(31);
  });
});

describe("createPaziChannelsConfigureHandler reply mode config", () => {
  it("stores replyToMode with custom ack reaction", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        replyToMode: "first",
        ackReaction: "rocket",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.replyToMode).toBe("first");
    expect((account as Record<string, unknown>)?.ackReaction).toBe("rocket");
  });

  it("returns replyToMode and ackReaction in response", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        replyToMode: "off",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.replyToMode).toBe("off");
    expect(data.ackReaction).toBe("eyes");
  });

  it("defaults replyToMode to all when not provided", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.replyToMode).toBe("all");
    expect(data.ackReaction).toBe("eyes");
  });

  it("trims whitespace from ackReaction", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        replyToMode: "all",
        ackReaction: "  white_check_mark  ",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.ackReaction).toBe("white_check_mark");
  });

  it("preserves threadReplyMode and ackMessage when reconfiguring", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
              threadReplyMode: "summary-only",
              ackMessage: "Old ack",
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
        accessMode: "open",
        replyToMode: "first",
        ackReaction: "thumbsup",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.threadReplyMode).toBe("summary-only");
    expect((account as Record<string, unknown>)?.ackMessage).toBe("Old ack");
    expect((account as Record<string, unknown>)?.replyToMode).toBe("first");
    expect((account as Record<string, unknown>)?.ackReaction).toBe("thumbsup");
  });

  it("stores reply placement and suppression settings together", async () => {
    const harness = createHarness();

    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        replyToMode: "all",
        ackReaction: "rocket",
        threadReplyMode: "summary-only",
        ackMessage: "On it",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.replyToMode).toBe("all");
    expect((account as Record<string, unknown>)?.ackReaction).toBe("rocket");
    expect((account as Record<string, unknown>)?.threadReplyMode).toBe("summary-only");
    expect((account as Record<string, unknown>)?.ackMessage).toBe("On it");
  });

  it("returns threadReplyMode and ackMessage in response", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
        threadReplyMode: "quiet",
        ackMessage: "Working",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.threadReplyMode).toBe("quiet");
  });
});

describe("createPaziChannelsConfigureHandler access control defaults", () => {
  it("defaults new Slack connection to closed (allowlist) mode", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        creatorSlackUserId: "U12345ABCD",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.dmPolicy).toBe("allowlist");
    expect(data.allowFrom).toEqual(["U12345ABCD"]);
    expect(data.creatorSlackUserId).toBe("U12345ABCD");
  });

  it("stores creatorSlackUserId in account config", async () => {
    const harness = createHarness();
    await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        creatorSlackUserId: "U12345ABCD",
      },
    });

    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.creatorSlackUserId).toBe("U12345ABCD");
    expect((account as Record<string, unknown>)?.dmPolicy).toBe("allowlist");
    expect((account as Record<string, unknown>)?.allowFrom).toEqual(["U12345ABCD"]);
  });

  it("ensures creator is always in allowFrom when closed mode with explicit list", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        creatorSlackUserId: "U12345ABCD",
        accessMode: "closed",
        allowFrom: ["UOTHER12345"],
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    const allowFrom = data.allowFrom as string[];
    expect(allowFrom).toContain("U12345ABCD");
    expect(allowFrom).toContain("UOTHER12345");
  });

  it("allows explicit open mode to override closed default", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.dmPolicy).toBe("open");
    expect(data.allowFrom).toEqual(["*"]);
  });

  it("rejects invalid creatorSlackUserId format", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        creatorSlackUserId: "invalid-id",
      },
    });

    expect(response.ok).toBe(false);
    expect(response.error?.message).toContain("Invalid Slack user ID format");
  });

  it("rejects explicit closed mode with no allowFrom and no creatorSlackUserId", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "closed",
      },
    });

    expect(response.ok).toBe(false);
    expect(response.error?.message).toContain("at least one allowed Slack user ID");
  });

  it("preserves existing dmPolicy when reconfiguring with tokens only", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
            },
          },
        },
      },
    });

    // Reconfigure with open mode explicitly
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-new",
        appToken: "xapp-new",
        accessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect((account as Record<string, unknown>)?.dmPolicy).toBe("open");
  });

  it("normalizes creatorSlackUserId to uppercase", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        creatorSlackUserId: "u12345abcd",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.creatorSlackUserId).toBe("U12345ABCD");
  });

  it("does not include creatorSlackUserId when not provided", async () => {
    const harness = createHarness();
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-bot",
        appToken: "xapp-app",
        accessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.creatorSlackUserId).toBeUndefined();
  });
});

describe("createPaziChannelsConfigureHandler backward-compat reconfiguration", () => {
  it("succeeds with token-only reconfiguration when accessMode is omitted", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
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
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.botToken).toBe("xoxb-new");
    expect(account?.appToken).toBe("xapp-new");
  });

  it("preserves open dmPolicy on token-only reconfiguration without accessMode", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
            },
          },
        },
      },
    });

    // First configure with open mode
    await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-old",
        appToken: "xapp-old",
        accessMode: "open",
      },
    });

    // Reconfigure with only tokens — no accessMode
    const response = await harness.invoke({
      channel: "slack",
      config: {
        botToken: "xoxb-new",
        appToken: "xapp-new",
      },
    });

    expect(response.ok).toBe(true);
    const data = response.data as Record<string, unknown>;
    expect(data.dmPolicy).toBe("open");
    expect(data.allowFrom).toEqual(["*"]);
  });

  it("preserves existing groupPolicy on token-only reconfiguration without groupAccessMode", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
              dmPolicy: "allowlist",
              allowFrom: ["U_OWNER"],
              groupPolicy: "allowlist",
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
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.groupPolicy).toBe("allowlist");
    expect(account?.dmPolicy).toBe("allowlist");
    expect(account?.allowFrom).toEqual(["U_OWNER"]);
  });

  it("updates group policy without rewriting DM access when only groupAccessMode is provided", async () => {
    const harness = createHarness({
      channels: {
        slack: {
          enabled: true,
          accounts: {
            default: {
              enabled: true,
              botToken: "xoxb-old",
              appToken: "xapp-old",
              dmPolicy: "allowlist",
              allowFrom: ["U_OWNER"],
              groupPolicy: "allowlist",
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
        groupAccessMode: "open",
      },
    });

    expect(response.ok).toBe(true);
    const cfg = harness.getConfig();
    const account = cfg.channels?.slack?.accounts?.default;
    expect(account?.groupPolicy).toBe("open");
    expect(account?.dmPolicy).toBe("allowlist");
    expect(account?.allowFrom).toEqual(["U_OWNER"]);
  });
});
