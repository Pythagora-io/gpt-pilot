import type { IncomingMessage, ServerResponse } from "node:http";
import { createSubsystemLogger } from "../logging/subsystem.js";
import { setProxyContext } from "./pazi-proxy.js";

type PaziContextRequest = {
  userId?: string;
  proxyToken?: string;
};

type PaziContextOpts = {
  gatewayToken?: string;
};

const log = createSubsystemLogger("gateway/pazi-context");

function writeJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<PaziContextRequest | null> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    if (typeof chunk === "string") {
      chunks.push(Buffer.from(chunk));
    } else {
      chunks.push(chunk);
    }
  }
  try {
    const body = JSON.parse(Buffer.concat(chunks).toString());
    if (body && typeof body === "object") {
      return body as PaziContextRequest;
    }
  } catch {
    return null;
  }
  return null;
}

export async function handlePaziContextRequest(
  req: IncomingMessage,
  res: ServerResponse,
  opts: PaziContextOpts,
): Promise<boolean> {
  if (req.method !== "POST" || req.url !== "/pazi/context") {
    return false;
  }

  if (!opts.gatewayToken) {
    log.warn("pazi context request rejected: gateway token missing");
    writeJson(res, 500, { error: "gateway_token_missing" });
    return true;
  }

  const authHeader = req.headers.authorization;
  if (authHeader !== `Bearer ${opts.gatewayToken}`) {
    writeJson(res, 401, { error: "unauthorized" });
    return true;
  }

  const body = await readJson(req);
  if (!body) {
    writeJson(res, 400, { error: "invalid JSON" });
    return true;
  }

  const { userId, proxyToken } = body;
  if (!userId || !proxyToken) {
    writeJson(res, 400, { error: "missing userId or proxyToken" });
    return true;
  }

  setProxyContext({ userId, proxyToken });
  writeJson(res, 200, { ok: true });
  return true;
}
