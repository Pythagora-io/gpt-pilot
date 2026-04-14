import type { IncomingMessage, ServerResponse } from "node:http";
import {
  loadAuthProfileStoreForSecretsRuntime,
  saveAuthProfileStore,
} from "openclaw/plugin-sdk/agent-runtime";
import { resolveCodexAuthIdentity } from "../../../openai/openai-codex-auth-identity.js";

// ── Constants ────────────────────────────────────────────────────

const PROVIDER_ID = "openai-codex";

// ── Helpers ──────────────────────────────────────────────────────

function writeJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readJsonBody(req: IncomingMessage): Promise<Record<string, unknown> | null> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    if (typeof chunk === "string") {
      chunks.push(Buffer.from(chunk));
    } else {
      chunks.push(chunk as Buffer);
    }
  }
  try {
    const parsed: unknown = JSON.parse(Buffer.concat(chunks).toString());
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return null;
  }
  return null;
}

// ── Helpers for auth profile inspection ──────────────────────────

function findCodexProfile(
  store: ReturnType<typeof loadAuthProfileStoreForSecretsRuntime>,
): { profileId: string; email?: string } | null {
  for (const [profileId, cred] of Object.entries(store.profiles)) {
    const c = cred as Record<string, unknown>;
    if (c.type === "oauth" && c.provider === PROVIDER_ID) {
      return {
        profileId,
        email: typeof c.email === "string" ? c.email : undefined,
      };
    }
  }
  return null;
}

// ── Action Handlers ──────────────────────────────────────────────

function handleStatus(res: ServerResponse): void {
  try {
    const store = loadAuthProfileStoreForSecretsRuntime();
    const profile = findCodexProfile(store);

    const result: Record<string, unknown> = {
      ok: true,
      connected: !!profile,
    };
    if (profile?.email) {
      result.email = profile.email;
    }
    writeJson(res, 200, result);
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "status_failed", message: String(err) });
  }
}

function handlePushCredentials(res: ServerResponse, body: Record<string, unknown>): void {
  const { accessToken, refreshToken, expiresAt, email } = body;

  if (typeof accessToken !== "string" || !accessToken) {
    writeJson(res, 400, { ok: false, error: "invalid_params: accessToken required" });
    return;
  }

  try {
    const identity = resolveCodexAuthIdentity({
      accessToken,
      email: typeof email === "string" ? email : undefined,
    });

    const store = loadAuthProfileStoreForSecretsRuntime();
    const profileId = `${PROVIDER_ID}:${identity.email ?? identity.profileName ?? "default"}`;

    store.profiles[profileId] = {
      type: "oauth",
      provider: PROVIDER_ID,
      access: accessToken,
      refresh: typeof refreshToken === "string" ? refreshToken : undefined,
      expires: typeof expiresAt === "number" ? expiresAt : undefined,
      email: identity.email,
    } as (typeof store.profiles)[string];

    // Update provider order
    if (!store.order) {
      store.order = {};
    }
    const orderList = store.order[PROVIDER_ID] ?? [];
    if (!orderList.includes(profileId)) {
      store.order[PROVIDER_ID] = [...orderList, profileId];
    }

    saveAuthProfileStore(store);
    writeJson(res, 200, { ok: true, email: identity.email });
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "push_credentials_failed", message: String(err) });
  }
}

function handlePushCredentials(res: ServerResponse, body: Record<string, unknown>): void {
  const { accessToken, refreshToken, expiresAt, email } = body;

  if (typeof accessToken !== "string" || !accessToken) {
    writeJson(res, 400, { ok: false, error: "invalid_params: accessToken required" });
    return;
  }

  try {
    // Cancel any in-progress interactive session
    cancelActiveSession();

    const identity = resolveCodexAuthIdentity({
      accessToken,
      email: typeof email === "string" ? email : undefined,
    });

    const store = loadAuthProfileStoreForSecretsRuntime();
    const profileId = `${PROVIDER_ID}:${identity.email ?? identity.profileName ?? "default"}`;

    store.profiles[profileId] = {
      type: "oauth",
      provider: PROVIDER_ID,
      access: accessToken,
      refresh: typeof refreshToken === "string" ? refreshToken : undefined,
      expires: typeof expiresAt === "number" ? expiresAt : undefined,
      email: identity.email,
    };

    // Update provider order
    if (!store.order) {
      store.order = {};
    }
    const orderList = store.order[PROVIDER_ID] ?? [];
    if (!orderList.includes(profileId)) {
      store.order[PROVIDER_ID] = [...orderList, profileId];
    }

    saveAuthProfileStore(store);
    writeJson(res, 200, { ok: true, email: identity.email });
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "push_credentials_failed", message: String(err) });
  }
}

function handleDisconnect(res: ServerResponse): void {
  try {
    const store = loadAuthProfileStoreForSecretsRuntime();
    const profilesToDelete: string[] = [];

    for (const [profileId, cred] of Object.entries(store.profiles)) {
      const c = cred as Record<string, unknown>;
      if (c.type === "oauth" && c.provider === PROVIDER_ID) {
        profilesToDelete.push(profileId);
      }
    }

    if (profilesToDelete.length === 0) {
      writeJson(res, 404, { ok: false, error: "not_found" });
      return;
    }

    for (const profileId of profilesToDelete) {
      delete store.profiles[profileId];

      // Clean up order entries
      if (store.order) {
        for (const [provider, ids] of Object.entries(store.order)) {
          const filtered = ids.filter((id) => id !== profileId);
          if (filtered.length === 0) {
            delete store.order[provider];
          } else {
            store.order[provider] = filtered;
          }
        }
      }
      // Clean up other metadata
      if (store.lastGood) {
        delete store.lastGood[profileId];
      }
      if (store.usageStats) {
        delete store.usageStats[profileId];
      }
    }

    saveAuthProfileStore(store);
    writeJson(res, 200, { ok: true, deleted: profilesToDelete });
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "disconnect_failed", message: String(err) });
  }
}

// ── Route Handler ────────────────────────────────────────────────

export function createPaziCodexOAuthHandler(): (
  req: IncomingMessage,
  res: ServerResponse,
) => Promise<void> {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    if (req.method !== "POST") {
      writeJson(res, 405, { ok: false, error: "method_not_allowed" });
      return;
    }

    const body = await readJsonBody(req);
    if (!body) {
      writeJson(res, 400, { ok: false, error: "invalid_json" });
      return;
    }

    const { action } = body;

    switch (action) {
      case "status":
        handleStatus(res);
        return;
      case "push-credentials":
        handlePushCredentials(res, body);
        return;
      case "push-credentials":
        handlePushCredentials(res, body);
        return;
      case "disconnect":
        handleDisconnect(res);
        return;
      default:
        writeJson(res, 400, { ok: false, error: "unknown_action" });
    }
  };
}
