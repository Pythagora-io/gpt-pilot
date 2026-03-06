#!/usr/bin/env bash
set -euo pipefail

is_truthy() {
  local raw="${1:-}"
  raw="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$raw" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

PAZI_HOME="${PAZI_HOME:-/home/pazi}"
DEFAULT_CONFIG_PATH="$PAZI_HOME/.openclaw/openclaw.json"
CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$DEFAULT_CONFIG_PATH}"
mkdir -p "$(dirname "$CONFIG_PATH")"

BROWSER_USE_FLAG="${BROWSER_USE_ENABLED:-}"

node - "$CONFIG_PATH" "$BROWSER_USE_FLAG" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");

let JSON5;
try {
  JSON5 = require("json5");
} catch {
  JSON5 = { parse: JSON.parse };
}

const configPath = process.argv[2];
const rawEnabled = String(process.argv[3] ?? "").trim();
const browserUseEnabled = /^(1|true|yes|on)$/i.test(rawEnabled);

const readConfig = () => {
  if (!fs.existsSync(configPath)) {
    return {};
  }
  const raw = fs.readFileSync(configPath, "utf8");
  if (!raw.trim()) {
    return {};
  }
  try {
    const parsed = JSON5.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
    return {};
  } catch {
    return {};
  }
};

const cfg = readConfig();

if (browserUseEnabled) {
  if (!cfg.browser || typeof cfg.browser !== "object" || Array.isArray(cfg.browser)) {
    cfg.browser = {};
  }
  cfg.browser.enabled = false;

  if (!cfg.tools || typeof cfg.tools !== "object" || Array.isArray(cfg.tools)) {
    cfg.tools = {};
  }

  const existingDeny = Array.isArray(cfg.tools.deny)
    ? cfg.tools.deny.filter((entry) => typeof entry === "string")
    : [];
  if (!existingDeny.includes("browser")) {
    existingDeny.push("browser");
  }
  cfg.tools.deny = existingDeny;
} else {
  if (cfg.browser && typeof cfg.browser === "object" && !Array.isArray(cfg.browser)) {
    delete cfg.browser.enabled;
    if (Object.keys(cfg.browser).length === 0) {
      delete cfg.browser;
    }
  }

  if (cfg.tools && typeof cfg.tools === "object" && !Array.isArray(cfg.tools)) {
    if (Array.isArray(cfg.tools.deny)) {
      const nextDeny = cfg.tools.deny.filter((entry) => entry !== "browser");
      if (nextDeny.length > 0) {
        cfg.tools.deny = nextDeny;
      } else {
        delete cfg.tools.deny;
      }
    }
    if (Object.keys(cfg.tools).length === 0) {
      delete cfg.tools;
    }
  }
}

fs.mkdirSync(path.dirname(configPath), { recursive: true });
fs.writeFileSync(configPath, `${JSON.stringify(cfg, null, 2)}\n`, "utf8");
NODE

if is_truthy "$BROWSER_USE_FLAG"; then
  echo "BROWSER_USE_ENABLED=true: disabled built-in browser and denied browser tool in $CONFIG_PATH"
else
  echo "BROWSER_USE_ENABLED is false/unset: removed Browser Use override keys in $CONFIG_PATH"
fi

if id -u pazi >/dev/null 2>&1; then
  chown pazi:pazi "$CONFIG_PATH" || true
fi

exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
