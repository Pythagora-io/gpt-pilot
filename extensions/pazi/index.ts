import type { Server as HttpServer } from "node:http";
import path from "node:path";
import { resolveAgentWorkspaceDir, resolveDefaultAgentId } from "openclaw/plugin-sdk/agent-runtime";
import {
  approveChannelPairingCode,
  listChannelPairingRequests,
  notifyPairingApproved,
} from "openclaw/plugin-sdk/channel-pairing";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";
import { normalizeAgentId } from "openclaw/plugin-sdk/routing";
import { probeSlack } from "../slack/runtime-api.js";
import { probeTelegram } from "../telegram/runtime-api.js";
import { trackChannelConnected } from "./src/analytics.js";
import { installBraveEnvDefaults, uninstallBraveEnvDefaults } from "./src/brave/brave-env.js";
import {
  installBraveFetchInterceptor,
  uninstallBraveFetchInterceptor,
} from "./src/brave/brave-fetch-interceptor.js";
import { resolveBrowserUseConfig } from "./src/browser-use/config.js";
import { createBrowserUseTools } from "./src/browser-use/tools.js";
import { createPaziChannelsConfigureHandler } from "./src/channels-configure.js";
import { createPaziChannelsDisconnectHandler } from "./src/channels-disconnect.js";
import {
  createPaziChannelsPairingApproveHandler,
  createPaziChannelsPairingListHandler,
} from "./src/channels-pairing.js";
import { resolvePaziBillingConfig } from "./src/config.js";
import {
  configurePersistencePath,
  configurePersistenceWarnLogger,
  getProxyContext,
  getProxyLastActivityAt,
  isProxyBusyForStatus,
  setProxyContext,
} from "./src/context.js";
import { createCredentialTools } from "./src/credentials/index.js";
import { createPaziCredentialsHandler } from "./src/gateway/pazi-credentials.js";
import {
  createPaziFilesDelete,
  createPaziFilesGet,
  createPaziFilesList,
  createPaziFilesSet,
} from "./src/gateway/pazi-files.js";
import { createPaziMemoryGet } from "./src/gateway/pazi-memory.js";
import {
  createPaziSkillsCapabilities,
  createPaziSkillsGet,
  createPaziSkillsSet,
} from "./src/gateway/pazi-skills.js";
import { createPaziSkillsCreateHandler } from "./src/gateway/skills-create.js";
import { createPaziSkillsDeleteHandler } from "./src/gateway/skills-delete.js";
import {
  createPaziTemplatesInstantiateHandler,
  createPaziTemplatesListHandler,
} from "./src/gateway/templates-instantiate.js";
import { paziBootstrapActionsHook } from "./src/hooks/pazi-bootstrap-actions.js";
import { paziBootstrapUserHook } from "./src/hooks/pazi-bootstrap-user.js";
import { registerBrowserGuardHook } from "./src/hooks/pazi-browser-guard.js";
import { registerBrowserPromptHook } from "./src/hooks/pazi-browser-prompt.js";
import { registerProxyAgentSyncHook } from "./src/hooks/pazi-proxy-agent-sync.js";
import { registerToolResultPersistHook } from "./src/hooks/pazi-tool-result-persist.js";
import { registerTranscriptionBillingHook } from "./src/hooks/pazi-transcription-billing.js";
import { registerWebchatFileSupportHook } from "./src/hooks/pazi-webchat-file-support.js";
import { applyPaziImageConfig } from "./src/image-generation/onboard.js";
import { buildPaziImageGenerationProvider } from "./src/image-generation/provider.js";
import { createPaziBrowserEnabledHandler } from "./src/proxy/pazi-browser-enabled.js";
import { createPaziContextHandler } from "./src/proxy/pazi-context.js";
import { createPaziMigrationNoticeHandler } from "./src/proxy/pazi-migration-notice.js";
import { startPaziProxy } from "./src/proxy/pazi-proxy.js";
import { createPaziUploadHandler } from "./src/proxy/pazi-upload.js";
import { createReactToMessageTool } from "./src/reactions/react-tool.js";
import { createReactionEventHandler } from "./src/reactions/reaction-event.js";
import { startSlackThreadCachePersistence } from "./src/slack-thread-cache-persistence.js";
import { registerSlackThreadReplyMode } from "./src/slack-thread-reply-mode.js";
import { installChannelAuthCrashGuard } from "./src/suppress-channel-auth-crash.js";
import { createUserActionTools } from "./src/user-actions/tools.js";

