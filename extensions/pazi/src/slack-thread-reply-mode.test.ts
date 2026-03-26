import { describe, expect, it } from "vitest";
import {
  buildFinalSummary,
  resolveThreadReplyConfig,
} from "./slack-thread-reply-mode.js";

describe("resolveThreadReplyConfig", () => {
  it("returns full mode when no config exists", () => {
    const result = resolveThreadReplyConfig({}, "default");
    expect(result).toEqual({ mode: "full", ackMessage: "On it" });
  });

  it("returns full mode when account has no threadReplyMode", () => {
    const cfg = {
      channels: { slack: { accounts: { default: { enabled: true } } } },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result).toEqual({ mode: "full", ackMessage: "On it" });
  });

  it("returns summary-only with custom ack", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            myAccount: {
              threadReplyMode: "summary-only",
              ackMessage: "Working on it!",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "myAccount");
    expect(result).toEqual({
      mode: "summary-only",
      ackMessage: "Working on it!",
    });
  });

  it("returns quiet mode with default ack", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: { threadReplyMode: "quiet" },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result).toEqual({ mode: "quiet", ackMessage: "On it" });
  });

  it("ignores invalid threadReplyMode values", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: { threadReplyMode: "invalid-mode" },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result.mode).toBe("full");
  });

  it("trims whitespace from ackMessage", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              threadReplyMode: "summary-only",
              ackMessage: "  Got it!  ",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result.ackMessage).toBe("Got it!");
  });

  it("falls back to default ack when ackMessage is empty string", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              threadReplyMode: "summary-only",
              ackMessage: "   ",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result.ackMessage).toBe("On it");
  });

  it("returns full for a missing account", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            other: { threadReplyMode: "quiet" },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "nonexistent");
    expect(result.mode).toBe("full");
  });
});

describe("buildFinalSummary", () => {
  it("extracts last assistant text from string content", () => {
    const messages = [
      { role: "user", content: "Do something" },
      { role: "assistant", content: "I did the thing." },
    ];
    expect(buildFinalSummary(messages, true)).toBe("I did the thing.");
  });

  it("extracts last assistant text from array content", () => {
    const messages = [
      { role: "user", content: "Hello" },
      {
        role: "assistant",
        content: [
          { type: "text", text: "First part" },
          { type: "text", text: "Second part" },
        ],
      },
    ];
    expect(buildFinalSummary(messages, true)).toBe("First part\n\nSecond part");
  });

  it("uses LAST assistant message, not first", () => {
    const messages = [
      { role: "user", content: "Do task 1" },
      { role: "assistant", content: "Did task 1." },
      { role: "user", content: "Now do task 2" },
      { role: "assistant", content: "Task 2 is complete." },
    ];
    expect(buildFinalSummary(messages, true)).toBe("Task 2 is complete.");
  });

  it("returns error message on failure", () => {
    const messages = [{ role: "user", content: "Do something" }];
    expect(buildFinalSummary(messages, false, "timeout exceeded")).toBe(
      "I ran into an error: timeout exceeded",
    );
  });

  it('returns "Done." when no assistant content', () => {
    const messages = [{ role: "user", content: "Hello" }];
    expect(buildFinalSummary(messages, true)).toBe("Done.");
  });

  it('returns "Done." for empty messages array', () => {
    expect(buildFinalSummary([], true)).toBe("Done.");
  });

  it("handles invalid message shapes gracefully", () => {
    const messages = [
      null,
      undefined,
      "not an object",
      42,
      { role: "assistant" },
    ];
    expect(buildFinalSummary(messages as unknown[], true)).toBe("Done.");
  });

  it("skips assistant messages with empty string content", () => {
    const messages = [
      { role: "assistant", content: "  " },
      { role: "assistant", content: "Real answer." },
    ];
    // Should find "Real answer." since the first one is whitespace-only
    expect(buildFinalSummary(messages, true)).toBe("Real answer.");
  });

  it("skips non-text blocks in array content", () => {
    const messages = [
      {
        role: "assistant",
        content: [
          { type: "tool_use", id: "tool_1" },
          { type: "text", text: "Here is the result." },
        ],
      },
    ];
    expect(buildFinalSummary(messages, true)).toBe("Here is the result.");
  });
});
