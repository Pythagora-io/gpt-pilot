import { describe, expect, it } from "vitest";
import { resolveThreadReplyConfig } from "./slack-thread-reply-mode.js";

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

  it("resolves threadReplyMode independently when replyToMode is also configured", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              replyToMode: "all",
              threadReplyMode: "summary-only",
              ackMessage: "Custom ack",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result).toEqual({ mode: "summary-only", ackMessage: "Custom ack" });
  });

  it("supports quiet mode with replyToMode first", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              replyToMode: "first",
              threadReplyMode: "quiet",
              ackMessage: "One sec",
            },
          },
        },
      },
    };
    expect(resolveThreadReplyConfig(cfg, "default")).toEqual({
      mode: "quiet",
      ackMessage: "One sec",
    });
  });

  it("defaults to full when replyToMode is set but threadReplyMode is not", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              replyToMode: "first",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result).toEqual({ mode: "full", ackMessage: "On it" });
  });

  it("resolves quiet mode when replyToMode is off", () => {
    const cfg = {
      channels: {
        slack: {
          accounts: {
            default: {
              replyToMode: "off",
              threadReplyMode: "quiet",
              ackMessage: "Handled",
            },
          },
        },
      },
    };
    const result = resolveThreadReplyConfig(cfg, "default");
    expect(result).toEqual({ mode: "quiet", ackMessage: "Handled" });
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