function normalizePluginConfig(
  value: OpenClawPluginApi["pluginConfig"],
): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value;
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
    // Suppress channel auth errors (e.g. expired Slack tokens) to prevent
    // infinite restart loops — restarting won't fix invalid credentials.
    installChannelAuthCrashGuard(api.logger);

    // PAZ-131: Persist proxy context to disk so it survives gateway restarts
    configurePersistenceWarnLogger((message) => {
      api.logger.warn(message);
    });
    const stateDir = api.runtime.state.resolveStateDir();
    configurePersistencePath(path.join(stateDir, "pazi", "proxy-context.json"));

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
    const browserEnabledHandler = createPaziBrowserEnabledHandler({
      configToken: gatewayAuthToken,
      env: process.env,
      logger: api.logger,
    });

    const migrationNoticeHandler = createPaziMigrationNoticeHandler({
      configToken: gatewayAuthToken,
      env: process.env,
      logger: api.logger,
    });

    const uploadHandler = createPaziUploadHandler({
      configToken: gatewayAuthToken,
      env: process.env,
      logger: api.logger,
    });

    api.registerGatewayMethod("pazi.files.list", createPaziFilesList(resolveWorkspace));
    api.registerGatewayMethod("pazi.files.get", createPaziFilesGet(resolveWorkspace));
    api.registerGatewayMethod("pazi.files.set", createPaziFilesSet(resolveWorkspace));
    api.registerGatewayMethod("pazi.files.delete", createPaziFilesDelete(resolveWorkspace));
    api.registerGatewayMethod("pazi.memory.get", createPaziMemoryGet(resolveWorkspace));
    api.registerGatewayMethod(
      "skills.create",
      createPaziSkillsCreateHandler({
        loadConfig: () => api.runtime.config.loadConfig(),
        resolveWorkspace,
      }),
    );
    api.registerGatewayMethod(
      "skills.delete",
      createPaziSkillsDeleteHandler({
        loadConfig: () => api.runtime.config.loadConfig(),
        writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
        resolveWorkspace,
      }),
    );

    const skillsDeps = {
      resolveWorkspace,
      loadConfig: () => api.runtime.config.loadConfig(),
    };
    api.registerGatewayMethod(
      "pazi.skills.capabilities",
      createPaziSkillsCapabilities({ loadConfig: () => api.runtime.config.loadConfig() }),
    );
    api.registerGatewayMethod("pazi.skills.get", createPaziSkillsGet(skillsDeps));
    api.registerGatewayMethod("pazi.skills.set", createPaziSkillsSet(skillsDeps));

    api.registerGatewayMethod(
      "pazi.templates.instantiate",
      createPaziTemplatesInstantiateHandler({ resolveWorkspace }),
    );
    api.registerGatewayMethod("pazi.templates.list", createPaziTemplatesListHandler());

    api.registerGatewayMethod(
      "pazi.channels.configure",
      createPaziChannelsConfigureHandler({
        loadConfig: () => api.runtime.config.loadConfig(),
        writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
        probeSlack: (token, timeoutMs) => probeSlack(token, timeoutMs),
        probeTelegram: (token, timeoutMs, proxyUrl) => probeTelegram(token, timeoutMs, proxyUrl),
        onConfigured: (result) => {
          void trackChannelConnected(pluginConfig, result.channel, result.accountId);
        },
      }),
    );
    api.registerGatewayMethod(
      "pazi.channels.disconnect",
      createPaziChannelsDisconnectHandler({
        loadConfig: () => api.runtime.config.loadConfig(),
        writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
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

    api.registerHook("agent:bootstrap", paziBootstrapActionsHook, {
      name: "pazi-bootstrap-actions",
      description: "Appends Pazi frontend-action docs to AGENTS.md",
    });

    api.registerHook("agent:bootstrap", paziBootstrapUserHook, {
      name: "pazi-bootstrap-user",
      description: "Injects user name from .pazi/user-meta.json into USER.md bootstrap context",
    });

    // PAZ-211: Redact credential values from persisted tool results
    registerToolResultPersistHook(api);
    registerProxyAgentSyncHook(api);

    // PAZ-280: Inject webchat file download/preview guidance into system prompt
    registerWebchatFileSupportHook(api);

    // PAZ-283: Deduct credits for channel audio transcription
    registerTranscriptionBillingHook(api);

    // PAZ-206: Slack thread reply mode — suppress intermediate messages
    registerSlackThreadReplyMode(api);

    // PAZ-256: Browser permission hooks
    registerBrowserPromptHook(api);
    registerBrowserGuardHook(api);

    const userActionTools = createUserActionTools({
      pluginConfig,
      onBrowserPermissionGranted: async () => {
        const ctx = getProxyContext();
        if (!ctx) {
          return;
        }
        setProxyContext({ ...ctx, browserEnabled: true });
      },
    });
    for (const tool of userActionTools) {
      api.registerTool(tool);
    }

    const credentialTools = createCredentialTools();
    for (const tool of credentialTools) {
      api.registerTool(tool);
    }

    // PAZ-310: Register react_to_message tool
    const reactTool = createReactToMessageTool({ pluginConfig });
    api.registerTool(reactTool);

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

    // PAZ-282: Register Pazi image generation provider
    api.registerImageGenerationProvider(
      buildPaziImageGenerationProvider({ pluginConfig, env: process.env }),
    );

    // PAZ-282: Auto-configure pazi as the default image generation provider
    // if no imageGenerationModel is set yet
    api.registerService({
      id: "pazi-image-generation-onboard",
      start: async () => {
        const currentConfig = api.runtime.config.loadConfig();
        if (!currentConfig.agents?.defaults?.imageGenerationModel) {
          const patched = applyPaziImageConfig(currentConfig);
          await api.runtime.config.writeConfigFile(patched);
          api.logger.info("pazi: auto-configured imageGenerationModel → pazi/gpt-image-1.5");
        }
      },
      stop: async () => {},
    });

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
      path: "/pazi/browser-enabled",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await browserEnabledHandler(req, res);
      },
    });

    api.registerHttpRoute({
      path: "/pazi/migration-notice",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Not Found");
          return;
        }
        await migrationNoticeHandler(req, res);
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

    const credentialsHandler = createPaziCredentialsHandler();
    api.registerHttpRoute({
      path: "/pazi/credentials",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Method Not Allowed");
          return;
        }
        await credentialsHandler(req, res);
      },
    });

    // PAZ-310: HTTP route for reaction events from the Pazi API
    const reactionEventHandler = createReactionEventHandler({
      configToken: gatewayAuthToken,
      logger: api.logger,
    });
    api.registerHttpRoute({
      path: "/pazi/reactions/event",
      auth: "gateway",
      handler: async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Method Not Allowed");
          return;
        }
        await reactionEventHandler(req, res);
      },
    });

    let proxyServer: HttpServer | null = null;
    let stopSlackThreadCachePersistence: (() => Promise<void>) | null = null;

    api.registerService({
      id: "pazi-slack-thread-cache-persistence",
      start: async () => {
        if (stopSlackThreadCachePersistence) {
          await stopSlackThreadCachePersistence();
          stopSlackThreadCachePersistence = null;
        }
        const persistenceStateDir = api.runtime.state.resolveStateDir();
        const manager = await startSlackThreadCachePersistence({
          stateDir: persistenceStateDir,
          logWarn: (message) => api.logger.warn(message),
        });
        stopSlackThreadCachePersistence = manager.stop;
      },
      stop: async () => {
        if (!stopSlackThreadCachePersistence) {
          return;
        }
        await stopSlackThreadCachePersistence();
        stopSlackThreadCachePersistence = null;
      },
    });

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

        // Enable Brave Search proxying through the Pazi backend
        // Only set sentinel + interceptor when apiUrl is configured,
        // so agents without Pazi API URL behave normally.
        if (resolved.apiUrl) {
          installBraveEnvDefaults();
          installBraveFetchInterceptor(resolved.apiUrl);
        }
      },
      stop: async () => {
        uninstallBraveFetchInterceptor();
        uninstallBraveEnvDefaults();

        if (!proxyServer) {
          return;
        }
        await stopServer(proxyServer, api.logger);
        proxyServer = null;
      },
    });
  },
};
