import type { IncomingMessage, ServerResponse } from "node:http";
import { getProxyContext, setProxyContext } from "../context.js";
import { resolveGatewayToken } from "../config.js";

type MigrationNoticeBody = {
  migrationId?: string;
  newPlan?: string;
};

type MigrationNoticeHandlerDeps = {
  configToken?: string;
  env?: NodeJS.ProcessEnv;
  logger: { info: (message: string) => void; warn: (message: string) => void };
};

function writeJson(res: ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readJsonBody(req: IncomingMessage): Promise<MigrationNoticeBody | null> {
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
      return parsed as MigrationNoticeBody;
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Creates an HTTP handler for POST /pazi/migration-notice.
 *
 * Called by the workspace controller when a migration starts for this workspace.
 * Sets a migrationNotice on the proxy context so the agent proxy can
 * gracefully reject new LLM requests.
 */
export function createPaziMigrationNoticeHandler(deps: MigrationNoticeHandlerDeps) {
  return async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const gatewayToken = resolveGatewayToken({
      configToken: deps.configToken,
      env: deps.env,
    });
    if (!gatewayToken) {
      deps.logger.warn("pazi migration-notice rejected: gateway token missing");
      writeJson(res, 500, { error: "gateway_token_missing" });
      return;
    }

    const authHeader = req.headers.authorization;
    if (authHeader !== `Bearer ${gatewayToken}`) {
      writeJson(res, 401, { error: "unauthorized" });
      return;
    }

    const body = await readJsonBody(req);
    if (!body?.migrationId || !body.newPlan) {
      writeJson(res, 400, { error: "missing migrationId or newPlan" });
      return;
    }

    const context = getProxyContext();
    if (!context) {
      writeJson(res, 503, { error: "no proxy context set" });
      return;
    }

    setProxyContext({
      ...context,
      migrationNotice: {
        migrationId: body.migrationId,
        newPlan: body.newPlan,
        startedAt: new Date().toISOString(),
      },
    });

    deps.logger.info(
      `pazi migration notice set: migrationId=${body.migrationId}, newPlan=${body.newPlan}`,
    );

    writeJson(res, 200, { ok: true });
  };
}
