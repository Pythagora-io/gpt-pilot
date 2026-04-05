import type { OpenClawConfig } from "openclaw/plugin-sdk/provider-onboard";
import { describe, expect, it } from "vitest";
import { applyHeartbeatDefaults, HEARTBEAT_SAFE_DEFAULTS } from "./heartbeat-defaults.js";

function makeConfig(heartbeat?: Record<string, unknown>): OpenClawConfig {
  return {
    agents: {
      defaults: {
        ...(heartbeat !== undefined ? { heartbeat } : {}),
      },
    },
  } as OpenClawConfig;
}

describe("applyHeartbeatDefaults", () => {
  it("fills all three fields when heartbeat has only session", () => {
    const cfg = makeConfig({ session: "__pazi_heartbeat" });
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.session).toBe("__pazi_heartbeat");
    expect(heartbeat.model).toBe(HEARTBEAT_SAFE_DEFAULTS.model);
    expect(heartbeat.lightContext).toBe(true);
    expect(heartbeat.isolatedSession).toBe(true);
  });

  it("returns config unchanged when all fields are already set", () => {
    const cfg = makeConfig({
      session: "__pazi_heartbeat",
      model: "custom/model",
      lightContext: false,
      isolatedSession: false,
    });
    const result = applyHeartbeatDefaults(cfg);
    expect(result).toBe(cfg);
  });

  it("preserves explicit false for boolean fields", () => {
    const cfg = makeConfig({
      session: "__pazi_heartbeat",
      lightContext: false,
      isolatedSession: false,
    });
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.lightContext).toBe(false);
    expect(heartbeat.isolatedSession).toBe(false);
    expect(heartbeat.model).toBe(HEARTBEAT_SAFE_DEFAULTS.model);
  });

  it("preserves a custom model", () => {
    const cfg = makeConfig({
      session: "__pazi_heartbeat",
      model: "anthropic/claude-sonnet-4-5",
    });
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.model).toBe("anthropic/claude-sonnet-4-5");
    expect(heartbeat.lightContext).toBe(true);
    expect(heartbeat.isolatedSession).toBe(true);
  });

  it("handles missing heartbeat object entirely", () => {
    const cfg = { agents: { defaults: {} } } as OpenClawConfig;
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.model).toBe(HEARTBEAT_SAFE_DEFAULTS.model);
    expect(heartbeat.lightContext).toBe(true);
    expect(heartbeat.isolatedSession).toBe(true);
  });

  it("handles missing agents.defaults entirely", () => {
    const cfg = {} as OpenClawConfig;
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.model).toBe(HEARTBEAT_SAFE_DEFAULTS.model);
    expect(heartbeat.lightContext).toBe(true);
    expect(heartbeat.isolatedSession).toBe(true);
  });

  it("fills only missing fields when some are set", () => {
    const cfg = makeConfig({
      session: "__pazi_heartbeat",
      model: "anthropic/claude-haiku-4-5",
    });
    const result = applyHeartbeatDefaults(cfg);
    const hb = (result.agents as Record<string, unknown>).defaults as Record<string, unknown>;
    const heartbeat = hb.heartbeat as Record<string, unknown>;

    expect(heartbeat.model).toBe("anthropic/claude-haiku-4-5");
    expect(heartbeat.lightContext).toBe(true);
    expect(heartbeat.isolatedSession).toBe(true);
  });
});
