type ChannelType = "slack" | "telegram";

interface ChannelDisconnectParams {
  channel: ChannelType;
  accountId?: string;
}

interface ChannelDisconnectResult {
  ok: true;
  channel: ChannelType;
  accountId: string;
  changed: boolean;
  accountRemoved: boolean;
  legacyCredentialsCleared: boolean;
  removedBindings: number;
  stopped: boolean;
  stopError?: string;
}

type GatewayErrorShape = {
  code: string;
  message: string;
};

interface GatewayMethodContext {
  params: unknown;
  respond: (ok: boolean, data?: unknown, error?: GatewayErrorShape) => void;
  context: {
    stopChannel: (channel: string, accountId?: string) => Promise<void>;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type OpenClawConfig = Record<string, any>;

interface ChannelDisconnectDeps {
  loadConfig: () => OpenClawConfig;
  writeConfigFile: (cfg: OpenClawConfig) => void | Promise<void>;
}

const VALID_CHANNELS: ReadonlySet<string> = new Set(["slack", "telegram"]);
const DEFAULT_ACCOUNT_ID = "default";
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

function isChannelType(value: unknown): value is ChannelType {
  return typeof value === "string" && VALID_CHANNELS.has(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeBindingChannel(channel: string): string {
  return channel.trim().toLowerCase();
}

function validateParams(raw: unknown):
  | {
      ok: true;
      params: ChannelDisconnectParams;
    }
  | { ok: false; error: string } {
  if (!isRecord(raw)) {
    return { ok: false, error: "params must be an object" };
  }
  if (!isChannelType(raw.channel)) {
    return { ok: false, error: "channel must be 'slack' or 'telegram'" };
  }
  return {
    ok: true,
    params: {
      channel: raw.channel,
      accountId: typeof raw.accountId === "string" ? raw.accountId : undefined,
    },
  };
}

function clearLegacyCredentialFields(params: {
  channel: ChannelType;
  channelConfig: Record<string, unknown>;
}): boolean {
  const fieldsByChannel: Record<ChannelType, readonly string[]> = {
    slack: ["botToken", "appToken", "botTokenFile", "appTokenFile"],
    telegram: ["botToken", "tokenFile"],
  };
  const keys = fieldsByChannel[params.channel];
  let changed = false;
  for (const key of keys) {
    if (key in params.channelConfig) {
      delete params.channelConfig[key];
      changed = true;
    }
  }
  return changed;
}

function removeAccountFromChannelConfig(params: {
  channelConfig: Record<string, unknown>;
  accountId: string;
}): { changed: boolean; removed: boolean } {
  const accountsRaw = params.channelConfig.accounts;
  if (!isRecord(accountsRaw)) {
    return { changed: false, removed: false };
  }
  if (!Object.hasOwn(accountsRaw, params.accountId)) {
    return { changed: false, removed: false };
  }

  const nextAccounts = { ...accountsRaw };
  delete nextAccounts[params.accountId];

  if (Object.keys(nextAccounts).length > 0) {
    params.channelConfig.accounts = nextAccounts;
  } else {
    delete params.channelConfig.accounts;
  }
  return { changed: true, removed: true };
}

function removeMatchingBindings(params: {
  cfg: OpenClawConfig;
  channel: ChannelType;
  accountId: string;
}): { changed: boolean; removedBindings: number; nextBindings?: unknown[] } {
  const bindings = Array.isArray(params.cfg.bindings) ? params.cfg.bindings : null;
  if (!bindings || bindings.length === 0) {
    return { changed: false, removedBindings: 0 };
  }

  const normalizedChannel = normalizeBindingChannel(params.channel);
  let removedBindings = 0;
  const nextBindings = bindings.filter((entry) => {
    if (!isRecord(entry) || !isRecord(entry.match)) {
      return true;
    }
    const matchChannel =
      typeof entry.match.channel === "string" ? normalizeBindingChannel(entry.match.channel) : "";
    const matchAccountId =
      typeof entry.match.accountId === "string" ? entry.match.accountId.trim() : "";
    if (matchChannel === normalizedChannel && matchAccountId === params.accountId) {
      removedBindings += 1;
      return false;
    }
    return true;
  });

  if (removedBindings === 0) {
    return { changed: false, removedBindings: 0 };
  }
  return { changed: true, removedBindings, nextBindings };
}

export function createPaziChannelsDisconnectHandler(
  deps: ChannelDisconnectDeps,
): (ctx: GatewayMethodContext) => Promise<void> {
  return async ({ params, respond, context }: GatewayMethodContext) => {
    const validation = validateParams(params);
    if (!validation.ok) {
      respondError(respond, ERROR_INVALID_REQUEST, validation.error);
      return;
    }

    const channel = validation.params.channel;
    const accountId = validation.params.accountId?.trim() || DEFAULT_ACCOUNT_ID;

    let stopped = false;
    let stopError: string | undefined;
    try {
      await context.stopChannel(channel, accountId);
      stopped = true;
    } catch (err) {
      stopError = err instanceof Error ? err.message : String(err);
    }

    try {
      const cfg = deps.loadConfig();
      const nextCfg = { ...cfg } as OpenClawConfig;
      let changed = false;
      let accountRemoved = false;
      let legacyCredentialsCleared = false;

      if (isRecord(cfg.channels)) {
        const nextChannels = { ...cfg.channels } as Record<string, unknown>;
        const channelConfigRaw = nextChannels[channel];
        if (isRecord(channelConfigRaw)) {
          const nextChannelConfig = { ...channelConfigRaw };
          const accountRemoval = removeAccountFromChannelConfig({
            channelConfig: nextChannelConfig,
            accountId,
          });
          if (accountRemoval.changed) {
            changed = true;
            accountRemoved = accountRemoval.removed;
          }

          if (accountId === DEFAULT_ACCOUNT_ID) {
            const cleared = clearLegacyCredentialFields({
              channel,
              channelConfig: nextChannelConfig,
            });
            if (cleared) {
              changed = true;
              legacyCredentialsCleared = true;
            }
          }

          if (changed) {
            if (Object.keys(nextChannelConfig).length > 0) {
              nextChannels[channel] = nextChannelConfig;
            } else {
              delete nextChannels[channel];
            }
            if (Object.keys(nextChannels).length > 0) {
              nextCfg.channels = nextChannels;
            } else {
              delete nextCfg.channels;
            }
          }
        }
      }

      const bindingCleanup = removeMatchingBindings({
        cfg,
        channel,
        accountId,
      });
      if (bindingCleanup.changed) {
        changed = true;
        if (bindingCleanup.nextBindings && bindingCleanup.nextBindings.length > 0) {
          nextCfg.bindings = bindingCleanup.nextBindings;
        } else {
          delete nextCfg.bindings;
        }
      }

      if (changed) {
        await deps.writeConfigFile(nextCfg);
      }

      const result: ChannelDisconnectResult = {
        ok: true,
        channel,
        accountId,
        changed,
        accountRemoved,
        legacyCredentialsCleared,
        removedBindings: bindingCleanup.removedBindings,
        stopped,
        ...(stopError ? { stopError } : {}),
      };
      respond(true, result);
    } catch (err) {
      respondError(
        respond,
        ERROR_UNAVAILABLE,
        `failed to disconnect channel account: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  };
}
