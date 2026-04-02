import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { describe, expect, it } from "vitest";
import { registerWebchatFileSupportHook } from "./pazi-webchat-file-support.js";

type BeforePromptBuildHandler = (
  event: unknown,
  ctx: { channelId?: string; messageProvider?: string },
) => { appendSystemContext: string } | undefined;

function captureHandler(): {
  handler: BeforePromptBuildHandler | undefined;
} {
  const result: { handler: BeforePromptBuildHandler | undefined } = { handler: undefined };

  const api = {
    on: (name: string, handler: BeforePromptBuildHandler, _opts?: { priority: number }) => {
      if (name === "before_prompt_build") {
        result.handler = handler;
      }
    },
  } as unknown as OpenClawPluginApi;

  registerWebchatFileSupportHook(api);
  return result;
}

describe("registerWebchatFileSupportHook", () => {
  it("registers a before_prompt_build handler", () => {
    const { handler } = captureHandler();
    expect(handler).toBeTypeOf("function");
  });

  it("injects guidance when channelId is webchat", () => {
    const { handler } = captureHandler();
    const result = handler?.({}, { channelId: "webchat" });
    expect(result).toBeDefined();
    expect(result?.appendSystemContext).toContain("## Webchat File Support");
  });

  it("injects guidance when messageProvider is webchat (fallback)", () => {
    const { handler } = captureHandler();
    const result = handler?.({}, { messageProvider: "webchat" });
    expect(result).toBeDefined();
    expect(result?.appendSystemContext).toContain("## Webchat File Support");
  });

  it("handles case insensitivity for channelId", () => {
    const { handler } = captureHandler();

    const upper = handler?.({}, { channelId: "WEBCHAT" });
    expect(upper?.appendSystemContext).toContain("## Webchat File Support");

    const mixed = handler?.({}, { channelId: "Webchat" });
    expect(mixed?.appendSystemContext).toContain("## Webchat File Support");
  });

  it("handles case insensitivity for messageProvider", () => {
    const { handler } = captureHandler();
    const result = handler?.({}, { messageProvider: "WEBCHAT" });
    expect(result?.appendSystemContext).toContain("## Webchat File Support");
  });

  it("returns undefined for non-webchat channels", () => {
    const { handler } = captureHandler();

    expect(handler?.({}, { channelId: "slack" })).toBeUndefined();
    expect(handler?.({}, { channelId: "telegram" })).toBeUndefined();
    expect(handler?.({}, { channelId: "discord" })).toBeUndefined();
    expect(handler?.({}, {})).toBeUndefined();
  });

  it("prefers channelId over messageProvider", () => {
    const { handler } = captureHandler();

    const result = handler?.({}, { channelId: "slack", messageProvider: "webchat" });
    expect(result).toBeUndefined();
  });

  it("guidance contains key phrases", () => {
    const { handler } = captureHandler();
    const result = handler?.({}, { channelId: "webchat" });
    const text = result?.appendSystemContext ?? "";

    expect(text).toContain("write");
    expect(text).toContain("file card");
    expect(text).toContain("Do NOT tell the user");
    expect(text).toContain("Do NOT use the `message` tool");
  });
});
