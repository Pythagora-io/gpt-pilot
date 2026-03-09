import type { PairingRequest } from "../../../src/pairing/pairing-store.js";

type ChannelType = "telegram";
type OpenClawConfig = Record<string, unknown>;

interface PairingListParams {
  channel: ChannelType;
  accountId?: string;
}

interface PairingApproveParams extends PairingListParams {
  code: string;
}

interface PairingListResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  pending: PairingRequestSummary[];
}

interface PairingApproveResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  approved: boolean;
  id?: string;
}

interface PairingRequestSummary {
  id: string;
  code: string;
  createdAt: string;
  lastSeenAt: string;
  meta?: {
    accountId?: string;
    username?: string;
    firstName?: string;
    lastName?: string;
    senderUserId?: string;
  };
}

type GatewayErrorShape = {
  code: string;
  message: string;
};

interface GatewayMethodContext {
  params: unknown;
  respond: (ok: boolean, data?: unknown, error?: GatewayErrorShape) => void;
}

interface PairingHandlersDeps {
  loadConfig: () => OpenClawConfig;
  env: NodeJS.ProcessEnv;
  logWarn: (message: string) => void;
  listRequests: (params: {
    channel: ChannelType;
    accountId: string;
    env: NodeJS.ProcessEnv;
  }) => Promise<PairingRequest[]>;
  approveCode: (params: {
    channel: ChannelType;
    accountId: string;
    code: string;
    env: NodeJS.ProcessEnv;
  }) => Promise<{ id: string; entry?: PairingRequest } | null>;
  notifyApproved: (params: {
    channelId: ChannelType;
    id: string;
    cfg: OpenClawConfig;
  }) => Promise<void>;
}

const DEFAULT_ACCOUNT_ID = "default";
const VALID_CHANNELS: ReadonlySet<string> = new Set(["telegram"]);
const ERROR_INVALID_REQUEST = "INVALID_REQUEST";
const ERROR_UNAVAILABLE = "UNAVAILABLE";

function respondError(
  respond: GatewayMethodContext["respond"],
  code: string,
  message: string,
  payload?: unknown,
): void {
  respond(false, payload, { code, message });
}

function resolveAccountId(raw: unknown): string {
  // These gateway methods are intentionally account-scoped. Missing/blank account IDs default
  // to "default" instead of unscoped pairing-store reads.
  if (typeof raw !== "string") {
    return DEFAULT_ACCOUNT_ID;
  }
  const trimmed = raw.trim();
  return trimmed || DEFAULT_ACCOUNT_ID;
}

function parseListParams(
  raw: unknown,
): { ok: true; value: PairingListParams } | { ok: false; error: string } {
  if (!raw || typeof raw !== "object") {
    return { ok: false, error: "params must be an object" };
  }
  const params = raw as Record<string, unknown>;
  const channel = params.channel === "telegram" ? "telegram" : null;
  if (!channel || !VALID_CHANNELS.has(channel)) {
    return { ok: false, error: "channel must be 'telegram'" };
  }
  return {
    ok: true,
    value: {
      channel,
      accountId: typeof params.accountId === "string" ? params.accountId : undefined,
    },
  };
}

function parseApproveParams(
  raw: unknown,
): { ok: true; value: PairingApproveParams } | { ok: false; error: string } {
  const parsed = parseListParams(raw);
  if (!parsed.ok) {
    return parsed;
  }
  const params = raw as Record<string, unknown>;
  const code = typeof params.code === "string" ? params.code.trim() : "";
  if (!code) {
    return { ok: false, error: "code is required" };
  }
  return {
    ok: true,
    value: {
      ...parsed.value,
      code,
    },
  };
}

function summarizePairingRequest(request: PairingRequest): PairingRequestSummary {
  const meta = request.meta ?? {};
  return {
    id: request.id,
    code: request.code,
    createdAt: request.createdAt,
    lastSeenAt: request.lastSeenAt,
    meta: {
      accountId: typeof meta.accountId === "string" ? meta.accountId : undefined,
      username: typeof meta.username === "string" ? meta.username : undefined,
      firstName: typeof meta.firstName === "string" ? meta.firstName : undefined,
      lastName: typeof meta.lastName === "string" ? meta.lastName : undefined,
      senderUserId: typeof meta.senderUserId === "string" ? meta.senderUserId : undefined,
    },
  };
}

export function createPaziChannelsPairingListHandler(
  deps: PairingHandlersDeps,
): (ctx: GatewayMethodContext) => Promise<void> {
  return async ({ params, respond }: GatewayMethodContext) => {
    const parsed = parseListParams(params);
    if (!parsed.ok) {
      respondError(respond, ERROR_INVALID_REQUEST, parsed.error);
      return;
    }

    const accountId = resolveAccountId(parsed.value.accountId);
    try {
      const pending = await deps.listRequests({
        channel: parsed.value.channel,
        accountId,
        env: deps.env,
      });
      const result: PairingListResult = {
        ok: true,
        channel: parsed.value.channel,
        accountId,
        pending: pending.map((entry) => summarizePairingRequest(entry)),
      };
      respond(true, result);
    } catch (err) {
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `failed to load pairing requests: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  };
}

export function createPaziChannelsPairingApproveHandler(
  deps: PairingHandlersDeps,
): (ctx: GatewayMethodContext) => Promise<void> {
  return async ({ params, respond }: GatewayMethodContext) => {
    const parsed = parseApproveParams(params);
    if (!parsed.ok) {
      respondError(respond, ERROR_INVALID_REQUEST, parsed.error);
      return;
    }

    const accountId = resolveAccountId(parsed.value.accountId);
    try {
      const cfgSnapshot = deps.loadConfig();
      const approved = await deps.approveCode({
        channel: parsed.value.channel,
        accountId,
        code: parsed.value.code,
        env: deps.env,
      });
      if (!approved) {
        const result: PairingApproveResult = {
          ok: true,
          channel: parsed.value.channel,
          accountId,
          approved: false,
        };
        respond(true, result);
        return;
      }
      try {
        await deps.notifyApproved({
          channelId: parsed.value.channel,
          id: approved.id,
          cfg: cfgSnapshot,
        });
      } catch (err) {
        deps.logWarn(
          `pazi.channels.pairing.approve notification failed for telegram id=${approved.id}: ${String(err)}`,
        );
        // Approval is persisted even when notification back to Telegram fails.
      }
      const result: PairingApproveResult = {
        ok: true,
        channel: parsed.value.channel,
        accountId,
        approved: true,
        id: approved.id,
      };
      respond(true, result);
    } catch (err) {
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `failed to approve pairing request: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  };
}
