import { describe, expect, it, vi } from "vitest";

// Mock the plugin SDK before importing
vi.mock("openclaw/plugin-sdk/runtime-env", () => ({
  registerUnhandledRejectionHandler: vi.fn((handler) => {
    // Store the handler so tests can invoke it
    (globalThis as Record<string, unknown>).__testHandler = handler;
    return vi.fn(); // unregister function
  }),
}));

import { installChannelAuthCrashGuard } from "./suppress-channel-auth-crash.js";

const createMockLogger = () => ({
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
  verbose: vi.fn(),
});

function getHandler(): (reason: unknown) => boolean {
  return (globalThis as Record<string, unknown>).__testHandler as (reason: unknown) => boolean;
}

describe("installChannelAuthCrashGuard", () => {
  it("suppresses invalid_auth errors", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(new Error("An API error occurred: invalid_auth"))).toBe(true);
    expect(logger.error).toHaveBeenCalledWith(
      expect.stringContaining("Suppressed channel auth crash"),
    );
  });

  it("suppresses token_revoked errors", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(new Error("token_revoked"))).toBe(true);
  });

  it("suppresses token_expired errors", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(new Error("token_expired"))).toBe(true);
  });

  it("suppresses account_inactive errors", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(new Error("account_inactive"))).toBe(true);
  });

  it("does not suppress unrelated errors", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(new Error("ECONNREFUSED"))).toBe(false);
    expect(handler(new Error("some random error"))).toBe(false);
    expect(handler(new TypeError("Cannot read properties of undefined"))).toBe(false);
  });

  it("does not suppress null/undefined", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler(null)).toBe(false);
    expect(handler(undefined)).toBe(false);
  });

  it("handles string reasons", () => {
    const logger = createMockLogger();
    installChannelAuthCrashGuard(logger as never);
    const handler = getHandler();

    expect(handler("invalid_auth")).toBe(true);
    expect(handler("some other string")).toBe(false);
  });
});
