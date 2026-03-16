import { beforeEach, describe, expect, it } from "vitest";
import {
  clearProxyContext,
  getProxyLastActivityAt,
  isProxyBusyForStatus,
  markProxyActivity,
  setProxyContext,
} from "./context.js";

describe("pazi context busy status", () => {
  beforeEach(() => {
    clearProxyContext();
  });

  it("returns not busy when no context has been set", () => {
    expect(isProxyBusyForStatus(1_000_000)).toBe(false);
    expect(getProxyLastActivityAt()).toBeNull();
  });

  it("returns not busy when context exists but there is no activity yet", () => {
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    expect(isProxyBusyForStatus(1_000_000)).toBe(false);
  });

  it("returns busy when activity is within the 30-minute window", () => {
    const nowMs = 1_000_000;
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    markProxyActivity(nowMs - 29 * 60 * 1000);
    expect(isProxyBusyForStatus(nowMs)).toBe(true);
  });

  it("returns not busy when activity is older than 30 minutes", () => {
    const nowMs = 1_000_000;
    setProxyContext({
      userId: "u1",
      agentId: "a1",
      proxyToken: "p1",
    });
    markProxyActivity(nowMs - 31 * 60 * 1000);
    expect(isProxyBusyForStatus(nowMs)).toBe(false);
  });
});
