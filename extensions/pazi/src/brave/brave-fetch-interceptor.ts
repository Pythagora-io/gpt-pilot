/**
 * Intercepts globalThis.fetch calls targeting the Brave Search API
 * and rewrites them to go through the Pazi backend proxy.
 *
 * The Pazi backend handles Brave API key injection and credit deduction.
 */

import { getProxyContext } from "../context.js";
import { BRAVE_PROXY_SENTINEL } from "./brave-env.js";

const BRAVE_ORIGIN = "https://api.search.brave.com";

/** Brave API path prefixes that should be proxied */
const PROXIED_PATH_PREFIXES = ["/res/v1/web/search", "/res/v1/llm/context"];

type FetchFn = typeof globalThis.fetch;
type RequestWithDuplex = Request & { duplex?: "half" };
type RequestInitWithDuplex = RequestInit & { duplex?: "half" };

let originalFetch: FetchFn | null = null;
let installedApiUrl: string | null = null;

function isBraveRequest(url: URL): boolean {
  return (
    url.origin === BRAVE_ORIGIN &&
    PROXIED_PATH_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))
  );
}

/**
 * Install the fetch interceptor.
 * Saves the original globalThis.fetch and replaces it with a version
 * that rewrites Brave Search API requests to go through the Pazi backend.
 *
 * @param apiUrl The Pazi API base URL (e.g. "https://api.pazi.ai")
 */
export function installBraveFetchInterceptor(apiUrl: string): void {
  if (originalFetch) {
    // Already installed — update the API URL if changed
    installedApiUrl = apiUrl;
    return;
  }

  const baseFetch = globalThis.fetch;
  originalFetch = baseFetch;
  installedApiUrl = apiUrl;

  const interceptedFetch: FetchFn = (input, init?) => {
    const currentApiUrl = installedApiUrl;
    if (!currentApiUrl) {
      // Defensive: if uninstalled during a call, fall through
      return baseFetch(input, init);
    }

    let url: URL | null = null;
    try {
      if (typeof input === "string") {
        url = new URL(input);
      } else if (input instanceof URL) {
        url = input;
      } else if (input instanceof Request) {
        url = new URL(input.url);
      }
    } catch {
      // Not a valid URL — pass through
    }

    if (!url || !isBraveRequest(url)) {
      return baseFetch(input, init);
    }

    // Only rewrite when the Brave env key is the sentinel used for Pazi proxy mode.
    // If a real BRAVE_API_KEY is configured, keep direct Brave behavior unchanged.
    if (process.env.BRAVE_API_KEY !== BRAVE_PROXY_SENTINEL) {
      return baseFetch(input, init);
    }

    // Rewrite to Pazi proxy: /brave/<path+query>
    const bravePath = url.pathname + url.search;
    const proxyUrl = `${currentApiUrl}/brave${bravePath}`;

    // Get proxy context for authentication
    const context = getProxyContext();
    if (!context) {
      // No proxy context available — fall through to original fetch
      // (will fail with invalid API key, but that's expected)
      return baseFetch(input, init);
    }

    // Build rewritten headers: keep Accept/Content-Type, strip X-Subscription-Token,
    // add proxy auth headers
    const originalHeaders = new Headers(
      init?.headers ?? (input instanceof Request ? input.headers : undefined),
    );

    const newHeaders = new Headers();
    // Forward Accept header
    const accept = originalHeaders.get("Accept");
    if (accept) {
      newHeaders.set("Accept", accept);
    }
    // Forward Content-Type for request bodies (POST llm/context, future Brave methods)
    const contentType = originalHeaders.get("Content-Type");
    if (contentType) {
      newHeaders.set("Content-Type", contentType);
    }
    // Forward Accept-Encoding if present
    const acceptEncoding = originalHeaders.get("Accept-Encoding");
    if (acceptEncoding) {
      newHeaders.set("Accept-Encoding", acceptEncoding);
    }

    // Add proxy authentication
    newHeaders.set("X-Proxy-Token", context.proxyToken);
    newHeaders.set("X-User-Id", context.userId);

    // Build new init, stripping `dispatcher` (SSRF guard pins to Brave's IP,
    // which would fail when redirected to the Pazi API host)
    const newInit: RequestInitWithDuplex = {
      method: init?.method ?? (input instanceof Request ? input.method : "GET"),
      headers: newHeaders,
      signal: init?.signal ?? (input instanceof Request ? input.signal : undefined),
      body: init?.body ?? (input instanceof Request ? input.body : undefined),
    };
    const duplex =
      (init as RequestInitWithDuplex | undefined)?.duplex ??
      (input instanceof Request ? (input as RequestWithDuplex).duplex : undefined);
    if (duplex) {
      newInit.duplex = duplex;
    }

    return baseFetch(proxyUrl, newInit);
  };

  globalThis.fetch = interceptedFetch;
}

/**
 * Uninstall the fetch interceptor, restoring the original globalThis.fetch.
 */
export function uninstallBraveFetchInterceptor(): void {
  if (originalFetch) {
    globalThis.fetch = originalFetch;
    originalFetch = null;
  }
  installedApiUrl = null;
}
