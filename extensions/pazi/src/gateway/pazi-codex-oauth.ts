import type { IncomingMessage, ServerResponse } from "node:http";
import { loginOpenAICodex } from "@mariozechner/pi-ai/oauth";
import {
  loadAuthProfileStoreForSecretsRuntime,
  saveAuthProfileStore,
} from "openclaw/plugin-sdk/agent-runtime";
import { resolveCodexAuthIdentity } from "../../../openai/openai-codex-auth-identity.js";

// ── Constants ────────────────────────────────────────────────────

const PROVIDER_ID = "openai-codex";
const SESSION_TTL_MS = 5 * 60 * 1000; // 5 minutes
const AUTH_URL_TIMEOUT_MS = 15_000; // 15 seconds to get auth URL

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

function generateSessionId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

// ── Session State ────────────────────────────────────────────────

interface OAuthSession {
  id: string;
  status: "pending" | "have_url" | "waiting_for_code" | "completed" | "failed";
  authUrl?: string;
  email?: string;
  error?: string;
  createdAt: number;
  resolveCode?: (code: string) => void;
  rejectCode?: (err: Error) => void;
  timeoutId?: ReturnType<typeof setTimeout>;
}

let activeSession: OAuthSession | null = null;

function cancelActiveSession(): void {
  if (!activeSession) {
    return;
  }
  if (activeSession.timeoutId) {
    clearTimeout(activeSession.timeoutId);
  }
  // Reject any pending code promise to unblock loginOpenAICodex
  if (activeSession.rejectCode) {
    activeSession.rejectCode(new Error("session_cancelled"));
  }
  activeSession = null;
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
    if (activeSession) {
      result.sessionStatus = activeSession.status;
      result.sessionId = activeSession.id;
    }
    writeJson(res, 200, result);
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "status_failed", message: String(err) });
  }
}

async function handleInitiate(res: ServerResponse): Promise<void> {
  // Cancel any existing session
  cancelActiveSession();

  const sessionId = generateSessionId();
  const session: OAuthSession = {
    id: sessionId,
    status: "pending",
    createdAt: Date.now(),
  };
  activeSession = session;

  // TTL: auto-fail after SESSION_TTL_MS
  session.timeoutId = setTimeout(() => {
    if (activeSession?.id === sessionId) {
      activeSession.status = "failed";
      activeSession.error = "session_timeout";
      // Reject pending code promise
      if (activeSession.rejectCode) {
        activeSession.rejectCode(new Error("session_timeout"));
      }
      // Clean up after 30s
      setTimeout(() => {
        if (activeSession?.id === sessionId) {
          activeSession = null;
        }
      }, 30_000);
    }
  }, SESSION_TTL_MS);

  // Promise for auth URL (resolved by onAuth callback)
  let authUrlResolve!: (url: string) => void;
  let authUrlReject!: (err: Error) => void;
  const authUrlPromise = new Promise<string>((resolve, reject) => {
    authUrlResolve = resolve;
    authUrlReject = reject;
  });

  // Promise for manual code input (resolved by "complete" action).
  // The promise is never awaited directly here — its resolve/reject callbacks
  // are stored on the session so the "complete" action can trigger them.
  let codeResolve!: (code: string) => void;
  let codeReject!: (err: Error) => void;
  void new Promise<string>((resolve, reject) => {
    codeResolve = resolve;
    codeReject = reject;
  });
  session.resolveCode = codeResolve;
  session.rejectCode = codeReject;

  // Start the OAuth flow in the background
  loginOpenAICodex({
    onAuth: (info: { url: string }) => {
      if (activeSession?.id !== sessionId) {
        return;
      }
      session.authUrl = info.url;
      session.status = "have_url";
      authUrlResolve(info.url);
    },
    onPrompt: async () => {
      // Called if the library needs manual input — wait for "complete" action
      if (activeSession?.id === sessionId) {
        session.status = "waiting_for_code";
      }
      return new Promise<string>((resolve, reject) => {
        if (activeSession?.id === sessionId) {
          session.resolveCode = resolve;
          session.rejectCode = reject;
        } else {
          reject(new Error("session_cancelled"));
        }
      });
    },
    onManualCodeInput: async () => {
      // Called when auto-callback doesn't arrive — wait for "complete" action
      if (activeSession?.id === sessionId) {
        session.status = "waiting_for_code";
      }
      return new Promise<string>((resolve, reject) => {
        if (activeSession?.id === sessionId) {
          session.resolveCode = resolve;
          session.rejectCode = reject;
        } else {
          reject(new Error("session_cancelled"));
        }
      });
    },
    onProgress: () => {
      // Ignore progress in gateway mode
    },
  })
    .then((creds) => {
      if (!creds || activeSession?.id !== sessionId) {
        return;
      }

      try {
        const identity = resolveCodexAuthIdentity({
          accessToken: creds.access,
          email: typeof creds.email === "string" ? creds.email : undefined,
        });

        const store = loadAuthProfileStoreForSecretsRuntime();
        const profileId = `${PROVIDER_ID}:${identity.email ?? identity.profileName ?? "default"}`;

        store.profiles[profileId] = {
          type: "oauth",
          provider: PROVIDER_ID,
          access: creds.access,
          refresh: creds.refresh,
          expires: creds.expires,
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

        session.status = "completed";
        session.email = identity.email;
      } catch (err) {
        session.status = "failed";
        session.error = String(err);
      }
    })
    .catch((err: unknown) => {
      if (activeSession?.id === sessionId) {
        session.status = "failed";
        session.error = String(err);
      }
    });

  // Wait for auth URL with timeout
  const authUrlTimeout = new Promise<null>((resolve) =>
    setTimeout(() => resolve(null), AUTH_URL_TIMEOUT_MS),
  );
  const authUrl = await Promise.race([authUrlPromise, authUrlTimeout]).catch(() => null);

  if (!authUrl) {
    // onAuth never fired — clean up and report
    if (activeSession?.id === sessionId && activeSession.status === "pending") {
      activeSession.status = "failed";
      activeSession.error = "auth_url_timeout";
    }
    authUrlReject(new Error("auth_url_timeout"));
    writeJson(res, 500, { ok: false, error: "auth_url_timeout" });
    return;
  }

  writeJson(res, 200, { ok: true, sessionId, authUrl });
}

function handleComplete(res: ServerResponse, body: Record<string, unknown>): void {
  const { sessionId, codeOrUrl } = body;

  if (typeof sessionId !== "string" || typeof codeOrUrl !== "string" || !codeOrUrl.trim()) {
    writeJson(res, 400, { ok: false, error: "invalid_params" });
    return;
  }

  if (!activeSession || activeSession.id !== sessionId) {
    writeJson(res, 404, { ok: false, error: "session_not_found" });
    return;
  }

  if (!activeSession.resolveCode) {
    writeJson(res, 409, { ok: false, error: "session_not_waiting_for_code" });
    return;
  }

  // Resolve the pending code promise — loginOpenAICodex will proceed
  activeSession.resolveCode(codeOrUrl.trim());
  writeJson(res, 200, { ok: true });
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
      case "initiate":
        await handleInitiate(res);
        return;
      case "complete":
        handleComplete(res, body);
        return;
      case "disconnect":
        handleDisconnect(res);
        return;
      default:
        writeJson(res, 400, { ok: false, error: "unknown_action" });
    }
  };
}
