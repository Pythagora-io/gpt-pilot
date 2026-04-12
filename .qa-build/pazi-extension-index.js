import { s as registerUnhandledRejectionHandler } from "../../unhandled-rejections-DL_irKW3.js";
import { c as saveAuthProfileStore, o as loadAuthProfileStoreForSecretsRuntime } from "../../store-DFKwcYXy.js";
import { c as normalizeAgentId } from "../../session-key-BMb3Kc4r.js";
import { m as resolveDefaultAgentId, p as resolveAgentWorkspaceDir, r as listAgentIds } from "../../agent-scope-z2S0aNZ_.js";
import { c as getPluginRuntimeGatewayRequestScope } from "../../types-Dh9bpXUJ.js";
import { a as isAgentBootstrapEvent, f as registerInternalHook, u as isMessageTranscribedEvent } from "../../internal-hooks-Bp9IGDlL.js";
import { t as loadJsonFile } from "../../json-file-C2pF_Wpf.js";
import { o as upsertAuthProfileWithLock } from "../../profiles-CNZnsvO8.js";
import { r as writeJsonAtomic, t as createAsyncLock } from "../../json-files-Cdwkkcv7.js";
import { dn as errorShape, un as ErrorCodes } from "../../method-scopes-DjaSV7lS.js";
import { c as readFileWithinRoot, m as writeFileWithinRoot, t as SafeOpenError } from "../../fs-safe-CCk9eQhk.js";
import { r as enqueueSystemEvent } from "../../system-events-B2OAV8S3.js";
import "../../json-store-CziE4aLD.js";
import { s as loadWorkspaceSkillEntries } from "../../skills-DkY7RyO1.js";
import "../../routing-DwGd5esU.js";
import { i as listChannelPairingRequests, m as notifyPairingApproved, n as approveChannelPairingCode } from "../../pairing-store-BG4n5RgS.js";
import "../../channel-pairing-CXPzZYnT.js";
import "../../runtime-env-C2i0QDTp.js";
import "../../infra-runtime-B76RzoP2.js";
import { t as buildWorkspaceSkillStatus } from "../../skills-status-CaG30bJX.js";
import "../../agent-runtime-2PslNgLf.js";
import "../../plugin-runtime-CxErs-XO.js";
import "../../gateway-runtime-B1IH8imd.js";
import "../../hook-runtime-CK67_kX7.js";
import { i as hydrateSlackThreadParticipationCache, n as getSlackThreadParticipationEntriesSnapshot } from "../../sent-thread-cache-CTFN2jX4.js";
import { t as sendMessageSlack } from "../../send-3gfo4OPL.js";
import { t as probeSlack } from "../../probe-XAPUTMaf.js";
import "../../runtime-api-C9fE9_Ma.js";
import { t as probeTelegram } from "../../probe-VsytIb-b.js";
import "../../runtime-api-veR3n7NW.js";
import { fileURLToPath } from "node:url";
import fs, { existsSync } from "node:fs";
import path, { basename, extname, join } from "node:path";
import { exec } from "node:child_process";
import { homedir, tmpdir } from "node:os";
import fs$1, { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { Type } from "@sinclair/typebox";
import http from "node:http";
import https from "node:https";
//#region extensions/pazi/src/config.ts
const DEFAULT_PROXY_PORT = 8765;
function normalizeString$1(value) {
	if (typeof value !== "string") return;
	const trimmed = value.trim();
	return trimmed.length > 0 ? trimmed : void 0;
}
function normalizePort(value) {
	if (typeof value === "number" && Number.isFinite(value) && value > 0) return Math.floor(value);
	if (typeof value === "string" && value.trim().length > 0) {
		const parsed = Number.parseInt(value, 10);
		if (Number.isFinite(parsed) && parsed > 0) return parsed;
	}
}
function resolvePaziBillingConfig(params) {
	const env = params.env ?? process.env;
	const raw = params.pluginConfig ?? {};
	return {
		apiUrl: normalizeString$1(raw.apiUrl) ?? normalizeString$1(env.PAZI_API_URL),
		proxyPort: normalizePort(raw.proxyPort) ?? normalizePort(env.PAZI_PROXY_PORT) ?? DEFAULT_PROXY_PORT
	};
}
function resolveGatewayToken(params) {
	const configToken = normalizeString$1(params.configToken);
	if (configToken) return configToken;
	return normalizeString$1((params.env ?? process.env).OPENCLAW_GATEWAY_TOKEN);
}
//#endregion
//#region extensions/pazi/src/context.ts
const STALE_BUSY_AFTER_MS = 1200 * 1e3;
let currentContext = null;
let lastProxyActivityAtMs = null;
let persistencePath = null;
let diskLoaded = false;
let persistenceWarnLogger = null;
let useDirectWrite = false;
function warnPersistence(message, err) {
	const formatErr = err instanceof Error ? err.message : String(err);
	const text = `pazi proxy context persistence: ${message}${err === void 0 ? "" : ` (${formatErr})`}`;
	if (persistenceWarnLogger) {
		persistenceWarnLogger(text);
		return;
	}
	console.warn(text);
}
function isEperm(err) {
	return typeof err === "object" && err !== null && "code" in err && err.code === "EPERM";
}
/**
* Configure the file path for persisting proxy context.
* Called once from the pazi plugin's register() function.
* Must be called before any get/set operations for persistence to work.
*/
function configurePersistencePath(filePath) {
	const normalized = filePath.trim();
	if (!normalized) {
		persistencePath = null;
		diskLoaded = false;
		useDirectWrite = false;
		warnPersistence("disabled because configured path was empty");
		return;
	}
	persistencePath = normalized;
	diskLoaded = false;
	useDirectWrite = false;
}
/**
* Configure warning logger used for persistence failures.
* Called from plugin register() to route warnings to gateway logger.
*/
function configurePersistenceWarnLogger(logger) {
	persistenceWarnLogger = logger;
}
/**
* Validate that a parsed JSON value is a valid ProxyContext.
* All fields must be non-empty strings.
*/
function isValidProxyContext(value) {
	if (!value || typeof value !== "object") return false;
	const obj = value;
	return typeof obj.userId === "string" && typeof obj.agentId === "string" && typeof obj.proxyToken === "string" && obj.userId.length > 0 && obj.agentId.length > 0 && obj.proxyToken.length > 0 && (obj.dashboardBaseUrl === void 0 || typeof obj.dashboardBaseUrl === "string");
}
/**
* Get the current proxy context. Returns the in-memory cached value if set.
* On first call after startup (when in-memory is null), lazy-loads from disk.
*/
function getProxyContext() {
	if (currentContext) return currentContext;
	if (!diskLoaded && persistencePath) {
		diskLoaded = true;
		try {
			const loaded = loadJsonFile(persistencePath);
			if (isValidProxyContext(loaded)) currentContext = loaded;
			else if (loaded !== void 0 && loaded !== null) warnPersistence(`ignored invalid persisted context at ${persistencePath}`);
		} catch (err) {
			warnPersistence(`failed to load persisted context from ${persistencePath}`, err);
		}
	}
	return currentContext;
}
/**
* Set the proxy context. Updates both in-memory cache and disk persistence.
* Disk write is best-effort — failures are silently caught.
*/
/**
* Check if browser access is enabled for the current workspace.
* Returns false if context is missing or browserEnabled is not explicitly true.
*/
function isBrowserEnabled() {
	return getProxyContext()?.browserEnabled === true;
}
function setProxyContext(ctx) {
	currentContext = ctx;
	diskLoaded = true;
	persistToDisk(ctx);
}
/**
* Best-effort persist context to disk.
* Primary path: atomic write-then-rename (safe against kill mid-write).
* Fallback: direct write when rename fails with EPERM (overlay filesystem).
*/
function persistToDisk(ctx) {
	if (!persistencePath) return;
	const data = JSON.stringify(ctx, null, 2) + "\n";
	if (useDirectWrite) {
		try {
			const dir = path.dirname(persistencePath);
			fs.mkdirSync(dir, {
				recursive: true,
				mode: 448
			});
			fs.writeFileSync(persistencePath, data, "utf8");
			fs.chmodSync(persistencePath, 384);
		} catch (err) {
			warnPersistence(`failed to persist context to ${persistencePath}`, err);
		}
		return;
	}
	const tmpPath = `${persistencePath}.${process.pid}.tmp`;
	try {
		const dir = path.dirname(persistencePath);
		fs.mkdirSync(dir, {
			recursive: true,
			mode: 448
		});
		fs.writeFileSync(tmpPath, data, "utf8");
		fs.chmodSync(tmpPath, 384);
		try {
			fs.renameSync(tmpPath, persistencePath);
		} catch (renameErr) {
			try {
				fs.rmSync(tmpPath, { force: true });
			} catch {}
			if (!isEperm(renameErr)) throw renameErr;
			useDirectWrite = true;
			warnPersistence(`rename failed with EPERM for ${persistencePath}; falling back to direct writes`, renameErr);
			fs.writeFileSync(persistencePath, data, "utf8");
			fs.chmodSync(persistencePath, 384);
		}
	} catch (err) {
		warnPersistence(`failed to persist context to ${persistencePath}`, err);
	}
}
function markProxyActivity(atMs = Date.now()) {
	lastProxyActivityAtMs = atMs;
}
function getProxyLastActivityAt() {
	return lastProxyActivityAtMs;
}
function isProxyBusyForStatus(nowMs = Date.now()) {
	if (!currentContext || lastProxyActivityAtMs === null) return false;
	return nowMs - lastProxyActivityAtMs <= STALE_BUSY_AFTER_MS;
}
//#endregion
//#region extensions/pazi/src/analytics.ts
async function trackChannelConnected(pluginConfig, channelType, accountId) {
	try {
		const context = getProxyContext();
		if (!context) return;
		const apiUrl = resolvePaziBillingConfig({
			pluginConfig,
			env: process.env
		}).apiUrl?.trim();
		if (!apiUrl) return;
		const url = new URL("/analytics/channel-connected", apiUrl);
		await fetch(url, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"x-proxy-token": context.proxyToken
			},
			body: JSON.stringify({
				channel_type: channelType,
				account_id: accountId
			})
		});
	} catch {}
}
//#endregion
//#region extensions/pazi/src/brave/brave-env.ts
/**
* Sets a sentinel BRAVE_API_KEY environment variable so the agent's web_search
* tool activates Brave Search support without needing a real API key.
*
* The actual API key is stored on the backend and injected by the Brave proxy.
* The sentinel value just ensures the tool doesn't skip Brave search due to
* a missing key.
*/
const BRAVE_PROXY_SENTINEL = "pazi-proxy";
let previousValue;
let installed = false;
/**
* Set BRAVE_API_KEY to a sentinel value if not already set.
* Saves the previous value for restoration on uninstall.
*/
function installBraveEnvDefaults() {
	if (installed) return;
	installed = true;
	previousValue = process.env.BRAVE_API_KEY;
	if (!process.env.BRAVE_API_KEY) process.env.BRAVE_API_KEY = BRAVE_PROXY_SENTINEL;
}
/**
* Restore the original BRAVE_API_KEY value (or remove it if it wasn't set).
*/
function uninstallBraveEnvDefaults() {
	if (!installed) return;
	installed = false;
	if (previousValue === void 0) delete process.env.BRAVE_API_KEY;
	else process.env.BRAVE_API_KEY = previousValue;
	previousValue = void 0;
}
//#endregion
//#region extensions/pazi/src/brave/brave-fetch-interceptor.ts
/**
* Intercepts globalThis.fetch calls targeting the Brave Search API
* and rewrites them to go through the Pazi backend proxy.
*
* The Pazi backend handles Brave API key injection and credit deduction.
*/
const BRAVE_ORIGIN = "https://api.search.brave.com";
/** Brave API path prefixes that should be proxied */
const PROXIED_PATH_PREFIXES = ["/res/v1/web/search", "/res/v1/llm/context"];
let originalFetch = null;
let installedApiUrl = null;
function isBraveRequest(url) {
	return url.origin === BRAVE_ORIGIN && PROXIED_PATH_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}
