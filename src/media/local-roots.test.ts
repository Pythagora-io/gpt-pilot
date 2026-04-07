import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getAgentScopedMediaLocalRoots, getDefaultMediaLocalRoots } from "./local-roots.js";

function normalizeHostPath(value: string): string {
  return path.normalize(path.resolve(value));
}

describe("local media roots", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("keeps temp, media cache, and workspace roots by default", () => {
    const stateDir = path.join("/tmp", "openclaw-media-roots-state");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const roots = getDefaultMediaLocalRoots();
    const normalizedRoots = roots.map(normalizeHostPath);

    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "media")));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace")));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "sandboxes")));
    expect(normalizedRoots).not.toContain(normalizeHostPath(path.join(stateDir, "agents")));
    expect(roots.length).toBeGreaterThanOrEqual(3);
  });

  it("adds configured agent workspaces without re-opening broad agent state roots", () => {
    const stateDir = path.join("/tmp", "openclaw-agent-media-roots-state");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    // "main" is the default agent; "ops" is a non-default agent whose
    // workspace resolves to stateDir/workspace-ops by convention.
    const cfg = {
      agents: {
        list: [{ id: "main", default: true }, { id: "ops" }],
      },
    };

    const roots = getAgentScopedMediaLocalRoots(cfg, "ops");
    const normalizedRoots = roots.map(normalizeHostPath);

    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace-ops")));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "sandboxes")));
    expect(normalizedRoots).not.toContain(normalizeHostPath(path.join(stateDir, "agents")));
  });

  it("includes all configured agents' workspace directories", () => {
    const stateDir = path.join("/tmp", "openclaw-multi-agent-roots");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const cfg = {
      agents: {
        list: [
          { id: "alpha", workspace: path.join(stateDir, "workspace-alpha") },
          { id: "beta" },
          { id: "gamma" },
        ],
      },
    };

    const roots = getAgentScopedMediaLocalRoots(cfg, "alpha");
    const normalizedRoots = roots.map(normalizeHostPath);

    // All three agent workspaces should be present
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace-alpha")));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace-beta")));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace-gamma")));
  });

  it("deduplicates when two agents share the same workspace path", () => {
    const stateDir = path.join("/tmp", "openclaw-dedup-roots");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const sharedWorkspace = path.join("/tmp", "shared-workspace");
    const cfg = {
      agents: {
        list: [
          { id: "a", workspace: sharedWorkspace },
          { id: "b", workspace: sharedWorkspace },
        ],
      },
    };

    const roots = getAgentScopedMediaLocalRoots(cfg, "a");
    const normalizedRoots = roots.map(normalizeHostPath);

    const sharedNormalized = normalizeHostPath(sharedWorkspace);
    const count = normalizedRoots.filter((r) => r === sharedNormalized).length;
    expect(count).toBe(1);
  });

  it("does not include unconfigured agent workspace — only configured agents", () => {
    const stateDir = path.join("/tmp", "openclaw-unconfigured-agent");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const cfg = {
      agents: {
        list: [{ id: "configured", workspace: path.join(stateDir, "workspace-configured") }],
      },
    };

    const roots = getAgentScopedMediaLocalRoots(cfg, "adhoc");
    const normalizedRoots = roots.map(normalizeHostPath);

    // Configured agent's workspace should be present
    expect(normalizedRoots).toContain(
      normalizeHostPath(path.join(stateDir, "workspace-configured")),
    );
    // Unconfigured/ad-hoc agent's workspace should NOT be present
    expect(normalizedRoots).not.toContain(
      normalizeHostPath(path.join(stateDir, "workspace-adhoc")),
    );
  });

  it("falls back to default agent workspace when config has no agents list", () => {
    const stateDir = path.join("/tmp", "openclaw-no-agents-list");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const baseRoots = getDefaultMediaLocalRoots();
    const scopedRoots = getAgentScopedMediaLocalRoots({});
    const normalizedScoped = scopedRoots.map(normalizeHostPath);

    // listAgentIds({}) returns [DEFAULT_AGENT_ID] ("main"), whose workspace
    // gets added to the base roots. The scoped roots should contain at least
    // one more entry than the base roots (the default agent's workspace).
    expect(scopedRoots.length).toBeGreaterThan(baseRoots.length);
    // Base roots should still be present
    expect(normalizedScoped).toContain(normalizeHostPath(path.join(stateDir, "media")));
    expect(normalizedScoped).toContain(normalizeHostPath(path.join(stateDir, "workspace")));
  });

  it("includes custom workspace path outside state dir", () => {
    const stateDir = path.join("/tmp", "openclaw-custom-ws");
    vi.stubEnv("OPENCLAW_STATE_DIR", stateDir);

    const customPath = "/tmp/my-custom-workspace";
    const cfg = {
      agents: {
        list: [{ id: "custom", workspace: customPath }, { id: "standard" }],
      },
    };

    const roots = getAgentScopedMediaLocalRoots(cfg, "custom");
    const normalizedRoots = roots.map(normalizeHostPath);

    expect(normalizedRoots).toContain(normalizeHostPath(customPath));
    expect(normalizedRoots).toContain(normalizeHostPath(path.join(stateDir, "workspace-standard")));
  });
});
