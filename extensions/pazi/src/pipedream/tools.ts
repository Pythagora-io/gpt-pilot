import { Type } from "@sinclair/typebox";
import type { AnyAgentTool, OpenClawConfig } from "openclaw/plugin-sdk";
import { callGateway } from "../../../../src/gateway/call.js";
import {
  checkIntegration,
  listActions,
  getAction,
  configureActionProp,
  reloadActionProps,
  runAction,
  searchApps,
  type PipedreamApiResult,
} from "./api.js";

export type PipedreamToolsDeps = {
  pluginConfig: Record<string, unknown> | null;
  config: OpenClawConfig;
};

type AgentToolResult = {
  content: Array<{ type: "text"; text: string }>;
  details?: unknown;
};

function json(payload: unknown): AgentToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    details: payload,
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
  return trimmed ? trimmed : undefined;
}

function readOptionalNumber(params: Record<string, unknown>, key: string): number | undefined {
  const value = params[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return undefined;
  }
  return value;
}

function coerceLimit(value: number | undefined): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return undefined;
  }
  return Math.floor(value);
}

function unwrapResult(result: PipedreamApiResult<unknown>): AgentToolResult {
  if (result.ok) {
    return json(result.data);
  }
  return json({ error: result.error });
}

type ConfigurableProp = {
  name?: string;
  type?: string;
  label?: string;
  description?: string;
  optional?: boolean;
  hidden?: boolean;
  disabled?: boolean;
  withLabel?: boolean;
  remoteOptions?: boolean;
  useQuery?: boolean;
  reloadProps?: boolean;
};

type ActionSchemaPayload = {
  action?: {
    configurableProps?: ConfigurableProp[];
  };
};

type LabelValueOption = { label: string; value: unknown };

function extractActionProps(payload: unknown): ConfigurableProp[] {
  if (!payload || typeof payload !== "object") {
    return [];
  }
  const data = payload as ActionSchemaPayload;
  const props = data.action?.configurableProps;
  return Array.isArray(props) ? props : [];
}

function isLabelValue(value: unknown): value is { label: string; value: unknown } {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as { label?: unknown; value?: unknown };
  return typeof record.label === "string" && "value" in record;
}

function normalizeOptions(payload: unknown): LabelValueOption[] {
  if (!payload || typeof payload !== "object") {
    return [];
  }
  const record = payload as {
    options?: Array<
      { label?: string; value?: unknown } | { lv?: { label?: string; value?: unknown } }
    >;
    stringOptions?: string[];
  };
  const options: LabelValueOption[] = [];
  if (Array.isArray(record.options)) {
    for (const raw of record.options) {
      if (!raw || typeof raw !== "object") {
        continue;
      }
      if ("lv" in raw && raw.lv && typeof raw.lv === "object") {
        const lv = raw.lv as { label?: string; value?: unknown };
        if (typeof lv.label === "string") {
          options.push({ label: lv.label, value: lv.value });
        }
        continue;
      }
      const direct = raw as { label?: string; value?: unknown };
      if (typeof direct.label === "string") {
        options.push({ label: direct.label, value: direct.value });
      }
    }
  }
  if (Array.isArray(record.stringOptions)) {
    for (const value of record.stringOptions) {
      options.push({ label: value, value });
    }
  }
  return options;
}

function matchesType(value: unknown, propType: string): boolean {
  if (propType === "any" || propType === "object" || propType === "sql") {
    return true;
  }
  if (propType === "string") {
    return typeof value === "string";
  }
  if (propType === "integer") {
    return typeof value === "number" && Number.isInteger(value);
  }
  if (propType === "boolean") {
    return typeof value === "boolean";
  }
  if (propType === "string[]") {
    return Array.isArray(value) && value.every((item) => typeof item === "string");
  }
  if (propType === "integer[]") {
    return Array.isArray(value) && value.every((item) => typeof item === "number");
  }
  return true;
}

