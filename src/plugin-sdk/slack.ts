// Legacy Slack runtime surface kept for in-repo extensions.
// Not exported in published package.json subpath aliases.

export { sendMessageSlack } from "../../extensions/slack/runtime-api.js";
export {
  getSlackThreadParticipationEntriesSnapshot,
  hydrateSlackThreadParticipationCache,
  recordSlackThreadParticipation,
} from "../../extensions/slack/src/sent-thread-cache.js";
