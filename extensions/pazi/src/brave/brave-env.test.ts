import { afterEach, describe, expect, it } from "vitest";
import {
  BRAVE_PROXY_SENTINEL,
  installBraveEnvDefaults,
  uninstallBraveEnvDefaults,
} from "./brave-env.js";

const originalBraveApiKey = process.env.BRAVE_API_KEY;

afterEach(() => {
  uninstallBraveEnvDefaults();
  if (originalBraveApiKey === undefined) {
    delete process.env.BRAVE_API_KEY;
  } else {
    process.env.BRAVE_API_KEY = originalBraveApiKey;
  }
});

describe("installBraveEnvDefaults", () => {
  it("sets a sentinel BRAVE_API_KEY when missing", () => {
    delete process.env.BRAVE_API_KEY;

    installBraveEnvDefaults();

    expect(process.env.BRAVE_API_KEY).toBe(BRAVE_PROXY_SENTINEL);
  });

  it("restores the original BRAVE_API_KEY on uninstall", () => {
    process.env.BRAVE_API_KEY = "original-key";

    installBraveEnvDefaults();
    uninstallBraveEnvDefaults();

    expect(process.env.BRAVE_API_KEY).toBe("original-key");
  });

  it("removes BRAVE_API_KEY on uninstall when originally missing", () => {
    delete process.env.BRAVE_API_KEY;

    installBraveEnvDefaults();
    uninstallBraveEnvDefaults();

    expect(process.env.BRAVE_API_KEY).toBeUndefined();
  });
});