async function sleep(ms: number, signal?: AbortSignal): Promise<"ok" | "aborted"> {
  if (signal?.aborted) {
    return "aborted";
  }
  return await new Promise<"ok" | "aborted">((resolve) => {
    const timer = setTimeout(() => {
      resolve("ok");
    }, ms);
    if (!signal) {
      return;
    }
    const onAbort = () => {
      clearTimeout(timer);
      resolve("aborted");
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

export function createPipedreamTools(deps: PipedreamToolsDeps): AnyAgentTool[] {
  return [
    {
      name: "pipedream_find_integrations",
      label: "Pipedream: Find Integrations",
      description:
        "ALWAYS call this FIRST to discover the correct Pipedream app slug. App slugs are often different from expected (e.g. Slack is 'slack_v2', Gmail is 'gmail', etc.). Returns matching apps with their exact slug to use in subsequent calls.",
      parameters: Type.Object(
        {
          query: Type.String({ description: "Search query." }),
          limit: Type.Optional(Type.Number({ description: "Maximum results to return." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const query = readRequiredString(params, "query");
          const limit = coerceLimit(readOptionalNumber(params, "limit"));
          const result = await searchApps({ pluginConfig: deps.pluginConfig }, query, limit);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_list_actions",
      label: "Pipedream: List Actions",
      description:
        "List available actions for a Pipedream app. Returns each action's key (use as actionId), name, description, and a basic configuredProps schema (exact property names and types). For full configurableProps metadata (remote options, withLabel, etc.), call pipedream_get_action.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          limit: Type.Optional(Type.Number({ description: "Maximum results to return." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const limit = coerceLimit(readOptionalNumber(params, "limit"));
          const result = await listActions({ pluginConfig: deps.pluginConfig }, app, limit);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_get_action",
      label: "Pipedream: Get Action Schema",
      description:
        "Fetch the full configurableProps schema for a specific action. Use this to see required props, remoteOptions, withLabel, and other metadata before calling pipedream_use_integration.",
      parameters: Type.Object(
        {
          actionId: Type.String({
            description: "Action key from pipedream_list_actions (e.g. 'slack_v2-send-message').",
          }),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const actionId = readRequiredString(params, "actionId");
          const result = await getAction({ pluginConfig: deps.pluginConfig }, actionId);
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_configure_prop",
      label: "Pipedream: Configure Prop",
      description:
        "Fetch remote options (label/value) for a configurable prop, or validate dynamic props. Use this for props marked remoteOptions/withLabel or when you need to map a human name to an ID.",
      parameters: Type.Object(
        {
          actionId: Type.String({
            description: "Action key from pipedream_list_actions.",
          }),
          propName: Type.String({
            description: "Configurable prop name from pipedream_get_action.",
          }),
          configuredProps: Type.Optional(
            Type.Record(Type.String(), Type.Unknown(), {
              description:
                "Current configuredProps values (excluding auth). Used to resolve dependent props.",
            }),
          ),
          query: Type.Optional(
            Type.String({
              description: "Optional search query for filtering options (if supported).",
            }),
          ),
          page: Type.Optional(Type.Number({ description: "Optional page for pagination." })),
          prevContext: Type.Optional(
            Type.Record(Type.String(), Type.Unknown(), {
              description: "Optional context from a previous configureProp call.",
            }),
          ),
          dynamicPropsId: Type.Optional(
            Type.String({
              description: "Optional dynamicPropsId when props are generated dynamically.",
            }),
          ),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const actionId = readRequiredString(params, "actionId");
          const propName = readRequiredString(params, "propName");
          const configuredProps = params.configuredProps;
          if (
            configuredProps !== undefined &&
            (typeof configuredProps !== "object" ||
              configuredProps === null ||
              Array.isArray(configuredProps))
          ) {
            throw new Error("configuredProps must be an object");
          }
          const query = readOptionalString(params, "query");
          const page = readOptionalNumber(params, "page");
          const prevContext = params.prevContext;
          if (
            prevContext !== undefined &&
            (typeof prevContext !== "object" || prevContext === null || Array.isArray(prevContext))
          ) {
            throw new Error("prevContext must be an object");
          }
          const dynamicPropsId = readOptionalString(params, "dynamicPropsId");

          const result = await configureActionProp({ pluginConfig: deps.pluginConfig }, actionId, {
            propName,
            configuredProps: configuredProps as Record<string, unknown> | undefined,
            query: query ?? undefined,
            page: page ?? undefined,
            prevContext: prevContext as Record<string, unknown> | undefined,
            dynamicPropsId,
          });
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_reload_props",
      label: "Pipedream: Reload Props",
      description:
        "Reload dynamic props after setting dependent values (when a prop has reloadProps=true).",
      parameters: Type.Object(
        {
          actionId: Type.String({ description: "Action key from pipedream_list_actions." }),
          configuredProps: Type.Optional(
            Type.Record(Type.String(), Type.Unknown(), {
              description: "Current configuredProps values (excluding auth).",
            }),
          ),
          dynamicPropsId: Type.Optional(Type.String({ description: "Dynamic props ID." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const actionId = readRequiredString(params, "actionId");
          const configuredProps = params.configuredProps;
          if (
            configuredProps !== undefined &&
            (typeof configuredProps !== "object" ||
              configuredProps === null ||
              Array.isArray(configuredProps))
          ) {
            throw new Error("configuredProps must be an object");
          }
          const dynamicPropsId = readOptionalString(params, "dynamicPropsId");

          const result = await reloadActionProps({ pluginConfig: deps.pluginConfig }, actionId, {
            configuredProps: configuredProps as Record<string, unknown> | undefined,
            dynamicPropsId: dynamicPropsId ?? undefined,
          });
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_check_integration",
      label: "Pipedream: Check Integration",
      description:
        "Check whether a Pipedream app is connected. Use the exact app slug from pipedream_find_integrations. Returns {connected: true, accountId} if connected.",
      parameters: Type.Object(
        {
          app: Type.String({
            description:
              "Pipedream app slug from pipedream_find_integrations (e.g. 'slack_v2', not 'slack').",
          }),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const result = await checkIntegration({ pluginConfig: deps.pluginConfig }, app);
          if (result.ok) {
            const data =
              result.data && typeof result.data === "object"
                ? (result.data as { connected?: unknown })
                : undefined;
            if (data?.connected !== true) {
              return json({
                ...data,
                hint: `App "${app}" is not connected. Did you use the correct slug? Call pipedream_find_integrations to discover the exact Pipedream slug (e.g. Slack is "slack_v2", not "slack").`,
              });
            }
          }
          return unwrapResult(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_use_integration",
      label: "Pipedream: Use Integration",
      description:
        "Run a Pipedream action. IMPORTANT: Use pipedream_list_actions to discover actionId and pipedream_get_action to fetch the full configurableProps schema. This tool validates your configuredProps and will reject calls with missing/unknown props. Do NOT guess property names — use the schema. Do NOT include auth/app props — authentication is automatic. For props with remoteOptions/withLabel, use pipedream_configure_prop to fetch options.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          actionId: Type.String({
            description: "Action key from pipedream_list_actions (e.g. 'slack_v2-send-message').",
          }),
          configuredProps: Type.Optional(
            Type.Record(Type.String(), Type.Unknown(), {
              description:
                "Action properties. Keys and types MUST match the configurableProps schema returned by pipedream_get_action.",
            }),
          ),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const actionId = readRequiredString(params, "actionId");
          const configuredProps = params.configuredProps;
          if (
            configuredProps !== undefined &&
            (typeof configuredProps !== "object" ||
              configuredProps === null ||
              Array.isArray(configuredProps))
          ) {
            throw new Error("configuredProps must be an object");
          }
          const props = (configuredProps as Record<string, unknown> | undefined) ?? {};
          const resolvedProps: Record<string, unknown> = { ...props };

          // Validate configuredProps against full action schema
          const actionResult = await getAction({ pluginConfig: deps.pluginConfig }, actionId);
          if (!actionResult.ok) {
            return json({
              error: actionResult.error,
              hint: "Failed to fetch action schema. Try pipedream_get_action again before calling pipedream_use_integration.",
            });
          }

          const actionProps = extractActionProps(actionResult.data);
          const authPropNames = actionProps
            .filter((p) => p.type === "app" && typeof p.name === "string")
            .map((p) => p.name as string);

          const expectedProps = actionProps.filter((p) => {
            if (!p.name || typeof p.name !== "string") {
              return false;
            }
            if (p.type === "app") {
              return false;
            }
            if (p.hidden === true || p.disabled === true) {
              return false;
            }
            return true;
          });

          const tryResolveValue = async (
            prop: ConfigurableProp,
            value: unknown,
          ): Promise<
            { ok: true; value: unknown } | { ok: false; error: string; options?: string[] }
          > => {
            if (!prop.name || typeof prop.name !== "string") {
              return { ok: true, value };
            }
            if (isLabelValue(value)) {
              return { ok: true, value };
            }
            if (Array.isArray(value)) {
              const resolvedValues: unknown[] = [];
              for (const item of value) {
                if (isLabelValue(item)) {
                  resolvedValues.push(item);
                  continue;
                }
                if (typeof item !== "string") {
                  return {
                    ok: false,
                    error: `Prop "${prop.name}" expects label/value objects; got non-string array item.`,
                  };
                }
                const lookup = await configureActionProp(
                  { pluginConfig: deps.pluginConfig },
                  actionId,
                  {
                    propName: prop.name,
                    configuredProps: resolvedProps,
                    query: prop.useQuery ? item : undefined,
                  },
                );
                if (!lookup.ok) {
                  return { ok: false, error: lookup.error };
                }
                const options = normalizeOptions(lookup.data);
                const match = options.filter(
                  (opt) =>
                    opt.label.toLowerCase() === item.toLowerCase() ||
                    String(opt.value ?? "").toLowerCase() === item.toLowerCase(),
                );
                if (match.length !== 1) {
                  return {
                    ok: false,
                    error:
                      match.length === 0
                        ? `No option found for "${item}" in prop "${prop.name}".`
                        : `Multiple options found for "${item}" in prop "${prop.name}".`,
                    options: options.slice(0, 5).map((opt) => opt.label),
                  };
                }
                const selected = match[0];
                const selectedValue = selected.value ?? selected.label;
                const resolved = prop.withLabel
                  ? { label: selected.label, value: selectedValue }
                  : selectedValue;
                resolvedValues.push(resolved);
              }
              return { ok: true, value: resolvedValues };
            }
            if (typeof value !== "string") {
              return { ok: true, value };
            }

            const lookup = await configureActionProp(
              { pluginConfig: deps.pluginConfig },
              actionId,
              {
                propName: prop.name,
                configuredProps: resolvedProps,
                query: prop.useQuery ? value : undefined,
              },
            );
            if (!lookup.ok) {
              return { ok: false, error: lookup.error };
            }
            const options = normalizeOptions(lookup.data);
            const match = options.filter(
              (opt) =>
                opt.label.toLowerCase() === value.toLowerCase() ||
                String(opt.value ?? "").toLowerCase() === value.toLowerCase(),
            );
            if (match.length !== 1) {
              return {
                ok: false,
                error:
                  match.length === 0
                    ? `No option found for "${value}" in prop "${prop.name}".`
                    : `Multiple options found for "${value}" in prop "${prop.name}".`,
                options: options.slice(0, 5).map((opt) => opt.label),
              };
            }
            const selected = match[0];
            const selectedValue = selected.value ?? selected.label;
            const resolved = prop.withLabel
              ? { label: selected.label, value: selectedValue }
              : selectedValue;
            return { ok: true, value: resolved };
          };

          // Auto-resolve remote options when needed
          const resolutionErrors: Array<{ prop: string; error: string; options?: string[] }> = [];
          for (const prop of expectedProps) {
            if (!prop.name || typeof prop.name !== "string") {
              continue;
            }
            if (!(prop.name in resolvedProps)) {
              continue;
            }
            const value = resolvedProps[prop.name];
            if (value === undefined || value === null) {
              continue;
            }

            const needsRemote =
              prop.remoteOptions === true || prop.useQuery === true || prop.withLabel === true;
            const needsLabel =
              prop.withLabel === true &&
              !(isLabelValue(value) || (Array.isArray(value) && value.every(isLabelValue)));

            if (needsRemote || needsLabel) {
              const resolved = await tryResolveValue(prop, value);
              if (!resolved.ok) {
                resolutionErrors.push({
                  prop: prop.name,
                  error: resolved.error,
                  options: resolved.options,
                });
              } else {
                resolvedProps[prop.name] = resolved.value;
              }
            }
          }

          if (resolutionErrors.length > 0) {
            return json({
              error: "Unable to resolve remote options for one or more props.",
              details: resolutionErrors,
              hint: "Call pipedream_configure_prop to fetch options and pass { label, value } for withLabel props.",
            });
          }

          const expectedNames = new Set(
            expectedProps.map((p) => (typeof p.name === "string" ? p.name : "")).filter(Boolean),
          );
          const requiredProps = expectedProps.filter((p) => p.optional !== true);
          const providedNames = new Set(
            Object.entries(resolvedProps)
              .filter(([_, value]) => value !== undefined && value !== null)
              .map(([name]) => name),
          );
          for (const authName of authPropNames) {
            providedNames.delete(authName);
          }

          const missingRequired = requiredProps
            .filter((p) => p.name && !providedNames.has(p.name))
            .map((p) => p.name);
          const unrecognized = [...providedNames].filter((n) => !expectedNames.has(n));

          const typeErrors = expectedProps
            .filter((p) => p.name && providedNames.has(p.name))
            .map((p) => {
              const value = resolvedProps[p.name as string];
              if (
                p.withLabel &&
                (isLabelValue(value) || (Array.isArray(value) && value.every(isLabelValue)))
              ) {
                return null;
              }
              if (!p.type) {
                return null;
              }
              if (!matchesType(value, p.type)) {
                return { name: p.name, expectedType: p.type };
              }
              return null;
            })
            .filter(Boolean);

          if (missingRequired.length > 0 || unrecognized.length > 0 || typeErrors.length > 0) {
            return json({
              error: "Invalid configuredProps.",
              missingRequired: missingRequired.length > 0 ? missingRequired : undefined,
              unrecognized: unrecognized.length > 0 ? unrecognized : undefined,
              typeErrors: typeErrors.length > 0 ? typeErrors : undefined,
              expectedProps: expectedProps.map((p) => ({
                name: p.name,
                type: p.type,
                description: p.description ?? p.label,
                required: p.optional !== true,
                remoteOptions: p.remoteOptions === true ? true : undefined,
                withLabel: p.withLabel === true ? true : undefined,
                useQuery: p.useQuery === true ? true : undefined,
              })),
              hint: "Use the exact property names and types from the expectedProps list above. For remote options, call pipedream_configure_prop to get label/value entries.",
            });
          }

          const authPropProvided = authPropNames.filter((name) =>
            Object.prototype.hasOwnProperty.call(resolvedProps, name),
          );
          if (authPropProvided.length > 0) {
            return json({
              error: "Do not include auth/app props in configuredProps.",
              authProps: authPropProvided,
              hint: "Remove auth props; authentication is added automatically.",
            });
          }

          const result = await runAction(
            { pluginConfig: deps.pluginConfig },
            app,
            actionId,
            Object.keys(resolvedProps).length > 0 ? resolvedProps : undefined,
          );
          if (result.ok) {
            return json({
              ...(result.data as Record<string, unknown>),
              _request: { app, actionId, configuredProps: resolvedProps },
              note:
                (result.data as { result?: unknown })?.result === null
                  ? "Action returned null result. This can be normal, but verify the message was delivered."
                  : undefined,
            });
          }
          return json({
            error: result.error,
            _request: { app, actionId, configuredProps: resolvedProps },
          });
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_request_integration",
      label: "Pipedream: Request Integration",
      description:
        "Prompt the user's UI to connect a Pipedream integration. Only use this AFTER check_integration returns connected=false. This opens an OAuth dialog in the frontend.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          message: Type.Optional(Type.String({ description: "Optional message to display." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>) {
        try {
          const app = readRequiredString(params, "app");
          const message = readOptionalString(params, "message");
          const result = await callGateway({
            method: "pazi.integration.emit",
            params: { action: "required", app, message },
            config: deps.config,
          });
          return json(result);
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    {
      name: "pipedream_wait_for_connection",
      label: "Pipedream: Wait For Connection",
      description:
        "Poll until a Pipedream integration is connected. Use after request_integration to wait for the user to complete the OAuth flow.",
      parameters: Type.Object(
        {
          app: Type.String({ description: "Pipedream app slug." }),
          timeoutMs: Type.Optional(
            Type.Number({ description: "Total time to wait before timing out." }),
          ),
          pollIntervalMs: Type.Optional(Type.Number({ description: "Delay between polls." })),
        },
        { additionalProperties: false },
      ),
      async execute(_toolCallId: string, params: Record<string, unknown>, signal?: AbortSignal) {
        try {
          const app = readRequiredString(params, "app");
          const timeoutMs = readOptionalNumber(params, "timeoutMs");
          const pollIntervalMs = readOptionalNumber(params, "pollIntervalMs");
          const resolvedTimeoutMs =
            typeof timeoutMs === "number" && timeoutMs > 0 ? timeoutMs : 120_000;
          const resolvedPollMs =
            typeof pollIntervalMs === "number" && pollIntervalMs > 0 ? pollIntervalMs : 3_000;
          const deadline = Date.now() + resolvedTimeoutMs;

          while (true) {
            if (signal?.aborted) {
              return json({ status: "aborted" });
            }

            const result = await checkIntegration({ pluginConfig: deps.pluginConfig }, app);
            if (!result.ok) {
              return json({ error: result.error });
            }

            const payload =
              result.data && typeof result.data === "object"
                ? (result.data as { connected?: unknown; accountId?: unknown })
                : undefined;
            if (payload?.connected === true) {
              const accountId =
                typeof payload.accountId === "string" ? payload.accountId : undefined;
              return json({ status: "connected", accountId });
            }

            const now = Date.now();
            if (now >= deadline) {
              return json({ status: "timeout" });
            }

            const waitMs = Math.min(resolvedPollMs, deadline - now);
            const slept = await sleep(waitMs, signal);
            if (slept === "aborted") {
              return json({ status: "aborted" });
            }
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
  ];
}
