import type { IncomingMessage, ServerResponse } from "node:http";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { setProxyContext } from "./context.js";
import { resolveGatewayToken } from "./config.js";

type JsonBody = {
  userId?: string;
  proxyToken?: string;
};

type ContextHandlerDeps = {
  configToken?: string;
  env?: NodeJS.ProcessEnv;
  logger: OpenClawPluginApi["logger"];
};

function writeJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readJsonBody(req: IncomingMessage): Promise<JsonBody | null> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    if (typeof chunk === "string") {
      chunks.push(Buffer.from(chunk));
    } else {
      chunks.push(chunk);
    }
  }
  try {
    const parsed = JSON.parse(Buffer.concat(chunks).toString());
    if (parsed && typeof parsed === "object") {
      return parsed as JsonBody;
    }
  } catch {
    return null;
  }
  return null;
}

export function createPaziContextHandler(deps: ContextHandlerDeps) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const gatewayToken = resolveGatewayToken({
      configToken: deps.configToken,
      env: deps.env,
    });
    if (!gatewayToken) {
      deps.logger.warn("pazi context request rejected: gateway token missing");
      writeJson(res, 500, { error: "gateway_token_missing" });
      return;
    }

    const authHeader = req.headers.authorization;
    if (authHeader !== `Bearer ${gatewayToken}`) {
      writeJson(res, 401, { error: "unauthorized" });
      return;
    }

    const body = await readJsonBody(req);
    if (!body) {
      writeJson(res, 400, { error: "invalid JSON" });
      return;
    }

    const { userId, proxyToken } = body;
    if (!userId || !proxyToken) {
      writeJson(res, 400, { error: "missing userId or proxyToken" });
      return;
    }

    setProxyContext({ userId, proxyToken });
    writeJson(res, 200, { ok: true });
  };
}
