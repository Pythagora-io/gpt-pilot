import type { IncomingMessage, ServerResponse } from "node:http";
import {
  loadAuthProfileStoreForSecretsRuntime,
  saveAuthProfileStore,
} from "openclaw/plugin-sdk/agent-runtime";
import { listCredentialSummaries, parseProfileId } from "../credentials/shared.js";

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

// ── Validation ───────────────────────────────────────────────────

const MAX_PROFILE_ID_LENGTH = 256;

function isValidProfileId(profileId: unknown): profileId is string {
  if (typeof profileId !== "string" || profileId.length === 0) return false;
  if (profileId.length > MAX_PROFILE_ID_LENGTH) return false;
  if (profileId.includes("/") || profileId.includes("\\") || profileId.includes("\0")) return false;
  // Must contain a colon (service:label format)
  if (!profileId.includes(":")) return false;
  // Validate it parses correctly
  const parsed = parseProfileId(profileId, "");
  return parsed.service.length > 0 && parsed.label.length > 0;
}

// ── Handlers ─────────────────────────────────────────────────────

function handleList(res: ServerResponse): void {
  try {
    const store = loadAuthProfileStoreForSecretsRuntime();
    const credentials = listCredentialSummaries(store);
    writeJson(res, 200, { ok: true, credentials });
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "load_failed", message: String(err) });
  }
}

function handleDelete(res: ServerResponse, profileId: unknown): void {
  if (!isValidProfileId(profileId)) {
    writeJson(res, 400, { ok: false, error: "invalid_profile_id" });
    return;
  }

  try {
    const store = loadAuthProfileStoreForSecretsRuntime();

    if (!(profileId in store.profiles)) {
      writeJson(res, 404, { ok: false, error: "not_found" });
      return;
    }

    delete store.profiles[profileId];

    // Also clean up order and usage stats entries if present
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
    if (store.lastGood) {
      delete store.lastGood[profileId];
    }
    if (store.usageStats) {
      delete store.usageStats[profileId];
    }

    saveAuthProfileStore(store);
    writeJson(res, 200, { ok: true, deleted: profileId });
  } catch (err) {
    writeJson(res, 500, { ok: false, error: "delete_failed", message: String(err) });
  }
}

// ── Route handler ────────────────────────────────────────────────

export function createPaziCredentialsHandler(): (
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
      case "list":
        handleList(res);
        return;
      case "delete":
        handleDelete(res, body.profileId);
        return;
      default:
        writeJson(res, 400, { ok: false, error: "unknown_action" });
    }
  };
}
