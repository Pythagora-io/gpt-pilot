import type { IncomingMessage, ServerResponse } from "node:http";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { resolveGatewayToken } from "../config.js";
import { getProxyContext, setProxyContext } from "../context.js";

type JsonBody = {
  browserEnabled?: boolean;
};

type BrowserEnabledHandlerDeps = {
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

export function createPaziBrowserEnabledHandler(deps: BrowserEnabledHandlerDeps) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const gatewayToken = resolveGatewayToken({
      configToken: deps.configToken,
      env: deps.env,
    });
    if (!gatewayToken) {
      deps.logger.warn("pazi browser-enabled request rejected: gateway token missing");
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

    const { browserEnabled } = body;
    if (typeof browserEnabled !== "boolean") {
      writeJson(res, 400, { error: "browserEnabled must be a boolean" });
      return;
    }

    // Get current context
    const currentContext = getProxyContext();
    if (!currentContext) {
      deps.logger.warn("pazi browser-enabled request rejected: no current context");
      writeJson(res, 500, { error: "no_current_context" });
      return;
    }

    // Update context with new browserEnabled value
    setProxyContext({
      ...currentContext,
      browserEnabled,
    });

    deps.logger.info(`Browser enabled status updated: ${browserEnabled}`);

    writeJson(res, 200, { ok: true, browserEnabled });
  };
}
