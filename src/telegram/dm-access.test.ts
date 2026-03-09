import type { Message } from "@grammyjs/types";
import type { Bot } from "grammy";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PAIRING_APPROVED_MESSAGE } from "../channels/plugins/pairing-message.js";
import type { NormalizedAllowFrom } from "./bot-access.js";

const hoisted = vi.hoisted(() => ({
  consumeChannelOnboardingCode: vi.fn(async () => false),
  addChannelAllowFromStoreEntry: vi.fn(async () => ({
    changed: true,
    allowFrom: [] as string[],
  })),
  upsertChannelPairingRequest: vi.fn(async () => ({
    code: "PAIRCODE",
    created: true,
  })),
  issuePairingChallenge: vi.fn(async () => ({
    created: true,
    code: "PAIRCODE",
  })),
}));

vi.mock("../pairing/pairing-store.js", () => ({
  consumeChannelOnboardingCode: hoisted.consumeChannelOnboardingCode,
  addChannelAllowFromStoreEntry: hoisted.addChannelAllowFromStoreEntry,
  upsertChannelPairingRequest: hoisted.upsertChannelPairingRequest,
}));

vi.mock("../pairing/pairing-challenge.js", () => ({
  issuePairingChallenge: hoisted.issuePairingChallenge,
}));

const { enforceTelegramDmAccess } = await import("./dm-access.js");

const EMPTY_DM_ALLOW: NormalizedAllowFrom = {
  entries: [],
  hasWildcard: false,
  hasEntries: false,
  invalidEntries: [],
};

function buildMessage(text: string): Message {
  return {
    chat: { id: 1001, type: "private" },
    from: { id: 999, username: "owner", first_name: "Owner" },
    text,
  } as unknown as Message;
}

function buildBot(sendMessage: ReturnType<typeof vi.fn>): Bot {
  return {
    api: {
      sendMessage,
    },
  } as unknown as Bot;
}

describe("enforceTelegramDmAccess onboarding flow", () => {
  beforeEach(() => {
    hoisted.consumeChannelOnboardingCode.mockReset();
    hoisted.consumeChannelOnboardingCode.mockResolvedValue(false);
    hoisted.addChannelAllowFromStoreEntry.mockReset();
    hoisted.addChannelAllowFromStoreEntry.mockResolvedValue({
      changed: true,
      allowFrom: [],
    });
    hoisted.upsertChannelPairingRequest.mockReset();
    hoisted.upsertChannelPairingRequest.mockResolvedValue({
      code: "PAIRCODE",
      created: true,
    });
    hoisted.issuePairingChallenge.mockReset();
    hoisted.issuePairingChallenge.mockResolvedValue({
      created: true,
      code: "PAIRCODE",
    });
  });

  it("auto-approves sender when /start payload matches onboarding code", async () => {
    hoisted.consumeChannelOnboardingCode.mockResolvedValue(true);
    const sendMessage = vi.fn(async () => undefined);
    const logger = { info: vi.fn() };

    const allowed = await enforceTelegramDmAccess({
      isGroup: false,
      dmPolicy: "pairing",
      msg: buildMessage("/start CLAIMME1"),
      chatId: 1001,
      effectiveDmAllow: EMPTY_DM_ALLOW,
      accountId: "default",
      bot: buildBot(sendMessage),
      logger,
    });

    expect(allowed).toBe(false);
    expect(hoisted.consumeChannelOnboardingCode).toHaveBeenCalledWith({
      channel: "telegram",
      accountId: "default",
      code: "CLAIMME1",
    });
    expect(hoisted.addChannelAllowFromStoreEntry).toHaveBeenCalledWith({
      channel: "telegram",
      accountId: "default",
      entry: "999",
    });
    expect(sendMessage).toHaveBeenCalledWith(1001, PAIRING_APPROVED_MESSAGE);
    expect(hoisted.issuePairingChallenge).not.toHaveBeenCalled();
  });

  it("falls back to pairing challenge when onboarding payload does not match", async () => {
    hoisted.consumeChannelOnboardingCode.mockResolvedValue(false);
    const sendMessage = vi.fn(async () => undefined);

    const allowed = await enforceTelegramDmAccess({
      isGroup: false,
      dmPolicy: "pairing",
      msg: buildMessage("/start INVALID"),
      chatId: 1001,
      effectiveDmAllow: EMPTY_DM_ALLOW,
      accountId: "default",
      bot: buildBot(sendMessage),
      logger: { info: vi.fn() },
    });

    expect(allowed).toBe(false);
    expect(hoisted.issuePairingChallenge).toHaveBeenCalledTimes(1);
    expect(hoisted.addChannelAllowFromStoreEntry).not.toHaveBeenCalled();
  });

  it("allows sender when already authorized", async () => {
    const allowlist: NormalizedAllowFrom = {
      entries: ["999"],
      hasWildcard: false,
      hasEntries: true,
      invalidEntries: [],
    };

    const allowed = await enforceTelegramDmAccess({
      isGroup: false,
      dmPolicy: "allowlist",
      msg: buildMessage("hello"),
      chatId: 1001,
      effectiveDmAllow: allowlist,
      accountId: "default",
      bot: buildBot(vi.fn(async () => undefined)),
      logger: { info: vi.fn() },
    });

    expect(allowed).toBe(true);
    expect(hoisted.consumeChannelOnboardingCode).not.toHaveBeenCalled();
    expect(hoisted.issuePairingChallenge).not.toHaveBeenCalled();
  });
});
