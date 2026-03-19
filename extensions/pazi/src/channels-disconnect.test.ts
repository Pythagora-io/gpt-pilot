import { describe, expect, it, vi } from "vitest";
import { createPaziChannelsDisconnectHandler } from "./channels-disconnect.js";

interface TestConfig {
  channels?: {
    slack?: {
      enabled?: boolean;
      botToken?: string;
      appToken?: string;
      accounts?: Record<string, unknown>;
    };
    telegram?: {
      enabled?: boolean;
      botToken?: string;
      tokenFile?: string;
      accounts?: Record<string, unknown>;
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

function createHarness(params?: { initialConfig?: TestConfig; stopThrows?: string }) {
  let cfg = structuredClone(params?.initialConfig ?? {});

  const loadConfig = vi.fn(() => cfg as Record<string, unknown>);
  const writeConfigFile = vi.fn(async (next: Record<string, unknown>) => {
    cfg = next as TestConfig;
  });
  const stopChannel = vi.fn(async () => {
    if (params?.stopThrows) {
      throw new Error(params.stopThrows);
    }
  });

  const handler = createPaziChannelsDisconnectHandler({
    loadConfig,
    writeConfigFile,
  });

  async function invoke(input: unknown): Promise<HandlerResponse> {
    const responses: HandlerResponse[] = [];
    await handler({
      params: input,
      respond: (ok, data, error) => {
        responses.push({ ok, data, error });
      },
      context: { stopChannel },
    });
    expect(responses).toHaveLength(1);
    return responses[0]!;
  }

  return { invoke, stopChannel, writeConfigFile, getConfig: () => cfg };
}

describe("createPaziChannelsDisconnectHandler", () => {
  it("removes Slack account config and matching channel/account binding", async () => {
    const harness = createHarness({
      initialConfig: {
        channels: {
          slack: {
            enabled: true,
            botToken: "legacy-bot",
            appToken: "legacy-app",
            accounts: {
              default: { enabled: true, botToken: "xoxb-default", appToken: "xapp-default" },
              qa: { enabled: true, botToken: "xoxb-qa", appToken: "xapp-qa" },
            },
          },
        },
        bindings: [
          { agentId: "default", match: { channel: "slack", accountId: "default" } },
          { agentId: "qa", match: { channel: "slack", accountId: "qa" } },
        ],
      },
    });

    const response = await harness.invoke({ channel: "slack", accountId: "default" });

    expect(response.ok).toBe(true);
    expect(harness.stopChannel).toHaveBeenCalledWith("slack", "default");
    const result = response.data as {
      changed: boolean;
      accountRemoved: boolean;
      legacyCredentialsCleared: boolean;
      removedBindings: number;
      stopped: boolean;
    };
    expect(result.changed).toBe(true);
    expect(result.accountRemoved).toBe(true);
    expect(result.legacyCredentialsCleared).toBe(true);
    expect(result.removedBindings).toBe(1);
    expect(result.stopped).toBe(true);

    const cfg = harness.getConfig();
    expect(cfg.channels?.slack?.accounts?.default).toBeUndefined();
    expect(cfg.channels?.slack?.accounts?.qa).toBeDefined();
    expect(cfg.channels?.slack?.botToken).toBeUndefined();
    expect(cfg.channels?.slack?.appToken).toBeUndefined();
    expect(cfg.bindings).toEqual([{ agentId: "qa", match: { channel: "slack", accountId: "qa" } }]);
  });

  it("defaults accountId to default for Telegram disconnect", async () => {
    const harness = createHarness({
      initialConfig: {
        channels: {
          telegram: {
            enabled: true,
            botToken: "legacy-token",
            tokenFile: "/tmp/telegram.token",
            accounts: {
              default: { enabled: true, botToken: "acct-token" },
            },
          },
        },
        bindings: [{ agentId: "default", match: { channel: "telegram", accountId: "default" } }],
      },
    });

    const response = await harness.invoke({ channel: "telegram" });

    expect(response.ok).toBe(true);
    expect(harness.stopChannel).toHaveBeenCalledWith("telegram", "default");
    const result = response.data as {
      accountId: string;
      changed: boolean;
      removedBindings: number;
      accountRemoved: boolean;
      legacyCredentialsCleared: boolean;
    };
    expect(result.accountId).toBe("default");
    expect(result.changed).toBe(true);
    expect(result.accountRemoved).toBe(true);
    expect(result.legacyCredentialsCleared).toBe(true);
    expect(result.removedBindings).toBe(1);

    const cfg = harness.getConfig();
    expect(cfg.channels?.telegram?.accounts?.default).toBeUndefined();
    expect(cfg.channels?.telegram?.botToken).toBeUndefined();
    expect(cfg.channels?.telegram?.tokenFile).toBeUndefined();
    expect(cfg.bindings).toBeUndefined();
  });

  it("still writes config when stopChannel fails", async () => {
    const harness = createHarness({
      stopThrows: "channel not running",
      initialConfig: {
        channels: {
          slack: {
            accounts: {
              default: { enabled: true, botToken: "xoxb-default", appToken: "xapp-default" },
            },
          },
        },
      },
    });

    const response = await harness.invoke({ channel: "slack", accountId: "default" });

    expect(response.ok).toBe(true);
    expect(harness.writeConfigFile).toHaveBeenCalledTimes(1);
    const result = response.data as {
      stopped: boolean;
      stopError?: string;
      changed: boolean;
    };
    expect(result.stopped).toBe(false);
    expect(result.stopError).toContain("channel not running");
    expect(result.changed).toBe(true);
    expect(harness.getConfig().channels?.slack?.accounts?.default).toBeUndefined();
  });
});