/**
* Install the fetch interceptor.
* Saves the original globalThis.fetch and replaces it with a version
* that rewrites Brave Search API requests to go through the Pazi backend.
*
* @param apiUrl The Pazi API base URL (e.g. "https://api.pazi.ai")
*/
function installBraveFetchInterceptor(apiUrl) {
	if (originalFetch) {
		installedApiUrl = apiUrl;
		return;
	}
	const baseFetch = globalThis.fetch;
	originalFetch = baseFetch;
	installedApiUrl = apiUrl;
	const interceptedFetch = (input, init) => {
		const currentApiUrl = installedApiUrl;
		if (!currentApiUrl) return baseFetch(input, init);
		let url = null;
		try {
			if (typeof input === "string") url = new URL(input);
			else if (input instanceof URL) url = input;
			else if (input instanceof Request) url = new URL(input.url);
		} catch {}
		if (!url || !isBraveRequest(url)) return baseFetch(input, init);
		if (process.env.BRAVE_API_KEY !== "pazi-proxy") return baseFetch(input, init);
		const proxyUrl = `${currentApiUrl}/brave${url.pathname + url.search}`;
		const context = getProxyContext();
		if (!context) return baseFetch(input, init);
		const originalHeaders = new Headers(init?.headers ?? (input instanceof Request ? input.headers : void 0));
		const newHeaders = new Headers();
		const accept = originalHeaders.get("Accept");
		if (accept) newHeaders.set("Accept", accept);
		const contentType = originalHeaders.get("Content-Type");
		if (contentType) newHeaders.set("Content-Type", contentType);
		const acceptEncoding = originalHeaders.get("Accept-Encoding");
		if (acceptEncoding) newHeaders.set("Accept-Encoding", acceptEncoding);
		newHeaders.set("X-Proxy-Token", context.proxyToken);
		newHeaders.set("X-User-Id", context.userId);
		const newInit = {
			method: init?.method ?? (input instanceof Request ? input.method : "GET"),
			headers: newHeaders,
			signal: init?.signal ?? (input instanceof Request ? input.signal : void 0),
			body: init?.body ?? (input instanceof Request ? input.body : void 0)
		};
		const duplex = init?.duplex ?? (input instanceof Request ? input.duplex : void 0);
		if (duplex) newInit.duplex = duplex;
		return baseFetch(proxyUrl, newInit);
	};
	globalThis.fetch = interceptedFetch;
}
/**
* Uninstall the fetch interceptor, restoring the original globalThis.fetch.
*/
function uninstallBraveFetchInterceptor() {
	if (originalFetch) {
		globalThis.fetch = originalFetch;
		originalFetch = null;
	}
	installedApiUrl = null;
}
//#endregion
//#region extensions/pazi/src/browser-use/config.ts
const DEFAULT_BROWSER_USE_TIMEOUT_MS = 12e4;
function normalizeString(value) {
	if (typeof value !== "string") return;
	const trimmed = value.trim();
	return trimmed.length > 0 ? trimmed : void 0;
}
function normalizeNumber(value) {
	if (typeof value === "number" && Number.isFinite(value) && value > 0) return Math.floor(value);
	if (typeof value === "string" && value.trim().length > 0) {
		const parsed = Number.parseInt(value, 10);
		if (Number.isFinite(parsed) && parsed > 0) return parsed;
	}
}
function normalizeBoolean(value) {
	if (typeof value === "boolean") return value;
	if (typeof value === "string") {
		const normalized = value.trim().toLowerCase();
		if ([
			"1",
			"true",
			"yes",
			"on"
		].includes(normalized)) return true;
		if ([
			"0",
			"false",
			"no",
			"off"
		].includes(normalized)) return false;
	}
}
function withBrowserUsePath(baseUrl) {
	try {
		const url = new URL(baseUrl);
		const normalizedPath = url.pathname.replace(/\/+$/, "");
		if (normalizedPath.endsWith("/browser-use")) url.pathname = normalizedPath;
		else if (normalizedPath.length === 0 || normalizedPath === "/") url.pathname = "/browser-use";
		else url.pathname = `${normalizedPath}/browser-use`;
		return url.toString();
	} catch {
		return baseUrl;
	}
}
function resolveBrowserUseConfig(params) {
	const env = params.env ?? process.env;
	const raw = params.pluginConfig ?? {};
	const browserUseEnabled = normalizeBoolean(raw.browserUseEnabled) ?? normalizeBoolean(env.BROWSER_USE_ENABLED) ?? false;
	const browserUseTimeoutMs = normalizeNumber(raw.browserUseTimeoutMs) ?? normalizeNumber(env.BROWSER_USE_TIMEOUT_MS) ?? DEFAULT_BROWSER_USE_TIMEOUT_MS;
	const billingConfig = resolvePaziBillingConfig({
		pluginConfig: params.pluginConfig,
		env
	});
	const browserUseApiBase = normalizeString(env.BROWSER_USE_API_URL) ?? normalizeString(billingConfig.apiUrl);
	return {
		browserUseEnabled,
		browserUseApiUrl: browserUseApiBase ? withBrowserUsePath(browserUseApiBase) : void 0,
		browserUseTimeoutMs
	};
}
//#endregion
//#region extensions/pazi/src/browser-use/api.ts
function resolveApiParams$1(pluginConfig) {
	const context = getProxyContext();
	if (!context) throw new Error("No billing context set — workspace may not be initialized yet");
	const resolved = resolveBrowserUseConfig({
		pluginConfig,
		env: process.env
	});
	const apiUrl = resolved.browserUseApiUrl?.trim();
	if (!apiUrl) throw new Error("Browser Use API URL not configured");
	let baseUrl;
	try {
		baseUrl = new URL(apiUrl);
	} catch {
		throw new Error(`Invalid Browser Use API URL: ${apiUrl}`);
	}
	return {
		apiUrl: baseUrl.toString(),
		proxyToken: context.proxyToken,
		timeoutMs: resolved.browserUseTimeoutMs
	};
}
function buildEndpointUrl(baseApiUrl, endpointPath) {
	const url = new URL(baseApiUrl);
	url.pathname = `${url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`}${endpointPath.replace(/^\/+/, "")}`;
	url.search = "";
	url.hash = "";
	return url;
}
function readErrorMessage(payload) {
	if (!payload) return;
	if (typeof payload === "string") return payload;
	if (typeof payload === "object") {
		const record = payload;
		if (typeof record.error === "string") return record.error;
		if (typeof record.message === "string") return record.message;
	}
}
async function readJsonBody$5(res) {
	const text = await res.text();
	if (!text.trim()) return null;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}
async function parseResponse$1(res) {
	const payload = await readJsonBody$5(res);
	if (res.ok) return {
		ok: true,
		data: payload
	};
	const message = readErrorMessage(payload) ?? res.statusText ?? "Request failed";
	return {
		ok: false,
		error: `Pazi Browser Use API error${res.status ? ` (${res.status})` : ""}: ${message}`
	};
}
function withTimeoutSignal$1(timeoutMs, signal) {
	const controller = new AbortController();
	const timer = setTimeout(() => {
		controller.abort();
	}, timeoutMs);
	const onAbort = () => {
		controller.abort();
	};
	if (signal) if (signal.aborted) controller.abort();
	else signal.addEventListener("abort", onAbort, { once: true });
	return {
		signal: controller.signal,
		cleanup: () => {
			clearTimeout(timer);
			if (signal) signal.removeEventListener("abort", onAbort);
		}
	};
}
async function requestJson(params) {
	const url = buildEndpointUrl(params.apiParams.apiUrl, params.endpointPath);
	const headers = new Headers(params.init?.headers);
	headers.set("x-proxy-token", params.apiParams.proxyToken);
	const timeout = withTimeoutSignal$1(params.apiParams.timeoutMs, params.signal);
	try {
		return await parseResponse$1(await fetch(url, {
			...params.init,
			headers,
			signal: timeout.signal
		}));
	} catch (err) {
		if (err instanceof Error && err.name === "AbortError") return {
			ok: false,
			error: `Pazi Browser Use API request timed out after ${String(params.apiParams.timeoutMs)}ms`
		};
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	} finally {
		timeout.cleanup();
	}
}
async function createSession(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: "session",
			init: {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(params.body ?? {})
			},
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function getSessionStatus(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: `session/${encodeURIComponent(params.sessionId)}`,
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function getSnapshot(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: `session/${encodeURIComponent(params.sessionId)}/snapshot`,
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function getScreenshot(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: `session/${encodeURIComponent(params.sessionId)}/screenshot`,
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function runTask(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: "task",
			init: {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(params.body)
			},
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function getTaskStatus(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: `task/${encodeURIComponent(params.taskId)}`,
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function stopSession(params, signal) {
	try {
		return await requestJson({
			apiParams: resolveApiParams$1(params.pluginConfig),
			endpointPath: `session/${encodeURIComponent(params.sessionId)}`,
			init: { method: "DELETE" },
			signal
		});
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
//#endregion
//#region extensions/pazi/src/browser-use/tools.ts
const BROWSER_USE_ACTIONS = [
	"run",
	"session_create",
	"session_stop",
	"snapshot",
	"screenshot",
	"status"
];
function stringEnum(values, options = {}) {
	return Type.Unsafe({
		type: "string",
		enum: [...values],
		...options
	});
}
function json$5(payload, summary) {
	const details = payload;
	return {
		content: [{
			type: "text",
			text: summary ? `${summary}\n\n${JSON.stringify(payload, null, 2)}` : JSON.stringify(payload, null, 2)
		}],
		details
	};
}
function readRequiredString(params, key) {
	const value = params[key];
	if (typeof value !== "string") throw new Error(`${key} required`);
	const trimmed = value.trim();
	if (!trimmed) throw new Error(`${key} required`);
	return trimmed;
}
function readOptionalString(params, key) {
	const value = params[key];
	if (typeof value !== "string") return;
	const trimmed = value.trim();
	return trimmed.length > 0 ? trimmed : void 0;
}
function fileExtensionFromContentType(contentType) {
	if (!contentType) return;
	const normalized = contentType.toLowerCase();
	if (normalized.includes("image/png")) return ".png";
	if (normalized.includes("image/jpeg") || normalized.includes("image/jpg")) return ".jpg";
	if (normalized.includes("image/webp")) return ".webp";
}
function extensionFromUrl(rawUrl) {
	try {
		const extension = extname(new URL(rawUrl).pathname).trim().toLowerCase();
		if (!extension) return;
		if (extension.length > 10) return;
		return extension;
	} catch {
		return;
	}
}
function withTimeoutSignal(timeoutMs, signal) {
	const controller = new AbortController();
	const timer = setTimeout(() => {
		controller.abort();
	}, timeoutMs);
	const onAbort = () => {
		controller.abort();
	};
	if (signal) if (signal.aborted) controller.abort();
	else signal.addEventListener("abort", onAbort, { once: true });
	return {
		signal: controller.signal,
		cleanup: () => {
			clearTimeout(timer);
			if (signal) signal.removeEventListener("abort", onAbort);
		}
	};
}
async function downloadScreenshot(params) {
	const timeout = withTimeoutSignal(params.timeoutMs, params.signal);
	try {
		const res = await fetch(params.url, {
			method: "GET",
			signal: timeout.signal
		});
		if (!res.ok) {
			const statusText = res.statusText || "request_failed";
			throw new Error(`Screenshot download failed (${String(res.status)}): ${statusText}`);
		}
		const bytes = Buffer.from(await res.arrayBuffer());
		const extension = fileExtensionFromContentType(res.headers.get("content-type")) ?? extensionFromUrl(params.url) ?? ".png";
		const path = join(await mkdtemp(join(tmpdir(), "openclaw-browser-use-")), `screenshot${extension}`);
		await writeFile(path, bytes);
		return {
			path,
			bytes: bytes.byteLength,
			mimeType: res.headers.get("content-type") ?? void 0
		};
	} finally {
		timeout.cleanup();
	}
}
function buildStatusHint(action) {
	if (action === "run") return "Task started. Poll with action=status and taskId until status is completed or failed.";
	if (action === "session_create") return "Session created. Use snapshot/screenshot/status/session_stop with this sessionId.";
	return "";
}
function createBrowserUseTools(deps) {
	return [{
		name: "browser_use",
		label: "Browser Use",
		description: "Stealth cloud browser automation via Pazi Browser Use API. Supports async run tasks and direct session controls.",
		parameters: Type.Object({
			action: stringEnum(BROWSER_USE_ACTIONS, { description: `Action to perform: ${BROWSER_USE_ACTIONS.join(", ")}` }),
			task: Type.Optional(Type.String({ description: "Natural language browsing task for action=run." })),
			taskId: Type.Optional(Type.String({ description: "Task ID for action=status." })),
			sessionId: Type.Optional(Type.String({ description: "Session ID for session_stop, snapshot, screenshot, or session status checks." })),
			url: Type.Optional(Type.String({ description: "Optional starting URL used when creating a new session." }))
		}, { additionalProperties: false }),
		async execute(_toolCallId, params, signal) {
			try {
				const actionRaw = params.action;
				const action = typeof actionRaw === "string" ? actionRaw.trim() : void 0;
				if (!action) throw new Error("action required");
				switch (action) {
					case "run": {
						const task = readRequiredString(params, "task");
						const sessionId = readOptionalString(params, "sessionId");
						const result = await runTask({
							pluginConfig: deps.pluginConfig,
							body: {
								task,
								...sessionId ? { sessionId } : {}
							}
						}, signal);
						if (!result.ok) return json$5({ error: result.error });
						return json$5({
							status: typeof result.data.status === "string" ? result.data.status : "running",
							taskId: result.data.taskId,
							liveUrl: result.data.liveUrl,
							hint: buildStatusHint(action)
						}, "Browser Use task started.");
					}
					case "session_create": {
						const startUrl = readOptionalString(params, "url");
						const result = await createSession({
							pluginConfig: deps.pluginConfig,
							body: startUrl ? { url: startUrl } : void 0
						}, signal);
						if (!result.ok) return json$5({ error: result.error });
						return json$5({
							sessionId: result.data.sessionId,
							liveUrl: result.data.liveUrl,
							status: result.data.status,
							hint: buildStatusHint(action)
						}, "Browser Use session created.");
					}
					case "session_stop": {
						const sessionId = readRequiredString(params, "sessionId");
						const result = await stopSession({
							pluginConfig: deps.pluginConfig,
							sessionId
						}, signal);
						if (!result.ok) return json$5({ error: result.error });
						return json$5({
							sessionId,
							...result.data
						}, "Browser Use session stopped.");
					}
					case "snapshot": {
						const sessionId = readRequiredString(params, "sessionId");
						const result = await getSnapshot({
							pluginConfig: deps.pluginConfig,
							sessionId
						}, signal);
						if (!result.ok) return json$5({ error: result.error });
						if (typeof result.data.text !== "string") return json$5({ error: "Snapshot response missing text" });
						return {
							content: [{
								type: "text",
								text: result.data.text
							}],
							details: {
								sessionId,
								text: result.data.text
							}
						};
					}
					case "screenshot": {
						const sessionId = readRequiredString(params, "sessionId");
						const screenshot = await getScreenshot({
							pluginConfig: deps.pluginConfig,
							sessionId
						}, signal);
						if (!screenshot.ok) return json$5({ error: screenshot.error });
						const screenshotUrl = typeof screenshot.data.url === "string" ? screenshot.data.url.trim() : "";
						if (!screenshotUrl) return json$5({ error: "Screenshot response missing URL" });
						const downloaded = await downloadScreenshot({
							url: screenshotUrl,
							timeoutMs: resolveBrowserUseConfig({
								pluginConfig: deps.pluginConfig,
								env: process.env
							}).browserUseTimeoutMs,
							signal
						});
						return {
							content: [{
								type: "text",
								text: `FILE:${downloaded.path}`
							}],
							details: {
								sessionId,
								url: screenshotUrl,
								path: downloaded.path,
								bytes: downloaded.bytes,
								mimeType: downloaded.mimeType,
								imagePaths: [downloaded.path]
							}
						};
					}
					case "status": {
						const taskId = readOptionalString(params, "taskId");
						const sessionId = readOptionalString(params, "sessionId");
						if (!taskId && !sessionId) throw new Error("taskId or sessionId required");
						if (taskId && sessionId) throw new Error("Provide either taskId or sessionId, not both");
						if (taskId) {
							const result = await getTaskStatus({
								pluginConfig: deps.pluginConfig,
								taskId
							}, signal);
							if (!result.ok) return json$5({ error: result.error });
							return json$5({
								...result.data,
								taskId
							}, "Browser Use task status.");
						}
						const sessionResult = await getSessionStatus({
							pluginConfig: deps.pluginConfig,
							sessionId
						}, signal);
						if (!sessionResult.ok) return json$5({ error: sessionResult.error });
						return json$5({
							...sessionResult.data,
							sessionId
						}, "Browser Use session status.");
					}
					default: return json$5({ error: `Unsupported action: ${String(action)}` });
				}
			} catch (err) {
				return json$5({ error: err instanceof Error ? err.message : String(err) });
			}
		}
	}];
}
//#endregion
//#region extensions/pazi/src/channels-configure.ts
const VALID_CHANNELS$2 = new Set([
	"slack",
	"telegram",
	"whatsapp"
]);
const VALID_ACK_REACTIONS = new Set([
	"eyes",
	"thumbsup",
	"rocket",
	"white_check_mark",
	"hourglass_flowing_sand"
]);
const ERROR_INVALID_REQUEST$2 = "INVALID_REQUEST";
const ERROR_UNAVAILABLE$2 = "UNAVAILABLE";
const TELEGRAM_PAIRING_POLL_INTERVAL_MS = 3e3;
const DEFAULT_SLASH_COMMAND = "pazi-agent";
const MAX_SLASH_COMMAND_NAME_CHARS = 31;
function sanitizeSlashCommandName(raw, fallback = DEFAULT_SLASH_COMMAND) {
	return (raw ?? "").trim().toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "").slice(0, MAX_SLASH_COMMAND_NAME_CHARS).replace(/-+$/g, "") || fallback;
}
function respondError$2(respond, code, message, payload) {
	respond(false, payload, {
		code,
		message
	});
}
function isChannelType$1(value) {
	return typeof value === "string" && VALID_CHANNELS$2.has(value);
}
function validateParams$1(raw) {
	if (!raw || typeof raw !== "object") return {
		ok: false,
		error: "params must be an object"
	};
	const p = raw;
	if (!isChannelType$1(p.channel)) return {
		ok: false,
		error: "channel must be 'slack', 'telegram', or 'whatsapp'"
	};
	const config = p.config;
	if (!config || typeof config !== "object") return {
		ok: false,
		error: "config must be an object"
	};
	const cfg = config;
	if (p.channel === "slack") {
		const botToken = typeof cfg.botToken === "string" ? cfg.botToken.trim() : "";
		const appToken = typeof cfg.appToken === "string" ? cfg.appToken.trim() : "";
		const accessMode = cfg.accessMode === "closed" ? "closed" : "open";
		const allowFrom = Array.isArray(cfg.allowFrom) ? cfg.allowFrom.filter((entry) => typeof entry === "string" && entry.trim().length > 0) : [];
		if (!botToken || !appToken) return {
			ok: false,
			error: "Slack requires botToken and appToken"
		};
		if (accessMode === "closed" && allowFrom.length === 0) return {
			ok: false,
			error: "Closed Slack access requires at least one allowed Slack user ID"
		};
	}
	if (p.channel === "telegram") {
		if (!(typeof cfg.token === "string" ? cfg.token.trim() : typeof cfg.botToken === "string" ? cfg.botToken.trim() : "")) return {
			ok: false,
			error: "Telegram requires token or botToken"
		};
	}
	return {
		ok: true,
		params: {
			channel: p.channel,
			accountId: typeof p.accountId === "string" ? p.accountId : void 0,
			timeoutMs: typeof p.timeoutMs === "number" ? p.timeoutMs : void 0,
			config: {
				name: typeof cfg.name === "string" ? cfg.name : void 0,
				botToken: typeof cfg.botToken === "string" ? cfg.botToken : void 0,
				appToken: typeof cfg.appToken === "string" ? cfg.appToken : void 0,
				appId: typeof cfg.appId === "string" ? cfg.appId : void 0,
				accessMode: cfg.accessMode === "closed" ? "closed" : "open",
				groupAccessMode: cfg.groupAccessMode === "closed" ? "closed" : "open",
				allowFrom: Array.isArray(cfg.allowFrom) ? cfg.allowFrom.filter((entry) => typeof entry === "string") : void 0,
				slashCommandName: typeof cfg.slashCommandName === "string" ? cfg.slashCommandName : void 0,
				token: typeof cfg.token === "string" ? cfg.token : void 0,
				replyToMode: cfg.replyToMode === "off" || cfg.replyToMode === "first" || cfg.replyToMode === "all" ? cfg.replyToMode : void 0,
				ackReaction: typeof cfg.ackReaction === "string" && VALID_ACK_REACTIONS.has(cfg.ackReaction.trim()) ? cfg.ackReaction.trim() : void 0,
				threadReplyMode: cfg.threadReplyMode === "full" || cfg.threadReplyMode === "summary-only" || cfg.threadReplyMode === "quiet" ? cfg.threadReplyMode : void 0,
				ackMessage: typeof cfg.ackMessage === "string" && cfg.ackMessage.trim().length > 0 ? cfg.ackMessage.trim() : void 0
			}
		}
	};
}
function normalizeSlackAllowFrom(input) {
	return (input ?? []).map((entry) => entry.trim().toUpperCase()).filter((entry) => entry.length > 0);
}
function normalizeBindingChannel$1(channel) {
	return channel.trim().toLowerCase();
}
function upsertChannelAgentBinding(cfg, params) {
	const channel = normalizeBindingChannel$1(params.channel);
	const accountId = params.accountId.trim();
	const agentId = params.agentId.trim();
	if (!channel || !accountId || !agentId || accountId === "default") return cfg;
	const filtered = (Array.isArray(cfg.bindings) ? cfg.bindings : []).filter((binding) => {
		const match = binding?.match;
		return !(binding?.agentId && typeof match?.channel === "string" && typeof match?.accountId === "string" && normalizeBindingChannel$1(match.channel) === channel && match.accountId.trim() === accountId);
	});
	return {
		...cfg,
		bindings: [...filtered, {
			agentId,
			match: {
				channel,
				accountId
			}
		}]
	};
}
function applySlackConfig(cfg, accountId, input, _probe) {
	const botToken = input.botToken?.trim() ?? "";
	const appToken = input.appToken?.trim() ?? "";
	const accessMode = input.accessMode === "closed" ? "closed" : "open";
	const groupAccessMode = input.groupAccessMode === "closed" ? "closed" : "open";
	const allowFrom = accessMode === "open" ? ["*"] : normalizeSlackAllowFrom(input.allowFrom);
	const dmPolicy = accessMode === "open" ? "open" : "allowlist";
	const groupPolicy = groupAccessMode === "open" ? "open" : "allowlist";
	const dm = {
		policy: dmPolicy,
		allowFrom
	};
	const slashCommandName = input.slashCommandName !== void 0 ? sanitizeSlashCommandName(input.slashCommandName) : void 0;
	const { streamMode: _legacyStreamMode, streaming: _rawStreaming, chunkMode: _legacyChunkMode, blockStreaming: _legacyBlockStreaming, blockStreamingCoalesce: _legacyBlockStreamingCoalesce, nativeStreaming: _legacyNativeStreaming, ...existingAccount } = cfg.channels?.slack?.accounts?.[accountId] ?? {};
	if (_rawStreaming && typeof _rawStreaming === "object" && !Array.isArray(_rawStreaming)) existingAccount.streaming = _rawStreaming;
	return upsertChannelAgentBinding({
		...cfg,
		channels: {
			...cfg.channels,
			slack: {
				...cfg.channels?.slack,
				enabled: true,
				accounts: {
					...cfg.channels?.slack?.accounts,
					[accountId]: {
						...existingAccount,
						enabled: true,
						botToken,
						appToken,
						dmPolicy,
						groupPolicy,
						allowFrom,
						dm,
						streaming: {
							...existingAccount.streaming && typeof existingAccount.streaming === "object" ? existingAccount.streaming : {},
							block: { enabled: false }
						},
						replyToMode: "all",
						...existingAccount?.allowBots === void 0 ? { allowBots: true } : {},
						...input.name ? { name: input.name } : {},
						...input.replyToMode ? { replyToMode: input.replyToMode } : {},
						...input.ackReaction?.trim() ? { ackReaction: input.ackReaction.trim() } : {},
						...input.threadReplyMode ? { threadReplyMode: input.threadReplyMode } : {},
						...input.ackMessage?.trim() ? { ackMessage: input.ackMessage.trim() } : {},
						...slashCommandName ? { slashCommand: {
							...cfg.channels?.slack?.accounts?.[accountId]?.slashCommand,
							enabled: true,
							name: slashCommandName
						} } : {}
					}
				}
			}
		}
	}, {
		channel: "slack",
		accountId,
		agentId: accountId
	});
}
function applyTelegramConfig(cfg, accountId, input) {
	const token = (input.token ?? input.botToken ?? "").trim();
	return upsertChannelAgentBinding({
		...cfg,
		channels: {
			...cfg.channels,
			telegram: {
				...cfg.channels?.telegram,
				enabled: true,
				accounts: {
					...cfg.channels?.telegram?.accounts,
					[accountId]: {
						...cfg.channels?.telegram?.accounts?.[accountId],
						enabled: true,
						botToken: token,
						dmPolicy: "pairing",
						...input.name ? { name: input.name } : {}
					}
				}
			}
		}
	}, {
		channel: "telegram",
		accountId,
		agentId: accountId
	});
}
function applyWhatsAppConfig(cfg, accountId, input) {
	return upsertChannelAgentBinding({
		...cfg,
		channels: {
			...cfg.channels,
			whatsapp: {
				...cfg.channels?.whatsapp,
				enabled: true,
				accounts: {
					...cfg.channels?.whatsapp?.accounts,
					[accountId]: {
						...cfg.channels?.whatsapp?.accounts?.[accountId],
						enabled: true,
						dmPolicy: "pairing",
						...input.name ? { name: input.name } : {}
					}
				}
			}
		}
	}, {
		channel: "whatsapp",
		accountId,
		agentId: accountId
	});
}
function createPaziChannelsConfigureHandler(deps) {
	return async ({ params, respond, context }) => {
		const validation = validateParams$1(params);
		if (!validation.ok || !validation.params) {
			respondError$2(respond, ERROR_INVALID_REQUEST$2, validation.error ?? "invalid params");
			return;
		}
		const { channel, config: inputConfig } = validation.params;
		const accountId = validation.params.accountId?.trim() || "default";
		const timeoutMs = validation.params.timeoutMs ?? 5e3;
		let probe;
		if (channel !== "whatsapp") {
			try {
				if (channel === "slack") {
					const token = inputConfig.botToken?.trim() ?? "";
					probe = await deps.probeSlack(token, timeoutMs);
				} else {
					const token = (inputConfig.token ?? inputConfig.botToken ?? "").trim();
					probe = await deps.probeTelegram(token, timeoutMs, void 0);
				}
			} catch (err) {
				respondError$2(respond, ERROR_UNAVAILABLE$2, `probe failed: ${err instanceof Error ? err.message : String(err)}`);
				return;
			}
			if (!probe.ok) {
				respondError$2(respond, ERROR_UNAVAILABLE$2, probe.error ?? "token probe failed", { probe });
				return;
			}
		}
		try {
			await context.stopChannel(channel, accountId);
		} catch (err) {
			respondError$2(respond, ERROR_UNAVAILABLE$2, `failed to stop channel: ${err instanceof Error ? err.message : String(err)}`);
			return;
		}
		try {
			let cfg = deps.loadConfig();
			if (channel === "slack") {
				if (!probe) {
					respondError$2(respond, ERROR_UNAVAILABLE$2, "slack probe result missing");
					return;
				}
				cfg = applySlackConfig(cfg, accountId, inputConfig, probe);
			} else if (channel === "telegram") cfg = applyTelegramConfig(cfg, accountId, inputConfig);
			else if (channel === "whatsapp") cfg = applyWhatsAppConfig(cfg, accountId, inputConfig);
			else throw new Error(`unsupported channel: ${String(channel)}`);
			await deps.writeConfigFile(cfg);
		} catch (err) {
			try {
				await context.startChannel(channel, accountId);
			} catch (restartErr) {
				respondError$2(respond, ERROR_UNAVAILABLE$2, `config write failed and restart failed: ${restartErr instanceof Error ? restartErr.message : String(restartErr)}`);
				return;
			}
			respondError$2(respond, ERROR_UNAVAILABLE$2, `config write failed: ${err instanceof Error ? err.message : String(err)}`);
			return;
		}
		try {
			await context.startChannel(channel, accountId);
		} catch (err) {
			respondError$2(respond, ERROR_UNAVAILABLE$2, `channel restart failed after config update: ${err instanceof Error ? err.message : String(err)}`);
			return;
		}
		const slackTeamId = channel === "slack" ? probe?.team?.id?.trim() ?? "" : "";
		const result = {
			ok: true,
			channel,
			accountId,
			...probe ? { probe } : {},
			...channel === "slack" && inputConfig.appId?.trim() ? { appId: inputConfig.appId.trim().toUpperCase() } : {},
			...slackTeamId ? { teamId: slackTeamId } : {},
			...channel === "slack" ? {
				dmPolicy: inputConfig.accessMode === "closed" ? "allowlist" : "open",
				groupPolicy: inputConfig.groupAccessMode === "closed" ? "allowlist" : "open",
				allowFrom: inputConfig.accessMode === "closed" ? normalizeSlackAllowFrom(inputConfig.allowFrom) : ["*"],
				replyToMode: inputConfig.replyToMode ?? "all",
				ackReaction: inputConfig.ackReaction?.trim() || "eyes",
				threadReplyMode: inputConfig.threadReplyMode ?? "quiet",
				ackMessage: inputConfig.ackMessage?.trim() || void 0
			} : {}
		};
		if (channel === "telegram") {
			const botUsername = probe?.bot?.username?.trim() ?? "";
			result.onboarding = {
				mode: "pairing",
				dmPolicy: "pairing",
				command: "/start",
				botUsername: botUsername || void 0,
				pollingIntervalMs: TELEGRAM_PAIRING_POLL_INTERVAL_MS,
				...botUsername ? { deepLink: `https://t.me/${encodeURIComponent(botUsername)}` } : {}
			};
		} else if (channel === "whatsapp") result.onboarding = {
			mode: "pairing",
			dmPolicy: "pairing",
			method: "qr"
		};
		await deps.onConfigured?.(result);
		respond(true, result);
	};
}
//#endregion
//#region extensions/pazi/src/channels-disconnect.ts
const VALID_CHANNELS$1 = new Set(["slack", "telegram"]);
const DEFAULT_ACCOUNT_ID$1 = "default";
const ERROR_INVALID_REQUEST$1 = "INVALID_REQUEST";
const ERROR_UNAVAILABLE$1 = "UNAVAILABLE";
function respondError$1(respond, code, message, payload) {
	respond(false, payload, {
		code,
		message
	});
}
function isChannelType(value) {
	return typeof value === "string" && VALID_CHANNELS$1.has(value);
}
function isRecord(value) {
	return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function normalizeBindingChannel(channel) {
	return channel.trim().toLowerCase();
}
function validateParams(raw) {
	if (!isRecord(raw)) return {
		ok: false,
		error: "params must be an object"
	};
	if (!isChannelType(raw.channel)) return {
		ok: false,
		error: "channel must be 'slack' or 'telegram'"
	};
	return {
		ok: true,
		params: {
			channel: raw.channel,
			accountId: typeof raw.accountId === "string" ? raw.accountId : void 0
		}
	};
}
function clearLegacyCredentialFields(params) {
	const keys = {
		slack: [
			"botToken",
			"appToken",
			"botTokenFile",
			"appTokenFile"
		],
		telegram: ["botToken", "tokenFile"]
	}[params.channel];
	let changed = false;
	for (const key of keys) if (key in params.channelConfig) {
		delete params.channelConfig[key];
		changed = true;
	}
	return changed;
}
function removeAccountFromChannelConfig(params) {
	const accountsRaw = params.channelConfig.accounts;
	if (!isRecord(accountsRaw)) return {
		changed: false,
		removed: false
	};
	if (!Object.hasOwn(accountsRaw, params.accountId)) return {
		changed: false,
		removed: false
	};
	const nextAccounts = { ...accountsRaw };
	delete nextAccounts[params.accountId];
	if (Object.keys(nextAccounts).length > 0) params.channelConfig.accounts = nextAccounts;
	else delete params.channelConfig.accounts;
	return {
		changed: true,
		removed: true
	};
}
function removeMatchingBindings(params) {
	const bindings = Array.isArray(params.cfg.bindings) ? params.cfg.bindings : null;
	if (!bindings || bindings.length === 0) return {
		changed: false,
		removedBindings: 0
	};
	const normalizedChannel = normalizeBindingChannel(params.channel);
	let removedBindings = 0;
	const nextBindings = bindings.filter((entry) => {
		if (!isRecord(entry) || !isRecord(entry.match)) return true;
		const matchChannel = typeof entry.match.channel === "string" ? normalizeBindingChannel(entry.match.channel) : "";
		const matchAccountId = typeof entry.match.accountId === "string" ? entry.match.accountId.trim() : "";
		if (matchChannel === normalizedChannel && matchAccountId === params.accountId) {
			removedBindings += 1;
			return false;
		}
		return true;
	});
	if (removedBindings === 0) return {
		changed: false,
		removedBindings: 0
	};
	return {
		changed: true,
		removedBindings,
		nextBindings
	};
}
function createPaziChannelsDisconnectHandler(deps) {
	return async ({ params, respond, context }) => {
		const validation = validateParams(params);
		if (!validation.ok) {
			respondError$1(respond, ERROR_INVALID_REQUEST$1, validation.error);
			return;
		}
		const channel = validation.params.channel;
		const accountId = validation.params.accountId?.trim() || DEFAULT_ACCOUNT_ID$1;
		let stopped = false;
		let stopError;
		try {
			await context.stopChannel(channel, accountId);
			stopped = true;
		} catch (err) {
			stopError = err instanceof Error ? err.message : String(err);
		}
		try {
			const cfg = deps.loadConfig();
			const nextCfg = { ...cfg };
			let changed = false;
			let accountRemoved = false;
			let legacyCredentialsCleared = false;
			if (isRecord(cfg.channels)) {
				const nextChannels = { ...cfg.channels };
				const channelConfigRaw = nextChannels[channel];
				if (isRecord(channelConfigRaw)) {
					const nextChannelConfig = { ...channelConfigRaw };
					const accountRemoval = removeAccountFromChannelConfig({
						channelConfig: nextChannelConfig,
						accountId
					});
					if (accountRemoval.changed) {
						changed = true;
						accountRemoved = accountRemoval.removed;
					}
					if (accountId === DEFAULT_ACCOUNT_ID$1) {
						if (clearLegacyCredentialFields({
							channel,
							channelConfig: nextChannelConfig
						})) {
							changed = true;
							legacyCredentialsCleared = true;
						}
					}
					if (changed) {
						if (Object.keys(nextChannelConfig).length > 0) nextChannels[channel] = nextChannelConfig;
						else delete nextChannels[channel];
						if (Object.keys(nextChannels).length > 0) nextCfg.channels = nextChannels;
						else delete nextCfg.channels;
					}
				}
			}
			const bindingCleanup = removeMatchingBindings({
				cfg,
				channel,
				accountId
			});
			if (bindingCleanup.changed) {
				changed = true;
				if (bindingCleanup.nextBindings && bindingCleanup.nextBindings.length > 0) nextCfg.bindings = bindingCleanup.nextBindings;
				else delete nextCfg.bindings;
			}
			if (changed) await deps.writeConfigFile(nextCfg);
			respond(true, {
				ok: true,
				channel,
				accountId,
				changed,
				accountRemoved,
				legacyCredentialsCleared,
				removedBindings: bindingCleanup.removedBindings,
				stopped,
				...stopError ? { stopError } : {}
			});
		} catch (err) {
			respondError$1(respond, ERROR_UNAVAILABLE$1, `failed to disconnect channel account: ${err instanceof Error ? err.message : String(err)}`);
		}
	};
}
//#endregion
//#region extensions/pazi/src/channels-pairing.ts
const DEFAULT_ACCOUNT_ID = "default";
const VALID_CHANNELS = new Set(["telegram"]);
const ERROR_INVALID_REQUEST = "INVALID_REQUEST";
const ERROR_UNAVAILABLE = "UNAVAILABLE";
function respondError(respond, code, message, payload) {
	respond(false, payload, {
		code,
		message
	});
}
function resolveAccountId(raw) {
	if (typeof raw !== "string") return DEFAULT_ACCOUNT_ID;
	return raw.trim() || DEFAULT_ACCOUNT_ID;
}
function parseListParams(raw) {
	if (!raw || typeof raw !== "object") return {
		ok: false,
		error: "params must be an object"
	};
	const params = raw;
	const channel = params.channel === "telegram" ? "telegram" : null;
	if (!channel || !VALID_CHANNELS.has(channel)) return {
		ok: false,
		error: "channel must be 'telegram'"
	};
	return {
		ok: true,
		value: {
			channel,
			accountId: typeof params.accountId === "string" ? params.accountId : void 0
		}
	};
}
function parseApproveParams(raw) {
	const parsed = parseListParams(raw);
	if (!parsed.ok) return parsed;
	const params = raw;
	const code = typeof params.code === "string" ? params.code.trim() : "";
	if (!code) return {
		ok: false,
		error: "code is required"
	};
	return {
		ok: true,
		value: {
			...parsed.value,
			code
		}
	};
}
function summarizePairingRequest(request) {
	const meta = request.meta ?? {};
	return {
		id: request.id,
		code: request.code,
		createdAt: request.createdAt,
		lastSeenAt: request.lastSeenAt,
		meta: {
			accountId: typeof meta.accountId === "string" ? meta.accountId : void 0,
			username: typeof meta.username === "string" ? meta.username : void 0,
			firstName: typeof meta.firstName === "string" ? meta.firstName : void 0,
			lastName: typeof meta.lastName === "string" ? meta.lastName : void 0,
			senderUserId: typeof meta.senderUserId === "string" ? meta.senderUserId : void 0
		}
	};
}
function createPaziChannelsPairingListHandler(deps) {
	return async ({ params, respond }) => {
		const parsed = parseListParams(params);
		if (!parsed.ok) {
			respondError(respond, ERROR_INVALID_REQUEST, parsed.error);
			return;
		}
		const accountId = resolveAccountId(parsed.value.accountId);
		try {
			const pending = await deps.listRequests({
				channel: parsed.value.channel,
				accountId,
				env: deps.env
			});
			respond(true, {
				ok: true,
				channel: parsed.value.channel,
				accountId,
				pending: pending.map((entry) => summarizePairingRequest(entry))
			});
		} catch (err) {
			respondError(respond, ERROR_UNAVAILABLE, `failed to load pairing requests: ${err instanceof Error ? err.message : String(err)}`);
		}
	};
}
function createPaziChannelsPairingApproveHandler(deps) {
	return async ({ params, respond }) => {
		const parsed = parseApproveParams(params);
		if (!parsed.ok) {
			respondError(respond, ERROR_INVALID_REQUEST, parsed.error);
			return;
		}
		const accountId = resolveAccountId(parsed.value.accountId);
		let cfgSnapshot = null;
		try {
			cfgSnapshot = deps.loadConfig();
		} catch (err) {
			deps.logWarn(`pazi.channels.pairing.approve failed to load config snapshot before approval: ${String(err)}`);
		}
		try {
			const approved = await deps.approveCode({
				channel: parsed.value.channel,
				accountId,
				code: parsed.value.code,
				env: deps.env
			});
			if (!approved) {
				respond(true, {
					ok: true,
					channel: parsed.value.channel,
					accountId,
					approved: false
				});
				return;
			}
			if (cfgSnapshot) try {
				await deps.notifyApproved({
					channelId: parsed.value.channel,
					id: approved.id,
					cfg: cfgSnapshot
				});
			} catch (err) {
				deps.logWarn(`pazi.channels.pairing.approve notification failed for telegram id=${approved.id}: ${String(err)}`);
			}
			else deps.logWarn(`pazi.channels.pairing.approve notification skipped for telegram id=${approved.id} because config snapshot was unavailable`);
			respond(true, {
				ok: true,
				channel: parsed.value.channel,
				accountId,
				approved: true,
				id: approved.id
			});
		} catch (err) {
			respondError(respond, ERROR_UNAVAILABLE, `failed to approve pairing request: ${err instanceof Error ? err.message : String(err)}`);
		}
	};
}
//#endregion
//#region extensions/pazi/src/credentials/shared.ts
function slug(raw) {
	return raw.trim().toLowerCase().replace(/[\s:]+/g, "-").replace(/[^a-z0-9._@+\-]+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
}
function normalizeService(raw) {
	return typeof raw === "string" ? slug(raw) : "";
}
function normalizeLabel(raw) {
	if (typeof raw !== "string" || !raw.trim()) return "default";
	return slug(raw);
}
function buildProfileId(service, label) {
	return `${normalizeService(service) || service}:${normalizeLabel(label)}`;
}
function parseProfileId(profileId, fallbackService) {
	const idx = profileId.indexOf(":");
	if (idx === -1) return {
		service: profileId || fallbackService,
		label: "default"
	};
	return {
		service: profileId.slice(0, idx) || fallbackService,
		label: profileId.slice(idx + 1) || "default"
	};
}
/**
* Strip line breaks and non-Latin1 code points from pasted secrets.
* Mirrors src/utils/normalize-secret-input.ts without violating the
* extension import boundary.
*/
function normalizeSecretValue(value) {
	if (typeof value !== "string") return "";
	const collapsed = value.replace(/[\r\n\u2028\u2029]+/g, "");
	let result = "";
	for (const char of collapsed) {
		const cp = char.codePointAt(0);
		if (typeof cp === "number" && cp <= 255) result += char;
	}
	return result.trim();
}
function buildCredential(params) {
	if (params.type === "api_key") return {
		type: "api_key",
		provider: params.service,
		key: params.key,
		...params.metadata ? { metadata: params.metadata } : {}
	};
	const cred = {
		type: "token",
		provider: params.service,
		token: params.key
	};
	if (params.metadata?.email) cred.email = params.metadata.email;
	return cred;
}
function isUserSavedCredential(cred) {
	return cred.type === "api_key" || cred.type === "token";
}
function credentialHasKey(cred) {
	if (cred.type === "api_key") return Boolean(cred.key || cred.keyRef);
	return Boolean(cred.token || cred.tokenRef);
}
function summarizeCredential(profileId, cred) {
	const { service, label } = parseProfileId(profileId, cred.provider);
	return {
		profileId,
		service,
		type: cred.type,
		label,
		hasKey: credentialHasKey(cred)
	};
}
function listCredentialSummaries(store, serviceFilter) {
	const normalized = serviceFilter ? normalizeService(serviceFilter) : void 0;
	const summaries = [];
	for (const [id, cred] of Object.entries(store.profiles)) {
		if (!isUserSavedCredential(cred)) continue;
		if (normalized && normalizeService(cred.provider) !== normalized) continue;
		summaries.push(summarizeCredential(id, cred));
	}
	return summaries;
}
/**
* Find a credential by service + optional label.
*
* Lookup order:
* 1. If label provided: exact match `{service}:{label}`
* 2. If no label: try `{service}:default`
* 3. If no default: find all profiles for service — if exactly one, return it; else null
*/
function findCredential(store, service, label) {
	const svc = normalizeService(service);
	if (label) {
		const id = buildProfileId(svc, label);
		const cred = store.profiles[id];
		if (cred && isUserSavedCredential(cred)) return {
			profileId: id,
			credential: cred
		};
		return null;
	}
	const defaultId = buildProfileId(svc, "default");
	const defaultCred = store.profiles[defaultId];
	if (defaultCred && isUserSavedCredential(defaultCred)) return {
		profileId: defaultId,
		credential: defaultCred
	};
	const matches = [];
	for (const [id, cred] of Object.entries(store.profiles)) {
		if (!isUserSavedCredential(cred)) continue;
		if (normalizeService(cred.provider) === svc) matches.push({
			profileId: id,
			credential: cred
		});
	}
	if (matches.length === 1) return matches[0];
	return null;
}
function listLabelsForService(store, service) {
	const svc = normalizeService(service);
	const labels = [];
	for (const [id, cred] of Object.entries(store.profiles)) {
		if (!isUserSavedCredential(cred)) continue;
		if (normalizeService(cred.provider) === svc) labels.push(parseProfileId(id, cred.provider).label);
	}
	return labels;
}
function extractCredentialValue(cred) {
	return cred.type === "api_key" ? cred.key : cred.token;
}
//#endregion
//#region extensions/pazi/src/credentials/get-credential.ts
function json$4(payload) {
	return {
		content: [{
			type: "text",
			text: JSON.stringify(payload, null, 2)
		}],
		details: payload
	};
}
function createGetCredentialTool() {
	return {
		name: "get_credential",
		label: "Get Credential",
		description: "Retrieve a previously saved credential value for use in the current session. The secret is returned securely (stripped from transcript persistence). If multiple profiles exist for a service, specify a label or call list_saved_credentials first.",
		parameters: Type.Object({
			service: Type.String({ description: "Provider/service name (e.g. 'github')" }),
			label: Type.Optional(Type.String({ description: "Profile label (e.g. 'work-account'). If omitted, returns the 'default' profile or the sole profile for that service." }))
		}, { additionalProperties: false }),
		async execute(_toolCallId, params) {
			try {
				const service = normalizeService(params.service);
				if (!service) throw new Error("service is required");
				const label = typeof params.label === "string" && params.label.trim() ? params.label.trim() : void 0;
				const store = loadAuthProfileStoreForSecretsRuntime();
				const match = findCredential(store, service, label);
				if (!match) {
					if (!label) {
						const labels = listLabelsForService(store, service);
						if (labels.length > 1) return json$4({ error: `Multiple credentials found for ${service}: ${labels.join(", ")}. Specify a label, or call list_saved_credentials to see all profiles.` });
					}
					return json$4({ error: label ? `No saved credential found for ${service} with label "${label}".` : `No saved credential found for ${service}.` });
				}
				const { profileId, credential } = match;
				const value = extractCredentialValue(credential);
				if (!value) return json$4({ error: `Credential ${profileId} exists but has no inline secret value.` });
				const parsed = parseProfileId(profileId, credential.provider);
				return {
					content: [{
						type: "text",
						text: `Retrieved saved credential "${profileId}" for ${service}.`
					}],
					details: {
						status: "ok",
						profileId,
						service: parsed.service,
						type: credential.type,
						label: parsed.label,
						value,
						...credential.type === "api_key" && credential.metadata ? { metadata: credential.metadata } : {},
						...credential.email ? { email: credential.email } : {}
					}
				};
			} catch (err) {
				return json$4({ error: err instanceof Error ? err.message : String(err) });
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/credentials/list-saved-credentials.ts
function createListSavedCredentialsTool() {
	return {
		name: "list_saved_credentials",
		label: "List Saved Credentials",
		description: "List saved credential profiles (service, type, label) without exposing secret values. Use to check what credentials are already stored before calling ask_for_credentials or get_credential.",
		parameters: Type.Object({ service: Type.Optional(Type.String({ description: "Optional: filter by provider/service name (e.g. 'github')" })) }, { additionalProperties: false }),
		async execute(_toolCallId, params) {
			try {
				const serviceFilter = typeof params.service === "string" && params.service.trim() ? normalizeService(params.service) : void 0;
				const summaries = listCredentialSummaries(loadAuthProfileStoreForSecretsRuntime(), serviceFilter);
				return {
					content: [{
						type: "text",
						text: summaries.length === 0 ? "No saved credentials found." : `Found ${summaries.length} saved credential profile(s).`
					}],
					details: { credentials: summaries }
				};
			} catch (err) {
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{
						type: "text",
						text: JSON.stringify({ error: msg }, null, 2)
					}],
					details: { error: msg }
				};
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/credentials/save-credential.ts
function json$3(payload) {
	return {
		content: [{
			type: "text",
			text: JSON.stringify(payload, null, 2)
		}],
		details: payload
	};
}
function createSaveCredentialTool() {
	return {
		name: "save_credential",
		label: "Save Credential",
		description: "Persist a user-provided API key or token into the agent's secure credential store (auth-profiles.json). Use after ask_for_credentials so the user does not need to re-enter credentials next session. Check list_saved_credentials first to avoid duplicates.",
		parameters: Type.Object({
			service: Type.String({ description: "Provider/service name, e.g. 'github' or 'openai'" }),
			type: Type.Unsafe({
				type: "string",
				enum: ["api_key", "token"],
				description: "Credential type: \"api_key\" or \"token\""
			}),
			key: Type.String({ description: "The credential value (API key or token)" }),
			label: Type.Optional(Type.String({ description: "Optional profile label for disambiguation (e.g. 'work-account'). Defaults to 'default'." })),
			metadata: Type.Optional(Type.Record(Type.String(), Type.String(), { description: "Optional key-value metadata (e.g. { email: 'user@example.com' })" }))
		}, { additionalProperties: false }),
		async execute(_toolCallId, params) {
			try {
				const service = normalizeService(params.service);
				if (!service) throw new Error("service is required");
				const type = params.type;
				if (type !== "api_key" && type !== "token") throw new Error("type must be \"api_key\" or \"token\"");
				const key = normalizeSecretValue(params.key);
				if (!key) throw new Error("key must be a non-empty string");
				const label = normalizeLabel(params.label);
				const metadata = params.metadata && typeof params.metadata === "object" ? params.metadata : void 0;
				const profileId = buildProfileId(service, label);
				if (!await upsertAuthProfileWithLock({
					profileId,
					credential: buildCredential({
						service,
						type,
						key,
						metadata
					})
				})) throw new Error("Failed to write to auth-profiles.json");
				const parsed = parseProfileId(profileId, service);
				return {
					content: [{
						type: "text",
						text: `Saved ${type} credential for ${service} as profile "${profileId}".`
					}],
					details: {
						status: "saved",
						profileId,
						service,
						type,
						label: parsed.label
					}
				};
			} catch (err) {
				return json$3({ error: err instanceof Error ? err.message : String(err) });
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/credentials/index.ts
function createCredentialTools() {
	return [
		createSaveCredentialTool(),
		createListSavedCredentialsTool(),
		createGetCredentialTool()
	];
}
//#endregion
//#region extensions/pazi/src/gateway/pazi-credentials.ts
function writeJson$4(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
	res.end(JSON.stringify(body));
}
async function readJsonBody$4(req) {
	const chunks = [];
	for await (const chunk of req) if (typeof chunk === "string") chunks.push(Buffer.from(chunk));
	else chunks.push(chunk);
	try {
		const parsed = JSON.parse(Buffer.concat(chunks).toString());
		if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
	} catch {
		return null;
	}
	return null;
}
const MAX_PROFILE_ID_LENGTH = 256;
function isValidProfileId(profileId) {
	if (typeof profileId !== "string" || profileId.length === 0) return false;
	if (profileId.length > MAX_PROFILE_ID_LENGTH) return false;
	if (profileId.includes("/") || profileId.includes("\\") || profileId.includes("\0")) return false;
	if (!profileId.includes(":")) return false;
	const parsed = parseProfileId(profileId, "");
	return parsed.service.length > 0 && parsed.label.length > 0;
}
function handleList(res) {
	try {
		writeJson$4(res, 200, {
			ok: true,
			credentials: listCredentialSummaries(loadAuthProfileStoreForSecretsRuntime())
		});
	} catch (err) {
		writeJson$4(res, 500, {
			ok: false,
			error: "load_failed",
			message: String(err)
		});
	}
}
function handleDelete(res, profileId) {
	if (!isValidProfileId(profileId)) {
		writeJson$4(res, 400, {
			ok: false,
			error: "invalid_profile_id"
		});
		return;
	}
	try {
		const store = loadAuthProfileStoreForSecretsRuntime();
		if (!(profileId in store.profiles)) {
			writeJson$4(res, 404, {
				ok: false,
				error: "not_found"
			});
			return;
		}
		delete store.profiles[profileId];
		if (store.order) for (const [provider, ids] of Object.entries(store.order)) {
			const filtered = ids.filter((id) => id !== profileId);
			if (filtered.length === 0) delete store.order[provider];
			else store.order[provider] = filtered;
		}
		if (store.lastGood) delete store.lastGood[profileId];
		if (store.usageStats) delete store.usageStats[profileId];
		saveAuthProfileStore(store);
		writeJson$4(res, 200, {
			ok: true,
			deleted: profileId
		});
	} catch (err) {
		writeJson$4(res, 500, {
			ok: false,
			error: "delete_failed",
			message: String(err)
		});
	}
}
function createPaziCredentialsHandler() {
	return async (req, res) => {
		if (req.method !== "POST") {
			writeJson$4(res, 405, {
				ok: false,
				error: "method_not_allowed"
			});
			return;
		}
		const body = await readJsonBody$4(req);
		if (!body) {
			writeJson$4(res, 400, {
				ok: false,
				error: "invalid_json"
			});
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
			default: writeJson$4(res, 400, {
				ok: false,
				error: "unknown_action"
			});
		}
	};
}
//#endregion
//#region extensions/pazi/src/gateway/pazi-files.ts
function isLikelyBinary(buffer) {
	const sampleLen = Math.min(buffer.length, 4096);
	for (let i = 0; i < sampleLen; i++) if (buffer[i] === 0) return true;
	return false;
}
const SCAN_SKIP_DIRS = new Set([
	".git",
	"node_modules",
	".DS_Store",
	"__pycache__",
	".cache"
]);
const SCAN_MAX_FILES = 1e4;
const SCAN_MAX_DEPTH = 10;
async function listFiles(workspaceDir) {
	const files = [];
	const resolvedWorkspace = path.resolve(workspaceDir);
	try {
		await fs$1.access(resolvedWorkspace);
	} catch {
		return files;
	}
	const queue = [{
		dir: resolvedWorkspace,
		depth: 0
	}];
	while (queue.length > 0 && files.length < SCAN_MAX_FILES) {
		const current = queue.shift();
		if (current.depth > SCAN_MAX_DEPTH) continue;
		let dirEntries;
		try {
			dirEntries = await fs$1.readdir(current.dir);
		} catch {
			continue;
		}
		for (const entryName of dirEntries) {
			if (files.length >= SCAN_MAX_FILES) break;
			if (SCAN_SKIP_DIRS.has(entryName)) continue;
			const fullPath = path.join(current.dir, entryName);
			let entryStat;
			try {
				entryStat = await fs$1.lstat(fullPath);
			} catch {
				continue;
			}
			if (entryStat.isDirectory()) {
				queue.push({
					dir: fullPath,
					depth: current.depth + 1
				});
				continue;
			}
			if (!entryStat.isFile() || entryStat.isSymbolicLink()) continue;
			files.push({
				name: path.relative(resolvedWorkspace, fullPath),
				path: fullPath,
				missing: false,
				size: entryStat.size,
				updatedAtMs: Math.floor(entryStat.mtimeMs)
			});
		}
	}
	return files;
}
function resolveRequestWorkspace$1(params, resolveWorkspace) {
	return resolveWorkspace(params && typeof params === "object" ? params.agentId : void 0);
}
function createPaziFilesList(resolveWorkspace) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace$1(params, resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const files = await listFiles(resolved.workspaceDir);
		respond(true, {
			agentId: resolved.agentId,
			workspace: resolved.workspaceDir,
			files
		});
	};
}
function createPaziFilesGet(resolveWorkspace) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace$1(params, resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const { agentId, workspaceDir } = resolved;
		const name = typeof params.name === "string" ? params.name.trim() : "";
		if (!name || name.includes("\0")) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file name "${name}"`));
			return;
		}
		try {
			const result = await readFileWithinRoot({
				rootDir: workspaceDir,
				relativePath: name
			});
			const filePath = path.join(workspaceDir, name);
			const binary = isLikelyBinary(result.buffer);
			respond(true, {
				agentId,
				workspace: workspaceDir,
				file: {
					name,
					path: filePath,
					missing: false,
					size: result.stat.size,
					updatedAtMs: Math.floor(result.stat.mtimeMs),
					content: binary ? result.buffer.toString("base64") : result.buffer.toString("utf-8"),
					encoding: binary ? "base64" : "utf8"
				}
			});
		} catch (err) {
			if (err instanceof SafeOpenError) {
				if (err.code === "not-found") {
					respond(true, {
						agentId,
						workspace: workspaceDir,
						file: {
							name,
							path: path.join(workspaceDir, name),
							missing: true
						}
					});
					return;
				}
				respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file: ${err.message}`));
				return;
			}
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, "read_failed"));
		}
	};
}
function createPaziFilesSet(resolveWorkspace) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace$1(params, resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const { agentId, workspaceDir } = resolved;
		const name = typeof params.name === "string" ? params.name.trim() : "";
		if (!name || name.includes("\0")) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file name "${name}"`));
			return;
		}
		const content = String(params.content ?? "");
		try {
			await writeFileWithinRoot({
				rootDir: workspaceDir,
				relativePath: name,
				data: content,
				encoding: "utf8",
				mkdir: true
			});
		} catch {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `unsafe workspace file "${name}"`));
			return;
		}
		const filePath = path.join(workspaceDir, name);
		let size;
		let updatedAtMs;
		try {
			const stat = await fs$1.stat(filePath);
			size = stat.size;
			updatedAtMs = Math.floor(stat.mtimeMs);
		} catch {}
		respond(true, {
			ok: true,
			agentId,
			workspace: workspaceDir,
			file: {
				name,
				path: filePath,
				missing: false,
				size,
				updatedAtMs,
				content
			}
		});
	};
}
function createPaziFilesDelete(resolveWorkspace) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace$1(params, resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const { agentId, workspaceDir } = resolved;
		const name = typeof params.name === "string" ? params.name.trim() : "";
		if (!name || name.includes("\0")) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file name "${name}"`));
			return;
		}
		const resolvedRoot = path.resolve(workspaceDir);
		const filePath = path.resolve(workspaceDir, name);
		if (!filePath.startsWith(resolvedRoot + path.sep) || filePath === resolvedRoot) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `invalid file: "${name}"`));
			return;
		}
		try {
			if (!(await fs$1.lstat(filePath)).isFile()) {
				respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `not a file: "${name}"`));
				return;
			}
		} catch {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `file not found: "${name}"`));
			return;
		}
		try {
			await fs$1.unlink(filePath);
		} catch (err) {
			if (err instanceof Error && "code" in err && err.code === "ENOENT") {
				respond(true, {
					ok: true,
					agentId,
					workspace: workspaceDir
				});
				return;
			}
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, "delete_failed"));
			return;
		}
		respond(true, {
			ok: true,
			agentId,
			workspace: workspaceDir
		});
	};
}
//#endregion
//#region extensions/pazi/src/gateway/pazi-memory.ts
const ROOT_MEMORY_FILES = ["MEMORY.md", "memory.md"];
const ROOT_MEMORY_NAMES = new Set(ROOT_MEMORY_FILES);
const DATED_MEMORY_RE = /^memory\/\d{4}-\d{2}-\d{2}(?:-[^/]+)?\.md$/;
function normalizeMemoryPath(name) {
	return name.replaceAll("\\", "/");
}
function classifyMemoryFile(name) {
	const normalizedName = normalizeMemoryPath(name);
	if (ROOT_MEMORY_NAMES.has(normalizedName)) return "root";
	if (DATED_MEMORY_RE.test(normalizedName)) return "daily";
	return "note";
}
function sortMemoryEntries(entries) {
	return [...entries].sort((a, b) => {
		const aRoot = rootRank(a.name);
		const bRoot = rootRank(b.name);
		if (aRoot !== bRoot) return aRoot - bRoot;
		if (a.kind === "daily" && b.kind === "daily") return b.name.localeCompare(a.name);
		if (a.kind === "daily") return -1;
		if (b.kind === "daily") return 1;
		return a.name.localeCompare(b.name);
	});
}
function rootRank(name) {
	if (name === "MEMORY.md") return 0;
	if (name === "memory.md") return 1;
	return 2;
}
async function discoverMemoryFiles(workspaceDir, maxFiles = 500, maxDepth = 5) {
	const result = [];
	let rootEntries = [];
	try {
		rootEntries = await fs$1.readdir(workspaceDir);
	} catch {}
	const rootEntrySet = new Set(rootEntries);
	for (const rootFile of ROOT_MEMORY_FILES) if (rootEntrySet.has(rootFile)) result.push(rootFile);
	const memoryDir = path.join(workspaceDir, "memory");
	async function walk(dir, depth) {
		if (depth > maxDepth || result.length >= maxFiles) return;
		let entries;
		try {
			entries = await fs$1.readdir(dir, { withFileTypes: true });
		} catch {
			return;
		}
		for (const entry of entries) {
			if (result.length >= maxFiles) break;
			const fullPath = path.join(dir, entry.name);
			if (entry.isDirectory()) await walk(fullPath, depth + 1);
			else if (entry.isFile() && entry.name.endsWith(".md")) result.push(normalizeMemoryPath(path.relative(workspaceDir, fullPath)));
		}
	}
	await walk(memoryDir, 0);
	return result;
}
function createPaziMemoryGet(resolveWorkspace) {
	return async ({ params, respond }) => {
		const resolved = resolveWorkspace(params && typeof params === "object" ? params.agentId : void 0);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const { workspaceDir } = resolved;
		const filePaths = await discoverMemoryFiles(workspaceDir);
		const entries = [];
		for (const relPath of filePaths) try {
			const result = await readFileWithinRoot({
				rootDir: workspaceDir,
				relativePath: relPath
			});
			const fullPath = path.join(workspaceDir, relPath);
			entries.push({
				name: relPath,
				path: fullPath,
				missing: false,
				size: result.stat.size,
				updatedAtMs: Math.floor(result.stat.mtimeMs),
				content: result.buffer.toString("utf-8"),
				kind: classifyMemoryFile(relPath)
			});
		} catch {
			continue;
		}
		respond(true, {
			agentId: resolved.agentId,
			workspace: workspaceDir,
			files: sortMemoryEntries(entries)
		});
	};
}
//#endregion
//#region extensions/pazi/src/gateway/pazi-skills.ts
function resolveRequestWorkspace(params, resolveWorkspace) {
	return resolveWorkspace(params && typeof params === "object" ? params.agentId : void 0);
}
/**
* Strip a leading YAML frontmatter block from user-pasted content
* to prevent double-frontmatter in the written SKILL.md.
* Only strips if the block between `---` delimiters contains YAML-like
* key-value pairs (e.g. `name: value`) to avoid mangling legitimate
* markdown thematic breaks.
*/
function stripLeadingFrontmatter$1(text) {
	const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
	if (!normalized.startsWith("---\n")) return normalized;
	const endIndex = normalized.indexOf("\n---", 4);
	if (endIndex === -1) return normalized;
	const block = normalized.slice(4, endIndex);
	if (!/^[a-zA-Z_][a-zA-Z0-9_-]*\s*:/m.test(block)) return normalized;
	return normalized.slice(endIndex + 4).replace(/^\n+/, "");
}
/**
* Split a SKILL.md file into frontmatter block and body.
* Returns `null` frontmatter when the file doesn't start with `---`.
*/
function splitSkillDocument(raw) {
	const normalized = raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
	if (!normalized.startsWith("---")) return {
		frontmatter: null,
		body: normalized
	};
	const endIndex = normalized.indexOf("\n---", 3);
	if (endIndex === -1) return {
		frontmatter: null,
		body: normalized
	};
	return {
		frontmatter: normalized.slice(4, endIndex),
		body: normalized.slice(endIndex + 4).replace(/^\n+/, "")
	};
}
/**
* Patch a single top-level scalar in frontmatter text.
* Uses `JSON.stringify` for the value to handle colons / quotes / newlines safely.
*/
function upsertFrontmatterScalar(frontmatter, key, value) {
	const safeValue = JSON.stringify(value);
	const lines = frontmatter.split("\n");
	const regex = new RegExp(`^${key}:\\s`);
	const idx = lines.findIndex((l) => regex.test(l) || l === `${key}:`);
	if (idx !== -1) lines[idx] = `${key}: ${safeValue}`;
	else if (key === "name") lines.unshift(`${key}: ${safeValue}`);
	else {
		const nameIdx = lines.findIndex((l) => /^name:\s/.test(l) || l === "name:");
		lines.splice(nameIdx !== -1 ? nameIdx + 1 : 0, 0, `${key}: ${safeValue}`);
	}
	return lines.join("\n");
}
/**
* Build the final SKILL.md content.
*
* The `content` parameter is body text only (no frontmatter) — the user edits
* body in the content field, while name/description come from separate inputs.
* We read the existing file to preserve any extra frontmatter fields (metadata,
* etc.) and patch only name/description.
*/
function buildUpdatedDocument(params) {
	const { existingRaw, content, name, description } = params;
	let baseFm;
	if (existingRaw) {
		const { frontmatter } = splitSkillDocument(existingRaw);
		baseFm = frontmatter ?? "";
	} else baseFm = "";
	let patchedFm = upsertFrontmatterScalar(baseFm || `name: ${JSON.stringify(name)}`, "name", name);
	patchedFm = upsertFrontmatterScalar(patchedFm, "description", description);
	const separator = content.startsWith("\n") ? "" : "\n";
	return `---\n${patchedFm}\n---\n${separator}${content}`;
}
function slugify(name) {
	return name.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9_-]/g, "").replace(/-+/g, "-").replace(/^-|-$/g, "") || "skill";
}
function createPaziSkillsCapabilities(deps) {
	return async ({ respond }) => {
		const extraDirs = deps.loadConfig().skills?.load?.extraDirs;
		const sharedDir = Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";
		respond(true, { sharedScopeSupported: Boolean(sharedDir) });
	};
}
function createPaziSkillsGet(deps) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace(params, deps.resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const p = params;
		const skillKey = typeof p.skillKey === "string" ? p.skillKey.trim() : "";
		if (!skillKey) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "missing skillKey"));
			return;
		}
		const { buildWorkspaceSkillStatus } = await import("../../plugin-sdk/agent-runtime.js");
		const cfg = deps.loadConfig();
		const entry = buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg }).skills.find((s) => s.skillKey === skillKey);
		if (!entry) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${skillKey}" not found`));
			return;
		}
		try {
			const { body } = splitSkillDocument(await fs$1.readFile(entry.filePath, "utf-8"));
			const cleanBody = stripLeadingFrontmatter$1(body);
			respond(true, {
				skillKey,
				name: entry.name,
				source: entry.source,
				description: entry.description ?? "",
				content: cleanBody,
				bundled: entry.source === "openclaw-bundled",
				scope: entry.source === "openclaw-extra" ? "all" : "agent"
			});
		} catch {
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, "failed to read skill file"));
		}
	};
}
function createPaziSkillsSet(deps) {
	return async ({ params, respond }) => {
		const resolved = resolveRequestWorkspace(params, deps.resolveWorkspace);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const p = params;
		const skillKey = typeof p.skillKey === "string" ? p.skillKey.trim() : "";
		const name = typeof p.name === "string" ? p.name.trim() : "";
		const description = typeof p.description === "string" ? p.description.trim() : "";
		const content = typeof p.content === "string" ? p.content : "";
		const scope = typeof p.scope === "string" ? p.scope : void 0;
		if (!skillKey) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "missing skillKey"));
			return;
		}
		if (!name) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "missing name"));
			return;
		}
		if (!description) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "missing description"));
			return;
		}
		if (!content.trim()) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "missing content"));
			return;
		}
		const { buildWorkspaceSkillStatus } = await import("../../plugin-sdk/agent-runtime.js");
		const cfg = deps.loadConfig();
		const status = buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg });
		const entry = status.skills.find((s) => s.skillKey === skillKey);
		if (!entry) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${skillKey}" not found`));
			return;
		}
		let existingRaw = null;
		try {
			existingRaw = await fs$1.readFile(entry.filePath, "utf-8");
		} catch {}
		const sanitizedContent = stripLeadingFrontmatter$1(content.trim());
		const finalContent = buildUpdatedDocument({
			existingRaw,
			name,
			description,
			content: sanitizedContent
		});
		const currentIsShared = entry.source === "openclaw-extra";
		const wantShared = scope === "all";
		const wantAgent = scope === "agent";
		const scopeChanging = wantShared && !currentIsShared || wantAgent && currentIsShared;
		let writePath;
		let createdOverride = false;
		let oldDirToRemove;
		const resolveSharedSkillsDir = () => {
			const extraDirs = cfg.skills?.load?.extraDirs;
			return Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";
		};
		const targetDirName = slugify(name);
		if (status.skills.find((s) => path.basename(path.dirname(s.filePath)).toLowerCase() === targetDirName && path.resolve(s.filePath) !== path.resolve(entry.filePath))) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${targetDirName}" already exists`));
			return;
		}
		const allAgentIds = listAgentIds(cfg);
		for (const agentIdEntry of allAgentIds) {
			if (agentIdEntry === resolved.agentId) continue;
			const wsDir = resolveAgentWorkspaceDir(cfg, agentIdEntry);
			try {
				await fs$1.access(path.join(wsDir, "skills", targetDirName, "SKILL.md"));
				const candidatePath = path.join(wsDir, "skills", targetDirName, "SKILL.md");
				if (path.resolve(candidatePath) !== path.resolve(entry.filePath)) {
					respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${targetDirName}" already exists`));
					return;
				}
			} catch {}
		}
		if (scopeChanging && wantShared) {
			const sharedDir = resolveSharedSkillsDir();
			if (!sharedDir) {
				respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "no shared skills directory configured (skills.load.extraDirs)"));
				return;
			}
			writePath = path.join(sharedDir, slugify(name), "SKILL.md");
			oldDirToRemove = path.dirname(entry.filePath);
		} else if (scopeChanging && wantAgent) {
			writePath = path.join(resolved.workspaceDir, "skills", slugify(name), "SKILL.md");
			oldDirToRemove = path.dirname(entry.filePath);
		} else {
			const isWorkspaceSkill = entry.source === "openclaw-workspace" || entry.source === "agents-skills-project";
			const isExtraSkill = entry.source === "openclaw-extra";
			if (isWorkspaceSkill || isExtraSkill) writePath = entry.filePath;
			else {
				const dirName = slugify(entry.skillKey);
				const overrideDir = path.join(resolved.workspaceDir, "skills", dirName);
				writePath = path.join(overrideDir, "SKILL.md");
				createdOverride = true;
			}
		}
		try {
			if (oldDirToRemove) {
				const newDir = path.dirname(writePath);
				await fs$1.cp(oldDirToRemove, newDir, { recursive: true });
				await fs$1.writeFile(writePath, finalContent, "utf-8");
				await fs$1.rm(oldDirToRemove, { recursive: true }).catch(() => {});
			} else {
				await fs$1.mkdir(path.dirname(writePath), { recursive: true });
				await fs$1.writeFile(writePath, finalContent, "utf-8");
			}
		} catch {
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, "failed to write skill file"));
			return;
		}
		respond(true, {
			ok: true,
			skillKey,
			createdOverride
		});
	};
}
//#endregion
//#region extensions/pazi/src/gateway/skills-create.ts
/**
* Strip a leading YAML frontmatter block from user-pasted content
* to prevent double-frontmatter in the written SKILL.md.
* Only strips if the block between `---` delimiters contains YAML-like
* key-value pairs (e.g. `name: value`) to avoid mangling legitimate
* markdown thematic breaks.
*/
function stripLeadingFrontmatter(text) {
	const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
	if (!normalized.startsWith("---\n")) return normalized;
	const endIndex = normalized.indexOf("\n---", 4);
	if (endIndex === -1) return normalized;
	const block = normalized.slice(4, endIndex);
	if (!/^[a-zA-Z_][a-zA-Z0-9_-]*\s*:/m.test(block)) return normalized;
	return normalized.slice(endIndex + 4).replace(/^\n+/, "");
}
function createPaziSkillsCreateHandler(deps) {
	return async ({ params, respond }) => {
		const name = typeof params.name === "string" ? params.name.trim() : "";
		const description = typeof params.description === "string" ? params.description.trim() : "";
		const content = typeof params.content === "string" ? params.content : "";
		if (!name) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "name is required"));
			return;
		}
		if (!description) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "description is required"));
			return;
		}
		if (!content.trim()) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "content is required"));
			return;
		}
		if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "name must be alphanumeric with dashes/underscores only"));
			return;
		}
		const normalizedName = name.toLowerCase();
		const scope = typeof params.scope === "string" ? params.scope : "agent";
		const cfg = deps.loadConfig();
		const extraDirs = cfg.skills?.load?.extraDirs;
		const sharedDir = Array.isArray(extraDirs) && typeof extraDirs[0] === "string" ? extraDirs[0].trim() : "";
		const agentId = params && typeof params === "object" ? params.agentId : void 0;
		const resolved = deps.resolveWorkspace(agentId);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		if (scope === "all" && !sharedDir) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "no shared skills directory configured (skills.load.extraDirs)"));
			return;
		}
		if (buildWorkspaceSkillStatus(resolved.workspaceDir, { config: cfg }).skills.find((s) => path.basename(path.dirname(s.filePath)).toLowerCase() === normalizedName)) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`));
			return;
		}
		const allAgentIds = listAgentIds(cfg);
		for (const agentIdEntry of allAgentIds) {
			if (agentIdEntry === resolved.agentId) continue;
			const wsDir = resolveAgentWorkspaceDir(cfg, agentIdEntry);
			try {
				await fs$1.access(path.join(wsDir, "skills", normalizedName, "SKILL.md"));
				respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${normalizedName}" already exists`));
				return;
			} catch {}
		}
		const skillDir = scope === "all" ? path.join(sharedDir, normalizedName) : path.join(resolved.workspaceDir, "skills", normalizedName);
		const skillFile = path.join(skillDir, "SKILL.md");
		const skillContent = `---
name: ${normalizedName}
description: ${description}
---

${stripLeadingFrontmatter(content.trim())}
`.trimEnd() + "\n";
		try {
			await fs$1.mkdir(skillDir, { recursive: true });
			await fs$1.writeFile(skillFile, skillContent, "utf-8");
		} catch (err) {
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, `failed to create skill: ${err instanceof Error ? err.message : String(err)}`));
			return;
		}
		respond(true, {
			ok: true,
			name: normalizedName,
			created: true
		});
	};
}
//#endregion
//#region extensions/pazi/src/gateway/skills-delete.ts
/**
* Sources that represent user-managed skills which can be deleted.
* Bundled and extra skills cannot be deleted — only disabled.
*/
const DELETABLE_SOURCES = new Set([
	"openclaw-workspace",
	"openclaw-managed",
	"openclaw-extra",
	"agents-skills-project",
	"agents-skills-personal"
]);
function createPaziSkillsDeleteHandler(deps) {
	return async ({ params, respond }) => {
		const skillKey = typeof params.skillKey === "string" ? params.skillKey.trim() : "";
		if (!skillKey) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "skillKey is required"));
			return;
		}
		const agentId = params && typeof params === "object" ? params.agentId : void 0;
		const resolved = deps.resolveWorkspace(agentId);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const cfg = deps.loadConfig();
		const entry = loadWorkspaceSkillEntries(resolved.workspaceDir, { config: cfg }).find((e) => {
			return (e.metadata?.skillKey ?? e.skill.name) === skillKey;
		});
		if (!entry) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `skill "${skillKey}" not found`));
			return;
		}
		if (!DELETABLE_SOURCES.has(entry.skill.source)) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `cannot delete ${entry.skill.source} skill — only user-managed skills can be removed`));
			return;
		}
		const skillDir = path.dirname(entry.skill.filePath);
		if (entry.skill.source === "openclaw-extra") {
			if (!(cfg.skills?.load?.extraDirs ?? []).filter((d) => typeof d === "string" && d.trim().length > 0).some((dir) => skillDir.startsWith(dir + path.sep) || skillDir === dir)) {
				respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "cannot delete plugin-provided skills"));
				return;
			}
		}
		try {
			await fs$1.rm(skillDir, {
				recursive: true,
				force: true
			});
		} catch (err) {
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, `failed to delete skill directory: ${err instanceof Error ? err.message : String(err)}`));
			return;
		}
		const skills = cfg.skills ? { ...cfg.skills } : {};
		const configEntries = skills.entries ? { ...skills.entries } : {};
		if (skillKey in configEntries) {
			delete configEntries[skillKey];
			skills.entries = configEntries;
			const nextConfig = {
				...cfg,
				skills
			};
			try {
				await deps.writeConfigFile(nextConfig);
			} catch {}
		}
		respond(true, {
			ok: true,
			skillKey,
			deleted: true
		});
	};
}
//#endregion
//#region extensions/pazi/src/templates/load-template.ts
const TEMPLATES_ROOT = new URL("../../templates/agent-templates", import.meta.url);
/**
* List all available template IDs by scanning subdirectories of the
* templates root that contain a `template.json`.
*/
async function listTemplateIds() {
	const rootDir = fileURLToPath(TEMPLATES_ROOT);
	let entries;
	try {
		entries = await fs$1.readdir(rootDir);
	} catch {
		return [];
	}
	const ids = [];
	for (const entry of entries) try {
		await fs$1.access(path.join(rootDir, entry, "template.json"));
		ids.push(entry);
	} catch {}
	return ids;
}
/**
* Load a template's manifest and all referenced files from disk.
*
* Returns `null` if the template does not exist or its manifest is invalid.
*/
async function loadTemplate$1(templateId) {
	if (!/^[a-zA-Z0-9_-]+$/.test(templateId)) return null;
	const templateDir = path.join(fileURLToPath(TEMPLATES_ROOT), templateId);
	const manifestPath = path.join(templateDir, "template.json");
	let rawManifest;
	try {
		rawManifest = await fs$1.readFile(manifestPath, "utf-8");
	} catch {
		return null;
	}
	let manifest;
	try {
		manifest = JSON.parse(rawManifest);
	} catch {
		return null;
	}
	if (typeof manifest.id !== "string" || manifest.id.trim() === "" || manifest.id !== templateId || typeof manifest.name !== "string" || typeof manifest.description !== "string" || !Array.isArray(manifest.files) || !Array.isArray(manifest.skills) || !manifest.files.every((entry) => typeof entry === "string" && entry.trim() !== "") || !manifest.skills.every((entry) => typeof entry === "string" && entry.trim() !== "")) return null;
	const allRelativePaths = [...manifest.files, ...manifest.skills].map((entry) => entry.trim());
	const files = [];
	const errors = [];
	const resolvedTemplateDir = path.resolve(templateDir);
	for (const relPath of allRelativePaths) {
		const resolvedPath = path.resolve(templateDir, relPath);
		if (!resolvedPath.startsWith(resolvedTemplateDir + path.sep) && resolvedPath !== resolvedTemplateDir) {
			errors.push(`${relPath}: path traversal rejected`);
			continue;
		}
		try {
			const content = await fs$1.readFile(resolvedPath, "utf-8");
			files.push({
				relativePath: relPath,
				content
			});
		} catch (err) {
			errors.push(`${relPath}: ${err instanceof Error ? err.message : "failed to read template file"}`);
		}
	}
	return {
		manifest,
		files,
		errors
	};
}
//#endregion
//#region extensions/pazi/src/gateway/templates-instantiate.ts
/**
* RPC handler: `pazi.templates.instantiate`
*
* Writes a template's files (IDENTITY.md, SOUL.md, skills) into the
* target agent's workspace.
*
* Params:
*   - templateId (string, required): ID of the template to instantiate
*   - agentId    (string, optional): target gateway agent ID
*/
function createPaziTemplatesInstantiateHandler(deps) {
	return async ({ params, respond }) => {
		const templateId = typeof params.templateId === "string" ? params.templateId.trim() : "";
		if (!templateId) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "templateId is required"));
			return;
		}
		const result = await loadTemplate$1(templateId);
		if (!result) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, `template "${templateId}" not found`));
			return;
		}
		const agentId = params && typeof params === "object" ? params.agentId : void 0;
		const resolved = deps.resolveWorkspace(agentId);
		if (!resolved) {
			respond(false, void 0, errorShape(ErrorCodes.INVALID_REQUEST, "unknown agent id"));
			return;
		}
		const { manifest, files, errors: loadErrors } = result;
		const written = [];
		const errors = [...loadErrors];
		for (const file of files) {
			const targetPath = path.join(resolved.workspaceDir, file.relativePath);
			const resolvedTarget = path.resolve(targetPath);
			const resolvedWorkspace = path.resolve(resolved.workspaceDir);
			if (!resolvedTarget.startsWith(resolvedWorkspace + path.sep) && resolvedTarget !== resolvedWorkspace) {
				errors.push(`${file.relativePath}: path traversal rejected`);
				continue;
			}
			try {
				await fs$1.mkdir(path.dirname(targetPath), { recursive: true });
				await fs$1.writeFile(targetPath, file.content, "utf-8");
				written.push(file.relativePath);
			} catch (err) {
				errors.push(`${file.relativePath}: ${err instanceof Error ? err.message : String(err)}`);
			}
		}
		if (written.length === 0 && errors.length > 0) {
			respond(false, void 0, errorShape(ErrorCodes.UNAVAILABLE, `failed to write any template files: ${errors.join("; ")}`));
			return;
		}
		respond(true, {
			ok: true,
			templateId: manifest.id,
			agentId: resolved.agentId,
			written,
			errors
		});
	};
}
/**
* RPC handler: `pazi.templates.list`
*
* Returns the list of available template IDs.
*/
function createPaziTemplatesListHandler() {
	return async ({ respond }) => {
		respond(true, {
			ok: true,
			templates: await listTemplateIds()
		});
	};
}
//#endregion
//#region extensions/pazi/src/goals/set-goal-tool.ts
function json$2(payload) {
	return {
		content: [{
			type: "text",
			text: JSON.stringify(payload, null, 2)
		}],
		details: payload
	};
}
function emitIntegrationEvent$1(payload) {
	const scope = getPluginRuntimeGatewayRequestScope();
	if (!scope?.context) throw new Error("Cannot emit outside a gateway request.");
	scope.context.broadcast("integration", payload);
}
async function createGoalViaApi(pluginConfig, body) {
	const context = getProxyContext();
	if (!context) return {
		ok: false,
		error: "No billing context set — workspace may not be initialized yet"
	};
	const apiUrl = resolvePaziBillingConfig({
		pluginConfig,
		env: process.env
	}).apiUrl?.trim();
	if (!apiUrl) return {
		ok: false,
		error: "PAZI_API_URL not configured"
	};
	let baseUrl;
	try {
		baseUrl = new URL(apiUrl);
	} catch {
		return {
			ok: false,
			error: `Invalid PAZI_API_URL: ${apiUrl}`
		};
	}
	const url = new URL("/goals", baseUrl);
	const headers = new Headers();
	headers.set("x-proxy-token", context.proxyToken);
	headers.set("Content-Type", "application/json");
	const res = await fetch(url, {
		method: "POST",
		headers,
		body: JSON.stringify(body)
	});
	const text = await res.text();
	const payload = text.trim() ? JSON.parse(text) : null;
	if (res.ok && payload) return {
		ok: true,
		data: payload
	};
	const record = payload;
	const errMsg = record?.error ?? record?.message ?? res.statusText ?? "Request failed";
	return {
		ok: false,
		error: `Pazi API error (${res.status}): ${errMsg}`
	};
}
function createSetGoalTool(deps) {
	return {
		name: "set_goal",
		label: "Set Goal",
		description: "Create a goal for the user with a tracking plan. The goal is created immediately and a display card appears in the user's dashboard showing the goal details and scheduled check-ins. Use this when the user asks you to set, create, or track a goal. IMPORTANT: Before calling this tool, ask the user questions to understand the goal deeply — what metrics to track, what integrations they use (Twitter, Google Analytics, etc.), how often they want check-ins (daily, weekly, monthly). Then create a comprehensive plan with specific scheduled tasks that will proactively track progress and determine next steps. Each scheduled check-in should be actionable — not just 'check progress' but 'analyze metrics, compare to target, and suggest specific actions to stay on track'. Returns the created goal ID and details.",
		parameters: Type.Object({
			title: Type.String({ description: "Short goal title (max 500 chars)" }),
			description: Type.Optional(Type.String({ description: "Detailed goal description (max 5000 chars)" })),
			targetDate: Type.Optional(Type.String({ description: "Target completion date (ISO 8601, e.g. '2026-05-01')" })),
			startingValue: Type.Optional(Type.Number({ description: "Starting metric value (e.g. 0, 100)" })),
			targetValue: Type.Optional(Type.Number({ description: "Target metric value (e.g. 1000, 50)" })),
			metricLabel: Type.Optional(Type.String({ description: "Metric label (e.g. 'followers', 'users', 'posts')" })),
			scheduledCheckIns: Type.Optional(Type.Array(Type.Object({
				name: Type.String({ description: "Check-in task name" }),
				schedule: Type.String({ description: "Cron expression for check-in schedule" }),
				description: Type.Optional(Type.String({ description: "Check-in description" }))
			}), { description: "Proposed scheduled check-ins for tracking this goal" }))
		}, { additionalProperties: false }),
		async execute(_toolCallId, params, _signal) {
			try {
				const title = typeof params.title === "string" ? params.title.trim() : "";
				const description = typeof params.description === "string" ? params.description.trim() : void 0;
				const targetDate = typeof params.targetDate === "string" ? params.targetDate.trim() : void 0;
				const startingValue = typeof params.startingValue === "number" ? params.startingValue : void 0;
				const targetValue = typeof params.targetValue === "number" ? params.targetValue : void 0;
				const metricLabel = typeof params.metricLabel === "string" ? params.metricLabel.trim() : void 0;
				const scheduledCheckIns = Array.isArray(params.scheduledCheckIns) ? params.scheduledCheckIns : void 0;
				if (!title) throw new Error("title is required");
				const context = getProxyContext();
				if (!context) throw new Error("No proxy context available — workspace may not be initialized yet");
				const result = await createGoalViaApi(deps.pluginConfig, {
					agentId: context.agentId,
					title,
					description: description || void 0,
					targetDate: targetDate || void 0,
					startingValue,
					targetValue,
					currentValue: startingValue,
					metricLabel: metricLabel || void 0,
					scheduledTaskIds: []
				});
				if (!result.ok) return json$2({ error: result.error });
				const goal = result.data.goal;
				emitIntegrationEvent$1({
					action: "goal_created",
					goalId: goal.id,
					title,
					description: description || void 0,
					targetDate: targetDate || void 0,
					startingValue,
					targetValue,
					currentValue: startingValue,
					metricLabel: metricLabel || void 0,
					scheduledCheckIns: scheduledCheckIns || void 0
				});
				return json$2({
					status: "created",
					goalId: goal.id,
					title,
					message: `Goal "${title}" has been created successfully.`
				});
			} catch (err) {
				return json$2({ error: err instanceof Error ? err.message : String(err) });
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-bootstrap-actions.ts
const TEMPLATE_PATH = new URL("../../templates/AGENTS.pazi.md", import.meta.url);
let cachedTemplate = null;
async function loadTemplate() {
	if (cachedTemplate !== null) return cachedTemplate;
	try {
		cachedTemplate = await fs$1.readFile(fileURLToPath(TEMPLATE_PATH), "utf-8");
		return cachedTemplate;
	} catch {
		return null;
	}
}
/**
* Bootstrap hook that appends Pazi frontend-action docs to AGENTS.md
* so the agent knows how to use voice client tools and PAZI_COMMAND text markers.
*/
const paziBootstrapActionsHook = async (event) => {
	if (!isAgentBootstrapEvent(event)) return;
	const template = await loadTemplate();
	if (!template) return;
	const agentsFile = event.context.bootstrapFiles.find((f) => f.name === "AGENTS.md");
	if (!agentsFile || agentsFile.missing) return;
	if (agentsFile.content && agentsFile.content.includes("## Pazi Frontend Actions")) return;
	agentsFile.content = (agentsFile.content ?? "") + "\n\n" + template;
};
//#endregion
//#region extensions/pazi/src/hooks/pazi-bootstrap-user.ts
function normalizeInjectedName(value) {
	return value.replace(/[\r\n]+/g, " ").trim();
}
/**
* Bootstrap hook that injects:
* 1. The user's name into USER.md (from `.pazi/user-meta.json`)
* 2. The agent's display name into IDENTITY.md (from config)
*
* The frontend writes `.pazi/user-meta.json` (via pazi.files.set) right
* after agents.create with: { "name": "Zvonimir" }
*
* The agent's display name comes from the agents.list config entry.
*
* Names are injected both in-memory (for the system prompt) and on disk
* (so the agent sees correct values when reading files with the read tool).
*/
const paziBootstrapUserHook = async (event) => {
	if (!isAgentBootstrapEvent(event)) return;
	const context = event.context;
	const identityFile = context.bootstrapFiles.find((f) => f.name === "IDENTITY.md");
	if (identityFile && !identityFile.missing && identityFile.content) {
		if (identityFile.content.match(/^- \*\*Name:\*\*\s*$/m)) {
			const agentId = context.agentId;
			const agentEntry = (Array.isArray(context.cfg?.agents?.list) ? context.cfg.agents.list : []).find((a) => a?.id === agentId);
			const agentName = typeof agentEntry?.name === "string" ? normalizeInjectedName(agentEntry.name) : "";
			if (agentName) {
				const updated = identityFile.content.replace(/^- \*\*Name:\*\*\s*$(\n\s+_\(set during agent creation\)_)?/m, () => `- **Name:** ${agentName}`);
				identityFile.content = updated;
				if (identityFile.path) try {
					await fs$1.writeFile(identityFile.path, updated, "utf-8");
				} catch {}
			}
		}
	}
	const userFile = context.bootstrapFiles.find((f) => f.name === "USER.md");
	if (!userFile || userFile.missing || !userFile.content) return;
	if (!userFile.content.match(/^- \*\*Name:\*\*\s*$/m)) return;
	const metaPath = path.join(context.workspaceDir, ".pazi", "user-meta.json");
	let userName;
	try {
		const raw = await fs$1.readFile(metaPath, "utf-8");
		const meta = JSON.parse(raw);
		userName = typeof meta.name === "string" ? normalizeInjectedName(meta.name) : void 0;
	} catch {
		return;
	}
	if (!userName) return;
	const updated = userFile.content.replace(/^- \*\*Name:\*\*\s*$/m, () => `- **Name:** ${userName}`).replace(/^- \*\*What to call them:\*\*\s*$/m, () => `- **What to call them:** ${userName}`);
	userFile.content = updated;
	if (userFile.path) try {
		await fs$1.writeFile(userFile.path, updated, "utf-8");
	} catch {}
};
//#endregion
//#region extensions/pazi/src/browser-permission/constants.ts
/**
* Tool names that require browser permission to be enabled.
* Used by the guard hook and the prompt hook.
*/
const BROWSER_TOOL_NAMES = new Set([
	"browser",
	"web_search",
	"web_fetch",
	"browser_use"
]);
//#endregion
//#region extensions/pazi/src/hooks/pazi-browser-guard.ts
/**
* Register before_tool_call hook that blocks browser-related tools
* when browsing is disabled for the workspace.
*/
function registerBrowserGuardHook(api) {
	api.on("before_tool_call", (event) => {
		if (!BROWSER_TOOL_NAMES.has(event.toolName)) return;
		if (isBrowserEnabled()) return;
		return {
			block: true,
			blockReason: "Web browsing is disabled for this workspace. Use the request_browser_permission tool to ask the user to enable it."
		};
	}, { priority: 10 });
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-browser-prompt.ts
const BROWSER_DISABLED_GUIDANCE = [
	"## Browser Access",
	"Browser tools (`browser`, `web_search`, `web_fetch`, `browser_use`) are currently DISABLED for this workspace.",
	"If you need to browse the web, use the `request_browser_permission` tool to ask the user to enable it.",
	"Do NOT attempt to call browser tools directly — they will be blocked."
].join("\n");
/**
* Register before_prompt_build hook that appends browser access guidance
* to the system prompt when browsing is disabled.
*/
function registerBrowserPromptHook(api) {
	api.on("before_prompt_build", () => {
		if (isBrowserEnabled()) return;
		return { appendSystemContext: BROWSER_DISABLED_GUIDANCE };
	});
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-proxy-agent-sync.ts
/**
* Keep proxy context agentId aligned with the active tool-call agent.
*
* Chat connections can be long-lived and span multiple agent sessions.
* Without this sync, integrations can be scoped to a stale/default agent.
*/
function registerProxyAgentSyncHook(api) {
	api.on("before_tool_call", (_event, ctx) => {
		const nextAgentId = typeof ctx.agentId === "string" ? ctx.agentId.trim() : "";
		if (!nextAgentId) return;
		const current = getProxyContext();
		if (!current || current.agentId === nextAgentId) return;
		setProxyContext({
			...current,
			agentId: nextAgentId
		});
	}, { priority: 20 });
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-tool-result-persist.ts
/**
* Strip sensitive `details` from credential-bearing tool results before
* transcript persistence. Covers ask_for_credentials, ask_for_browser_login,
* save_credential, and get_credential.
*
* list_saved_credentials is intentionally NOT included — it never returns
* secret values.
*/
const DETAILS_STRIPPED_TOOLS = new Set([
	"ask_for_credentials",
	"ask_for_browser_login",
	"save_credential",
	"get_credential"
]);
function registerToolResultPersistHook(api) {
	api.on("tool_result_persist", (event) => {
		if (!DETAILS_STRIPPED_TOOLS.has(event.toolName ?? "")) return;
		const msg = event.message;
		if (msg.details !== void 0) {
			const { details: _stripped, ...rest } = msg;
			return { message: rest };
		}
	}, { priority: 10 });
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-transcription-billing.ts
/**
* Try to get audio duration using ffprobe.
* Returns duration in seconds or null if ffprobe is unavailable or fails.
*/
function probeAudioDuration(mediaPath) {
	return new Promise((resolve) => {
		exec(`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${mediaPath}"`, { timeout: 5e3 }, (error, stdout) => {
			if (error) {
				resolve(null);
				return;
			}
			const duration = parseFloat(stdout.trim());
			if (Number.isFinite(duration) && duration > 0) resolve(duration);
			else resolve(null);
		});
	});
}
/**
* Estimate audio duration from file size.
* Assumes typical voice codec bitrate (~3000 bytes/sec for Opus).
*/
function estimateDurationFromFileSize(fileSizeBytes) {
	const estimatedSeconds = fileSizeBytes / 3e3;
	return Math.min(Math.max(estimatedSeconds, 1), 60);
}
/**
* Post transcription usage to the Pazi API for credit deduction.
*/
function postTranscriptionUsage(apiUrl, proxyToken, durationSeconds, logger) {
	const body = JSON.stringify({ durationSeconds });
	const url = new URL("/transcribe/usage", apiUrl);
	const req = (url.protocol === "https:" ? https.request : http.request)(url, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"X-Proxy-Token": proxyToken
		}
	}, (res) => {
		let responseBody = "";
		res.on("data", (chunk) => {
			responseBody += String(chunk);
		});
		res.on("end", () => {
			if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) logger.info(`pazi transcription billing: credits deducted (${String(durationSeconds)}s, status=${String(res.statusCode)})`);
			else logger.warn(`pazi transcription billing: API returned status ${String(res.statusCode)}: ${responseBody}`);
		});
	});
	req.on("error", (err) => {
		logger.warn(`pazi transcription billing: request failed: ${err.message}`);
	});
	req.write(body);
	req.end();
}
/**
* Register an internal hook handler for `message:transcribed` events.
* When the core agent transcribes channel audio (Slack, Telegram, etc.),
* this hook fires and reports usage to the Pazi API for credit deduction.
*
* This is best-effort: failures are logged but never block message processing.
*/
function registerTranscriptionBillingHook(api) {
	const logger = {
		info: (msg) => api.logger.info(msg),
		warn: (msg) => api.logger.warn(msg)
	};
	registerInternalHook("message:transcribed", async (event) => {
		if (!isMessageTranscribedEvent(event)) return;
		const context = getProxyContext();
		if (!context?.proxyToken) return;
		const apiUrl = process.env.PAZI_API_URL?.trim();
		if (!apiUrl) return;
		const mediaPath = event.context.mediaPath;
		let durationSeconds = null;
		if (mediaPath && typeof mediaPath === "string") {
			durationSeconds = await probeAudioDuration(mediaPath);
			if (durationSeconds === null) try {
				durationSeconds = estimateDurationFromFileSize(fs.statSync(mediaPath).size);
				logger.info(`pazi transcription billing: estimated duration from file size (${String(Math.round(durationSeconds))}s)`);
			} catch {
				logger.warn(`pazi transcription billing: could not stat mediaPath "${mediaPath}", skipping`);
				return;
			}
		}
		if (durationSeconds === null || durationSeconds <= 0) {
			logger.warn("pazi transcription billing: could not determine audio duration, skipping");
			return;
		}
		durationSeconds = Math.min(durationSeconds, 60);
		postTranscriptionUsage(apiUrl, context.proxyToken, durationSeconds, logger);
	});
}
//#endregion
//#region extensions/pazi/src/hooks/pazi-webchat-file-support.ts
const WEBCHAT_FILE_GUIDANCE = `## Webchat File Support
The webchat dashboard fully supports file downloads and previews. When a user asks you to create, export, or generate a file:

### How it works
1. Use the \`write\` tool to create the file in the workspace.
2. The dashboard automatically detects each Write tool call and renders a file card with download and preview buttons.
3. Each \`write\` call produces one file card. To deliver multiple files, call \`write\` once per file.

### File naming
- Use descriptive file names with proper extensions (e.g. \`quarterly-report.csv\`, \`dashboard.html\`, not \`output.txt\`).
- Place files in the workspace root or a clearly named subdirectory.

### Supported types
- **Text:** HTML, JSON, CSV, TXT, Markdown, XML, YAML, TOML
- **Code:** JS, TS, Python, Go, Rust, Java, C/C++, Shell, SQL, and more
- **Documents:** PDF
- **Images:** PNG, JPG, GIF, SVG, WebP
- **Archives:** ZIP, TAR, GZ
- **Audio/Video:** MP3, WAV, MP4, WebM
- Download works for all types. Inline preview works for text, HTML, images, and PDF.
- For binary files (images, archives, audio/video), download always works; preview availability varies by type.

### After writing a file
- Tell the user the file is ready and they can download or preview it using the card that appeared in the chat.
- Do NOT paste raw file paths or instruct the user to run terminal commands to retrieve the file.
- Do NOT dump file contents into the chat when the user asked for a file — write it instead.

### Prohibitions
- Do NOT tell the user that webchat doesn't support file downloads — it does.
- Do NOT use the \`message\` tool with \`media\` or \`buffer\` params to deliver files — use the \`write\` tool.`;
/**
* Injects file download/preview guidance into the system prompt for webchat sessions.
*
* Without this, the agent's system prompt shows `capabilities=none` for webchat
* and the agent refuses to create files, telling users that webchat doesn't support
* file downloads.
*/
function registerWebchatFileSupportHook(api) {
	api.on("before_prompt_build", (_event, ctx) => {
		if ((ctx.channelId ?? ctx.messageProvider ?? "").toLowerCase() !== "webchat") return;
		return { appendSystemContext: WEBCHAT_FILE_GUIDANCE };
	}, { priority: 10 });
}
//#endregion
//#region extensions/pazi/src/image-generation/onboard.ts
const PAZI_DEFAULT_IMAGE_MODEL_REF = "pazi/gpt-image-1.5";
/**
* Set Pazi as the default image generation provider if no provider is configured yet.
* This makes the `image_generate` tool visible to the agent.
*/
function applyPaziImageConfig(cfg) {
	if (cfg.agents?.defaults?.imageGenerationModel) return cfg;
	return {
		...cfg,
		agents: {
			...cfg.agents,
			defaults: {
				...cfg.agents?.defaults,
				imageGenerationModel: { primary: PAZI_DEFAULT_IMAGE_MODEL_REF }
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/image-generation/provider.ts
const PAZI_IMAGE_MODEL = "gpt-image-1.5";
const PAZI_PROVIDER_ID = "pazi";
const DEFAULT_IMAGE_REQUEST_TIMEOUT_MS = 7e4;
const SUPPORTED_SIZES = [
	"1024x1024",
	"1024x1536",
	"1536x1024"
];
/** Resolve the image size from request params */
function mapSize(raw) {
	const normalized = raw?.trim();
	if (normalized && SUPPORTED_SIZES.includes(normalized)) return normalized;
	return "1024x1024";
}
function postJson(url, headers, body, options) {
	const doRequest = url.protocol === "https:" ? https.request : http.request;
	return new Promise((resolve, reject) => {
		const timeoutMs = typeof options?.timeoutMs === "number" && Number.isFinite(options.timeoutMs) && options.timeoutMs > 0 ? Math.floor(options.timeoutMs) : DEFAULT_IMAGE_REQUEST_TIMEOUT_MS;
		let settled = false;
		const finish = (cb) => {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			cb();
		};
		const req = doRequest(url, {
			method: "POST",
			headers: {
				...headers,
				"Content-Type": "application/json"
			}
		}, (res) => {
			const chunks = [];
			res.on("data", (chunk) => chunks.push(chunk));
			res.on("end", () => {
				const raw = Buffer.concat(chunks).toString("utf8");
				try {
					const data = JSON.parse(raw);
					finish(() => resolve({
						status: res.statusCode ?? 500,
						data
					}));
				} catch {
					finish(() => resolve({
						status: res.statusCode ?? 500,
						data: { error: raw }
					}));
				}
			});
		});
		const timeout = setTimeout(() => {
			finish(() => reject(/* @__PURE__ */ new Error(`Pazi image generation request timed out after ${timeoutMs}ms`)));
			req.destroy();
		}, timeoutMs);
		req.on("error", (err) => {
			finish(() => reject(err));
		});
		req.write(body);
		req.end();
	});
}
function buildPaziImageGenerationProvider(params) {
	return {
		id: PAZI_PROVIDER_ID,
		label: "Pazi (GPT Image)",
		defaultModel: PAZI_IMAGE_MODEL,
		models: [PAZI_IMAGE_MODEL],
		capabilities: {
			generate: {
				maxCount: 1,
				supportsSize: true,
				supportsAspectRatio: false,
				supportsResolution: false
			},
			edit: {
				enabled: false,
				maxCount: 0,
				maxInputImages: 0,
				supportsSize: false,
				supportsAspectRatio: false,
				supportsResolution: false
			},
			geometry: { sizes: [...SUPPORTED_SIZES] }
		},
		async generateImage(req) {
			const context = getProxyContext();
			if (!context) throw new Error("Pazi proxy context not available — cannot generate image");
			markProxyActivity();
			const resolved = resolvePaziBillingConfig({
				pluginConfig: params?.pluginConfig,
				env: params?.env
			});
			if (!resolved.apiUrl) throw new Error("PAZI_API_URL not configured — cannot generate image");
			const quality = "medium";
			const size = mapSize(req.size);
			const target = new URL("/images/generate", resolved.apiUrl);
			const body = JSON.stringify({
				prompt: req.prompt,
				quality,
				size,
				model: req.model || PAZI_IMAGE_MODEL
			});
			const { status, data } = await postJson(target, {
				"X-Proxy-Token": context.proxyToken,
				"X-User-Id": context.userId,
				"X-Agent-Id": context.agentId
			}, body, { timeoutMs: req.timeoutMs });
			if (status === 402) throw new Error("Insufficient credits for image generation. Ask the user to add credits.");
			if (status === 400 && data.error === "content_policy") throw new Error(data.message ?? "Image generation blocked by content policy.");
			if (status === 504) throw new Error("Image generation timed out. Please try again.");
			if (status !== 200 || !data.b64_json) throw new Error(`Pazi image generation failed (${status}): ${data.message ?? data.error ?? "unknown error"}`);
			return {
				images: [{
					buffer: Buffer.from(data.b64_json, "base64"),
					mimeType: "image/png",
					fileName: "generated-image.png",
					revisedPrompt: data.revisedPrompt,
					metadata: {
						imageId: data.imageId,
						costUsd: data.costUsd,
						creditsDeducted: data.creditsDeducted,
						quality: data.quality,
						size: data.size
					}
				}],
				model: req.model || PAZI_IMAGE_MODEL,
				metadata: {
					imageId: data.imageId,
					b64_json: data.b64_json,
					costUsd: data.costUsd,
					creditsDeducted: data.creditsDeducted
				}
			};
		}
	};
}
//#endregion
//#region extensions/pazi/src/proxy/pazi-browser-enabled.ts
function writeJson$3(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
	res.end(JSON.stringify(body));
}
async function readJsonBody$3(req) {
	const chunks = [];
	for await (const chunk of req) if (typeof chunk === "string") chunks.push(Buffer.from(chunk));
	else chunks.push(chunk);
	try {
		const parsed = JSON.parse(Buffer.concat(chunks).toString());
		if (parsed && typeof parsed === "object") return parsed;
	} catch {
		return null;
	}
	return null;
}
function createPaziBrowserEnabledHandler(deps) {
	return async (req, res) => {
		const gatewayToken = resolveGatewayToken({
			configToken: deps.configToken,
			env: deps.env
		});
		if (!gatewayToken) {
			deps.logger.warn("pazi browser-enabled request rejected: gateway token missing");
			writeJson$3(res, 500, { error: "gateway_token_missing" });
			return;
		}
		if (req.headers.authorization !== `Bearer ${gatewayToken}`) {
			writeJson$3(res, 401, { error: "unauthorized" });
			return;
		}
		const body = await readJsonBody$3(req);
		if (!body) {
			writeJson$3(res, 400, { error: "invalid JSON" });
			return;
		}
		const { browserEnabled } = body;
		if (typeof browserEnabled !== "boolean") {
			writeJson$3(res, 400, { error: "browserEnabled must be a boolean" });
			return;
		}
		const currentContext = getProxyContext();
		if (!currentContext) {
			deps.logger.warn("pazi browser-enabled request rejected: no current context");
			writeJson$3(res, 500, { error: "no_current_context" });
			return;
		}
		setProxyContext({
			...currentContext,
			browserEnabled
		});
		deps.logger.info(`Browser enabled status updated: ${browserEnabled}`);
		writeJson$3(res, 200, {
			ok: true,
			browserEnabled
		});
	};
}
//#endregion
//#region extensions/pazi/src/proxy/pazi-context.ts
function writeJson$2(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
	res.end(JSON.stringify(body));
}
async function readJsonBody$2(req) {
	const chunks = [];
	for await (const chunk of req) if (typeof chunk === "string") chunks.push(Buffer.from(chunk));
	else chunks.push(chunk);
	try {
		const parsed = JSON.parse(Buffer.concat(chunks).toString());
		if (parsed && typeof parsed === "object") return parsed;
	} catch {
		return null;
	}
	return null;
}
function createPaziContextHandler(deps) {
	return async (req, res) => {
		const gatewayToken = resolveGatewayToken({
			configToken: deps.configToken,
			env: deps.env
		});
		if (!gatewayToken) {
			deps.logger.warn("pazi context request rejected: gateway token missing");
			writeJson$2(res, 500, { error: "gateway_token_missing" });
			return;
		}
		if (req.headers.authorization !== `Bearer ${gatewayToken}`) {
			writeJson$2(res, 401, { error: "unauthorized" });
			return;
		}
		const body = await readJsonBody$2(req);
		if (!body) {
			writeJson$2(res, 400, { error: "invalid JSON" });
			return;
		}
		const { userId, agentId, proxyToken, dashboardBaseUrl, browserEnabled } = body;
		if (!userId || !agentId || !proxyToken) {
			writeJson$2(res, 400, { error: "missing userId, agentId, or proxyToken" });
			return;
		}
		setProxyContext({
			userId,
			agentId,
			proxyToken,
			dashboardBaseUrl: typeof dashboardBaseUrl === "string" && dashboardBaseUrl.trim() ? dashboardBaseUrl.trim() : void 0,
			browserEnabled: browserEnabled === true
		});
		writeJson$2(res, 200, { ok: true });
	};
}
//#endregion
//#region extensions/pazi/src/billing/pazi-billing-message.ts
/**
* Pazi-specific billing error message for when users run out of credits.
* Replaces the generic "API key" message with subscription-specific guidance.
*/
const PAZI_OUT_OF_CREDITS_MESSAGE = "⚠️ You've run out of Pazi credits. Upgrade your subscription to continue: https://pazi.ai/dashboard/account/subscription";
//#endregion
//#region extensions/pazi/src/proxy/pazi-proxy.ts
function requestForUrl(url) {
	return url.protocol === "https:" ? https.request : http.request;
}
function pickAnthropicHeaders(incoming) {
	const forward = {};
	for (const key of [
		"anthropic-version",
		"anthropic-beta",
		"accept",
		"content-type"
	]) {
		const value = incoming[key];
		if (typeof value === "string") forward[key] = value;
	}
	return forward;
}
function writeJson$1(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
	res.end(JSON.stringify(body));
}
async function startPaziProxy(params) {
	const apiUrl = params.apiUrl?.trim();
	if (!apiUrl) {
		params.logger.info("pazi proxy disabled (PAZI_API_URL not set)");
		return null;
	}
	let baseUrl;
	try {
		baseUrl = new URL(apiUrl);
	} catch {
		params.logger.warn(`pazi proxy disabled (invalid PAZI_API_URL: ${apiUrl})`);
		return null;
	}
	const server = http.createServer(async (req, res) => {
		if (req.method !== "POST" || !req.url?.startsWith("/v1/messages")) {
			res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
			res.end("Not Found");
			return;
		}
		const context = getProxyContext();
		if (!context) {
			writeJson$1(res, 503, { error: "no billing context set" });
			return;
		}
		markProxyActivity();
		const chunks = [];
		for await (const chunk of req) if (typeof chunk === "string") chunks.push(Buffer.from(chunk));
		else chunks.push(chunk);
		const body = Buffer.concat(chunks);
		const target = new URL("/anthropic/v1/messages", baseUrl);
		const proxyReq = requestForUrl(target)(target, {
			method: "POST",
			headers: {
				...pickAnthropicHeaders(req.headers),
				"X-Proxy-Token": context.proxyToken,
				"X-User-Id": context.userId,
				"X-Agent-Id": context.agentId
			}
		}, (proxyRes) => {
			if (proxyRes.statusCode === 402) {
				const chunks = [];
				proxyRes.on("data", (chunk) => {
					chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
				});
				proxyRes.on("end", () => {
					const responseBody = Buffer.concat(chunks).toString("utf8");
					try {
						const parsed = JSON.parse(responseBody);
						if (parsed && parsed.error === "insufficient_credits") {
							const body = JSON.stringify({
								type: "error",
								error: {
									type: "insufficient_credits",
									message: PAZI_OUT_OF_CREDITS_MESSAGE
								}
							});
							res.writeHead(402, {
								"Content-Type": "application/json; charset=utf-8",
								"Content-Length": Buffer.byteLength(body).toString()
							});
							res.end(body);
							return;
						}
					} catch (e) {}
					res.writeHead(402, proxyRes.headers);
					res.end(responseBody);
				});
				proxyRes.on("error", (err) => {
					params.logger.warn(`pazi proxy 402 response error: ${String(err)}`);
					if (!res.headersSent) writeJson$1(res, 502, {
						error: "proxy_error",
						message: err.message
					});
				});
			} else {
				res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
				proxyRes.pipe(res);
			}
		});
		proxyReq.on("error", (err) => {
			params.logger.warn(`pazi proxy error: ${String(err)}`);
			if (!res.headersSent) writeJson$1(res, 502, {
				error: "proxy_error",
				message: err.message
			});
		});
		proxyReq.write(body);
		proxyReq.end();
	});
	server.on("clientError", (err, socket) => {
		params.logger.warn(`pazi proxy client error: ${String(err)}`);
		socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(params.port, "127.0.0.1", () => {
			server.off("error", reject);
			resolve();
		});
	});
	params.logger.info(`pazi proxy listening on 127.0.0.1:${params.port}`);
	return server;
}
//#endregion
//#region extensions/pazi/src/proxy/pazi-upload.ts
function writeJson(res, status, body) {
	res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
	res.end(JSON.stringify(body));
}
async function readJsonBody$1(req) {
	const chunks = [];
	for await (const chunk of req) if (typeof chunk === "string") chunks.push(Buffer.from(chunk));
	else chunks.push(chunk);
	try {
		const parsed = JSON.parse(Buffer.concat(chunks).toString());
		if (parsed && typeof parsed === "object") return parsed;
	} catch {
		return null;
	}
	return null;
}
/** Resolve a unique path, appending -1, -2, etc. on collision. */
function uniquePath(dir, name) {
	const ext = extname(name);
	const base = basename(name, ext);
	let candidate = join(dir, name);
	let counter = 0;
	while (existsSync(candidate)) {
		counter++;
		candidate = join(dir, `${base}-${String(counter)}${ext}`);
	}
	return candidate;
}
function createPaziUploadHandler(deps) {
	return async (req, res) => {
		const gatewayToken = resolveGatewayToken({
			configToken: deps.configToken,
			env: deps.env
		});
		if (!gatewayToken) {
			deps.logger.warn("pazi upload request rejected: gateway token missing");
			writeJson(res, 500, { error: "gateway_token_missing" });
			return;
		}
		if (req.headers.authorization !== `Bearer ${gatewayToken}`) {
			writeJson(res, 401, { error: "unauthorized" });
			return;
		}
		const body = await readJsonBody$1(req);
		if (!body) {
			writeJson(res, 400, { error: "invalid JSON" });
			return;
		}
		const { files } = body;
		if (!Array.isArray(files) || files.length === 0) {
			writeJson(res, 400, { error: "no files provided" });
			return;
		}
		const uploadDir = join(homedir(), "Desktop", "agent");
		await mkdir(uploadDir, { recursive: true });
		const paths = [];
		for (const file of files) {
			if (!file.name || !file.content) continue;
			const filePath = uniquePath(uploadDir, file.name);
			await writeFile(filePath, Buffer.from(file.content, "base64"));
			paths.push(filePath);
		}
		deps.logger.info(`pazi upload: wrote ${String(paths.length)} file(s) to ${uploadDir}`);
		writeJson(res, 200, { paths });
	};
}
//#endregion
//#region extensions/pazi/src/reactions/react-tool.ts
/**
* Agent tool: react_to_message
*
* Allows the agent to react to a user message with an emoji in webchat.
* Persists reaction via API and broadcasts to frontend via WebSocket.
*
* When no messageId is provided, stores the reaction with a "latest-user"
* sentinel that the frontend resolves to the most recent user message.
*/
const ALLOWED_EMOJIS = [
	"🙌",
	"👍",
	"❤️",
	"🎉",
	"🔥",
	"👀",
	"🤔",
	"😂",
	"🤷"
];
function json$1(payload) {
	return {
		content: [{
			type: "text",
			text: JSON.stringify(payload, null, 2)
		}],
		details: payload
	};
}
function broadcastReactionEvent(payload) {
	const scope = getPluginRuntimeGatewayRequestScope();
	if (!scope?.context) return;
	scope.context.broadcast("integration", payload);
}
/**
* Sentinel messageId used when the agent reacts without specifying a target.
* The frontend resolves this to the most recent user message in the session.
*/
const LATEST_USER_SENTINEL = "latest-user";
function createReactToMessageTool(deps) {
	return {
		name: "react_to_message",
		label: "React to Message",
		description: "React to a user message in web chat with an emoji. Use this in webchat sessions (not Slack/Discord — those use the message tool with action=react). Call this to express appreciation, acknowledgment, or humor in response to the user's messages. The reaction appears as a badge below their message. You don't need to provide a messageId — it automatically reacts to the most recent user message. Available emojis: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷",
		parameters: Type.Object({
			emoji: Type.String({ description: "The emoji to react with. Must be one of: 🙌 👍 ❤️ 🎉 🔥 👀 🤔 😂 🤷" }),
			messageId: Type.Optional(Type.String({ description: "Optional: the stable ID of the user message to react to. If omitted, automatically reacts to the most recent user message." }))
		}, { additionalProperties: false }),
		async execute(_toolCallId, params) {
			const explicitMessageId = typeof params.messageId === "string" ? params.messageId.trim() : "";
			const emoji = typeof params.emoji === "string" ? params.emoji : "";
			if (!emoji) return json$1({ error: "emoji is required" });
			if (!ALLOWED_EMOJIS.includes(emoji)) return json$1({ error: `Invalid emoji. Allowed: ${ALLOWED_EMOJIS.join(" ")}` });
			const context = getProxyContext();
			if (!context) return json$1({ error: "No proxy context — workspace not initialized" });
			const apiUrl = resolvePaziBillingConfig({
				pluginConfig: deps.pluginConfig,
				env: process.env
			}).apiUrl?.trim();
			if (!apiUrl) return json$1({ error: "PAZI_API_URL not configured" });
			if (!context.agentId) return json$1({ error: "No active agent — cannot determine session key" });
			const sessionKey = `agent:${context.agentId}:main`;
			const messageId = explicitMessageId || LATEST_USER_SENTINEL;
			try {
				const url = new URL("/chat/reactions/agent", apiUrl);
				const response = await fetch(url, {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"x-proxy-token": context.proxyToken
					},
					body: JSON.stringify({
						sessionKey,
						messageId,
						messageRole: "user",
						emoji
					})
				});
				if (!response.ok) {
					const text = await response.text().catch(() => "");
					return json$1({ error: `API error (${response.status}): ${text}` });
				}
				broadcastReactionEvent({
					action: "reaction_added",
					messageId,
					emoji,
					actor: "agent"
				});
				return json$1({
					success: true,
					messageId,
					emoji
				});
			} catch (err) {
				return json$1({ error: err instanceof Error ? err.message : String(err) });
			}
		}
	};
}
//#endregion
//#region extensions/pazi/src/reactions/reaction-event.ts
function readJsonBody(req) {
	return new Promise((resolve, reject) => {
		const chunks = [];
		req.on("data", (chunk) => chunks.push(chunk));
		req.on("end", () => {
			try {
				resolve(JSON.parse(Buffer.concat(chunks).toString("utf-8")));
			} catch (err) {
				reject(err);
			}
		});
		req.on("error", reject);
	});
}
function createReactionEventHandler(deps) {
	return async (req, res) => {
		try {
			const body = await readJsonBody(req);
			if (!body.sessionKey || !body.emoji || !body.action) {
				res.writeHead(400, { "Content-Type": "application/json" });
				res.end(JSON.stringify({ error: "missing_fields" }));
				return;
			}
			enqueueSystemEvent(`User ${body.action === "added" ? "reacted with" : "removed reaction"} ${body.emoji} on a message`, {
				sessionKey: body.sessionKey,
				contextKey: `web:reaction:${body.action}:${body.sessionKey}:${body.emoji}:${String(Date.now())}`
			});
			deps.logger.info(`Reaction event enqueued: ${body.action} ${body.emoji}`);
			res.writeHead(200, { "Content-Type": "application/json" });
			res.end(JSON.stringify({ ok: true }));
		} catch (err) {
			deps.logger.warn(`Reaction event handler error: ${String(err)}`);
			res.writeHead(500, { "Content-Type": "application/json" });
			res.end(JSON.stringify({ error: "internal_error" }));
		}
	};
}
//#endregion
//#region extensions/pazi/src/slack-thread-cache-persistence.ts
const STORE_VERSION = 1;
const TTL_MS = 1440 * 60 * 1e3;
const POLL_INTERVAL_MS = 5e3;
function loadFromDisk(filePath, logWarn) {
	let raw;
	try {
		raw = fs.readFileSync(filePath, "utf-8");
	} catch (err) {
		if (!(typeof err === "object" && err != null && "code" in err && err.code === "ENOENT")) logWarn?.(`pazi: failed reading persisted slack thread cache at ${filePath}: ${String(err)}`);
		return;
	}
	let parsed;
	try {
		parsed = JSON.parse(raw);
	} catch {
		logWarn?.(`pazi: ignoring invalid slack thread cache JSON at ${filePath}`);
		return;
	}
	const obj = parsed;
	if (obj?.version !== STORE_VERSION || !Array.isArray(obj.entries)) return;
	const now = Date.now();
	const valid = [];
	for (const entry of obj.entries) {
		if (typeof entry?.key !== "string" || !entry.key) continue;
		if (typeof entry?.ts !== "number" || !Number.isFinite(entry.ts) || entry.ts <= 0) continue;
		if (now - entry.ts > TTL_MS) continue;
		valid.push([entry.key, entry.ts]);
	}
	if (valid.length > 0) hydrateSlackThreadParticipationCache(valid);
}
/** Cheap size+sum fingerprint — avoids sorting the full map on every poll. */
function snapshotFingerprint(snapshot) {
	let sum = 0;
	for (const ts of snapshot.values()) sum += ts;
	return `${snapshot.size}:${sum}`;
}
async function startSlackThreadCachePersistence(params) {
	const filePath = path.join(params.stateDir, "pazi", "slack", "sent-thread-cache.json");
	loadFromDisk(filePath, params.logWarn);
	const withWriteLock = createAsyncLock();
	let hasLoggedPersistError = false;
	let lastFingerprint = snapshotFingerprint(getSlackThreadParticipationEntriesSnapshot());
	async function persistIfChanged() {
		await withWriteLock(async () => {
			const snapshot = getSlackThreadParticipationEntriesSnapshot();
			const fingerprint = snapshotFingerprint(snapshot);
			if (fingerprint === lastFingerprint) return;
			const payload = {
				version: STORE_VERSION,
				entries: [...snapshot.entries()].map(([key, ts]) => ({
					key,
					ts
				}))
			};
			try {
				await writeJsonAtomic(filePath, payload, {
					mode: 384,
					ensureDirMode: 448,
					trailingNewline: true
				});
				lastFingerprint = fingerprint;
				hasLoggedPersistError = false;
			} catch (err) {
				if (!hasLoggedPersistError) {
					hasLoggedPersistError = true;
					params.logWarn?.(`pazi: failed persisting slack thread cache at ${filePath}: ${String(err)}`);
				}
			}
		});
	}
	const timer = setInterval(() => {
		persistIfChanged();
	}, POLL_INTERVAL_MS);
	const flush = async () => {
		await persistIfChanged();
	};
	const stop = async () => {
		clearInterval(timer);
		await flush();
	};
	return {
		flush,
		stop
	};
}
//#endregion
//#region extensions/pazi/src/slack-thread-reply-mode.ts
const DEFAULT_ACK_MESSAGE = "On it";
/**
* Global suppression registry shared via globalThis.
*
* Why globalThis instead of module scope?
* ─────────────────────────────────────
* The pazi extension is loaded as TypeScript via jiti with tryNative=false,
* which creates a separate module graph from the gateway's native ESM modules.
* Module-scoped closures (like the `suppressionChecks[]` array inside
* `registerSlackReplySuppression`) are duplicated — the extension writes to
* jiti's copy while the gateway's `shouldSuppressSlackReply` reads from the
* native ESM copy, which is always empty.
*
* By storing the suppressed threads map on globalThis, all module instances
* (jiti and native ESM) share the same state. The `message_sending` hook
* (which runs in the gateway's own context) reads from the same map that
* the `message_received` hook writes to.
*/
const GLOBAL_KEY = "__openclawPaziSlackSuppressedThreads";
function getGlobalSuppressedThreads() {
	const g = globalThis;
	if (!g[GLOBAL_KEY]) g[GLOBAL_KEY] = /* @__PURE__ */ new Map();
	return g[GLOBAL_KEY];
}
function resolveThreadReplyConfig(cfg, accountId) {
	const account = cfg?.channels?.slack?.accounts?.[accountId];
	if (!account || typeof account !== "object") return {
		mode: "quiet",
		ackMessage: DEFAULT_ACK_MESSAGE
	};
	const raw = account;
	return {
		mode: raw.threadReplyMode === "summary-only" || raw.threadReplyMode === "quiet" ? raw.threadReplyMode : raw.threadReplyMode === "full" ? "full" : "quiet",
		ackMessage: typeof raw.ackMessage === "string" && raw.ackMessage.trim() ? raw.ackMessage.trim() : DEFAULT_ACK_MESSAGE
	};
}
/**
* Extract the Slack target ID from a `from` or `conversationId` string.
* Observed formats: "channel:C123", "user:U123", "slack:C123", "C123"
* Returns the bare ID (C/G/D/U prefix + alphanumeric).
*/
function extractSlackTargetId(from) {
	return from.match(/(?:^|:)([CGDU][A-Z0-9]+)$/i)?.[1] ?? null;
}
/**
* Build a composite key for thread tracking.
*/
function threadKey(accountId, targetId, threadTs) {
	return `${accountId}:${targetId}:${threadTs}`;
}
/**
* Check whether a given Slack account has any active suppressed threads.
*/
function hasActiveSuppression(accountId) {
	const suppressedThreads = getGlobalSuppressedThreads();
	for (const thread of suppressedThreads.values()) if (thread.accountId === accountId) return true;
	return false;
}
function registerSlackThreadReplyMode(api) {
	const suppressedThreads = getGlobalSuppressedThreads();
	api.on("message_sending", (event, ctx) => {
		if (ctx.channelId !== "slack") return;
		const accountId = ctx.accountId ?? "default";
		const threadTs = typeof event?.metadata?.threadTs === "string" ? event.metadata.threadTs : typeof event?.metadata?.threadId === "string" ? event.metadata.threadId : void 0;
		if (!threadTs) {
			if (hasActiveSuppression(accountId)) return { cancel: true };
			return;
		}
		const targetCandidates = [
			typeof event?.metadata?.targetId === "string" ? event.metadata.targetId : void 0,
			typeof event?.metadata?.channelId === "string" ? event.metadata.channelId : void 0,
			typeof event?.to === "string" ? event.to : void 0,
			typeof ctx.conversationId === "string" ? ctx.conversationId : void 0
		];
		let targetId;
		for (const candidate of targetCandidates) {
			const parsed = candidate ? extractSlackTargetId(candidate) : null;
			if (parsed) {
				targetId = parsed;
				break;
			}
		}
		if (targetId) {
			const key = threadKey(accountId, targetId, threadTs);
			if (suppressedThreads.has(key)) return { cancel: true };
			const wildcardKey = threadKey(accountId, "", threadTs);
			if (suppressedThreads.has(wildcardKey)) return { cancel: true };
		}
		for (const thread of suppressedThreads.values()) if (thread.accountId === accountId && thread.threadTs === threadTs) return { cancel: true };
	});
	api.on("message_received", async (event, ctx) => {
		if (ctx.channelId !== "slack") return;
		const accountId = ctx.accountId ?? "default";
		const threadTs = typeof event.metadata?.threadId === "string" ? event.metadata.threadId : void 0;
		if (!threadTs?.trim()) return;
		const cfg = api.runtime.config.loadConfig();
		const config = resolveThreadReplyConfig(cfg, accountId);
		if (config.mode === "full") return;
		const sendTarget = (ctx.conversationId ?? "").trim();
		const rawTargetId = extractSlackTargetId(sendTarget) ?? extractSlackTargetId(event.from ?? "");
		const targetId = sendTarget.startsWith("user:") ? "" : rawTargetId;
		if (targetId == null || !sendTarget) return;
		const key = threadKey(accountId, targetId, threadTs);
		if (suppressedThreads.has(key)) return;
		const thread = {
			accountId,
			targetId,
			sendTarget,
			threadTs,
			mode: config.mode,
			ackMessage: config.ackMessage,
			ackSent: false
		};
		suppressedThreads.set(key, thread);
		if (config.mode === "summary-only") try {
			await sendMessageSlack(sendTarget, config.ackMessage, {
				cfg,
				accountId,
				threadTs
			});
			thread.ackSent = true;
		} catch (err) {
			api.logger.warn(`pazi: failed to send Slack ack: ${err instanceof Error ? err.message : String(err)}`);
		}
	});
	api.on("agent_end", async (event, ctx) => {
		if (ctx.channelId !== "slack") return;
		const skMatch = (ctx.sessionKey ?? "").match(/^agent:([^:]+):slack:(?:channel|user):([^:]+)(?::thread:([^:]+))?/);
		const resolvedAccountId = skMatch?.[1] ?? "default";
		const skThreadTs = skMatch?.[3];
		let matchedKey;
		let matchedThread;
		for (const [key, thread] of suppressedThreads) {
			if (thread.accountId !== resolvedAccountId) continue;
			if (skThreadTs && thread.threadTs !== skThreadTs) continue;
			matchedKey = key;
			matchedThread = thread;
			break;
		}
		if (!matchedThread || !matchedKey) return;
		suppressedThreads.delete(matchedKey);
	});
}
//#endregion
//#region extensions/pazi/src/suppress-channel-auth-crash.ts
/**
* Regex matching non-recoverable channel auth errors that should NOT crash the gateway.
* These errors indicate invalid/expired tokens — restarting won't fix them.
*/
const CHANNEL_AUTH_ERROR_RE = /\binvalid_auth\b|\btoken_revoked\b|\btoken_expired\b|\baccount_inactive\b|\bnot_authed\b|\borg_login_required\b|\bteam_access_not_granted\b|\bmissing_scope\b|\bcannot_find_service\b|\binvalid_token\b/i;
function collectReasonCandidates(reason) {
	const queue = [reason];
	const seen = /* @__PURE__ */ new Set();
	const candidates = [];
	while (queue.length > 0) {
		const current = queue.shift();
		if (current == null || seen.has(current)) continue;
		seen.add(current);
		if (typeof current === "string") {
			candidates.push(current);
			continue;
		}
		if (current instanceof Error) {
			if (current.message) candidates.push(current.message);
			if (current.stack) candidates.push(current.stack);
		}
		if (!current || typeof current !== "object") continue;
		const record = current;
		for (const key of [
			"message",
			"error",
			"code",
			"name",
			"type"
		]) {
			const value = record[key];
			if (typeof value === "string" && value.trim()) candidates.push(value);
		}
		for (const key of [
			"cause",
			"reason",
			"original",
			"error",
			"data"
		]) {
			const nested = record[key];
			if (nested !== void 0) queue.push(nested);
		}
		if (Array.isArray(record.errors)) queue.push(...record.errors);
	}
	return candidates;
}
function formatReasonForLog(reason) {
	if (reason instanceof Error) return reason.message;
	if (typeof reason === "string") return reason;
	const candidates = collectReasonCandidates(reason).map((value) => value.trim()).filter(Boolean);
	if (candidates.length > 0) return candidates[0];
	try {
		return JSON.stringify(reason);
	} catch {
		return String(reason);
	}
}
function isChannelAuthError(reason) {
	if (!reason) return false;
	return collectReasonCandidates(reason).some((value) => CHANNEL_AUTH_ERROR_RE.test(value));
}
/**
* Register a global unhandled-rejection handler that suppresses channel auth
* errors (e.g. Slack invalid_auth) instead of crashing the gateway process.
*
* Without this, an expired Slack token causes an unhandled promise rejection
* on every startup, killing the process ~15s after launch and creating an
* infinite supervisor restart loop.
*/
function installChannelAuthCrashGuard(logger) {
	return registerUnhandledRejectionHandler((reason) => {
		if (isChannelAuthError(reason)) {
			const message = formatReasonForLog(reason);
			logger.error(`Suppressed channel auth crash (token likely expired/revoked): ${message}. Reconfigure the channel credentials to restore functionality.`);
			return true;
		}
		return false;
	});
}
//#endregion
//#region extensions/pazi/src/user-actions/api.ts
function resolveApiParams(pluginConfig) {
	const context = getProxyContext();
	if (!context) throw new Error("No billing context set — workspace may not be initialized yet");
	const apiUrl = resolvePaziBillingConfig({
		pluginConfig,
		env: process.env
	}).apiUrl?.trim();
	if (!apiUrl) throw new Error("PAZI_API_URL not configured");
	let baseUrl;
	try {
		baseUrl = new URL(apiUrl);
	} catch {
		throw new Error(`Invalid PAZI_API_URL: ${apiUrl}`);
	}
	return {
		apiUrl: baseUrl.toString(),
		proxyToken: context.proxyToken
	};
}
async function fetchWithToken(params, url, init) {
	const headers = new Headers(init?.headers);
	headers.set("x-proxy-token", params.proxyToken);
	return await fetch(url, {
		...init,
		headers
	});
}
async function parseResponse(res) {
	const text = await res.text();
	const payload = text.trim() ? JSON.parse(text) : null;
	if (res.ok) return {
		ok: true,
		data: payload
	};
	const record = payload;
	const errMsg = record?.error ?? record?.message ?? res.statusText ?? "Request failed";
	return {
		ok: false,
		error: `Pazi API error (${res.status}): ${errMsg}`
	};
}
async function createUserAction(pluginConfig, body) {
	try {
		const params = resolveApiParams(pluginConfig);
		return await parseResponse(await fetchWithToken(params, new URL("/user-actions", params.apiUrl), {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body)
		}));
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
async function getUserAction(pluginConfig, requestId) {
	try {
		const params = resolveApiParams(pluginConfig);
		return await parseResponse(await fetchWithToken(params, new URL(`/user-actions/${encodeURIComponent(requestId)}`, params.apiUrl)));
	} catch (err) {
		return {
			ok: false,
			error: err instanceof Error ? err.message : String(err)
		};
	}
}
//#endregion
//#region extensions/pazi/src/user-actions/tools.ts
function json(payload) {
	return {
		content: [{
			type: "text",
			text: JSON.stringify(payload, null, 2)
		}],
		details: payload
	};
}
async function sleep(ms, signal) {
	if (signal?.aborted) return "aborted";
	return await new Promise((resolve) => {
		const timer = setTimeout(() => {
			resolve("ok");
		}, ms);
		if (!signal) return;
		const onAbort = () => {
			clearTimeout(timer);
			resolve("aborted");
		};
		signal.addEventListener("abort", onAbort, { once: true });
	});
}
function emitIntegrationEvent(payload) {
	const scope = getPluginRuntimeGatewayRequestScope();
	if (!scope?.context) throw new Error("Cannot emit outside a gateway request.");
	scope.context.broadcast("integration", payload);
}
async function pollUntilResolved(pluginConfig, requestId, service, kind, timeoutMs, pollIntervalMs, signal) {
	const deadline = Date.now() + timeoutMs;
	while (true) {
		if (signal?.aborted) return json({
			status: "aborted",
			requestId
		});
		const result = await getUserAction(pluginConfig, requestId);
		if (!result.ok) return json({ error: result.error });
		const { status } = result.data.request;
		if (status === "completed") {
			const req = result.data.request;
			if (kind === "credentials") {
				const values = req.result?.values ?? {};
				return {
					content: [{
						type: "text",
						text: `Credentials received securely for ${service}. Fields: ${Object.keys(values).join(", ")}\nTip: use save_credential to persist these for future sessions.`
					}],
					details: {
						status: "completed",
						requestId,
						service,
						values
					}
				};
			}
			if (kind === "browser_permission") return json({
				status: "completed",
				requestId,
				enabled: true,
				message: "Browser permission granted. Browsing tools are now available."
			});
			return json({
				status: "completed",
				requestId,
				service,
				confirmed: true
			});
		}
		if (status === "cancelled") return json({
			status: "cancelled",
			requestId,
			service
		});
		if (status === "expired") return json({
			status: "expired",
			requestId
		});
		if (Date.now() >= deadline) return json({
			status: "timeout",
			requestId
		});
		const waitMs = Math.min(pollIntervalMs, deadline - Date.now());
		if (waitMs > 0) {
			if (await sleep(waitMs, signal) === "aborted") return json({
				status: "aborted",
				requestId
			});
		}
	}
}
function createUserActionTools(deps) {
	return [
		{
			name: "ask_for_credentials",
			label: "Ask For Credentials",
			description: "Prompt the user to enter credentials (API keys, passwords, tokens). Opens a secure form in the user's dashboard. Waits for the user to submit and returns the entered values. Works in all session types (text, voice, web, Slack). Use when you need credentials for a third-party service.",
			parameters: Type.Object({
				service: Type.String({ description: "Name of the service (e.g., 'GitHub', 'AWS')" }),
				fields: Type.Array(Type.String(), { description: "Credential field names to request (e.g., ['api_key', 'secret'])" }),
				message: Type.Optional(Type.String({ description: "Explanation of why credentials are needed" })),
				timeoutMs: Type.Optional(Type.Number({ description: "Max wait time in ms (default: 120000)" })),
				pollIntervalMs: Type.Optional(Type.Number({ description: "Poll interval in ms (default: 3000)" }))
			}, { additionalProperties: false }),
			async execute(_toolCallId, params, signal) {
				try {
					const service = typeof params.service === "string" ? params.service.trim() : "";
					const fields = params.fields;
					const message = typeof params.message === "string" ? params.message.trim() : void 0;
					const timeoutMs = typeof params.timeoutMs === "number" && params.timeoutMs > 0 ? params.timeoutMs : 12e4;
					const pollIntervalMs = typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0 ? params.pollIntervalMs : 3e3;
					if (!service) throw new Error("service is required");
					if (!Array.isArray(fields) || fields.length === 0) throw new Error("fields must be a non-empty array of strings");
					const fieldNames = fields.map((f) => typeof f === "string" ? f.trim() : String(f));
					const created = await createUserAction(deps.pluginConfig, {
						kind: "credentials",
						service,
						fields: fieldNames,
						message: message || void 0
					});
					if (!created.ok) return json({ error: created.error });
					const requestId = created.data.request.requestId;
					emitIntegrationEvent({
						action: "credentials_required",
						requestId,
						service,
						fields: fieldNames,
						message: message || void 0
					});
					return await pollUntilResolved(deps.pluginConfig, requestId, service, "credentials", timeoutMs, pollIntervalMs, signal);
				} catch (err) {
					return json({ error: err instanceof Error ? err.message : String(err) });
				}
			}
		},
		{
			name: "ask_for_browser_login",
			label: "Ask For Browser Login",
			description: "Prompt the user to log into a website in their browser. Opens a card in the dashboard with a link and confirmation button. Waits for the user to confirm they've logged in. Works in all session types. Use when the agent needs cookie-based authentication or the service has no API integration.",
			parameters: Type.Object({
				service: Type.String({ description: "Name of the service (e.g., 'Google', 'Jira')" }),
				url: Type.String({ description: "URL to open for login" }),
				message: Type.Optional(Type.String({ description: "Instructions for the user" })),
				timeoutMs: Type.Optional(Type.Number({ description: "Max wait time in ms (default: 120000)" })),
				pollIntervalMs: Type.Optional(Type.Number({ description: "Poll interval in ms (default: 3000)" }))
			}, { additionalProperties: false }),
			async execute(_toolCallId, params, signal) {
				try {
					const service = typeof params.service === "string" ? params.service.trim() : "";
					const url = typeof params.url === "string" ? params.url.trim() : "";
					const message = typeof params.message === "string" ? params.message.trim() : void 0;
					const timeoutMs = typeof params.timeoutMs === "number" && params.timeoutMs > 0 ? params.timeoutMs : 12e4;
					const pollIntervalMs = typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0 ? params.pollIntervalMs : 3e3;
					if (!service) throw new Error("service is required");
					if (!url) throw new Error("url is required");
					const created = await createUserAction(deps.pluginConfig, {
						kind: "browser_login",
						service,
						url,
						message: message || void 0
					});
					if (!created.ok) return json({ error: created.error });
					const requestId = created.data.request.requestId;
					emitIntegrationEvent({
						action: "browser_login_required",
						requestId,
						service,
						url,
						message: message || void 0
					});
					return await pollUntilResolved(deps.pluginConfig, requestId, service, "browser_login", timeoutMs, pollIntervalMs, signal);
				} catch (err) {
					return json({ error: err instanceof Error ? err.message : String(err) });
				}
			}
		},
		{
			name: "request_browser_permission",
			label: "Request Browser Permission",
			description: "Ask the user to enable web browsing for this workspace. Use this when you need to use browser, web_search, web_fetch, or browser_use tools but they are currently disabled. Opens a permission dialog in the user's dashboard.",
			parameters: Type.Object({
				message: Type.Optional(Type.String({ description: "Explain to the user why browsing is needed" })),
				timeoutMs: Type.Optional(Type.Number({ description: "Max wait time in ms (default: 120000)" })),
				pollIntervalMs: Type.Optional(Type.Number({ description: "Poll interval in ms (default: 3000)" }))
			}, { additionalProperties: false }),
			async execute(_toolCallId, params, signal) {
				try {
					const message = typeof params.message === "string" ? params.message.trim() : void 0;
					const timeoutMs = typeof params.timeoutMs === "number" && params.timeoutMs > 0 ? params.timeoutMs : 12e4;
					const pollIntervalMs = typeof params.pollIntervalMs === "number" && params.pollIntervalMs > 0 ? params.pollIntervalMs : 3e3;
					const created = await createUserAction(deps.pluginConfig, {
						kind: "browser_permission",
						service: "Web Browsing",
						message: message || void 0
					});
					if (!created.ok) return json({ error: created.error });
					const requestId = created.data.request.requestId;
					emitIntegrationEvent({
						action: "browser_permission_required",
						requestId,
						message: message || void 0
					});
					const result = await pollUntilResolved(deps.pluginConfig, requestId, "Web Browsing", "browser_permission", timeoutMs, pollIntervalMs, signal);
					const details = result.details;
					if (details?.status === "completed" || details?.enabled === true) await deps.onBrowserPermissionGranted?.();
					return result;
				} catch (err) {
					return json({ error: err instanceof Error ? err.message : String(err) });
				}
			}
		}
	];
}
//#endregion
//#region extensions/pazi/index.ts
function normalizePluginConfig(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) return null;
	return value;
}
async function stopServer(server, logger) {
	await new Promise((resolve) => {
		server.close((err) => {
			if (err) logger.warn(`pazi proxy shutdown failed: ${String(err)}`);
			resolve();
		});
	});
}
var pazi_default = {
	id: "pazi",
	name: "Pazi Proxy",
	description: "Routes Anthropic calls through the Pazi API.",
	register(api) {
		installChannelAuthCrashGuard(api.logger);
		configurePersistenceWarnLogger((message) => {
			api.logger.warn(message);
		});
		const stateDir = api.runtime.state.resolveStateDir();
		configurePersistencePath(path.join(stateDir, "pazi", "proxy-context.json"));
		const defaultAgentId = resolveDefaultAgentId(api.config);
		const resolveWorkspace = (requestedAgentId) => {
			const requested = typeof requestedAgentId === "number" ? String(requestedAgentId) : requestedAgentId;
			const normalized = typeof requested === "string" && requested.trim() ? normalizeAgentId(requested) : defaultAgentId;
			return {
				agentId: normalized,
				workspaceDir: resolveAgentWorkspaceDir(api.config, normalized)
			};
		};
		const pluginConfig = normalizePluginConfig(api.pluginConfig);
		const gatewayAuthToken = typeof api.config.gateway?.auth?.token === "string" ? api.config.gateway.auth.token : void 0;
		const contextHandler = createPaziContextHandler({
			configToken: gatewayAuthToken,
			env: process.env,
			logger: api.logger
		});
		const browserEnabledHandler = createPaziBrowserEnabledHandler({
			configToken: gatewayAuthToken,
			env: process.env,
			logger: api.logger
		});
		const uploadHandler = createPaziUploadHandler({
			configToken: gatewayAuthToken,
			env: process.env,
			logger: api.logger
		});
		api.registerGatewayMethod("pazi.files.list", createPaziFilesList(resolveWorkspace));
		api.registerGatewayMethod("pazi.files.get", createPaziFilesGet(resolveWorkspace));
		api.registerGatewayMethod("pazi.files.set", createPaziFilesSet(resolveWorkspace));
		api.registerGatewayMethod("pazi.files.delete", createPaziFilesDelete(resolveWorkspace));
		api.registerGatewayMethod("pazi.memory.get", createPaziMemoryGet(resolveWorkspace));
		api.registerGatewayMethod("skills.create", createPaziSkillsCreateHandler({
			loadConfig: () => api.runtime.config.loadConfig(),
			resolveWorkspace
		}));
		api.registerGatewayMethod("skills.delete", createPaziSkillsDeleteHandler({
			loadConfig: () => api.runtime.config.loadConfig(),
			writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
			resolveWorkspace
		}));
		const skillsDeps = {
			resolveWorkspace,
			loadConfig: () => api.runtime.config.loadConfig()
		};
		api.registerGatewayMethod("pazi.skills.capabilities", createPaziSkillsCapabilities({ loadConfig: () => api.runtime.config.loadConfig() }));
		api.registerGatewayMethod("pazi.skills.get", createPaziSkillsGet(skillsDeps));
		api.registerGatewayMethod("pazi.skills.set", createPaziSkillsSet(skillsDeps));
		api.registerGatewayMethod("pazi.templates.instantiate", createPaziTemplatesInstantiateHandler({ resolveWorkspace }));
		api.registerGatewayMethod("pazi.templates.list", createPaziTemplatesListHandler());
		api.registerGatewayMethod("pazi.channels.configure", createPaziChannelsConfigureHandler({
			loadConfig: () => api.runtime.config.loadConfig(),
			writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg),
			probeSlack: (token, timeoutMs) => probeSlack(token, timeoutMs),
			probeTelegram: (token, timeoutMs, proxyUrl) => probeTelegram(token, timeoutMs, proxyUrl),
			onConfigured: (result) => {
				trackChannelConnected(pluginConfig, result.channel, result.accountId);
			}
		}));
		api.registerGatewayMethod("pazi.channels.disconnect", createPaziChannelsDisconnectHandler({
			loadConfig: () => api.runtime.config.loadConfig(),
			writeConfigFile: (cfg) => api.runtime.config.writeConfigFile(cfg)
		}));
		const pairingGatewayDeps = {
			loadConfig: () => api.runtime.config.loadConfig(),
			env: process.env,
			logWarn: (message) => {
				api.logger.warn(message);
			},
			listRequests: ({ channel, accountId, env }) => listChannelPairingRequests(channel, env, accountId),
			approveCode: ({ channel, accountId, code, env }) => approveChannelPairingCode({
				channel,
				accountId,
				code,
				env
			}),
			notifyApproved: ({ channelId, id, cfg }) => notifyPairingApproved({
				channelId,
				id,
				cfg
			})
		};
		api.registerGatewayMethod("pazi.channels.pairing.list", createPaziChannelsPairingListHandler(pairingGatewayDeps));
		api.registerGatewayMethod("pazi.channels.pairing.approve", createPaziChannelsPairingApproveHandler(pairingGatewayDeps));
		api.registerHook("agent:bootstrap", paziBootstrapActionsHook, {
			name: "pazi-bootstrap-actions",
			description: "Appends Pazi frontend-action docs to AGENTS.md"
		});
		api.registerHook("agent:bootstrap", paziBootstrapUserHook, {
			name: "pazi-bootstrap-user",
			description: "Injects user name from .pazi/user-meta.json into USER.md bootstrap context"
		});
		registerToolResultPersistHook(api);
		registerProxyAgentSyncHook(api);
		registerWebchatFileSupportHook(api);
		registerTranscriptionBillingHook(api);
		registerSlackThreadReplyMode(api);
		registerBrowserPromptHook(api);
		registerBrowserGuardHook(api);
		const userActionTools = createUserActionTools({
			pluginConfig,
			onBrowserPermissionGranted: async () => {
				const ctx = getProxyContext();
				if (!ctx) return;
				setProxyContext({
					...ctx,
					browserEnabled: true
				});
			}
		});
		for (const tool of userActionTools) api.registerTool(tool);
		const credentialTools = createCredentialTools();
		for (const tool of credentialTools) api.registerTool(tool);
		const reactTool = createReactToMessageTool({ pluginConfig });
		api.registerTool(reactTool);
		const setGoalTool = createSetGoalTool({ pluginConfig });
		api.registerTool(setGoalTool);
		if (resolveBrowserUseConfig({
			pluginConfig,
			env: process.env
		}).browserUseEnabled) {
			const browserUseTools = createBrowserUseTools({ pluginConfig });
			for (const tool of browserUseTools) api.registerTool(tool);
		}
		api.registerImageGenerationProvider(buildPaziImageGenerationProvider({
			pluginConfig,
			env: process.env
		}));
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
			stop: async () => {}
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
			}
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
			}
		});
		api.registerHttpRoute({
			path: "/health",
			auth: "gateway",
			handler: (_req, res) => {
				res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
				res.end(JSON.stringify({
					status: "ok",
					timestamp: (/* @__PURE__ */ new Date()).toISOString()
				}));
			}
		});
		api.registerHttpRoute({
			path: "/status",
			auth: "gateway",
			handler: (_req, res) => {
				const lastActivityAtMs = getProxyLastActivityAt();
				res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
				res.end(JSON.stringify({
					status: "running",
					busy: isProxyBusyForStatus(),
					lastActivityAt: lastActivityAtMs === null ? null : new Date(lastActivityAtMs).toISOString(),
					version: process.env.AGENT_VERSION ?? "unknown",
					environment: "production"
				}));
			}
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
			}
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
			}
		});
		const reactionEventHandler = createReactionEventHandler({
			configToken: gatewayAuthToken,
			logger: api.logger
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
			}
		});
		let proxyServer = null;
		let stopSlackThreadCachePersistence = null;
		api.registerService({
			id: "pazi-slack-thread-cache-persistence",
			start: async () => {
				if (stopSlackThreadCachePersistence) {
					await stopSlackThreadCachePersistence();
					stopSlackThreadCachePersistence = null;
				}
				stopSlackThreadCachePersistence = (await startSlackThreadCachePersistence({
					stateDir: api.runtime.state.resolveStateDir(),
					logWarn: (message) => api.logger.warn(message)
				})).stop;
			},
			stop: async () => {
				if (!stopSlackThreadCachePersistence) return;
				await stopSlackThreadCachePersistence();
				stopSlackThreadCachePersistence = null;
			}
		});
		api.registerService({
			id: "pazi-proxy",
			start: async () => {
				const resolved = resolvePaziBillingConfig({
					pluginConfig,
					env: process.env
				});
				proxyServer = await startPaziProxy({
					apiUrl: resolved.apiUrl,
					port: resolved.proxyPort,
					logger: api.logger
				});
				if (resolved.apiUrl) {
					installBraveEnvDefaults();
					installBraveFetchInterceptor(resolved.apiUrl);
				}
			},
			stop: async () => {
				uninstallBraveFetchInterceptor();
				uninstallBraveEnvDefaults();
				if (!proxyServer) return;
				await stopServer(proxyServer, api.logger);
				proxyServer = null;
			}
		});
	}
};
//#endregion
export { pazi_default as default };
