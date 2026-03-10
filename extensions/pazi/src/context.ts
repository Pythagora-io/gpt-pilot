type ProxyContext = {
  userId: string;
  agentId: string;
  proxyToken: string;
};

const STALE_BUSY_AFTER_MS = 30 * 60 * 1000;

let currentContext: ProxyContext | null = null;
let lastProxyActivityAtMs: number | null = null;

export function getProxyContext(): ProxyContext | null {
  return currentContext;
}

export function setProxyContext(ctx: ProxyContext): void {
  currentContext = ctx;
}

export function markProxyActivity(atMs = Date.now()): void {
  lastProxyActivityAtMs = atMs;
}

export function getProxyLastActivityAt(): number | null {
  return lastProxyActivityAtMs;
}

export function isProxyBusyForStatus(nowMs = Date.now()): boolean {
  if (!currentContext || lastProxyActivityAtMs === null) {
    return false;
  }
  return nowMs - lastProxyActivityAtMs <= STALE_BUSY_AFTER_MS;
}

export function clearProxyContext(): void {
  currentContext = null;
  lastProxyActivityAtMs = null;
}
