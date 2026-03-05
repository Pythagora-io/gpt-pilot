type ProxyContext = {
  userId: string;
  agentId: string;
  proxyToken: string;
};

let currentContext: ProxyContext | null = null;

export function getProxyContext(): ProxyContext | null {
  return currentContext;
}

export function setProxyContext(ctx: ProxyContext): void {
  currentContext = ctx;
}

export function clearProxyContext(): void {
  currentContext = null;
}
