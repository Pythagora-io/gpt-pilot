import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { extname, join } from "node:path";
import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk";
import {
  createSession,
  getSessionStatus,
  getSnapshot,
  getScreenshot,
  getTaskStatus,
  runTask,
  stopSession,
} from "./api.js";
import { resolveBrowserUseConfig } from "./config.js";

const BROWSER_USE_ACTIONS = [
  "run",
  "session_create",
  "session_stop",
  "snapshot",
  "screenshot",
  "status",
] as const;

type BrowserUseAction = (typeof BROWSER_USE_ACTIONS)[number];

type AgentToolResult = {
  content: Array<{ type: "text"; text: string }>;
  details?: unknown;
};

export type BrowserUseToolsDeps = {
  pluginConfig: Record<string, unknown> | null;
};

function stringEnum<T extends readonly string[]>(
  values: T,
  options: { description?: string } = {},
) {
  return Type.Unsafe<T[number]>({
    type: "string",
    enum: [...values],
    ...options,
  });
}

function json(payload: unknown, summary?: string): AgentToolResult {
  const details = payload as Record<string, unknown>;
  const text = summary
    ? `${summary}\n\n${JSON.stringify(payload, null, 2)}`
    : JSON.stringify(payload, null, 2);
  return {
    content: [{ type: "text", text }],
    details,
  };
}

