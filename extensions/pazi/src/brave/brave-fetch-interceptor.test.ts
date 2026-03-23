import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearProxyContext, setProxyContext } from "../context.js";
import { BRAVE_PROXY_SENTINEL } from "./brave-env.js";
import {
  installBraveFetchInterceptor,
  uninstallBraveFetchInterceptor,
} from "./brave-fetch-interceptor.js";

describe("installBraveFetchInterceptor", () => {
  let originalFetch: typeof globalThis.fetch;
  let originalBraveApiKey: string | undefined;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    originalBraveApiKey = process.env.BRAVE_API_KEY;
    process.env.BRAVE_API_KEY = BRAVE_PROXY_SENTINEL;
    clearProxyContext();
  });

  afterEach(() => {
    uninstallBraveFetchInterceptor();
    clearProxyContext();
    globalThis.fetch = originalFetch;
    if (originalBraveApiKey === undefined) {
      delete process.env.BRAVE_API_KEY;
    } else {
      process.env.BRAVE_API_KEY = originalBraveApiKey;
    }
    vi.restoreAllMocks();
  });

  it("rewrites Brave requests to the Pazi proxy with proxy auth headers", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;

    setProxyContext({
      userId: "user-1",
      agentId: "agent-1",
      proxyToken: "proxy-token-1",
    });
    installBraveFetchInterceptor("https://api.pazi.ai");

    await globalThis.fetch("https://api.search.brave.com/res/v1/web/search?q=hello", {
      headers: {
        Accept: "application/json",
        "X-Subscription-Token": "should-not-leak",
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api.pazi.ai/brave/res/v1/web/search?q=hello");

    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("x-proxy-token")).toBe("proxy-token-1");
    expect(headers.get("x-user-id")).toBe("user-1");
    expect(headers.get("x-subscription-token")).toBeNull();
  });

  it("forwards request body for Brave requests", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;

    setProxyContext({
      userId: "user-2",
      agentId: "agent-2",
      proxyToken: "proxy-token-2",
    });
    installBraveFetchInterceptor("https://api.pazi.ai");

    const payload = JSON.stringify({ q: "hello" });

    const requestInit: RequestInit & { dispatcher?: unknown } = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: payload,
      // Keep proxy fetch init free of upstream Brave-specific dispatcher pinning.
      dispatcher: { pinned: true },
    };

    await globalThis.fetch("https://api.search.brave.com/res/v1/llm/context", requestInit);

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init as RequestInit).method).toBe("POST");
    expect((init as RequestInit).body).toBe(payload);
    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get("content-type")).toBe("application/json");
    expect(init).not.toHaveProperty("dispatcher");
  });

  it("falls through to original Brave request when proxy context is missing", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;
    installBraveFetchInterceptor("https://api.pazi.ai");

    await globalThis.fetch("https://api.search.brave.com/res/v1/web/search?q=hello");

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api.search.brave.com/res/v1/web/search?q=hello");
  });

  it("falls through for non-Brave URLs", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;
    installBraveFetchInterceptor("https://api.pazi.ai");

    await globalThis.fetch("https://example.com/health");

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://example.com/health");
  });

  it("falls through for unsupported Brave paths", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;
    installBraveFetchInterceptor("https://api.pazi.ai");

    await globalThis.fetch("https://api.search.brave.com/res/v1/images/search?q=hello");

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api.search.brave.com/res/v1/images/search?q=hello");
  });

  it("does not rewrite when a real BRAVE_API_KEY is configured", async () => {
    process.env.BRAVE_API_KEY = "real-brave-key";
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;
    setProxyContext({
      userId: "user-3",
      agentId: "agent-3",
      proxyToken: "proxy-token-3",
    });
    installBraveFetchInterceptor("https://api.pazi.ai");

    await globalThis.fetch("https://api.search.brave.com/res/v1/web/search?q=hello");

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api.search.brave.com/res/v1/web/search?q=hello");
  });

  it("updates proxy apiUrl when installed again", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;
    setProxyContext({
      userId: "user-4",
      agentId: "agent-4",
      proxyToken: "proxy-token-4",
    });

    installBraveFetchInterceptor("https://api-1.pazi.ai");
    installBraveFetchInterceptor("https://api-2.pazi.ai");

    await globalThis.fetch("https://api.search.brave.com/res/v1/web/search?q=hello");

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api-2.pazi.ai/brave/res/v1/web/search?q=hello");
  });

  it("restores original fetch on uninstall", () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    globalThis.fetch = fetchMock as typeof globalThis.fetch;

    installBraveFetchInterceptor("https://api.pazi.ai");
    const interceptedFetch = globalThis.fetch;
    uninstallBraveFetchInterceptor();

    expect(interceptedFetch).not.toBe(fetchMock);
    expect(globalThis.fetch).toBe(fetchMock);
  });
});
