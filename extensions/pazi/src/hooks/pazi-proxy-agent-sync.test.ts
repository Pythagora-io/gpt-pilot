import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { beforeEach, describe, expect, it } from "vitest";
import { _resetForTest, getProxyContext, setProxyContext } from "../context.js";
import { registerProxyAgentSyncHook } from "./pazi-proxy-agent-sync.js";

describe("registerProxyAgentSyncHook", () => {
  beforeEach(() => {
    _resetForTest();
  });

  it("updates proxy context agentId from before_tool_call context", () => {
    let beforeToolCallHandler: ((event: unknown, ctx: { agentId?: string }) => void) | undefined;

    const api = {
      on: (name: string, handler: (event: unknown, ctx: { agentId?: string }) => void) => {
        if (name === "before_tool_call") {
          beforeToolCallHandler = handler;
        }
      },
    } as unknown as OpenClawPluginApi;

    registerProxyAgentSyncHook(api);
    expect(beforeToolCallHandler).toBeTypeOf("function");

    setProxyContext({
      userId: "user-1",
      agentId: "default-agent",
      proxyToken: "proxy-token-1",
    });

    beforeToolCallHandler?.({}, { agentId: "active-agent" });

    expect(getProxyContext()?.agentId).toBe("active-agent");
  });

  it("ignores empty agentId values", () => {
    let beforeToolCallHandler: ((event: unknown, ctx: { agentId?: string }) => void) | undefined;

    const api = {
      on: (name: string, handler: (event: unknown, ctx: { agentId?: string }) => void) => {
        if (name === "before_tool_call") {
          beforeToolCallHandler = handler;
        }
      },
    } as unknown as OpenClawPluginApi;

    registerProxyAgentSyncHook(api);

    setProxyContext({
      userId: "user-1",
      agentId: "default-agent",
      proxyToken: "proxy-token-1",
    });

    beforeToolCallHandler?.({}, { agentId: "   " });

    expect(getProxyContext()?.agentId).toBe("default-agent");
  });
});