function readRequiredString(params: Record<string, unknown>, key: string): string {
  const value = params[key];
  if (typeof value !== "string") {
    throw new Error(`${key} required`);
  }
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${key} required`);
  }
  return trimmed;
}

function readOptionalString(params: Record<string, unknown>, key: string): string | undefined {
  const value = params[key];
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function fileExtensionFromContentType(contentType: string | null): string | undefined {
  if (!contentType) {
    return undefined;
  }
  const normalized = contentType.toLowerCase();
  if (normalized.includes("image/png")) {
    return ".png";
  }
  if (normalized.includes("image/jpeg") || normalized.includes("image/jpg")) {
    return ".jpg";
  }
  if (normalized.includes("image/webp")) {
    return ".webp";
  }
  return undefined;
}

function extensionFromUrl(rawUrl: string): string | undefined {
  try {
    const parsed = new URL(rawUrl);
    const extension = extname(parsed.pathname).trim().toLowerCase();
    if (!extension) {
      return undefined;
    }
    if (extension.length > 10) {
      return undefined;
    }
    return extension;
  } catch {
    return undefined;
  }
}

function withTimeoutSignal(
  timeoutMs: number,
  signal?: AbortSignal,
): {
  signal: AbortSignal;
  cleanup: () => void;
} {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  const onAbort = () => {
    controller.abort();
  };

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", onAbort, { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timer);
      if (signal) {
        signal.removeEventListener("abort", onAbort);
      }
    },
  };
}

async function downloadScreenshot(params: {
  url: string;
  timeoutMs: number;
  signal?: AbortSignal;
}): Promise<{ path: string; bytes: number; mimeType?: string }> {
  const timeout = withTimeoutSignal(params.timeoutMs, params.signal);

  try {
    const res = await fetch(params.url, {
      method: "GET",
      signal: timeout.signal,
    });

    if (!res.ok) {
      const statusText = res.statusText || "request_failed";
      throw new Error(`Screenshot download failed (${String(res.status)}): ${statusText}`);
    }

    const bytes = Buffer.from(await res.arrayBuffer());
    const extension =
      fileExtensionFromContentType(res.headers.get("content-type")) ??
      extensionFromUrl(params.url) ??
      ".png";

    const dir = await mkdtemp(join(tmpdir(), "openclaw-browser-use-"));
    const path = join(dir, `screenshot${extension}`);
    await writeFile(path, bytes);

    return {
      path,
      bytes: bytes.byteLength,
      mimeType: res.headers.get("content-type") ?? undefined,
    };
  } finally {
    timeout.cleanup();
  }
}

function buildStatusHint(action: BrowserUseAction): string {
  if (action === "run") {
    return "Task started. Poll with action=status and taskId until status is completed or failed.";
  }
  if (action === "session_create") {
    return "Session created. Use snapshot/screenshot/status/session_stop with this sessionId.";
  }
  return "";
}

export function createBrowserUseTools(deps: BrowserUseToolsDeps): AnyAgentTool[] {
  return [
    {
      name: "browser_use",
      label: "Browser Use",
      description:
        "Stealth cloud browser automation via Pazi Browser Use API. Supports async run tasks and direct session controls.",
      parameters: Type.Object(
        {
          action: stringEnum(BROWSER_USE_ACTIONS, {
            description: `Action to perform: ${BROWSER_USE_ACTIONS.join(", ")}`,
          }),
          task: Type.Optional(
            Type.String({
              description: "Natural language browsing task for action=run.",
            }),
          ),
          taskId: Type.Optional(Type.String({ description: "Task ID for action=status." })),
          sessionId: Type.Optional(
            Type.String({
              description:
                "Session ID for session_stop, snapshot, screenshot, or session status checks.",
            }),
          ),
          url: Type.Optional(
            Type.String({
              description: "Optional starting URL used when creating a new session.",
            }),
          ),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>, signal?: AbortSignal) {
        try {
          const actionRaw = params.action;
          const action =
            typeof actionRaw === "string" ? (actionRaw.trim() as BrowserUseAction) : undefined;
          if (!action) {
            throw new Error("action required");
          }

          switch (action) {
            case "run": {
              const task = readRequiredString(params, "task");
              const sessionId = readOptionalString(params, "sessionId");
              const result = await runTask(
                {
                  pluginConfig: deps.pluginConfig,
                  body: {
                    task,
                    ...(sessionId ? { sessionId } : {}),
                  },
                },
                signal,
              );
              if (!result.ok) {
                return json({ error: result.error });
              }

              return json(
                {
                  status: typeof result.data.status === "string" ? result.data.status : "running",
                  taskId: result.data.taskId,
                  liveUrl: result.data.liveUrl,
                  hint: buildStatusHint(action),
                },
                "Browser Use task started.",
              );
            }

            case "session_create": {
              const startUrl = readOptionalString(params, "url");
              const result = await createSession(
                {
                  pluginConfig: deps.pluginConfig,
                  body: startUrl ? { url: startUrl } : undefined,
                },
                signal,
              );
              if (!result.ok) {
                return json({ error: result.error });
              }

              return json(
                {
                  sessionId: result.data.sessionId,
                  liveUrl: result.data.liveUrl,
                  status: result.data.status,
                  hint: buildStatusHint(action),
                },
                "Browser Use session created.",
              );
            }

            case "session_stop": {
              const sessionId = readRequiredString(params, "sessionId");
              const result = await stopSession(
                { pluginConfig: deps.pluginConfig, sessionId },
                signal,
              );
              if (!result.ok) {
                return json({ error: result.error });
              }
              return json({ sessionId, ...result.data }, "Browser Use session stopped.");
            }

            case "snapshot": {
              const sessionId = readRequiredString(params, "sessionId");
              const result = await getSnapshot(
                { pluginConfig: deps.pluginConfig, sessionId },
                signal,
              );
              if (!result.ok) {
                return json({ error: result.error });
              }
              if (typeof result.data.text !== "string") {
                return json({ error: "Snapshot response missing text" });
              }
              return {
                content: [{ type: "text", text: result.data.text }],
                details: {
                  sessionId,
                  text: result.data.text,
                },
              };
            }

            case "screenshot": {
              const sessionId = readRequiredString(params, "sessionId");
              const screenshot = await getScreenshot(
                { pluginConfig: deps.pluginConfig, sessionId },
                signal,
              );
              if (!screenshot.ok) {
                return json({ error: screenshot.error });
              }

              const screenshotUrl =
                typeof screenshot.data.url === "string" ? screenshot.data.url.trim() : "";
              if (!screenshotUrl) {
                return json({ error: "Screenshot response missing URL" });
              }

              const resolvedCfg = resolveBrowserUseConfig({
                pluginConfig: deps.pluginConfig,
                env: process.env,
              });

              const downloaded = await downloadScreenshot({
                url: screenshotUrl,
                timeoutMs: resolvedCfg.browserUseTimeoutMs,
                signal,
              });

              return {
                content: [{ type: "text", text: `FILE:${downloaded.path}` }],
                details: {
                  sessionId,
                  url: screenshotUrl,
                  path: downloaded.path,
                  bytes: downloaded.bytes,
                  mimeType: downloaded.mimeType,
                  imagePaths: [downloaded.path],
                },
              };
            }

            case "status": {
              const taskId = readOptionalString(params, "taskId");
              const sessionId = readOptionalString(params, "sessionId");

              if (!taskId && !sessionId) {
                throw new Error("taskId or sessionId required");
              }
              if (taskId && sessionId) {
                throw new Error("Provide either taskId or sessionId, not both");
              }

              if (taskId) {
                const result = await getTaskStatus(
                  { pluginConfig: deps.pluginConfig, taskId },
                  signal,
                );
                if (!result.ok) {
                  return json({ error: result.error });
                }

                return json({ taskId, ...result.data }, "Browser Use task status.");
              }

              const sessionResult = await getSessionStatus(
                {
                  pluginConfig: deps.pluginConfig,
                  sessionId: sessionId as string,
                },
                signal,
              );
              if (!sessionResult.ok) {
                return json({ error: sessionResult.error });
              }

              return json({ sessionId, ...sessionResult.data }, "Browser Use session status.");
            }

            default: {
              action satisfies never;
              return json({ error: `Unsupported action: ${String(action)}` });
            }
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
  ];
}
