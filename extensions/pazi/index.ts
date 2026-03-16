import type { Server as HttpServer } from "node:http";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { resolveAgentWorkspaceDir, resolveDefaultAgentId } from "../../src/agents/agent-scope.js";
import { notifyPairingApproved } from "../../src/channels/plugins/pairing.js";
import {
  approveChannelPairingCode,
  listChannelPairingRequests,
} from "../../src/pairing/pairing-store.js";
import { normalizeAgentId } from "../../src/routing/session-key.js";
import { resolveBrowserUseConfig } from "./src/browser-use/config.js";
import { createBrowserUseTools } from "./src/browser-use/tools.js";
import { createPaziChannelsConfigureHandler } from "./src/channels-configure.js";
import {
  createPaziChannelsPairingApproveHandler,
  createPaziChannelsPairingListHandler,
} from "./src/channels-pairing.js";
import { resolvePaziBillingConfig } from "./src/config.js";
import { getProxyLastActivityAt, isProxyBusyForStatus } from "./src/context.js";
import {
  createPaziFilesGet,
  createPaziFilesList,
  createPaziFilesSet,
} from "./src/gateway/pazi-files.js";
import { createPipedreamTools } from "./src/pipedream/tools.js";
import { createPaziContextHandler } from "./src/proxy/pazi-context.js";
import { startPaziProxy } from "./src/proxy/pazi-proxy.js";
import { createPaziUploadHandler } from "./src/proxy/pazi-upload.js";

function normalizePluginConfig(
  value: OpenClawPluginApi["pluginConfig"],
): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

async function stopServer(server: HttpServer, logger: OpenClawPluginApi["logger"]) {
  await new Promise<void>((resolve) => {
    server.close((err) => {
      if (err) {
        logger.warn(`pazi proxy shutdown failed: ${String(err)}`);
      }
      resolve();
    });
  });
}

export default {
  id: "pazi",
  name: "Pazi Proxy",
  description: "Routes Anthropic calls through the Pazi API.",
  register(api: OpenClawPluginApi) {
    const defaultAgentId = resolveDefaultAgentId(api.config);
    const resolveWorkspace = (requestedAgentId: unknown) => {
      const requested =
        typeof requestedAgentId === "number" ? String(requestedAgentId) : requestedAgentId;
      const normalized =
        typeof requested === "string" && requested.trim()
          ? normalizeAgentId(requested)
          : defaultAgentId;
      return {
        agentId: normalized,
        workspaceDir: resolveAgentWorkspaceDir(api.config, normalized),
      };
    };

    const pluginConfig = normalizePluginConfig(api.pluginConfig);
    const gatewayAuthToken =
      typeof api.config.gateway?.auth?.token === "string"
        ? api.config.gateway.auth.token
        : undefined;
    const contextHandler = createPaziContextHandler({
      configToken: gatewayAuthToken,
      env: process.env,
      logger: api.logger,
    });

    const uploadHandler = createPaziUploadHandler({
      configToken: gatewayAuthToken,
      env: process.env,
      logger: api.logger,
    });

    api.registerGatewayMethod("pazi.integration.emit", ({ params, respond, context }) => {
      context.broadcast("integration", params);
      respond(true, { emitted: true });
    });
    api.registerGatewayMethod("pazi.files.list", createPaziFilesList(resolveWorkspace));
    api.registerGatewayMethod("pazi.files.get", createPaziFilesGet(resolveWorkspace));
    api.registerGatewayMethod("pazi.files.set", createPaziFilesSet(resolveWorkspace));

    api.registerGatewayMethod(
      "pazi.channels.configure",
      createPaziChannelsConfigureHandler({
        loadConfig: () => api.runtime.config.loadConfig(),
        writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
        probeSlack: (token, timeoutMs) => api.runtime.channel.slack.probeSlack(token, timeoutMs),
        probeTelegram: (token, timeoutMs, proxyUrl) =>
          api.runtime.channel.telegram.probeTelegram(token, timeoutMs, proxyUrl),
      }),
    );
    const gatewayEnv = process.env;
    const pairingGatewayDeps = {
      loadConfig: () => api.runtime.config.loadConfig(),
      env: gatewayEnv,
      logWarn: (message: string) => {
        api.logger.warn(message);
      },
      listRequests: ({
        channel,
        accountId,
        env,
      }: {
        channel: "telegram";
        accountId: string;
        env: NodeJS.ProcessEnv;
      }) => listChannelPairingRequests(channel, env, accountId),
      approveCode: ({
        channel,
        accountId,
        code,
        env,
      }: {
        channel: "telegram";
        accountId: string;
        code: string;
        env: NodeJS.ProcessEnv;
      }) => approveChannelPairingCode({ channel, accountId, code, env }),
      notifyApproved: ({
        channelId,
        id,
        cfg,
      }: {
        channelId: "telegram";
        id: string;
        cfg: Record<string, unknown>;
      }) =>
        notifyPairingApproved({
          channelId,
          id,
          cfg,
        }),
    };
    api.registerGatewayMethod(
      "pazi.channels.pairing.list",
      createPaziChannelsPairingListHandler(pairingGatewayDeps),
    );
    api.registerGatewayMethod(
      "pazi.channels.pairing.approve",
      createPaziChannelsPairingApproveHandler(pairingGatewayDeps),
    );

    const tools = createPipedreamTools({
      pluginConfig,
      config: api.config,
    });
    for (const tool of tools) {
      api.registerTool(tool);
    }

    const browserUseConfig = resolveBrowserUseConfig({
      pluginConfig,
      env: process.env,
    });
    if (browserUseConfig.browserUseEnabled) {
      const browserUseTools = createBrowserUseTools({ pluginConfig });
      for (const tool of browserUseTools) {
        api.registerTool(tool);
      }
    }

    api.registerHttpRoute({
      path: "/pazi/context",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await contextHandler(req, res);
      },
    });

    api.registerHttpRoute({
      path: "/health",
      auth: "gateway",
      handler: (_req, res) => {
        res.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
        });
        res.end(JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }));
      },
    });

    api.registerHttpRoute({
      path: "/status",
      auth: "gateway",
      handler: (_req, res) => {
        const lastActivityAtMs = getProxyLastActivityAt();
        res.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
        });
        res.end(
          JSON.stringify({
            status: "running",
            busy: isProxyBusyForStatus(),
            lastActivityAt:
              lastActivityAtMs === null ? null : new Date(lastActivityAtMs).toISOString(),
            version: process.env.AGENT_VERSION ?? "unknown",
            environment: process.env.NODE_ENV ?? "development",
          }),
        );
      },
    });

    api.registerHttpRoute({
      path: "/pazi/upload",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await uploadHandler(req, res);
      },
    });

    let proxyServer: HttpServer | null = null;

    api.registerService({
      id: "pazi-proxy",
      start: async () => {
        const resolved = resolvePaziBillingConfig({
          pluginConfig,
          env: process.env,
        });
        proxyServer = await startPaziProxy({
          apiUrl: resolved.apiUrl,
          port: resolved.proxyPort,
          logger: api.logger,
        });
      },
      stop: async () => {
        if (!proxyServer) {
          return;
        }
        await stopServer(proxyServer, api.logger);
        proxyServer = null;
      },
    });
  },
};
